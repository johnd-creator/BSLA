"""Hermetic query-shape and semantic parity checks for attention candidates."""
from collections import Counter
from datetime import timedelta
import unittest

from sqlalchemy import event, select
from sqlalchemy.dialects import postgresql

import test_daily_work_order_activity as daily

NOW, MISSING = daily.NOW, daily.MISSING
from src.repositories.maintenance_activity import latest_registered_work_orders, activity_evidence


class MaintenanceInvestigationPerformanceTest(unittest.TestCase):
    def setUp(self):
        self.fixture = daily.DailyWorkOrderActivityTest()
        self.fixture.setUp()
        self.database = self.fixture.database
        self.repository = self.fixture.repository

    def tearDown(self):
        self.fixture.tearDown()

    def populate_edge_cases(self):
        f = self.fixture
        old = NOW - timedelta(days=4)
        f.add_asset("SECOND")
        f.add_asset("TECHNICAL", registered=False)
        f.add(
            f.event("a", start=old, finish=old + timedelta(hours=1)),
            f.event("b", start=NOW),
            f.event("copy-old", work_order="COPY", start=old, changed=old),
            f.event("copy-current", work_order="COPY", start=NOW),
            f.event("cancel-old", work_order="CANCEL", start=old, changed=old),
            f.event("cancel-current", work_order="CANCEL", status="CAN", start=NOW),
            f.event("moved-old", work_order="MOVED", start=old, changed=old),
            f.event("moved-current", work_order="MOVED", asset="TECHNICAL", start=NOW),
            f.event("null-id", work_order=None, start=NOW),
            f.event("source-id", work_order=None, start=old, sources={"wonum": "SOURCE"}),
            f.event("source-id-copy", work_order=None, start=NOW, sources={"wonum": "SOURCE"}),
            f.event("invalid-order", start=NOW, finish=old),
            f.event("finish-only", finish=NOW),
            f.event("unverified-time", start=NOW, evidence=False),
            f.event("no-source-scope", start=NOW, sources={"scope_evidence": None}),
            f.event("foreign-site", start=NOW, sources={"siteid": "OTHER"}),
            f.event("foreign-org", start=NOW, sources={"orgid": "OTHER"}),
            f.event("future", start=NOW + timedelta(seconds=1)),
            f.event("outside-window", start=NOW - timedelta(days=190)),
            f.event("second-a", asset="SECOND", start=old),
            f.event("second-b", asset="SECOND", start=NOW),
            *(f.event("task-"+str(i), task=marker, start=NOW) for i, marker in enumerate(
                [True, None, MISSING, "false", "true", 0, 1])),
        )

    def test_compact_scalar_scope_matches_legacy_on_duplicates_unknowns_and_moved_assets(self):
        self.populate_edge_cases()
        legacy = latest_registered_work_orders(self.database)
        compact = latest_registered_work_orders(self.database, compact=True)
        fields = ["equipment_id", "work_order_key", "identity_records", "status", "source_asset_number",
                  "task_state", "source_scope_verified", "invalid_actual_order", "start_clock_verified",
                  "finish_clock_verified", "activity_start", "activity_finish"]
        with self.database.read_session() as session:
            before = session.execute(select(*(legacy.c[name] for name in fields))).all()
            after = session.execute(select(*(compact.c[name] for name in fields))).all()
        self.assertEqual(Counter(map(tuple, before)), Counter(map(tuple, after)))
        self.assertEqual(activity_evidence(self.database, legacy), activity_evidence(self.database, compact))
        self.assertFalse(any(row.work_order_key == "MOVED" for row in after))
        self.assertEqual(next(row for row in after if row.work_order_key == "CANCEL").activity_start, None)

    def test_one_bounded_statement_returns_metadata_even_for_empty_or_past_end_page(self):
        self.populate_edge_cases()
        statements = []
        def record(_conn, _cursor, statement, _parameters, _context, _many):
            statements.append(statement)
        event.listen(self.database.engine, "before_cursor_execute", record)
        try:
            page = self.repository.maintenance_investigation(as_of=NOW, limit=1)
        finally:
            event.remove(self.database.engine, "before_cursor_execute", record)
        self.assertEqual(len(statements), 1)
        self.assertEqual(len(page["assets"]), 1)
        self.assertEqual(page["meta"]["total"], 2)
        self.assertTrue(page["meta"]["has_more"])
        self.assertIn("LIMIT", statements[0])
        past = self.repository.maintenance_investigation(as_of=NOW, offset=1000, limit=1)
        self.assertEqual(past["assets"], [])
        self.assertEqual(past["summary"], page["summary"])
        self.assertEqual(past["activity_evidence"], page["activity_evidence"])
        self.assertEqual(past["meta"]["total"], 2)
        self.assertFalse(past["meta"]["has_more"])

    def test_empty_store_and_all_unknown_preserve_unavailable_not_false_health(self):
        result = self.repository.maintenance_investigation(as_of=NOW)
        self.assertEqual(result["assets"], [])
        self.assertEqual(result["summary"]["registered_assets"], 1)
        self.assertEqual(result["summary"]["maintenance_events"], 0)
        self.assertEqual(result["activity_evidence"]["availability"], "UNAVAILABLE")
        self.fixture.add(self.fixture.event("unknown", task=MISSING))
        result = self.repository.maintenance_investigation(as_of=NOW)
        self.assertEqual(result["activity_evidence"]["unknown_task_work_orders"], 1)
        self.assertEqual(result["activity_evidence"]["availability"], "UNAVAILABLE")

    def test_postgres_materializes_compact_evidence_without_removing_read_only_guards(self):
        compact = latest_registered_work_orders(self.database, compact=True)
        sql = str(select(compact).compile(dialect=postgresql.dialect()))
        self.assertIn("latest_work_order_payload AS MATERIALIZED", sql)
        self.assertIn("registered_work_order_facts AS MATERIALIZED", sql)
        self.assertNotIn("sources", compact.c.keys())
        self.assertNotIn("provenance", compact.c.keys())
        self.assertIn("identity_rank", sql)
        self.assertIn("reliability_asset_registry", sql)
