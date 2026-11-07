<?php

namespace Tests\Feature;

use App\Models\User;
use App\Services\ReliabilityMart;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Http\Client\Factory;
use Illuminate\Support\Facades\Http;
use Tests\TestCase;

class WorkOrderAnnualTest extends TestCase
{
    use RefreshDatabase;

    private const ASSET = 'asset:MAXIMO:MXASSET:BSR:IP:TEST';

    protected function setUp(): void
    {
        parent::setUp();
        config(['services.reliability_mart.url' => 'http://mart.test']);
        Http::preventStrayRequests();
        $user = User::factory()->create(['roles' => ['ENGINEER'], 'active' => true])->refresh();
        $this->actingAs($user)->withSession(['auth_version' => $user->auth_version]);
    }

    private function scope(bool $inventory = true): array
    {
        return ['asset_ref' => self::ASSET, 'population' => $inventory ? 'COLLECTED_HIERARCHY' : 'REGISTRY', 'site_code' => 'BSR', 'organization_code' => 'IP', 'date_basis' => 'ACTUAL_START', 'time_zone' => 'Asia/Jakarta', 'count_basis' => 'UNIQUE_WORK_ORDER_ID'];
    }

    private function summary(): array
    {
        return ['scope' => $this->scope(), 'availability_state' => 'REQUIRES_VALIDATED_DCS_HISTORY',
            'counts' => ['record_count' => 102, 'work_order_count' => 100, 'dated_work_order_count' => 80, 'unknown_date_work_order_count' => 19, 'duplicate_work_order_count' => 1, 'duplicate_record_count' => 2, 'missing_identity_record_count' => 1],
            'years' => [['year' => 2026, 'work_orders' => 80, 'work_types' => [['value' => 'PM', 'count' => 72], ['value' => 'CM', 'count' => 8]], 'statuses' => [['value' => 'CLOSE', 'count' => 79], ['value' => 'WAPPR', 'count' => 1]]]],
            'unknown_year' => ['year' => null, 'work_orders' => 19, 'work_types' => [['value' => null, 'count' => 19]], 'statuses' => [['value' => 'CLOSE', 'count' => 19]]]];
    }

    private function fake(?array $summary = null, string $year = '2026', ?string $actual = '2025-12-31T17:00:00Z', bool $inventory = true): void
    {
        Http::fake([
            'mart.test/v1/reliability/assets/*' => Http::response(['canonical_id' => self::ASSET, 'source_asset_number' => 'TEST', 'description' => 'Annual test asset', 'site_code' => 'BSR', 'organization_code' => 'IP', 'registered' => ! $inventory, 'hierarchy_category' => 'equipment', 'scope_basis' => 'DIRECT_SOURCE_UNIT']),
            'mart.test/v1/reliability/asset-work-orders/annual-summary*' => Http::response($summary ?? $this->summary()),
            'mart.test/v1/reliability/asset-work-orders/year*' => fn ($r) => Http::response(['scope' => $this->scope($inventory), 'selected_year' => $year, 'meta' => ['total' => 80, 'offset' => (int) ($r['offset'] ?? 0), 'limit' => 25, 'has_more' => true], 'items' => [['canonical_id' => 'event:1', 'equipment_id' => self::ASSET, 'work_order_id' => 'workorder:MAXIMO:MXWODETAIL:BSR:IP:1', 'site_code' => 'BSR', 'organization_code' => 'IP', 'status' => 'CLOSE', 'actual_start' => $actual, 'description' => 'Annual WO record']]]),
            'mart.test/v1/reliability/*maintenance-events*' => Http::response(['items' => [], 'meta' => ['total' => 0, 'offset' => 0, 'limit' => 25, 'has_more' => false], 'scope' => [...$this->scope(), 'date_basis' => 'ACTUAL_START_OR_SOURCE_CHANGED']]),
        ]);
    }

