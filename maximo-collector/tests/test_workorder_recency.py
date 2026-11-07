"""Cursor loss/regression tests: fakes, no DB or network."""
from contextlib import contextmanager
from dataclasses import replace
from datetime import datetime, timezone
from types import SimpleNamespace
import unittest

import requests

from src.adapters.maximo.oslc_client import OslcError, OslcPaginationLimitError, OslcRequestBudgetExceeded
from src.services.sync import ObjectSyncConfig, SyncService
from src.services.workorder_recency import bootstrap_recent_work_orders

CURSOR = datetime(2026, 8, 21, tzinfo=timezone.utc)


def row(name, day=21):
    return dict(wonum=name, reportdate="2025-01-01T00:00:00+07:00", changedate=f"2026-08-{day:02d}T00:00:00Z", siteid="BSR", orgid="IP")


class Store:
    def __init__(self, cursor=CURSOR):
        self.cursor = cursor
        self.rows = {}
        self.runs = []
        self.cursor_writes = 0
        self.floor = CURSOR
        self.anchor = None
    @contextmanager
    def work_order_recovery_lock(self): yield True
    def prepare_work_order_recovery_floor(self):
        if self.anchor is None:
            self.anchor = self.floor
        return self.anchor
    def get_cursor(self, scope): return self.cursor
    def set_cursor(self, scope, change, seen):
        self.cursor = change
        self.cursor_writes += 1
    def record_run(self, stats): self.runs.append(stats)
    def is_unchanged(self, kind, identity, column, change):
        return identity in self.rows and self.rows[identity].change == change
    def upsert_for(self, kind, entity):
        outcome = "updated" if entity.id in self.rows else "inserted"
        self.rows[entity.id] = entity
        return outcome


class Client:
    def __init__(self, pages):
        self.pages = pages
        self.request_telemetry = {"business_requests": 0}
        self.calls = []
        self.last_iteration_pages = 0
    @contextmanager
    def bounded_requests(self, limit):
        self.limit = limit
        yield
    def iterate_pages(self, name, **kwargs):
        self.calls.append(kwargs)
        for page in self.pages:
            if self.last_iteration_pages >= kwargs["max_pages"]:
                raise OslcPaginationLimitError(name, pages=self.last_iteration_pages, max_pages=kwargs["max_pages"], next_page_fingerprint="test")
            if self.request_telemetry["business_requests"] >= self.limit:
                raise OslcRequestBudgetExceeded("budget")
            self.last_iteration_pages += 1
            self.request_telemetry["business_requests"] += 1
            if isinstance(page, Exception): raise page
            yield page
    def iterate(self, name, **kwargs):
        # Historical backfill continues through old rows, without recency cutoff.
        self.calls.append(kwargs)
        for page in self.pages:
            yield from page


def mapper(raw):
    return SimpleNamespace(id=raw["wonum"], change=datetime.fromisoformat(raw["changedate"].replace("Z", "+00:00")))

CFG = ObjectSyncConfig("mxwodetail", "work_order", mapper,
    prefix_field="wonum", allowed_prefixes=("BSR",), prefix_query=True,
    watermark_query=False, recent_work_orders=True, cursor_requires_zero_errors=True,
    page_size=25, max_pages=20, request_limit=40)


