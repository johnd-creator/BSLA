<?php

namespace Tests\Unit;

use App\Services\ReliabilityReviewQueue;
use PHPUnit\Framework\TestCase;

class ReliabilityReviewQueueTest extends TestCase
{
    private function report(): array
    {
        return ['events' => [
            ['event_id' => 1, 'state' => 'unreviewed', 'date' => '2026-01-01', 'in_year' => true],
            ['event_id' => 2, 'state' => 'stale', 'date' => '2025-01-01', 'in_year' => false],
            ['event_id' => 3, 'state' => 'uncertain', 'date' => null, 'in_year' => false],
            ['event_id' => 4, 'state' => 'failure', 'date' => '2026-01-02', 'in_year' => true],
            ['event_id' => 5, 'state' => 'not_failure', 'date' => '2026-01-02', 'in_year' => true],
            ['event_id' => 6, 'state' => 'duplicate', 'date' => '2026-01-02', 'in_year' => true],
            ['event_id' => 7, 'state' => 'voided', 'date' => null, 'in_year' => false],
        ], 'overlap_event_ids' => [4], 'evidence_hash' => 'UNCHANGED', 'metrics' => ['mtbf' => ['value' => null]]];
    }

    public function test_state_filters_and_attention_queue_include_conflicts_without_reclassification(): void
    {
        $service = new ReliabilityReviewQueue;
        $report = $this->report();
        $before = $report;
        foreach (['all' => range(1, 7), 'needs_review' => [1, 2, 3, 4], 'unreviewed' => [1], 'stale' => [2], 'uncertain' => [3], 'conflict' => [4], 'failure' => [4], 'not_failure' => [5], 'duplicate' => [6], 'voided' => [7]] as $state => $ids) {
            $page = $service->paginate($report, ['review_state' => $state], '/reliability');
            $this->assertSame($ids, array_column($page->items(), 'event_id'), $state);
        }
        $this->assertSame($before, $report);
    }

    public function test_period_filters_keep_unknown_year_distinct_and_combine_with_state(): void
    {
        $service = new ReliabilityReviewQueue;
        foreach (['all' => range(1, 7), 'in_year' => [1, 4, 5, 6], 'unknown_year' => [3, 7], 'out_of_year' => [2]] as $period => $ids) {
            $page = $service->paginate($this->report(), ['review_period' => $period], '/reliability');
            $this->assertSame($ids, array_column($page->items(), 'event_id'), $period);
        }
        $page = $service->paginate($this->report(), ['review_state' => 'needs_review', 'review_period' => 'in_year'], '/reliability');
        $this->assertSame([1, 4], array_column($page->items(), 'event_id'));
    }

    public function test_pages_are_bounded_stable_and_keep_exact_query_and_queue_anchor(): void
    {
        $report = $this->report();
        $report['events'] = array_map(fn ($id) => ['event_id' => $id, 'state' => 'unreviewed', 'date' => '2026-01-01', 'in_year' => true], range(1, 45));
        $service = new ReliabilityReviewQueue;
        $filters = ['review_state' => 'unreviewed', 'review_period' => 'in_year', 'review_page' => 2];
        $page = $service->paginate($report, $filters, '/reliability', ['asset_ref' => 'asset:EXACT+ID', 'year' => 2026]);
        $this->assertSame(range(21, 40), array_column($page->items(), 'event_id'));
        $this->assertSame(45, $page->total());
        $this->assertSame(3, $page->lastPage());
        parse_str(parse_url($page->nextPageUrl(), PHP_URL_QUERY), $query);
        $this->assertSame(['asset_ref' => 'asset:EXACT+ID', 'year' => '2026', 'review_state' => 'unreviewed', 'review_period' => 'in_year', 'review_page' => '3'], $query);
        $this->assertSame('reliability-review-queue', parse_url($page->nextPageUrl(), PHP_URL_FRAGMENT));
        $this->assertSame([], $service->paginate($report, ['review_page' => 99], '/reliability')->items());
    }
}
