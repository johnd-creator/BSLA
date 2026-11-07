<?php

namespace Tests\Feature;

use App\Models\User;
use DOMDocument;
use DOMXPath;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Http\Client\Factory;
use Illuminate\Support\Facades\Http;
use Tests\TestCase;

class AssetInventoryTest extends TestCase
{
    use RefreshDatabase;

    private const ID = 'asset:MAXIMO:MXASSET:BSR:IP:INVENTORY-TEST';

    protected function setUp(): void
    {
        parent::setUp();
        Http::preventStrayRequests();
        config(['services.reliability_mart.url' => 'http://mart.test', 'services.asset_mapping.file' => null]);
    }

    private function signIn(string $role = 'ENGINEER'): void
    {
        $user = User::factory()->create(['roles' => [$role]])->refresh();
        $this->actingAs($user)->withSession(['auth_version' => $user->auth_version]);
    }

    private function asset(array $changes = []): array
    {
        return array_replace([
            'canonical_id' => self::ID, 'source_asset_number' => 'INVENTORY-TEST',
            'site_code' => 'BSR', 'organization_code' => 'IP', 'description' => 'Synthetic inventory asset',
            'asset_type' => 'PRODUCTION', 'unit' => null, 'hierarchy_category' => 'unknown',
            'scope_basis' => 'SOURCE_PARENT_CHAIN', 'registered' => false,
            'sources' => ['raw' => 'PRIVATE-RAW'],
        ], $changes);
    }

    private function page(array $items = [], array $meta = []): array
    {
        return ['items' => $items, 'meta' => array_replace(['total' => count($items), 'offset' => 0, 'limit' => 25, 'has_more' => false], $meta)];
    }

    private function summary(array $changes = []): array
    {
        return array_replace_recursive([
            'scope' => ['site_code' => 'BSR', 'organization_code' => 'IP', 'unit' => 'CS01', 'population' => 'COLLECTED_HIERARCHY'],
            'counts' => ['total' => 1234, 'equipment' => 1000, 'component' => 150, 'part' => 60, 'system' => 2, 'unknown' => 22],
            'coverage' => ['state' => 'PARTIAL', 'full_source_baseline_complete' => false, 'last_completed_at' => null],
            'classification' => ['basis' => 'EXACT_SOURCE_ID_WORKBOOK_ROLE', 'status' => 'INDICATIVE_DOCUMENT_ROLE', 'unknown_count' => 22, 'note' => 'PRIVATE-NOTE'],
        ], $changes);
    }

    private function fake(array $summary, array $page): void
    {
        Http::fake([
            'mart.test/v1/reliability/assets/inventory-summary*' => fn () => Http::response($summary),
            'mart.test/v1/reliability/assets/inventory?*' => fn () => Http::response($page),
        ]);
    }

    private function document(string $html): DOMXPath
    {
        $previous = libxml_use_internal_errors(true);
        $document = new DOMDocument;
        $document->loadHTML('<?xml encoding="utf-8" ?>'.$html);
        libxml_clear_errors();
        libxml_use_internal_errors($previous);

        return new DOMXPath($document);
    }

    public function test_four_cards_use_global_aggregates_and_keep_system_and_unknown_in_total(): void
    {
        $this->fake($this->summary(), $this->page([$this->asset()], ['total' => 80, 'offset' => 25, 'has_more' => true]));
        $this->signIn();
        $response = $this->get('/assets?unit=CS01&status=OPERATING&asset_type=PRODUCTION&offset=25')->assertOk()
            ->assertSee('1.234')->assertSee('1.000')->assertSee('2 System')->assertSee('22 belum dikategorikan')
            ->assertSee('Cakupan belum lengkap')->assertSee('tidak mengikuti filter')->assertSee('Acuan Excel engineer')
            ->assertSee('Synthetic inventory asset')->assertDontSee('PRIVATE-RAW')->assertDontSee('PRIVATE-NOTE');
        $document = $this->document($response->getContent());
        $labels = iterator_to_array($document->query('//dl[@class="asset-summary-grid"]//dt'));
        $this->assertSame(['Total Asset', 'Equipment', 'Component', 'Part'], array_map(fn ($node) => $node->textContent, $labels));
        $this->assertSame(4, $document->query('//dl[@class="asset-summary-grid"]//dd')->length);
        $this->assertSame('1.234', $document->query('//dl[@class="asset-summary-grid"]//span[@class="asset-summary-value"]')->item(0)->textContent);
        Http::assertSentCount(2);
        Http::assertSent(fn ($request) => str_contains($request->url(), '/inventory-summary?')
            && $request->method() === 'GET' && $request->data() === ['site_code' => 'BSR', 'organization_code' => 'IP']);
        Http::assertSent(fn ($request) => str_contains($request->url(), '/inventory?') && $request['offset'] === 25 && $request['limit'] === 25 && $request['asset_type'] === 'PRODUCTION');
    }

