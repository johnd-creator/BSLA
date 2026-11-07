"""Hermetic regression tests for daily WO evidence, never production access."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import unittest

from sqlalchemy import select
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Session

from src.api.reliability import _decision_overview, _maintenance_investigation
from src.config import MartDbConfig
from src.repositories.maintenance_activity import latest_registered_work_orders
from src.repositories.mart_database import MartDatabase
from src.repositories.mart_models import AssetMasterMart, MaintenanceEventMart, MartBase, ReliabilityAssetRegistryMart
from src.repositories.mart_reader import MartQueryRepository

NOW = datetime(2026, 11, 5, 20, tzinfo=timezone.utc)  # November 6, 03:00 WIB
ASSET = "asset:BSR:IP:ONE"
MISSING = object()


class DailyWorkOrderActivityTest(unittest.TestCase):
    def setUp(self):
        self.database = MartDatabase(MartDbConfig(dsn="sqlite+pysqlite:///:memory:"))
        MartBase.metadata.create_all(self.database.engine)
        self.repository = MartQueryRepository(self.database)
        self.add_asset(ASSET)

    def tearDown(self):
        self.database.engine.dispose()

    def add_asset(self, ref, site="BSR", org="IP", registered=True):
        common = dict(site_code=site, organization_code=org, mart_created_at=NOW, mart_updated_at=NOW,
                      contract_version="1.0", provenance={}, relationship_evidence={})
        with Session(self.database.engine) as session:
            session.add(AssetMasterMart(canonical_id=ref, source_asset_number=ref, **common))
            if registered:
                session.add(ReliabilityAssetRegistryMart(asset_ref=ref, source_asset_number=ref, site_code=site,
                    organization_code=org, registry_source="SYNTHETIC", snapshot_sha256="a"*64,
                    snapshot_row_count=1, snapshot_imported_at=NOW))
            session.commit()

    def event(self, key, *, work_order=MISSING, start=None, finish=None, changed=NOW, status="CLOSE",
              task=False, sources=None, asset=ASSET, site="BSR", org="IP", evidence=True):
        if work_order is MISSING:
            work_order = "WO:" + key
        maximo = {"siteid": site, "orgid": org, "worktype": "PM", "scope_evidence": "DIRECT_SOURCE"}
        if task is not MISSING:
            maximo["istask"] = task
        if evidence:
            maximo["actual_dates"] = {"fields": {"actstart": {"state": "VALID" if start else "NULL"},
                                                  "actfinish": {"state": "VALID" if finish else "NULL"}}}
        if sources:
            maximo.update(sources)
        return MaintenanceEventMart(canonical_id="EVENT:"+key, id=key, equipment_id=asset, work_order_id=work_order,
            status=status, event_type="PM", actual_start=start, actual_finish=finish, source_changed_at=changed,
            site_code=site, organization_code=org, contract_version="1.0", sources={"maximo": maximo},
            provenance={}, relationship_evidence={}, mart_created_at=NOW, mart_updated_at=changed or NOW)

    def add(self, *events):
        with Session(self.database.engine) as session:
            session.add_all(events)
            session.commit()

    def overview(self, days=7):
        return self.repository.decision_overview(window_days=days, as_of=NOW)

    def test_600_metadata_changes_are_not_600_maintenance_activities(self):
        self.add(*(self.event(str(i)) for i in range(600)))
        result = self.overview()
        self.assertEqual(result["summary"]["maintenance_activity_7d"], 0)
        self.assertEqual(sum(x["event_count"] for x in result["trend"]), 0)
        self.assertEqual(result["daily_activity"][-1], {"date": "2026-11-06", "started_work_orders": 0,
            "finished_work_orders": 0, "record_changed_work_orders": 600})
        evidence = result["activity_evidence"]
        self.assertEqual(evidence["availability"], "UNAVAILABLE")
        self.assertEqual(evidence["unique_work_orders"], 600)
        self.assertEqual(evidence["unknown_start_work_orders"], 600)
        self.assertEqual(evidence["unknown_finish_work_orders"], 600)
        self.assertIn("does not establish zero maintenance", evidence["interpretation"])

    def test_duplicate_rows_are_deduped_before_status_and_date_filters(self):
        earlier = NOW - timedelta(days=2)
        self.add(
            self.event("a-old", work_order="A", start=earlier, changed=earlier),
            self.event("a-current", work_order="A", start=NOW, changed=NOW),
            self.event("reopened-old", work_order="REOPENED", start=earlier, changed=earlier),
            self.event("reopened-current", work_order="REOPENED", status="INPRG", start=earlier, changed=NOW),
            self.event("cancelled-old", work_order="CANCELLED", start=earlier, changed=earlier),
            self.event("cancelled-current", work_order="CANCELLED", status="CAN", start=earlier, changed=NOW),
        )
        result = self.overview()
        self.assertEqual(result["summary"]["maintenance_activity_7d"], 1)
        self.assertEqual(result["activity_evidence"]["retained_records"], 6)
        self.assertEqual(result["activity_evidence"]["unique_work_orders"], 3)
        self.assertEqual(result["activity_evidence"]["duplicate_records_excluded"], 3)
        self.assertEqual(result["activity_evidence"]["not_closed_work_orders"], 2)
        self.assertEqual(result["status_distribution"], [{"value":"CLOSE", "count":1}])

    def test_task_flags_require_real_boolean_and_unknown_is_not_main_wo(self):
        self.add(*(self.event(str(i), start=NOW, task=value) for i, value in enumerate(
            [False, True, None, MISSING, 0, 1, "false", "true", "garbage"])))
        result = self.overview()
        self.assertEqual(result["summary"]["maintenance_activity_7d"], 1)
        self.assertEqual(result["activity_evidence"]["task_work_orders_excluded"], 1)
        self.assertEqual(result["activity_evidence"]["unknown_task_work_orders"], 7)
        self.assertEqual(result["activity_evidence"]["availability"], "PARTIAL")

    def test_wib_calendar_midnight_is_exclusive_and_future_is_not_counted(self):
        boundary = datetime(2026, 11, 5, 17, tzinfo=timezone.utc)
        self.add(self.event("before", start=boundary-timedelta(seconds=1)),
                 self.event("midnight", start=boundary),
                 self.event("future", start=NOW+timedelta(seconds=1)))
        result = self.overview()
        self.assertEqual(result["summary"]["maintenance_activity_7d"], 2)
        self.assertEqual(result["daily_activity"][-2]["date"], "2026-11-05")
        self.assertEqual(result["daily_activity"][-2]["started_work_orders"], 1)
        self.assertEqual(result["daily_activity"][-1]["started_work_orders"], 1)
        self.assertEqual(sum(x["event_count"] for x in result["trend"]), 2)
        self.assertEqual(result["window_start"], datetime(2026, 10, 30, 17, tzinfo=timezone.utc))

    def test_week_starts_at_monday_wib_not_monday_utc(self):
        boundary = datetime(2026, 11, 1, 17, tzinfo=timezone.utc)
        self.add(self.event("sunday", start=boundary-timedelta(seconds=1)), self.event("monday", start=boundary))
        result = self.overview()
        self.assertEqual(result["trend"][-1]["period_start"], boundary)
        self.assertEqual(result["trend"][-2]["event_count"], 1)
        self.assertEqual(result["trend"][-1]["event_count"], 1)

    def test_start_and_finish_are_separate_evidence_and_invalid_clocks_stay_unknown(self):
        yesterday = NOW-timedelta(days=1)
        self.add(self.event("independent", start=yesterday, finish=NOW),
            self.event("finish-only", finish=NOW),
            self.event("invalid-order", start=NOW, finish=yesterday),
            self.event("unverified", start=NOW, evidence=False),
            self.event("naive-source", start=NOW, sources={"actual_dates": {"fields":{"actstart":{"state":"NAIVE"}}}}),
            self.event("not-close", start=NOW, finish=NOW, status="COMP"))
        result = self.overview()
        self.assertEqual(result["summary"]["maintenance_activity_7d"], 1)
        self.assertEqual(result["daily_activity"][-1]["finished_work_orders"], 2)
        self.assertEqual(result["daily_activity"][-1]["started_work_orders"], 0)
        self.assertEqual(result["activity_evidence"]["invalid_actual_order_work_orders"], 1)
        self.assertEqual(result["activity_evidence"]["unknown_start_work_orders"], 4)

    def test_scope_excludes_foreign_unregistered_and_explicit_source_mismatches(self):
        self.add_asset("TECH", registered=False)
        self.add_asset("FOREIGN", site="OTHER")
        self.add(self.event("good", start=NOW), self.event("wrong-site", start=NOW, site="OTHER"),
            self.event("wrong-org", start=NOW, org="OTHER"), self.event("technical", start=NOW, asset="TECH"),
            self.event("foreign-registry", start=NOW, asset="FOREIGN"),
            self.event("source-mismatch", start=NOW, sources={"siteid":"OTHER"}),
            self.event("source-org-mismatch", start=NOW, sources={"orgid":"OTHER"}))
        result = self.overview()
        self.assertEqual(result["activity_evidence"]["unique_work_orders"], 1)
        self.assertEqual(result["summary"]["maintenance_activity_7d"], 1)

    def test_normalized_asset_join_scope_is_not_direct_wo_scope_evidence(self):
        self.add(self.event("direct", start=NOW),
            self.event("legacy", start=NOW, sources={"scope_evidence":"LEGACY_ASSET_JOIN_UNVERIFIED_WO_SCOPE"}),
            self.event("missing-marker", start=NOW, sources={"scope_evidence":None}))
        result = self.overview()
        self.assertEqual(result["summary"]["maintenance_activity_7d"], 1)
        self.assertEqual(result["activity_evidence"]["unknown_source_scope_work_orders"], 2)
        self.assertEqual(result["activity_evidence"]["availability"], "PARTIAL")

    def test_latest_asset_assignment_precedes_registry_join(self):
        self.add_asset("TECH", registered=False)
        self.add(self.event("old", work_order="SAME", start=NOW, changed=NOW-timedelta(days=1)),
                 self.event("new", work_order="SAME", start=NOW, asset="TECH"))
        self.assertEqual(self.overview()["summary"]["maintenance_activity_7d"], 0)

    def test_missing_identity_never_turns_canonical_event_rows_into_work_orders(self):
        self.add(self.event("missing", work_order=None, start=NOW),
            self.event("source-number", work_order=None, start=NOW, sources={"wonum":"RETAINED-123"}),
            self.event("source-number-copy", work_order=None, start=NOW, sources={"wonum":"RETAINED-123"}))
        result = self.overview()
        self.assertEqual(result["summary"]["maintenance_activity_7d"], 1)
        self.assertEqual(result["activity_evidence"]["unknown_identity_records"], 1)
        self.assertEqual(result["activity_evidence"]["duplicate_records_excluded"], 1)

    def test_api_explicitly_labels_counting_timezone_and_unknown_coverage(self):
        self.add(self.event("missing", task=MISSING))
        response = _decision_overview(self.overview(), 7).model_dump(mode="json")
        self.assertEqual(response["scope"]["timezone"], "Asia/Jakarta")
        self.assertIn("no timestamp fallback", response["scope"]["date_basis"])
        self.assertEqual(response["activity_evidence"]["availability"], "UNAVAILABLE")
        self.assertEqual(len(response["daily_maintenance_activity"]), 7)
        self.assertNotIn("sources", str(response))
        investigation = _maintenance_investigation(self.repository.maintenance_investigation(as_of=NOW))
        self.assertEqual(investigation.activity_evidence.unknown_task_work_orders, 1)
        self.assertEqual(investigation.scope.interpretation, "ACTIVITY_NOT_FAILURE")
        self.assertEqual(investigation.summary.maintenance_events, 0)

    def test_investigation_counts_distinct_eligible_work_orders_only(self):
        self.add(self.event("one", work_order="ONE", start=NOW-timedelta(days=1)),
            self.event("duplicate", work_order="ONE", start=NOW-timedelta(days=1)),
            self.event("two", work_order="TWO", start=NOW), self.event("task", start=NOW, task=True),
            self.event("changed-only", changed=NOW))
        result = self.repository.maintenance_investigation(as_of=NOW)
        self.assertEqual(result["summary"]["maintenance_events"], 2)
        self.assertEqual(result["summary"]["repeat_activity_events"], 1)
        self.assertEqual(result["assets"][0]["latest_gap_days"], 1)
        self.assertEqual(result["assets"][0]["event_count"], 2)

    def test_postgres_query_has_scope_dedup_and_json_boolean_type_guard(self):
        database = SimpleNamespace(engine=SimpleNamespace(dialect=SimpleNamespace(name="postgresql")))
        statement = select(latest_registered_work_orders(database))
        sql = str(statement.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds":True}))
        self.assertIn("jsonb_typeof", sql)
        self.assertIn("row_number() OVER", sql)
        self.assertIn("reliability_asset_registry.site_code = 'BSR'", sql)
        self.assertNotIn("AS BOOLEAN", sql)  # malformed marker must not cause a cast failure
        self.assertNotIn("coalesce(ranked_work_orders.actual_start", sql.lower())


if __name__ == "__main__":
    unittest.main()
