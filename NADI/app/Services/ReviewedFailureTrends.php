<?php

namespace App\Services;

class ReviewedFailureTrends
{
    public const BASES = ['count' => 'Jumlah failure yang direview', 'active_repair' => 'Jam perbaikan aktif lengkap', 'restoration' => 'Jam pemulihan fungsi lengkap'];

    public function report(array $report): array
    {
        $points = [];
        $missingTime = $conflicts = 0;
        foreach ($report['calculation']['event_trace'] as $event) {
            if ($event['state'] !== 'failure') {
                continue;
            }
            $missingTime += in_array('MISSING_EXACT_ONSET', $event['exclusion_reasons'], true) && ! in_array('OUTSIDE_ONSET_YEAR', $event['exclusion_reasons'], true) ? 1 : 0;
            $conflicts += in_array('CONFLICT_OR_UNRESOLVED_RECURRENCE', $event['exclusion_reasons'], true) && $event['month'] !== null ? 1 : 0;
            if (! $event['eligible_failure']) {
                continue;
            }
            $points[] = array_intersect_key($event, array_flip(['event_id', 'reference', 'event_version', 'review_id', 'review_revision', 'month', 'category', 'active_repair_seconds', 'restoration_seconds']));
        }
        $partial = $report['coverage']['local_rows_truncated'];
        $result = ['schema_version' => 'reviewed-failure-trends-v2', 'status' => $partial ? 'PARTIAL_WITHHELD' : ($points ? 'REVIEWED_LOCAL_RECORDS_ONLY' : 'INSUFFICIENT_DATA'),
            'points' => $points, 'excluded_missing_onset' => $missingTime, 'excluded_conflicting_episodes' => $conflicts,
            'event_ids' => array_column($points, 'event_id'), 'reviewed_count' => $partial ? null : count($points),
            'meaning' => 'Current exact-onset local failure reviews only, with conflicting intervals and unresolved recurrence excluded. Observation types are not root causes. Each duration uses its own complete-episode population. No WO proxy, no plant aggregation, no extrapolation.'];
        $count = $this->select($result, 'count');
        $result['monthly_counts'] = $partial ? null : array_column($count['months'], 'value', 'month');
        $result['pareto'] = $count['pareto'];

        return $result;
    }

    /** Display filters never change stored evidence, arithmetic or snapshot hashes. */
    public function select(array $trends, string $basis = 'count', ?int $month = null): array
    {
        $partial = $trends['status'] === 'PARTIAL_WITHHELD';
        $months = [];
        for ($i = 1; $i <= 12; $i++) {
            $months[$i] = ['month' => $i, 'value' => 0, 'episodes' => 0, 'event_ids' => []];
        }
        $categories = [];
        $incomplete = $included = 0;
        foreach ($partial ? [] : ($trends['points'] ?? []) as $point) {
            if ($month !== null && $point['month'] !== $month) {
                continue;
            }
            $seconds = $basis === 'count' ? 1 : $point[$basis.'_seconds'];
            if ($seconds === null) {
                $incomplete++;

                continue;
            }
            $value = $basis === 'count' ? 1 : $seconds / 3600;
            $m = $point['month'];
            $months[$m]['value'] += $value;
            $months[$m]['episodes']++;
            $months[$m]['event_ids'][] = $point['event_id'];
            $category = $point['category'];
            $categories[$category] ??= ['category' => $category, 'value' => 0, 'count' => 0, 'event_ids' => []];
            $categories[$category]['value'] += $value;
            $categories[$category]['count']++;
            $categories[$category]['event_ids'][] = $point['event_id'];
            $included++;
        }
        uasort($categories, fn ($a, $b) => ($b['value'] <=> $a['value']) ?: strcmp($a['category'], $b['category']));
        $total = array_sum(array_column($categories, 'value'));
        $cumulative = 0;
        $pareto = [];
        foreach ($categories as $item) {
            $cumulative += $item['value'];
            $pareto[] = [...$item, 'share_percent' => $total > 0 ? round($item['value'] / $total * 100, 2) : null,
                'cumulative_percent' => $total > 0 ? round($cumulative / $total * 100, 2) : null];
        }

        return ['basis' => $basis, 'label' => self::BASES[$basis], 'unit' => $basis === 'count' ? 'kejadian lokal' : 'jam', 'month' => $month,
            'status' => $partial ? 'PARTIAL_WITHHELD' : ($included ? 'REVIEWED_LOCAL_RECORDS_ONLY' : 'INSUFFICIENT_DATA'),
            'months' => $months, 'pareto' => $pareto, 'total' => $partial || ! $included ? null : $total,
            'included_episodes' => $included, 'excluded_incomplete' => $incomplete,
            'max_month' => max([1, ...array_column($months, 'value')]), 'max_category' => max([1, ...array_column($pareto, 'value')])];
    }
}
