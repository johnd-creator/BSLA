"""Disposable Git, policy and transport fixtures; no Docker/systemd/source requests."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from datetime import datetime, timezone, timedelta

DEPLOY=Path(__file__).resolve().parents[2]/'deploy/development'
def load(path):
    spec=importlib.util.spec_from_file_location('test_'+path.stem,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
m=load(DEPLOY/'hierarchy_source_admission.py')
installer=load(DEPLOY/'hierarchy_release_controller.py')


class AdmissionTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.base=Path(self.temp.name);self.base.chmod(0o700)
        self.front=self.base/'front';self.front.mkdir();self.recovery=self.base/'recovery'
        self.state=self.base/'state';self.state.mkdir(mode=0o700);self.control=SimpleNamespace(STATE=self.state,ORIGIN='https://localhost:3000')
        self.git=lambda *args,cwd=None:subprocess.check_output(['git','-c','core.hooksPath=/dev/null',*args],cwd=cwd or self.front,text=True,stderr=subprocess.PIPE).strip()
        self.git('init','-q');self.git('config','user.name','Synthetic');self.git('config','user.email','synthetic@invalid')
        for p in m.PERSISTENCE:
            self.put(p if Path(p).suffix else p+'/synthetic.txt','unchanged')
        self.put('reliability-cockpit/src/api/reliability.py','old')
        self.put('reliability-cockpit/web/lib/api.ts','old')
        self.put('reliability-data-contracts/mappings/maximo-to-contracts.md','old')
        self.put('reliability-cockpit/web/package.json','{"dependencies":{"example":"1.0"}}')
        self.commit();self.old=self.git('rev-parse','HEAD')
        self.git('clone','--no-hardlinks','--quiet',str(self.front),str(self.recovery),cwd=self.base)
        for p in m.ALLOWED_DELTA:self.put(p,'new')
        self.put('reliability-cockpit/src/services/factual_read_entitlements.py',(DEPLOY.parents[1]/'reliability-cockpit/src/services/factual_read_entitlements.py').read_text())
        self.commit();self.head=self.git('rev-parse','HEAD')
        self.comparator=SimpleNamespace(COMPATIBILITY_PATHS=('reliability-cockpit/src','reliability-cockpit/web/lib/api.ts','reliability-data-contracts'))
        self.patch=patch.object(m,'BASE_SHA',self.old);self.patch.start();self.addCleanup(self.patch.stop)
        self.admission={'version':1,'purpose':'NADI_HIERARCHY_LOCAL_RELEASE_01','prior_sha':self.old,
            'recovery_sha':self.old,'candidate_sha':self.head,'candidate_tree':self.git('rev-parse','HEAD^{tree}'),
            'objects':{p:[m.object_id(self.recovery,self.old,p),m.object_id(self.front,self.head,p)] for p in self.comparator.COMPATIBILITY_PATHS},
            'changed_files':{p:[m.object_id(self.recovery,self.old,p),m.object_id(self.front,self.head,p)] for p in m.ALLOWED_DELTA},
            'factual_approval_sha256':'0'*64,'subject':'local:synthetic-engineer','engineering_asset_ids':['SYNTHETIC-QA'],
            'owner_decision_ref':'synthetic-owner','review_ref':'synthetic-independent-review'}
        self.save_admission()

    def tearDown(self):self.temp.cleanup()
    def put(self,p,data):
        path=self.front/p;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(data)
    def commit(self):self.git('add','.');self.git('commit','-qm','synthetic checkpoint')
    def private(self,p,data):p.write_bytes(data);p.chmod(0o600)
    def save_admission(self):
        d=self.state/'source-admissions';d.mkdir(mode=0o700,exist_ok=True)
        data=(m.canonical(self.admission)+'\n').encode();self.private(d/'approved.json',data)
        record={'hierarchy_release':{'admission_file':str(d/'approved.json'),'admission_sha256':m.sha(data),'module_sha256':m.sha((DEPLOY/'hierarchy_source_admission.py').read_bytes())}}
        self.private(self.state/'local-development-release.json',json.dumps(record).encode())
    def check(self):return m.compatible(self.control,self.comparator,self.front,self.recovery,self.head,self.old)
    def new_head(self):
        self.head=self.git('rev-parse','HEAD');self.admission.update(candidate_sha=self.head,candidate_tree=self.git('rev-parse','HEAD^{tree}'))
        self.admission['objects']={p:[m.object_id(self.recovery,self.old,p),m.object_id(self.front,self.head,p)] for p in self.comparator.COMPATIBILITY_PATHS};self.save_admission()

    def test_exact_candidate_and_recovery_objects_pass(self):
        self.assertEqual(len(self.check()),64)

    def test_unknown_candidate_or_changed_recovery_sha_fails(self):
        for candidate,recovery in [('a'*40,self.old),(self.head,'b'*40)]:
            with self.assertRaisesRegex(RuntimeError,'REVISION_MISMATCH'):
                m.compatible(self.control,self.comparator,self.front,self.recovery,candidate,recovery)

    def test_missing_pin_corrupt_manifest_and_public_file_fail_closed(self):
        path=self.state/'source-admissions/approved.json';data=path.read_bytes()
        path.chmod(0o644)
        with self.assertRaisesRegex(RuntimeError,'PRIVATE_ADMISSION'):self.check()
        path.chmod(0o600);path.write_bytes(data+b' ')
        with self.assertRaisesRegex(RuntimeError,'APPROVAL_CHANGED'):self.check()

    def test_unknown_protected_source_delta_is_rejected_even_with_new_revision(self):
        self.put('reliability-cockpit/src/services/UNREVIEWED.py','unapproved');self.commit();self.new_head()
        with self.assertRaisesRegex(RuntimeError,'UNREVIEWED_DELTA'):self.check()

    def test_persistence_and_dependencies_cannot_use_the_admission_exception(self):
        self.put('reliability-cockpit/web/package.json','{"dependencies":{"example":"2.0"}}');self.commit();self.new_head()
        with self.assertRaisesRegex(RuntimeError,'DEPENDENCY_DIFFERENCE'):self.check()
        self.put('reliability-cockpit/src/services/local_authentication.py','changed');self.commit();self.new_head()
        with self.assertRaisesRegex(RuntimeError,'PERSISTENCE_CHANGE_DENIED'):self.check()

    def test_recorded_object_leaf_or_path_inventory_drift_is_denied(self):
        self.admission['objects']['reliability-cockpit/src'][1]='f'*40;self.save_admission()
        with self.assertRaisesRegex(RuntimeError,'OBJECT_MISMATCH'):self.check()
        self.admission['objects']['reliability-cockpit/src'][1]=m.object_id(self.front,self.head,'reliability-cockpit/src')
        self.admission['changed_files']['reliability-cockpit/src/api/reliability.py'][1]='f'*40;self.save_admission()
        with self.assertRaisesRegex(RuntimeError,'LEAF_MISMATCH'):self.check()

    def test_uncommitted_and_untracked_protected_source_is_denied(self):
        self.put('reliability-cockpit/src/api/reliability.py','dirty')
        with self.assertRaisesRegex(RuntimeError,'WORKTREE_DRIFT'):self.check()
        self.git('restore','reliability-cockpit/src/api/reliability.py')
        self.put('reliability-cockpit/src/untracked.py','unknown')
        with self.assertRaisesRegex(RuntimeError,'WORKTREE_DRIFT'):self.check()

    def policy(self):
        from src.services.factual_read_entitlements import append_event,instant,ISSUER,ZERO
        directory=self.state/'factual-read-120';directory.mkdir(mode=0o700)
        now=datetime.now(timezone.utc).replace(microsecond=0)
        event={'action':'ISSUE','scope_kind':'EXACT_ASSETS','grant_id':'synthetic-grant','subject':self.admission['subject'],
            'assets':['asset:MAXIMO:MXASSET:BSR:IP:SYNTHETIC-A'],'capabilities':sorted(m.CAPABILITIES),
            'not_before':instant(now),'expires_at':instant(now+timedelta(hours=1)),
            'actor':ISSUER,'approval_ref':'synthetic-owner','operator_ref':'synthetic-operator','at':instant(now)}
        result=append_event(directory/'grants.ndjson',event,expected_head=ZERO)
        approval={k:v for k,v in event.items() if k!='at'};approval.update(schema_version=1,expected_head=ZERO)
        data=(m.canonical(approval)+'\n').encode();self.private(directory/'activation-approval.json',data)
        self.admission['factual_approval_sha256']=m.sha(data);self.save_admission()
        return event,result,directory

    def test_exact_active_grant_is_required_and_old_runtime_ignores_policy(self):
        selected={'root':str(self.front),'sha':self.head}
        with self.assertRaises(FileNotFoundError):m.factual_environment(self.control,selected)
        event,result,directory=self.policy()
        self.assertEqual(m.factual_environment(self.control,selected),['NADI_FACTUAL_READ_POLICY_FILE='+str(directory/'grants.ndjson')])
        before=(directory/'grants.ndjson').read_bytes()
        self.assertEqual(m.factual_environment(self.control,{'sha':self.old}),[])
        self.assertEqual((directory/'grants.ndjson').read_bytes(),before)

    def test_revocation_and_changed_approval_stop_new_release(self):
        from src.services.factual_read_entitlements import append_event
        event,result,directory=self.policy()
        append_event(directory/'grants.ndjson',{**event,'action':'REVOKE'},expected_head=result['sha256'])
        with self.assertRaisesRegex(RuntimeError,'ACTIVE_EXACT_HIERARCHY_GRANT_REQUIRED'):
            m.factual_environment(self.control,{'root':str(self.front),'sha':self.head})
        file=directory/'activation-approval.json';file.write_bytes(file.read_bytes()+b' ')
        with self.assertRaisesRegex(RuntimeError,'EXACT_FACTUAL_APPROVAL_CHANGED'):
            m.factual_environment(self.control,{'root':str(self.front),'sha':self.head})

    def test_engineer_session_exact_subject_author_and_original_write_scope(self):
        proof=self.base/'session.private.json';self.private(proof,json.dumps({'cookie':'__Host-nadi_session='+'a'*43}).encode())
        session={'subject':self.admission['subject'],'roles':['AUTHOR'],'asset_ids':['SYNTHETIC-QA']}
        manager=SimpleNamespace(probe=Mock(return_value={'status':200,'data':session}))
        selected={'root':str(self.front),'sha':self.head}
        m.engineer_session(self.control,manager,selected,proof)
        with self.assertRaisesRegex(RuntimeError,'EXACT_ENGINEER_SESSION_REQUIRED'):m.engineer_session(self.control,manager,selected,None)
        for fields in [{'subject':'local:other'},{'roles':['ADMIN']},{'asset_ids':['SYNTHETIC-QA','REAL-ASSET']}]:
            manager.probe.return_value={'status':200,'data':{**session,**fields}}
            with self.assertRaisesRegex(RuntimeError,'EXACT_ENGINEER_AUTHOR_SESSION_REQUIRED'):m.engineer_session(self.control,manager,selected,proof)

    def test_unknown_controller_patch_cannot_be_applied(self):
        with self.assertRaisesRegex(RuntimeError,'AMENDMENT_ANCHOR_CHANGED'):installer.amend('class Unreviewed: pass')
        self.assertEqual(len(installer.BASELINE_FILES),5)


if __name__=='__main__':unittest.main()
