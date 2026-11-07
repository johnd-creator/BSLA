from contextlib import contextmanager
from dataclasses import replace
from datetime import datetime, timezone
import unittest
from src.adapters.maximo.mappers import work_order_from_payload
from src.adapters.maximo.actual_dates import retained_values
from src.adapters.maximo.canonical_mappers import maintenance_event_from_payload
from src.config import DbConfig
from src.repositories.database import Database
from src.repositories.models import WorkOrderOrm
from src.repositories.store import CollectorStore
from src.services.workorder_policy import acquire_work_order, SUMMARY_FIELDS
from src.services.sync import ObjectSyncConfig, SyncService
from src.adapters.maximo.oslc_client import OslcError, OslcPaginationLimitError

T=datetime(2026,10,13,tzinfo=timezone.utc)
def row(status='APPR', day=20, **kw):
 return dict(wonum='BSR-TEST',siteid='BSR',orgid='IP',assetnum='A1',status=status,
             reportdate=kw.pop('reportdate','2025-01-01T00:00:00+07:00'),changedate=f'2026-10-{day:02}T12:00:00Z',statusdate=kw.pop('statusdate',f'2026-10-{day:02}T12:00:00Z'),description='Retained detail',istask=False,**kw)
CFG=ObjectSyncConfig('mxwodetail','work_order',work_order_from_payload,prefix_field='wonum',allowed_prefixes=('BSR',),
  recent_work_orders=True,work_order_lifecycle=True,cursor_requires_zero_errors=True,max_pages=1,
  request_limit=40,page_size=25,select=tuple(SUMMARY_FIELDS)+('description','istask','actstart','actfinish'))

class Detail:
 def __init__(self,payload=None): self.payload=payload;self.calls=[]
 def iterate(self,*a,**kw): self.calls.append(kw);yield self.payload

