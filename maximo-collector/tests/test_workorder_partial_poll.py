from contextlib import contextmanager
from dataclasses import replace
import unittest
from unittest.mock import patch
import requests
from test_workorder_lifecycle import CFG, Pages, ReplayStore, row
from src.services.sync import SyncService
from src.adapters.maximo.oslc_client import OslcPaginationLimitError

EMPTY = dict(checked=0, updated=0, inserted=0, unchanged=0, detail_fetched=0, errors=0)
class BudgetPages(Pages):
    def __init__(self, pages):
        super().__init__(pages); self.limits=[]
    @contextmanager
    def bounded_requests(self, n):
        previous=self.request_telemetry.get('budget');boundary=self.request_telemetry['business_requests']+n
        self.request_telemetry['budget']=min(previous,boundary) if previous is not None else boundary
        self.limits.append(n)
        try:yield
        finally:self.request_telemetry['budget']=previous
    def iterate_pages(self, *args, **kwargs):
        for page in super().iterate_pages(*args, **kwargs):
            if isinstance(page, Exception):raise page
            yield page

class PartialPollTest(unittest.TestCase):
    def run_sync(self,pages,budget=40,page_cap=5,poll=None):
        store=ReplayStore();store.budget=page_cap;client=BudgetPages(pages)
        with patch('src.services.workorder_status_poll.poll_active_work_orders',side_effect=poll or (lambda *args:dict(EMPTY))) as mocked:
            stats=SyncService(client,store).sync(replace(CFG,request_limit=budget))
        return stats,store,client,mocked
    def test_overlap_uses_only_remaining_budget_and_preserves_partial_cursor(self):
        def poll(client,store,config,excluded):
            self.assertEqual(client.request_telemetry['budget'],40)
            self.assertEqual(client.request_telemetry['business_requests'],2)
            self.assertEqual(excluded,{'BSR-TEST'})
            client.request_telemetry['business_requests']+=3
            return dict(EMPTY,checked=2,updated=1,unchanged=1)
        s,store,c,m=self.run_sync([[row('CLOSE')],[row('CLOSE')]],poll=poll)
        self.assertEqual(m.call_count,1);self.assertEqual(c.limits,[40,38])
        self.assertFalse(s.complete);self.assertEqual(s.recency['stop_reason'],'UNSTABLE_PAGINATION')
        self.assertEqual(store.cursor_writes,0);self.assertEqual(s.recency['requests'],5)
        self.assertEqual(s.recency['source_rows_read'],2);self.assertEqual(s.rows_seen,4)
        self.assertEqual(s.recency['validated_pages'],1);self.assertEqual(s.recency['pages'],2)
    def test_page_limit_can_poll_without_losing_next_page_budget(self):
        s,store,c,m=self.run_sync([[row('CLOSE',22)],[row('CLOSE',21)]],page_cap=1)
        self.assertEqual(m.call_count,1);self.assertEqual(s.recency['stop_reason'],'PAGE_LIMIT')
        self.assertEqual(s.recency['next_page_cap'],2);self.assertEqual(store.cursor_writes,0)
    def test_no_poll_after_source_or_scope_or_order_error(self):
        cases=[[[row('CLOSE')],requests.ReadTimeout()], [[{**row('CLOSE'),'siteid':'OTHER'}]],
               [[row('CLOSE',20)],[{**row('CLOSE',22),'siteid':'OTHER'}]],
               [[row('CLOSE',20)],[row('CLOSE',22)]]]
        for pages in cases:
            with self.subTest(pages=pages):
                s,store,c,m=self.run_sync(pages);self.assertEqual(m.call_count,0);self.assertFalse(s.complete)
    def test_exhausted_budget_skips_without_reopening_budget(self):
        s,store,c,m=self.run_sync([[row('CLOSE')],[row('CLOSE')]],budget=2,page_cap=1)
        # page cap allows one request, leaving only one. No zero-sized context.
        self.assertEqual(m.call_count,0);self.assertEqual(c.limits,[2])
        self.assertEqual(s.recency['active_status_poll']['stop_reason'],'SHARED_REQUEST_BUDGET')
    def test_poll_failure_preserves_original_partial_reason(self):
        def poll(*args):return dict(EMPTY,errors=1)
        s,store,c,m=self.run_sync([[row('CLOSE')],[row('CLOSE')]],poll=poll)
        self.assertEqual(s.recency['stop_reason'],'UNSTABLE_PAGINATION');self.assertEqual(s.errors,2)
        self.assertEqual(store.cursor_writes,0)
    def test_complete_head_poll_failure_prevents_cursor_promotion(self):
        def poll(*args):raise ValueError('local store unavailable')
        s,store,c,m=self.run_sync([[row('CLOSE',12)]],poll=poll)
        self.assertEqual(s.recency['stop_reason'],'ACTIVE_STATUS_CHECK_FAILED');self.assertFalse(s.complete)
        self.assertEqual(store.cursor_writes,0)
    def test_nested_detail_page_cap_never_enables_fallback(self):
        failure=OslcPaginationLimitError('mxwodetail',pages=2,max_pages=2,next_page_fingerprint='test')
        with patch('src.services.workorder_recency.acquire_work_order',side_effect=failure):
            s,store,c,m=self.run_sync([[row('CLOSE')]])
        self.assertEqual(s.recency['stop_reason'],'MAPPING_OR_STORE_ERROR')
        self.assertEqual(m.call_count,0);self.assertFalse(s.complete);self.assertEqual(store.cursor_writes,0)
