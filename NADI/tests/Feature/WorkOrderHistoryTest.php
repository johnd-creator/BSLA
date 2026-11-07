<?php

namespace Tests\Feature;

use App\Models\User;
use App\Services\ReliabilityMart;
use App\Services\WorkOrderEvidence;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Http\Client\Factory;
use Illuminate\Support\Facades\Http;
use Tests\TestCase;

class WorkOrderHistoryTest extends TestCase
{
    use RefreshDatabase;

    private const ASSET = 'asset:MAXIMO:MXASSET:BSR:IP:TEST';

    private const WO = 'workorder:MAXIMO:MXWODETAIL:BSR:IP:WO-1';

    protected function setUp(): void
    {
        parent::setUp();
        config(['services.reliability_mart.url' => 'http://mart.test', 'services.asset_mapping.file' => null]);
        Http::preventStrayRequests();
    }

    private function signIn(string $role = 'ENGINEER'): void
    {
        $user = User::factory()->create(['roles' => [$role], 'active' => true])->refresh();
        $this->actingAs($user)->withSession(['auth_version' => $user->auth_version]);
    }

    private function record(array $changes = []): array
    {
        return array_replace([
            'canonical_id' => 'maintenance_event:MAXIMO:MXWODETAIL:BSR:IP:WO-1',
            'work_order_id' => self::WO, 'equipment_id' => self::ASSET,
            'site_code' => 'BSR', 'organization_code' => 'IP', 'status' => 'CLOSE',
            'description' => 'Synthetic inspection', 'event_type' => 'PM',
            'actual_start' => null, 'actual_finish' => null, 'source_changed_at' => '2026-11-01T12:00:00Z',
            'source_detail' => ['work_order_number' => 'WO-1', 'asset_number' => 'TEST'],
            'classification' => ['raw_work_type' => 'PM', 'canonical_category' => 'PM', 'state' => 'CANONICAL_SUPPORTED', 'origin' => 'RETAINED_MAXIMO_WORKTYPE', 'confidence' => 'VERIFIED'],
            'failure_code' => null,
        ], $changes);
    }

    private function fake(array $items, array $meta = []): void
    {
        Http::fake([
            'mart.test/v1/reliability/assets/*' => fn () => Http::response(['canonical_id' => self::ASSET, 'source_asset_number' => 'TEST', 'description' => 'Exact test asset', 'site_code' => 'BSR', 'organization_code' => 'IP', 'registered' => true, 'hierarchy_category' => 'equipment', 'scope_basis' => 'DIRECT_SOURCE_UNIT']),
            'mart.test/v1/reliability/maintenance-events*' => fn () => Http::response(['items' => $items, 'meta' => array_replace(['total' => count($items), 'offset' => 0, 'limit' => 25, 'has_more' => false], $meta)]),
        ]);
    }

    public function test_history_preserves_asset_date_status_sort_and_mode_across_pagination_and_detail(): void
    {
        $this->signIn();
        $this->fake([$this->record()], ['total' => 80, 'offset' => 25, 'has_more' => true]);
        $response = $this->get(route('work-orders.index', ['asset_ref' => self::ASSET, 'status' => 'CLOSE', 'from' => '2026-11-01', 'to' => '2026-11-02', 'sort' => 'date_asc', 'view' => 'disturbances', 'offset' => 25]));
        $response->assertOk()->assertSee('Exact test asset')->assertSee('History gangguan')->assertSee('Pemeliharaan terklasifikasi')->assertSee('Unknown')->assertSee('Kejadian tervalidasi')->assertSee('Data belum tersedia')->assertSee('WO di halaman ini')->assertSee('offset=50', false)->assertSee('view=disturbances', false)->assertSee('from=2026-11-01', false)->assertSee('sort=date_asc', false)->assertSee('Perubahan record · bukan waktu kejadian');
        Http::assertSent(fn ($r) => str_contains($r->url(), '/maintenance-events') && $r->method() === 'GET' && $r['asset_ref'] === self::ASSET && $r['status'] === 'CLOSE' && $r['date_from'] === '2026-11-01T00:00:00+07:00' && $r['date_to'] === '2026-11-02T23:59:59.999999+07:00' && $r['limit'] === 25 && $r['offset'] === 25 && $r['sort'] === 'date_asc' && ! isset($r['view']));
        Http::assertSentCount(2);
    }

    public function test_all_four_roles_can_read_without_new_write_permissions(): void
    {
        $this->fake([$this->record()]);
        foreach (['ADMIN', 'ENGINEER', 'SUPERVISOR', 'MANAGER'] as $role) {
            $this->signIn($role);
            $this->get('/work-orders?view=disturbances')->assertOk()->assertSee('Synthetic inspection');
        }
        $this->post('/work-orders', [])->assertStatus(405);
    }

