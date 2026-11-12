"""B2 pure policy and disabled-capability tests; no DB or source access."""
import unittest
from datetime import datetime, timezone
from src.repositories.database import Base
from src.repositories.deferred_store import (DeferredProjectionStore, LedgerLimits,
    CaptureError, family_identity, classify, describe)

class DeferredPolicyTest(unittest.TestCase):
    def test_disabled_before_connection(self):
        with self.assertRaisesRegex(CaptureError,'disabled'): DeferredProjectionStore(None)

    def test_metadata_not_operational(self):
        self.assertFalse(any(t.startswith('mart_deferred_') for t in Base.metadata.tables))

    def test_family_identity_does_not_depend_on_source_time_or_fingerprint(self):
        self.assertEqual(family_identity('asset_master','A'),family_identity('asset_master','A'))
        self.assertNotEqual(family_identity('asset_master','A'),family_identity('maintenance_event','A'))
        with self.assertRaises(CaptureError): family_identity('unknown','A')

    def test_scope_unknown_not_exclusion(self):
        self.assertEqual(classify('asset_master','A',{'siteid':None,'orgid':None})[1:],
                         ('DEFERRED','UNPROVEN_SCOPE'))

    def test_missing_required_id_recoverable(self):
        self.assertEqual(classify('asset_master','A',{'siteid':'BSR','orgid':'IP','assetnum':''})[1:],
                         ('DEFERRED','MISSING_REQUIRED_ID'))

    def test_invalid_timestamp_blocked_mapping(self):
        self.assertEqual(classify('asset_master','A',{'siteid':'BSR','orgid':'IP','assetnum':'A',
                            'changedate':'invalid'})[1:],('FAILED','INVALID_MAPPING'))

    def test_missing_equipment_classification_and_scoped_key(self):
        meta,dependencies=describe('maintenance_event','BSR-1',{'equipment_id':' a '},
                                  'DEFERRED','MISSING_LOCAL_EQUIPMENT')
        self.assertEqual(meta['classification'],'DEFERRED_DEPENDENCY')
        self.assertEqual(dependencies,[('LOCAL_EQUIPMENT','asset:MAXIMO:MXASSET:BSR:IP:A')])

    def test_unknown_scope_metadata_does_not_invent_site(self):
        meta,_=describe('asset_master','A',{'siteid':'OTHER','orgid':None},'DEFERRED','UNPROVEN_SCOPE')
        self.assertIsNone(meta['site']); self.assertIsNone(meta['organization']); self.assertIsNone(meta['canonical_id'])

    def test_unknown_reason_rejected_without_copying_exception(self):
        with self.assertRaises(CaptureError): describe('asset_master','A',{},'DEFERRED','arbitrary private exception')

    def test_resource_bounds_and_aware_policy_expiry(self):
        for kwargs in ({'obligations_per_transaction':2},{'transition_batch':0},{'max_attempts':21},
                       {'max_transitions':3},{'max_dependencies':9},{'max_versions':0},
                       {'coverage_proofs':10001},{'policy_expires_at':datetime(2020,1,1)}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError): LedgerLimits(**kwargs)

    def test_fractional_or_boolean_limits_are_not_accepted(self):
        for kwargs in ({'max_attempts':1.5},{'transition_batch':True},{'coverage_proofs':False}):
            with self.subTest(kwargs=kwargs),self.assertRaises(ValueError): LedgerLimits(**kwargs)
