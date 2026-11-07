"""Offline future projection correction; never run against retained stores."""
import unittest
from datetime import datetime
from src.repositories.models import WorkOrderOrm
from src.services.local_mart_projector import _work_order_payload
from src.adapters.maximo.canonical_mappers import maintenance_event_from_payload
from src.services.mart import _maintenance_row
from src.services.local_mart_projector import CollectorMartProjector
from src.repositories import models, mart_models
from test_local_mart_projector import _databases, NOW


class WorkOrderLineageTest(unittest.TestCase):
    def test_disposable_projector_writer_replay_persists_corrected_fields(self):
        collector,mart=_databases()
        with collector.session() as session:
            session.add(models.EquipmentOrm(id="ASSET-SYNTHETIC",sources={"maximo":{"assetnum":"ASSET-SYNTHETIC","siteid":"BSR","orgid":"IP"}}))
            session.add(WorkOrderOrm(id="BSR-SYNTHETIC-ROUNDTRIP",equipment_id="ASSET-SYNTHETIC",status="CLOSE",work_type="CD",failure_code="RETAINED-CODE",reported_at=NOW,scheduled_start=NOW,scheduled_finish=NOW,source_changed_at=NOW,downtime_hours=0,actual_labor_hours=0))
            session.commit()
        projector=CollectorMartProjector(collector,mart,batch_size=1)
        self.assertEqual(projector.project("maintenance_event").rows_inserted,1)
        self.assertEqual(projector.project("maintenance_event").rows_unchanged,1)
        with mart.session() as session:
            row=session.query(mart_models.MaintenanceEventMartOrm).one()
            self.assertEqual(row.failure_code,"RETAINED-CODE")
            self.assertIsNone(row.actual_start)
            self.assertIsNone(row.actual_finish)
            self.assertIsNone(row.downtime_hours)  # Source flag is not a duration.
            # SQLite drops timezone metadata. Its uncertainty stays explicit.
            self.assertEqual(row.sources["maximo"]["reportdate"],NOW.replace(tzinfo=None).isoformat())
            self.assertEqual(row.sources["maximo"]["schedstart"],NOW.replace(tzinfo=None).isoformat())

    def test_legacy_retained_fields_survive_projection_mapping_and_read_model(self):
        for raw in ["2026-10-23T14:51:51.123400+07:00", "2026-10-23T14:51:51.123400"]:
            clock = datetime.fromisoformat(raw)
            row = WorkOrderOrm(id="BSR-SYNTHETIC-01", equipment_id="ASSET-SYNTHETIC", work_type="CD", status="CLOSE", reported_at=clock, scheduled_start=clock, scheduled_finish=clock, failure_code="SOURCE-CODE", actual_labor_hours=0, downtime_hours=0, estimated_duration_hours=25, source_changed_at=datetime.fromisoformat("2026-10-24T00:00:00+00:00"))
            payload = _work_order_payload(row)
            mapped = maintenance_event_from_payload(payload)
            persisted = _maintenance_row(mapped)
            self.assertEqual(persisted["failure_code"], "SOURCE-CODE")
            self.assertEqual(persisted["labor_hours"], 0)
            self.assertIsNone(persisted["downtime_hours"])  # Legacy coerced flag cannot become hours.
            self.assertIsNone(persisted["actual_start"])
            self.assertIsNone(persisted["actual_finish"])
            self.assertIsNone(persisted["duration_hours"])
            self.assertIsNone(mapped["event_type"])
            self.assertEqual(mapped["status"], "CLOSE")
            for key in ["reportdate", "schedstart", "schedfinish"]:
                self.assertEqual(mapped["sources"]["maximo"][key],raw)

    def test_direct_canonical_source_clock_preserves_exact_text(self):
        raw="2026-10-23T14:51:51.123400+07:00"
        mapped=maintenance_event_from_payload({"wonum":"BSR-SYNTHETIC","assetnum":"ASSET-SYNTHETIC","siteid":"BSR","orgid":"IP","reportdate":raw})
        self.assertEqual(mapped["sources"]["maximo"]["reportdate"],raw)

    def test_no_recovery_from_unretained_dates_or_person_json(self):
        row=WorkOrderOrm(id="BSR-SYNTHETIC",equipment_id="ASSET-SYNTHETIC", sources={"maximo":{"actstart":"UNTRUSTED","reportedby":"PRIVATE"}})
        payload=_work_order_payload(row)
        self.assertIsNone(payload["actstart"])
        self.assertNotIn("PRIVATE",str(payload))
        mapped=maintenance_event_from_payload(payload)
        self.assertIsNone(mapped["failure_code"])
        self.assertIsNone(mapped["sources"]["maximo"]["reportdate"])


if __name__ == "__main__":
    unittest.main()
