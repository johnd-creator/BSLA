"""Offline synthetic policy/identity/clock/denominator qualification; no IO sources."""
import copy
import json
import unittest
from pathlib import Path
from decimal import Decimal, localcontext, Inexact
from jsonschema import Draft202012Validator
from pydantic import ValidationError
from contracts.sprint4.engine import evaluate
from contracts.sprint4.models import Packet, Result
ROOT=Path(__file__).parents[1]/'contracts/sprint4'
def fixture():return json.loads((ROOT/'reference-input.synthetic.json').read_text())
def metrics(p):
    result=evaluate(p);Result.model_validate(result);return {r['metric']:r for r in result['metrics']}
def clock(value):return dict(original=value,precision='SECOND')
class Sprint4FoundationTest(unittest.TestCase):
    def blocked(self,p,metric='MTTR',reason=None):
        result=metrics(p)[metric];self.assertIsNone(result['value']);self.assertEqual(result['synthetic_status'],'NOT_ELIGIBLE')
        if reason:self.assertIn(reason,result['reasons'])
    def test_hand_reconciled_reference_and_original_lineage(self):
        p=fixture();before=copy.deepcopy(p);result=evaluate(p);ref=json.loads((ROOT/'reference-expected.synthetic.json').read_text())
        for key in ['MTBF','MTTR']:
            for field,value in ref[key.lower()].items():self.assertEqual(metrics(p)[key][field],value)
        self.assertEqual(p,before);self.assertEqual(result['source_lineage'],p)
        self.assertEqual(result['operational_eligibility'],'NOT_ELIGIBLE')
        self.assertTrue(any(r['reason']=='EXPLICIT_WAITING_EXCLUDED' for r in result['audit']))
        self.assertNotEqual(metrics(p)['MTBF']['numerator_hours'],'744')
    def test_schema_is_versioned_additive_strict_and_matches_models(self):
        schema=json.loads((ROOT/'packet.schema.json').read_text());Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(fixture());self.assertEqual(schema,Packet.model_json_schema())
        for key,value in [('contract_version','1.0'),('execution_mode','OPERATIONAL'),('mtbf',123)]:
            p=fixture();p[key]=value;self.blocked(p,'MTBF')
    def test_zero_failures_is_null_with_complete_exposure(self):
        p=fixture();p.update(failures=[],repairs=[],outages=[]);m=metrics(p)
        self.assertIsNone(m['MTBF']['value']);self.assertEqual(m['MTBF']['reasons'],['NO_FAILURES_OBSERVED']);self.assertEqual(m['MTBF']['numerator_hours'],'600')
        self.assertIsNone(m['MTTR']['value']);self.assertEqual(m['MTTR']['reasons'],['NO_COMPLETED_REPAIR_EPISODES'])
    def test_zero_hours_missing_hours_and_nonfinite_never_confused(self):
        p=fixture();p['exposures'][0]['operating_hours']='0';self.blocked(p,'MTBF','ZERO_OPERATING_EXPOSURE')
        for value in [None,False,0,600.0,'NaN','Infinity','-1','1e3']:
            p=fixture();p['exposures'][0]['operating_hours']=value;self.blocked(p,'MTBF')
    def test_missing_exposure_does_not_become_calendar_hours_or_block_independent_repair(self):
        p=fixture();p['exposures']=[];self.blocked(p,'MTBF');self.assertEqual(metrics(p)['MTTR']['value'],'2')
        for key in ['failure_inventory_complete','exposure_coverage_complete','repair_inventory_complete']:
            p=fixture();p[key]=False;self.blocked(p,'MTTR' if key.startswith('repair') else 'MTBF')
    def test_pm_cm_are_activities_not_automatically_failures(self):
        for work_type in ['PM','CM',None]:
            p=fixture();p['repairs']=[];p['outages']=[]
            for row in p['failures']:row.update(kind='MAINTENANCE_ACTIVITY',work_type=work_type)
            self.assertEqual(metrics(p)['MTBF']['reasons'],['NO_FAILURES_OBSERVED'])
        p=fixture();p['failures'][0]['qualification']='UNVERIFIED';self.blocked(p,'MTBF')
    def test_child_wo_shared_wo_and_repeated_status_do_not_define_denominator(self):
        p=fixture();self.assertEqual(metrics(p)['MTBF']['denominator'],2)
        p['failures'].append(copy.deepcopy(p['failures'][0]));self.assertEqual(metrics(p)['MTBF']['denominator'],2)
        self.assertTrue(any(r['reason']=='IDENTICAL_REPLAY_EXCLUDED' for r in evaluate(p)['audit']))
    def test_explicit_duplicate_preserved_and_conflicting_duplicate_blocks(self):
        p=fixture();d=copy.deepcopy(p['failures'][0]);d.update(record_id='SYNTHETIC:DUP',duplicate_of=d['record_id']);p['failures'].append(d)
        self.assertEqual(metrics(p)['MTBF']['denominator'],2)
        d['occurred_at']=clock('2026-01-05T09:00:00Z');self.blocked(p,'MTBF','CONTRADICTORY_DUPLICATE')
    def test_duplicate_cycle_missing_target_and_conflicting_replay(self):
        for change in ['cycle','missing','conflict']:
            p=fixture();d=copy.deepcopy(p['failures'][0])
            if change=='cycle':d['duplicate_of']=d['record_id']
            elif change=='missing':d['duplicate_of']='SYNTHETIC:MISSING'
            else:d['work_type']='OTHER'
            p['failures'].append(d);self.blocked(p,'MTBF')
    def test_explicit_supersession_preserves_prior_revision_and_rejects_latest_wins(self):
        p=fixture();old=copy.deepcopy(p['exposures'][0]);old['operating_hours']='500'
        p['exposures'][0].update(revision=2,supersedes_revision=1);p['exposures'].append(old)
        result=evaluate(p);self.assertEqual(metrics(p)['MTBF']['value'],'300');self.assertEqual(len(result['source_lineage']['exposures']),2)
        p['exposures'][0]['supersedes_revision']=None;self.blocked(p,'MTBF','UNRESOLVED_REVISION_CHAIN')
    def test_mixed_asset_scope_population_versions_and_units_rejected(self):
        for key in ['canonical_asset_id','site','organization','population_ref']:
            p=fixture();p['failures'][0]['scope'][key]='OTHER';self.blocked(p,'MTBF')
        for collection in ['failures','repairs','exposures','outages']:
            p=fixture();p[collection][0]['definition_version']='OTHER';self.blocked(p,'MTBF')
        p=fixture();p['exposures'][0]['unit']='min';self.blocked(p,'MTBF')
        p=fixture();p['scope']['canonical_asset_id']='asset:MAXIMO:REAL';self.blocked(p,'MTBF')
    def test_unqualified_proofs_and_pending_policy_never_grant_approval(self):
        for key in ['failure_inventory_evidence','exposure_coverage_evidence','repair_inventory_evidence']:
            p=fixture();p[key]['qualification']='UNVERIFIED';self.blocked(p,'MTTR' if key.startswith('repair') else 'MTBF')
        p=fixture();p['policy']['approval']='PENDING_ENGINEER_VALIDATION';self.blocked(p,'MTBF');self.blocked(p)
    def test_partial_naive_invalid_or_precision_contradictory_clocks_rejected(self):
        for value,precision in [(None,'UNKNOWN'),('2026-01-05','DATE'),('08:00:00','UNKNOWN'),('2026-01-05T08:00:00','SECOND'),('2026-02-30T08:00:00Z','SECOND'),('2026-01-05T08:00:00.1Z','SECOND')]:
            p=fixture();p['failures'][0]['occurred_at']=dict(original=value,precision=precision);self.blocked(p,'MTBF')
    def test_half_open_boundary_and_original_offsets(self):
        p=fixture();p['repairs']=[];p['outages']=[];p['failures'][0]['occurred_at']=clock('2026-01-01T07:00:00+07:00');p['failures'][1]['occurred_at']=p['window']['end']
        self.assertEqual(metrics(p)['MTBF']['denominator'],1);self.assertEqual(metrics(p)['MTBF']['value'],'600')
    def test_timezone_mismatch_unknown_zone_and_dst_offsets(self):
        for zone in ['MISSING/ZONE','America/New_York']:
            p=fixture();p['window']['timezone']=zone;self.blocked(p,'MTBF')
        p=fixture();p['window'].update(start=clock('2025-12-31T19:00:00-05:00'),end=clock('2026-01-31T19:00:00-05:00'),timezone='America/New_York');self.assertEqual(metrics(p)['MTBF']['value'],'300')
    def test_exposure_gaps_overlaps_bad_quality_and_excess_hours(self):
        for modify in [lambda e:e.update(operating_hours='900'),lambda e:e.update(quality='BAD'),lambda e:e.update(start=clock('2026-01-02T00:00:00Z'))]:
            p=fixture();modify(p['exposures'][0]);self.blocked(p,'MTBF')
        p=fixture();d=copy.deepcopy(p['exposures'][0]);d['record_id']='SYNTHETIC:OVERLAP';p['exposures'].append(d);self.blocked(p,'MTBF','EXPOSURE_GAP_OR_OVERLAP')
    def test_repair_duration_excludes_explicit_wait_and_planned_only_by_policy(self):
        p=fixture();self.assertEqual(metrics(p)['MTTR']['numerator_hours'],'4')
        p['repairs'][0]['intervals'][1]['kind']='PLANNED';self.assertEqual(metrics(p)['MTTR']['value'],'2')
        p['policy']['waiting_planned_rule']='PENDING';self.blocked(p,'MTTR','WAIT_PLANNED_POLICY_PENDING')
    def test_incomplete_censored_reopened_never_filled_from_now(self):
        for state in ['OPEN','CENSORED','REOPENED']:
            p=fixture();p['repairs'][0]['state']=state;self.blocked(p)
        p=fixture();p['repairs'][0]['restored_at']=dict(original=None,precision='UNKNOWN');self.blocked(p)
        p=fixture();p['repairs'][0]['reopened_from']='SYNTHETIC:REPAIR-Z';self.blocked(p)
    def test_repair_overlap_gap_before_failure_and_outside_window(self):
        for value in ['2026-01-05T08:30:00Z','2026-01-05T10:00:00Z']:
            p=fixture();p['repairs'][0]['intervals'][1]['start']=clock(value);self.blocked(p)
        p=fixture();p['failures'][0]['occurred_at']=clock('2026-01-05T10:00:00Z');self.blocked(p)
        p=fixture();p['repairs'][0]['restored_at']=clock('2026-02-02T00:00:00Z');self.blocked(p)
    def test_overlapping_episodes_and_outage_contradiction(self):
        p=fixture();p['outages']=[];p['failures'][1]['occurred_at']=p['failures'][0]['occurred_at'];p['repairs'][1]['repair_started_at']=clock('2026-01-05T08:00:00Z');p['repairs'][1]['restored_at']=clock('2026-01-05T10:00:00Z');p['repairs'][1]['intervals'][0].update(start=clock('2026-01-05T08:00:00Z'),end=clock('2026-01-05T10:00:00Z'));self.blocked(p,'MTTR','OVERLAPPING_ACTIVE_REPAIR_EPISODES')
        p=fixture();p['outages'][0]['end']=clock('2026-01-05T10:00:00Z');self.blocked(p,'MTTR','OUTAGE_REPAIR_CONTRADICTION')
    def test_order_independent_metrics_deterministic_arithmetic_and_no_mutation(self):
        p=fixture();a=evaluate(p)
        with localcontext() as ctx:ctx.prec=4;self.assertEqual(evaluate(p),a)
        p['failures'].reverse();p['repairs'].reverse();self.assertEqual(evaluate(p)['metrics'],a['metrics'])
    def test_payload_limits_and_raw_shape_do_not_raise_or_leak(self):
        for p in [{},None,{'credential':'SECRET_UNRELATED'}, {'label':'x'*(2*1024*1024+1)}]:
            result=evaluate(p);self.assertNotIn('SECRET_UNRELATED',json.dumps(result));self.assertIsNone(result['metrics'][0]['value'])
        p=fixture();p['failures']*=501;self.blocked(p,'MTBF')
    def test_engine_not_imported_by_application_and_legacy_unchanged(self):
        root=ROOT.parents[1]
        paths=list((root/'src').rglob('*.py'));self.assertGreater(len(paths),50)
        for path in paths:
            self.assertNotIn('contracts.sprint4',path.read_text())

    def test_review_clock_offset_and_utc_overflow_are_typed_rejections(self):
        for value in ['2026-01-05T08:00:00+00:99','0001-01-01T00:00:00+01:00','9999-12-31T23:59:59-01:00','2026-01-05T08:00:00-00:00']:
            for target in ['window','failure','repair']:
                p=fixture()
                if target=='window':p['window']['start']=clock(value)
                elif target=='failure':p['failures'][0]['occurred_at']=clock(value)
                else:p['repairs'][0]['intervals'][0]['start']=clock(value)
                self.blocked(p,'MTTR' if target=='repair' else 'MTBF')
    def test_review_ambient_decimal_traps_and_exponents_do_not_change_result(self):
        p=fixture();p['repairs'][1]['restored_at']=clock('2026-01-20T08:00:01Z');p['repairs'][1]['intervals'][0]['end']=p['repairs'][1]['restored_at'];expected=evaluate(p)
        with localcontext() as ctx:
            ctx.traps[Inexact]=True;ctx.Emax=1;ctx.Emin=-1;ctx.prec=2
            self.assertEqual(evaluate(p),expected)
    def test_review_zero_exposure_without_failures_is_not_observation_evidence(self):
        p=fixture();p.update(failures=[],repairs=[],outages=[]);p['exposures'][0]['operating_hours']='0';self.blocked(p,'MTBF','ZERO_OPERATING_EXPOSURE')
    def test_review_exposure_cannot_contradict_known_total_outage(self):
        p=fixture();p['exposures'][0]['operating_hours']='744';self.blocked(p,'MTBF','EXPOSURE_OUTAGE_CONTRADICTION')
    def test_review_multiple_restorations_require_reopened_policy(self):
        p=fixture();d=copy.deepcopy(p['repairs'][0]);d.update(record_id='SYNTHETIC:SECOND-RESTORE');p['repairs'].append(d);self.blocked(p,'MTTR','MULTIPLE_RESTORATIONS_FOR_FAILURE')

    def test_review_active_interval_segmentation_is_exactly_invariant(self):
        p=fixture();p['outages']=[];p['failures']=p['failures'][:1];p['repairs']=p['repairs'][:1]
        repair=p['repairs'][0];repair['restored_at']=clock('2026-01-05T09:00:00Z');interval=copy.deepcopy(repair['intervals'][0]);repair['intervals']=[interval]
        expected=metrics(p)['MTTR'];self.assertEqual(expected['value'],'1')
        repair['intervals']=[]
        for i,(a,b) in enumerate([('08:00','08:20'),('08:20','08:40'),('08:40','09:00')]):
            row=copy.deepcopy(interval);row.update(interval_id='SYNTHETIC:SPLIT-'+str(i),start=clock('2026-01-05T'+a+':00Z'),end=clock('2026-01-05T'+b+':00Z'));repair['intervals'].append(row)
        self.assertEqual(metrics(p)['MTTR'],expected);repair['intervals'].reverse();self.assertEqual(metrics(p)['MTTR'],expected)

    def test_visual_fixture_is_exact_engine_output_and_not_a_second_formula(self):
        actual=json.loads((ROOT.parents[1]/'web/fixtures/reliability-performance-result.synthetic.json').read_text())
        self.assertEqual(actual,evaluate(fixture()))
    def test_bounded_representative_population(self):
        import time
        p=fixture();p.update(repairs=[],outages=[]);base=copy.deepcopy(p['failures'][0]);p['failures']=[]
        for i in range(1000):
            row=copy.deepcopy(base);row['record_id']='SYNTHETIC:EVENT-'+str(i);p['failures'].append(row)
        start=time.perf_counter();result=metrics(p)['MTBF'];self.assertEqual(result['denominator'],1000);self.assertEqual(result['value'],'0.6');self.assertLess(time.perf_counter()-start,5,'gross synthetic regression budget, not operational SLA')

    def test_review_wait_active_interleaving_still_overlaps_episode_envelopes(self):
        p=fixture();p['outages']=[];p['failures'][1]['occurred_at']=clock('2026-01-05T09:00:00Z');repair=p['repairs'][1];repair.update(repair_started_at=clock('2026-01-05T09:00:00Z'),restored_at=clock('2026-01-05T11:00:00Z'));repair['intervals'][0].update(start=repair['repair_started_at'],end=repair['restored_at']);self.blocked(p,'MTTR','OVERLAPPING_REPAIR_EPISODES')

    def test_review_wait_planned_source_cannot_contradict_active_repair(self):
        for kind in ['WAITING','PLANNED']:
            p=fixture();p['outages'][0].update(kind=kind,end=clock('2026-01-05T09:00:00Z'));self.blocked(p,'MTTR','WAIT_PLANNED_ACTIVE_CONTRADICTION')

    def test_result_contract_is_versioned_and_keeps_operational_values_disabled(self):
        schema=json.loads((ROOT/'result.schema.json').read_text());self.assertEqual(schema,Result.model_json_schema());Draft202012Validator.check_schema(schema)
        for document in [fixture(),{}]:
            result=evaluate(document);Result.model_validate(result);Draft202012Validator(schema).validate(result)
        result=evaluate(fixture());result['operational_eligibility']='ELIGIBLE'
        with self.assertRaises(ValidationError):Result.model_validate(result)

    def test_review_window_iana_conversion_extremes_fail_closed(self):
        p=fixture();p['window'].update(start=clock('0001-01-01T00:00:00Z'),timezone='America/New_York');self.blocked(p,'MTBF','INVALID_WINDOW_OR_TIMEZONE')
        p=fixture();p['window'].update(start=clock('2026-01-01T14:00:00+14:00'),end=clock('9999-12-31T23:59:59Z'),timezone='Pacific/Kiritimati');self.blocked(p,'MTBF','INVALID_WINDOW_OR_TIMEZONE')