    public function test_source_codes_and_descriptions_cannot_invent_failures(): void
    {
        foreach (['CD', 'PDM', 'OH', 'RTF', 'MOD', 'UNRECOGNIZED'] as $raw) {
            $evidence = WorkOrderEvidence::fromRecord(['classification_raw_work_type' => $raw, 'classification_state' => 'UNMAPPED', 'actual_start' => null, 'event_type' => null, 'description' => 'BREAKDOWN FAILURE TRIP', 'status' => 'CLOSE']);
            $this->assertSame('unknown', $evidence['review']);
            $this->assertSame($raw, $evidence['work_type']);
        }
        foreach (['PM', 'INSPECTION', 'CALIBRATION'] as $type) {
            $this->assertSame('maintenance', WorkOrderEvidence::fromRecord(['actual_start' => null, 'event_type' => $type])['review']);
        }
        foreach (['CM', 'REPAIR', 'EMERGENCY'] as $type) {
            $evidence = WorkOrderEvidence::fromRecord(['actual_start' => null, 'event_type' => $type]);
            $this->assertSame('candidate', $evidence['review']);
            $this->assertStringContainsString('bukan bukti gangguan', $evidence['reason']);
        }
        $conflict = WorkOrderEvidence::fromRecord(['actual_start' => null, 'event_type' => 'CM', 'classification_raw_work_type' => 'PM']);
        $this->assertSame('unknown', $conflict['review']);
        $this->assertSame('unknown', WorkOrderEvidence::fromRecord(['event_type' => 'CM', 'classification_state' => 'UNRECOGNIZED'])['review']);
        $withCode = WorkOrderEvidence::fromRecord(['actual_start' => null, 'event_type' => 'PM', 'failure_code' => 'SOURCE-CODE']);
        $this->assertSame('candidate', $withCode['review']);
        foreach (['WAPPR', 'CLOSE', 'CAN', 'CANCEL', 'WDONE'] as $status) {
            $this->assertSame('unknown', WorkOrderEvidence::fromRecord(['actual_start' => null, 'status' => $status])['review']);
        }
    }

    public function test_wo_details_show_allowlisted_evidence_without_raw_payload_or_invented_event_id(): void
    {
        $this->signIn();
        $this->fake([$this->record(['failure_code' => '<script>source-code</script>', 'sources' => ['private' => 'PRIVATE-RAW'], 'reported_by' => 'PRIVATE-PERSON', 'event_id' => 'FAKE-VALIDATED-EVENT'])]);
        $this->get(route('work-orders.show', ['ref' => self::WO, 'view' => 'disturbances', 'asset_ref' => self::ASSET]))
            ->assertOk()->assertSee('Kandidat review')->assertSee('&lt;script&gt;source-code', false)->assertDontSee('<script>source-code', false)->assertSee('ID record WO · bukan ID kejadian')->assertSee('Belum tervalidasi')->assertDontSee('PRIVATE-RAW')->assertDontSee('PRIVATE-PERSON')->assertDontSee('FAKE-VALIDATED-EVENT')->assertSee('view=disturbances', false);
        Http::assertSentCount(2);
    }

    public function test_bad_pages_fail_closed_instead_of_cross_asset_leakage_or_double_counts(): void
    {
        $this->signIn();
        foreach ([[$this->record(['equipment_id' => 'asset:OTHER'])], [$this->record(), $this->record()], [$this->record(), $this->record(['canonical_id' => 'other-row'])], [$this->record(['classification' => ['raw_work_type' => ['bad']]])], [$this->record(['status' => 'WAPPR'])]] as $items) {
            Http::swap(new Factory);
            Http::preventStrayRequests();
            $this->fake($items);
            $this->get(route('work-orders.index', ['asset_ref' => self::ASSET, 'status' => 'CLOSE', 'view' => 'disturbances']))->assertOk()->assertSee('Riwayat belum terhubung')->assertDontSee('Synthetic inspection')->assertDontSee('WO di halaman ini');
        }
    }

    public function test_asset_verification_failure_does_not_fall_back_to_unscoped_work_orders(): void
    {
        $this->signIn();
        Http::fake(['mart.test/*' => Http::response([], 404)]);
        $this->get(route('work-orders.index', ['asset_ref' => self::ASSET]))->assertOk()->assertSee('Riwayat belum terhubung');
        Http::assertSentCount(2);
    }

    public function test_empty_history_is_not_claimed_healthy_and_missing_classification_is_unknown(): void
    {
        $this->signIn();
        $this->fake([]);
        $this->get('/work-orders?view=disturbances')->assertOk()->assertSee('Tidak ada record WO pada filter ini')->assertSee('Ini tidak membuktikan aset tidak pernah mengalami gangguan')->assertSee('Data belum tersedia');
        Http::swap(new Factory);
        Http::preventStrayRequests();
        $this->fake([$this->record(['event_type' => null, 'classification' => null])]);
        $this->get('/work-orders?view=disturbances')->assertOk()->assertSee('Unknown · belum terklasifikasi');
    }

