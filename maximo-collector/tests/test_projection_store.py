"""Source-free B1 guard/format and caller-owned transaction regressions."""
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch
from sqlalchemy import select
from src.config import DbConfig
from src.repositories.database import Database, Base
from src.repositories.mart_models import AssetMasterMartOrm
from src.repositories.projection_store import (Budget, CaptureError, ProjectionStore,
    captured_payload, fingerprint, map_input)
from src.services.canonical import CanonicalCollection
from src.services.mart import MartWriter, ScopeViolation
from src.adapters.maximo.canonical_mappers import asset_master_from_payload


def asset():
    return asset_master_from_payload({"assetnum":"SYNTHETIC", "siteid":"BSR", "orgid":"IP"})


class ProjectionFoundationTest(unittest.TestCase):
    def test_disabled_before_any_database_access(self):
        with self.assertRaisesRegex(CaptureError, 'disabled'):
            ProjectionStore(None)

    def test_exclusive_writer_required(self):
        with self.assertRaisesRegex(CaptureError, 'exclusive'):
            ProjectionStore(None, enabled=True)

    def test_sqlite_cannot_claim_postgresql_proof(self):
        db = Database(DbConfig('sqlite+pysqlite:///:memory:'))
        with self.assertRaisesRegex(CaptureError, 'PostgreSQL'):
            ProjectionStore(db, enabled=True, exclusive_writer=True)

    def test_candidate_tables_not_registered_in_operational_base(self):
        self.assertFalse(any(t.startswith('mart_capture_') for t in Base.metadata.tables))

    def test_fingerprint_stable_and_domain_sensitive(self):
        self.assertEqual(fingerprint('asset_master','A',{'a':1,'b':None}),
                         fingerprint('asset_master','A',{'b':None,'a':1}))
        self.assertNotEqual(fingerprint('asset_master','A',{}), fingerprint('maintenance_event','A',{}))
        self.assertNotEqual(fingerprint('asset_master','A',{'x':1}), fingerprint('asset_master','A',{'x':2}))

    def test_null_timestamp_not_replaced(self):
        self.assertEqual(captured_payload('asset_master', {'source_id':'A','changedate':None}),
                         {'changedate':None})

    def test_nonfinite_input_refused(self):
        with self.assertRaises(ValueError):
            fingerprint('asset_master','A',{'bad':float('nan')})

    def test_budgets_are_finite(self):
        for kwargs in ({'rows':0}, {'page':501}, {'seconds':61}, {'bytes':-1}, {'lease_seconds':301}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                Budget(**kwargs)

    def test_unknown_scope_not_exclusion(self):
        record, state, reason = map_input('asset_master','A', {'siteid':None,'orgid':None})
        self.assertEqual((record,state,reason),(None,'DEFERRED','UNPROVEN_SCOPE'))

    def test_missing_local_dependency_not_projected(self):
        self.assertEqual(map_input('maintenance_event','BSR-1',
            {'equipment_id':'MISSING','local_equipment_present':False})[1:],
            ('DEFERRED','MISSING_LOCAL_EQUIPMENT'))

    def test_expected_prefix_exclusion_is_explicit(self):
        self.assertEqual(map_input('maintenance_event','OTHER-1',{})[1:],
                         ('EXPECTED_EXCLUSION','APPROVED_WO_PREFIX'))

    def test_caller_path_no_hidden_commit_and_rollback(self):
        db = Database(DbConfig('sqlite+pysqlite:///:memory:'))
        db.create_all()
        writer = MartWriter(db)
        collection = CanonicalCollection('asset_master',[asset()])
        with db.session() as s:
            with patch.object(s,'commit', side_effect=AssertionError('hidden commit')):
                writer.persist_in_session(collection, s)
                self.assertIsNotNone(s.get(AssetMasterMartOrm,asset()['canonical_id']))
                s.rollback()
        with db.session() as s:
            self.assertIsNone(s.get(AssetMasterMartOrm,asset()['canonical_id']))

    def test_caller_validation_all_before_write(self):
        db = Database(DbConfig('sqlite+pysqlite:///:memory:')); db.create_all()
        invalid = asset(); invalid['site_code'] = 'OTHER'
        with db.session() as s:
            with self.assertRaises(ScopeViolation):
                MartWriter(db).persist_in_session(CanonicalCollection('asset_master',[asset(),invalid]),s)
            self.assertEqual(s.scalars(select(AssetMasterMartOrm)).all(),[])

    def test_legacy_dry_run_and_empty_collection_never_open_session(self):
        writer=MartWriter(None)
        self.assertEqual(writer.persist_collection(CanonicalCollection('asset_master',[asset()]),
                         dry_run=True).records_received,1)
        self.assertEqual(writer.persist_collection(CanonicalCollection('asset_master',[])).records_received,0)

    def test_legacy_scope_validation_precedes_database_session(self):
        invalid=asset(); invalid['site_code']='OTHER'
        with self.assertRaises(ScopeViolation):
            MartWriter(None).persist_collection(CanonicalCollection('asset_master',[invalid]))
