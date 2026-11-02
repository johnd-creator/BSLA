"""Integrated population qualification; SQLite memory only, no retained/source IO.

Direct bulk seeding is deliberately a read-test fixture, not an importer. Mutation,
CAS, receipts, review and revision behavior remain covered by real HTTP/PG suites.
"""
import copy
import json
import time
import tracemalloc
import unittest
from pathlib import Path
from sqlalchemy import event, insert
from src.repositories.human_records import RecordRow
import test_pdm_input as native
import test_sprint3_evidence as source

OUT = Path("/tmp/nadi-sprint05/performance.json")


def record(name, value):
    OUT.parent.mkdir(parents=True, exist_ok=True)
    old = json.loads(OUT.read_text()) if OUT.exists() else {}
    old[name] = value
    old["classification"] = "SYNTHETIC_SQLITE_ONLY_NOT_OPERATIONAL_SLA"
    OUT.write_text(json.dumps(old, indent=2) + "\n")


class InspectionPopulationTest(unittest.TestCase):
    def setUp(self):
        self.fx = native.PdmInputTest()
        self.fx.setUp()
        template = self.fx.multi("S5-synthetic-seed")
        self.original = copy.deepcopy(template["measurements"])
        docs = []
        for i in range(2500):
            row = copy.deepcopy(template)
            row["record_id"] = f"inspection:SYNTHETIC-S5-{i:05d}"
            row["observations"] = ["SYNTHETIC needle" if i % 10 == 0 else "SYNTHETIC ordinary"]
            # Explicit denied population proves scope filtering before counts.
            if i >= 2000:
                row["canonical_asset_id"] = "asset:SYNTHETIC-DENIED"
            docs.append(dict(kind="MANUAL_INSPECTION", record_id=row["record_id"], revision=1, document=row))
        # Use owning service kind, never a guessed schema enum.
        for doc in docs:
            doc["kind"] = self.fx.inspections.kind
        with self.fx.engine.begin() as connection:
            connection.execute(insert(RecordRow), docs)
        self.actor = self.fx.directory("author")

    def tearDown(self):
        self.fx.tearDown()

    def measure(self, name, reader):
        queries = []
        def listen(c, cursor, sql, parameters, context, many):
            queries.append(sql)
        event.listen(self.fx.engine, "before_cursor_execute", listen)
        tracemalloc.start()
        start = time.perf_counter()
        try:
            page = reader()
            elapsed = time.perf_counter() - start
            peak = tracemalloc.get_traced_memory()[1]
        finally:
            tracemalloc.stop()
            event.remove(self.fx.engine, "before_cursor_execute", listen)
        self.assertEqual(len(queries), 1, "no per-record application query fanout")
        self.assertTrue(queries[0].lstrip().upper().startswith("SELECT"))
        # Actual implementation streams all filtered documents to count; SQL LIMIT
        # is not claimed for this JSON reader. Python retains only selected page.
        self.assertLess(len(page["items"]), 26)
        self.assertLess(elapsed, 60, "gross synthetic regression guard only")
        wire = len(json.dumps(page, default=lambda x: x.model_dump(mode="json")).encode())
        self.assertLess(wire, 2 * 1024 * 1024)
        record(name, dict(seconds=elapsed, python_peak_bytes=peak, select_count=len(queries),
                         returned=len(page["items"]), total=page["total"], json_bytes=wire,
                         seeded_inspections=2501, denied_inspections=500,
                         implementation="filtered document scan, yield_per=100; not indexed search"))
        return page

    def test_register_sizes_stable_exact_scope_and_originals(self):
        for limit in (1, 5, 10):
            first = self.measure(f"register_{limit}", lambda: self.fx.inspections.list(
                self.actor, asset_id=self.fx.asset, offset=0, limit=limit))
            second = self.fx.inspections.list(self.actor, asset_id=self.fx.asset, offset=limit, limit=limit)
            self.assertEqual(first["total"], 2001)
            self.assertEqual(first["items"][0].measurements[0].value, 0)
            self.assertIsNone(first["items"][0].measurements[1].value)
            ids = lambda page: {x.record_id for x in page["items"]}
            self.assertFalse(ids(first) & ids(second))
            self.assertTrue(all(x.canonical_asset_id == self.fx.asset for x in second["items"]))
            self.assertEqual(ids(first), ids(self.fx.inspections.list(self.actor, asset_id=self.fx.asset, limit=limit)))
        from src.domain.engineering import EngineeringError
        with self.assertRaises(EngineeringError):
            self.fx.inspections.list(self.actor, asset_id="asset:SYNTHETIC-DENIED", limit=10)

    def test_contextual_measurement_history_bounded_count_original_types(self):
        page = self.measure("history", lambda: self.fx.inspections.measurement_history(
            self.actor, asset_id=self.fx.asset, method="VIBRATION", point="point:SYNTHETIC", limit=25))
        self.assertEqual(page["total"], 10005)
        values = [x["measurement"].value for x in page["items"][:5]]
        self.assertEqual(values, [0, None, "trace", False, 4.2])
        self.assertIs(values[3], False)
        filtered = self.fx.inspections.measurement_history(self.actor, asset_id=self.fx.asset,
                                                         search="needle", quantity="synthetic_quantity", limit=10)
        self.assertEqual(filtered["total"], 1000)
        self.assertEqual(filtered["event_time_basis"], "MEASURED_AT")


class MaintenancePopulationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source.Sprint3EvidenceTest.setUpClass()
    @classmethod
    def tearDownClass(cls):
        source.Sprint3EvidenceTest.tearDownClass()

    def test_sql_query_count_payload_and_stable_source_pages(self):
        from test_reliability_mart import ASSET_A
        fx = source.Sprint3EvidenceTest
        statements = []
        def listen(c, cursor, sql, parameters, context, many):
            statements.append(sql)
        event.listen(fx.db.engine, "before_cursor_execute", listen)
        tracemalloc.start()
        start = time.perf_counter()
        try:
            seen = set()
            for offset in range(0, 500, 25):
                page = fx.repository.list_maintenance(asset_ref=ASSET_A, offset=offset, limit=25)
                self.assertEqual(page.total, 10000)
                ids = {r.canonical_id for r in page.items}
                self.assertFalse(ids & seen)
                seen |= ids
                self.assertEqual(len(page.items), 25)
            elapsed = time.perf_counter() - start
            peak = tracemalloc.get_traced_memory()[1]
        finally:
            tracemalloc.stop()
            event.remove(fx.db.engine, "before_cursor_execute", listen)
        self.assertEqual(len(statements), 40, "one count + one bounded page SELECT per request")
        self.assertTrue(all(sql.lstrip().upper().startswith("SELECT") for sql in statements))
        self.assertEqual(sum("LIMIT" in sql.upper() for sql in statements), 20)
        record("maintenance", dict(seeded_events=10025, selected_events=10000, pages=20,
                                   rows_per_page=25, select_count=len(statements), seconds=elapsed,
                                   python_peak_bytes=peak, distinct_page_ids=len(seen)))


if __name__ == "__main__":
    unittest.main()
