<?php

namespace Tests\Feature;

use App\Models\User;
use App\Services\HistorianDemand;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Http\Client\Factory;
use Illuminate\Support\Facades\Http;
use Tests\TestCase;

class HistorianDemandTest extends TestCase
{
    use RefreshDatabase;

    private function snapshot(): array
    {
        $now = gmdate('Y-m-d\TH:i:s\Z');

        return ['subscription' => str_repeat('a', 48), 'page' => 'demo-temperature', 'source_mode' => 'simulation', 'generated_at' => $now,
            'sample_seconds' => 4, 'lease_seconds' => 20, 'grace_seconds' => 10, 'context_enabled' => false, 'status' => 'current',
            'tags' => [['tag' => 'DEMO.TEMP', 'label' => 'Suhu demonstrasi', 'unit' => '°C', 'value' => 0, 'source_at' => $now, 'received_at' => $now,
                'quality' => 'good', 'source_quality' => 'good', 'freshness' => 'fresh', 'age_seconds' => 0, 'private' => 'NEVER_EXPOSE']], 'private' => 'NEVER_EXPOSE'];
    }

    private function login(): static
    {
        $user = User::factory()->create(['roles' => ['MANAGER']])->refresh();

        return $this->actingAs($user)->withSession(['auth_version' => $user->auth_version]);
    }

    private function configured(): void
    {
        config(['historian.url' => 'http://127.0.0.1:8015']);
        Http::preventStrayRequests();
    }

    public function test_guest_and_disabled_state_do_not_contact_any_source(): void
    {
        Http::preventStrayRequests();
        config(['historian.url' => null]);
        $this->get('/operations/historian')->assertRedirect('/login');
        $this->postJson('/operations/historian/subscribe', [])->assertUnauthorized();
        $this->login()->get('/operations/historian')->assertOk()->assertSee('Gateway simulasi belum diaktifkan')->assertSee('SIMULASI · BUKAN DATA DCS');
        $this->postJson('/operations/historian/subscribe', ['page' => 'demo-temperature', 'client' => 'tab1'])->assertStatus(503);
        Http::assertNothingSent();
    }

    public function test_session_owner_is_server_derived_and_allowlisted_data_excludes_private_fields(): void
    {
        $this->configured();
        Http::fake(['127.0.0.1:8015/*' => Http::response($this->snapshot())]);
        $this->login()->postJson('/operations/historian/subscribe', ['page' => 'demo-temperature', 'client' => 'tab1', 'owner' => 'client-injected', 'url' => 'http://evil.test'])
            ->assertOk()->assertJsonPath('tags.0.value', 0)->assertDontSee('NEVER_EXPOSE')->assertHeader('Cache-Control', 'no-store, private');
        Http::assertSent(fn ($r) => $r->method() === 'POST' && $r->url() === 'http://127.0.0.1:8015/v1/historian/subscribe' && preg_match('/^[a-f0-9]{64}$/D', $r['owner']) && ! isset($r['url']));
    }

    public function test_page_tag_and_history_range_validation_rejects_unmapped_inputs(): void
    {
        $this->configured();
        $this->login();
        $this->postJson('/operations/historian/subscribe', ['page' => 'real-unit', 'client' => 'tab'])->assertUnprocessable();
        $this->postJson('/operations/historian/subscribe', ['page' => 'demo-temperature', 'client' => '../bad'])->assertUnprocessable();
        $base = ['subscription' => str_repeat('a', 48), 'tag' => 'DEMO.TEMP', 'start' => gmdate('Y-m-d\TH:i:s\Z', time() - 3601), 'end' => gmdate('Y-m-d\TH:i:s\Z'), 'limit' => 120];
        $this->postJson('/operations/historian/history', $base)->assertUnprocessable();
        $this->postJson('/operations/historian/history', array_replace($base, ['tag' => 'guessed-tag']))->assertUnprocessable();
        $this->postJson('/operations/historian/history', array_replace($base, ['limit' => 1001]))->assertUnprocessable();
        $this->get('/operations/historian/subscribe')->assertStatus(405);
        Http::assertNothingSent();
    }

