"""No production access: resumable source snapshots and publication invariants."""
from contextlib import contextmanager
import copy,re
from datetime import datetime,timezone
from unittest import TestCase
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from src.config import DbConfig
from src.repositories.database import Database
from src.repositories.models import EquipmentOrm,WorkOrderOrm,SyncCursorOrm
from src.repositories.store import CollectorStore
from src.repositories.asset_inventory import AssetInventoryStore
from src.repositories.asset_inventory_sweep import SweepStore,InventoryStageOrm
from src.services.asset_inventory_sweep import collect_sweep_batch,validate_page,signature,VERIFY_FIELDS,SweepGuard,version_only_advanced
from test_asset_inventory import REF,raw

def row(n,name,unit='CS01',parent=None,**kw):return raw(name,unit,parent,assetid=n,**kw)
class Store(CollectorStore):
 @contextmanager
 def work_order_recovery_lock(self):yield True
class Client:
 def __init__(self,rows,callback=None):self.rows=copy.deepcopy(rows);self.callback=callback;self.calls=[];self.request_telemetry={'business_requests':0};self.bound=0
 @contextmanager
 def bounded_requests(self,limit):self.bound=self.request_telemetry['business_requests']+limit;yield
 def iterate_pages(self,name,**kw):
  assert self.request_telemetry['business_requests']<self.bound
  self.request_telemetry['business_requests']+=1;self.calls.append(kw)
  if self.callback:self.callback(self,kw)
  rows=copy.deepcopy(self.rows);where=kw['where']
  for operator,number in re.findall(r'assetid(<=|>|=)(\d+)',where):
   n=int(number);rows=[r for r in rows if (r['assetid']<=n if operator=='<=' else r['assetid']>n if operator=='>' else r['assetid']==n)]
  date=re.search(r'changedate>="([^"]+)"',where)
  if date:
   threshold=datetime.fromisoformat(date[1]);rows=[r for r in rows if datetime.fromisoformat(r['changedate'].replace('Z','+00:00'))>=threshold]
  rows.sort(key=lambda r:r['assetid'],reverse=kw['order_by'].startswith('-'))
  yield [{k:v for k,v in r.items() if k in kw['select']} for r in rows[:kw['page_size']]]
