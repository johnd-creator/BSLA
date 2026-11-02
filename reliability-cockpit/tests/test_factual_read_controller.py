"""Only disposable metadata; never calls systemd, Docker or a service."""
import importlib.util
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock
from datetime import datetime,timedelta,timezone
from src.services.factual_read_entitlements import canonical,instant,append_event,ZERO,CAPABILITIES,ISSUER

FILE=Path(__file__).resolve().parents[2]/'deploy/development/local_development.py'
spec=importlib.util.spec_from_file_location('factual_controller_test',FILE)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


class FactualReadControllerTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.state=Path(self.temp.name)
        self.manager=m.LocalDevelopment.__new__(m.LocalDevelopment)
        self.manager.c=SimpleNamespace(STATE=self.state)
        self.root=self.state/'candidate'
        schema=self.root/'reliability-cockpit/src/services/factual_read_entitlements.py'
        schema.parent.mkdir(parents=True)
        schema.write_bytes((FILE.parents[2]/'reliability-cockpit/src/services/factual_read_entitlements.py').read_bytes())

    def tearDown(self):self.temp.cleanup()

    def test_missing_policy_blocks_new_candidate_without_issuing_grants(self):
        with self.assertRaises(RuntimeError):self.manager.factual_read_environment(self.root,required=True)
        self.assertFalse((self.state/'factual-read-120').exists())
        # Older source rollback ignores new policy and leaves it untouched.
        self.assertEqual(self.manager.factual_read_environment(self.state/'old-pr119'),[])

    def policy(self):
        root=self.state/'factual-read-120';root.mkdir(mode=0o700)
        file=root/'grants.ndjson';now=datetime.now(timezone.utc).replace(microsecond=0)
        event=dict(action='ISSUE',grant_id='synthetic-grant',subject='local:synthetic-engineer',assets=['asset:MAXIMO:MXASSET:BSR:IP:SYNTHETIC-A'],capabilities=sorted(CAPABILITIES),not_before=instant(now),expires_at=instant(now+timedelta(hours=1)),actor=ISSUER,approval_ref='synthetic-owner',operator_ref='synthetic-operator',at=instant(now))
        append_event(file,event,expected_head=ZERO)
        approval={k:v for k,v in event.items() if k!='at'}
        approval.update(schema_version=1,expected_head=ZERO)
        a=root/'activation-approval.json';a.write_text(canonical(approval)+'\n');a.chmod(0o600)
        return file

    def test_exact_stable_private_state_bound_to_frontend_only(self):
        file=self.policy()
        expected=['NADI_FACTUAL_READ_POLICY_FILE='+str(file)]
        self.assertEqual(self.manager.factual_read_environment(self.root,required=True),expected)
        self.manager.start=Mock()
        self.manager.start_pair({'root':str(self.root),'node':'synthetic-node','config_path':'synthetic-config','sha':'a'*40,'factual_read_required':True})
        calls=self.manager.start.call_args_list
        self.assertEqual(len(calls),2)
        self.assertNotIn(expected[0],calls[0].args[3])
        self.assertIn(expected[0],calls[1].args[3])

    def test_bad_policy_fails_before_any_pair_process_start(self):
        root=self.state/'factual-read-120';root.mkdir(mode=0o700)
        file=root/'grants.ndjson';file.write_text('synthetic');file.chmod(0o644)
        self.manager.start=Mock()
        with self.assertRaises(RuntimeError):self.manager.start_pair({'root':str(self.root),'node':'synthetic','config_path':'synthetic','sha':'a'*40,'factual_read_required':True})
        self.manager.start.assert_not_called()

    def test_symlink_and_world_readable_directory_denied(self):
        root=self.state/'factual-read-120';root.mkdir(mode=0o700)
        target=self.state/'other';target.write_text('synthetic');target.chmod(0o600)
        file=root/'grants.ndjson';file.symlink_to(target)
        with self.assertRaises(OSError):self.manager.factual_read_environment(self.root,required=True)
        file.unlink();file.write_text('synthetic');file.chmod(0o600);root.chmod(0o755)
        with self.assertRaises(RuntimeError):self.manager.factual_read_environment(self.root,required=True)

    def test_corrupt_or_revoked_grant_denied_before_start_and_old_rollback_preserves_state(self):
        file=self.policy();data=file.read_bytes();file.write_bytes(data.replace(b'"version":1',b'"version":2'))
        self.manager.start=Mock()
        with self.assertRaises(ValueError):self.manager.start_pair({'root':str(self.root),'factual_read_required':True})
        self.manager.start.assert_not_called()
        before=file.read_bytes();self.assertEqual(self.manager.factual_read_environment(self.state/'old-pr119'),[])
        self.assertEqual(file.read_bytes(),before)

    def test_future_event_clock_cannot_pass_task_preflight(self):
        import json,hashlib
        file=self.policy();lines=file.read_text().splitlines();event=json.loads(lines[1]);event.pop('sha256')
        event['at']=instant(datetime.now(timezone.utc)+timedelta(seconds=30))
        event['sha256']=hashlib.sha256(canonical(event).encode()).hexdigest()
        file.write_text(lines[0]+'\n'+canonical(event)+'\n')
        with self.assertRaises(RuntimeError):self.manager.factual_read_environment(self.root,required=True)


if __name__=='__main__':unittest.main()
