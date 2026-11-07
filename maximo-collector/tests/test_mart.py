"""Hermetic Reliability Mart persistence tests; no Maximo or production DB."""

from __future__ import annotations

import copy
import unittest

from sqlalchemy import func, select

from src.adapters.maximo.canonical_mappers import (
    asset_health_assessment_from_payload,
    asset_master_from_payload,
    fmea_assessment_from_payload,
    maintenance_event_from_payload,
    overhaul_event_from_payload,
    rcfa_analysis_from_payload,
)
from src.config import DbConfig
from src.repositories import mart_models as orm
from src.repositories.database import Database
from src.services.canonical import CanonicalCollection
from src.services.mart import (
    CanonicalRecordRejected,
    MartIntegrityAuditor,
    MartWriter,
    ScopeViolation,
    UnsupportedCanonicalEntity,
    UnsupportedContractVersion,
)
from tests.fixtures.canonical_payloads import ASSET, BHM, FMEA, OVERHAUL, RCFA, WORK_ORDER


class ReliabilityMartTest(unittest.TestCase):
    def setUp(self):
        self.db = Database(DbConfig("sqlite+pysqlite:///:memory:"))
        self.db.create_all()
        self.writer = MartWriter(self.db)

    def tearDown(self):
        self.db.engine.dispose()

    @staticmethod
    def _collection(entity, record):
        return CanonicalCollection(entity, records=[copy.deepcopy(record)])

    def _records(self):
        asset = asset_master_from_payload(ASSET)
        workorder = maintenance_event_from_payload(WORK_ORDER)
        return {
            "asset_master": asset,
            "maintenance_event": workorder,
            "fmea_assessment": fmea_assessment_from_payload(FMEA),
            "rcfa_analysis": rcfa_analysis_from_payload(RCFA),
            "asset_health_assessment": asset_health_assessment_from_payload(BHM),
            "overhaul_event": overhaul_event_from_payload(
                OVERHAUL,
                workorder_index={WORK_ORDER["wonum"]: workorder},
            ),
        }

    def test_mart_tables_have_canonical_identity_and_no_hard_relationship_fks(self):
        expected = {
            "asset_master", "maintenance_event", "fmea_assessment", "rcfa_analysis",
            "asset_health_assessment", "overhaul_event",
        }
        # Base metadata is the authoritative SQLAlchemy registry.
        from src.repositories.database import Base
        actual = {name for name in Base.metadata.tables if name in expected}
        self.assertEqual(actual, expected)
        for table_name in expected:
            table = Base.metadata.tables[table_name]
            self.assertEqual([column.name for column in table.primary_key.columns], ["canonical_id"])
            self.assertFalse(table.foreign_keys)
            self.assertFalse({"raw_payload", "raw_response", "oslc_response"} & set(table.columns))

    def test_all_six_entities_insert_and_json_round_trip(self):
        records = self._records()
        for entity, record in records.items():
            stats = self.writer.persist_collection(self._collection(entity, record))
            self.assertEqual(stats.records_received, 1)
            self.assertEqual(stats.records_inserted, 1)

        with self.db.session() as session:
            fmea = session.get(orm.FmeaAssessmentMartOrm, records["fmea_assessment"]["canonical_id"])
            overhaul = session.get(orm.OverhaulEventMartOrm, records["overhaul_event"]["canonical_id"])
            self.assertEqual(fmea.provenance, records["fmea_assessment"]["provenance"])
            self.assertEqual(fmea.relationship_evidence, records["fmea_assessment"]["relationship_evidence"])
            self.assertEqual(overhaul.unresolved_source_attributes, records["overhaul_event"]["unresolved_source_attributes"])
            self.assertEqual(overhaul.sources, records["overhaul_event"]["sources"])

    def test_same_record_is_idempotent_and_mutable_update_preserves_created_at(self):
        record = asset_master_from_payload(ASSET)
        first = self.writer.persist_collection(self._collection("asset_master", record))
        self.assertEqual(first.records_inserted, 1)
        with self.db.session() as session:
            before = session.get(orm.AssetMasterMartOrm, record["canonical_id"])
            created_at = before.mart_created_at
            updated_at = before.mart_updated_at

        duplicate = self.writer.persist_collection(self._collection("asset_master", record))
        self.assertEqual(duplicate.records_unchanged, 1)
        with self.db.session() as session:
            unchanged = session.get(orm.AssetMasterMartOrm, record["canonical_id"])
            self.assertEqual(unchanged.mart_created_at, created_at)
            self.assertEqual(unchanged.mart_updated_at, updated_at)

        changed = copy.deepcopy(record)
        changed["status"] = "MAINTENANCE"
        update = self.writer.persist_collection(self._collection("asset_master", changed))
        self.assertEqual(update.records_updated, 1)
        with self.db.session() as session:
            after = session.get(orm.AssetMasterMartOrm, record["canonical_id"])
            self.assertEqual(after.status, "MAINTENANCE")
            self.assertEqual(after.mart_created_at, created_at)
            self.assertGreater(after.mart_updated_at, updated_at)

    def test_each_canonical_entity_upsert_is_idempotent(self):
        for entity, record in self._records().items():
            inserted = self.writer.persist_collection(self._collection(entity, record))
            duplicate = self.writer.persist_collection(self._collection(entity, record))
            self.assertEqual(inserted.records_inserted, 1, entity)
            self.assertEqual(duplicate.records_unchanged, 1, entity)

    def test_scope_guard_rejects_provenance_and_top_level_mismatches(self):
        cases = []
        provenance_bad = asset_master_from_payload(ASSET)
        provenance_bad["provenance"]["source_site"] = "OTHER_SITE"
        cases.append(provenance_bad)
        top_level_bad = asset_master_from_payload(ASSET)
        top_level_bad["site_code"] = "OTHER_SITE"
        cases.append(top_level_bad)
        organization_bad = asset_master_from_payload(ASSET)
        organization_bad["organization_code"] = "OTHER_ORG"
        cases.append(organization_bad)
        for record in cases:
            with self.assertRaises(ScopeViolation):
                self.writer.persist_collection(self._collection("asset_master", record))
        with self.db.session() as session:
            self.assertEqual(session.scalar(select(func.count()).select_from(orm.AssetMasterMartOrm)), 0)

    def test_contract_version_raw_payload_and_deferred_entity_are_rejected(self):
        version_bad = asset_master_from_payload(ASSET)
        version_bad["contract_version"] = "2.0"
        with self.assertRaises(UnsupportedContractVersion):
            self.writer.persist_collection(self._collection("asset_master", version_bad))

        raw_bad = asset_master_from_payload(ASSET)
        raw_bad["raw_payload"] = {"secret": "must-not-persist"}
        with self.assertRaises(CanonicalRecordRejected):
            self.writer.persist_collection(self._collection("asset_master", raw_bad))

        with self.assertRaises(UnsupportedCanonicalEntity):
            self.writer.persist_collection(CanonicalCollection("fmea_failure_mode", records=[]))

    def test_rcfa_nullable_relationships_persist(self):
        record = rcfa_analysis_from_payload(RCFA)
        stats = self.writer.persist_collection(self._collection("rcfa_analysis", record))
        self.assertEqual(stats.records_inserted, 1)
        with self.db.session() as session:
            stored = session.get(orm.RcfaAnalysisMartOrm, record["canonical_id"])
            self.assertIsNone(stored.asset_ref)
            self.assertIsNone(stored.location_ref)
            self.assertIsNone(stored.workorder_ref)
            self.assertIsNone(stored.failure_event_ref)

    def test_logical_asset_and_workorder_audit_reports_resolved_and_unresolved(self):
        records = self._records()
        for entity in ("asset_master", "maintenance_event", "fmea_assessment", "asset_health_assessment", "overhaul_event"):
            self.writer.persist_collection(self._collection(entity, records[entity]))

        initial = MartIntegrityAuditor(self.db).audit()
        self.assertEqual(initial["asset_reference_total"], 4)
        self.assertEqual(initial["asset_reference_resolved"], 4)
        self.assertEqual(initial["workorder_reference_total"], 1)
        self.assertEqual(initial["workorder_reference_resolved"], 1)

        missing_asset = fmea_assessment_from_payload({**FMEA, "fmeaid": "<fmea-id-2>", "assetnum": "<missing-asset>"})
        self.writer.persist_collection(self._collection("fmea_assessment", missing_asset))
        missing_workorder = overhaul_event_from_payload(
            {**OVERHAUL, "domid": "<oh-id-2>", "wonum": "BSR-<missing-work-order>"},
            workorder_index={},
        )
        self.writer.persist_collection(self._collection("overhaul_event", missing_workorder))

        audited = MartIntegrityAuditor(self.db).audit()
        self.assertEqual(audited["asset_reference_total"], 5)
        self.assertEqual(audited["asset_reference_resolved"], 4)
        self.assertEqual(audited["asset_reference_unresolved"], 1)
        self.assertEqual(audited["workorder_reference_total"], 2)
        self.assertEqual(audited["workorder_reference_resolved"], 1)
        self.assertEqual(audited["workorder_reference_unresolved"], 1)

    def test_overhaul_workorder_reference_targets_maintenance_work_order_id(self):
        records = self._records()
        maintenance = records["maintenance_event"]
        overhaul = records["overhaul_event"]
        self.assertEqual(overhaul["workorder_ref"], maintenance["work_order_id"])
        self.assertNotEqual(overhaul["workorder_ref"], maintenance["canonical_id"])
        self.writer.persist_collection(self._collection("maintenance_event", maintenance))
        self.writer.persist_collection(self._collection("overhaul_event", overhaul))
        with self.db.session() as session:
            stored = session.get(orm.OverhaulEventMartOrm, overhaul["canonical_id"])
            self.assertEqual(stored.workorder_ref, maintenance["work_order_id"])

    def test_workorder_audit_counts_source_refs_when_target_index_is_non_unique(self):
        records = self._records()
        maintenance = records["maintenance_event"]
        duplicate_target = copy.deepcopy(maintenance)
        duplicate_target["canonical_id"] = "maintenance_event:MAXIMO:MXWODETAIL:BSR:IP:<event-2>"
        duplicate_target["id"] = duplicate_target["canonical_id"]
        self.writer.persist_collection(self._collection("maintenance_event", maintenance))
        self.writer.persist_collection(self._collection("maintenance_event", duplicate_target))
        self.writer.persist_collection(self._collection("overhaul_event", records["overhaul_event"]))
        audit = MartIntegrityAuditor(self.db).audit()
        self.assertEqual(audit["workorder_reference_total"], 1)
        self.assertEqual(audit["workorder_reference_resolved"], 1)

    def test_transaction_rolls_back_entire_batch_on_scope_violation(self):
        valid = asset_master_from_payload(ASSET)
        invalid = copy.deepcopy(valid)
        invalid["canonical_id"] = "asset:MAXIMO:MXASSET:BSR:IP:<asset-2>"
        invalid["provenance"]["source_record_id"] = "<asset-2>"
        invalid["site_code"] = "OTHER_SITE"
        collection = CanonicalCollection("asset_master", records=[valid, invalid])
        with self.assertRaises(ScopeViolation):
            self.writer.persist_collection(collection)
        with self.db.session() as session:
            self.assertEqual(session.scalar(select(func.count()).select_from(orm.AssetMasterMartOrm)), 0)

    def test_dry_run_validates_without_writing(self):
        record = asset_master_from_payload(ASSET)
        stats = self.writer.persist_collection(self._collection("asset_master", record), dry_run=True)
        self.assertEqual(stats.records_received, 1)
        self.assertEqual(stats.records_inserted, 0)
        with self.db.session() as session:
            self.assertEqual(session.scalar(select(func.count()).select_from(orm.AssetMasterMartOrm)), 0)

    def test_datetime_round_trip_preserves_timezone(self):
        record = maintenance_event_from_payload({**WORK_ORDER, "status": "CLOSE"})
        self.writer.persist_collection(self._collection("maintenance_event", record))
        with self.db.session() as session:
            stored = session.get(orm.MaintenanceEventMartOrm, record["canonical_id"])
            self.assertIsNotNone(stored.actual_start.tzinfo)
            self.assertEqual(stored.actual_start.isoformat(), "2026-08-19T09:15:00+07:00")


if __name__ == "__main__":
    unittest.main()
