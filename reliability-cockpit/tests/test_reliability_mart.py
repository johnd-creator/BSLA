"""Hermetic tests for the MX-010R Reliability Mart read boundary."""

from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import insert
from sqlalchemy.orm import Session

from src.api import reliability as reliability_api
from src.api.app import create_app
from src.config import MartDbConfig
from src.repositories.mart_database import MartDatabase, ReadOnlySession
from src.repositories.mart_models import (
    AssetHealthAssessmentMart,
    AssetMasterMart,
    FmeaAssessmentMart,
    MaintenanceEventMart,
    MartBase,
    OverhaulEventMart,
    RcfaAnalysisMart,
    ReliabilityAssetRegistryMart,
)
from src.repositories.mart_reader import MartQueryRepository
from src.services.reliability import ReliabilityQueryService
from src.services.registered_maintenance_overview import registered_maintenance_overview


NOW = datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc)
ASSET_A = "asset:MAXIMO:MXASSET:BSR:IP:ASSET-A"
ASSET_B = "asset:MAXIMO:MXASSET:BSR:IP:ASSET-B"
TECHNICAL_ASSET = "asset:MAXIMO:MXASSET:BSR:IP:TECHNICAL"


def _common(canonical_id: str, entity: str) -> dict:
    return {
        "canonical_id": canonical_id,
        "contract_version": "1.0",
        "site_code": "BSR",
        "organization_code": "IP",
        "provenance": {
            "source_system": "MAXIMO",
            "source_application": "RELIABILITY",
            "source_object": entity,
            "source_record_id": f"synthetic-{entity}",
            "source_site": "BSR",
            "source_organization": "IP",
        },
        "relationship_evidence": {},
        "sources": {"maximo": {"source_object": entity}},
        "mart_created_at": NOW,
        "mart_updated_at": NOW,
    }


class ReliabilityMartReadTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.database = MartDatabase(MartDbConfig(dsn="sqlite+pysqlite:///:memory:"))
        MartBase.metadata.create_all(cls.database.engine)
        with Session(cls.database.engine) as session:
            session.add_all([
                AssetMasterMart(**_common(ASSET_A, "MXASSET"), source_asset_number="ASSET-A", description="Synthetic asset A", status="OPERATING", asset_type="PUMP", unit="UNIT-A", source_updated_at=NOW),
                AssetMasterMart(**_common(ASSET_B, "MXASSET"), source_asset_number="ASSET-B", description="Synthetic asset B", status="IDLE", asset_type="MOTOR", unit="UNIT-B", source_updated_at=NOW),
                AssetMasterMart(**_common(TECHNICAL_ASSET, "MXASSET"), source_asset_number="TECHNICAL", description="Technical context", status="OPERATING", asset_type="COMPONENT", unit="UNIT-A", source_updated_at=NOW),
                ReliabilityAssetRegistryMart(asset_ref=ASSET_A, source_asset_number="ASSET-A", site_code="BSR", organization_code="IP", registry_source="MAXIMO_LIST_OF_ASSETS", snapshot_sha256="a" * 64, snapshot_row_count=2, snapshot_imported_at=NOW),
                ReliabilityAssetRegistryMart(asset_ref=ASSET_B, source_asset_number="ASSET-B", site_code="BSR", organization_code="IP", registry_source="MAXIMO_LIST_OF_ASSETS", snapshot_sha256="a" * 64, snapshot_row_count=2, snapshot_imported_at=NOW),
                AssetMasterMart(**_common("asset:OTHER:OTHER", "MXASSET") | {"site_code": "OTHER", "organization_code": "OTHER", "source_asset_number": "OUTSIDE"}),
                MaintenanceEventMart(**_common("maintenance:EVENT-A", "MXWODETAIL"), id="EVENT-A", equipment_id=ASSET_A, work_order_id="WO-REF-A", event_type="CORRECTIVE", status="COMPLETE", actual_start=NOW, actual_finish=NOW, source_changed_at=NOW),
                MaintenanceEventMart(**_common("maintenance:EVENT-B", "MXWODETAIL"), id="EVENT-B", equipment_id=ASSET_B, work_order_id="WO-REF-B", event_type="PM", status="CAN", actual_start=None, actual_finish=None, source_changed_at=NOW),
                FmeaAssessmentMart(**_common("fmea:FMEA-A", "IPFMEA"), source_record_id="FMEA-A", source_number="FMEA-N-A", revision="1", lifecycle_status="ACTIVE", description="Synthetic FMEA", asset_ref=ASSET_A, failure_code_ref="FC-A", source_updated_at=NOW, status_changed_at=NOW),
                AssetHealthAssessmentMart(**_common("bhm:BHM-A", "IPBHM"), source_record_id="BHM-A", revision="1", lifecycle_status="ACTIVE", description="Synthetic health", function_description="Synthetic function", asset_ref=ASSET_A, source_created_at=NOW, source_updated_at=NOW, status_changed_at=NOW),
                OverhaulEventMart(**_common("oh:OH-A", "IP_DOM_OH"), source_record_id="OH-A", source_number="OH-N-A", lifecycle_status="COMPLETE", workorder_ref="WO-REF-A", asset_ref=ASSET_A, planned_start_at=NOW, actual_start_at=NOW, progress=100, source_created_at=NOW, source_updated_at=NOW, unresolved_source_attributes={"performance_test": None}),
                OverhaulEventMart(**_common("oh:OH-MISSING", "IP_DOM_OH"), source_record_id="OH-MISSING", source_number="OH-N-MISSING", lifecycle_status="OPEN", workorder_ref="WO-MISSING", asset_ref=None, planned_start_at=NOW, source_created_at=NOW, source_updated_at=NOW),
                RcfaAnalysisMart(**_common("rcfa:RCFA-A", "IPRCFA"), source_record_id="RCFA-A", source_number="RCFA-N-A", lifecycle_status="OPEN", category="ROOT", asset_ref=None, location_ref=None, workorder_ref=None, failure_event_ref=None, source_created_at=NOW, requested_at=NOW),
            ])
            session.commit()
        cls.repository = MartQueryRepository(cls.database)
        cls.service = ReliabilityQueryService(cls.repository)

    def test_asset_scope_and_pagination(self):
        page = self.repository.list_assets(limit=1)
        self.assertEqual(page.total, 2)
        self.assertEqual(len(page.items), 1)
        self.assertTrue(page.has_more)
        self.assertIsNone(self.repository.get_asset("asset:OTHER:OTHER"))
        self.assertIsNone(self.repository.get_asset(TECHNICAL_ASSET))

    def test_entity_filters_and_latest_health(self):
        self.assertEqual(self.repository.list_maintenance(asset_ref=ASSET_A).total, 1)
        self.assertEqual(self.repository.list_maintenance(work_order_id="WO-REF-A").total, 1)
        self.assertEqual(self.repository.list_fmea(asset_ref=ASSET_A).total, 1)
        self.assertEqual(self.repository.list_health(asset_ref=ASSET_A).total, 1)
        self.assertEqual(self.repository.latest_health(ASSET_A).canonical_id, "bhm:BHM-A")
        self.assertEqual(self.repository.list_overhauls(asset_ref=ASSET_A).total, 1)
        self.assertEqual(self.repository.list_overhauls(workorder_ref="WO-MISSING").total, 1)
        self.assertEqual(self.repository.list_rcfa(category="ROOT").total, 1)

    def test_timeline_is_bounded_vendor_neutral_and_excludes_rcfa(self):
        timeline = self.service.timeline(ASSET_A, limit=50)
        self.assertEqual(timeline.total, 4)
        self.assertEqual({event.event_type for event in timeline.items}, {"MAINTENANCE", "FMEA", "ASSET_HEALTH", "OVERHAUL"})
        self.assertNotIn("IPRCFA", {event.event_type for event in timeline.items})

    def test_context_does_not_invent_rcfa_relationship(self):
        context = self.service.asset_context(ASSET_A)
        self.assertEqual(context["rcfa_relationship_status"], "UNRESOLVED")
        self.assertEqual(len(context["maintenance"].items), 1)
        self.assertEqual(len(context["fmea"].items), 1)

    def test_integrity_counts_resolved_and_unresolved_logical_refs(self):
        result = self.repository.integrity_summary()
        self.assertEqual(result["asset_refs_total"], 5)
        self.assertEqual(result["asset_refs_resolved"], 5)
        self.assertEqual(result["asset_refs_unresolved"], 0)
        self.assertEqual(result["workorder_refs_total"], 2)
        self.assertEqual(result["workorder_refs_resolved"], 1)
        self.assertEqual(result["workorder_refs_unresolved"], 1)
        self.assertEqual(result["registered_assets_total"], 2)
        self.assertEqual(result["registered_assets_resolved"], 2)
        self.assertEqual(result["maintenance_registered_total"], 2)

    def test_maintenance_date_filter_falls_back_to_source_changed_at(self):
        self.assertEqual(self.repository.list_maintenance(date_from=NOW).total, 2)

    def test_registry_summary_is_aggregate_only(self):
        result = self.repository.registry_summary()
        self.assertEqual(result["registered_asset_count"], 2)
        self.assertEqual(result["snapshot_row_count"], 2)
        self.assertNotIn("asset_ref", result)

    def test_decision_overview_is_registry_scoped_and_backend_aggregated(self):
        result = self.repository.decision_overview(window_days=30, as_of=NOW)
        self.assertEqual(result["registered_assets"], 2)
        self.assertEqual(result["summary"]["maintenance_activity_7d"], 1)
        self.assertEqual(result["summary"]["maintenance_activity_30d"], 1)
        self.assertEqual(result["summary"]["assets_active_7d"], 1)
        self.assertEqual(result["summary"]["assets_active_30d"], 1)
        self.assertEqual(len(result["trend"]), 12)
        self.assertEqual({row["value"] for row in result["status_distribution"]}, {"COMPLETE"})
        self.assertEqual({row["value"] for row in result["work_type_distribution"]}, {"CORRECTIVE"})
        self.assertEqual([row["source_asset_number"] for row in result["activity_concentration"]], ["ASSET-A"])
        self.assertEqual(result["records"]["fmea_records"], 1)
        self.assertEqual(result["records"]["fmea_assets_represented"], 1)
        self.assertNotIn("rcfa_assets_represented", result["records"])
        with Session(self.database.engine) as session:
            session.add(MaintenanceEventMart(**_common("maintenance:EVENT-UNKNOWN", "MXWODETAIL"), id="EVENT-UNKNOWN", equipment_id=ASSET_A, actual_start=NOW, source_changed_at=NOW))
            session.flush()
            unknown_result = self.repository.decision_overview(window_days=30, as_of=NOW)
            session.rollback()
        self.assertIn({"value": "UNKNOWN", "count": 1}, unknown_result["status_distribution"])
        self.assertIn({"value": "UNKNOWN", "count": 1}, unknown_result["work_type_distribution"])

    def test_work_order_reference_uses_scoped_work_order_field(self):
        rows = self.repository.list_maintenance(work_order_id="WO-REF-A").items
        self.assertEqual(rows[0].canonical_id, "maintenance:EVENT-A")
        self.assertNotEqual(rows[0].canonical_id, "WO-REF-A")

    def test_read_only_facade_blocks_dml(self):
        with self.database.read_session() as session:
            self.assertIsInstance(session, ReadOnlySession)
            with self.assertRaises(RuntimeError):
                session.execute(insert(AssetMasterMart).values(canonical_id="blocked"))
            with self.assertRaises(AttributeError):
                session.commit  # type: ignore[attr-defined]