class RecencyTest(unittest.TestCase):
    def run_sync(self, pages, store=None, config=CFG):
        store = store or Store()
        client = Client(pages)
        stats = SyncService(client, store).sync(config)
        return stats, store, client

    def test_newest_first_and_newer_upsert(self):
        stats, store, client = self.run_sync([[row("BSR1", 22), row("BSR2", 21), row("BSR0", 20)]])
        self.assertEqual(client.calls[0]["order_by"], "-changedate")
        self.assertIn('wonum in ["BSR%"]', client.calls[0]["where"])
        self.assertNotIn(">=", client.calls[0]["where"])
        self.assertEqual(set(store.rows), {"BSR1", "BSR2"})
        self.assertEqual(store.cursor.day, 22)
        self.assertEqual(stats.recency["stop_reason"], "CURSOR_REACHED")

    def test_no_new_cycle_costs_one_page(self):
        stats, store, client = self.run_sync([[row("BSR0", 20)], [row("BSRold", 19)]])
        self.assertEqual(client.request_telemetry["business_requests"], 1)
        self.assertEqual(stats.recency["stop_reason"], "NO_NEW_ROWS")
        self.assertEqual(store.cursor, CURSOR)

    def test_ties_continue_across_pages(self):
        stats, store, client = self.run_sync([[row("BSRa")], [row("BSRb"), row("BSRc")], [row("BSRold", 20)]])
        self.assertEqual(len(store.rows), 3)
        self.assertEqual(stats.recency["pages"], 3)
        self.assertTrue(stats.complete)

    def test_equal_cursor_is_idempotent(self):
        store = Store()
        self.run_sync([[row("BSRa"), row("BSRold", 20)]], store)
        stats, store, _ = self.run_sync([[row("BSRa"), row("BSRold", 20)]], store)
        self.assertEqual(stats.upserted, 0)
        self.assertEqual(stats.unchanged, 1)
        self.assertEqual(len(store.rows), 1)

    def test_out_of_order_after_old_row_cannot_stop_or_write(self):
        stats, store, _ = self.run_sync([[row("BSRold", 20), row("BSRnew", 22)]])
        self.assertFalse(stats.complete)
        self.assertEqual(stats.recency["stop_reason"], "ORDER_VIOLATION")
        self.assertFalse(store.rows)
        self.assertEqual(store.cursor_writes, 0)

    def test_order_checked_across_pages(self):
        stats, store, _ = self.run_sync([[row("BSRa", 22)], [row("BSRb", 23)]])
        self.assertFalse(stats.complete)
        self.assertEqual(store.cursor, CURSOR)

    def test_partial_pagination_retains_cursor_and_progress(self):
        stats, store, _ = self.run_sync([[row("BSRa", 22)], [row("BSRb")]], config=replace(CFG, max_pages=1))
        self.assertEqual(stats.recency["stop_reason"], "PAGE_LIMIT")
        self.assertIn("BSRa", store.rows)
        self.assertEqual(store.cursor_writes, 0)
        stats, store, _ = self.run_sync([[row("BSRa", 22), row("BSRb"), row("BSRold", 20)]], store)
        self.assertEqual(stats.upserted, 1)
        self.assertEqual(store.cursor.day, 22)

    def test_source_failure_preserves_cursor(self):
        stats, store, _ = self.run_sync([[row("BSRa", 22)], requests.ReadTimeout()])
        self.assertEqual(stats.recency["stop_reason"], "SOURCE_ERROR")
        self.assertEqual(store.cursor_writes, 0)

    def test_mapping_error_preserves_cursor(self):
        def bad(raw): raise ValueError("bad")
        stats, store, _ = self.run_sync([[row("BSRa", 22)]], config=replace(CFG, mapper=bad))
        self.assertFalse(stats.complete)
        self.assertEqual(stats.recency["stop_reason"], "MAPPING_OR_STORE_ERROR")
        self.assertEqual(store.cursor_writes, 0)

    def test_prefix_guard_remains_local(self):
        stats, store, _ = self.run_sync([[row("OTHER", 22), row("BSRa"), row("BSRold", 20)]])
        self.assertEqual(set(store.rows), {"BSRa"})
        self.assertEqual(stats.recency["prefix_skipped"], 1)
        self.assertEqual(store.cursor, CURSOR)

    def test_unsupported_order_fails_closed(self):
        stats, store, client = self.run_sync([requests.HTTPError("unsupported")])
        self.assertFalse(stats.complete)
        self.assertEqual(len(client.calls), 1)
        self.assertEqual(store.cursor_writes, 0)

    def test_unordered_config_rejected_before_source(self):
        with self.assertRaises(ValueError):
            self.run_sync([], config=replace(CFG, order_by=None))

    def test_historical_backfill_is_independent(self):
        stats, store, client = self.run_sync([[row("BSRa", 22), row("BSRold", 19)]],
            config=replace(CFG, recent_work_orders=False, watermark_field=None, order_by=None))
        self.assertEqual(set(store.rows), {"BSRa", "BSRold"})
        self.assertEqual(store.cursor_writes, 0)
        self.assertNotIn(">=", client.calls[0]["where"])

    def test_missing_cursor_never_seeded_from_partial_batch(self):
        stats, store, _ = self.run_sync([[row("BSRa", 22)], [row("BSRb")]],
            store=Store(None), config=replace(CFG, max_pages=1))
        self.assertFalse(stats.complete)
        self.assertEqual(stats.recency["stop_reason"], "BOOTSTRAP_REQUIRED")
        self.assertEqual(stats.recency["requests"], 0)
        self.assertIsNone(store.cursor)
        self.assertEqual(store.cursor_writes, 0)

    def test_request_budget_does_not_move_cursor(self):
        stats, store, _ = self.run_sync([[row("BSRa", 22)], [row("BSRb")]], config=replace(CFG, request_limit=1))
        self.assertEqual(stats.recency["stop_reason"], "REQUEST_BUDGET")
        self.assertEqual(store.cursor_writes, 0)

    def test_missing_timestamp_and_scope_fail_closed(self):
        for mutation in ({"changedate": ""}, {"siteid": "OTHER"}, {"orgid": "OTHER"}):
            with self.subTest(mutation=mutation):
                stats, store, _ = self.run_sync([[{**row("BSRa", 22), **mutation}]])
                self.assertFalse(stats.complete)
                self.assertEqual(store.cursor_writes, 0)

    def test_duplicate_identity_only_latest_version_written(self):
        stats, store, _ = self.run_sync([[row("BSRa", 22), row("BSRa"), row("BSRold", 20)]])
        self.assertEqual(stats.duplicate_ids, 1)
        self.assertEqual(store.rows["BSRa"].change.day, 22)

    def test_complete_small_bootstrap_can_establish_cursor(self):
        store = Store(None)
        stats = bootstrap_recent_work_orders(Client([[row("BSRa", 22), row("BSRb")]]), store, CFG)
        self.assertTrue(stats.complete)
        self.assertEqual(stats.recency["stop_reason"], "SOURCE_EXHAUSTED")
        self.assertEqual(store.cursor.day, 22)

    def test_store_failure_preserves_cursor(self):
        class BrokenStore(Store):
            def upsert_for(self, *args): raise RuntimeError("store unavailable")
        stats, store, _ = self.run_sync([[row("BSRa", 22)]], store=BrokenStore())
        self.assertFalse(stats.complete)
        self.assertEqual(stats.recency["stop_reason"], "MAPPING_OR_STORE_ERROR")
        self.assertEqual(store.cursor_writes, 0)


