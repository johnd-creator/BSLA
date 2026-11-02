"""Sprint2 bounded reads: in-process trusted HTTP and disposable fixtures only."""
import json
import unittest
from unittest.mock import patch
from src.services import pdm_read_budget as budget
import test_pdm_input as native


class BoundedRegisterTest(unittest.TestCase):
    def setUp(self):
        self.fx = native.PdmInputTest()
        self.fx.setUp()

    def tearDown(self):
        self.fx.tearDown()

    def test_fixed_sizes_walk_exact_authorized_population(self):
        expected = sorted(self.fx.multi(f"s2:{i}")["record_id"] for i in range(23))
        for size in (1, 5, 10):
            actual = []
            for offset in range(0, 23, size):
                page = self.fx.call("GET", f"inspections?offset={offset}&limit={size}")
                self.assertEqual((page["total"], page["limit"], page["offset"]), (23, size, offset))
                self.assertEqual(page["has_more"], offset + size < 23)
                self.assertEqual(len(page["items"]), min(size, 23 - offset))
                actual.extend(x["record_id"] for x in page["items"])
            self.assertEqual(actual, expected)

    def test_oversized_unicode_page_fails_without_partial_or_leaked_content(self):
        # Each record is individually readable; ten together exceed the unchanged
        # two-MiB transport ceiling. Do not silently return fewer than requested.
        measurements = [dict(quantity="SYNTHETIC", value="測" * 1200) for _ in range(100)]
        for i in range(10):
            self.fx.multi(f"large:{i}", measurements=measurements)
        response = self.fx.client.get("/v1/engineering/inspections?limit=10")
        self.assertEqual(response.status_code, 413, f"status={response.status_code}, bytes={len(response.content)}")
        self.assertLess(len(response.content), 100)
        error = response.json()
        self.assertEqual(error, {"detail": {"code": "PDM_PAGE_BODY_LIMIT"}})
        self.assertNotIn("測", json.dumps(error, ensure_ascii=False))
        page = self.fx.call("GET", "inspections?limit=1")
        self.assertEqual((page["total"], len(page["items"])), (10, 1))
        self.assertEqual(page["items"][0]["measurements"][0]["value"], "測" * 1200)
        self.fx.call("GET", "inspections?asset_id=asset:FOREIGN&limit=10", expected=404)

    def test_large_provisional_page_preserves_raw_and_excludes_native_history(self):
        from test_pdm_input_capture import capture
        source=capture()
        template=source['rows'][0]
        source['rows']=[{**template,'row_id':f's-{i}','raw_value':'測'*2000} for i in range(50)]
        for i in range(10):
            self.fx.multi(f'capture:{i}',measurements=[],input_capture=source)
        response=self.fx.client.get('/v1/engineering/inspections?limit=10')
        self.assertEqual(response.status_code,413,f'status={response.status_code}, bytes={len(response.content)}')
        self.assertEqual(response.json(),{'detail':{'code':'PDM_PAGE_BODY_LIMIT'}})
        page=self.fx.call('GET','inspections?limit=1')
        row=page['items'][0]
        self.assertEqual((row['input_capture']['rows'][0]['raw_value'],row['input_capture']['clocks'][0]['precision']),('測'*2000,'DATE'))
        self.assertEqual(self.fx.call('GET','inspections/measurement-history?limit=25')['total'],0)

    def test_exact_full_envelope_utf8_boundary_and_incremental_stop(self):
        self.fx.multi("wire", observations=["零測😀"], measurements=[dict(quantity="SYNTHETIC", value=None),dict(quantity="BOOL",value=False)])
        page = self.fx.call("GET", "inspections?limit=10")
        response = self.fx.client.get("/v1/engineering/inspections?limit=10")
        exact = budget.wire_size(page)
        self.assertEqual(exact, len(response.content))
        with patch.object(budget, "PDM_PAGE_BYTES", exact):
            self.fx.call("GET", "inspections?limit=10")
        with patch.object(budget, "PDM_PAGE_BYTES", exact-1):
            self.fx.call("GET", "inspections?limit=10", expected=413)
        for i in range(9):
            self.fx.multi(f"wire:{i}")
        with patch.object(budget, "wire_size", wraps=budget.wire_size) as measured, patch.object(budget, "PDM_PAGE_BYTES", 1):
            self.fx.call("GET", "inspections?limit=10", expected=413)
            self.assertEqual(measured.call_count, 1, "must stop retaining models at first excess item")

    def test_visibility_and_revocation_precede_population_and_budget(self):
        own = self.fx.multi("owner")
        # Reviewer-created draft is visible only to independent reviewers, not author.
        from src.domain.engineering import Role
        grant=self.fx.provider.grants["reviewer"]
        self.fx.provider.grants["reviewer"]=grant.model_copy(update={"principal":grant.principal.model_copy(update={"roles":grant.principal.roles|{Role.AUTHOR}})})
        other = self.fx.call("POST", "inspections", dict(request_id="other",draft=dict(canonical_asset_id=self.fx.asset,method="OTHER",method_version="synthetic",inspector_ref="reviewer",observations=["PRIVATE_OTHER_DRAFT"])),actor="reviewer",expected=201)
        page = self.fx.call("GET", "inspections?limit=10")
        self.assertEqual(page["total"], 1)
        self.assertEqual([x["record_id"] for x in page["items"]], [own["record_id"]])
        self.assertNotIn("PRIVATE_OTHER_DRAFT", json.dumps(page))
        self.assertEqual(self.fx.call("GET", "inspections?limit=10",actor="reviewer")["total"],2)
        approved = self.fx.approved_inspection()
        self.assertEqual(self.fx.call("GET", "inspections?status=APPROVED&limit=10")["total"],1)
        self.fx.authority.revoke(self.fx.directory("author"),self.fx.credentials["author"][0])
        with patch.object(budget, "wire_size", side_effect=AssertionError("serialization before auth")):
            self.fx.call("GET", "inspections?limit=10", expected=401)

    def test_page_guard_does_not_change_measurement_history_or_filter_semantics(self):
        for i in range(11):
            self.fx.multi(f"filter:{i}", observations=["needle" if i % 2 else "other"])
        page = self.fx.call("GET", "inspections?search=needle&method=VIBRATION&status=DRAFT&limit=10")
        self.assertEqual(page["total"], 5)
        self.assertTrue(all(x["observations"] == ["needle"] for x in page["items"]))
        events = self.fx.call("GET", "inspections/measurement-history?point=point:SYNTHETIC&quantity=synthetic_quantity&limit=25")
        self.assertEqual((events["total"], events["limit"], len(events["items"])), (55, 25, 25))
        self.assertEqual(events["event_time_basis"], "MEASURED_AT")
        for value in ("0", "101", "-1"):
            self.fx.call("GET", f"inspections?limit={value}", expected=422)


import os

@unittest.skipUnless(os.getenv("GITHUB_ACTIONS")=="true" and os.getenv("NADI_APPLICATION_TEST_DSN"),"named disposable CI PostgreSQL only")
class BoundedPostgresRegisterTest(BoundedRegisterTest):
    def setUp(self):
        self.fx = native.PdmPostgresInputTest()
        self.fx.setUp()


if __name__ == "__main__":
    unittest.main()