class RegisteredMaintenanceOverviewTest(unittest.TestCase):
    def setUp(self):
        self.database = MartDatabase(MartDbConfig(dsn="sqlite+pysqlite:///:memory:"))
        MartBase.metadata.create_all(self.database.engine)
        self.repository = MartQueryRepository(self.database)
        with Session(self.database.engine) as session:
            for i in range(30):
                number = f"SYNTHETIC-{i:02d}"
                asset = f"asset:MAXIMO:MXASSET:BSR:IP:{number}"
                session.add(AssetMasterMart(**_common(asset, "MXASSET"), source_asset_number=number, description=number))
                session.add(ReliabilityAssetRegistryMart(asset_ref=asset, source_asset_number=number, site_code="BSR", organization_code="IP", registry_source="SYNTHETIC", snapshot_sha256="a"*64, snapshot_row_count=30, snapshot_imported_at=NOW))
                if i < 29:session.add(MaintenanceEventMart(**_common(f"maintenance:{i}", "MXWODETAIL"), id=str(i), equipment_id=asset, actual_start=NOW))
            for i in range(3):
                session.add(MaintenanceEventMart(**_common(f"maintenance:repeat-{i}", "MXWODETAIL"), id=f"repeat-{i}", equipment_id="asset:MAXIMO:MXASSET:BSR:IP:SYNTHETIC-00", actual_start=None, source_changed_at=NOW+timedelta(days=1)))
            foreign = "asset:MAXIMO:MXASSET:OTHER:IP:FOREIGN"
            session.add(ReliabilityAssetRegistryMart(asset_ref=foreign, source_asset_number="FOREIGN", site_code="OTHER", organization_code="IP", registry_source="SYNTHETIC", snapshot_sha256="a"*64, snapshot_row_count=1, snapshot_imported_at=NOW))
            for i, asset in enumerate([foreign, TECHNICAL_ASSET, "asset:MAXIMO:MXASSET:BSR:IP:SYNTHETIC-00"]):
                fields = _common(f"maintenance:excluded-{i}", "MXWODETAIL")
                if i == 2:fields["organization_code"] = "OTHER"
                session.add(MaintenanceEventMart(**fields, id=f"excluded-{i}", equipment_id=asset, actual_start=NOW))
            session.commit()

    def tearDown(self):self.database.engine.dispose()

    def test_full_registry_counts_and_top_ten_exclude_unregistered_foreign_and_wrong_wo_scope(self):
        result = registered_maintenance_overview(self.database)
        self.assertEqual(result["summary"], {"registered_assets":30,"maintenance_events":32,"assets_with_maintenance":29})
        self.assertEqual(result["scope"]["kind"], "REGISTERED_BSR_IP")
        self.assertEqual(len(result["assets"]), 10)
        self.assertEqual(result["assets"][0]["maintenance_events"], 4)
        self.assertEqual(result["assets"][0]["latest_retained_activity"].replace(tzinfo=timezone.utc), NOW+timedelta(days=1))
        self.assertNotIn("SYNTHETIC-29", [r["source_asset_number"] for r in result["assets"]])
        self.assertTrue(all("SYNTHETIC-" in row["canonical_id"] for row in result["assets"]))
        self.assertEqual(self.repository.list_assets(offset=20, limit=10).total, 30)
        self.assertEqual(len(self.repository.list_assets(offset=20, limit=10).items), 10)
        self.assertIsNone(self.repository.get_asset(TECHNICAL_ASSET))
        body = reliability_api.registered_maintenance_overview(service=ReliabilityQueryService(self.repository))
        self.assertEqual(body.summary.maintenance_events, 32)
        self.assertEqual(body.operational_kpis, "NOT_ELIGIBLE")

    def test_queries_are_aggregate_only_and_never_touch_unrelated_domains(self):
        from sqlalchemy import event
        statements = []
        def record(conn, cursor, statement, parameters, context, executemany):statements.append(statement.lower())
        event.listen(self.database.engine, "before_cursor_execute", record)
        try:
            with patch.object(self.repository, "integrity_summary", side_effect=AssertionError("unrelated query")), patch.object(self.repository, "decision_overview", side_effect=AssertionError("ADMIN query")):
                registered_maintenance_overview(self.database)
        finally:event.remove(self.database.engine, "before_cursor_execute", record)
        self.assertEqual(len(statements), 5)
        for sql in statements:
            self.assertTrue(sql.lstrip().startswith("select"))
            for table in ["fmea_assessment","asset_health_assessment","rcfa_analysis","overhaul_event","asset_af_mapping"]:self.assertNotIn(table, sql)
            self.assertIn("reliability_asset_registry", sql)
        self.assertTrue(any("limit" in statement for statement in statements))

    def test_empty_registry_returns_zero_without_placeholder_rows(self):
        empty = MartDatabase(MartDbConfig(dsn="sqlite+pysqlite:///:memory:"))
        try:
            MartBase.metadata.create_all(empty.engine)
            result = registered_maintenance_overview(empty)
            self.assertEqual(result["summary"], {"registered_assets":0,"maintenance_events":0,"assets_with_maintenance":0})
            self.assertEqual(result["assets"], [])
        finally:empty.engine.dispose()


class ReliabilityMartApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not hasattr(ReliabilityMartReadTest, "database"):
            ReliabilityMartReadTest.setUpClass()
        cls.database = ReliabilityMartReadTest.database
        cls.app = create_app()
        cls.service = ReliabilityQueryService(MartQueryRepository(cls.database))

    @classmethod
    def tearDownClass(cls) -> None:
        pass

    def test_vendor_neutral_assets_and_legacy_routes_are_present(self):
        body = reliability_api.list_assets(offset=0, limit=1, service=self.service)
        self.assertEqual(body["meta"].total, 2)
        self.assertNotIn("sources", body["items"][0].model_dump())
        paths = self.app.openapi()["paths"]
        self.assertIn("/equipment", paths)
        self.assertIn("/work-orders", paths)
        self.assertIn("/v1/reliability/assets", paths)

    def test_scope_and_filter_safety(self):
        asset_schema = self.app.openapi()["paths"]["/v1/reliability/assets"]["get"]["parameters"]
        site_parameter = next(item for item in asset_schema if item["name"] == "site_code")
        limit_parameter = next(item for item in asset_schema if item["name"] == "limit")
        self.assertEqual(site_parameter["schema"]["const"], "BSR")
        self.assertEqual(limit_parameter["schema"]["maximum"], 200)
        with self.assertRaises(HTTPException) as error:
            reliability_api.rcfa(asset_ref=ASSET_A, service=self.service)
        self.assertEqual(error.exception.status_code, 422)

    def test_context_timeline_and_unresolved_overhaul(self):
        context = reliability_api.asset_context(ASSET_A, service=self.service)
        self.assertEqual(context.rcfa_relationship_status, "UNRESOLVED")
        timeline = reliability_api.asset_timeline(ASSET_A, offset=0, limit=50, service=self.service)["items"]
        self.assertEqual(len(timeline), 4)
        overhauls = reliability_api.overhauls(workorder_ref="WO-MISSING", offset=0, limit=50, service=self.service)
        self.assertIsNone(overhauls["items"][0].asset_ref)

    def test_missing_asset_is_404_and_integrity_is_aggregate_only(self):
        with self.assertRaises(HTTPException) as error:
            reliability_api.get_asset("not-found", service=self.service)
        self.assertEqual(error.exception.status_code, 404)
        body = reliability_api.integrity(service=self.service).model_dump()
        self.assertEqual(body["workorder_refs_unresolved"], 1)
        self.assertNotIn("canonical_id", body)
        with self.assertRaises(HTTPException) as technical_error:
            reliability_api.get_asset(TECHNICAL_ASSET, service=self.service)
        self.assertEqual(technical_error.exception.status_code, 404)

    def test_registry_endpoint_is_available(self):
        body = reliability_api.registry(service=self.service)
        self.assertEqual(body.registered_asset_count, 2)

    def test_data_trust_overview_keeps_population_and_semantics_separate(self):
        response = reliability_api.data_trust(service=self.service)
        self.assertEqual(response.scope.source_system, "MAXIMO")
        self.assertEqual(response.scope.sync_freshness, "NOT_AVAILABLE")
        self.assertEqual(response.population.registered_reliability_assets, 2)
        self.assertEqual(response.population.registry_resolved, 2)
        self.assertEqual(response.population.registry_unresolved, 0)
        self.assertEqual(response.population.technical_asset_context, 3)
        self.assertEqual(response.population.maintenance_total, 2)
        self.assertEqual(response.population.registry_maintenance, 2)
        self.assertEqual({domain.domain for domain in response.domains}, {"ASSET", "MAINTENANCE", "FMEA", "ASSET_HEALTH", "RCFA", "OVERHAUL"})
        relationships = {row.relationship: row for row in response.relationships}
        self.assertEqual(relationships["RCFA → Asset"].evidence, "UNRESOLVED")
        self.assertEqual(relationships["Overhaul Work Order → local maintenance_event"].resolved_count, 1)
        readiness = {row.capability: row for row in response.semantic_readiness}
        self.assertEqual(readiness["Maintenance Activity"].status, "AVAILABLE")
        self.assertEqual(readiness["Health Score"].status, "BLOCKED")
        self.assertEqual(readiness["PdM alerts"].status, "NOT_AVAILABLE")
        self.assertEqual(readiness["Recommendations"].status, "DEFERRED")
        self.assertTrue(any("not mean the source system is defective" in limitation for limitation in response.limitations))

    def test_data_trust_empty_mart_is_factual(self):
        empty_database = MartDatabase(MartDbConfig(dsn="sqlite+pysqlite:///:memory:"))
        MartBase.metadata.create_all(empty_database.engine)
        response = reliability_api.data_trust(service=ReliabilityQueryService(MartQueryRepository(empty_database)))
        self.assertEqual(response.population.registered_reliability_assets, 0)
        self.assertEqual(response.population.technical_asset_context, 0)
        self.assertEqual(response.population.maintenance_total, 0)
        self.assertEqual(response.population.fmea, 0)
        self.assertEqual(response.population.asset_health, 0)
        self.assertEqual(response.population.rcfa, 0)
        self.assertEqual(response.population.overhaul, 0)
        self.assertEqual(len(response.domains), 6)
        with patch("src.api.reliability.get_mart_database", side_effect=reliability_api.MartDatabaseConfigError("offline")):
            with self.assertRaises(HTTPException) as error:
                reliability_api._db()
        self.assertEqual(error.exception.status_code, 503)

    def test_decision_overview_endpoint_defaults_to_30d_and_rejects_unbounded_window(self):
        class FixedDateTime(datetime):
            @classmethod
            def now(cls, tz=None):
                return NOW

        with patch("src.repositories.mart_reader.datetime", FixedDateTime):
            response = reliability_api.decision_overview(window_days=30, service=self.service)
        self.assertEqual(response.window_days, 30)
        self.assertEqual(response.summary.registered_assets.evidence_class, "VERIFIED")
        self.assertEqual(response.summary.assets_active_7d.value, 1)
        parameter = self.app.openapi()["paths"]["/v1/reliability/decision-overview"]["get"]["parameters"][0]
        self.assertEqual(parameter["schema"]["enum"], [7, 30, 90])
        for invalid in (0, 14, 180, 365):
            with self.assertRaises(HTTPException) as error:
                reliability_api.decision_overview(window_days=invalid, service=self.service)
            self.assertEqual(error.exception.status_code, 422)
        parameters = self.app.openapi()["paths"]["/v1/reliability/maintenance-investigation"]["get"]["parameters"]
        for name, expected in (("window_days", [30, 90, 180]), ("min_events", [2, 3, 5])):
            self.assertEqual(next(p for p in parameters if p["name"] == name)["schema"]["enum"], expected)


    def test_decision_overview_returns_503_when_mart_is_unavailable(self):
        with patch("src.api.reliability.get_mart_database", side_effect=reliability_api.MartDatabaseConfigError("offline")):
            with self.assertRaises(HTTPException) as error:
                reliability_api._db()
        self.assertEqual(error.exception.status_code, 503)