    public function test_summary_is_full_population_and_drilldown_keeps_year(): void
    {
        $this->fake();
        $this->get(route('work-orders.index', ['asset_ref' => self::ASSET, 'year' => '2026', 'offset' => 25, 'status' => 'CLOSE']))
            ->assertOk()->assertSee('Aktivitas WO per tahun')->assertSee('Tahun belum diketahui')->assertSee('dari 100 identitas WO di Mart')->assertSee('PM')->assertSee('72')->assertSee('WAPPR')->assertSee('Annual WO record')->assertSee('year=2026', false)->assertSee('offset=50', false)->assertSee('historian DCS')->assertSee('asset wellness')->assertSee('Pareto loss')->assertSee('1 identitas WO berulang (2 record)');
        Http::assertSent(fn ($r) => str_contains($r->url(), 'annual-summary') && $r['population'] === 'COLLECTED_HIERARCHY' && ! isset($r['offset']) && ! isset($r['status']) && ! isset($r['year']));
        Http::assertSent(fn ($r) => str_contains($r->url(), 'asset-work-orders/year') && $r['year'] === '2026' && $r['offset'] === 25 && $r['asset_ref'] === self::ASSET);
    }

    public function test_unknown_year_does_not_use_changedate_and_registry_scope_is_supported(): void
    {
        $summary = $this->summary();
        $summary['scope'] = $this->scope(false);
        $this->fake($summary, 'unknown', null, false);
        $this->get(route('work-orders.index', ['asset_ref' => self::ASSET, 'year' => 'unknown']))->assertOk()->assertSee('Annual WO record')->assertSee('Tahun mulai belum diketahui');
        Http::assertSent(fn ($r) => str_contains($r->url(), 'asset-work-orders/year') && $r['population'] === 'REGISTRY');
    }

    public function test_mismatched_year_rejects_list_without_hiding_valid_summary(): void
    {
        $this->fake(null, '2026', '2025-12-31T16:59:59Z');
        $this->get(route('work-orders.index', ['asset_ref' => self::ASSET, 'year' => '2026']))->assertOk()->assertSee('Riwayat belum terhubung')->assertDontSee('Annual WO record')->assertSee('dari 100 identitas WO di Mart');
    }

    public function test_bad_summary_does_not_fabricate_zero_or_hide_list(): void
    {
        $summary = $this->summary();
        $summary['counts']['dated_work_order_count'] = 81;
        $this->fake($summary);
        $this->get(route('work-orders.index', ['asset_ref' => self::ASSET, 'year' => '2026']))->assertOk()->assertSee('Ringkasan tahunan belum dapat diverifikasi')->assertSee('Annual WO record')->assertDontSee('dari 100 identitas WO di Mart');
    }

    public function test_invalid_year_and_conflicting_dates_are_rejected_before_fetch(): void
    {
        foreach ([['year' => '0'], ['year' => '10000'], ['year' => '2026', 'from' => '2026-01-01'], ['year' => '2026', 'to' => '2026-12-31']] as $query) {
            $this->getJson(route('work-orders.index', ['asset_ref' => self::ASSET, ...$query]))->assertUnprocessable();
        }
        $this->getJson('/work-orders?year=2026')->assertUnprocessable();
        Http::assertNothingSent();
    }

    public function test_summary_rejects_wrong_scope_duplicates_and_unreconciled_distributions(): void
    {
        $cases = [];
        $data = $this->summary();
        $data['scope']['date_basis'] = 'SOURCE_CHANGED';
        $cases[] = $data;
        $data = $this->summary();
        $data['years'][0]['statuses'][0]['count'] = 80;
        $cases[] = $data;
        $data = $this->summary();
        $data['years'][0]['work_types'] = [['value' => 'PM', 'count' => 40], ['value' => 'PM', 'count' => 40]];
        $cases[] = $data;
        $data = $this->summary();
        $data['years'][] = $data['years'][0];
        $cases[] = $data;
        foreach ($cases as $data) {
            Http::swap(new Factory);
            $this->fake($data);
            try {
                app(ReliabilityMart::class)->annualWorkOrders(self::ASSET, true);
                $this->fail('Invalid summary accepted.');
            } catch (\RuntimeException $e) {
                $this->assertNotEmpty($e->getMessage());
            }
        }
    }
}
