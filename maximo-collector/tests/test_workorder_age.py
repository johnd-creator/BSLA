from datetime import datetime, timedelta, timezone
from unittest.mock import patch
import unittest
from src.services.workorder_age import window, eligibility
from src.services.workorder_policy import acquire_work_order
from src.services.workorder_status_poll import poll_active_work_orders
import test_workorder_lifecycle as fixtures
from test_workorder_lifecycle import CFG, row, Detail, Pages, ReplayStore
from test_workorder_status_poll import Client
from src.services.sync import SyncService

NOW=datetime(2026,11,6,2,0,tzinfo=timezone.utc)
class AgeWindowTest(unittest.TestCase):
 def test_boundary_inclusive_before_excluded_and_equivalent_offset(self):
  lo,hi=window(NOW)
  self.assertEqual(lo,datetime(2022,11,6,2,tzinfo=timezone.utc))
  self.assertEqual(eligibility({'reportdate':lo.isoformat()},(lo,hi)),'AGE_ELIGIBLE')
  self.assertEqual(eligibility({'reportdate':(lo-timedelta(microseconds=1)).isoformat()},(lo,hi)),'AGE_EXCLUDED')
  self.assertEqual(eligibility({'reportdate':'2022-11-06T09:00:00+07:00'},(lo,hi)),'AGE_ELIGIBLE')
 def test_calendar_years_not_fixed_days_and_leap_century_clamp(self):
  self.assertEqual(window(datetime(2104,2,29,2,tzinfo=timezone.utc))[0],datetime(2100,2,28,2,tzinfo=timezone.utc))
  self.assertEqual(window(datetime(2028,2,29,2,tzinfo=timezone.utc))[0],datetime(2024,2,29,2,tzinfo=timezone.utc))
 def test_jakarta_calendar_boundary(self):
  self.assertEqual(window(datetime(2104,2,28,18,tzinfo=timezone.utc))[0],datetime(2100,2,27,18,tzinfo=timezone.utc))
 def test_unknown_never_uses_changedate_statusdate_or_actual(self):
  for value in (None,'','bad','2025-01-01','2025-01-01T00:00:00','2030-01-01T00:00:00Z',1):
   self.assertEqual(eligibility({'reportdate':value,'changedate':NOW.isoformat(),'statusdate':NOW.isoformat(),'actstart':NOW.isoformat()},window(NOW)),'AGE_UNKNOWN')
 def test_naive_local_clock_rejected(self):
  with self.assertRaises(ValueError):window(NOW.replace(tzinfo=None))

# Inherit fixture helpers only, not the previous test methods.
class AgeAcquisitionTest(unittest.TestCase):
 setUp=fixtures.LifecycleTest.setUp
 tearDown=fixtures.LifecycleTest.tearDown
 stored=fixtures.LifecycleTest.stored
 ingest=fixtures.LifecycleTest.ingest
 def test_old_open_and_terminal_zero_details_zero_insert(self):
  for status in ('APPR','CLOSE','CAN','CANCEL'):
   p=row(status,reportdate='2020-01-01T00:00:00Z');c=Detail(p)
   self.assertEqual(acquire_work_order(c,self.store,CFG,p),('unchanged','AGE_EXCLUDED'))
   self.assertEqual(c.calls,[]);self.assertIsNone(self.stored())
 def test_old_existing_retained_byte_for_byte(self):
  p=row(reportdate='2020-01-01T00:00:00Z');self.ingest(p)
  before=self.stored();c=Detail({**p,'status':'CLOSE'})
  acquire_work_order(c,self.store,CFG,{**p,'status':'CLOSE'})
  after=self.stored();self.assertEqual(before.sources,after.sources);self.assertEqual(before.status,after.status)
  self.assertFalse(c.calls)
 def test_missing_invalid_and_naive_block_details_and_inserts(self):
  for date in (None,'bad','2025-01-01T00:00:00'):
   p=row(reportdate=date);c=Detail(p)
   self.assertEqual(acquire_work_order(c,self.store,CFG,p),('unchanged','AGE_UNKNOWN'))
   self.assertFalse(c.calls);self.assertIsNone(self.stored())
 def test_recent_summary_cannot_write_old_or_missing_detail(self):
  for date in ('2020-01-01T00:00:00Z',None):
   c=Detail(row(reportdate=date));out=acquire_work_order(c,self.store,CFG,row())
   self.assertTrue(out[1].startswith('AGE_'));self.assertIsNone(self.stored())
 def test_active_queue_excludes_old_unknown_future_before_requests(self):
  for i,date in enumerate(('2020-01-01T00:00:00Z',None,'2030-01-01T00:00:00Z')):
   self.ingest({**row(reportdate=date),'wonum':f'BSR-{i}'})
  c=Client({});result=poll_active_work_orders(c,self.store,CFG,set())
  self.assertFalse(c.calls);self.assertEqual(result['checked'],0)
 def test_source_summary_corrects_apparently_recent_to_old_without_write(self):
  self.ingest(row());before=self.stored().sources
  c=Client({'BSR-TEST':row(reportdate='2020-01-01T00:00:00Z')})
  result=poll_active_work_orders(c,self.store,CFG,set())
  self.assertEqual(result['age_excluded'],1);self.assertEqual(len(c.calls),1)
  self.assertEqual(self.stored().sources,before)
 def test_api_retains_old_row(self):
  # Read-side remains independent of acquisition eligibility; no retention pruning.
  self.ingest(row(reportdate='2020-01-01T00:00:00Z'))
  self.assertIsNotNone(self.stored())
  self.assertEqual(self.store.work_order_snapshot('BSR-TEST')['status'],'APPR')
  from src.repositories.models import WorkOrderOrm
  self.assertEqual(len(self.store.list_rows(WorkOrderOrm)),1)

class AgeTraversalTest(unittest.TestCase):
 def run_sync(self,payload):
  store=ReplayStore();client=Pages([[payload]])
  original=client.iterate_pages
  client.calls=[]
  def record(*args, **kwargs):
   client.calls.append(kwargs)
   yield from original(*args, **kwargs)
  client.iterate_pages=record
  with patch('src.services.workorder_status_poll.poll_active_work_orders',return_value=dict(checked=0,updated=0,inserted=0,unchanged=0,detail_fetched=0,errors=0)):
   result=SyncService(client,store).sync(CFG)
  return result,store,client
 def test_old_list_no_detail_no_upsert_and_eligible_cursor_progress(self):
  r,s,c=self.run_sync(row(reportdate='2020-01-01T00:00:00Z'))
  self.assertEqual(r.upserted,0);self.assertEqual(r.recency['age_excluded'],1)
  self.assertTrue(r.complete);self.assertEqual(s.cursor_writes,1)
  self.assertIn('reportdate',c.calls[0]['select'])
 def test_missing_age_does_not_promote_cursor(self):
  r,s,c=self.run_sync(row(reportdate=None))
  self.assertEqual(r.upserted,0);self.assertFalse(r.complete)
  self.assertEqual(s.cursor_writes,0);self.assertEqual(r.recency['age_unknown'],1)