    public function test_all_roles_can_read_summary_and_inventory_without_writes(): void
    {
        $this->fake($this->summary(), $this->page([$this->asset(['hierarchy_category' => 'system'])]));
        foreach (['ADMIN', 'ENGINEER', 'SUPERVISOR', 'MANAGER'] as $role) {
            $this->signIn($role);
            $this->get('/assets')->assertOk()->assertSee('Total Asset')->assertSee('Synthetic inventory asset')->assertSee('System');
        }
        Http::assertSentCount(8);
        Http::assertNotSent(fn ($request) => $request->method() !== 'GET');
    }

    public function test_missing_summary_does_not_hide_valid_inventory_or_turn_missing_counts_into_zero(): void
    {
        Http::fake([
            'mart.test/v1/reliability/assets/inventory-summary*' => Http::response(['detail' => 'PRIVATE-UPSTREAM'], 404),
            'mart.test/v1/reliability/assets/inventory?*' => Http::response($this->page([$this->asset()])),
        ]);
        $this->signIn();
        $response = $this->get('/assets')->assertOk()->assertSee('Synthetic inventory asset')->assertSee('Ringkasan belum tersedia')
            ->assertDontSee('PRIVATE-UPSTREAM')->assertDontSee('Belum terhubung');
        $document = $this->document($response->getContent());
        foreach ($document->query('//dl[@class="asset-summary-grid"]//span[@class="asset-summary-value"]') as $value) {
            $this->assertSame('—', $value->textContent);
        }
    }

    public function test_older_backend_preserves_registry_list_with_an_explicit_smaller_scope(): void
    {
        Http::fake([
            'mart.test/v1/reliability/assets/inventory-summary*' => Http::response([], 404),
            'mart.test/v1/reliability/assets/inventory?*' => Http::response([], 404),
            'mart.test/v1/reliability/assets?*' => Http::response($this->page([$this->asset()])),
        ]);
        $this->signIn();
        $this->get('/assets')->assertOk()->assertSee('Synthetic inventory asset')->assertSee('Daftar sementara hanya memuat aset Registry')
            ->assertSee('Ringkasan belum tersedia')->assertDontSee('Belum terhubung');
        Http::assertSentCount(3);
    }

    public function test_valid_summary_survives_inventory_failure(): void
    {
        Http::fake([
            'mart.test/v1/reliability/assets/inventory-summary*' => Http::response($this->summary()),
            'mart.test/v1/reliability/assets/inventory?*' => Http::response([], 503),
        ]);
        $this->signIn();
        $this->get('/assets')->assertOk()->assertSee('1.234')->assertSee('Belum terhubung')->assertDontSee('Synthetic inventory asset');
    }

    public function test_empty_verified_inventory_displays_real_zero_counts(): void
    {
        $this->fake($this->summary(['counts' => ['total' => 0, 'equipment' => 0, 'component' => 0, 'part' => 0, 'system' => 0, 'unknown' => 0], 'classification' => ['unknown_count' => 0]]), $this->page());
        $this->signIn();
        $response = $this->get('/assets')->assertOk()->assertSee('Tidak ada aset yang sesuai')->assertDontSee('Ringkasan belum tersedia');
        foreach ($this->document($response->getContent())->query('//dl[@class="asset-summary-grid"]//span[@class="asset-summary-value"]') as $value) {
            $this->assertSame('0', $value->textContent);
        }
    }

    public function test_invalid_scope_counts_classification_or_coverage_are_not_presented_as_verified(): void
    {
        $this->signIn();
        foreach ([
            ['scope' => ['site_code' => 'OTHER']],
            ['scope' => ['organization_code' => 'OTHER']],
            ['scope' => ['unit' => 'CS02']],
            ['scope' => ['population' => 'REGISTRY']],
            ['counts' => ['total' => 1210]],
            ['counts' => ['equipment' => '1000']],
            ['counts' => ['component' => -1]],
            ['counts' => ['part' => null]],
            ['classification' => ['unknown_count' => 0]],
            ['classification' => ['basis' => 'DEPTH_GUESS']],
            ['classification' => ['status' => 'UNKNOWN']],
            ['coverage' => ['full_source_baseline_complete' => 'false']],
            ['coverage' => ['state' => 'COMPLETE_AS_OF_MANUAL_SCAN']],
            ['coverage' => ['state' => 'COMPLETE_AS_OF_MANUAL_SCAN', 'full_source_baseline_complete' => true]],
            ['coverage' => ['last_completed_at' => '<script>private</script>']],
        ] as $changes) {
            Http::swap(new Factory);
            Http::preventStrayRequests();
            $this->fake($this->summary($changes), $this->page([$this->asset()]));
            $this->get('/assets')->assertOk()->assertSee('Ringkasan belum tersedia')->assertSee('Synthetic inventory asset')->assertDontSee('1.234');
        }
    }

