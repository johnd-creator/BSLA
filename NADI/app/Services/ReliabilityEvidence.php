<?php

namespace App\Services;

use App\Models\AssetDisruption;
use App\Models\PdmActivity;
use App\Models\ReliabilityReview;
use Carbon\CarbonImmutable;
use Illuminate\Support\Facades\DB;
use Throwable;

class ReliabilityEvidence
{
    public const ZONE = 'Asia/Jakarta';

    public const LIMIT = 2000;

    public function report(string $asset, int $year, ReliabilityMart $mart): array
    {
        $identity = $wo = null;
        try {
            $identity = $mart->historyAsset($asset);
            $wo = $mart->annualWorkOrders($asset, ! $identity['registered']);
        } catch (Throwable) {
            // A source outage never removes local evidence and never becomes zero.
        }

        // Source HTTP is already finished. Keep all local evidence reads in one
        // SQLite snapshot so concurrent corrections cannot mix record versions.
        $connection = DB::connection();
        if ($connection->getDriverName() !== 'sqlite' || $connection->transactionLevel() > 0) {
            return $connection->transaction(fn () => $this->localReport($asset, $year, $identity, $wo));
        }
        // Laravel uses IMMEDIATE for writes. A standalone evidence read instead
        // starts PDO's deferred SQLite transaction without changing that policy.
        // All owning-store queries use this same PDO; there is no read replica.
        $pdo = $connection->getPdo();
        $pdo->beginTransaction();
        try {
            $report = $this->localReport($asset, $year, $identity, $wo);
            $pdo->commit();

            return $report;
        } catch (Throwable $error) {
            if ($pdo->inTransaction()) {
                $pdo->rollBack();
            }
            throw $error;
        }
    }

