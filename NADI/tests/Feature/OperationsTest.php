<?php

namespace Tests\Feature;

use App\Models\User;
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
            'mart.test/v1/reliability/assets?*' => fn () => Http::response(['items' => [$asset], 'meta' => ['offset' => 0, 'limit' => 25, 'total' => 26, 'has_more' => true]]),
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

    public function test_invalid_input_is_rejected_before_any_source_read(): void
    {
        $this->signIn();
        $this->get('/operations?offset=-1')->assertSessionHasErrors('offset');
        $this->get('/operations?unit='.str_repeat('x', 61))->assertSessionHasErrors('unit');
        $this->get('/operations?equipment=asset%2Fwrong')->assertNotFound();
        Http::assertNothingSent();
    }
}