class BootstrapRecoveryTest(unittest.TestCase):
    def bootstrap(self, pages, store=None, config=CFG):
        store = store or Store(None)
        client = Client(pages)
        stats = bootstrap_recent_work_orders(client, store, config)
        return stats, store, client

    def test_missing_cursor_routine_never_queries_source_repeatedly(self):
        store, client = Store(None), Client([RuntimeError("must not access source")])
        for _ in range(3):
            stats = SyncService(client, store).sync(CFG)
            self.assertEqual(stats.recency["stop_reason"], "BOOTSTRAP_REQUIRED")
            self.assertFalse(stats.complete)
        self.assertEqual(client.calls, [])
        self.assertEqual(client.request_telemetry["business_requests"], 0)

    def test_local_floor_and_newest_first_then_cursor_established(self):
        stats, store, client = self.bootstrap([[row("BSRnew", 22)], [row("BSRtie")], [row("BSRold", 20)]])
        self.assertTrue(stats.complete)
        self.assertEqual(stats.recency["recovery_floor"], CURSOR.isoformat())
        self.assertTrue(stats.recency["recovery_floor_reached"])
        self.assertEqual(store.cursor.day, 22)
        self.assertEqual(set(store.rows), {"BSRnew", "BSRtie"})
        self.assertEqual(client.calls[0]["order_by"], "-changedate")
        self.assertIn('wonum in ["BSR%"]', client.calls[0]["where"])

    def test_empty_local_store_blocks_without_source(self):
        store = Store(None)
        store.floor = None
        stats, store, client = self.bootstrap([], store)
        self.assertEqual(stats.recency["stop_reason"], "BOOTSTRAP_BLOCKED")
        self.assertEqual(client.calls, [])
        self.assertIsNone(store.cursor)

    def test_floor_ties_continue_across_pages(self):
        stats, store, _ = self.bootstrap([[row("BSRnew", 22), row("BSRa")], [row("BSRb")], [row("BSRold", 20)]])
        self.assertTrue(stats.complete)
        self.assertEqual(set(store.rows), {"BSRnew", "BSRa", "BSRb"})

    def test_page_limit_partial_does_not_establish_cursor(self):
        stats, store, _ = self.bootstrap([[row("BSRa", 22)], [row("BSRb")]], config=replace(CFG, max_pages=1))
        self.assertEqual(stats.recency["stop_reason"], "PAGE_LIMIT")
        self.assertFalse(stats.recency["recovery_floor_reached"])
        self.assertIsNone(store.cursor)
        self.assertEqual(store.cursor_writes, 0)

    def test_budget_partial_does_not_establish_cursor(self):
        stats, store, _ = self.bootstrap([[row("BSRa", 22)], [row("BSRb")]], config=replace(CFG, request_limit=1))
        self.assertEqual(stats.recency["stop_reason"], "REQUEST_BUDGET")
        self.assertIsNone(store.cursor)

    def test_retry_keeps_original_floor_after_partial_upsert(self):
        store = Store(None)
        self.bootstrap([[row("BSRa", 22)], [row("BSRb")]], store, replace(CFG, max_pages=1))
        store.floor = datetime(2026, 8, 22, tzinfo=timezone.utc)  # local MAX rose
        stats, store, _ = self.bootstrap([[row("BSRa", 22)], [row("BSRb")], [row("BSRold", 20)]], store)
        self.assertEqual(stats.recency["recovery_floor"], CURSOR.isoformat())
        self.assertTrue(stats.complete)
        self.assertIn("BSRb", store.rows)
        self.assertEqual(stats.upserted, 1)

    def test_source_failure_no_cursor(self):
        stats, store, _ = self.bootstrap([[row("BSRa", 22)], requests.ReadTimeout()])
        self.assertEqual(stats.recency["stop_reason"], "SOURCE_ERROR")
        self.assertEqual(store.cursor_writes, 0)

    def test_mapping_failure_no_cursor(self):
        def bad(raw): raise ValueError("bad")
        stats, store, _ = self.bootstrap([[row("BSRa", 22)]], config=replace(CFG, mapper=bad))
        self.assertEqual(stats.recency["stop_reason"], "MAPPING_OR_STORE_ERROR")
        self.assertEqual(store.cursor_writes, 0)

    def test_store_failure_no_cursor(self):
        class Broken(Store):
            def upsert_for(self, *args): raise RuntimeError("store unavailable")
        stats, store, _ = self.bootstrap([[row("BSRa", 22)]], Broken(None))
        self.assertEqual(stats.recency["stop_reason"], "MAPPING_OR_STORE_ERROR")
        self.assertEqual(store.cursor_writes, 0)

    def test_ordering_violation_no_cursor(self):
        stats, store, _ = self.bootstrap([[row("BSRa", 22)], [row("BSRb", 23)]])
        self.assertEqual(stats.recency["stop_reason"], "ORDER_VIOLATION")
        self.assertIsNone(store.cursor)

    def test_scope_violation_no_cursor(self):
        for field in ("siteid", "orgid"):
            stats, store, _ = self.bootstrap([[{**row("BSRa", 22), field: "OTHER"}]])
            self.assertEqual(stats.recency["stop_reason"], "SCOPE_ERROR")
            self.assertIsNone(store.cursor)

    def test_success_then_routine_cycle_costs_one_page(self):
        stats, store, _ = self.bootstrap([[row("BSRa", 22), row("BSRb"), row("BSRold", 20)]])
        self.assertTrue(stats.complete)
        client = Client([[row("BSRa", 22), row("BSRb")], [row("BSRold", 20)]])
        routine = SyncService(client, store).sync(CFG)
        self.assertEqual(routine.recency["stop_reason"], "NO_NEW_ROWS")
        self.assertEqual(routine.recency["requests"], 1)
        self.assertEqual(routine.upserted, 0)

    def test_exhaustion_above_floor_is_not_reconciled(self):
        stats, store, _ = self.bootstrap([[row("BSRa", 22)]])
        self.assertEqual(stats.recency["stop_reason"], "RECOVERY_FLOOR_NOT_REACHED")
        self.assertIsNone(store.cursor)

    def test_changes_after_start_remain_eligible(self):
        future = {**row("BSRa"), "changedate": "2100-01-01T00:00:00Z"}
        stats, store, _ = self.bootstrap([[future, row("BSRold", 20)]])
        self.assertTrue(stats.complete)
        self.assertLessEqual(store.cursor, stats.started_at)
        client = Client([[future, row("BSRold", 20)]])
        followup = SyncService(client, store).sync(CFG)
        self.assertEqual(followup.unchanged, 1)
        self.assertEqual(followup.recency["prefix_accepted"], 2)

    def test_existing_cursor_is_never_reset_by_bootstrap(self):
        stats, store, client = self.bootstrap([], Store())
        self.assertEqual(stats.recency["stop_reason"], "BOOTSTRAP_NOT_REQUIRED")
        self.assertEqual(client.calls, [])
        self.assertEqual(store.cursor, CURSOR)

    def test_parallel_bootstrap_fails_cheaply(self):
        class Busy(Store):
            @contextmanager
            def work_order_recovery_lock(self): yield False
        stats, store, client = self.bootstrap([], Busy(None))
        self.assertEqual(stats.recency["stop_reason"], "BOOTSTRAP_BUSY")
        self.assertEqual(client.calls, [])

    def test_cursor_store_failure_reports_partial(self):
        class Broken(Store):
            def set_cursor(self, *args): raise RuntimeError("transaction failed")
        stats, store, _ = self.bootstrap([[row("BSRa", 22), row("BSRold", 20)]], Broken(None))
        self.assertFalse(stats.complete)
        self.assertEqual(stats.recency["stop_reason"], "CURSOR_STORE_ERROR")
        self.assertIsNone(store.cursor)

    def test_unverified_or_unlimited_config_rejected_before_source(self):
        for config in (replace(CFG, prefix_query=False), replace(CFG, max_pages=1001),
                       replace(CFG, request_limit=2001), replace(CFG, page_size=26)):
            with self.assertRaises(ValueError): self.bootstrap([], config=config)
