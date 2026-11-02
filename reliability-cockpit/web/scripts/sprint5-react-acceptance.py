"""Fail closed if the disclosed API→React test did not actually execute."""
import json
from pathlib import Path
import unittest

from test_projection_acceptance import ProjectionAcceptanceTest

suite = unittest.TestSuite([ProjectionAcceptanceTest(
    "test_api_documents_render_actual_asset_evidence_and_trust_views")])
result = unittest.TextTestRunner(verbosity=2).run(suite)
receipt = {"test": "ProjectionAcceptanceTest.test_api_documents_render_actual_asset_evidence_and_trust_views",
           "executed": result.testsRun, "skipped": len(result.skipped),
           "failures": len(result.failures), "errors": len(result.errors),
           "classification": "SYNTHETIC_API_TO_ACTUAL_REACT"}
out = Path("/tmp/nadi-sprint05/react-acceptance.json")
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(receipt, indent=2) + "\n")
if result.testsRun != 1 or result.skipped or not result.wasSuccessful():
    raise SystemExit("MANDATORY_REACT_ACCEPTANCE_NOT_EXECUTED_OR_FAILED")
print("Sprint5 mandatory React acceptance PASS: executed=1 skipped=0")
