<?php

namespace Tests\Feature;

use App\Models\InspectionDraft;
use App\Models\User;
use App\Support\DevelopmentAccess;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Http\Client\Factory;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Cache;
use Illuminate\Support\Facades\Http;
use Tests\TestCase;

class DraftFeaturesTest extends TestCase
{
    use RefreshDatabase;

    private const PASSWORD = 'test-only-inspection-password';

    protected function setUp(): void
    {
        parent::setUp();
        Cache::flush();
        config(['services.asset_mapping.file' => null]);
        Http::preventStrayRequests();
        config(['services.reliability_mart.url' => 'http://mart.test']);
    }

    private function account(string $role = 'ENGINEER'): User
    {
        return User::factory()->create(['password' => self::PASSWORD, 'roles' => [$role], 'active' => true])->refresh();
    }

    private function signIn(User $user): static
    {
        return $this->actingAs($user)->withSession(['auth_version' => $user->auth_version]);
    }

    private function requestData(array $changes = []): array
    {
        return array_replace(['request_reference' => 'TEST-REQUEST', 'request_summary' => 'Synthetic inspection request'], $changes);
    }

    private function backlog(array $changes = []): array
    {
        return ['items' => [array_replace(['canonical_id' => 'wo:BSR:1', 'equipment_id' => 'asset:BSR:1', 'work_order_id' => 'wo:1', 'status' => 'WAPPR', 'site_code' => 'BSR', 'organization_code' => 'IP', 'source_detail' => ['work_order_number' => 'TEST-WO-1', 'asset_number' => 'TEST-ASSET-1'], 'sources' => ['secret' => 'DO-NOT-EXPOSE']], $changes)],
            'meta' => ['total' => 18, 'offset' => 0, 'limit' => 10, 'has_more' => true]];
    }

    public function test_each_role_can_log_in_by_username_and_read_workspace(): void
    {
        foreach (['ADMIN', 'ENGINEER', 'SUPERVISOR', 'MANAGER'] as $role) {
            $user = $this->account($role);
            $this->post('/login', ['login' => strtoupper($user->username), 'password' => self::PASSWORD])->assertRedirect(route('home'));
            $this->assertAuthenticatedAs($user);
            $this->get('/')->assertOk()->assertSee('Beranda kosong');
            $this->get('/inspections')->assertOk()->assertSee('Total draft lokal');
            $this->post('/logout')->assertRedirect(route('login'));
            $this->assertGuest();
        }
    }

    public function test_login_failure_is_generic_for_username_and_email(): void
    {
        foreach (['not-a-user', 'unknown@example.test'] as $login) {
            $this->post('/login', ['login' => $login, 'password' => 'wrong'])->assertSessionHasErrors(['login' => 'Username/email atau kata sandi tidak sesuai.']);
            $this->assertGuest();
        }
    }

    public function test_local_accounts_reject_nonlocal_environment_and_stale_session(): void
    {
        $user = $this->account();
        $user->development_only = true;
        $user->save();
        $this->post('/login', ['login' => $user->username, 'password' => self::PASSWORD])->assertSessionHasErrors('login');
        $this->assertGuest();
        $this->signIn($user)->get('/')->assertRedirect(route('login'));
        $this->assertGuest();
    }

    public function test_development_accounts_require_both_loopback_ip_and_host(): void
    {
        $user = $this->account();
        $user->development_only = true;
        $this->app['env'] = 'local';
        $this->assertTrue(DevelopmentAccess::allowed($user, Request::create('http://127.0.0.1/', server: ['REMOTE_ADDR' => '127.0.0.1'])));
        $this->assertFalse(DevelopmentAccess::allowed($user, Request::create('http://127.0.0.1/', server: ['REMOTE_ADDR' => '192.0.2.10'])));
        $this->assertFalse(DevelopmentAccess::allowed($user, Request::create('http://public.example/', server: ['REMOTE_ADDR' => '127.0.0.1'])));
        $this->app['env'] = 'production';
        $this->assertFalse(DevelopmentAccess::allowed($user, Request::create('http://127.0.0.1/', server: ['REMOTE_ADDR' => '127.0.0.1'])));
    }

