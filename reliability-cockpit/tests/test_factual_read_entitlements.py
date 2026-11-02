"""Synthetic directory + private disposable policy files. No operational DB/source."""
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import sqlite3
import tempfile
from types import SimpleNamespace
import unittest

from src.services.factual_read_entitlements import (
    ISSUER, ZERO, CAPABILITIES, canonical, decode, private_read, append_event, instant, PolicyCommitUncertain)
from src.qa.factual_reads import administer, load_approval, bind_directory, main

ASSET = "asset:MAXIMO:MXASSET:BSR:IP:SYNTHETIC-A"
SUBJECT = "local:synthetic-engineer"
NOW = datetime(2026, 11, 2, 10, 0, tzinfo=timezone.utc)


class Directory:
    def __init__(self):
        self.db = sqlite3.connect(":memory:")
        self.db.execute("CREATE TABLE account(subject TEXT,roles TEXT,assets TEXT)")
        self.db.executemany("INSERT INTO account VALUES(?,?,?)", [
            (ISSUER, '["ADMIN"]', '["SYNTHETIC-QA"]'),
            (SUBJECT, '["AUTHOR"]', '["SYNTHETIC-QA"]')])
        self.actor = self.current_grant(ISSUER)
        self.revoked = False

    def current_grant(self, subject):
        row = self.db.execute("SELECT roles,assets FROM account WHERE subject=?", (subject,)).fetchone()
        if not row: return None
        return SimpleNamespace(version=1, principal=SimpleNamespace(principal_id=subject,
            roles=frozenset(json.loads(row[0])), asset_ids=frozenset(json.loads(row[1]))))

    @contextmanager
    def guard(self, subject, version):
        if self.revoked: raise ValueError("REVOKED")
        yield


class FactualReadEntitlementsTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="synthetic-factual-read-")
        self.root = Path(self.temp.name); self.root.chmod(0o700)
        self.path = self.root / "grants.ndjson"
        self.provider = Directory()
        self.approval = dict(schema_version=1, expected_head=ZERO, action="ISSUE", grant_id="synthetic-grant-1",
            subject=SUBJECT, assets=[ASSET], capabilities=sorted(CAPABILITIES),
            not_before=instant(NOW), expires_at=instant(NOW+timedelta(hours=24)), actor=ISSUER,
            approval_ref="synthetic-owner-approval-1", operator_ref="synthetic-operator")
        self.lookup = lambda asset: dict(canonical_id=asset, site_code="BSR", organization_code="IP")

    def tearDown(self):
        self.provider.db.close(); self.temp.cleanup()

    def run_admin(self, approval=None, **kwargs):
        return administer(self.provider, self.provider.actor, approval or self.approval, self.path,
            now=kwargs.pop("now", NOW), lookup=kwargs.pop("lookup", self.lookup), **kwargs)

    def test_plan_never_creates_policy_or_changes_engineering_directory(self):
        before = list(self.provider.db.iterdump())
        self.assertEqual(self.run_admin()["status"], "PLAN_ONLY")
        self.assertFalse(self.path.exists())
        self.assertEqual(list(self.provider.db.iterdump()), before)

    def test_registered_scope_is_explicit_read_only_reversible_and_bounded(self):
        before = list(self.provider.db.iterdump())
        approval = {**self.approval, "assets":[], "scope_kind":"REGISTERED_BSR_IP"}
        calls = []
        def lookup(value):
            calls.append(value)
            return {"source":"MAXIMO_LIST_OF_ASSETS", "registered_asset_count":137}
        result = self.run_admin(approval, lookup=lookup, apply=True)
        self.assertEqual(calls, [None])  # No per-asset fan-out / account scope mutation.
        self.assertEqual(decode(private_read(self.path))[0]["scope_kind"], "REGISTERED_BSR_IP")
        revoke = {**approval, "action":"REVOKE", "expected_head":result["head_sha256"]}
        for fields in [{"scope_kind":"EXACT_ASSETS", "assets":[ASSET]}, {"scope_kind":None}]:
            with self.assertRaises(ValueError):self.run_admin({**revoke, **fields}, apply=True)
        self.run_admin(revoke, now=NOW+timedelta(minutes=1), apply=True)
        self.assertEqual(decode(private_read(self.path))[-1]["action"], "REVOKE")
        self.assertEqual(list(self.provider.db.iterdump()), before)

    def test_registered_scope_rejects_wildcards_foreign_scope_and_unverified_registry(self):
        for fields in [{"scope_kind":"REGISTERED_BSR_IP", "assets":[ASSET]},
                       {"scope_kind":"ALL", "assets":[]}, {"scope_kind":None},
                       {"scope_kind":"REGISTERED_BSR_IP", "assets":["*"]}]:
            with self.assertRaises((ValueError, TypeError)):self.run_admin({**self.approval, **fields}, apply=True)
        for metadata in [{"source":"OTHER", "registered_asset_count":137},
                         {"source":"MAXIMO_LIST_OF_ASSETS", "registered_asset_count":True},
                         {"source":"MAXIMO_LIST_OF_ASSETS", "registered_asset_count":0}]:
            with self.assertRaises(ValueError):self.run_admin({**self.approval,"assets":[],"scope_kind":"REGISTERED_BSR_IP"},lookup=lambda _:metadata,apply=True)
        self.assertFalse(self.path.exists())

    def test_issue_revoke_audit_and_engineering_write_scope_unchanged(self):
        before = list(self.provider.db.iterdump())
        receipt = self.run_admin(apply=True)
        self.assertEqual(receipt["version"], 1)
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)
        approval = {**self.approval, "expected_head":receipt["head_sha256"], "action":"REVOKE",
                    "approval_ref":"synthetic-owner-revoke"}
        self.run_admin(approval, now=NOW+timedelta(minutes=1), apply=True)
        events = decode(private_read(self.path))
        self.assertEqual([x["action"] for x in events], ["ISSUE", "REVOKE"])
        self.assertEqual([x["version"] for x in events], [1, 2])
        self.assertEqual(list(self.provider.db.iterdump()), before)
        self.assertNotIn(ASSET, self.provider.current_grant(SUBJECT).principal.asset_ids)
        self.assertEqual(self.provider.current_grant(SUBJECT).principal.roles, {"AUTHOR"})

    def test_stale_cas_retry_and_changed_approval_cannot_extend_or_reissue(self):
        self.run_admin(apply=True); before = self.path.read_bytes()
        with self.assertRaises(ValueError): self.run_admin(apply=True)
        self.assertEqual(self.path.read_bytes(), before)
        with self.assertRaises(ValueError):
            self.run_admin({**self.approval, "expires_at":instant(NOW+timedelta(days=2))}, apply=True)
        self.assertEqual(self.path.read_bytes(), before)

    def test_approval_digest_and_canonical_bytes_bind_exact_subject_scope_expiry(self):
        file = self.root / "approval.json"
        file.write_text(canonical(self.approval)+"\n"); file.chmod(0o600)
        digest = sha256(file.read_bytes()).hexdigest()
        self.assertEqual(load_approval(file, digest), self.approval)
        with self.assertRaises(ValueError): load_approval(file, ZERO)
        file.write_text('{"schema_version":0,'+canonical(self.approval)[1:]+"\n")
        with self.assertRaises(ValueError): load_approval(file, sha256(file.read_bytes()).hexdigest())

    def test_admin_authentication_does_not_authorize_other_issuers_or_self_grants(self):
        for update in [dict(actor="local:other-admin"), dict(subject=ISSUER)]:
            with self.subTest(update=update), self.assertRaises(ValueError): self.run_admin({**self.approval, **update}, apply=True)
        self.provider.actor = self.provider.current_grant(SUBJECT)
        with self.assertRaises(ValueError): self.run_admin(apply=True)
        self.assertFalse(self.path.exists())

    def test_revoked_issuer_unknown_or_non_author_beneficiary_denied(self):
        self.provider.revoked = True
        with self.assertRaises(ValueError): self.run_admin(apply=True)
        self.provider.revoked = False
        for subject in ["local:unknown", ISSUER]:
            with self.assertRaises(ValueError): self.run_admin({**self.approval, "subject":subject}, apply=True)
        self.assertFalse(self.path.exists())

    def test_expired_future_and_nonregistered_foreign_scope_denied(self):
        for now in [NOW-timedelta(seconds=1), NOW+timedelta(days=1)]:
            with self.assertRaises(ValueError): self.run_admin(now=now, apply=True)
        for field,value in [("assets", ["*"]), ("assets", [ASSET.replace(":BSR:", ":OTHER:")]),
                            ("capabilities", ["ADMIN"]), ("capabilities", ["ENGINEERING_WRITE"])]:
            with self.assertRaises(ValueError): self.run_admin({**self.approval, field:value}, apply=True)
        for bad in [dict(canonical_id=ASSET,site_code="OTHER",organization_code="IP"),
                    dict(canonical_id=ASSET+"-FOREIGN",site_code="BSR",organization_code="IP")]:
            with self.assertRaises(ValueError): self.run_admin(lookup=lambda _:bad, apply=True)
        self.assertFalse(self.path.exists())

    def test_duplicate_keys_tamper_chain_truncation_and_schema_fail_closed(self):
        self.run_admin(apply=True); data = self.path.read_bytes()
        for bad in [data[:-1], data.replace(b'\n',b'\r\n'), data.replace(b'"version":1', b'"version":2'),
                    data.replace(b'"action":"ISSUE"', b'"action":"REVOKE","action":"ISSUE"'),
                    data.replace(b'"schema_version":1', b'"schema_version":2')]:
            with self.subTest(bad=bad[:60]), self.assertRaises((ValueError,UnicodeError)): decode(bad)
        # A valid older prefix is detectable only against independent custody/watermarks.
        # Do not claim the hash chain alone supplies anti-rollback protection.

    def test_private_permissions_symlinks_hardlinks_and_nonregular_files_denied(self):
        self.run_admin(apply=True)
        self.path.chmod(0o644)
        with self.assertRaises(ValueError): private_read(self.path)
        self.path.chmod(0o600)
        link = self.root / "hardlink"; os.link(self.path, link)
        with self.assertRaises(ValueError): private_read(self.path)
        link.unlink(); link.symlink_to(self.path)
        with self.assertRaises((ValueError,OSError)): private_read(link)
        self.root.chmod(0o755)
        with self.assertRaises(ValueError): private_read(self.path)
        self.root.chmod(0o700)

    def test_grant_cli_binds_actual_local_authority_not_a_copied_directory(self):
        good="postgresql+psycopg://nadi_local_dev_01:synthetic@127.0.0.1:15443/nadi_local_dev_01_test"
        bind_directory(good,"nadi_local_dev_01_test")
        for bad in [good.replace('15443','15444'),good.replace('127.0.0.1','192.0.2.1'),
                    good.replace('/nadi_local_dev_01_test','/restored_copy_test'),good+'?host=192.0.2.1',
                    good.replace('://nadi_local_dev_01:', '://postgres:')]:
            with self.assertRaises(ValueError):bind_directory(bad,"nadi_local_dev_01_test")

    def test_cli_plan_does_not_authenticate_connect_or_mutate_directory(self):
        from unittest.mock import patch
        import contextlib,io
        approval={**self.approval,"not_before":instant(datetime.now(timezone.utc)-timedelta(seconds=10)),
                  "expires_at":instant(datetime.now(timezone.utc)+timedelta(hours=1))}
        file=self.root/'approval.json';file.write_text(canonical(approval)+'\n');file.chmod(0o600)
        args=['--approval-file',str(file),'--approval-sha256',sha256(file.read_bytes()).hexdigest(),
              '--ledger',str(self.path),'--expected-database','nadi_local_dev_01_test','--admin-username','synthetic-admin',
              '--operator-ref','synthetic-operator','--acknowledge-private-administration']
        with patch('sqlalchemy.create_engine') as engine,patch('src.qa.users.secret') as secret,contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(args),0);engine.assert_not_called();secret.assert_not_called()
        self.assertFalse(self.path.exists())

    def test_failure_after_atomic_replace_reports_uncertain_live_grant(self):
        from unittest.mock import patch
        import stat
        real_fsync=os.fsync
        def fail_directory(fd):
            if stat.S_ISDIR(os.fstat(fd).st_mode):raise OSError('synthetic fsync failure')
            return real_fsync(fd)
        with patch('src.services.factual_read_entitlements.os.fsync',side_effect=fail_directory):
            with self.assertRaises(PolicyCommitUncertain) as error:self.run_admin(apply=True)
        events=decode(private_read(self.path))
        self.assertEqual(events[-1]['action'],'ISSUE')
        self.assertEqual(error.exception.event['sha256'],events[-1]['sha256'])
        with self.assertRaises(ValueError):self.run_admin(apply=True)


if __name__ == "__main__": unittest.main()
