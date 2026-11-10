<?php

namespace App\Services;

use Illuminate\Pagination\LengthAwarePaginator;

class ReliabilityReviewQueue
{
    public const PER_PAGE = 20;

    public const STATES = ['all' => 'Semua status', 'needs_review' => 'Perlu diperiksa', 'unreviewed' => 'Belum direview', 'stale' => 'Review kedaluwarsa', 'uncertain' => 'Belum dipastikan', 'conflict' => 'Interval konflik', 'failure' => 'Kehilangan fungsi · review lokal', 'not_failure' => 'Bukan failure aset ini', 'duplicate' => 'Duplikat', 'voided' => 'Dibatalkan'];

    public const PERIODS = ['all' => 'Semua periode', 'in_year' => 'Periode dipilih', 'unknown_year' => 'Tanpa tahun', 'out_of_year' => 'Di luar periode dipilih'];

    // This is a display-only projection. Never filter the evidence report used
    // for sample arithmetic, quality totals, downloads, hashes or snapshots.
    public function paginate(array $report, array $filters, string $path, array $query = []): LengthAwarePaginator
    {
        $state = $filters['review_state'] ?? 'all';
        $period = $filters['review_period'] ?? 'all';
        $overlap = array_fill_keys($report['overlap_event_ids'], true);
        $rows = array_values(array_filter($report['events'], function (array $row) use ($state, $period, $overlap): bool {
            $conflict = isset($overlap[$row['event_id']]);
            $matchesState = match ($state) {
                'all' => true,
                'needs_review' => in_array($row['state'], ['unreviewed', 'stale', 'uncertain'], true) || $conflict,
                'conflict' => $conflict,
                default => $row['state'] === $state,
            };
            $matchesPeriod = match ($period) {
                'in_year' => $row['in_year'],
                'unknown_year' => $row['date'] === null,
                'out_of_year' => $row['date'] !== null && ! $row['in_year'],
                default => true,
            };

            return $matchesState && $matchesPeriod;
        }));
        $page = (int) ($filters['review_page'] ?? 1);

        return new LengthAwarePaginator(array_slice($rows, ($page - 1) * self::PER_PAGE, self::PER_PAGE), count($rows), self::PER_PAGE, $page, [
            'path' => $path, 'pageName' => 'review_page', 'query' => array_filter([...$query, 'review_state' => $state, 'review_period' => $period], fn ($value) => $value !== null), 'fragment' => 'reliability-review-queue',
        ]);
    }
}
