<?php

namespace Tests\Feature;

use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Http\Client\Factory;
use Illuminate\Support\Facades\Cache;
use Illuminate\Support\Facades\Hash;
use Illuminate\Support\Facades\Http;
use Tests\TestCase;

class WorkspaceTest extends TestCase
{
    use RefreshDatabase;

    private const PASSWORD = 'a-test-only-password-123';

    protected function setUp(): void
    {
        parent::setUp();
        Http::preventStrayRequests();
        config(['services.asset_mapping.file' => null]);
        Cache::flush();
        config(['services.reliability_mart.url' => 'http://mart.test']);
    }

    private function account(array $roles = ['ADMIN'], bool $active = true): User
    {
        return User::factory()->create(['password' => self::PASSWORD, 'roles' => $roles, 'active' => $active])->refresh();
    }

    private function signedIn(User $user): static
    {
        return $this->actingAs($user)->withSession(['auth_version' => $user->auth_version]);
    }

    private function input(array $extra = []): array
    {
        return array_replace(['name' => 'New User', 'username' => 'newuser', 'email' => 'new@example.test', 'password' => self::PASSWORD,
            'password_confirmation' => self::PASSWORD, 'roles' => ['ENGINEER'], 'active' => '1'], $extra);
    }

    private function asset(array $extra = []): array
    {
        return array_replace(['canonical_id' => 'asset:BSR:123', 'contract_version' => '1.0', 'site_code' => 'BSR',
            'organization_code' => 'IP', 'hierarchy_category' => 'equipment', 'scope_basis' => 'DIRECT_SOURCE_UNIT', 'registered' => true, 'source_asset_number' => '123', 'description' => 'Verified test asset'], $extra);
    }

    private function page(array $items, array $meta = []): array
    {
        return ['items' => $items, 'meta' => array_replace(['total' => count($items), 'offset' => 0, 'limit' => 25, 'has_more' => false], $meta)];
    }

    public function test_guest_cannot_access_workspace_assets_or_administration(): void
    {
        foreach (['/', '/assets', '/assets/123', '/users', '/roles', '/users/create'] as $path) {
            $this->get($path)->assertRedirect(route('login'));
        }
        Http::assertNothingSent();
    }

    public function test_login_page_has_accessible_fields_and_no_public_registration(): void
    {
        $this->get('/login')->assertOk()->assertSee('Masuk ke workspace')->assertSee('autocomplete="current-password"', false);
        $this->get('/register')->assertNotFound();
    }

    public function test_successful_login_regenerates_session_and_logout_revokes_it(): void
    {
        $user = $this->account();
        $this->withSession(['before' => 'login']);
        $previous = session()->getId();
        $this->post('/login', ['email' => strtoupper($user->email), 'password' => self::PASSWORD])->assertRedirect(route('home'));
        $this->assertAuthenticatedAs($user);
        $this->assertNotSame($previous, session()->getId());
        $this->get('/')->assertOk()->assertSee('Ringkasan workspace')->assertDontSee('Semua user');
        $this->post('/logout')->assertRedirect(route('login'));
        $this->assertGuest();
        $this->get('/assets')->assertRedirect(route('login'));
    }

    public function test_wrong_unknown_and_disabled_accounts_get_same_error(): void
    {
        $active = $this->account();
        $disabled = $this->account(['ENGINEER'], false);
        foreach ([$active->email, $disabled->email, 'unknown@example.test'] as $email) {
            $this->post('/login', ['email' => $email, 'password' => $email === $disabled->email ? self::PASSWORD : 'incorrect'])
                ->assertSessionHasErrors(['login' => 'Username/email atau kata sandi tidak sesuai.']);
            $this->assertGuest();
        }
    }

    public function test_login_attempts_are_limited(): void
    {
        for ($i = 0; $i < 5; $i++) {
            $this->post('/login', ['email' => 'unknown@example.test', 'password' => 'wrong']);
        }
        $this->post('/login', ['email' => 'unknown@example.test', 'password' => 'wrong'])
            ->assertSessionHasErrors(['login' => 'Terlalu banyak percobaan. Coba lagi dalam satu menit.']);
    }