class LifecycleTest(unittest.TestCase):
 def setUp(self):
  self.db=Database(DbConfig('sqlite+pysqlite:///:memory:'));self.db.create_all();self.store=CollectorStore(self.db)
 def tearDown(self):self.db.engine.dispose()
 def stored(self):
  with self.db.session() as s:return s.get(WorkOrderOrm,'BSR-TEST')
 def ingest(self,payload):return self.store.upsert_work_order(work_order_from_payload(payload))
 def acquire(self,payload,detail=None):
  c=Detail(detail or payload);summary={k:v for k,v in payload.items() if k in SUMMARY_FIELDS}
  outcome=acquire_work_order(c,self.store,CFG,summary);return outcome,c
 def test_active_refresh_only_when_version_changes_without_actual_requests(self):
  p=row(actstart='2026-10-20T01:00:00Z',actfinish='2026-10-20T02:00:00Z')
  _,c=self.acquire(p);self.assertNotIn('actstart',c.calls[0]['select'])
  self.assertEqual(self.stored().sources['maximo']['actual_dates']['fields']['actstart']['state'],'UNAVAILABLE')
  _,c=self.acquire(p);self.assertFalse(c.calls)
  p=row(day=21);p['description']='Updated active';self.acquire(p)
  self.assertEqual(self.stored().description,'Updated active')
 def test_first_close_reads_actual_once_repeated_terminal_has_zero_detail_reads_and_writes(self):
  self.ingest(row());p=row('CLOSE',21,actstart='2026-10-20T01:00:00Z',actfinish='2026-10-20T02:00:00Z')
  _,c=self.acquire(p);self.assertIn('actstart',c.calls[0]['select']);proof=self.stored().sources
  p=row('CLOSE',22);p['description']='Must not overwrite';out,c=self.acquire(p)
  self.assertEqual(out,('unchanged','TERMINAL_FROZEN'));self.assertFalse(c.calls)
  self.assertEqual(self.stored().description,'Retained detail');self.assertEqual(self.stored().sources,proof)
 def test_close_to_cancel_updates_status_without_detail_or_clock_replay(self):
  self.acquire(row('CLOSE',20,actstart='2026-10-20T01:00:00Z',actfinish='2026-10-20T02:00:00Z'))
  _,c=self.acquire(row('CAN',21));self.assertFalse(c.calls);r=self.stored();self.assertEqual(r.status,'CAN')
  self.assertEqual(retained_values(r.sources['maximo']['actual_dates'],r.id,r.equipment_id,r.source_changed_at),{})
 def test_new_close_gets_one_initial_detail(self):
  _,c=self.acquire(row('CLOSE'));self.assertEqual(len(c.calls),1);self.assertIn('actfinish',c.calls[0]['select'])
 def test_cancel_preserves_status_without_reading_detail(self):
  for status in ('CAN','CANCEL'):
   with self.subTest(status=status):
    p=row(status);_,c=self.acquire(p);self.assertFalse(c.calls);self.assertEqual(self.stored().status,status)
    # Delete only hermetic row to test the alternative source vocabulary.
    with self.db.session() as s:s.delete(s.get(WorkOrderOrm,'BSR-TEST'));s.commit()
 def test_active_cancel_does_not_replace_details(self):
  self.ingest(row());p=row('CAN',21);p['description']='Ignored'
  _,c=self.acquire(p);self.assertFalse(c.calls);self.assertEqual(self.stored().description,'Retained detail')
 def test_legacy_nonclose_actual_evidence_is_archived_not_destroyed_or_reused(self):
  from src.adapters.maximo.actual_dates import evidence
  old=evidence(row('CLOSE',20,actstart='2026-10-20T01:00:00Z',actfinish='2026-10-20T02:00:00Z'))
  self.ingest(row('APPR'))
  with self.db.session() as s:
   r=s.get(WorkOrderOrm,'BSR-TEST');r.sources={'maximo':{'actual_dates':old}};s.commit()
  self.acquire(row('CLOSE',21));m=self.stored().sources['maximo']
  self.assertEqual(m['actual_dates_history'][0]['evidence'],old)
  self.assertEqual(m['actual_dates']['fields']['actstart']['state'],'UNAVAILABLE')
 def test_reopen_reclose_never_replays_previous_actuals(self):
  self.acquire(row('CLOSE',20,actstart='2026-10-20T01:00:00Z',actfinish='2026-10-20T02:00:00Z'))
  self.acquire(row('APPR',21));self.assertEqual(len(self.stored().sources['maximo']['actual_dates_history']),1)
  self.acquire(row('CLOSE',22));r=self.stored();p=r.sources['maximo']['actual_dates']
  self.assertEqual(retained_values(p,r.id,r.equipment_id,r.source_changed_at),{})
 def test_reclose_valid_clocks_are_current_not_prior_cycle(self):
  self.acquire(row('CLOSE',20,actstart='2026-10-20T01:00:00Z',actfinish='2026-10-20T02:00:00Z'))
  self.acquire(row('APPR',21));self.acquire(row('CLOSE',22,actstart='2026-10-22T01:00:00Z',actfinish='2026-10-22T04:00:00Z'))
  self.assertIn('2026-10-22',self.stored().sources['maximo']['actual_dates']['fields']['actstart']['original'])
 def test_detail_race_and_wrong_identity_fail_without_write(self):
  for changed in ({'siteid':'OTHER'},{'orgid':'OTHER'},{'assetnum':'OTHER'},{'wonum':'OTHER'},{'status':'CLOSE'},{'changedate':'2026-10-21T12:00:00Z'}):
   p=row()
   with self.assertRaises(OslcError):self.acquire(p,{**p,**changed})
   self.assertIsNone(self.stored())
 def test_same_version_status_change_needs_matching_direct_confirmation(self):
  self.ingest(row());_,c=self.acquire(row('CLOSE'))
  self.assertEqual(len(c.calls),1);self.assertEqual(self.stored().status,'CLOSE')
  self.assertTrue(self.stored().sources['maximo']['collection']['same_version_status_confirmed'])
 def test_same_version_conflicting_confirmation_does_not_write(self):
  self.ingest(row())
  with self.assertRaises(OslcError):self.acquire(row('CLOSE'),row('APPR'))
  self.assertEqual(self.stored().status,'APPR')
 def test_direct_store_same_version_conflict_without_confirmation_is_rejected(self):
  self.ingest(row())
  with self.assertRaises(ValueError):self.ingest(row('CLOSE'))
  self.assertEqual(self.stored().status,'APPR')
 def test_same_version_status_confirmation_rejects_unknown_dates(self):
  self.ingest(row())
  for value in (None,'bad','2026-10-20T12:00:00'):
   with self.assertRaises(OslcError):self.acquire(row('CLOSE',statusdate=value))
   self.assertEqual(self.stored().status,'APPR')
 def test_same_version_status_confirmation_accepts_equivalent_offsets(self):
  self.ingest(row());self.acquire(row('CLOSE'),row('CLOSE',statusdate='2026-10-20T19:00:00+07:00'))
  self.assertEqual(self.stored().status,'CLOSE')
 def test_same_version_cancellation_confirms_only_summary_never_detail_actual(self):
  self.ingest(row());_,c=self.acquire(row('CAN'))
  self.assertEqual(c.calls[0]['select'],list(SUMMARY_FIELDS));self.assertEqual(self.stored().status,'CAN')
  self.assertEqual(self.stored().description,'Retained detail')
 def test_older_input_does_not_fetch_detail(self):
  self.ingest(row(day=22));out,c=self.acquire(row(day=21));self.assertFalse(c.calls);self.assertEqual(out[0],'unchanged')
 def test_missing_nested_details_preserve_prior_observations(self):
  p=row(seksi='Retained section',pctaskid='42');self.ingest(p);self.acquire(row(day=21))
  m=self.stored().sources['maximo'];self.assertEqual(m['extra']['seksi'],'Retained section');self.assertEqual(m['hierarchy']['source_fields']['pctaskid'],'42')
 def test_missing_active_fields_do_not_erase_retained_detail(self):
  self.ingest(row());p=row(day=21);p.pop('description');self.acquire(p);self.assertEqual(self.stored().description,'Retained detail')
 def test_backfill_cannot_bypass_lifecycle_or_source_lock(self):
  with self.assertRaises(ValueError):SyncService(Detail(),self.store).sync(replace(CFG,recent_work_orders=False))
 def test_old_source_backlog_newly_ingested_still_reaches_incremental_mart(self):
  from src.repositories.models import EquipmentOrm
  from src.repositories.mart_models import MaintenanceEventMartOrm
  from src.services.local_mart_projector import CollectorMartProjector
  with self.db.session() as s:
   s.add(EquipmentOrm(id='A1',sources={'maximo':{'siteid':'BSR','orgid':'IP'}}));s.commit()
  self.ingest(row(day=22));projector=CollectorMartProjector(self.db,self.db,batch_size=1);projector.project('maintenance_event')
  older={**row(day=14),'wonum':'BSR-OLDER'};self.ingest(older)
  report=projector.project('maintenance_event',incremental=True)
  with self.db.session() as s:self.assertEqual(s.query(MaintenanceEventMartOrm).count(),2)
  self.assertGreaterEqual(report.rows_written,1)
 def test_repeated_same_observation_does_not_move_local_ingestion_time(self):
  p=row();self.ingest(p);before=self.stored().sources['maximo']['collector_updated_at']
  self.assertEqual(self.ingest(p),'unchanged');self.assertEqual(self.stored().sources['maximo']['collector_updated_at'],before)
 def test_canonical_nonclose_has_no_actual_clocks(self):
  p=row('COMP',actstart='2026-10-20T01:00:00Z',actfinish='2026-10-20T02:00:00Z');v=maintenance_event_from_payload(p)
  self.assertIsNone(v['actual_start']);self.assertIsNone(v['actual_finish']);self.assertIsNone(v['duration_hours'])
 def test_canonical_task_scope_evidence_is_explicit(self):
  v=maintenance_event_from_payload(row('CLOSE'));m=v['sources']['maximo'];self.assertIs(m['istask'],False);self.assertEqual(m['siteid'],'BSR');self.assertEqual(m['orgid'],'IP')
 def test_adaptive_checkpoint_is_durable_separate_from_success_cursor(self):
  self.store.set_cursor('mxwodetail',T,1);self.store.save_work_order_catchup_pages(T,40)
  restarted=CollectorStore(self.db);self.assertEqual(restarted.work_order_catchup_pages(T,20,200),40)
  self.assertEqual(restarted.get_cursor('mxwodetail').replace(tzinfo=timezone.utc),T)
  self.assertEqual(restarted.work_order_catchup_pages(datetime(2026,10,14,tzinfo=timezone.utc),20,200),20)