    private function localReport(string $asset, int $year, ?array $identity, ?array $wo): array
    {
        $events = AssetDisruption::forAsset($asset)->with(['members', 'workOrders'])->orderBy('id')->limit(self::LIMIT + 1)->get();
        $truncated = $events->count() > self::LIMIT;
        $events = $events->take(self::LIMIT);
        $latestIds = ReliabilityReview::where('asset_ref', $asset)->whereIn('asset_disruption_id', $events->pluck('id'))->selectRaw('MAX(id) as id')->groupBy('asset_disruption_id')->pluck('id');
        $reviews = ReliabilityReview::whereIn('id', $latestIds)->get()->keyBy('asset_disruption_id');
        $start = CarbonImmutable::create($year, 1, 1, 0, 0, 0, self::ZONE);
        $end = $start->addYear();
        $rows = [];
        $quality = array_fill_keys(['all_local_observations', 'in_year', 'unknown_year', 'out_of_year', 'voided', 'unreviewed', 'stale', 'uncertain', 'failure', 'not_failure', 'duplicate', 'date_only', 'missing_failure_time', 'restoration_complete', 'restoration_missing', 'repair_complete', 'repair_ongoing', 'repair_unknown', 'repair_not_applicable', 'cross_year_restoration', 'conflicting_intervals'], 0);
        $active = $restoration = $allRestoration = $allRepair = [];
        foreach ($events as $event) {
            $review = $reviews->get($event->id);
            $state = $this->state($event, $review, $events, $reviews);
            $currentFailure = $state === 'failure';
            $basis = $currentFailure && $review->failure_at ? 'REVIEWED_FAILURE_ONSET' : ($event->occurred_at ? 'OBSERVATION_INSTANT' : ($event->occurred_on ? 'OBSERVATION_LITERAL_DATE' : 'UNKNOWN'));
            $date = $currentFailure && $review->failure_at ? $review->failure_at->setTimezone(self::ZONE)->format('Y-m-d') : ($event->occurred_at?->setTimezone(self::ZONE)->format('Y-m-d') ?? $event->occurred_on);
            $inYear = $date !== null && substr($date, 0, 4) === (string) $year;
            $quality['all_local_observations']++;
            if ($state === 'voided') {
                $quality['voided']++;
            } elseif ($date === null) {
                $quality['unknown_year']++;
            } elseif (! $inYear) {
                $quality['out_of_year']++;
            } else {
                $quality['in_year']++;
                $quality[$state]++;
                $quality['date_only'] += $basis === 'OBSERVATION_LITERAL_DATE' ? 1 : 0;
            }
            $row = ['event_id' => $event->id, 'reference' => $event->reference(), 'event_version' => $event->version,
                'observation' => [...$event->only(['asset_ref', 'event_type', 'description', 'known_cause', 'impact', 'impact_note', 'occurred_on', 'restored_on', 'timezone', 'work_order_ref', 'evidence_note', 'status']), 'occurred_at' => $event->occurred_at?->toIso8601String(), 'restored_at' => $event->restored_at?->toIso8601String(), 'members' => $event->members->map(fn ($member) => ['asset_ref' => $member->asset_ref, 'role' => $member->role])->all()],
                'asset_role' => $event->roleFor($asset), 'state' => $state, 'date' => $date, 'date_basis' => $basis, 'in_year' => $inYear,
                'review_id' => $review?->id, 'review_revision' => $review?->revision, 'reviewer_id' => $review?->created_by,
                'reviewed_at' => $review?->created_at?->toIso8601String(), 'required_function' => $review?->required_function,
                'evidence' => $review?->evidence, 'reason' => $review?->reason, 'duplicate_of' => $review?->duplicate_of,
                'failure_at' => $review?->failure_at?->toIso8601String(), 'restored_at' => $review?->restored_at?->toIso8601String(),
                'repair_state' => $review?->repair_state, 'active_intervals' => $review?->active_intervals ?? [], 'timing_evidence' => $review?->timing_evidence,
                'work_orders' => $event->workOrders->map(fn ($link) => ['asset_ref' => $link->asset_ref, 'matches_selected_asset' => $link->asset_ref === $asset, 'work_order_ref' => $link->work_order_ref, 'record_ref' => $link->record_ref, 'relation_state' => $link->relation_state, 'note' => $link->note, 'identity_checked_at' => $link->identity_checked_at?->toIso8601String()])->all(),
            ];
            if ($currentFailure) {
                if ($review->failure_at && $review->restored_at) {
                    $allRestoration[] = ['event_id' => $event->id, 'start' => $review->failure_at->timestamp, 'end' => $review->restored_at->timestamp];
                }
                foreach ($review->active_intervals as $interval) {
                    $allRepair[] = ['event_id' => $event->id, 'start' => CarbonImmutable::parse($interval['start'])->timestamp, 'end' => CarbonImmutable::parse($interval['end'])->timestamp];
                }
            }
            if ($currentFailure && $inYear) {
                $quality['missing_failure_time'] += $review->failure_at ? 0 : 1;
                if ($review->failure_at && $review->restored_at) {
                    $quality['restoration_complete']++;
                    $quality['cross_year_restoration'] += $review->restored_at->gte($end) ? 1 : 0;
                    $restoration[] = ['event_id' => $event->id, 'start' => $review->failure_at->timestamp, 'end' => $review->restored_at->timestamp, 'seconds' => (int) $review->failure_at->diffInSeconds($review->restored_at)];
                } else {
                    $quality['restoration_missing']++;
                }
                $quality[match ($review->repair_state) {
                    'completed' => 'repair_complete', 'ongoing' => 'repair_ongoing', 'not_applicable' => 'repair_not_applicable', default => 'repair_unknown'
                }]++;
                if ($review->repair_state === 'completed' && $review->active_intervals && $review->failure_at) {
                    $active[] = ['event_id' => $event->id, 'intervals' => $review->active_intervals, 'seconds' => array_sum(array_column($review->active_intervals, 'seconds'))];
                }
            }
            $rows[] = $row;
        }
        // Check all retained years: a previous-year episode may overlap this cohort.
        $overlap = array_values(array_unique([...$this->overlappingEvents($allRestoration), ...$this->overlappingEvents($allRepair)]));
        $quality['conflicting_intervals'] = count($overlap);
        $blockers = ['OPERATING_EXPOSURE_NOT_AVAILABLE', 'ORGANIZATION_DEFINITION_AND_POPULATION_NOT_APPROVED', 'OBSERVATION_COVERAGE_NOT_ESTABLISHED'];
        if (! $identity) {
            $blockers[] = 'ASSET_SOURCE_UNAVAILABLE';
        }
        if (! $wo) {
            $blockers[] = 'WO_SOURCE_UNAVAILABLE';
        }
        if ($truncated) {
            $blockers[] = 'LOCAL_EVIDENCE_LIMIT_REACHED';
        }
        foreach (['unknown_year', 'unreviewed', 'stale', 'uncertain', 'missing_failure_time', 'restoration_missing', 'repair_ongoing', 'repair_unknown', 'conflicting_intervals'] as $key) {
            if ($quality[$key] > 0) {
                $blockers[] = strtoupper($key);
            }
        }
        if ($quality['in_year'] === 0) {
            $blockers[] = 'NO_LOCAL_OBSERVATIONS_IN_PERIOD';
        }
        $sample = function (array $episodes) use ($overlap, $truncated): array {
            $excluded = array_values(array_filter($episodes, fn ($episode) => in_array($episode['event_id'], $overlap, true)));
            $eligible = array_values(array_filter($episodes, fn ($episode) => ! in_array($episode['event_id'], $overlap, true)));
            $seconds = array_sum(array_column($eligible, 'seconds'));

            return ['value' => ! $truncated && count($eligible) ? round($seconds / count($eligible) / 3600, 6) : null, 'unit' => 'hours', 'status' => $truncated ? 'PARTIAL' : (count($eligible) ? 'REVIEWED_LOCAL_SAMPLE_ONLY' : 'NOT_AVAILABLE'), 'numerator_seconds' => $truncated || ! count($eligible) ? null : $seconds, 'denominator_completed_episodes' => count($eligible), 'excluded_overlap_episodes' => count($excluded), 'event_ids' => array_column($eligible, 'event_id')];
        };
        $pdm = PdmActivity::where('asset_ref', $asset)->whereBetween('measured_on', [$year.'-01-01', $year.'-12-31']);
        $pdmData = ['count' => (clone $pdm)->count(), 'date_only' => (clone $pdm)->where('time_precision', 'date')->count(), 'linked_analysis' => (clone $pdm)->whereHas('inspection')->count(), 'date_basis' => 'MEASURED_LITERAL_DATE', 'meaning' => 'Local measurements, not failure or continuous operating exposure'];
        $fingerprint = hash_init('sha256');
        foreach ((clone $pdm)->with('inspection')->orderBy('id')->lazyById(200) as $activity) {
            hash_update($fingerprint, json_encode([$activity->id, $activity->version, $activity->updated_at, $activity->inspection?->id, $activity->inspection?->version, $activity->inspection?->updated_at], JSON_THROW_ON_ERROR));
        }
        $pdmData['evidence_hash'] = hash_final($fingerprint);
        $woYear = $wo ? (collect($wo['years'])->firstWhere('year', $year) ?? ['year' => $year, 'work_orders' => 0, 'work_types' => [], 'statuses' => []]) : null;
        $report = [
            'schema_version' => 'nadi.reliability-evidence.v1', 'rule_version' => ReliabilityReview::RULE, 'observed_at' => now()->toIso8601String(),
            'asset_ref' => $asset, 'asset' => $identity ? array_intersect_key($identity, array_flip(['canonical_id', 'source_asset_number', 'description', 'registered', 'hierarchy_category'])) : null,
            'period' => ['year' => $year, 'timezone' => self::ZONE, 'start_inclusive' => $start->toIso8601String(), 'end_exclusive' => $end->toIso8601String(), 'is_closed_calendar_year' => $end->lte(now()), 'episode_basis' => 'Reviewed failure onset when known; otherwise observation date for review queue. Full completed episode belongs to onset year, never clipped or double-counted in later year.'],
            'population' => 'Exact asset only; no hierarchy propagation or sum across assets', 'source_freshness' => 'UNKNOWN',
            'coverage' => ['local_rows_truncated' => $truncated, 'observation_coverage' => 'UNKNOWN', 'operating_seconds' => null, 'covered_seconds' => null, 'coverage_percent' => null, 'historian' => 'NOT_INTEGRATED', 'manual_operating_evidence' => 'NOT_RECORDED'],
            'metrics' => ['mtbf' => ['value' => null, 'unit' => 'hours', 'status' => 'NOT_READY'], 'mttr' => ['value' => null, 'unit' => 'hours', 'status' => 'NOT_READY'], 'availability' => ['value' => null, 'unit' => 'percent', 'status' => 'NOT_READY']],
            'reviewed_samples' => ['mean_active_repair' => $sample($active), 'mean_restoration' => $sample($restoration)],
            'quality' => $quality, 'blockers' => $blockers, 'overlap_event_ids' => $overlap,
            'work_orders' => ['state' => $wo ? 'RETAINED_MART_CONTEXT' : 'UNAVAILABLE', 'date_basis' => 'ACTUAL_START', 'timezone' => self::ZONE, 'selected_year' => $woYear, 'all_year_counts' => $wo['counts'] ?? null, 'meaning' => 'WO identities, not failure occurrences. Actual elapsed and labor are not repair duration.'],
            'pdm' => $pdmData, 'events' => $rows,
        ];
        $hashBasis = $report;
        unset($hashBasis['observed_at']);
        $report['evidence_hash'] = hash('sha256', json_encode($hashBasis, JSON_THROW_ON_ERROR));

        return $report;
    }