    public function test_new_pages_require_authentication(): void
    {
        foreach (['/action-board', '/inspections', '/inspections/create'] as $path) {
            $this->get($path)->assertRedirect(route('login'));
        }
        Http::assertNothingSent();
    }

    public function test_action_board_separates_live_wappr_records_from_unknown_risk(): void
    {
        Http::fake(['mart.test/*' => Http::response($this->backlog())]);
        $this->signIn($this->account('MANAGER'))->get('/action-board')->assertOk()->assertSee('STRUKTUR KEPUTUSAN')
            ->assertSee('Peringkat belum dihitung')->assertSee('TEST-WO-1')->assertSee('18 record WAPPR')
            ->assertDontSee('DO-NOT-EXPOSE')->assertSee('bukan jumlah gangguan');
        Http::assertSent(fn ($r) => $r->method() === 'GET' && $r['status'] === 'WAPPR' && $r['limit'] === 10);
        Http::assertSentCount(1);
    }

    public function test_action_board_rejects_wrong_scope_status_and_connection_errors(): void
    {
        foreach ([Http::response($this->backlog(['status' => 'COMP'])), Http::response($this->backlog(['site_code' => 'OTHER'])), Http::response([], 503)] as $response) {
            Http::swap(new Factory);
            Http::preventStrayRequests();
            Http::fake(['mart.test/*' => $response]);
            $this->signIn($this->account('SUPERVISOR'))->get('/action-board')->assertOk()->assertSee('Backlog belum terhubung')->assertDontSee('TEST-WO-1');
        }
    }

    public function test_asset_navigation_contains_nested_master_asset_and_action_board(): void
    {
        $this->signIn($this->account())->get('/')->assertOk()->assertSee('<details class="asset-menu"', false)->assertSee('Master Asset')->assertSee('Action Board')->assertSee('Beranda kosong');
        Http::assertNothingSent();
    }

    public function test_engineer_can_save_request_then_finding_and_recommendation_as_one_draft(): void
    {
        $engineer = $this->account();
        $other = $this->account();
        $this->signIn($engineer)->get('/inspections/create')->assertOk();
        $this->post('/inspections', $this->requestData(['created_by' => $other->id, 'version' => 99]))->assertRedirect();
        $draft = InspectionDraft::firstOrFail();
        $this->assertSame($engineer->id, $draft->created_by);
        $this->assertSame(1, $draft->version);
        $this->get('/inspections/'.$draft->id)->assertOk()->assertSee('Permintaan draft');
        $data = $this->requestData(['method' => 'VISUAL', 'inspected_on' => now()->format('Y-m-d'), 'finding' => 'Synthetic inspection finding', 'recommendation' => 'Synthetic recommended action', 'version' => 1]);
        $this->put('/inspections/'.$draft->id, $data)->assertRedirect(route('inspections.show', $draft));
        $draft->refresh();
        $this->assertSame('Rekomendasi draft', $draft->stageLabel());
        $this->assertSame(2, $draft->version);
        $this->assertDatabaseCount('inspection_drafts', 1);
        $this->get('/inspections')->assertOk()->assertSee('Synthetic recommended action')->assertSee('Belum dinilai');
        Http::assertNothingSent();
    }

