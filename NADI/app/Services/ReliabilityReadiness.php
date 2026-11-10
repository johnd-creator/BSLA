<?php

namespace App\Services;

use App\Models\ReliabilityPolicy;
use Carbon\CarbonImmutable;

class ReliabilityReadiness
{
    public function assess(array $report, array $exposure, ?ReliabilityPolicy $policy): array
    {
        $rules = $policy?->rules ?? [];
        $q = $report['quality'];
        $range = ($report['period']['kind'] ?? 'year') !== 'year';
        $common = [];
        if (($rules['status'] ?? null) !== 'reviewed_local') {
            $common[] = 'LOCAL_METHOD_NOT_REVIEWED';
        }
        foreach (['required_function', 'failure_definition'] as $field) {
            if (mb_strlen(trim($rules[$field] ?? '')) < 5) {
                $common[] = strtoupper($field).'_UNDECIDED';
            }
        }
        if (($rules['failure_coverage'] ?? null) !== 'attested_complete') {
            $common[] = 'FAILURE_OBSERVATION_COVERAGE_UNKNOWN';
        }
        if (($rules['failure_scope'] ?? null) !== 'attested_same_function') {
            $common[] = 'FUNCTION_SCOPE_NOT_RECONCILED';
        }
        if ($policy && ($rules['failure_scope_hash'] ?? null) !== app(ReliabilityScope::class)->hashRows($report['events'])) {
            $common[] = 'FAILURE_SCOPE_ATTESTATION_STALE';
        }
        if (($rules['recurrence_policy'] ?? null) !== 'restored_before_recurrence') {
            $common[] = 'RECURRENCE_POLICY_UNDECIDED';
        }
        if (($rules['incomplete_policy'] ?? null) !== 'withhold') {
            $common[] = 'INCOMPLETE_EPISODE_POLICY_UNDECIDED';
        }
        if ($report['coverage']['local_rows_truncated']) {
            $common[] = 'LOCAL_EVIDENCE_LIMIT_REACHED';
        }
        foreach (['unknown_year', 'unreviewed', 'stale', 'uncertain', 'missing_failure_time', 'conflicting_intervals'] as $key) {
            if ($q[$key] > 0) {
                $common[] = strtoupper($key);
            }
        }
        $failures = array_values(array_filter($report['events'], fn ($e) => $e['state'] === 'failure' && $e['failure_at']));
        usort($failures, fn ($a, $b) => CarbonImmutable::parse($a['failure_at'])->timestamp <=> CarbonImmutable::parse($b['failure_at'])->timestamp);
        $previous = null;
        $recurrenceIds = [];
        $unrestored = null;
        foreach ($failures as $failure) {
            if ($previous && ($failure['in_year'] || $previous['in_year']) && (! $previous['restored_at'] || CarbonImmutable::parse($previous['restored_at'])->gte(CarbonImmutable::parse($failure['failure_at'])))) {
                $common[] = 'RECURRENCE_NOT_ESTABLISHED';
                $recurrenceIds[] = $previous['event_id'];
                $recurrenceIds[] = $failure['event_id'];
            }
            if ($unrestored && ($failure['in_year'] || $unrestored['in_year'])) {
                $common[] = 'RECURRENCE_NOT_ESTABLISHED';
                $recurrenceIds[] = $unrestored['event_id'];
                $recurrenceIds[] = $failure['event_id'];
            }
            if (! $failure['restored_at']) {
                $unrestored ??= $failure;
            }
            $previous = $failure;
        }
        if ($q['failure'] === 0) {
            $common[] = 'NO_REVIEWED_FAILURES';
        }
        $mtbf = $common;
        if (! in_array($rules['exposure_basis'] ?? null, ['run_only', 'run_and_standby'], true)) {
            $mtbf[] = 'EXPOSURE_BASIS_UNDECIDED';
        }
        if (! isset($rules['minimum_coverage'])) {
            $mtbf[] = 'MINIMUM_OPERATING_COVERAGE_UNDECIDED';
        } elseif ($exposure['coverage_percent'] === null || $exposure['coverage_percent'] < (float) $rules['minimum_coverage']) {
            $mtbf[] = 'OPERATING_COVERAGE_BELOW_RULE';
        }
        if (! ($range ? $report['period']['is_closed_period'] : $report['period']['is_closed_calendar_year'])) {
            $mtbf[] = $range ? 'SELECTED_PERIOD_NOT_CLOSED' : 'FULL_CALENDAR_YEAR_NOT_CLOSED';
        }
        if ($policy && CarbonImmutable::parse($rules['failure_scope_checked_at'] ?? $policy->created_at)->lt(CarbonImmutable::parse($report['period']['end_exclusive']))) {
            $mtbf[] = $range ? 'FAILURE_CENSUS_DOES_NOT_COVER_SELECTED_PERIOD' : 'FAILURE_CENSUS_DOES_NOT_COVER_FULL_YEAR';
        }
        if ($exposure['truncated']) {
            $mtbf[] = 'OPERATING_LOG_LIMIT_REACHED';
        }
        if ($exposure['operating_seconds'] === null) {
            $mtbf[] = 'OPERATING_EXPOSURE_NOT_AVAILABLE';
        }
        // Never scale sparse RUN records to a whole-year failure denominator.
        // Configured minimum is reported but not a license to fill unknown time.
        foreach (['GAP', 'UNKNOWN', 'OVERLAP'] as $state) {
            if ($exposure['seconds'][$state] > 0) {
                $mtbf[] = 'OPERATING_'.$state;
            }
        }
        $exposureSeconds = $exposure['operating_seconds'];
        if ($exposureSeconds !== null && ($rules['exposure_basis'] ?? null) === 'run_and_standby') {
            $exposureSeconds += $exposure['seconds']['STANDBY'];
        }
        if ($exposureSeconds !== null && $exposureSeconds <= 0) {
            $mtbf[] = 'NO_POSITIVE_ELIGIBLE_EXPOSURE';
        }
        foreach ($failures as $failure) {
            if (! $failure['in_year']) {
                continue;
            }
            $onset = CarbonImmutable::parse($failure['failure_at'])->timestamp;
            $eligible = false;
            foreach ($exposure['segments'] as $segment) {
                // The end boundary may be the instant RUN changes to failed STOP.
                if (CarbonImmutable::parse($segment['start'])->timestamp < $onset && CarbonImmutable::parse($segment['end'])->timestamp >= $onset && in_array($segment['state'], ($rules['exposure_basis'] ?? null) === 'run_and_standby' ? ['RUN', 'STANDBY'] : ['RUN'], true)) {
                    $eligible = true;
                    break;
                }
            }
            if (! $eligible) {
                $mtbf[] = 'FAILURE_OUTSIDE_VERIFIED_EXPOSURE';
            }
        }
        $active = $restoration = $common;
        foreach (['repair_ongoing', 'repair_unknown', 'repair_not_applicable'] as $key) {
            if ($q[$key] > 0) {
                $active[] = strtoupper($key);
            }
        }
        if ($report['reviewed_samples']['mean_active_repair']['denominator_completed_episodes'] !== $q['failure']) {
            $active[] = 'ACTIVE_REPAIR_COHORT_INCOMPLETE';
        }
        if ($q['restoration_missing'] > 0) {
            $restoration[] = 'RESTORATION_INCOMPLETE';
        }
        if ($report['reviewed_samples']['mean_restoration']['denominator_completed_episodes'] !== $q['failure']) {
            $restoration[] = 'RESTORATION_COHORT_INCOMPLETE';
        }
        $mttr = match ($rules['mttr_basis'] ?? null) {
            'active_repair' => $active, 'restoration' => $restoration, default => [...$common, 'MTTR_BASIS_UNDECIDED'],
        };
        $status = fn ($blockers) => ['status' => $blockers ? 'INSUFFICIENT_LOCAL_EVIDENCE' : 'LOCAL_EVIDENCE_READY', 'blockers' => array_values(array_unique($blockers))];

        return ['recurrence_event_ids' => array_values(array_unique($recurrenceIds)), 'method_version' => $range ? ReliabilityPolicy::RANGE_SCHEMA : ReliabilityPolicy::SCHEMA, 'policy' => $policy ? ['id' => $policy->id, 'revision' => $policy->revision, 'actor_id' => $policy->created_by, 'created_at' => $policy->created_at->toIso8601String(), 'rules' => $rules, 'evidence' => $policy->evidence, 'reason' => $policy->reason] : null,
            'mtbf' => [...$status($mtbf), 'eligible_operating_seconds' => $exposureSeconds, 'reviewed_failure_count' => $q['failure']],
            'mttr' => [...$status($mttr), 'basis' => $rules['mttr_basis'] ?? 'undecided', 'operating_exposure_required' => false],
            'active_repair' => $status($active), 'restoration' => $status($restoration),
            'failure_coverage' => [
                'status' => ($rules['failure_coverage'] ?? null) !== 'attested_complete' ? 'UNKNOWN' : (in_array('FAILURE_SCOPE_ATTESTATION_STALE', $common, true) ? 'STALE' : (($rules['status'] ?? null) === 'reviewed_local' ? 'ATTESTED_LOCAL' : 'UNKNOWN')),
                'checked_at' => $rules['failure_scope_checked_at'] ?? null,
            ],
            'official_kpi' => ['status' => 'REQUIRES_SUPERVISOR_DECISION', 'blockers' => ['SUPERVISOR_APPROVAL_REQUIRED']],
            'meaning' => ($range ? 'Exact range method and attestation; no annual attestation is inherited. ' : '').'Readiness is local evidence sufficiency, not organizational approval. Failure census attestation is separate from operating-state coverage. WO/historian availability is not an MTTR gate. Full annual MTBF requires complete non-conflicting exposure, never calendar extrapolation.'];
    }
}
