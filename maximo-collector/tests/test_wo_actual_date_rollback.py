"""Synthetic worker replay and field-CAS regressions; no source access."""
import copy
from datetime import datetime
import unittest

from test_wo_actual_dates import RAW, seed
from src.config import DbConfig
from src.repositories.database import Database
from src.repositories import models, mart_models
from src.repositories.store import CollectorStore
from src.adapters.maximo.mappers import work_order_from_payload
from src.adapters.maximo.canonical_mappers import maintenance_event_from_payload
from src.services.canonical import CanonicalCollection
from src.services.local_mart_projector import _work_order_payload
from src.services.mart import MartWriter
from src.services.wo_actual_date_recovery import apply_cohort, rollback_cohort, plan_cohort, seal, _snapshot
from src.services import wo_actual_date_journal as journal


class RollbackScenarios:
    """Also inherited by the isolated PostgreSQL-only suite."""
    target = "disposable-sqlite"

    def prepare(self, second=False):
        seed(self.db)
        self.raws = {RAW["wonum"]: copy.deepcopy(RAW)}
        if second:
            raw = dict(RAW, wonum="BSR-SYNTHETIC-2")
            seed(self.db, raw)
            self.raws[raw["wonum"]] = raw
        self.plan = plan_cohort(self.db, list(self.raws))
        self.receipt = self.apply()
        return self.receipt

    def checkpoint(self, receipt):
        self.saved.append(copy.deepcopy(receipt))

    def apply(self, checkpoint=None):
        return apply_cohort(self.db, self.plan, self.raws, expected_database=self.target,
                            approved_plan_sha256=seal(self.plan), checkpoint=checkpoint or self.checkpoint)

    def rollback(self, receipt=None, checkpoint=None):
        return rollback_cohort(self.db, receipt or self.receipt, expected_database=self.target,
                               checkpoint=checkpoint or self.checkpoint)

    def snapshots(self):
        with self.db.session() as s:
            return {i["wonum"]: {"legacy": _snapshot(s.get(models.WorkOrderOrm, i["wonum"])),
                                 "mart": _snapshot(s.get(mart_models.MaintenanceEventMartOrm, i["canonical_id"]))}
                    for i in self.plan["cohort"]}

    def worker(self, raw):
        CollectorStore(self.db).upsert_work_order(work_order_from_payload(raw))
        with self.db.session() as s:
            mapped = maintenance_event_from_payload(_work_order_payload(s.get(models.WorkOrderOrm, raw["wonum"])))
        MartWriter(self.db).persist_collection(CanonicalCollection("maintenance_event", records=[mapped]))

    def assertRestored(self, result):
        now = self.snapshots()
        for entry in result["records"]:
            current = now[entry["wonum"]]
            for c in entry["write_set"]["fields"]:
                self.assertTrue(journal.same(journal.slot(current[c["side"]], c["path"]), c["before"]))
            self.assertIsNone(current["mart"]["actual_start"])
            self.assertIsNone(current["mart"]["actual_finish"])

    def test_failure_code_only_survives(self):
        self.prepare()
        with self.db.session() as s:
            s.query(mart_models.MaintenanceEventMartOrm).one().failure_code = "WORKER"
            s.commit()
        self.assertRestored(self.rollback())
        self.assertEqual(self.snapshots()[RAW["wonum"]]["mart"]["failure_code"], "WORKER")

    def test_unrelated_source_and_retained_json_survive(self):
        self.prepare()
        with self.db.session() as s:
            for cls in (models.WorkOrderOrm, mart_models.MaintenanceEventMartOrm):
                row = s.query(cls).one(); sources = copy.deepcopy(row.sources)
                sources["maximo"]["independent"] = {"nullable": None, "list": [1, 2]}
                sources["independent"] = "worker"; row.sources = sources
            s.commit()
        self.assertRestored(self.rollback())
        for side in ("legacy", "mart"):
            self.assertEqual(self.snapshots()[RAW["wonum"]][side]["sources"]["maximo"]["independent"]["list"], [1, 2])

    def test_status_replay_and_same_dates_survive(self):
        self.prepare(); self.worker(dict(RAW, status="CAN", failurecode="REAL-WORKER"))
        before = self.snapshots()[RAW["wonum"]]["mart"]["mart_updated_at"]
        self.assertRestored(self.rollback())
        row = self.snapshots()[RAW["wonum"]]["mart"]
        self.assertEqual(row["status"], "CAN"); self.assertEqual(row["failure_code"], "REAL-WORKER")
        self.assertGreater(row["mart_updated_at"], before)

    def test_null_replay_keeps_dates_until_rollback(self):
        self.prepare(); self.worker(dict(RAW, actstart=None, actfinish=None))
        self.assertIsNotNone(self.snapshots()[RAW["wonum"]]["mart"]["actual_start"])
        self.assertRestored(self.rollback())

    def test_advanced_row_version_with_unchanged_authoritative_fields(self):
        self.prepare(); self.worker(dict(RAW, actstart=None, actfinish=None, status="CAN", changedate="2026-09-04T00:00:00Z"))
        self.assertRestored(self.rollback())
        for side in ("legacy", "mart"):
            self.assertEqual(self.snapshots()[RAW["wonum"]][side]["source_changed_at"].date().isoformat(), "2026-09-04")

    def test_advanced_version_without_proof_conflicts(self):
        self.prepare()
        with self.db.session() as s:
            for cls in (models.WorkOrderOrm, mart_models.MaintenanceEventMartOrm):
                row = s.query(cls).one(); row.source_changed_at = datetime.fromisoformat("2026-09-04T00:00:00+00:00")
                sources = copy.deepcopy(row.sources); sources["maximo"].pop("actual_dates"); row.sources = sources
            s.commit()
        current = self.snapshots()
        with self.assertRaises(ValueError): self.rollback()
        self.assertTrue(journal.same(current, self.snapshots()))

    def test_new_start_conflicts(self):
        self.prepare(); self.worker(dict(RAW, changedate="2026-09-04T00:00:00Z", actstart="2026-09-01T01:00:00Z"))
        current = self.snapshots()
        with self.assertRaises(ValueError): self.rollback()
        self.assertTrue(journal.same(current, self.snapshots()))

    def test_new_finish_conflicts(self):
        self.prepare(); self.worker(dict(RAW, changedate="2026-09-04T00:00:00Z", actfinish="2026-09-02T01:00:00Z"))
        with self.assertRaises(ValueError): self.rollback()

    def test_same_dates_newer_provenance_conflicts(self):
        self.prepare(); self.worker(dict(RAW, changedate="2026-09-04T00:00:00Z"))
        with self.assertRaises(ValueError): self.rollback()

    def test_duplicate_rollback_requires_verified_rollback_journal(self):
        self.prepare(); result = self.rollback(); self.assertRestored(result)
        current = self.snapshots(); again = self.rollback(result)
        self.assertEqual(result, again); self.assertTrue(journal.same(current, self.snapshots()))
        with self.assertRaises(ValueError): self.rollback(self.receipt)

    def test_recovery_idempotence_and_reapply_after_rollback(self):
        self.prepare(); current = self.snapshots(); self.apply()
        self.assertTrue(journal.same(current, self.snapshots()))
        self.rollback(); self.apply()
        self.assertTrue(journal.same(journal.date_guard(self.snapshots()[RAW["wonum"]]), self.receipt["records"][0]["date_guard"]))

    def test_recovery_checkpoint_interruption_is_atomic(self):
        seed(self.db); self.raws = {RAW["wonum"]: RAW}; self.plan = plan_cohort(self.db, list(self.raws))
        current = self.snapshots()
        def fail(receipt): raise OSError("synthetic private disk failure")
        with self.assertRaises(OSError): self.apply(checkpoint=fail)
        self.assertTrue(journal.same(current, self.snapshots()))
        self.apply()

    def test_rollback_checkpoint_interruption_is_atomic(self):
        self.prepare(); current = self.snapshots()
        def fail(receipt): raise OSError("synthetic private disk failure")
        with self.assertRaises(OSError): self.rollback(checkpoint=fail)
        self.assertTrue(journal.same(current, self.snapshots()))
        self.assertRestored(self.rollback())

    def test_prepared_recovery_journal_reconciles_commit_ack_loss(self):
        self.prepare(); prepared = self.saved[0]
        self.assertEqual(prepared["state"], "PREPARED")
        self.assertRestored(self.rollback(prepared))

    def test_rollback_prepared_journal_reconciles_commit_ack_loss(self):
        self.prepare(); self.rollback(); prepared = self.saved[-1]
        self.assertEqual(prepared["state"], "ROLLBACK_PREPARED")
        result = self.rollback(prepared); self.assertEqual(result["state"], "ROLLED_BACK")
        self.assertRestored(result)

    def test_prepared_rollback_after_precommit_failure_can_retry(self):
        self.prepare(); saved = []
        def fail(receipt):
            saved.append(receipt)
            raise OSError("synthetic commit interruption")
        with self.assertRaises(OSError): self.rollback(checkpoint=fail)
        self.assertRestored(self.rollback(saved[0]))

    def test_duplicate_after_proven_advanced_version_rollback(self):
        self.prepare(); self.worker(dict(RAW, changedate="2026-09-04T00:00:00Z", actstart=None, actfinish=None))
        result = self.rollback(); self.assertEqual(result, self.rollback(result))


    def test_absent_null_and_explicit_json_before_values_restore_exactly(self):
        for original in (None, {}, {"maximo": {"actual_dates": None, "actstart": None}}):
            # Each variant uses a fresh synthetic WO, never a file/database fixture.
            raw = dict(RAW, wonum="BSR-PRESENCE-" + str(len(self.saved)))
            seed(self.db, raw)
            with self.db.session() as s:
                local = s.get(models.WorkOrderOrm, raw["wonum"])
                mart = s.get(mart_models.MaintenanceEventMartOrm, maintenance_event_from_payload(raw)["id"])
                local.sources = copy.deepcopy(original); mart.sources = copy.deepcopy(original); s.commit()
            self.raws = {raw["wonum"]: raw}; self.plan = plan_cohort(self.db, list(self.raws)); self.receipt = self.apply()
            self.rollback()
            row = self.snapshots()[raw["wonum"]]
            self.assertEqual(row["legacy"]["sources"], original)
            self.assertEqual(row["mart"]["sources"], original)

    def test_new_independent_json_container_is_preserved(self):
        seed(self.db)
        with self.db.session() as s:
            for cls in (models.WorkOrderOrm, mart_models.MaintenanceEventMartOrm):
                s.query(cls).one().sources = None
            s.commit()
        self.raws = {RAW["wonum"]: RAW}; self.plan = plan_cohort(self.db, list(self.raws)); self.receipt = self.apply()
        with self.db.session() as s:
            for cls in (models.WorkOrderOrm, mart_models.MaintenanceEventMartOrm):
                row = s.query(cls).one(); sources = copy.deepcopy(row.sources)
                sources["maximo"]["worker"] = "retained"; row.sources = sources
            s.commit()
        self.rollback()
        for side in ("legacy", "mart"):
            self.assertEqual(self.snapshots()[RAW["wonum"]][side]["sources"], {"maximo": {"worker": "retained"}})


    def test_partial_cohort_conflict_writes_nothing(self):
        self.prepare(second=True)
        second = list(self.raws.values())[1]
        self.worker(dict(second, changedate="2026-09-04T00:00:00Z"))
        current = self.snapshots()
        with self.assertRaises(ValueError): self.rollback()
        self.assertTrue(journal.same(current, self.snapshots()))

    def test_registry_scope_change_conflicts(self):
        self.prepare()
        with self.db.session() as s:
            s.query(mart_models.ReliabilityAssetRegistryMartOrm).one().site_code = "OTHER"; s.commit()
        with self.assertRaises(ValueError): self.rollback()

    def test_journal_tampering_and_old_format_fail_closed(self):
        self.prepare(); bad = copy.deepcopy(self.receipt)
        bad["records"][0]["write_set"]["fields"][0]["path"] = ["status"]
        with self.assertRaises(ValueError): self.rollback(journal.signed(bad))
        with self.assertRaises(ValueError): self.rollback({"records": self.receipt["records"]})


class MemoryRollbackTest(RollbackScenarios, unittest.TestCase):
    def setUp(self):
        self.db = Database(DbConfig("sqlite+pysqlite:///:memory:")); self.db.create_all(); self.saved = []
    def tearDown(self): self.db.engine.dispose()
