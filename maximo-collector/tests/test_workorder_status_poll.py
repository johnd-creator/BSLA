import re,unittest
from src.services.workorder_status_poll import poll_active_work_orders
from src.services.workorder_policy import SUMMARY_FIELDS
from src.repositories.database import Database
from src.repositories.store import CollectorStore
from src.repositories.models import WorkOrderOrm
from src.config import DbConfig
from src.adapters.maximo.mappers import work_order_from_payload
from src.adapters.maximo.oslc_client import OslcRequestBudgetExceeded
from test_workorder_lifecycle import CFG,row

class Client:
 def __init__(self,records,budget=40):self.records=records;self.calls=[];self.request_telemetry={'business_requests':0,'budget':budget}
 def iterate(self,name,**kw):
  if self.request_telemetry['business_requests']>=self.request_telemetry['budget']:raise OslcRequestBudgetExceeded('budget')
  self.request_telemetry['business_requests']+=1;self.calls.append(kw)
  key=re.search(r'wonum="([^"\n]+)"',kw['where']).group(1)
  record=self.records.get(key)
  if record:
   yield {k:v for k,v in record.items() if k in kw['select']}

class ActiveStatusPollTest(unittest.TestCase):
 def setUp(self):
  self.db=Database(DbConfig('sqlite+pysqlite:///:memory:'));self.db.create_all();self.store=CollectorStore(self.db)
 def tearDown(self):self.db.engine.dispose()
 def add(self,p):self.store.upsert_work_order(work_order_from_payload(p))
 def stored(self,id='BSR-TEST'):
  with self.db.session() as s:return s.get(WorkOrderOrm,id)
 def test_old_active_same_timestamp_close_is_reconciled_beyond_head_cursor(self):
  self.add(row('COMP',10));p=row('CLOSE',10,actstart='2026-10-10T01:00:00Z',actfinish='2026-10-10T02:00:00Z')
  c=Client({'BSR-TEST':p});r=poll_active_work_orders(c,self.store,CFG,set())
  self.assertEqual(r['updated'],1);self.assertEqual(r['detail_fetched'],1);self.assertEqual(len(c.calls),2)
  self.assertEqual(c.calls[0]['select'],list(SUMMARY_FIELDS));self.assertIn('actstart',c.calls[1]['select'])
  self.assertEqual(self.stored().status,'CLOSE');self.assertFalse(self.store.active_work_order_candidates(('BSR',),set()))
 def test_terminal_rows_never_enter_queue_or_trigger_requests(self):
  for i,status in enumerate(('CLOSE','CAN','CANCEL')):self.add({**row(status),'wonum':f'BSR-{i}'})
  c=Client({});r=poll_active_work_orders(c,self.store,CFG,set());self.assertFalse(c.calls);self.assertEqual(r['checked'],0)
 def test_unchanged_active_uses_only_summary_and_rotates_without_dirtying_ingestion(self):
  self.add(row());self.add({**row(),'wonum':'BSR-Z'});c=Client({'BSR-TEST':row(),'BSR-Z':{**row(),'wonum':'BSR-Z'}})
  r=poll_active_work_orders(c,self.store,CFG,set(),max_checks=1);self.assertEqual(r['checked'],1);self.assertEqual(r['detail_fetched'],0)
  self.assertEqual(self.store.active_work_order_candidates(('BSR',),set(),1),['BSR-Z'])
  first=self.stored().sources['maximo']['collector_updated_at'];self.store.mark_work_order_status_checked('BSR-TEST')
  self.assertEqual(self.stored().sources['maximo']['collector_updated_at'],first)
  self.assertEqual(c.calls[0]['select'],list(SUMMARY_FIELDS))
 def test_recent_head_ids_and_non_bsr_ids_excluded(self):
  self.add(row());self.add({**row(),'wonum':'OTHER-1'})
  self.assertFalse(self.store.active_work_order_candidates(('BSR',),{'BSR-TEST'}))
 def test_shared_budget_does_not_start_unfinishable_check(self):
  self.add(row());c=Client({'BSR-TEST':row()},budget=1);r=poll_active_work_orders(c,self.store,CFG,set())
  self.assertFalse(c.calls);self.assertEqual(r['stop_reason'],'SHARED_REQUEST_BUDGET')
 def test_missing_or_foreign_source_row_preserves_local_data_and_records_failed_check(self):
  for records in ({},{'BSR-TEST':{**row(),'siteid':'OTHER'}}):
   self.add(row());r=poll_active_work_orders(Client(records),self.store,CFG,set());self.assertEqual(r['errors'],1)
   self.assertEqual(self.stored().status,'APPR');self.assertEqual(self.stored().sources['maximo']['status_check_state'],'FAILED')
 def test_active_clock_fields_are_never_requested(self):
  self.add(row(day=19));c=Client({'BSR-TEST':row(actstart='2026-10-20T01:00:00Z',actfinish='2026-10-20T02:00:00Z')})
  r=poll_active_work_orders(c,self.store,CFG,set());self.assertEqual(r['detail_fetched'],1)
  self.assertTrue(all('actstart' not in q['select'] and 'actfinish' not in q['select'] for q in c.calls))
  self.assertEqual(self.stored().sources['maximo']['actual_dates']['fields']['actstart']['state'],'UNAVAILABLE')
