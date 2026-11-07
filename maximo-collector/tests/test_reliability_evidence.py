"""Hermetic reliability evidence regressions; synthetic rows, no source requests."""
from copy import deepcopy
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import unittest

from jsonschema import Draft202012Validator, FormatChecker
from src.adapters.maximo.canonical_mappers import maintenance_event_from_payload
from src.adapters.maximo.mappers import work_order_from_payload
from src.adapters.maximo.reliability_fields import DETAIL_FIELDS, evidence, observation
from src.api.app import WORK_ORDER_SELECT, sync_config_for
from src.config import DbConfig
from src.repositories.database import Database
from src.repositories.models import EquipmentOrm, WorkOrderOrm
from src.repositories.mart_models import MaintenanceEventMartOrm
from src.repositories.store import CollectorStore
from src.services.local_mart_projector import CollectorMartProjector, _work_order_payload
from src.services.canonical import CANONICAL_CONFIGS
from src.services.workorder_policy import acquire_work_order, SUMMARY_FIELDS


def row(**changes):
    return dict(wonum='BSR-SYNTHETIC', assetnum='SYNTHETIC-A', siteid='BSR', orgid='IP',
                status='APPR', reportdate='2026-10-01T00:00:00+07:00',
                changedate='2026-11-01T00:00:00Z', statusdate='2026-11-01T00:00:00Z',
                failurecode='CLASS-A', problemcode='PROBLEM-A', faildate='2026-10-01T03:00:00+07:00',
                parent='BSR-PARENT', origrecordclass='SR', origrecordid='ORIGIN-1',
                woclass='WORKORDER', istask=False, haschildren=True,
                hasfollowupwork=False, downtime=True, **changes)


class EvidenceTest(unittest.TestCase):
    def test_expanded_detail_only_uses_verified_fields(self):
        self.assertTrue(set(DETAIL_FIELDS).issubset(WORK_ORDER_SELECT))
        self.assertTrue(set(DETAIL_FIELDS).issubset(CANONICAL_CONFIGS['mxwodetail'].select))
        self.assertIn('failurecode', CANONICAL_CONFIGS['mxwodetail'].select)
        self.assertFalse(set(DETAIL_FIELDS) & set(SUMMARY_FIELDS))
        self.assertNotIn('plncausecode', WORK_ORDER_SELECT)
        self.assertNotIn('failureinformation', WORK_ORDER_SELECT)
        config = sync_config_for('mxwodetail')
        self.assertTrue(config.work_order_lifecycle)
        self.assertTrue(config.recent_work_orders)
        self.assertTrue(config.cursor_requires_zero_errors)
        self.assertEqual(config.page_size, 25)

    def test_source_fields_never_create_failure_or_restoration_semantics(self):
        result = maintenance_event_from_payload(row())
        self.assertEqual(result['failure_code'], 'CLASS-A')
        self.assertEqual(result['sources']['maximo']['failurecode'], 'CLASS-A')
        proof = result['sources']['maximo']['reliability_evidence']
        self.assertEqual(proof['semantics'], 'SOURCE_FIELDS_ONLY')
        self.assertEqual(proof['fields']['origrecordclass']['value'], 'SR')
        self.assertEqual(proof['fields']['faildate']['state'], 'VALID')
        self.assertFalse({'failure_at','restored_at','failure_id','mtbf','mttr'} & set(result))
        self.assertIsNone(result['downtime_hours'])
        self.assertIs(result['sources']['maximo']['downtime'], True)
        self.assertIsNone(work_order_from_payload(row()).downtime_hours)
        self.assertIsNone(work_order_from_payload(row()).parent_wo)

    def test_numeric_downtime_is_not_hours_either(self):
        for value in (False, True, 0, 1, 12.5, '12.5', 'true'):
            payload = row(); payload['downtime'] = value
            self.assertIsNone(work_order_from_payload(payload).downtime_hours)
            self.assertIsNone(maintenance_event_from_payload(payload)['downtime_hours'])

    def test_missing_null_invalid_and_naive_are_distinct(self):
        self.assertEqual(observation('problemcode', None, present=False)['state'], 'UNAVAILABLE')
        self.assertEqual(observation('problemcode', None)['state'], 'MISSING')
        self.assertEqual(observation('problemcode', {'private':'value'})['state'], 'INVALID')
        self.assertEqual(observation('hasfollowupwork', 'unexpected')['state'], 'INVALID')
        self.assertEqual(observation('faildate', '2026-11-01T01:00:00')['state'], 'NAIVE')
        self.assertIsNone(observation('faildate', '2026-11-01T01:00:00')['value'])
        self.assertIsNone(observation('faildate', float('inf'))['original'])

    def test_unapproved_payload_does_not_cross_evidence_boundary(self):
        payload = row(); payload.update(href='private', reportedby='private', failureinformation='private', plncausecode='private')
        proof = evidence(payload)
        self.assertNotIn('private', repr(proof))
        self.assertNotIn('plncausecode', proof['fields'])

    def test_new_evidence_validates_both_contracts(self):
        root = Path(__file__).parents[2] / 'reliability-data-contracts/schemas'
        for name,record in [('work-order',asdict(work_order_from_payload(row()))),('maintenance-event',maintenance_event_from_payload(row()))]:
            # Domain datetime fields are serialized by the API/store boundary.
            serialized=json.loads(json.dumps(record,default=lambda value:value.isoformat()))
            schema=json.loads((root/(name+'.schema.json')).read_text())
            Draft202012Validator(schema,format_checker=FormatChecker()).validate(serialized)


