<?php

namespace App\Services;

use App\Models\ReliabilityPolicy;
use App\Models\ReliabilityReview;
use Carbon\CarbonImmutable;
use Throwable;

/** Deterministic calculation over an already captured local evidence report. */
class ReliabilityCalculator
{
    public const VERSION = 'nadi-reliability-calculation-v2';

    public function calculate(array $report): array
    {
        $readiness = $report['readiness'];
        $policy = $readiness['policy'];
        $rules = $policy['rules'] ?? [];
        $events = $segments = [];
        $failureIds = $repairIds = $restorationIds = [];
        $repairSeconds = $restorationSeconds = 0;
        $invalid = $invalidRepair = $invalidRestoration = [];
        $recurrence = $readiness['recurrence_event_ids'] ?? [];
        $conflicts = array_unique([...$report['overlap_event_ids'], ...$recurrence]);
        foreach ($report['events'] as $event) {
            $reasons = [];
            if ($event['state'] !== 'failure') {
                $reasons[] = strtoupper($event['state']);
            }
            if (! $event['in_year']) {
                $reasons[] = $event['date'] === null ? 'UNKNOWN_YEAR' : 'OUTSIDE_ONSET_YEAR';
            }
            if (! $event['failure_at']) {
                $reasons[] = 'MISSING_EXACT_ONSET';
            }
            if (in_array($event['event_id'], $conflicts, true)) {
                $reasons[] = 'CONFLICT_OR_UNRESOLVED_RECURRENCE';
            }
            if ($event['state'] === 'failure' && (($event['review_event_version'] ?? null) !== $event['event_version'] || ($event['review_rule_version'] ?? null) !== ReliabilityReview::RULE)) {
                $reasons[] = 'REVIEW_BASIS_MISMATCH';
            }
            $active = $restoration = null;
            $repairInvalid = $restorationInvalid = false;
            $onset = $restored = null;
            try {
                $onset = $event['failure_at'] ? CarbonImmutable::parse($event['failure_at']) : null;
            } catch (Throwable) {
                $reasons[] = 'INVALID_ONSET_EVIDENCE';
                if ($event['in_year'] && $event['state'] === 'failure') {
                    $invalid[] = 'INVALID_ONSET_EVIDENCE';
                }
            }
            try {
                $restored = $event['restored_at'] ? CarbonImmutable::parse($event['restored_at']) : null;
                if ($onset && $restored) {
                    if ($restored->lt($onset)) {
                        throw new \UnexpectedValueException('Reversed restoration');
                    }
                    $restoration = (int) $onset->diffInSeconds($restored);
                }
            } catch (Throwable) {
                $restorationInvalid = true;
                $restored = null;
            }
            try {
                if ($event['repair_state'] === 'completed' && $event['active_intervals']) {
                    $active = 0;
                    $previousEnd = null;
                    foreach ($event['active_intervals'] as $interval) {
                        $start = CarbonImmutable::parse($interval['start']);
                        $end = CarbonImmutable::parse($interval['end']);
                        $seconds = (int) $start->diffInSeconds($end);
                        if ($end->lt($start) || ($onset && $start->lt($onset)) || ($restored && $end->gt($restored)) || ($previousEnd && $start->lt($previousEnd)) || $seconds !== $interval['seconds']) {
                            throw new \UnexpectedValueException('Inconsistent repair evidence');
                        }
                        $active += $seconds;
                        $previousEnd = $end;
                    }
                }
            } catch (Throwable) {
                $repairInvalid = true;
                $active = null;
            }
            $eligible = ! $reasons;
            if ($eligible && $repairInvalid) {
                $invalidRepair[] = 'INVALID_TIMING_EVIDENCE';
            }
            if ($eligible && $restorationInvalid) {
                $invalidRestoration[] = 'INVALID_TIMING_EVIDENCE';
            }
            if ($eligible) {
                $failureIds[] = $event['event_id'];
                if ($active !== null) {
                    $repairIds[] = $event['event_id'];
                    $repairSeconds += $active;
                }
                if ($restoration !== null) {
                    $restorationIds[] = $event['event_id'];
                    $restorationSeconds += $restoration;
                }
            }
            $events[] = ['event_id' => $event['event_id'], 'reference' => $event['reference'], 'event_version' => $event['event_version'],
                'reviewer_id' => $event['reviewer_id'], 'reviewed_at' => $event['reviewed_at'],
                'review_id' => $event['review_id'], 'review_revision' => $event['review_revision'], 'review_rule_version' => $event['review_rule_version'] ?? null,
                'state' => $event['state'], 'onset' => $event['failure_at'], 'restored_at' => $event['restored_at'],
                'month' => $event['failure_at'] && $event['in_year'] ? (int) substr($event['date'], 5, 2) : null,
                'category' => $event['observation']['event_type'] ?? 'unknown', 'eligible_failure' => $eligible,
                'exclusion_reasons' => array_values(array_unique($reasons)), 'active_repair_seconds' => $eligible ? $active : null,
                'restoration_seconds' => $eligible ? $restoration : null, 'active_repair_exclusion' => $repairInvalid ? 'INVALID_TIMING_EVIDENCE' : ($active === null ? 'INCOMPLETE_OR_NOT_APPLICABLE' : null),
                'restoration_exclusion' => $restorationInvalid ? 'INVALID_TIMING_EVIDENCE' : ($restoration === null ? 'RESTORATION_INCOMPLETE' : null),
                'active_intervals' => $event['active_intervals'], 'required_function' => $event['required_function'],
                'evidence' => $event['evidence'], 'timing_evidence' => $event['timing_evidence'], 'work_orders' => $event['work_orders']];
        }
        $operatingSeconds = 0;
        $segmentInvalid = false;
        $periodStart = CarbonImmutable::parse($report['period']['start_inclusive'])->timestamp;
        $periodEnd = CarbonImmutable::parse($report['period']['end_exclusive'])->timestamp;
        $previousEnd = $periodStart;
        foreach ($report['manual_operating']['segments'] as $index => $segment) {
            $start = CarbonImmutable::parse($segment['start'])->timestamp;
            $end = CarbonImmutable::parse($segment['end'])->timestamp;
            $seconds = $end - $start;
            $valid = $start === $previousEnd && $end > $start && $start >= $periodStart && $end <= $periodEnd && $seconds === $segment['seconds'];
            $eligible = $valid && in_array($segment['state'], ($rules['exposure_basis'] ?? null) === 'run_and_standby' ? ['RUN', 'STANDBY'] : ['RUN'], true);
            $segmentInvalid = $segmentInvalid || ! $valid;
            $operatingSeconds += $eligible ? $seconds : 0;
            $segments[] = [...$segment, 'index' => $index + 1, 'eligible' => $eligible, 'eligible_seconds' => $eligible ? $seconds : 0,
                'exclusion_reason' => $eligible ? null : ($valid ? $segment['state'].'_NOT_ELIGIBLE_EXPOSURE' : 'INVALID_SEGMENT_SEQUENCE')];
            $previousEnd = $end;
        }
        foreach ($events as &$event) {
            $event['matched_exposure_segments'] = [];
            if ($event['eligible_failure']) {
                $onset = CarbonImmutable::parse($event['onset'])->timestamp;
                foreach ($segments as $segment) {
                    if ($segment['eligible'] && CarbonImmutable::parse($segment['start'])->timestamp < $onset && CarbonImmutable::parse($segment['end'])->timestamp >= $onset) {
                        $event['matched_exposure_segments'][] = $segment['index'];
                    }
                }
            }
            $event['mtbf_exposure_eligible'] = $event['eligible_failure'] && (bool) $event['matched_exposure_segments'];
        }
        unset($event);
        $segmentInvalid = $segmentInvalid || $previousEnd !== $periodEnd;
        $methodInvalid = $policy && ($rules['schema_version'] ?? null) !== ReliabilityPolicy::SCHEMA;
        $shared = [...$invalid, ...($methodInvalid ? ['UNSUPPORTED_METHOD_VERSION'] : [])];
        $metric = function (string $basis, ?int $seconds, array $ids, array $blockers, string $formula) use ($shared): array {
            $blockers = array_values(array_unique([...$blockers, ...$shared, ...($seconds === null ? ['NUMERATOR_NOT_AVAILABLE'] : []), ...(! $ids ? ['NO_ELIGIBLE_DENOMINATOR'] : [])]));

            return ['value' => $blockers ? null : round($seconds / count($ids) / 3600, 6), 'unit' => 'hours', 'status' => $blockers ? 'INSUFFICIENT_DATA' : 'PILOT_CALCULATED',
                'basis' => $basis, 'formula' => $formula, 'numerator_seconds' => $seconds, 'denominator_episodes' => count($ids),
                'event_ids' => $ids, 'blockers' => $blockers, 'numerator_is_partial' => (bool) $blockers];
        };
        $mtbfBlockers = [...$readiness['mtbf']['blockers'], ...($segmentInvalid ? ['INVALID_EXPOSURE_SEQUENCE'] : [])];
        if ($readiness['mtbf']['eligible_operating_seconds'] !== null && $operatingSeconds !== $readiness['mtbf']['eligible_operating_seconds']) {
            $mtbfBlockers[] = 'EXPOSURE_RECONCILIATION_MISMATCH';
        }
        if (count($failureIds) !== $report['quality']['failure']) {
            $mtbfBlockers[] = 'FAILURE_COHORT_RECONCILIATION_MISMATCH';
        }
        $pilot = [
            'mtbf' => $metric('operating_exposure_per_failure', $report['manual_operating']['operating_seconds'] === null ? null : $operatingSeconds, $failureIds, $mtbfBlockers, 'eligible_operating_seconds / eligible_failures / 3600'),
            'active_repair' => $metric('active_repair', $repairIds ? $repairSeconds : null, $repairIds, [...$readiness['active_repair']['blockers'], ...$invalidRepair], 'completed_active_repair_seconds / completed_repair_episodes / 3600'),
            'restoration' => $metric('restoration', $restorationIds ? $restorationSeconds : null, $restorationIds, [...$readiness['restoration']['blockers'], ...$invalidRestoration], 'completed_restoration_seconds / completed_restoration_episodes / 3600'),
        ];
        $pilot['mttr'] = match ($rules['mttr_basis'] ?? null) {
            'active_repair' => $pilot['active_repair'], 'restoration' => $pilot['restoration'],
            default => $metric('undecided', null, [], $readiness['mttr']['blockers'], 'MTTR definition must be selected'),
        };
        // A local method/review is not organizational authority. This boundary is
        // deliberately separate from arithmetic and cannot be promoted by a POST.
        $official = [];
        foreach (['mtbf', 'mttr'] as $key) {
            $official[$key] = ['value' => null, 'unit' => 'hours', 'status' => 'NOT_AUTHORIZED', 'data_ready' => $pilot[$key]['status'] === 'PILOT_CALCULATED',
                'blockers' => array_values(array_unique([...$pilot[$key]['blockers'], 'SUPERVISOR_APPROVAL_REQUIRED']))];
        }
        $result = ['engine_version' => self::VERSION, 'asset_ref' => $report['asset_ref'], 'period' => $report['period'],
            'policy_id' => $policy['id'] ?? null, 'policy_revision' => $policy['revision'] ?? null, 'method_version' => $rules['schema_version'] ?? null,
            'pilot' => $pilot, 'official' => $official, 'event_trace' => $events, 'exposure_trace' => $segments,
            'operating_records' => $report['manual_operating']['records'],
            'assurance' => 'Local pilot arithmetic only. Supervisor approval is a separate versioned decision, never inferred by this pure calculation. WO duration and calendar hours are never substituted. Partial numerators are trace totals, not publishable KPI.'];
        $basis = ['engine_version' => self::VERSION, 'period' => $report['period'], 'asset_ref' => $report['asset_ref'], 'policy' => $policy,
            'events' => $report['events'], 'manual_operating' => $report['manual_operating'], 'readiness' => $report['readiness']];
        $result['basis_hash'] = hash('sha256', json_encode($basis, JSON_THROW_ON_ERROR));
        $result['calculation_hash'] = hash('sha256', json_encode($result, JSON_THROW_ON_ERROR));

        return $result;
    }
}