class SweepTests(TestCase):
 def setUp(self):
  self.db=Database(DbConfig(dsn='sqlite+pysqlite:///:memory:'));self.db.create_all()
  self.store=Store(self.db);AssetInventoryStore(self.db).create_tables();self.s=SweepStore(self.db);self.s.create_tables()
 def tearDown(self):self.db.engine.dispose()
 def finish(self,c,**kw):
  result=None
  for _ in range(20):
   result=collect_sweep_batch(c,self.store,REF,max_requests=2,**kw)
   self.assertEqual(result['errors'],0,result)
   if result['state']=='PUBLISHED':return result
  self.fail(str(result))
 def test_small_batches_resume_and_publish_only_after_recheck(self):
  c=Client([row(10,'E1'),row(20,'C1',None,'E1'),row(30,'P1',None,'C1')])
  first=collect_sweep_batch(c,self.store,REF,max_requests=2)
  self.assertEqual(first['collect_cursor'],30);self.assertEqual(first['state'],'COLLECTING')
  with self.db.session() as s:self.assertEqual(s.query(EquipmentOrm).count(),0)
  result=self.finish(c);self.assertTrue(result['full_source_baseline_complete']);self.assertEqual(result['inventory_assets'],3)
  self.assertEqual(result['verified_rows'],3)
  with self.db.session() as s:
   self.assertIsNone(s.get(EquipmentOrm,'C1').unit);self.assertEqual(s.query(WorkOrderOrm).count(),0);self.assertEqual(s.query(SyncCursorOrm).count(),0)
  for call in c.calls:self.assertNotIn('pageno',str(call));self.assertLessEqual(call['page_size'],50)
 def test_already_published_performs_no_new_source_read(self):
  c=Client([row(10,'E1')]);self.finish(c);before=c.request_telemetry['business_requests']
  result=collect_sweep_batch(c,self.store,REF)
  self.assertEqual(result['stop_reason'],'ALREADY_PUBLISHED');self.assertEqual(c.request_telemetry['business_requests'],before)
 def test_atomic_page_and_checkpoint_rollback_on_duplicate_identity(self):
  run=self.s.choose(REF['sha256']);self.s.initialize(run.id,100)
  records=[(10,row(10,'E1'),signature(row(10,'E1'))),(20,row(20,'E1'),signature(row(20,'E1')))]
  with self.assertRaises(IntegrityError):self.s.save_collect_page(run.id,0,records)
  self.assertEqual(self.s.get(run.id).collect_cursor,0);self.assertEqual(self.s.summary(run.id)['staged_rows'],0)
 def test_stale_checkpoint_cannot_skip_records(self):
  run=self.s.choose(REF['sha256']);self.s.initialize(run.id,100)
  with self.assertRaises(ValueError):self.s.save_collect_page(run.id,99,[])
  self.assertEqual(self.s.get(run.id).state,'COLLECTING')
 def test_reordered_or_out_of_range_source_fails_closed(self):
  for rows in ([row(20,'C1'),row(10,'E1')],[row(101,'E1')],[row(0,'E1')],[row(10,'E1',siteid='OTHER')]):
   with self.assertRaises(SweepGuard):validate_page(rows,lower=0,upper=100)
 def test_changed_source_is_exactly_refreshed_before_verification_advances(self):
  def mutate(c,kw):
   if self.s.choose(REF['sha256']).state=='VERIFYING' and kw['order_by']=='+assetid' and 'assetid=' not in kw['where']:c.rows[0]['description']='new source description'
  c=Client([row(10,'E1')],mutate);result=self.finish(c)
  self.assertTrue(any('assetid=10' in x['where'] for x in c.calls))
  with self.db.session() as s:self.assertEqual(s.get(EquipmentOrm,'E1').description,'new source description')
 def test_new_source_id_extends_upper_boundary_and_rechecks(self):
  def mutate(c,kw):
   if kw['order_by']=='-assetid' and len([x for x in c.calls if x['order_by']=='-assetid'])==2:
    c.rows.append(row(20,'C1',None,'E1'))
  c=Client([row(10,'E1')],mutate);result=self.finish(c)
  self.assertEqual(result['verified_rows'],2);self.assertEqual(result['rounds'],2)
 def test_asset_moved_into_scope_below_cursor_is_found_in_independent_recheck(self):
  def mutate(c,kw):
   if self.s.choose(REF['sha256']).state=='VERIFYING' and kw['order_by']=='+assetid' and 'assetid=' not in kw['where'] and not any(r['assetid']==5 for r in c.rows):
    c.rows.append(row(5,'C1',None,'E1'))
  c=Client([row(10,'E1')],mutate);result=self.finish(c)
  self.assertEqual(result['verified_rows'],2)
  with self.db.session() as s:self.assertIsNotNone(s.get(EquipmentOrm,'C1'))
 def test_source_removed_before_recheck_not_published_as_current(self):
  def mutate(c,kw):
   if self.s.choose(REF['sha256']).state=='VERIFYING' and kw['order_by']=='+assetid' and 'assetid=' not in kw['where']:c.rows=[r for r in c.rows if r['assetid']!=5]
  c=Client([row(5,'C1',None,'E1'),row(10,'E1')],mutate);result=self.finish(c)
  self.assertEqual(result['staged_rows'],2);self.assertEqual(result['verified_rows'],1)
 def test_source_change_during_confirmation_keeps_verification_cursor(self):
  def mutate(c,kw):
   if self.s.choose(REF['sha256']).state=='VERIFYING' and kw['order_by']=='+assetid' and 'assetid=' not in kw['where']:c.rows[0]['description']='summary'
   if 'assetid=10' in kw['where']:c.rows[0]['description']='later'
  c=Client([row(10,'E1')],mutate)
  result=collect_sweep_batch(c,self.store,REF,max_requests=20)
  self.assertEqual(result['stop_reason'],'SOURCE_CHANGED_DURING_VERIFICATION');self.assertEqual(result['verify_cursor'],0)
  with self.db.session() as s:self.assertEqual(s.query(EquipmentOrm).count(),0)
  c.callback=None;self.finish(c)
 def test_empty_source_does_not_erase_inventory_or_claim_completion(self):
  result=collect_sweep_batch(Client([]),self.store,REF)
  self.assertEqual(result['stop_reason'],'UNEXPECTED_EMPTY_SOURCE_SCOPE');self.assertFalse(result['full_source_baseline_complete'])
 def test_response_cap_failure_does_not_advance_checkpoint(self):
  def cap(c,kw):
   if kw['order_by']=='+assetid':raise RuntimeError('oversized body (1500000 > 1048576 bytes)')
  result=collect_sweep_batch(Client([row(10,'E1')],cap),self.store,REF)
  self.assertEqual(result['stop_reason'],'RESPONSE_SIZE_CAP');self.assertEqual(result['collect_cursor'],0)
 def test_reference_mismatch_cannot_resume_another_source_run(self):
  run=self.s.choose('b'*64)
  with self.assertRaises(ValueError):collect_sweep_batch(Client([]),self.store,REF,identity=run.id)
 def test_source_busy_makes_no_request(self):
  @contextmanager
  def busy():yield False
  self.store.work_order_recovery_lock=busy;c=Client([row(10,'E1')])
  result=collect_sweep_batch(c,self.store,REF)
  self.assertEqual(result['stop_reason'],'SOURCE_BUSY');self.assertEqual(c.request_telemetry['business_requests'],0)
 def test_deadline_before_read_saves_no_progress(self):
  times=iter([0,181,181]);c=Client([row(10,'E1')])
  result=collect_sweep_batch(c,self.store,REF,monotonic=lambda:next(times))
  self.assertEqual(result['requests'],0);self.assertEqual(result['collect_cursor'],0)

 def test_change_tail_catches_lower_id_moving_in_after_verification(self):
  def mutate(c,kw):
   if kw['order_by']=='-assetid' and len([x for x in c.calls if x['order_by']=='-assetid'])==2:
    c.rows.append(row(5,'C1',None,'E1',changedate=datetime.now(timezone.utc).isoformat()))
  c=Client([row(10,'E1')],mutate);result=self.finish(c)
  self.assertEqual(result['verified_rows'],2)
  self.assertTrue(any('changedate>=' in call['where'] for call in c.calls))

 def test_version_only_advance_preserves_newer_exact_payload(self):
  def mutate(c,kw):
   if self.s.choose(REF['sha256']).state=='VERIFYING' and kw['order_by']=='+assetid' and 'assetid=' not in kw['where']:
    c.rows[0]['changedate']='2025-01-01T00:00:01Z';c.rows[0]['totalcost']=123.45
   if 'assetid=10' in kw['where']:
    c.rows[0]['changedate']='2025-01-01T00:00:02Z';c.rows[0]['totalcost']=123.45
  c=Client([row(10,'E1',changedate='2025-01-01T00:00:00Z')],mutate)
  result=self.finish(c)
  self.assertEqual(result['version_advance_observations'],1)
  with self.db.session() as s:self.assertEqual(float(s.get(EquipmentOrm,'E1').total_cost),123.45)
  self.assertEqual(self.s.stage(result['sweep_id'],10).payload['changedate'],'2025-01-01T00:00:02Z')
 def test_version_only_advance_rejects_changed_business_fields(self):
  before=row(10,'E1',changedate='2025-01-01T00:00:00Z')
  for field,value in [('parent','OTHER'),('eq11','OTHER'),('status','OTHER'),('description','OTHER'),('assetnum','OTHER'),('assetid',11)]:
   after={**before,field:value,'changedate':'2025-01-01T00:00:01Z'}
   self.assertFalse(version_only_advanced(before,after),field)
 def test_version_only_advance_rejects_unknown_equal_or_regressing_time(self):
  before=row(10,'E1',changedate='2025-01-01T00:00:00Z')
  for stamp in (None,'2025-01-01T00:00:00Z','2024-12-31T23:59:59Z'):
   self.assertFalse(version_only_advanced(before,{**before,'changedate':stamp}))

 def test_dense_volatile_versions_advance_without_per_id_request_explosion(self):
  def mutate(c,kw):
   if self.s.choose(REF['sha256']).state=='VERIFYING':
    for item in c.rows:item['changedate']='2025-01-01T00:00:01Z'
  c=Client([row(n,'E'+str(n),changedate='2025-01-01T00:00:00Z') for n in range(1,51)],mutate)
  result=self.finish(c)
  self.assertEqual(result['verified_rows'],50)
  self.assertEqual(result['version_advance_observations'],50)
  self.assertFalse(any(re.search(r'assetid=\d+',x['where']) for x in c.calls))
  self.assertLess(len(c.calls),10)
 def test_full_page_recheck_refuses_regressing_source_version(self):
  def mutate(c,kw):
   if self.s.choose(REF['sha256']).state=='VERIFYING':c.rows[0]['changedate']='2024-01-01T00:00:00Z'
  c=Client([row(10,'E1',changedate='2025-01-01T00:00:00Z')],mutate)
  result=collect_sweep_batch(c,self.store,REF,max_requests=20)
  self.assertEqual(result['stop_reason'],'SOURCE_VERSION_REGRESSED_DURING_VERIFICATION')
  self.assertEqual(result['verify_cursor'],0)