    public function test_remote_credentials_paths_and_redirects_are_rejected(): void
    {
        Http::preventStrayRequests();
        foreach (['http://pi.test:8015', 'http://user:pass@127.0.0.1:8015', 'http://127.0.0.1:8015/evil', 'https://127.0.0.1:8015', 'http://127.0.0.1:8015?url=x'] as $url) {
            config(['historian.url' => $url]);
            $this->assertNull(app(HistorianDemand::class)->call('subscribe', []));
        }
        Http::assertNothingSent();
        $this->configured();
        Http::fake(['*' => Http::response([], 302, ['Location' => 'http://evil.test'])]);
        $this->assertNull(app(HistorianDemand::class)->call('subscribe', []));
    }

    public function test_stale_bad_unknown_partial_malformed_and_oversized_fail_closed(): void
    {
        $this->configured();
        $base = $this->snapshot();
        $stale = $base;
        $stale['tags'][0]['source_at'] = gmdate('Y-m-d\TH:i:s\Z', time() - 30);
        $stale['tags'][0]['age_seconds'] = 30;
        $bad = $base;
        $bad['tags'][0]['quality'] = 'bad';
        $future = $base;
        $future['tags'][0]['source_at'] = gmdate('Y-m-d\TH:i:s\Z', time() + 60);
        $invented = $base;
        $invented['tags'][0]['tag'] = 'REAL.TAG';
        $missing = $base;
        unset($missing['tags'][0]['value']);
        foreach ([$stale, $bad, $future, $invented, $missing, array_replace($base, ['source_mode' => 'dcs']), array_replace($base, ['tags' => []]), str_repeat('x', 1048577)] as $payload) {
            Http::swap(new Factory);
            Http::fake(['*' => Http::response($payload)]);
            $this->assertNull(app(HistorianDemand::class)->call('subscribe', ['page' => 'demo-temperature']));
        }
    }

    public function test_cold_no_data_and_stale_null_values_are_explicit_not_zero(): void
    {
        $this->configured();
        $cold = $this->snapshot();
        $cold['status'] = 'no_data';
        $cold['tags'][0] = array_replace($cold['tags'][0], ['value' => null, 'source_at' => null, 'received_at' => null, 'age_seconds' => null, 'quality' => 'no_data', 'source_quality' => 'no_data', 'freshness' => 'no_data']);
        Http::fake(['*' => Http::response($cold)]);
        $result = app(HistorianDemand::class)->call('subscribe', ['page' => 'demo-temperature']);
        $this->assertNotNull($result);
        $this->assertNull($result['tags'][0]['value']);
        $this->assertNull($result['tags'][0]['source_at']);
        $this->assertSame('no_data', $result['status']);
    }

    public function test_history_is_explicit_bounded_and_strips_private_fields(): void
    {
        $this->configured();
        $start = gmdate('Y-m-d\TH:i:s\Z', time() - 900);
        $end = gmdate('Y-m-d\TH:i:s\Z');
        Http::fake(['*' => Http::response(['source_mode' => 'simulation', 'tag' => 'DEMO.TEMP', 'start' => $start, 'end' => $end,
            'limit' => 120, 'coverage' => 'not_asserted', 'generated_at' => $end, 'points' => [['source_at' => $start, 'value' => 0, 'quality' => 'good', 'private' => 'NEVER_EXPOSE']]])]);
        $this->login()->postJson('/operations/historian/history', ['subscription' => str_repeat('a', 48), 'tag' => 'DEMO.TEMP', 'start' => $start, 'end' => $end, 'limit' => 120])
            ->assertOk()->assertJsonPath('points.0.value', 0)->assertDontSee('NEVER_EXPOSE');
    }

    public function test_heartbeat_must_match_requested_lease_and_release_is_idempotent_at_client(): void
    {
        $this->configured();
        Http::fake(['*' => Http::response($this->snapshot())]);
        $this->assertNull(app(HistorianDemand::class)->call('heartbeat', ['subscription' => str_repeat('b', 48)]));
        Http::swap(new Factory);
        Http::fake(['*' => Http::response(['released' => true, 'private' => 'NEVER_EXPOSE'])]);
        $this->assertSame(['released' => true], app(HistorianDemand::class)->call('release', ['subscription' => str_repeat('a', 48)]));
    }

    public function test_configured_page_only_starts_browser_lease_and_retains_operations_navigation(): void
    {
        $this->configured();
        $this->login()->get('/operations/historian?page=demo-temperature')->assertOk()->assertSee('data-historian', false)->assertSee('Konteks operasi')->assertSee('CEMS')->assertSee('Hanya 1 tag');
        Http::assertNothingSent();
    }
}
