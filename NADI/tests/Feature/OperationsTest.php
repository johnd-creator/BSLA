<?php

namespace Tests\Feature;

use App\Models\User;
use App\Services\OperationsDraft;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Http;
use Tests\TestCase;

class OperationsTest extends TestCase
{
    use RefreshDatabase;

    private const ASSET = 'asset:MAXIMO:MXASSET:BSR:IP:TEST-EQUIPMENT';

    protected function setUp(): void
    {
        parent::setUp();
        Http::preventStrayRequests();
        config(['services.reliability_mart.url' => 'http://mart.test']);
    }

    private function signIn(string $role = 'ENGINEER'): void
    {
        $user = User::factory()->create(['roles' => [$role], 'active' => true])->refresh();
        $this->actingAs($user)->withSession(['auth_version' => $user->auth_version]);
    }

    private function asset(array $changes = []): array
    {
        return array_replace(['canonical_id' => self::ASSET, 'source_asset_number' => 'TEST-EQUIPMENT', 'description' => 'Verified synthetic equipment', 'site_code' => 'BSR', 'organization_code' => 'IP', 'unit' => 'CS01', 'status' => 'OPERATING', 'raw' => 'PRIVATE-RAW'], $changes);
    }

    private function fakeMart(array $changes = []): void
    {
        $asset = $this->asset($changes);
        Http::fake([
            'mart.test/v1/reliability/assets/*' => fn () => Http::response($asset),
            'mart.test/v1/reliability/assets?*' => fn ($request) => Http::response(['items' => [$asset], 'meta' => ['offset' => (int) ($request['offset'] ?? 0), 'limit' => 25, 'total' => 26, 'has_more' => (int) ($request['offset'] ?? 0) < 25]]),
        ]);
    }

    public function test_operations_requires_login_and_supports_only_get(): void
    {
        $this->get('/operations')->assertRedirect(route('login'));
        $this->signIn();
        $this->post('/operations')->assertStatus(405);
        Http::assertNothingSent();
    }

    public function test_all_four_roles_can_read_the_unconnected_operations_foundation(): void
    {
        $this->fakeMart();
        foreach (['ADMIN', 'ENGINEER', 'SUPERVISOR', 'MANAGER'] as $role) {
            $this->signIn($role);
            $this->get('/operations')->assertOk()->assertSee('Historian belum terhubung')->assertSee('bukan pengganti HMI')->assertSee('Belum dinilai')->assertSee('Jumlah WO bukan jumlah kejadian gangguan tervalidasi')->assertSee('Cache tampilan')->assertSee('Belum aktif')->assertSee('Verified synthetic equipment')->assertDontSee('PRIVATE-RAW');
        }
        Http::assertSentCount(4);
        Http::assertSent(fn ($r) => $r->method() === 'GET' && $r['limit'] === 25 && $r['site_code'] === 'BSR' && $r['organization_code'] === 'IP');
    }

    public function test_selected_equipment_links_exact_source_identity_without_implying_live_status(): void
    {
        $this->fakeMart();
        $this->signIn();
        $this->get(route('operations', ['equipment' => self::ASSET, 'unit' => 'CS01']))->assertOk()->assertSee('ASSET TERPILIH')->assertSee('Bukan status operasi realtime')->assertSee('Belum diverifikasi')->assertSee(route('work-orders.index', ['asset_ref' => self::ASSET]), false)->assertSee(route('inspections.create', ['asset_ref' => self::ASSET]), false)->assertSee(route('assets.show', self::ASSET), false)->assertDontSee('PRIVATE-RAW');
        Http::assertSentCount(2);
        Http::assertSent(fn ($r) => $r->url() === 'http://mart.test/v1/reliability/assets/'.rawurlencode(self::ASSET) && $r->method() === 'GET');
    }

    public function test_unavailable_api_shows_no_fabricated_equipment_or_values(): void
    {
        Http::fake(['mart.test/*' => Http::response([], 503)]);
        $this->signIn();
        $this->get(route('operations', ['equipment' => self::ASSET]))->assertOk()->assertSee('Daftar equipment belum terhubung')->assertSee('Detail equipment belum terhubung')->assertSee('Belum terhubung')->assertDontSee('ASSET TERPILIH');
        Http::assertSentCount(2);
    }