class ReplayStore:
 def __init__(self):self.cursor=T;self.budget=1;self.runs=[];self.cursor_writes=0
 @contextmanager
 def work_order_recovery_lock(self):yield True
 def get_cursor(self,*a):return self.cursor
 def set_cursor(self,k,v,n):self.cursor=v;self.cursor_writes+=1
 def work_order_catchup_pages(self,c,b,m):return self.budget
 def save_work_order_catchup_pages(self,c,p):self.budget=p
 def record_run(self,s):self.runs.append(s)
 def active_work_order_candidates(self,*args):return []
 def mark_work_order_status_checked(self,*args):pass
 def work_order_snapshot(self,id):return {'status':'CLOSE','source_changed_at':datetime(2026,10,14,tzinfo=timezone.utc)}
 def upsert_for(self,*a):raise AssertionError('terminal must not write')
class Pages:
 def __init__(self,pages):self.pages=pages;self.request_telemetry={'business_requests':0};self.last_iteration_pages=0
 @contextmanager
 def bounded_requests(self,n):yield
 def iterate_pages(self,name,**kw):
  for i,p in enumerate(self.pages):
   if i>=kw['max_pages']:raise OslcPaginationLimitError(name,pages=i,max_pages=kw['max_pages'],next_page_fingerprint='x')
   self.request_telemetry['business_requests']+=1;self.last_iteration_pages+=1;yield p
