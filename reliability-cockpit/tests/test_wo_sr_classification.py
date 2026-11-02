"""Synthetic classification read contract: no retained data or source calls."""
import unittest
from types import SimpleNamespace
from src.api.reliability import MaintenanceView, _maintenance


def record(raw=None, canonical=None, status="COMP", sources=None):
    fields = {k: None for k in MaintenanceView.model_fields if k != "classification"}
    fields.update(canonical_id="maintenance:SYNTHETIC", contract_version="1.0", id="SYNTHETIC",
                  equipment_id="asset:SYNTHETIC", site_code="BSR", organization_code="IP",
                  event_type=canonical, status=status,
                  sources=sources if sources is not None else {"maximo": {"worktype": raw}})
    return SimpleNamespace(**fields)


class ClassificationReadTest(unittest.TestCase):
    def test_supported_types_keep_enum_and_raw_separate(self):
        for code in ["CM", "PM", "INSPECTION", "CALIBRATION", "REPAIR", "EMERGENCY"]:
            with self.subTest(code=code):
                row = _maintenance(record(code, code))
                self.assertEqual(row.event_type, code)
                self.assertEqual(row.classification.raw_work_type, code)
                self.assertEqual(row.classification.state, "CANONICAL_SUPPORTED")
                self.assertEqual(row.classification.confidence, "VERIFIED")
                self.assertIsNone(row.classification.description)

    def test_retained_unmapped_codes_are_not_unknown_or_translated(self):
        for code in ["CD", "PDM", "EM", "OH", "RTF", "S", "PRO", "ECO", "SYNTHETIC_NEW", " CD "]:
            row = _maintenance(record(code))
            self.assertIsNone(row.event_type)
            self.assertEqual(row.classification.raw_work_type, code)
            self.assertEqual(row.classification.state, "UNMAPPED")
            self.assertEqual(row.classification.confidence, "UNRESOLVED")
            self.assertIsNone(row.classification.workflow_name)

    def test_missing_retained_and_not_exposed_are_distinct(self):
        for raw in [None, "", "   ", {}, 4, False]:
            self.assertEqual(_maintenance(record(raw)).classification.state, "MISSING_RETAINED_TYPE")
        self.assertEqual(_maintenance(record(None, "PM")).classification.state, "CANONICAL_ONLY")
        # Legacy API documents have no new field; that is not proof of missing source.
        legacy = _maintenance(record()).model_dump(exclude={"classification"})
        self.assertIsNone(MaintenanceView.model_validate(legacy).classification)

    def test_actual_status_preserved_without_workflow_translation(self):
        for status in ["INPRG", "COMP", "CLOSE", "SYNTHETIC_STATUS", None, "", " "]:
            row = _maintenance(record("CD", status=status))
            self.assertEqual(row.status, status)
            self.assertEqual(row.classification.status_state, "AVAILABLE" if status and status.strip() else "MISSING_RETAINED_STATUS")

    def test_personal_vendor_payload_never_serialized(self):
        src = {"maximo": {"worktype": "CD", "reportedby": "PRIVATE_SYNTHETIC", "workflow": "UNVERIFIED", "status": "NOT_AUTHORITATIVE"}, "secret": "PRIVATE_SYNTHETIC"}
        row = _maintenance(record(sources=src))
        text = row.model_dump_json()
        self.assertNotIn("PRIVATE_SYNTHETIC", text)
        self.assertNotIn("sources", row.model_dump())
        self.assertNotIn("provenance", row.model_dump())
        self.assertEqual(row.status, "COMP")
        for malformed in [{"maximo": []}, {"maximo": None}, {}]:
            self.assertIsNone(_maintenance(record(sources=malformed)).classification.raw_work_type)
