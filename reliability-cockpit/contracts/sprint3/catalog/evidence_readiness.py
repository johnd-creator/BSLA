"""Offline decision/readiness tools. No source, persistence or KPI calculations.

Inputs are explicitly recorded evidence, not names to match. Output does not grant
permissions, approve a mapping, or authorize a source request.
"""
from collections import Counter
from copy import deepcopy
from datetime import datetime

CROSSWALK_STATES = {'VERIFIED', 'CANDIDATE', 'UNRESOLVED', 'FORBIDDEN'}
INPUT_STATES = {'AVAILABLE_VERIFIED', 'AVAILABLE_UNAPPROVED', 'MISSING', 'BLOCKED'}
REQUIRED_KPI_INPUTS = (
    'equipment_identity', 'observation_period', 'failure_event_identity',
    'failure_source_traceability', 'preventive_corrective_definition',
    'failure_vs_maintenance_definition', 'operating_exposure_hours',
    'exposure_source_quality', 'failure_start', 'repair_start', 'repair_end',
    'active_repair_vs_total_outage', 'incomplete_timestamps_policy',
    'overlap_policy', 'reopened_work_order_policy', 'duplicate_event_policy',
    'repeated_status_update_policy',
)


def crosswalk_inventory(rows):
    """Retain all bounded recorded relationships; downgrade ambiguity, never infer."""
    if len(rows) > 10000:
        raise ValueError('offline inventory exceeds explicit 10000-row limit')
    def ref(value):
        return isinstance(value,str) and 0 < len(value) <= 512 and value == value.strip()
    def aware(value):
        try:
            stamp=datetime.fromisoformat(value)
            return stamp.tzinfo is not None and stamp.utcoffset() is not None
        except (TypeError,ValueError):
            return False
    result = deepcopy(rows)
    af_counts = Counter((r.get('pi_source_ref'),r.get('pi_af_server_ref'),r.get('pi_af_database_ref'),r.get('pi_af_ref')) for r in rows)
    counts = Counter((r.get('canonical_asset_id'), r.get('site_code'), r.get('organization_code')) for r in rows)
    for row in result:
        state = row['recorded_status']
        if state not in CROSSWALK_STATES:
            raise ValueError('unrecognized recorded mapping status')
        conditions = set(row['conditions'])
        identity = (row.get('canonical_asset_id'), row.get('site_code'), row.get('organization_code'))
        if not all(ref(row.get(k)) for k in ['canonical_asset_id','site_code','organization_code','maximo_equipment_ref','pi_source_ref','pi_af_server_ref','pi_af_database_ref','pi_af_ref']):
            conditions.add('MISSING_IDENTITY')
        af_identity=(row.get('pi_source_ref'),row.get('pi_af_server_ref'),row.get('pi_af_database_ref'),row.get('pi_af_ref'))
        if all(af_identity) and af_counts[af_identity] > 1:
            conditions.add('CONFLICTING_IDENTITY')
        if counts[identity] > 1:
            conditions.add('DUPLICATE_IDENTITY')
        if not all(ref(row.get(k)) for k in ['mapping_evidence_ref','mapping_owner']) or not aware(row.get('mapping_verified_at')):
            conditions.add('MISSING_EVIDENCE')
        if state == 'FORBIDDEN' or 'SOURCE_FORBIDDEN' in conditions:
            decision = 'FORBIDDEN'
        elif conditions:
            decision = 'UNRESOLVED'
        else:
            decision = state  # CANDIDATE never becomes VERIFIED.
        row.update(decision_status=decision, conditions=sorted(conditions), conclusion_eligible=decision == 'VERIFIED')
    return result


def kpi_readiness(inputs):
    """Return completeness only. Even complete inputs require Sprint4 approval."""
    if set(inputs) != set(REQUIRED_KPI_INPUTS):
        raise ValueError('exact prerequisite inventory required')
    for row in inputs.values():
        if set(row) != {'status', 'evidence_ref', 'owner', 'definition_version'} or row['status'] not in INPUT_STATES:
            raise ValueError('invalid prerequisite evidence')
        if row['status'] == 'AVAILABLE_VERIFIED' and not all(isinstance(row[k],str) and row[k].strip() == row[k] and 0 < len(row[k]) <= 512 for k in ['evidence_ref','owner','definition_version']):
            raise ValueError('verification needs scoped evidence and version')
    incomplete = [key for key in REQUIRED_KPI_INPUTS if inputs[key]['status'] != 'AVAILABLE_VERIFIED']
    return {'contract_version': 'sprint3-readiness-1', 'status': 'NOT_ELIGIBLE',
            'input_completeness': 'INCOMPLETE' if incomplete else 'RECORDED_COMPLETE',
            'unqualified_inputs': incomplete, 'reason': 'SPRINT4_POLICY_AND_IMPLEMENTATION_NOT_AUTHORIZED'}
