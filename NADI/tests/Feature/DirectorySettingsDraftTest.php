<?php

namespace Tests\Feature;

use App\Auth\DirectoryAuthenticator;
use App\Enums\Role;
use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\File;
use Illuminate\Support\Facades\URL;
use Tests\TestCase;

class DirectorySettingsDraftTest extends TestCase
{
    use RefreshDatabase;

    private const URL = 'https://127.0.0.1/settings/ldap';

    private string $tempStorage;

    protected function setUp(): void
    {
        parent::setUp();
        $this->tempStorage = sys_get_temp_dir().'/directory-settings-test-'.bin2hex(random_bytes(8));
        mkdir($this->tempStorage.'/app', 0700, true);
        $this->app->useStoragePath($this->tempStorage);
        $this->mock(DirectoryAuthenticator::class)->shouldNotReceive('authenticate');
    }

    protected function tearDown(): void
    {
        if (isset($this->tempStorage)) {
            File::deleteDirectory($this->tempStorage);
        }
        parent::tearDown();
    }

    private function user(Role $role): User
    {
        $user = User::factory()->create(['roles' => [$role->value]])->refresh();
        $this->actingAs($user)->withSession(['auth_version' => $user->auth_version]);

        return $user;
    }

    private function path(): string
    {
        return $this->tempStorage.'/app/nadi-drafts/directory-settings.json';
    }

    public function test_admin_can_save_bounded_private_draft_but_runtime_is_untouched(): void
    {
        $this->user(Role::Admin);
        $this->get(self::URL)->assertOk()->assertHeader('Cache-Control', 'no-store, private')->assertSee('Draft saja')->assertSee('636')->assertDontSee('name="bind_password"', false);
        $this->assertFileDoesNotExist($this->path());
        $this->post(self::URL, ['host' => 'dc01.example.internal', 'base_dn' => 'DC=example,DC=internal',
            'group_dn' => 'CN=Viewer,OU=Groups,DC=example,DC=internal', 'bind_name' => 'svc-nadi@example.internal', 'current_password' => 'password'])
            ->assertRedirect(route('settings.directory'));
        $data = json_decode(file_get_contents($this->path()), true, flags: JSON_THROW_ON_ERROR);
        $this->assertSame(['host', 'base_dn', 'group_dn', 'bind_name'], array_keys($data));
        $this->assertSame(0600, fileperms($this->path()) & 0777);
        $this->assertSame(0700, fileperms(dirname($this->path())) & 0777);
        $this->get(self::URL)->assertOk()->assertSee('svc-nadi@example.internal');
        $this->assertFalse(config('directory.enabled'));
        $this->assertNull(config('directory.host'));
        $this->assertNull(config('directory.bind_password'));
        $this->get('http://127.0.0.1/storage/nadi-drafts/directory-settings.json')->assertForbidden();
        $this->get(URL::signedRoute('storage.local', ['path' => 'nadi-drafts/directory-settings.json'], absolute: false))->assertNotFound();
    }

    public function test_other_local_roles_and_directory_viewer_cannot_access_settings(): void
    {
        $this->get(self::URL)->assertRedirect(route('login'));
        foreach ([Role::Engineer, Role::Supervisor, Role::Manager] as $role) {
            $this->user($role);
            $this->get(self::URL)->assertForbidden();
            $this->post(self::URL, [])->assertForbidden();
        }
        $viewer = User::factory()->create(['roles' => [Role::Viewer->value], 'directory_subject' => str_repeat('3', 64)])->refresh();
        config(['directory.enabled' => true, 'directory.realm' => 'tests', 'directory.required_group' => 'Viewer', 'session.secure' => true]);
        $this->actingAs($viewer)->withSession(['auth_version' => $viewer->auth_version, 'directory_until' => now()->addMinutes(5)->timestamp,
            'directory_realm' => 'tests', 'directory_group_hash' => hash('sha256', 'Viewer')]);
        $this->get('https://127.0.0.1/settings/ldap')->assertForbidden();
        $this->post('https://127.0.0.1/settings/ldap', [])->assertForbidden();
        $this->assertFileDoesNotExist($this->path());
    }

    public function test_wrong_password_invalid_endpoint_and_unexpected_secret_never_persist_or_flash(): void
    {
        $this->user(Role::Admin);
        $this->post(self::URL, ['host' => 'dc01.example.internal', 'current_password' => 'not-my-local-pass'])->assertSessionHasErrors('current_password');
        $this->assertNull(session()->getOldInput('current_password'));
        $this->assertNull(session()->getOldInput('host'));
        foreach (['ldaps://dc.example.internal:636', '192.0.2.100', ['bad-array']] as $host) {
            $this->post(self::URL, ['host' => $host, 'current_password' => 'password'])->assertSessionHasErrors('host');
        }
        $this->post(self::URL, ['host' => 'dc01.example.internal', 'current_password' => 'password', 'bind_password' => 'do-not-save-test-marker'])
            ->assertUnprocessable()->assertDontSee('do-not-save-test-marker');
        $this->assertNull(session()->getOldInput('bind_password'));
        $this->post(self::URL, ['bind_name' => 'unstructured-secret-test-marker', 'current_password' => 'password'])->assertSessionHasErrors('bind_name');
        $this->assertNull(session()->getOldInput('bind_name'));
        $this->post(self::URL.'?host=dc01.example.internal', ['current_password' => 'password'])->assertUnprocessable();
        $this->assertFileDoesNotExist($this->path());
    }

    public function test_remote_http_is_rejected(): void
    {
        $this->user(Role::Admin);
        $this->get('http://127.0.0.1/settings/ldap')->assertForbidden(); // Non-local environment
        $this->app->instance('env', 'local');
        $this->get('http://127.0.0.1/settings/ldap')->assertOk();
        $this->withServerVariables(['REMOTE_ADDR' => '192.0.2.90']);
        $this->get('http://nadi.example.internal/settings/ldap')->assertForbidden();
        $this->withSession(['_token' => 'synthetic-form-token']);
        $this->post('http://nadi.example.internal/settings/ldap', ['_token' => 'synthetic-form-token', 'host' => 'dc01.example.internal', 'current_password' => 'password'])->assertForbidden();
        $this->assertFileDoesNotExist($this->path());
    }
}
