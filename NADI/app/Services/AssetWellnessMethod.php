<?php

namespace App\Services;

use App\Models\AssetWellnessPolicy;
use App\Models\PdmActivity;
use Carbon\CarbonImmutable;

/** Evidence qualification preview only: never returns a health/official score. */
class AssetWellnessMethod
{
    public function report(string $asset, int|ReliabilityPeriod $year): array
    {
        $period = $year instanceof ReliabilityPeriod ? $year : ReliabilityPeriod::year($year);
        $ready = $period->storageReady('asset_wellness_policies');
        $asOf = $period->annual ? now('Asia/Jakarta')->toDateString() : $period->end->subDay()->toDateString();
        $policy = $ready ? $period->constrain(AssetWellnessPolicy::where('asset_ref', $asset))->with('author:id,name')->latest('revision')->first() : null;
        $checks = [];
        foreach ($policy?->rules['pdm_rules'] ?? [] as $rule) {
            $checks[] = $this->checkPoint($asset, $period, $rule, $asOf);
        }

        $weights = collect($policy?->rules['components'] ?? [])->pluck('weight')->filter(fn ($value) => $value !== null && $value !== '');
        $weightSum = $weights->count() === 4 ? (float) $weights->sum() : null;

        return ['storage_ready' => $ready, 'policy' => $policy, 'checks' => $checks,
            'status' => 'DRAFT_NOT_APPROVED', 'score' => null,
            'as_of_date' => $asOf, 'age_basis' => $period->annual ? 'READ_DATE' : 'PERIOD_END_WITH_CURRENT_REVISIONS',
            'evidence_completeness' => 'NOT_ASSESSED',
            'draft_weights' => ['specified' => $weights->count(), 'sum' => $weightSum, 'status' => $weightSum === null ? 'INCOMPLETE' : (abs($weightSum - 100) < 0.000001 ? 'DRAFT_TOTAL_100' : 'SUM_NOT_100')],
            'normalization_status' => 'DRAFT_TEXT_ONLY_NOT_VALIDATED',
            'note' => 'Usulan rentang dan usia bukan aturan yang disahkan. Daftar bukti wajib masih perlu diperiksa engineer; kelengkapan isian bukan kelengkapan bukti atau kesehatan.'];
    }

    private function checkPoint(string $asset, ReliabilityPeriod $period, array $rule, string $asOf): array
    {
        $scope = $rule['scope'];
        $query = PdmActivity::where('asset_ref', $asset)->whereBetween('measured_on', [$period->start->toDateString(), $period->end->subDay()->toDateString()]);
        foreach (['template_id', 'template_fingerprint', 'method', ...PdmTrend::CONTEXT] as $key) {
            $query->where($key, $scope[$key]);
        }
        // Never replace a missing latest reading with an older valid one.
        $latest = $query->with('inspection.pdmReviewAudit')->newestMeasurement()->first();
        $anchor = PdmActivity::whereKey($rule['anchor_id'])->where('asset_ref', $asset)->first();
        $basisCurrent = $anchor && hash_equals($rule['anchor_fingerprint'], $anchor->analysisBasis()['fingerprint']);
        $result = ['rule' => $rule, 'activity' => $latest, 'basis_current' => $basisCurrent,
            'value' => null, 'age_days' => null, 'order_ambiguous' => false, 'freshness' => 'UNKNOWN', 'range' => 'NOT_COMPARED', 'analysis' => 'NO_ANALYSIS'];
        if (! $latest || ! $basisCurrent) {
            return $result;
        }
        $sameDay = (clone $query)->where('measured_on', $latest->measured_on?->format('Y-m-d'));
        $result['order_ambiguous'] = (clone $sameDay)->count() > 1 && ((clone $sameDay)->where('time_precision', 'date')->exists()
            || ($latest->measured_at && (clone $sameDay)->where('measured_at', $latest->getRawOriginal('measured_at'))->count() > 1));
        $point = $rule['point'];
        $field = collect($latest->template_snapshot['fields'] ?? [])->firstWhere('key', $point);
        $reading = $latest->readings[$point] ?? [];
        $exact = $latest->template_snapshot === $scope['template_snapshot'] && $field === $rule['field'] && ($reading['unit'] ?? $field['unit'] ?? null) === $rule['unit'];
        if (! $exact || ! in_array($latest->time_precision, ['date', 'datetime'], true) || ($latest->time_precision === 'datetime' && (! $latest->measured_at || $latest->measured_at->isFuture()))) {
            return $result;
        }
        $date = $latest->measured_on?->format('Y-m-d');
        $today = $asOf;
        if ($date && $date <= $today) {
            // Calendar-date age only. Date-only measurements acquire no time or zone.
            $result['age_days'] = (int) CarbonImmutable::parse($date, 'UTC')->diffInDays(CarbonImmutable::parse($today, 'UTC'));
            $result['freshness'] = $rule['max_age_days'] === null ? 'UNDECIDED' : ($result['age_days'] > $rule['max_age_days'] ? 'OLDER_THAN_PROPOSAL' : 'WITHIN_PROPOSED_AGE');
        }
        $raw = $reading['value'] ?? null;
        if (! $result['order_ambiguous'] && $raw !== null && $raw !== '' && is_numeric($raw) && is_finite((float) $raw) && $result['age_days'] !== null) {
            $result['value'] = (float) $raw;
            $result['range'] = (($rule['lower'] !== null && (float) $raw < $rule['lower']) || ($rule['upper'] !== null && (float) $raw > $rule['upper'])) ? 'OUTSIDE_PROPOSED_RANGE' : 'WITHIN_PROPOSED_RANGE';
        }
        $inspection = $latest->inspection;
        if ($inspection && $inspection->asset_ref === $asset && ($inspection->finding || $inspection->recommendation)) {
            $inspection->setRelation('pdmActivity', $latest);
            $result['analysis'] = match ($inspection->pdmReviewState()) {
                'stale' => 'STALE', 'unknown' => 'UNKNOWN', default => 'CURRENT_LOCAL',
            };
        }

        return $result;
    }
}