    public function test_completed_scan_displays_its_time_without_claiming_current_freshness(): void
    {
        $this->fake($this->summary(['coverage' => ['state' => 'COMPLETE_AS_OF_MANUAL_SCAN', 'full_source_baseline_complete' => true, 'last_completed_at' => '2026-11-06T12:00:00Z']]), $this->page());
        $this->signIn();
        $this->get('/assets')->assertOk()->assertSee('2026-11-06T12:00:00Z')->assertSee('Bukan jaminan kesegaran saat ini')->assertDontSee('Cakupan belum lengkap');
    }

    public function test_completed_source_scan_with_pending_projection_keeps_counts_but_stays_partial(): void
    {
        $this->fake($this->summary(['coverage' => ['full_source_baseline_complete' => true, 'pending_projection' => 3, 'last_completed_at' => '2026-11-06T12:00:00Z']]), $this->page());
        $this->signIn();
        $this->get('/assets')->assertOk()->assertSee('1.234')->assertSee('Cakupan belum lengkap')->assertSee('3 aset masih menunggu proyeksi')
            ->assertDontSee('Ringkasan belum tersedia');
    }

    public function test_inventory_detail_keeps_unknown_and_original_unit_without_registry_actions(): void
    {
        Http::fake(['mart.test/v1/reliability/assets/inventory/*' => Http::response($this->asset())]);
        $this->signIn();
        $this->get('/assets/'.self::ID)->assertOk()->assertSee('Synthetic inventory asset')->assertSee('Belum dikategorikan')
            ->assertSee('Relasi parent sumber ke CS01')->assertSee('Belum terdaftar')->assertDontSee('PRIVATE-RAW')
            ->assertDontSee('Buka konteks Operasi')->assertSee('Lihat WO untuk Asset ini')->assertSee('History gangguan')->assertDontSee('Buat draft inspeksi untuk Asset ini');
        Http::assertSentCount(1);
    }

    public function test_registered_inventory_detail_retains_existing_role_gated_actions(): void
    {
        Http::fake(['mart.test/v1/reliability/assets/inventory/*' => fn () => Http::response($this->asset(['registered' => true, 'hierarchy_category' => 'part']))]);
        $this->signIn();
        $this->get('/assets/'.self::ID)->assertOk()->assertSee('Part')->assertSee('Buka konteks Operasi')->assertSee('Buat draft inspeksi untuk Asset ini');
        $this->signIn('MANAGER');
        $this->get('/assets/'.self::ID)->assertOk()->assertSee('Lihat WO untuk Asset ini')->assertDontSee('Buat draft inspeksi untuk Asset ini');
    }

    public function test_existing_registry_detail_links_survive_an_asset_outside_inventory_scope(): void
    {
        Http::fake([
            'mart.test/v1/reliability/assets/inventory/*' => Http::response([], 404),
            'mart.test/v1/reliability/assets/'.rawurlencode(self::ID) => Http::response($this->asset()),
        ]);
        $this->signIn();
        $this->get('/assets/'.self::ID)->assertOk()->assertSee('Synthetic inventory asset')->assertSee('Buka konteks Operasi');
        Http::assertSentCount(2);
    }

    public function test_inventory_does_not_guess_categories_or_registry_membership_from_source_type(): void
    {
        $this->signIn();
        foreach ([['hierarchy_category' => null], ['hierarchy_category' => 'PRODUCTION'], ['registered' => 'true'], ['scope_basis' => 'GUESSED']] as $changes) {
            Http::swap(new Factory);
            Http::preventStrayRequests();
            $this->fake($this->summary(), $this->page([$this->asset($changes)]));
            $this->get('/assets')->assertOk()->assertSee('Belum terhubung')->assertDontSee('Synthetic inventory asset')->assertSee('1.234');
        }
    }

    public function test_inventory_search_and_category_are_forwarded_and_retained_in_pagination(): void
    {
        $this->signIn();
        $this->fake($this->summary(), $this->page([$this->asset()], ['total' => 80, 'offset' => 25, 'has_more' => true]));
        $this->get('/assets?q=SYNTHETIC-PUMP&category=component&offset=25')->assertOk()->assertSee('Synthetic inventory asset')->assertSee('Cari KKS / deskripsi')->assertSee('q=SYNTHETIC-PUMP', false)->assertSee('category=component', false)->assertSee('offset=50', false);
        Http::assertSent(fn ($r) => str_contains($r->url(), '/assets/inventory?') && $r['q'] === 'SYNTHETIC-PUMP' && $r['category'] === 'component');
    }

    public function test_inventory_search_never_falls_back_to_unfiltered_registry(): void
    {
        $this->signIn();
        Http::fake(['mart.test/*' => fn () => Http::response([], 404)]);
        $this->get('/assets?q=SYNTHETIC-PUMP')->assertOk()->assertSee('Belum terhubung')->assertDontSee('Daftar sementara hanya memuat aset Registry');
        Http::assertNotSent(fn ($r) => str_contains($r->url(), '/assets?'));
    }
}
