"""Additive WO view qualification. Synthetic only; no source or retained writes."""
import unittest
from datetime import datetime
from src.api.reliability import MaintenanceView, _maintenance
from test_wo_sr_classification import record


class WorkOrderDetailTest(unittest.TestCase):
    def test_retained_clocks_keep_original_offset_precision_and_naive_state(self):
        for clock in ["2026-10-23T07:51:51Z", "2026-10-23T14:51:51.123400+07:00", "2026-10-23T14:51:51.123400", "2026-10-23T14:51:51-00:00"]:
            source = {"maximo": {"wonum": "WO-SYNTHETIC-01", "assetnum": "ASSET-SYNTHETIC", "reportdate": clock, "schedstart": clock, "schedfinish": clock}}
            detail = _maintenance(record(sources=source)).source_detail
            self.assertEqual(detail.work_order_number, "WO-SYNTHETIC-01")
            self.assertEqual(detail.asset_number, "ASSET-SYNTHETIC")
            self.assertEqual([detail.reported_at, detail.scheduled_start, detail.scheduled_finish], [clock] * 3)

    def test_missing_invalid_unexposed_and_zero_do_not_become_facts(self):
        for value in [None, "", "invalid", "2026-02-30T01:02:03Z", "2026-01-01", "2026-10-23T07:51:51+0700", "2026-10-23T07:51:51+07", "2026-10-23T07:51:51+07:00:30", "2026-10-23T07:51:51+00:60", "2026-10-23T07:51:51,123Z", "2026-W43-5T07:51:51Z", {}, 0, False]:
            row = record(sources={"maximo": {"reportdate": value}})
            row.duration_hours = 0
            dto = _maintenance(row)
            self.assertIsNone(dto.source_detail.reported_at)
            self.assertIsNone(dto.actual_start)
            self.assertIsNone(dto.duration_hours)
            self.assertEqual(dto.actual_timing_state, "NOT_CLOSED")
        legacy = _maintenance(record()).model_dump(exclude={"source_detail"})
        self.assertIsNone(MaintenanceView.model_validate(legacy).source_detail)

    def test_old_fields_identical_and_only_allowlisted_new_scalars_exposed(self):
        row = record("CD", sources={"maximo": {"worktype": "CD", "wonum": "WO-SYNTHETIC", "reportedby": "DO_NOT_EXPOSE", "extra": {"private": "DO_NOT_EXPOSE"}, "failurecode": "NOT_AUTHORITATIVE"}})
        row.actual_start = datetime.fromisoformat("2026-10-23T14:51:51+07:00")
        row.failure_code = "RETAINED-CODE"
        dto = _maintenance(row)
        for key in MaintenanceView.model_fields.keys() - {"source_detail", "classification", "description", "actual_timing_state", "actual_start", "actual_finish", "duration_hours"}:
            self.assertEqual(getattr(dto,key), getattr(row,key))
        self.assertIsNone(dto.actual_start)
        self.assertIsNone(dto.actual_finish)
        self.assertIsNone(dto.duration_hours)
        self.assertEqual(dto.actual_timing_state, "NOT_CLOSED")
        self.assertNotIn("DO_NOT_EXPOSE", dto.model_dump_json())
        self.assertNotIn("sources", dto.model_dump())
        self.assertNotIn("provenance", dto.model_dump())
        self.assertEqual(dto.failure_code, "RETAINED-CODE")
        self.assertEqual(set(dto.source_detail.model_dump()), {"work_order_number","asset_number","reported_at","scheduled_start","scheduled_finish"})


if __name__ == "__main__":
    unittest.main()