    private function state(AssetDisruption $event, ?ReliabilityReview $review, $events, $reviews): string
    {
        if ($event->status !== 'recorded') {
            return 'voided';
        }
        if (! $review) {
            return 'unreviewed';
        }
        if ($review->event_version !== $event->version || $review->rule_version !== ReliabilityReview::RULE) {
            return 'stale';
        }
        if ($review->classification === 'duplicate') {
            $target = $events->firstWhere('id', $review->duplicate_of);
            $targetReview = $reviews->get($review->duplicate_of);
            if (! $target || $target->status !== 'recorded' || $target->version !== $review->duplicate_version || ! $targetReview || $targetReview->classification !== 'failure' || $targetReview->revision !== $review->duplicate_review_revision || $targetReview->event_version !== $target->version || $targetReview->rule_version !== ReliabilityReview::RULE) {
                return 'stale';
            }
        }

        return $review->classification;
    }

    private function overlappingEvents(array $intervals): array
    {
        usort($intervals, fn ($a, $b) => $a['start'] <=> $b['start']);
        $conflicts = [];
        $furthest = null;
        foreach ($intervals as $interval) {
            // Empty intervals are valid zero, not occupied time. Within one
            // event active intervals are already validated non-overlapping.
            if ($interval['start'] === $interval['end']) {
                continue;
            }
            if ($furthest && $interval['start'] < $furthest['end'] && $interval['event_id'] !== $furthest['event_id']) {
                $conflicts[] = $interval['event_id'];
                $conflicts[] = $furthest['event_id'];
            }
            if (! $furthest || $interval['end'] > $furthest['end']) {
                $furthest = $interval;
            }
        }

        return array_values(array_unique($conflicts));
    }
}
