"""Run with the existing Maximo Collector test environment from its directory."""
import unittest
from src.adapters.maximo.mappers import service_request_from_payload, work_order_from_payload
from src.adapters.maximo.canonical_mappers import maintenance_event_from_payload

class RetainedMappingContractTest(unittest.TestCase):
    def test_status_and_worktype_through_legacy_and_canonical(self):
        for code in ["CM", "PM", "CD", "PDM", "EM", "OH", None]:
            source = dict(wonum="SYNTHETIC", assetnum="SYNTHETIC", siteid="BSR", orgid="IP", worktype=code, status="COMP")
            legacy = work_order_from_payload(source)
            canonical = maintenance_event_from_payload(source)
            self.assertEqual(legacy.status, canonical["status"])
            self.assertEqual(legacy.work_type, canonical["sources"]["maximo"]["worktype"])
            self.assertEqual(canonical["event_type"], code if code in {"CM", "PM"} else None)

    def test_sr_class_type_and_shared_workflow_remain_independent(self):
        for code in ["CD", "CM", "FLM", "SYNTHETIC_NEW"]:
            row = service_request_from_payload(dict(ticketid="SYNTHETIC", worktype=code, **{"class": "SR"}, status="QUEUED", workflow="SR-C"))
            self.assertEqual(row.work_type, code)
            self.assertEqual(row.class_label, "SR")
            self.assertEqual(row.status, "QUEUED")
            self.assertNotIn("workflow", row.sources["maximo"])
            self.assertNotEqual(row.work_type, "SR-C")

if __name__ == "__main__":
    unittest.main()