class OverhaulSemanticsFixtureTest(unittest.TestCase):
    """Synthetic Overhaul rows cover source and local relationship states."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.database = MartDatabase(MartDbConfig(dsn="sqlite+pysqlite:///:memory:"))
        MartBase.metadata.create_all(cls.database.engine)
        with Session(cls.database.engine) as session:
            session.add_all([
                AssetMasterMart(**_common(ASSET_A, "MXASSET"), source_asset_number="ASSET-A", description="Synthetic asset A", status="OPERATING", asset_type="PUMP", unit="UNIT-A", source_updated_at=NOW),
                AssetMasterMart(**_common(TECHNICAL_ASSET, "MXASSET"), source_asset_number="TECHNICAL", description="Technical context", status="OPERATING", asset_type="COMPONENT", unit="UNIT-A", source_updated_at=NOW),
                ReliabilityAssetRegistryMart(asset_ref=ASSET_A, source_asset_number="ASSET-A", site_code="BSR", organization_code="IP", registry_source="SYNTHETIC", snapshot_sha256="c" * 64, snapshot_row_count=1, snapshot_imported_at=NOW),
                MaintenanceEventMart(**_common("maintenance:OH-WO", "MXWODETAIL"), id="OH-WO", equipment_id=ASSET_A, work_order_id="WO-RESOLVED", event_type="PM", status="COMP", actual_start=NOW, source_changed_at=NOW),
                OverhaulEventMart(**(_common("oh:OH-RESOLVED", "IP_DOM_OH") | {"sources": {"maximo": {"wonum": "WO-SOURCE-A"}}}), source_record_id="OH-RESOLVED", source_number="OH-1", lifecycle_status="EKS-COMP", workorder_ref="WO-RESOLVED", asset_ref=ASSET_A, planned_start_at=NOW - timedelta(days=10), planned_finish_at=NOW - timedelta(days=5), actual_start_at=NOW - timedelta(days=9), actual_finish_at=NOW - timedelta(days=4), progress=45.28, source_created_at=NOW - timedelta(days=20), source_updated_at=NOW, unresolved_source_attributes={"inspection_number": "INS-1", "performance_test": "RAW"}),
                OverhaulEventMart(**(_common("oh:OH-MISSING", "IP_DOM_OH") | {"sources": {"maximo": {"wonum": "WO-SOURCE-B"}}}), source_record_id="OH-MISSING", source_number="OH-2", lifecycle_status="OPEN", workorder_ref="WO-MISSING", asset_ref=None, planned_start_at=NOW),
                OverhaulEventMart(**(_common("oh:OH-TECHNICAL", "IP_DOM_OH") | {"sources": {"maximo": {}}}), source_record_id="OH-TECHNICAL", source_number="OH-3", lifecycle_status=None, workorder_ref=None, asset_ref=TECHNICAL_ASSET, progress=None),
            ])
            session.commit()
        cls.repository = MartQueryRepository(cls.database)

    def test_overhaul_overview_separates_source_and_mart_resolution(self):
        result = self.repository.overhaul_overview()
        self.assertEqual(result["summary"]["overhaul_records"], 3)
        self.assertEqual(result["summary"]["records_with_work_order"], 2)
        self.assertEqual(result["summary"]["work_orders_resolved_in_mart"], 1)
        self.assertEqual(result["summary"]["work_orders_unresolved_in_mart"], 1)
        self.assertEqual(result["summary"]["work_order_source_missing"], 1)
        self.assertEqual(result["summary"]["records_with_asset"], 2)
        self.assertEqual(result["summary"]["asset_master_resolved"], 2)
        self.assertEqual(result["summary"]["registered_assets_resolved"], 1)
        self.assertEqual(result["summary"]["technical_non_registry"], 1)
        self.assertEqual(result["summary"]["planned_duration_available"], 1)
        self.assertEqual(result["summary"]["actual_duration_available"], 1)
        self.assertEqual(result["summary"]["records_with_progress"], 1)
        self.assertEqual(result["summary"]["inspection_number_present"], 1)
        self.assertEqual(result["summary"]["performance_test_present"], 1)
        self.assertEqual(result["evidence"]["schedule_variance"], "BUSINESS_SEMANTICS_REQUIRED")

    def test_workspace_exposes_human_source_numbers_and_neutral_states(self):
        resolved = self.repository.list_overhaul_workspace(source_work_order_number="WO-SOURCE-A").items
        self.assertEqual(len(resolved), 1)
        self.assertEqual(resolved[0].source_work_order_number, "WO-SOURCE-A")
        self.assertEqual(resolved[0].work_order_resolution, "SOURCE_LINK_VERIFIED_AND_MART_RESOLVED")
        self.assertEqual(resolved[0].asset_resolution, "ASSET_RESOLVED_REGISTERED")
        self.assertEqual(resolved[0].source_asset_number, "ASSET-A")
        unresolved = self.repository.list_overhaul_workspace(source_work_order_number="WO-SOURCE-B").items
        self.assertEqual(unresolved[0].asset_resolution, "ASSET_UNRESOLVED")
        missing = self.repository.list_overhaul_workspace(source_work_order_number="NO_MATCH")
        self.assertEqual(missing.total, 0)
        by_number = self.repository.list_overhaul_workspace(source_number="OH-2").items
        self.assertEqual(len(by_number), 1)
        self.assertEqual(by_number[0].source_number, "OH-2")


class OverhaulApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not hasattr(OverhaulSemanticsFixtureTest, "database"):
            OverhaulSemanticsFixtureTest.setUpClass()
        cls.database = OverhaulSemanticsFixtureTest.database
        cls.service = ReliabilityQueryService(MartQueryRepository(cls.database))

    def test_overview_and_list_are_typed(self):
        response = reliability_api.overhaul_overview(service=self.service)
        self.assertEqual(response.scope.asset_relationship, "DERIVED_VIA_WORK_ORDER")
        self.assertEqual(response.summary.overhaul_records, 3)
        page = reliability_api.overhauls(source_work_order_number="WO-SOURCE-A", offset=0, limit=50, service=self.service)
        self.assertEqual(page["meta"].total, 1)
        self.assertEqual(page["items"][0].source_work_order_number, "WO-SOURCE-A")
        self.assertEqual(page["items"][0].asset_resolution, "ASSET_RESOLVED_REGISTERED")

    def test_empty_overview_and_mart_unavailable_boundary(self):
        empty_db = MartDatabase(MartDbConfig(dsn="sqlite+pysqlite:///:memory:"))
        MartBase.metadata.create_all(empty_db.engine)
        response = reliability_api.overhaul_overview(service=ReliabilityQueryService(MartQueryRepository(empty_db)))
        self.assertEqual(response.summary.overhaul_records, 0)
        with patch("src.api.reliability.get_mart_database", side_effect=reliability_api.MartDatabaseConfigError("offline")):
            with self.assertRaises(HTTPException) as error:
                reliability_api._db()
        self.assertEqual(error.exception.status_code, 503)


class FmeaSemanticsFixtureTest(unittest.TestCase):
    """Synthetic FMEA evidence for identity, relationship, and raw-value boundaries."""

    A = "asset:MAXIMO:MXASSET:BSR:IP:FMEA-A"
    B = "asset:MAXIMO:MXASSET:BSR:IP:FMEA-B"
    TECHNICAL = "asset:MAXIMO:MXASSET:BSR:IP:FMEA-TECHNICAL"
    UNRESOLVED = "asset:MAXIMO:MXASSET:BSR:IP:FMEA-UNRESOLVED"
    AS_OF = datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc)

    @classmethod
    def setUpClass(cls) -> None:
        cls.database = MartDatabase(MartDbConfig(dsn="sqlite+pysqlite:///:memory:"))
        MartBase.metadata.create_all(cls.database.engine)

        def asset(ref: str, number: str) -> AssetMasterMart:
            return AssetMasterMart(
                **_common(ref, "MXASSET"),
                source_asset_number=number,
                description=f"Synthetic {number}",
                status="OPERATING",
                asset_type="PUMP",
                unit="UNIT-A",
                source_updated_at=cls.AS_OF,
            )

        def registry(ref: str, number: str) -> ReliabilityAssetRegistryMart:
            return ReliabilityAssetRegistryMart(
                asset_ref=ref,
                source_asset_number=number,
                site_code="BSR",
                organization_code="IP",
                registry_source="SYNTHETIC",
                snapshot_sha256="f" * 64,
                snapshot_row_count=2,
                snapshot_imported_at=cls.AS_OF,
            )

        def fmea(
            number: int,
            ref: str | None,
            source_number: str | None,
            revision: str | None,
            status: str | None,
            source_failure_code: str | None,
            *,
            status_changed: datetime | None,
            source_updated: datetime | None,
        ) -> FmeaAssessmentMart:
            sources = {"maximo": {"source_object": "IPFMEA"}}
            if source_failure_code is not None:
                sources["maximo"]["failurecode"] = source_failure_code
            return FmeaAssessmentMart(
                **(_common(f"fmea:FMEA-{number}", "IPFMEA") | {"sources": sources}),
                source_record_id=f"FMEA-{number}",
                source_number=source_number,
                revision=revision,
                lifecycle_status=status,
                description=f"Synthetic FMEA {number}",
                asset_ref=ref,
                failure_code_ref=source_failure_code,
                source_updated_at=source_updated,
                status_changed_at=status_changed,
            )

        with Session(cls.database.engine) as session:
            session.add_all([
                asset(cls.A, "FMEA-A"), asset(cls.B, "FMEA-B"), asset(cls.TECHNICAL, "FMEA-TECHNICAL"),
                registry(cls.A, "FMEA-A"), registry(cls.B, "FMEA-B"),
                fmea(1, cls.A, "FMEA-1", "1", "MONITORED", "FC-A", status_changed=cls.AS_OF - timedelta(days=2), source_updated=cls.AS_OF - timedelta(days=4)),
                fmea(2, cls.A, "FMEA-1", "2", "REVISI", None, status_changed=None, source_updated=cls.AS_OF - timedelta(days=1)),
                fmea(3, cls.A, "FMEA-2", "1", "VER-OK", "FC-B", status_changed=cls.AS_OF - timedelta(days=3), source_updated=cls.AS_OF - timedelta(days=5)),
                fmea(4, cls.B, None, "0", "WAPPR", None, status_changed=None, source_updated=None),
                fmea(5, cls.TECHNICAL, "FMEA-T", "1", "MONITORED", None, status_changed=cls.AS_OF, source_updated=cls.AS_OF),
                fmea(6, cls.UNRESOLVED, "FMEA-U", "1", "UNKNOWN", None, status_changed=cls.AS_OF, source_updated=cls.AS_OF),
                fmea(7, None, "FMEA-N", None, None, None, status_changed=None, source_updated=None),
            ])
            session.commit()
        cls.repository = MartQueryRepository(cls.database)

    def test_overview_measures_registry_relationship_identity_and_raw_values(self):
        result = self.repository.fmea_overview(as_of=self.AS_OF)
        self.assertEqual(result["summary"], {
            "fmea_records": 7,
            "records_with_asset_ref": 6,
            "records_without_asset_ref": 1,
            "asset_master_resolved": 5,
            "registry_resolved": 4,
            "technical_non_registry_records": 1,
            "unresolved_asset_refs": 1,
            "registered_assets_represented": 2,
            "assets_with_multiple_records": 1,
            "maximum_records_per_asset": 3,
            "records_with_failure_code": 2,
            "record_date_available": 5,
        })
        self.assertEqual({row["value"] for row in result["status_distribution"]}, {"MONITORED", "REVISI", "VER-OK", "WAPPR", "UNKNOWN", "UNKNOWN"})
        self.assertEqual({row["value"] for row in result["revision_distribution"]}, {"0", "1", "2", "UNKNOWN"})
        self.assertEqual(result["record_recency"]["latest_record_at"], self.AS_OF)
        self.assertEqual(result["record_recency"]["oldest_record_at"], (self.AS_OF - timedelta(days=3)).replace(tzinfo=None))

    def test_workspace_is_registry_scoped_filters_source_values_and_dates(self):
        page = self.repository.list_fmea_workspace(as_of=self.AS_OF, limit=50)
        self.assertEqual(page.total, 4)
        self.assertEqual({row.source_asset_number for row in page.items}, {"FMEA-A", "FMEA-B"})
        self.assertEqual({row.source_failure_code for row in page.items}, {"FC-A", "FC-B", None})
        latest = self.repository.list_fmea_workspace(asset_number="fmea-a", as_of=self.AS_OF, limit=1).items[0]
        self.assertEqual(latest.source_number, "FMEA-1")
        self.assertEqual(latest.source_record_id, "FMEA-2")
        self.assertEqual(latest.fmea_record_date, (self.AS_OF - timedelta(days=1)).replace(tzinfo=None))
        self.assertAlmostEqual(latest.fmea_age_days, 1.0)
        by_code = self.repository.list_fmea_workspace(source_failure_code="FC-B", as_of=self.AS_OF)
        self.assertEqual(by_code.total, 1)
        by_number = self.repository.list_fmea_workspace(source_number="FMEA-1", as_of=self.AS_OF)
        self.assertEqual(by_number.total, 2)


class FmeaApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not hasattr(FmeaSemanticsFixtureTest, "database"):
            FmeaSemanticsFixtureTest.setUpClass()
        cls.database = FmeaSemanticsFixtureTest.database
        cls.service = ReliabilityQueryService(MartQueryRepository(cls.database))

    def test_overview_and_list_api_are_typed_and_scoped(self):
        response = reliability_api.fmea_overview(service=self.service)
        self.assertEqual(response.scope.interpretation, "ASSESSMENT_RECORDS_NOT_RISK_SCORE")
        self.assertEqual(response.summary.fmea_records, 7)
        self.assertEqual(response.summary.registered_assets_represented, 2)
        self.assertEqual(response.evidence.failure_mode_details, "DATA_NOT_AVAILABLE")
        page = reliability_api.fmea(asset_number="FMEA-A", source_failure_code="FC-A", offset=0, limit=50, service=self.service)
        self.assertEqual(page["meta"].total, 1)
        self.assertEqual(page["items"][0].source_failure_code, "FC-A")

    def test_empty_and_unavailable_boundaries(self):
        empty_db = MartDatabase(MartDbConfig(dsn="sqlite+pysqlite:///:memory:"))
        MartBase.metadata.create_all(empty_db.engine)
        empty_service = ReliabilityQueryService(MartQueryRepository(empty_db))
        response = reliability_api.fmea_overview(service=empty_service)
        self.assertEqual(response.summary.fmea_records, 0)
        self.assertEqual(response.summary.maximum_records_per_asset, 0)
        with patch("src.api.reliability.get_mart_database", side_effect=reliability_api.MartDatabaseConfigError("offline")):
            with self.assertRaises(HTTPException) as error:
                reliability_api._db()
        self.assertEqual(error.exception.status_code, 503)


class RcfaSemanticsFixtureTest(unittest.TestCase):
    """Synthetic global RCFA evidence with no guessed relationships."""

    AS_OF = datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc)

    @classmethod
    def setUpClass(cls) -> None:
        cls.database = MartDatabase(MartDbConfig(dsn="sqlite+pysqlite:///:memory:"))
        MartBase.metadata.create_all(cls.database.engine)

        def rcfa(number: int, source_number: str | None, revision: str | None, status: str | None, category: str | None, requested: datetime | None) -> RcfaAnalysisMart:
            return RcfaAnalysisMart(
                **_common(f"rcfa:RCFA-{number}", "IPRCFA"),
                source_record_id=f"RCFA-{number}",
                source_number=source_number,
                revision=revision,
                lifecycle_status=status,
                category=category,
                asset_ref=None,
                location_ref=None,
                workorder_ref=None,
                failure_event_ref=None,
                source_created_at=None,
                requested_at=requested,
            )

        with Session(cls.database.engine) as session:
            session.add_all([
                rcfa(1, "RCFA-1", "0", "CLOSE", "1", cls.AS_OF - timedelta(days=3)),
                rcfa(2, "RCFA-2", "0", "OPEN", "1", cls.AS_OF - timedelta(days=2)),
                rcfa(3, "RCFA-2", "1", "REVISI", None, None),
                rcfa(4, "RCFA-3", "1", "CLOSE", "2", cls.AS_OF),
                rcfa(5, "RCFA-4", "2", None, "2", cls.AS_OF - timedelta(days=1)),
                rcfa(6, "RCFA-5", "0", "CLOSE", "3", None),
            ])
            session.commit()
        cls.repository = MartQueryRepository(cls.database)

    def test_overview_is_global_and_relationship_safe(self):
        result = self.repository.rcfa_overview(as_of=self.AS_OF)
        self.assertEqual(result["summary"], {
            "rcfa_records": 6,
            "records_with_category": 5,
            "records_with_revision": 6,
            "records_with_requested_at": 4,
            "records_with_source_created_at": 0,
            "record_date_available": 4,
        })
        self.assertEqual({row["value"] for row in result["status_distribution"]}, {"CLOSE", "OPEN", "REVISI", "UNKNOWN"})
        self.assertEqual({row["value"] for row in result["category_distribution"]}, {"1", "2", "3", "UNKNOWN"})
        self.assertEqual({row["value"] for row in result["revision_distribution"]}, {"0", "1", "2"})
        self.assertEqual(result["scope"]["asset_relationship"], "UNRESOLVED")
        self.assertEqual(result["record_recency"]["latest_record_at"].replace(tzinfo=None), self.AS_OF.replace(tzinfo=None))
        self.assertEqual(result["evidence"]["request_to_created_gap"], "DATA_NOT_AVAILABLE")

    def test_workspace_filters_paginates_and_exposes_no_relationship(self):
        page = self.repository.list_rcfa_workspace(as_of=self.AS_OF, offset=0, limit=2)
        self.assertEqual(page.total, 6)
        self.assertTrue(page.has_more)
        self.assertTrue(all(row.asset_ref is None and row.workorder_ref is None and row.failure_event_ref is None for row in page.items))
        status = self.repository.list_rcfa_workspace(lifecycle_status="CLOSE", as_of=self.AS_OF)
        self.assertEqual(status.total, 3)
        category = self.repository.list_rcfa_workspace(category="2", as_of=self.AS_OF)
        self.assertEqual(category.total, 2)
        number = self.repository.list_rcfa_workspace(source_number="RCFA-2", as_of=self.AS_OF)
        self.assertEqual(number.total, 2)
        latest = self.repository.list_rcfa_workspace(as_of=self.AS_OF, limit=1).items[0]
        self.assertEqual(latest.source_number, "RCFA-3")
        self.assertEqual(latest.rcfa_record_date, self.AS_OF.replace(tzinfo=None))
        self.assertAlmostEqual(latest.rcfa_age_days, 0.0)


class RcfaApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not hasattr(RcfaSemanticsFixtureTest, "database"):
            RcfaSemanticsFixtureTest.setUpClass()
        cls.database = RcfaSemanticsFixtureTest.database
        cls.service = ReliabilityQueryService(MartQueryRepository(cls.database))

    def test_overview_and_list_api_are_typed(self):
        response = reliability_api.rcfa_overview(service=self.service)
        self.assertEqual(response.scope.interpretation, "GLOBAL_RCFA_RECORDS")
        self.assertEqual(response.summary.rcfa_records, 6)
        self.assertEqual(response.evidence.asset_relationship, "DATA_NOT_AVAILABLE")
        page = reliability_api.rcfa(lifecycle_status="CLOSE", category="1", offset=0, limit=50, service=self.service)
        self.assertEqual(page["meta"].total, 1)
        self.assertEqual(page["items"][0].relationship_status, "UNRESOLVED")
        self.assertIsNone(page["items"][0].asset_ref)

    def test_asset_filter_is_rejected_and_empty_boundary_is_safe(self):
        with self.assertRaises(HTTPException) as error:
            reliability_api.rcfa(asset_ref="asset:synthetic", service=self.service)
        self.assertEqual(error.exception.status_code, 422)
        empty_db = MartDatabase(MartDbConfig(dsn="sqlite+pysqlite:///:memory:"))
        MartBase.metadata.create_all(empty_db.engine)
        response = reliability_api.rcfa_overview(service=ReliabilityQueryService(MartQueryRepository(empty_db)))
        self.assertEqual(response.summary.rcfa_records, 0)
        self.assertIsNone(response.record_recency.latest_record_at)
        with patch("src.api.reliability.get_mart_database", side_effect=reliability_api.MartDatabaseConfigError("offline")):
            with self.assertRaises(HTTPException) as error:
                reliability_api._db()
        self.assertEqual(error.exception.status_code, 503)


class MaintenanceInvestigationFixtureTest(unittest.TestCase):
    """Synthetic repeat-activity evidence for the SQL aggregation boundary."""

    A = "asset:MAXIMO:MXASSET:BSR:IP:INV-A"
    B = "asset:MAXIMO:MXASSET:BSR:IP:INV-B"
    C = "asset:MAXIMO:MXASSET:BSR:IP:INV-C"
    TECHNICAL = "asset:MAXIMO:MXASSET:BSR:IP:INV-TECHNICAL"

    @classmethod
    def setUpClass(cls) -> None:
        cls.database = MartDatabase(MartDbConfig(dsn="sqlite+pysqlite:///:memory:"))
        MartBase.metadata.create_all(cls.database.engine)
        def asset(ref: str, number: str) -> AssetMasterMart:
            return AssetMasterMart(
                **_common(ref, "MXASSET"),
                source_asset_number=number,
                description=f"Synthetic {number}",
                status="OPERATING",
                asset_type="PUMP",
                unit="UNIT-A",
                source_updated_at=NOW,
            )

        def registry(ref: str, number: str) -> ReliabilityAssetRegistryMart:
            return ReliabilityAssetRegistryMart(
                asset_ref=ref,
                source_asset_number=number,
                site_code="BSR",
                organization_code="IP",
                registry_source="SYNTHETIC",
                snapshot_sha256="b" * 64,
                snapshot_row_count=3,
                snapshot_imported_at=NOW,
            )

        def event(
            number: int,
            ref: str,
            days_ago: int | None,
            *,
            raw_work_type: str | None,
            event_type: str | None,
            actual_start: datetime | None = None,
            source_changed_at: datetime | None = None,
        ) -> MaintenanceEventMart:
            sources = {"maximo": {"source_object": "MXWODETAIL"}}
            if raw_work_type is not None:
                sources["maximo"]["worktype"] = raw_work_type
            activity = NOW - timedelta(days=days_ago) if days_ago is not None else None
            return MaintenanceEventMart(
                **(_common(f"maintenance:INV-{number}", "MXWODETAIL") | {"sources": sources}),
                id=f"INV-{number}",
                equipment_id=ref,
                work_order_id=f"WO-INV-{number}",
                event_type=event_type,
                status="CAN" if number == 6 else "CLOSE",
                actual_start=actual_start if actual_start is not None else activity,
                actual_finish=None,
                source_changed_at=source_changed_at if source_changed_at is not None else activity,
            )

        with Session(cls.database.engine) as session:
            session.add_all([asset(cls.A, "INV-A"), asset(cls.B, "INV-B"), asset(cls.C, "INV-C"), asset(cls.TECHNICAL, "INV-TECHNICAL")])
            session.add_all([registry(cls.A, "INV-A"), registry(cls.B, "INV-B"), registry(cls.C, "INV-C")])
            session.add_all([
                event(1, cls.A, 5, raw_work_type="PM", event_type="PM"),
                event(2, cls.A, 10, raw_work_type="PDM", event_type=None),
                event(3, cls.A, 20, raw_work_type="PDM", event_type=None),
                event(4, cls.A, 30, raw_work_type="CD", event_type=None),
                event(5, cls.A, 40, raw_work_type=None, event_type=None),
                event(6, cls.B, 15, raw_work_type="CM", event_type="CM"),
                event(7, cls.B, 25, raw_work_type="CM", event_type="CM"),
                event(8, cls.C, 100, raw_work_type="PM", event_type="PM", actual_start=NOW - timedelta(days=15), source_changed_at=NOW - timedelta(days=100)),
                event(9, cls.TECHNICAL, 5, raw_work_type="PM", event_type="PM"),
                event(10, cls.A, None, raw_work_type="PM", event_type="PM", actual_start=None, source_changed_at=None),
            ])
            session.commit()
        cls.repository = MartQueryRepository(cls.database)

    def test_repeat_activity_counts_and_registry_scope(self):
        result = self.repository.maintenance_investigation(window_days=90, min_events=2, as_of=NOW)
        self.assertEqual(result["summary"], {
            "registered_assets": 3,
            "maintenance_events": 8,
            "assets_with_activity": 3,
            "assets_with_2plus_events": 2,
            "assets_with_3plus_events": 1,
            "repeat_activity_events": 5,
        })
        self.assertEqual([row["source_asset_number"] for row in result["assets"]], ["INV-A", "INV-B"])
        self.assertEqual(result["assets"][0]["event_count"], 5)
        self.assertEqual(result["assets"][0]["repeat_activity_events"], 4)
        self.assertEqual(result["assets"][1]["event_count"], 2)
        self.assertEqual(result["assets"][1]["repeat_activity_events"], 1)

    def test_activity_date_preference_gaps_and_work_types(self):
        result = self.repository.maintenance_investigation(window_days=180, min_events=2, as_of=NOW)
        first = result["assets"][0]
        self.assertEqual(first["latest_work_type"], "PM")
        self.assertEqual(first["dominant_work_type"], "PDM")
        self.assertAlmostEqual(first["latest_gap_days"], 5.0)
        self.assertAlmostEqual(first["minimum_gap_days"], 5.0)

        thirty_day = self.repository.maintenance_investigation(window_days=30, min_events=2, as_of=NOW)
        self.assertEqual(thirty_day["summary"]["maintenance_events"], 7)
        self.assertEqual(thirty_day["summary"]["assets_with_activity"], 3)

        overview = self.repository.decision_overview(window_days=90, as_of=NOW)
        self.assertEqual({row["value"] for row in overview["work_type_distribution"]}, {"PM", "PDM", "CD", "CM", "UNKNOWN"})
        self.assertEqual(sum(row["count"] for row in overview["work_type_distribution"]), 8)
        self.assertIn({"value": "CAN", "count": 1}, overview["status_distribution"])

    def test_allowlisted_thresholds_pagination_and_sort(self):
        result = self.repository.maintenance_investigation(window_days=30, min_events=3, offset=0, limit=1, sort="latest_gap_asc", as_of=NOW)
        self.assertEqual(result["meta"], {"total": 1, "offset": 0, "limit": 1, "has_more": False})
        self.assertEqual(result["assets"][0]["source_asset_number"], "INV-A")
        with self.assertRaises(ValueError):
            self.repository.maintenance_investigation(window_days=7, as_of=NOW)
        with self.assertRaises(ValueError):
            self.repository.maintenance_investigation(min_events=4, as_of=NOW)


class MaintenanceInvestigationApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not hasattr(MaintenanceInvestigationFixtureTest, "database"):
            MaintenanceInvestigationFixtureTest.setUpClass()
        cls.database = MaintenanceInvestigationFixtureTest.database
        cls.service = ReliabilityQueryService(MartQueryRepository(cls.database))

    def test_api_default_and_allowlisted_windows(self):
        class FixedDateTime(datetime):
            @classmethod
            def now(cls, tz=None):
                return NOW

        with patch("src.repositories.mart_reader.datetime", FixedDateTime):
            response = reliability_api.maintenance_investigation(window_days=90, min_events=2, offset=0, limit=25, sort="event_count_desc", service=self.service)
        self.assertEqual(response.window.days, 90)
        self.assertEqual(response.summary.repeat_activity_events, 5)
        self.assertEqual(response.scope.interpretation, "ACTIVITY_NOT_FAILURE")
        for days in (30, 90, 180):
            with patch("src.repositories.mart_reader.datetime", FixedDateTime):
                response = reliability_api.maintenance_investigation(window_days=days, min_events=2, offset=0, limit=25, sort="event_count_desc", service=self.service)
            self.assertEqual(response.window.days, days)

    def test_api_validation_and_503_boundary(self):
        with self.assertRaises(HTTPException) as error:
            reliability_api.maintenance_investigation(window_days=7, service=self.service)
        self.assertEqual(error.exception.status_code, 422)
        with self.assertRaises(HTTPException) as error:
            reliability_api.maintenance_investigation(window_days=90, min_events=4, offset=0, limit=25, sort="event_count_desc", service=self.service)
        self.assertEqual(error.exception.status_code, 422)
        with patch("src.api.reliability.get_mart_database", side_effect=reliability_api.MartDatabaseConfigError("offline")):
            with self.assertRaises(HTTPException) as error:
                reliability_api._db()
        self.assertEqual(error.exception.status_code, 503)


class AssetHealthSemanticsFixtureTest(unittest.TestCase):
    A = "asset:MAXIMO:MXASSET:BSR:IP:HEALTH-A"
    B = "asset:MAXIMO:MXASSET:BSR:IP:HEALTH-B"
    TECHNICAL = "asset:MAXIMO:MXASSET:BSR:IP:HEALTH-TECHNICAL"
    UNRESOLVED = "asset:MAXIMO:MXASSET:BSR:IP:HEALTH-UNRESOLVED"
    AS_OF = datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc)

    @classmethod
    def setUpClass(cls) -> None:
        cls.database = MartDatabase(MartDbConfig(dsn="sqlite+pysqlite:///:memory:"))
        MartBase.metadata.create_all(cls.database.engine)

        def asset(ref: str, number: str) -> AssetMasterMart:
            return AssetMasterMart(
                **_common(ref, "MXASSET"),
                source_asset_number=number,
                description=f"Synthetic {number}",
                status="OPERATING",
                asset_type="PUMP",
                unit="UNIT-A",
                source_updated_at=cls.AS_OF,
            )

        def registry(ref: str, number: str) -> ReliabilityAssetRegistryMart:
            return ReliabilityAssetRegistryMart(
                asset_ref=ref,
                source_asset_number=number,
                site_code="BSR",
                organization_code="IP",
                registry_source="SYNTHETIC",
                snapshot_sha256="c" * 64,
                snapshot_row_count=2,
                snapshot_imported_at=cls.AS_OF,
            )

        def health(
            number: int,
            ref: str | None,
            *,
            status: str | None,
            revision: str | None,
            created: datetime | None,
            updated: datetime | None,
            status_changed: datetime | None,
        ) -> AssetHealthAssessmentMart:
            sources = {"maximo": {"source_object": "IPBHM", "eid": f"EID-{number}"}}
            return AssetHealthAssessmentMart(
                **(_common(f"bhm:HEALTH-{number}", "IPBHM") | {"sources": sources}),
                source_record_id=f"BHM-{number}",
                revision=revision,
                lifecycle_status=status,
                description=f"Assessment description {number}",
                function_description=f"Function {number}",
                asset_ref=ref,
                source_created_at=created,
                source_updated_at=updated,
                status_changed_at=status_changed,
            )

        with Session(cls.database.engine) as session:
            session.add_all([asset(cls.A, "HEALTH-A"), asset(cls.B, "HEALTH-B"), asset(cls.TECHNICAL, "HEALTH-TECHNICAL")])
            session.add_all([registry(cls.A, "HEALTH-A"), registry(cls.B, "HEALTH-B")])
            session.add_all([
                health(1, cls.A, status="VER-OK", revision="0", created=datetime(2026, 1, 1), updated=datetime(2026, 1, 2), status_changed=None),
                health(2, cls.A, status="VER-OK", revision="0", created=datetime(2026, 1, 3), updated=datetime(2026, 1, 4), status_changed=datetime(2026, 1, 5)),
                health(3, cls.B, status="DRAFT", revision="0", created=None, updated=None, status_changed=None),
                health(4, cls.TECHNICAL, status="VER-OK", revision="1", created=datetime(2026, 1, 6), updated=datetime(2026, 1, 6), status_changed=None),
                health(5, cls.UNRESOLVED, status="UNKNOWN-SOURCE", revision="1", created=datetime(2026, 1, 7), updated=datetime(2026, 1, 7), status_changed=None),
                health(6, None, status=None, revision=None, created=None, updated=None, status_changed=None),
            ])
            session.commit()
        cls.repository = MartQueryRepository(cls.database)

    def test_overview_measures_relationships_status_and_multiple_records(self):
        result = self.repository.asset_health_overview(as_of=self.AS_OF)
        self.assertEqual(result["summary"], {
            "assessment_records": 6,
            "records_with_asset_ref": 5,
            "records_without_asset_ref": 1,
            "asset_master_resolved": 4,
            "registry_resolved": 3,
            "technical_non_registry_records": 1,
            "unresolved_asset_refs": 1,
            "registered_assets_represented": 2,
            "assets_with_multiple_records": 1,
            "maximum_records_per_asset": 2,
        })
        self.assertEqual({row["value"] for row in result["status_distribution"]}, {"VER-OK", "DRAFT", "UNKNOWN-SOURCE", "UNKNOWN"})
        self.assertEqual(result["record_recency"]["latest_record_at"], datetime(2026, 1, 7, tzinfo=timezone.utc))
        self.assertEqual(result["record_recency"]["oldest_record_at"], datetime(2026, 1, 2))
        self.assertAlmostEqual(result["record_recency"]["latest_assessment_age_days"], 8.5)
        self.assertNotIn("eid", result)

    def test_workspace_is_registry_scoped_and_date_fallback_is_transparent(self):
        page = self.repository.list_health_workspace(offset=0, limit=50, as_of=self.AS_OF)
        self.assertEqual(page.total, 3)
        self.assertEqual({row.source_asset_number for row in page.items}, {"HEALTH-A", "HEALTH-B"})
        latest = self.repository.latest_health_workspace(self.A, as_of=self.AS_OF)
        self.assertEqual(latest.source_record_id, "BHM-2")
        self.assertEqual(latest.assessment_record_date, datetime(2026, 1, 5))
        self.assertAlmostEqual(latest.assessment_age_days, 10.5)
        null_date = next(row for row in page.items if row.source_asset_number == "HEALTH-B")
        self.assertIsNone(null_date.assessment_record_date)
        self.assertIsNone(null_date.assessment_age_days)

    def test_workspace_filters_and_pagination(self):
        filtered = self.repository.list_health_workspace(asset_number="health-a", offset=0, limit=1, as_of=self.AS_OF)
        self.assertEqual(filtered.total, 2)
        self.assertEqual(len(filtered.items), 1)
        self.assertTrue(filtered.has_more)
        status = self.repository.list_health_workspace(lifecycle_status="DRAFT", offset=0, limit=50, as_of=self.AS_OF)
        self.assertEqual(status.total, 1)


class AssetHealthApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not hasattr(AssetHealthSemanticsFixtureTest, "database"):
            AssetHealthSemanticsFixtureTest.setUpClass()
        cls.database = AssetHealthSemanticsFixtureTest.database
        cls.service = ReliabilityQueryService(MartQueryRepository(cls.database))

    def test_overview_api_and_list_filters(self):
        class FixedDateTime(datetime):
            @classmethod
            def now(cls, tz=None):
                return AssetHealthSemanticsFixtureTest.AS_OF

        with patch("src.repositories.mart_reader.datetime", FixedDateTime):
            overview = reliability_api.asset_health_overview(service=self.service)
        self.assertEqual(overview.summary.assessment_records, 6)
        self.assertEqual(overview.summary.registered_assets_represented, 2)
        self.assertEqual(overview.evidence.health_score, "BUSINESS_SEMANTICS_REQUIRED")
        page = reliability_api.asset_health_list(asset_number="health-a", lifecycle_status=None, updated_from=None, updated_to=None, offset=0, limit=1, sort="updated_desc", service=self.service)
        self.assertEqual(page["meta"].total, 2)
        self.assertEqual(page["items"][0].source_asset_number, "HEALTH-A")

    def test_empty_overview_is_factual_and_mart_unavailable_is_503(self):
        empty_database = MartDatabase(MartDbConfig(dsn="sqlite+pysqlite:///:memory:"))
        MartBase.metadata.create_all(empty_database.engine)
        empty_service = ReliabilityQueryService(MartQueryRepository(empty_database))
        empty = reliability_api.asset_health_overview(service=empty_service)
        self.assertEqual(empty.summary.assessment_records, 0)
        self.assertEqual(empty.summary.registered_assets_represented, 0)
        self.assertEqual(empty.status_distribution, [])
        with patch("src.api.reliability.get_mart_database", side_effect=reliability_api.MartDatabaseConfigError("offline")):
            with self.assertRaises(HTTPException) as error:
                reliability_api._db()
        self.assertEqual(error.exception.status_code, 503)


if __name__ == "__main__":
    unittest.main()