class PersistenceTest(unittest.TestCase):
    def setUp(self):
        self.db=Database(DbConfig('sqlite+pysqlite:///:memory:'));self.db.create_all()
        self.store=CollectorStore(self.db)
        with self.db.session() as session:
            session.add(EquipmentOrm(id='SYNTHETIC-A', sources={'maximo':{'siteid':'BSR','orgid':'IP'}}));session.commit()
    def tearDown(self):
        self.db.engine.dispose()
    def stored(self):
        with self.db.session() as session:return session.get(WorkOrderOrm,'BSR-SYNTHETIC')
    def ingest(self,payload):
        return self.store.upsert_work_order(work_order_from_payload(payload))
    def test_sparse_update_retains_per_field_observation_version(self):
        self.ingest(row()); old=self.stored().sources['maximo']['reliability_evidence']
        sparse={key:value for key,value in row().items() if key in SUMMARY_FIELDS}
        sparse['changedate']='2026-11-02T00:00:00Z';self.ingest(sparse)
        proof=self.stored().sources['maximo']['reliability_evidence']
        self.assertEqual(proof['fields']['problemcode'],old['fields']['problemcode'])
        self.assertEqual(proof['fields']['problemcode']['source_changed_at'],'2026-11-01T00:00:00+00:00')
        self.assertEqual(self.stored().failure_code,'CLASS-A')
        explicit=dict(sparse,changedate='2026-11-03T00:00:00Z',problemcode=None,faildate=None)
        self.ingest(explicit);proof=self.stored().sources['maximo']['reliability_evidence']
        self.assertEqual(proof['fields']['problemcode']['state'],'MISSING')
        self.assertIsNone(proof['fields']['faildate']['value'])
    def test_identity_change_cannot_reuse_retained_clues(self):
        self.ingest(row()); payload={key:value for key,value in row().items() if key in SUMMARY_FIELDS}
        payload.update(assetnum='SYNTHETIC-B',changedate='2026-11-02T00:00:00Z');self.ingest(payload)
        self.assertEqual(self.stored().sources['maximo']['reliability_evidence']['fields']['faildate']['state'],'UNAVAILABLE')
    def test_full_local_projection_repairs_failure_code_idempotently(self):
        self.ingest(row());self.store.set_cursor('mxwodetail',datetime(2026,11,1,tzinfo=timezone.utc),1)
        before=self.store.get_cursor('mxwodetail')
        projector=CollectorMartProjector(self.db,self.db,batch_size=1)
        self.assertEqual(projector.project('maintenance_event').rows_inserted,1)
        self.assertEqual(projector.project('maintenance_event').rows_unchanged,1)
        with self.db.session() as session:
            value=session.query(MaintenanceEventMartOrm).one()
            self.assertEqual(value.failure_code,'CLASS-A')
            self.assertEqual(value.sources['maximo']['reliability_evidence']['fields']['problemcode']['value'],'PROBLEM-A')
            self.assertIsNone(value.downtime_hours)
        self.assertEqual(self.store.get_cursor('mxwodetail'),before)
    def test_legacy_numeric_downtime_never_replays_as_hours(self):
        self.ingest(row())
        with self.db.session() as session:
            value=session.get(WorkOrderOrm,'BSR-SYNTHETIC');value.sources={'maximo':{'siteid':'BSR','orgid':'IP'}};value.downtime_hours=1.0;session.commit()
        record=maintenance_event_from_payload(_work_order_payload(self.stored()))
        self.assertEqual(record['failure_code'],'CLASS-A')
        self.assertIsNone(record['downtime_hours'])
        self.assertIsNone(record['sources']['maximo']['downtime'])
    def test_projection_revalidates_identity_version_and_allowlist(self):
        self.ingest(row()); payload=_work_order_payload(self.stored())
        for mutation in ('identity','future','extra'):
            candidate=deepcopy(payload);proof=candidate['collector_reliability_evidence']
            if mutation=='identity':proof['identity']['siteid']='OTHER'
            elif mutation=='future':proof['fields']['problemcode']['source_changed_at']='2099-01-01T00:00:00Z'
            else:proof['fields']['person_secret']={'value':'PRIVATE'}
            result=maintenance_event_from_payload(candidate)['sources']['maximo']['reliability_evidence']
            if mutation!='extra':self.assertEqual(result['fields']['problemcode']['state'],'UNAVAILABLE')
            self.assertNotIn('PRIVATE',repr(result))
    def test_terminal_freeze_and_summary_cancellation_do_not_expand_collection(self):
        payload=row();payload['status']='CLOSE';self.ingest(payload)
        class Never:
            def iterate(self,*args,**kwargs):raise AssertionError('terminal source request')
        summary={key:value for key,value in payload.items() if key in SUMMARY_FIELDS}
        result=acquire_work_order(Never(),self.store,sync_config_for('mxwodetail'),summary)
        self.assertEqual(result,('unchanged','TERMINAL_FROZEN'))
        old=self.stored().sources['maximo']['reliability_evidence']
        summary.update(status='CAN',changedate='2026-11-02T00:00:00Z',problemcode='UNSOLICITED')
        acquire_work_order(Never(),self.store,sync_config_for('mxwodetail'),summary)
        self.assertEqual(self.stored().sources['maximo']['reliability_evidence'],old)
    def test_legacy_summary_poll_does_not_create_empty_reliability_evidence(self):
        payload=row()
        class Detail:
            def iterate(self,*args,**kwargs):yield payload
        summary={key:value for key,value in payload.items() if key in SUMMARY_FIELDS}
        config=sync_config_for('mxwodetail')
        acquire_work_order(Detail(),self.store,config,summary)
        acquire_work_order(Detail(),self.store,config,summary)
        with self.db.session() as session:
            stored=session.get(WorkOrderOrm,'BSR-SYNTHETIC')
            sources=deepcopy(stored.sources);sources['maximo'].pop('reliability_evidence',None)
            stored.sources=sources;session.commit()
        before=deepcopy(self.stored().sources)
        outcome=acquire_work_order(Detail(),self.store,config,summary)
        self.assertEqual(outcome,('unchanged','UNCHANGED_SUMMARY'))
        self.assertEqual(self.stored().sources,before)

    def test_nonclosed_actual_clocks_remain_ineligible(self):
        payload=row();payload.update(actstart='2026-10-01T00:00:00Z',actfinish='2026-10-01T01:00:00Z')
        result=maintenance_event_from_payload(payload)
        self.assertIsNone(result['duration_hours']);self.assertIsNone(result['actual_finish'])