    public function test_cross_scope_identity_is_never_exposed(): void
    {
        $this->signIn();
        $this->fakeMart(['site_code' => 'OTHER', 'description' => 'MUST-NOT-EXPOSE']);
        $this->get(route('operations', ['equipment' => self::ASSET]))->assertOk()->assertSee('Detail equipment belum terhubung')->assertDontSee('ASSET TERPILIH')->assertDontSee('MUST-NOT-EXPOSE');
    }

    public function test_selected_identity_must_match_the_exact_requested_asset(): void
    {
        Http::fake([
            'mart.test/v1/reliability/assets/*' => fn () => Http::response($this->asset(['canonical_id' => 'asset:OTHER:WRONG', 'description' => 'WRONG-DETAIL'])),
            'mart.test/v1/reliability/assets?*' => fn () => Http::response(['items' => [$this->asset()], 'meta' => ['offset' => 0, 'limit' => 25, 'total' => 1, 'has_more' => false]]),
        ]);
        $this->signIn();
        $this->get(route('operations', ['equipment' => self::ASSET]))->assertOk()->assertSee('Detail equipment belum terhubung')->assertDontSee('ASSET TERPILIH')->assertDontSee('WRONG-DETAIL');
    }

    public function test_boiler_draft_links_only_to_local_details_without_source_binding(): void
    {
        Http::fake(['mart.test/*' => Http::response([], 503)]);
        $this->signIn();
        $response = $this->get('/operations')->assertOk()
            ->assertSee('Boiler overview')->assertSee('Semua nilai masih placeholder')
            ->assertSee('SIMULASI WARNA')->assertSee('bukan kondisi aset')
            ->assertSee('? Unknown')->assertSee('Alarm DCS')
            ->assertSee('Kualitas: unknown')->assertSee('Link Asset belum dipetakan');
        $document = new \DOMDocument;
        @$document->loadHTML($response->getContent());
        $xpath = new \DOMXPath($document);
        $this->assertCount(18, $xpath->query('//*[@data-operations-draft]//a[@data-component]'));
        $this->assertCount(18, $xpath->query('//nav[@aria-label="Detail komponen BOIL"]/a'));
        $this->assertCount(8, $xpath->query('//nav[@aria-label="Layar proses draft"]//a'));
        foreach ($xpath->query('//*[@data-operations-draft]//a') as $link) {
            $this->assertStringStartsWith(route('operations').'?screen=BOIL&component=', $link->getAttribute('href'));
            $this->assertStringEndsWith('#ops-component-detail', $link->getAttribute('href'));
        }
        $this->assertCount(0, $xpath->query('//*[@id="ops-wellness-demo" and @checked]'));
        $this->assertCount(0, $xpath->query('//*[@data-operations-draft]//button'));
        $this->assertCount(0, $xpath->query('//*[@data-operations-draft]//script | //*[@data-operations-draft]//*[@data-historian or @data-cems]'));
        Http::assertSentCount(1);
        Http::assertSent(fn ($request) => $request->method() === 'GET' && str_starts_with($request->url(), 'http://mart.test/v1/reliability/assets?'));
    }

    public function test_every_boiler_component_has_read_only_placeholder_details(): void
    {
        $this->signIn('MANAGER');
        Http::fake(['mart.test/*' => Http::response([], 503)]);
        $this->assertCount(18, OperationsDraft::components());
        foreach (OperationsDraft::components() as $id => $detail) {
            $response = $this->get(route('operations', ['component' => $id]))->assertOk()
                ->assertSee('id="ops-component-detail"', false)->assertSee($detail['label'])
                ->assertSee('Tutup detail')->assertSee('Pembacaan pada draft')
                ->assertSee('Bukan pernyataan bebas alarm.')->assertSee('Tidak mengikuti warna simulasi.')
                ->assertSee('Canonical Asset')->assertSee('Tag historian')->assertSee('Belum dipetakan');
            $document = new \DOMDocument;
            @$document->loadHTML($response->getContent());
            $xpath = new \DOMXPath($document);
            $this->assertCount(count($detail['units']), $xpath->query('//*[@id="ops-component-detail"]//*[@class="ops-reading"]'));
            $this->assertCount(0, $xpath->query('//*[@id="ops-component-detail"]//input | //*[@id="ops-component-detail"]//button | //*[@id="ops-component-detail"]//form'));
        }
        Http::assertSentCount(18);
        Http::assertNotSent(fn ($request) => $request->method() !== 'GET' || ! str_starts_with($request->url(), 'http://mart.test/v1/reliability/assets?'));
    }