class ReplayTest(unittest.TestCase):
 def test_bounded_restarts_progress_beyond_original_first_page(self):
  pages=[]
  for day in (22,21,20,19,12):
   p=row('CLOSE',day);p['wonum']=f'BSR-{day}';pages.append([p])
  s=ReplayStore();results=[]
  for _ in range(4):results.append(SyncService(Pages(pages),s).sync(CFG))
  self.assertEqual([r.recency['page_cap'] for r in results],[1,2,4,8])
  self.assertTrue(all(not r.complete for r in results[:3]));self.assertTrue(results[-1].complete)
  self.assertEqual(s.cursor_writes,1);self.assertEqual(results[-1].rows_seen,5)
 def test_page_repeat_is_partial_no_cursor_promotion(self):
  s=ReplayStore();s.budget=5;r=SyncService(Pages([[row('CLOSE')],[row('CLOSE')]]),s).sync(CFG)
  self.assertFalse(r.complete);self.assertEqual(r.recency['stop_reason'],'UNSTABLE_PAGINATION');self.assertEqual(s.cursor_writes,0)
 def test_foreign_scope_and_missing_scope_remain_separate_and_unwritten(self):
  for mutation,key in (({'siteid':'OTHER'},'source_scope_excluded'),({'orgid':None},'source_scope_unknown')):
   s=ReplayStore();r=SyncService(Pages([[{**row('CLOSE'),**mutation}]]),s).sync(CFG)
   self.assertFalse(r.complete);self.assertEqual(r.recency[key],1);self.assertEqual(s.cursor_writes,0)
 def test_partial_page_overlap_never_promotes_cursor(self):
  s=ReplayStore();s.budget=10
  a={**row('CLOSE',22),'wonum':'BSR-A'};b={**row('CLOSE',21),'wonum':'BSR-B'};d={**row('CLOSE',20),'wonum':'BSR-D'}
  r=SyncService(Pages([[a,b],[b,d],[row('CLOSE',12)]]),s).sync(CFG)
  self.assertFalse(r.complete);self.assertEqual(r.recency['stop_reason'],'UNSTABLE_PAGINATION');self.assertEqual(s.cursor_writes,0)
 def test_concurrent_worker_stops_without_source(self):
  class Busy(ReplayStore):
   @contextmanager
   def work_order_recovery_lock(self):yield False
  c=Pages([[row('CLOSE')]]);r=SyncService(c,Busy()).sync(CFG)
  self.assertEqual(r.recency['stop_reason'],'SOURCE_BUSY');self.assertEqual(c.request_telemetry['business_requests'],0)
