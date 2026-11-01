"""Synthetic, offline prerequisite/crosswalk qualification, never plant approval."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('sprint3_readiness', ROOT/'catalog/evidence_readiness.py')
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)

class Sprint3EvidenceContractTest(unittest.TestCase):
    def test_schemas_and_synthetic_examples(self):
        for name, example in [('asset-crosswalk-decision','sprint3-crosswalk'), ('reliability-kpi-readiness','sprint3-kpi-readiness')]:
            schema = json.loads((ROOT/f'schemas/{name}.schema.json').read_text())
            Draft202012Validator.check_schema(schema)
            fixture = json.loads((ROOT/f'examples/{example}.synthetic.json').read_text())
            for row in fixture if isinstance(fixture,list) else [fixture]:
                Draft202012Validator(schema).validate(row)
                altered = copy.deepcopy(row); altered['mtbf'] = 123
                self.assertFalse(Draft202012Validator(schema).is_valid(altered))

    def test_crosswalk_preserves_rows_and_never_promotes(self):
        rows = json.loads((ROOT/'examples/sprint3-crosswalk.synthetic.json').read_text()); before=copy.deepcopy(rows)
        result = module.crosswalk_inventory(rows)
        self.assertEqual(rows,before)
        self.assertEqual([r['decision_status'] for r in result],['VERIFIED','CANDIDATE','UNRESOLVED','FORBIDDEN','UNRESOLVED','UNRESOLVED'])
        self.assertEqual(len(rows),len(result))
        for key in ['mapping_owner','mapping_verified_at','mapping_evidence_ref','maximo_equipment_ref','canonical_asset_id','pi_af_ref']:
            row=copy.deepcopy(rows[0]); row[key]=None
            self.assertEqual(module.crosswalk_inventory([row])[0]['decision_status'],'UNRESOLVED')
        collision=copy.deepcopy(rows[0]); collision['canonical_asset_id']='SYNTHETIC:OTHER'
        self.assertTrue(all(r['decision_status']=='UNRESOLVED' for r in module.crosswalk_inventory([rows[0],collision])))
        for key,value in [('mapping_verified_at','not-a-date'),('mapping_verified_at','2026-01-01T00:00:00'),('mapping_owner',' '),('mapping_evidence_ref',' padded ')]:
            row=copy.deepcopy(rows[0]);row[key]=value
            self.assertEqual(module.crosswalk_inventory([row])[0]['decision_status'],'UNRESOLVED')
        with self.assertRaises(ValueError): module.crosswalk_inventory(rows*2000)

    def test_complete_synthetic_evidence_still_not_engineer_approval(self):
        inputs={k:{'status':'AVAILABLE_VERIFIED','evidence_ref':'SYNTHETIC:only','owner':'SYNTHETIC:reviewer','definition_version':'SYNTHETIC:1'} for k in module.REQUIRED_KPI_INPUTS}
        result=module.kpi_readiness(inputs)
        self.assertEqual(result['status'],'NOT_ELIGIBLE'); self.assertEqual(result['input_completeness'],'RECORDED_COMPLETE')
        self.assertNotIn('mtbf',result); self.assertNotIn('mttr',result)
        for key in module.REQUIRED_KPI_INPUTS:
            for state in ['AVAILABLE_UNAPPROVED','MISSING','BLOCKED']:
                modified=copy.deepcopy(inputs);modified[key]['status']=state
                result=module.kpi_readiness(modified)
                self.assertEqual(result['unqualified_inputs'],[key]);self.assertEqual(result['status'],'NOT_ELIGIBLE')
        for invalid in [{}, {**inputs,'mttr':0}]:
            with self.assertRaises(ValueError):module.kpi_readiness(invalid)
        inputs['failure_event_identity']['evidence_ref']=None
        with self.assertRaises(ValueError):module.kpi_readiness(inputs)

    def test_activity_fields_do_not_qualify_reliability(self):
        inputs=json.loads((ROOT/'examples/sprint3-kpi-readiness.synthetic.json').read_text())
        self.assertEqual(module.kpi_readiness(inputs)['status'],'NOT_ELIGIBLE')
        for case,key in [('incomplete timestamps','incomplete_timestamps_policy'),('overlap','overlap_policy'),('reopened WO','reopened_work_order_policy'),('status updates','repeated_status_update_policy'),('duplicates','duplicate_event_policy'),('ordinary CM','failure_vs_maintenance_definition'),('calendar vs operating hours','operating_exposure_hours'),('downtime vs active repair','active_repair_vs_total_outage')]:
            with self.subTest(case=case):
                self.assertIn(key,module.kpi_readiness(inputs)['unqualified_inputs'])