    public function test_non_admin_roles_cannot_read_or_mutate_users_or_roles(): void
    {
        $target = $this->account();
        foreach ([['ENGINEER'], ['SUPERVISOR'], ['MANAGER'], ['ENGINEER', 'SUPERVISOR']] as $roles) {
            $user = $this->account($roles);
            $this->signedIn($user);
            $this->get('/')->assertOk()->assertDontSee('User management');
            foreach (['/users', '/roles', '/users/create', "/users/{$target->id}/edit"] as $path) {
                $this->get($path)->assertForbidden();
            }
            $this->post('/users', $this->input())->assertForbidden();
            $this->put("/users/{$target->id}", $this->input(['version' => 1]))->assertForbidden();
        }
        $this->assertDatabaseMissing('users', ['email' => 'new@example.test']);
    }

    public function test_admin_can_create_multi_role_account_with_hashed_password(): void
    {
        $this->signedIn($this->account());
        $this->get('/users')->assertOk();
        $this->get('/roles')->assertOk()->assertSee('Supervisor');
        $this->get('/users/create')->assertOk();
        $this->post('/users', $this->input(['roles' => ['ENGINEER', 'SUPERVISOR'], 'auth_version' => 999]))->assertRedirect(route('users.index'));
        $user = User::where('email', 'new@example.test')->firstOrFail();
        $this->assertTrue(Hash::check(self::PASSWORD, $user->password));
        $this->assertSame(['ENGINEER', 'SUPERVISOR'], $user->roles);
        $this->assertSame(1, $user->auth_version);
        $this->assertArrayNotHasKey('password', $user->toArray());
        $this->assertArrayNotHasKey('auth_version', $user->toArray());
    }

    public function test_invalid_roles_weak_password_and_duplicate_email_are_rejected(): void
    {
        $admin = $this->account();
        $this->signedIn($admin);
        $this->post('/users', $this->input(['roles' => ['SUPERADMIN']]))->assertSessionHasErrors('roles.0');
        $this->post('/users', $this->input(['roles' => ['ADMIN', 'ADMIN']]))->assertSessionHasErrors('roles.0');
        $this->post('/users', $this->input(['password' => 'short', 'password_confirmation' => 'short']))->assertSessionHasErrors('password');
        $this->post('/users', $this->input(['email' => strtoupper($admin->email)]))->assertSessionHasErrors('email');
    }

    public function test_admin_can_change_roles_password_status_and_reject_stale_updates(): void
    {
        $admin = $this->account();
        $target = $this->account(['ENGINEER']);
        $this->signedIn($admin)->get("/users/{$target->id}/edit")->assertOk();
        $data = $this->input(['email' => $target->email, 'version' => $target->auth_version, 'roles' => ['SUPERVISOR'],
            'password' => 'replacement-test-password', 'password_confirmation' => 'replacement-test-password', 'active' => '0']);
        $this->put("/users/{$target->id}", $data)->assertRedirect(route('users.index'));
        $target->refresh();
        $this->assertFalse($target->active);
        $this->assertSame(['SUPERVISOR'], $target->roles);
        $this->assertSame(2, $target->auth_version);
        $this->assertTrue(Hash::check('replacement-test-password', $target->password));
        $this->put("/users/{$target->id}", $data)->assertSessionHasErrors('version');
        $data['version'] = 2;
        $data['active'] = '1';
        $data['password'] = $data['password_confirmation'] = '';
        $this->put("/users/{$target->id}", $data)->assertRedirect(route('users.index'));
        $this->assertTrue($target->fresh()->active);
    }

    public function test_admin_cannot_disable_or_change_own_roles(): void
    {
        $admin = $this->account();
        $this->signedIn($admin);
        $data = $this->input(['email' => $admin->email, 'version' => 1, 'roles' => ['ADMIN'], 'active' => '0']);
        $this->put("/users/{$admin->id}", $data)->assertSessionHasErrors('roles');
        $data['active'] = '1';
        $data['roles'] = ['ENGINEER'];
        $this->put("/users/{$admin->id}", $data)->assertSessionHasErrors('roles');
        $this->assertTrue($admin->fresh()->active);
        $this->assertSame(['ADMIN'], $admin->fresh()->roles);
    }

    public function test_disabled_or_stale_sessions_are_rejected(): void
    {
        $user = $this->account();
        $this->signedIn($user);
        $user->active = false;
        $user->save();
        $this->get('/')->assertRedirect(route('login'));
        $this->assertGuest();
        $user->active = true;
        $user->auth_version++;
        $user->save();
        $this->signedIn($user)->withSession(['auth_version' => 1])->get('/users')->assertRedirect(route('login'));
        $this->assertGuest();
    }