    public function test_date_validation_prevents_requests_and_allows_one_sided_ranges(): void
    {
        $this->signIn();
        foreach (['from=2026-02-31', 'from=2026-11-02&to=2026-11-01', 'sort=unsafe', 'view=unsafe'] as $query) {
            $this->getJson('/work-orders?'.$query)->assertUnprocessable();
        }
        Http::assertNothingSent();
        $this->fake([]);
        $this->get('/work-orders?to=2026-11-06')->assertOk();
        $this->get('/work-orders?from=2026-11-06')->assertOk();
        Http::assertSentCount(2);
    }

    public function test_distinct_work_orders_remain_distinct_without_pretending_to_deduplicate_incidents(): void
    {
        $this->fake([$this->record(['event_type' => 'CM', 'classification' => null]), $this->record(['canonical_id' => 'maintenance_event:MAXIMO:MXWODETAIL:BSR:IP:WO-2', 'work_order_id' => 'workorder:MAXIMO:MXWODETAIL:BSR:IP:WO-2', 'event_type' => 'CM', 'classification' => null])]);
        $page = app(ReliabilityMart::class)->workOrders([]);
        $this->assertCount(2, $page['items']);
        $this->assertArrayNotHasKey('event_id', $page['items'][0]);
        $this->assertArrayNotHasKey('incident_count', $page);
    }

    private function inventoryFake(array $scope = [], int $status = 200): void
    {
        Http::fake([
            'mart.test/v1/reliability/assets/inventory/*' => fn () => Http::response([
                'canonical_id' => self::ASSET, 'source_asset_number' => 'TEST', 'description' => 'Non-Registry inventory asset',
                'site_code' => 'BSR', 'organization_code' => 'IP', 'registered' => false,
                'hierarchy_category' => 'component', 'scope_basis' => 'SOURCE_PARENT_CHAIN',
            ]),
            'mart.test/v1/reliability/inventory-maintenance-events*' => fn () => Http::response([
                'items' => [$this->record()], 'meta' => ['total' => 1, 'offset' => 0, 'limit' => 25, 'has_more' => false],
                'scope' => array_replace(['population' => 'COLLECTED_HIERARCHY', 'asset_ref' => self::ASSET, 'site_code' => 'BSR', 'organization_code' => 'IP', 'date_basis' => 'ACTUAL_START_OR_SOURCE_CHANGED'], $scope),
            ], $status),
        ]);
    }

    public function test_non_registry_history_uses_only_exact_inventory_api_and_preserves_context(): void
    {
        $this->signIn();
        $this->inventoryFake();
        $this->get(route('work-orders.index', ['asset_ref' => self::ASSET, 'view' => 'disturbances']))
            ->assertOk()->assertSee('Non-Registry inventory asset')->assertSee('Inventaris · non-Registry')->assertSee('Synthetic inspection')->assertSee('Pemeliharaan terklasifikasi');
        Http::assertSentCount(2);
        Http::assertSent(fn ($r) => str_contains($r->url(), '/inventory-maintenance-events') && $r['asset_ref'] === self::ASSET && $r->method() === 'GET');
        Http::assertNotSent(fn ($r) => str_contains($r->url(), '/maintenance-events?'));
    }

    public function test_non_registry_detail_verifies_both_asset_and_work_order_in_inventory_scope(): void
    {
        $this->signIn();
        $this->inventoryFake();
        $this->get(route('work-orders.show', ['asset_ref' => self::ASSET, 'ref' => self::WO, 'view' => 'disturbances']))
            ->assertOk()->assertSee('INVENTARIS NON-REGISTRY')->assertSee('Synthetic inspection')->assertSee('view=disturbances', false);
        Http::assertSentCount(2);
        Http::assertSent(fn ($r) => str_contains($r->url(), '/inventory-maintenance-events') && $r['asset_ref'] === self::ASSET && $r['work_order_id'] === self::WO);
    }

    public function test_unavailable_inventory_endpoint_is_not_presented_as_zero_work_orders(): void
    {
        $this->signIn();
        $this->inventoryFake(status: 404);
        $this->get(route('work-orders.index', ['asset_ref' => self::ASSET]))->assertOk()
            ->assertSee('Riwayat WO inventaris belum tersedia')->assertSee('Ini bukan hasil nol WO')->assertDontSee('Tidak ada record WO pada filter ini');
        Http::assertSentCount(2);
        Http::assertNotSent(fn ($r) => str_contains($r->url(), '/maintenance-events?'));
    }

    public function test_inventory_response_scope_must_match_exact_asset_population_and_date_basis(): void
    {
        $this->signIn();
        foreach ([['asset_ref' => 'asset:OTHER'], ['population' => 'REGISTRY'], ['site_code' => 'OTHER'], ['organization_code' => 'OTHER'], ['date_basis' => 'INCIDENT_DATE']] as $scope) {
            Http::swap(new Factory);
            Http::preventStrayRequests();
            $this->inventoryFake($scope);
            $this->get(route('work-orders.index', ['asset_ref' => self::ASSET]))->assertOk()->assertSee('Riwayat belum terhubung')->assertDontSee('Synthetic inspection');
        }
    }
}
