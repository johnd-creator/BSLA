import copy
import unittest
from datetime import datetime,timezone
from test_wo_actual_dates import RAW,seed
from src.repositories.database import Database
from src.config import DbConfig
from src.repositories import models,mart_models
from src.services.wo_detail_reprojection import plan_details,project_details,rollback_details
from src.services.wo_actual_date_recovery import apply_cohort,seal
from src.adapters.maximo.mappers import work_order_from_payload
from src.adapters.maximo.canonical_mappers import maintenance_event_from_payload
from src.services.local_mart_projector import _work_order_payload
from src.api.app import WORK_ORDER_SELECT

class DetailTest(unittest.TestCase):
 target="disposable-sqlite"
 def checkpoint(self,receipt): self.saved.append(receipt)
 def setUp(self):
  self.db=Database(DbConfig('sqlite+pysqlite:///:memory:'));self.db.create_all();self.saved=[];self.seed_detail()
 def seed_detail(self):
  seed(self.db)
  with self.db.session() as s:
   w=s.query(models.WorkOrderOrm).one();m=s.query(mart_models.MaintenanceEventMartOrm).one()
   for row in (w,m):
    source=copy.deepcopy(row.sources);source['maximo'].pop('wo_detail',None);row.sources=source
   w.description='Original technical work';w.priority='3';w.estimated_duration_hours=0;w.failure_code='DIRECT';s.commit()
 def tearDown(self):self.db.engine.dispose()
 def project(self):
  self.plan=plan_details(self.db,[RAW['wonum']]);return project_details(self.db,self.plan,approved_plan_sha256=seal(self.plan),expected_database=self.target,checkpoint_callback=self.checkpoint)
 def test_complete_detail_roundtrip_and_no_sensitive_values(self):
  self.assertTrue({'parent','wogroup','actstart','actfinish'}.issubset(WORK_ORDER_SELECT))
  raw=dict(RAW,description='Original WO',wopriority='3',reportedby='PRIVATE',actlabcost=10000,parent='BSR-PARENT',wogroup='RAW-GROUP')
  mapped=work_order_from_payload(raw);self.assertNotIn('PRIVATE',str(mapped.sources['maximo']['wo_detail']));self.assertNotIn('actlabcost',str(mapped.sources['maximo']['wo_detail']))
  proof=maintenance_event_from_payload(raw)['sources']['maximo']['wo_detail']
  self.assertEqual(proof['fields']['description']['value'],'Original WO');self.assertEqual(proof['fields']['wo_group']['value'],'RAW-GROUP')
 def test_projection_idempotent_and_worker_metadata_rollback(self):
  receipt=self.project();again=self.project();self.assertTrue(all(not e['fields'] for e in again['records']))
  with self.db.session() as s:
   m=s.query(mart_models.MaintenanceEventMartOrm).one();m.status='CAN';v=copy.deepcopy(m.sources);v['maximo']['unrelated']='KEEP';m.sources=v;s.commit()
  rolled=rollback_details(self.db,receipt,expected_database=self.target,checkpoint_callback=self.checkpoint)
  self.assertEqual(rolled,rollback_details(self.db,rolled,expected_database=self.target,checkpoint_callback=self.checkpoint))
  with self.db.session() as s:
   m=s.query(mart_models.MaintenanceEventMartOrm).one();self.assertEqual(m.status,'CAN');self.assertEqual(m.sources['maximo']['unrelated'],'KEEP');self.assertNotIn('wo_detail',m.sources['maximo'])
 def test_newer_version_refuses_rollback(self):
  receipt=self.project()
  with self.db.session() as s:s.query(mart_models.MaintenanceEventMartOrm).one().source_changed_at=datetime(2027,1,1,tzinfo=timezone.utc);s.commit()
  with self.assertRaises(ValueError):rollback_details(self.db,receipt,expected_database=self.target,checkpoint_callback=self.checkpoint)
 def test_actual_date_recovery_preserved_across_detail_reprojection(self):
  receipt=self.project();date_plan={**self.plan,'format':'wo-actual-dates/1'};dates=apply_cohort(self.db,date_plan,{RAW['wonum']:RAW},expected_database=self.target,approved_plan_sha256=seal(date_plan),checkpoint=self.checkpoint)
  rollback_details(self.db,receipt,expected_database=self.target,checkpoint_callback=self.checkpoint)
  with self.db.session() as s:self.assertIsNotNone(s.query(mart_models.MaintenanceEventMartOrm).one().actual_start)
 def test_legacy_null_not_promoted_to_source_null(self):
  self.project()
  with self.db.session() as s:
   proof=s.query(mart_models.MaintenanceEventMartOrm).one().sources['maximo']['wo_detail']
   self.assertEqual(proof['fields']['description']['state'],'RETAINED_LEGACY_VALUE');self.assertEqual(proof['fields']['target_completion']['state'],'SOURCE_NOT_YET_VERIFIED')
 def test_partial_acquisition_does_not_erase_legacy_description(self):
  from src.repositories.store import CollectorStore
  incoming=dict(RAW,changedate='2026-09-04T00:00:00Z')
  CollectorStore(self.db).upsert_work_order(work_order_from_payload(incoming))
  with self.db.session() as s:
   w=s.query(models.WorkOrderOrm).one();self.assertEqual(w.description,'Original technical work')
   self.assertEqual(w.sources['maximo']['wo_detail']['fields']['description']['state'],'RETAINED_LEGACY_VALUE')
 def test_source_null_and_oversized_source_are_distinct(self):
  for value,expected in ((None,'SOURCE_CONFIRMED_EMPTY'),('x'*4001,'SOURCE_VALUE_INVALID')):
   proof=work_order_from_payload(dict(RAW,description=value)).sources['maximo']['wo_detail']
   self.assertEqual(proof['fields']['description']['state'],expected)
 def test_wrong_detail_plan_cannot_be_used_for_actual_date_approval(self):
  plan=plan_details(self.db,[RAW['wonum']])
  self.assertEqual(plan['format'],'wo-details-plan/1')
  with self.assertRaises(ValueError):apply_cohort(self.db,plan,{RAW['wonum']:RAW},expected_database=self.target,approved_plan_sha256=seal(plan))
 def test_checkpoint_failure_is_atomic(self):
  p=plan_details(self.db,[RAW['wonum']])
  def fail(r):raise OSError('synthetic disk failure')
  with self.assertRaises(OSError):project_details(self.db,p,approved_plan_sha256=seal(p),expected_database=self.target,checkpoint_callback=fail)
  with self.db.session() as s:self.assertNotIn('wo_detail',s.query(mart_models.MaintenanceEventMartOrm).one().sources['maximo'])

 def test_equivalent_retained_clock_preserves_original_text(self):
  raw='2026-09-01T00:00:00+07:00'
  with self.db.session() as s:
   s.query(models.WorkOrderOrm).one().reported_at=datetime.fromisoformat(raw).astimezone(timezone.utc)
   m=s.query(mart_models.MaintenanceEventMartOrm).one();source=copy.deepcopy(m.sources);source['maximo']['reportdate']=raw;m.sources=source;s.commit()
  if self.db.engine.dialect.name=='sqlite':
   # SQLite strips ORM timestamp offsets. Supply the independently known UTC
   # fixture serialization; the identical PG case exercises the actual mapper.
   from unittest.mock import patch
   with self.db.session() as s:payload=_work_order_payload(s.query(models.WorkOrderOrm).one())
   payload['reportdate']='2026-08-31T17:00:00Z'
   with patch('src.services.wo_detail_reprojection._work_order_payload',return_value=payload):self.project()
  else:self.project()
  with self.db.session() as s:self.assertEqual(s.query(mart_models.MaintenanceEventMartOrm).one().sources['maximo']['reportdate'],raw)
 def test_detail_versions_are_field_scoped(self):
  from src.repositories.store import CollectorStore
  store=CollectorStore(self.db)
  store.upsert_work_order(work_order_from_payload(dict(RAW,description='A')))
  later=dict(RAW,changedate='2026-09-04T00:00:00Z')
  store.upsert_work_order(work_order_from_payload(later))
  store.upsert_work_order(work_order_from_payload(dict(later,description='B')))
  with self.db.session() as s:self.assertEqual(s.query(models.WorkOrderOrm).one().description,'B')
  with self.assertRaises(ValueError):store.upsert_work_order(work_order_from_payload(dict(later,description='C')))
 def test_rollback_does_not_resurrect_worker_deleted_metadata(self):
  receipt=self.project()
  with self.db.session() as s:
   m=s.query(mart_models.MaintenanceEventMartOrm).one();source=copy.deepcopy(m.sources)
   for key in list(source['maximo']):
    if key not in ('wo_detail','reportdate','schedstart','schedfinish'):source['maximo'].pop(key)
   m.sources=source;s.commit()
  rollback_details(self.db,receipt,expected_database=self.target,checkpoint_callback=self.checkpoint)
  with self.db.session() as s:self.assertNotIn('wonum',s.query(mart_models.MaintenanceEventMartOrm).one().sources.get('maximo',{}))
 def test_date_only_recovery_preserves_identical_detail_proof_and_string_boolean(self):
  from src.repositories.store import CollectorStore
  from src.services.wo_actual_date_recovery import rollback_cohort
  store=CollectorStore(self.db);store.upsert_work_order(work_order_from_payload(dict(RAW,istask='0')))
  with self.db.session() as s:
   before=copy.deepcopy(s.query(models.WorkOrderOrm).one().sources['maximo']['wo_detail'])
   self.assertFalse(before['fields']['is_task']['value']);self.assertEqual(before['fields']['is_task']['original_value'],'0')
  plan={**plan_details(self.db,[RAW['wonum']]),'format':'wo-actual-dates/1'}
  receipt=apply_cohort(self.db,plan,{RAW['wonum']:RAW},expected_database=self.target,approved_plan_sha256=seal(plan),checkpoint=self.checkpoint)
  rollback_cohort(self.db,receipt,expected_database=self.target,checkpoint=self.checkpoint)
  with self.db.session() as s:self.assertEqual(s.query(models.WorkOrderOrm).one().sources['maximo']['wo_detail'],before)
 def test_blank_source_clock_is_empty_not_invalid(self):
  proof=work_order_from_payload(dict(RAW,reportdate='',schedstart='')).sources['maximo']['wo_detail']
  for key in ('reported_at','scheduled_start'):
   self.assertEqual(proof['fields'][key]['state'],'SOURCE_CONFIRMED_EMPTY');self.assertEqual(proof['fields'][key]['value'],'')

 def test_known_null_requires_newer_field_evidence(self):
  from src.repositories.store import CollectorStore
  store=CollectorStore(self.db)
  store.upsert_work_order(work_order_from_payload(dict(RAW,description=None)))
  with self.assertRaises(ValueError):store.upsert_work_order(work_order_from_payload(dict(RAW,description='Conflicting same-version value')))
  store.upsert_work_order(work_order_from_payload(dict(RAW,changedate='2026-09-04T00:00:00Z',description='Newer observed value')))
  with self.db.session() as s:self.assertEqual(s.query(models.WorkOrderOrm).one().description,'Newer observed value')
 def test_reprojection_preserves_known_source_null_and_allows_unverified_absence(self):
  from src.adapters.maximo.wo_detail import evidence
  with self.db.session() as s:
   m=s.query(mart_models.MaintenanceEventMartOrm).one();source=copy.deepcopy(m.sources);source['maximo']['wo_detail']=evidence(dict(RAW,description=None));m.sources=source;s.commit()
  with self.assertRaises(ValueError):self.project()
  with self.db.session() as s:
   m=s.query(mart_models.MaintenanceEventMartOrm).one();source=copy.deepcopy(m.sources);source['maximo']['wo_detail']=evidence(RAW);m.sources=source;s.commit()
  self.project()
  with self.db.session() as s:self.assertEqual(s.query(mart_models.MaintenanceEventMartOrm).one().sources['maximo']['wo_detail']['fields']['description']['value'],'Original technical work')