    public function test_unreferenced_screens_do_not_invent_diagrams_or_parameters(): void
    {
        $this->signIn();
        Http::fake(['mart.test/*' => Http::response([], 503)]);
        foreach (array_slice(OperationsDraft::SCREENS, 1) as $screen) {
            $response = $this->get(route('operations', ['screen' => $screen]))->assertOk()
                ->assertSee($screen.' · Referensi belum tersedia')
                ->assertSee('Diagram, equipment, jalur proses, dan parameter belum dibuat.')
                ->assertSee('? Unknown')->assertSee('Tidak terhubung')->assertSee('Belum dinilai')
                ->assertDontSee('class="ops-process"', false)->assertDontSee('ops-reading-grid')
                ->assertDontSee('MILL G')->assertDontSee('Contoh warna wellness');
            $document = new \DOMDocument;
            @$document->loadHTML($response->getContent());
            $xpath = new \DOMXPath($document);
            $active = $xpath->query('//nav[@aria-label="Layar proses draft"]//a[@aria-current="page"]');
            $this->assertCount(1, $active);
            $this->assertSame($screen, $active->item(0)->textContent);
        }
        Http::assertSentCount(7);
    }

    public function test_registry_filter_and_pagination_stay_open_and_preserve_draft_context(): void
    {
        $this->signIn();
        $this->fakeMart();
        foreach ([['unit' => 'CS01'], ['offset' => 25], ['unit' => ''], ['unit' => '0'], ['offset' => 0]] as $query) {
            $response = $this->get(route('operations', array_merge($query, ['screen' => 'BOIL', 'component' => 'drum'])))->assertOk();
            $document = new \DOMDocument;
            @$document->loadHTML($response->getContent());
            $xpath = new \DOMXPath($document);
            $this->assertCount(1, $xpath->query('//details[@class="ops-registry" and @open]'));
            $this->assertCount(2, $xpath->query('//input[@name="screen" and @value="BOIL"]'));
            $this->assertCount(2, $xpath->query('//input[@name="component" and @value="drum"]'));
            foreach ($xpath->query('//*[@class="operations-pagination"]//a') as $link) {
                $this->assertStringContainsString('screen=BOIL', $link->getAttribute('href'));
                $this->assertStringContainsString('component=drum', $link->getAttribute('href'));
            }
        }
    }

    public function test_selected_registry_asset_is_not_implicitly_mapped_to_a_draft_symbol(): void
    {
        $this->signIn('MANAGER');
        $this->fakeMart();
        $response = $this->get(route('operations', ['component' => 'drum', 'equipment' => self::ASSET]))->assertOk()
            ->assertSee('ASSET TERPILIH')->assertSee('tidak menghubungkannya otomatis ke DRUM');
        $document = new \DOMDocument;
        @$document->loadHTML($response->getContent());
        $xpath = new \DOMXPath($document);
        $this->assertStringNotContainsString('TEST-EQUIPMENT', $xpath->query('//*[@id="ops-component-detail"]')->item(0)->textContent);
        $this->assertCount(0, $xpath->query('//a[contains(@href, "/inspections/create")]'));
        Http::assertSentCount(2);
    }

    public function test_draft_detail_is_readable_by_each_role_without_extra_permissions(): void
    {
        $this->fakeMart();
        foreach (['ADMIN', 'ENGINEER', 'SUPERVISOR', 'MANAGER'] as $role) {
            $this->signIn($role);
            $this->get('/operations?component=drum')->assertOk()->assertSee('Tutup detail');
        }
        Http::assertSentCount(4);
    }

    public function test_invalid_input_is_rejected_before_any_source_read(): void
    {
        $this->signIn();
        $this->get('/operations?offset=-1')->assertSessionHasErrors('offset');
        $this->get('/operations?unit='.str_repeat('x', 61))->assertSessionHasErrors('unit');
        $this->get('/operations?equipment=asset%2Fwrong')->assertNotFound();
        $this->get('/operations?screen=INVALID')->assertSessionHasErrors('screen');
        $this->get('/operations?screen[]=BOIL')->assertSessionHasErrors('screen');
        $this->get('/operations?component=invalid')->assertSessionHasErrors('component');
        $this->get('/operations?component[]=drum')->assertSessionHasErrors('component');
        $this->get('/operations?screen=TURB&component=drum')->assertNotFound();
        Http::assertNothingSent();
    }
}
