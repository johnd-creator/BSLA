<?php

namespace Tests\Feature;

use App\Auth\DirectoryAuthenticator;
use App\Auth\DirectoryIdentity;
use App\Enums\Role;
use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Hash;
use Illuminate\Testing\TestResponse;
use Mockery\MockInterface;
use Tests\TestCase;

class DirectoryLoginTest extends TestCase
{
    use RefreshDatabase;

    private const LOGIN = 'https://localhost/login/directory';

    private const GROUP = 'synthetic-group';

    private function enable(): void
    {
        config(['session.secure' => true, 'directory.enabled' => true, 'directory.realm' => 'synthetic-realm', 'directory.required_group' => self::GROUP]);
    }

    private function attempt(): TestResponse
    {
        return $this->from(self::LOGIN)->post(self::LOGIN, ['login' => 'one-account', 'password' => 'synthetic-passphrase']);
    }

    private function fake(?DirectoryIdentity $identity, int $times = 1): void
    {
        $this->mock(DirectoryAuthenticator::class, function (MockInterface $mock) use ($identity, $times) {
            $mock->shouldReceive('authenticate')->times($times)->with('one-account', 'synthetic-passphrase', self::GROUP)->andReturn($identity);
        });
    }

    public function test_disabled_or_insecure_never_invokes_directory(): void
    {
        $this->mock(DirectoryAuthenticator::class)->shouldNotReceive('authenticate');
        $this->attempt()->assertNotFound();
        $this->enable();
        $this->post('http://localhost/login/directory', ['login' => 'one-account', 'password' => 'fake'])->assertNotFound();
        $this->assertDatabaseCount('users', 0);
    }

    public function test_default_provider_missing_group_and_wrong_group_never_provision_and_do_not_flash_password(): void
    {
        $this->enable();
        $this->attempt()->assertSessionHasErrors('login');
        $this->assertNull(session()->getOldInput('password'));
        $this->fake(new DirectoryIdentity('object-one', 'unallowed'), 1);
        $this->attempt()->assertSessionHasErrors('login');
        config(['directory.required_group' => '']);
        $this->attempt()->assertSessionHasErrors('login');
        $this->assertGuest();
        $this->assertDatabaseCount('users', 0);
    }

    public function test_single_exact_login_provisions_only_viewer_then_enforces_route_and_logout_allowlist(): void
    {
        $this->enable();
        $this->fake(new DirectoryIdentity('object-one', self::GROUP), 2);
        $local = User::factory()->create(['username' => 'one-account', 'roles' => [Role::Admin->value]]);
        $this->attempt()->assertRedirect('https://localhost/viewer');
        $this->assertAuthenticated();
        $viewer = User::query()->whereNotNull('directory_subject')->sole();
        $this->assertNotSame($local->id, $viewer->id);
        $this->assertSame([Role::Viewer->value], $viewer->roles);
        $this->assertNull($viewer->username);
        $this->assertStringEndsWith('@directory.invalid', $viewer->email);
        $this->assertFalse(Hash::check('synthetic-passphrase', $viewer->password));
        $this->get('https://localhost/viewer')->assertOk()->assertSee('belum memiliki akses data operasional');
        foreach (['/', '/assets', '/work-orders', '/operations', '/operations/historian', '/operations/cems', '/reports/summary.csv', '/users', '/reliability/evidence.json', '/reliability/snapshots/987654', '/disruptions/987654'] as $path) {
            $this->get('https://localhost'.$path)->assertForbidden();
        }
        $this->post('https://localhost/operations/historian/subscribe')->assertForbidden();
        $this->post('https://localhost/logout')->assertRedirect('https://localhost/login');
        $this->assertGuest();
        $this->attempt()->assertRedirect('https://localhost/viewer');
        $this->assertDatabaseCount('users', 2);
    }

    public function test_local_password_cannot_authenticate_directory_identity_and_local_login_is_preserved(): void
    {
        $this->enable();
        $directory = User::factory()->create(['directory_subject' => str_repeat('1', 64), 'roles' => [Role::Viewer->value]]);
        $local = User::factory()->create(['roles' => [Role::Manager->value]]);
        $this->post('/login', ['login' => $directory->email, 'password' => 'password'])->assertSessionHasErrors('login');
        $this->assertGuest();
        $this->post('/login', ['login' => $local->email, 'password' => 'password'])->assertRedirect('/');
        $this->assertAuthenticatedAs($local);
        $this->get('/viewer')->assertForbidden();
    }

    public function test_unauthorized_identity_collision_does_not_link_or_elevate(): void
    {
        $this->enable();
        $id = hash('sha256', 'synthetic-realm:object-one');
        $local = User::factory()->create(['email' => 'viewer-'.$id.'@directory.invalid', 'roles' => [Role::Admin->value]]);
        $this->fake(new DirectoryIdentity('object-one', self::GROUP), 2);
        $this->attempt()->assertSessionHasErrors('login');
        $this->assertGuest();
        $this->assertNull($local->fresh()->directory_subject);
        $local->forceFill(['directory_subject' => $id])->save();
        $this->attempt()->assertSessionHasErrors('login');
        $this->assertGuest();
        $this->assertSame([Role::Admin->value], $local->fresh()->roles);
        $this->assertDatabaseCount('users', 1);
    }

    public function test_flag_off_preserves_local_login_before_directory_migration(): void
    {
        $migration = require database_path('migrations/2026_11_21_000001_add_directory_subject_to_users.php');
        $migration->down();
        try {
            $local = User::factory()->create(['roles' => [Role::Manager->value]]);
            $this->post('/login', ['login' => $local->email, 'password' => 'password'])->assertRedirect('/');
            $this->assertAuthenticatedAs($local);
            $this->get('/viewer')->assertForbidden();
        } finally {
            $migration->up();
        }
    }

    public function test_admin_cannot_edit_or_elevate_a_directory_account(): void
    {
        $admin = User::factory()->create(['roles' => [Role::Admin->value]])->refresh();
        $viewer = User::factory()->create(['directory_subject' => str_repeat('1', 64), 'roles' => [Role::Viewer->value]])->refresh();
        $this->actingAs($admin)->withSession(['auth_version' => $admin->auth_version]);
        $this->get('/users/'.$viewer->id.'/edit')->assertForbidden();
        $this->put('/users/'.$viewer->id, [
            'name' => 'Changed', 'username' => 'viewer_test', 'email' => 'viewer@example.invalid',
            'password' => 'synthetic-only-long-passphrase', 'password_confirmation' => 'synthetic-only-long-passphrase',
            'roles' => [Role::Admin->value], 'active' => true, 'version' => $viewer->auth_version,
        ])->assertForbidden();
        $this->assertSame([Role::Viewer->value], $viewer->fresh()->roles);
        $this->assertSame($viewer->password, $viewer->fresh()->password);
    }

    public function test_absolute_session_deadline_and_switch_off_both_revoke_session(): void
    {
        $this->enable();
        $this->fake(new DirectoryIdentity('object-one', self::GROUP), 2);
        $this->attempt();
        $this->travel(14)->minutes();
        $this->get('https://localhost/viewer')->assertOk();
        $this->travel(1)->minutes();
        $this->get('https://localhost/viewer')->assertRedirect('https://localhost/login');
        $this->assertGuest();
        $this->attempt()->assertRedirect('https://localhost/viewer');
        config(['directory.enabled' => false]);
        $this->get('https://localhost/viewer')->assertRedirect('https://localhost/login');
        $this->assertGuest();
    }
}