    public function test_read_only_roles_and_other_engineers_cannot_change_a_draft(): void
    {
        $owner = $this->account();
        $draft = new InspectionDraft($this->requestData());
        $draft->created_by = $owner->id;
        $draft->save();
        foreach (['ADMIN', 'SUPERVISOR', 'MANAGER'] as $role) {
            $this->signIn($this->account($role))->get('/inspections')->assertOk();
            $this->get('/inspections/create')->assertForbidden();
            $this->post('/inspections', $this->requestData())->assertForbidden();
            $this->get('/inspections/'.$draft->id)->assertOk();
            $this->get('/inspections/'.$draft->id.'/edit')->assertForbidden();
            $this->put('/inspections/'.$draft->id, $this->requestData(['version' => 1]))->assertForbidden();
        }
        $this->signIn($this->account())->put('/inspections/'.$draft->id, $this->requestData(['version' => 1]))->assertForbidden();
        $this->assertSame(1, $draft->fresh()->version);
    }

    public function test_recommendation_requires_actual_inspection_fields(): void
    {
        $this->signIn($this->account());
        $this->post('/inspections', $this->requestData(['recommendation' => 'Synthetic recommendation']))
            ->assertSessionHasErrors(['finding', 'method', 'inspected_on']);
        $this->post('/inspections', $this->requestData(['method' => 'VISUAL', 'finding' => 'Synthetic finding', 'inspected_on' => now()->addDay()->format('Y-m-d')]))
            ->assertSessionHasErrors('inspected_on');
        $this->assertDatabaseCount('inspection_drafts', 0);
    }

    public function test_draft_stale_revision_is_rejected_and_text_is_escaped(): void
    {
        $this->signIn($this->account());
        $this->post('/inspections', $this->requestData(['request_summary' => '<script>not executable</script>']))->assertRedirect();
        $draft = InspectionDraft::firstOrFail();
        $this->get('/inspections/'.$draft->id)->assertOk()->assertSee('&lt;script&gt;', false)->assertDontSee('<script>not executable</script>', false);
        $this->put('/inspections/'.$draft->id, $this->requestData(['version' => 999]))->assertSessionHasErrors('version');
        $this->assertSame(1, $draft->fresh()->version);
    }

    public function test_asset_references_are_verified_and_no_asset_payload_is_copied(): void
    {
        Http::fake(['mart.test/*' => Http::response(['canonical_id' => 'asset:BSR:1', 'site_code' => 'BSR', 'organization_code' => 'IP', 'description' => 'SOURCE-DESCRIPTION-NOT-COPIED'])]);
        $this->signIn($this->account());
        $this->post('/inspections', $this->requestData(['asset_ref' => 'asset:BSR:1']))->assertRedirect();
        $draft = InspectionDraft::firstOrFail();
        $this->assertSame('asset:BSR:1', $draft->asset_ref);
        $this->assertStringNotContainsString('SOURCE-DESCRIPTION-NOT-COPIED', $draft->toJson());
        Http::assertSent(fn ($r) => $r->method() === 'GET');
        Http::swap(new Factory);
        Http::preventStrayRequests();
        Http::fake(['mart.test/*' => Http::response([], 503)]);
        $this->post('/inspections', $this->requestData(['asset_ref' => 'asset:unverified']))->assertSessionHasErrors('asset_ref');
        $this->assertDatabaseCount('inspection_drafts', 1);
    }

    public function test_draft_search_and_stage_filters_use_local_records_only(): void
    {
        $this->signIn($this->account());
        $this->post('/inspections', $this->requestData());
        $this->post('/inspections', $this->requestData(['request_reference' => 'SECOND-TEST', 'method' => 'VISUAL', 'inspected_on' => now()->format('Y-m-d'), 'finding' => 'Synthetic finding', 'recommendation' => 'Synthetic recommendation']));
        $this->get('/inspections?stage=recommendation')->assertOk()->assertSee('SECOND-TEST')->assertDontSee('TEST-REQUEST');
        $this->get('/inspections?q=SECOND-TEST')->assertOk()->assertSee('SECOND-TEST')->assertDontSee('TEST-REQUEST');
        $this->get('/inspections?stage=unapproved')->assertSessionHasErrors('stage');
        Http::assertNothingSent();
    }
}