    public function test_asset_list_filters_paginates_and_strips_unapproved_fields(): void
    {
        Http::fake(['mart.test/*' => Http::response($this->page([$this->asset(['sources' => ['secret' => 'RAW-VENDOR-SECRET']])], ['total' => 99, 'offset' => 25, 'has_more' => true]))]);
        $this->signedIn($this->account(['ENGINEER']))->get('/assets?unit=1&offset=25')->assertOk()->assertSee('Verified test asset')
            ->assertSee('Berikutnya')->assertSee('Sebelumnya')->assertDontSee('RAW-VENDOR-SECRET');
        Http::assertSent(fn ($r) => $r->method() === 'GET' && str_contains($r->url(), '/assets/inventory?') && $r['unit'] === '1' && $r['offset'] === 25 && $r['limit'] === 25 && $r['site_code'] === 'BSR' && $r['organization_code'] === 'IP');
        Http::assertSentCount(2);
    }

    public function test_asset_detail_is_read_only_and_escapes_source_text(): void
    {
        Http::fake(['mart.test/*' => Http::response($this->asset(['description' => '<script>alert(1)</script>']))]);
        $this->signedIn($this->account(['SUPERVISOR']))->get('/assets/asset:BSR:123')->assertOk()->assertSee('&lt;script&gt;', false)->assertDontSee('<script>alert(1)</script>', false);
        Http::assertSent(fn ($r) => $r->method() === 'GET' && str_contains($r->url(), 'asset%3ABSR%3A123'));
        $this->post('/assets', [])->assertStatus(405);
        $this->put('/assets/asset:BSR:123', [])->assertStatus(405);
    }

    public function test_asset_missing_configuration_offline_and_bad_responses_show_disconnected(): void
    {
        $this->signedIn($this->account());
        config(['services.reliability_mart.url' => null]);
        $this->get('/assets')->assertOk()->assertSee('Belum terhubung');
        Http::assertNothingSent();
        config(['services.reliability_mart.url' => 'http://mart.test']);
        foreach ([Http::response('private upstream error', 503), Http::response('not-json'), Http::response($this->page([$this->asset(['site_code' => 'OTHER'])])), Http::response(str_repeat('x', 1048577))] as $response) {
            Http::swap(new Factory);
            Http::preventStrayRequests();
            Http::fake(['mart.test/*' => $response]);
            $this->get('/assets')->assertOk()->assertSee('Belum terhubung')->assertDontSee('private upstream error');
        }
    }

    public function test_asset_empty_page_and_missing_detail_have_distinct_states(): void
    {
        $this->signedIn($this->account());
        Http::fake(['mart.test/*' => Http::response($this->page([]))]);
        $this->get('/assets')->assertOk()->assertSee('Tidak ada aset yang sesuai')->assertDontSee('Belum terhubung');
        Http::swap(new Factory);
        Http::preventStrayRequests();
        Http::fake(['mart.test/*' => Http::response([], 404)]);
        $this->get('/assets/missing')->assertNotFound();
    }

    public function test_asset_identity_mismatch_and_bad_pagination_are_rejected(): void
    {
        $this->signedIn($this->account());
        Http::fake(['mart.test/*' => Http::response($this->asset())]);
        $this->get('/assets/different-id')->assertOk()->assertSee('Belum terhubung');
        Http::swap(new Factory);
        Http::preventStrayRequests();
        Http::fake(['mart.test/*' => Http::response($this->page([$this->asset()], ['limit' => 999]))]);
        $this->get('/assets')->assertOk()->assertSee('Belum terhubung');
    }

    public function test_bad_asset_filters_never_reach_upstream_and_response_is_not_cached(): void
    {
        $this->signedIn($this->account());
        $this->get('/assets?offset=-1')->assertSessionHasErrors('offset');
        $this->get('/assets?sort=sql-injection')->assertSessionHasErrors('sort');
        Http::assertNothingSent();
        $this->get('/')->assertHeader('X-Frame-Options', 'DENY')->assertHeader('X-Content-Type-Options', 'nosniff');
        $this->assertStringContainsString('no-store', $this->get('/')->headers->get('Cache-Control'));
    }
}
