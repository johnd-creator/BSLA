<?php

namespace Tests\Feature;

use App\Models\User;
use App\Services\CemsAssetMapping;
use App\Services\CemsLive;
use App\Services\ReliabilityMart;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Http\Client\Factory;
use Illuminate\Support\Facades\Http;
use Tests\TestCase;

class CemsLiveTest extends TestCase
{
    use RefreshDatabase;

    private function snapshot(): array
    {
        return ['stack_id' => '1', 'source_mode' => 'simulation', 'poll_interval_seconds' => 5, 'retention_seconds' => 21600, 'status' => 'live',
            'generated_at' => gmdate('Y-m-d\TH:i:s\Z'), 'cache_started_at' => gmdate('Y-m-d\TH:i:s\Z', time() - 60), 'last_cycle_at' => null, 'samples_retained' => 1,
            'parameters' => [['parameter_code' => 'SO2', 'name' => 'Sulfur dioxide', 'unit' => 'mg/Nm3', 'value_raw' => null, 'value_final' => 0,
                'observed_at' => gmdate('Y-m-d\TH:i:s\Z'), 'last_good_at' => gmdate('Y-m-d\TH:i:s\Z'), 'quality' => 'good', 'age_seconds' => 0, 'secret' => 'PRIVATE_FIXTURE_SECRET']], 'secret' => 'PRIVATE_FIXTURE_SECRET'];
    }

    public function test_authentication_and_unconfigured_state_never_call_source(): void
    {
        Http::preventStrayRequests();
        config(['services.cems_live.url' => null]);
        $this->get('/operations/cems')->assertRedirect('/login');
        $this->get('/operations/cems/refresh')->assertRedirect('/login');
        $user = User::factory()->create(['roles' => ['MANAGER']])->refresh();
        $this->actingAs($user)->withSession(['auth_version' => $user->auth_version])->get('/operations/cems')->assertOk()->assertSee('CEMS belum tersedia')->assertSee('Konteks operasi');
        Http::assertNothingSent();
    }

    public function test_shared_cache_allowlist_zero_and_simulation_label(): void
    {
        Http::preventStrayRequests();
        config(['services.cems_live.url' => 'http://cems.test']);
        Http::fake(['cems.test/v1/cems/snapshot' => Http::response($this->snapshot()), 'cems.test/v1/cems/history*' => Http::response(['parameter_code' => 'SO2', 'retention_seconds' => 21600, 'points' => [['observed_at' => gmdate('Y-m-d\TH:i:s\Z'), 'value_final' => null, 'quality' => 'read_error', 'secret' => 'PRIVATE_FIXTURE_SECRET']], 'truncated' => false])]);
        $result = app(CemsLive::class)->read('http://evil.test');
        $this->assertSame('SO2', $result['parameter']);
        $this->assertSame(0, $result['snapshot']['parameters'][0]['value_final']);
        $this->assertArrayNotHasKey('secret', $result['snapshot']);
        $this->assertArrayNotHasKey('secret', $result['snapshot']['parameters'][0]);
        $this->assertArrayNotHasKey('secret', $result['history']['points'][0]);
        Http::swap(new Factory);
        Http::fake(['cems.test/v1/cems/snapshot' => Http::response($this->snapshot()), '*' => Http::response([], 503)]);
        $user = User::factory()->create(['roles' => ['SUPERVISOR']])->refresh();
        $this->actingAs($user)->withSession(['auth_version' => $user->auth_version])->get('/operations/cems')->assertOk()->assertSee('SIMULASI · BUKAN DATA PLC')->assertSee('Sulfur dioxide')->assertSee('KKS belum dipetakan')->assertSee('Skema CEMS 2D')->assertDontSee('PRIVATE_FIXTURE_SECRET')->assertHeader('Cache-Control', 'no-store, private');
        Http::assertSent(fn ($r) => $r->method() === 'GET' && str_contains($r->url(), 'parameter=SO2'));
    }

    public function test_invalid_redirect_oversized_and_legacy_payloads_fail_closed(): void
    {
        config(['services.cems_live.url' => 'http://cems.test']);
        $missing = $this->snapshot();
        unset($missing['parameters'][0]['value_final']);
        foreach ([Http::response([], 302, ['Location' => 'http://other.test']), Http::response(str_repeat('x', 1048577)), Http::response(['items' => []]), Http::response($missing), Http::response(array_replace($this->snapshot(), ['source_mode' => 'unknown']))] as $response) {
            Http::swap(new Factory);
            Http::fake(['*' => $response]);
            $this->assertNull(app(CemsLive::class)->read()['snapshot']);
        }
    }

    public function test_read_only_routes_reject_writes(): void
    {
        $user = User::factory()->create();
        $this->actingAs($user)->withSession(['auth_version' => $user->auth_version])->post('/operations/cems')->assertStatus(405);
    }

    public function test_asset_links_require_verified_evidence_and_exact_inventory_identity(): void
    {
        $mart = \Mockery::mock(ReliabilityMart::class);
        $mapping = app(CemsAssetMapping::class);
        config(['cems.asset_mappings' => ['SO2' => ['verified' => false, 'canonical_id' => 'asset:fixture', 'kks' => 'FIXTURE', 'evidence' => 'fixture only']]]);
        $this->assertSame([], $mapping->resolve([['parameter_code' => 'SO2']], $mart));
        config(['cems.asset_mappings.SO2.verified' => true]);
        $mart->shouldReceive('inventoryDetail')->with('asset:fixture')->once()->andReturn(['canonical_id' => 'asset:fixture', 'source_asset_number' => 'OTHER']);
        $this->assertSame([], $mapping->resolve([['parameter_code' => 'SO2']], $mart));
        $verified = \Mockery::mock(ReliabilityMart::class);
        $verified->shouldReceive('inventoryDetail')->with('asset:fixture')->once()->andReturn(['canonical_id' => 'asset:fixture', 'source_asset_number' => 'FIXTURE']);
        $this->assertSame(['SO2' => ['canonical_id' => 'asset:fixture', 'kks' => 'FIXTURE']], $mapping->resolve([['parameter_code' => 'SO2']], $verified));
    }

    public function test_stale_snapshot_and_non_good_numeric_values_fail_closed(): void
    {
        config(['services.cems_live.url' => 'http://cems.test']);
        $stale = $this->snapshot();
        $stale['generated_at'] = gmdate('Y-m-d\TH:i:s\Z', time() - 30);
        $bad = $this->snapshot();
        $bad['parameters'][0]['quality'] = 'read_error';
        $aged = $this->snapshot();
        $aged['parameters'][0]['age_seconds'] = 15;
        foreach ([$stale, $bad, $aged] as $payload) {
            Http::swap(new Factory);
            Http::fake(['*' => Http::response($payload)]);
            $this->assertNull(app(CemsLive::class)->read()['snapshot']);
        }
        $this->assertSame('0.0001', CemsLive::formatValue(0.0001));
        $this->assertSame('0', CemsLive::formatValue(0));
        $this->assertSame('—', CemsLive::formatValue(null));
    }

    public function test_minute_feed_is_strict_signal_only_dto(): void
    {
        config(['services.cems_live.url' => 'http://cems.test']);
        Http::fake(['*' => Http::response(['source_mode' => 'simulation', 'feed_interval_seconds' => 60, 'window_seconds' => 60, 'meaning' => 'signal_data_only', 'generated_at' => null, 'feed_age_seconds' => null, 'status' => 'warming_up', 'signals' => [['parameter_code' => 'SO2', 'last_received_at' => null, 'good_samples_last_minute' => 0, 'expected_samples_per_minute' => 12, 'signal_state' => 'no_recent_good_data', 'equipment_running' => true]]])]);
        $data = app(CemsLive::class)->signals([['parameter_code' => 'SO2']], 'simulation');
        $this->assertSame('warming_up', $data['status']);
        $this->assertArrayNotHasKey('equipment_running', $data['signals'][0]);
    }

    public function test_minute_feed_accepts_boundary_sample_and_rejects_frozen_current_feed(): void
    {
        config(['services.cems_live.url' => 'http://cems.test']);
        $payload = ['source_mode' => 'simulation', 'feed_interval_seconds' => 60, 'window_seconds' => 60, 'meaning' => 'signal_data_only', 'generated_at' => gmdate('Y-m-d\TH:i:s\Z'), 'feed_age_seconds' => 0, 'status' => 'current', 'signals' => [['parameter_code' => 'SO2', 'last_received_at' => null, 'good_samples_last_minute' => 13, 'expected_samples_per_minute' => 12, 'signal_state' => 'receiving']]];
        Http::fake(['*' => Http::response($payload)]);
        $this->assertSame(13, app(CemsLive::class)->signals([['parameter_code' => 'SO2']], 'simulation')['signals'][0]['good_samples_last_minute']);
        $excess = $payload;
        $excess['signals'][0]['good_samples_last_minute'] = 14;
        $frozen = $payload;
        $frozen['generated_at'] = gmdate('Y-m-d\TH:i:s\Z', time() - 75);
        $inconsistent = $payload;
        $inconsistent['feed_age_seconds'] = 30;
        foreach ([$excess, $frozen, $inconsistent] as $invalid) {
            Http::swap(new Factory);
            Http::fake(['*' => Http::response($invalid)]);
            $this->assertNull(app(CemsLive::class)->signals([['parameter_code' => 'SO2']], 'simulation'));
        }
    }

    public function test_one_stack_has_one_card_per_parameter_with_its_own_minute_feed(): void
    {
        Http::preventStrayRequests();
        config(['services.cems_live.url' => 'http://cems.test']);
        $snapshot = $this->snapshot();
        $codes = ['SO2', 'NOx', 'O2', 'PM', 'Hg', 'CO2', 'Laju_alir', 'NO', 'NO2', 'CO', 'Flow', 'Opacity', 'Temp', 'Humidity', 'Pressure'];
        $snapshot['parameters'] = array_map(fn ($code) => array_replace($snapshot['parameters'][0], ['parameter_code' => $code, 'name' => $code]), $codes);
        $signals = ['source_mode' => 'simulation', 'feed_interval_seconds' => 60, 'window_seconds' => 60, 'meaning' => 'signal_data_only', 'generated_at' => gmdate('Y-m-d\TH:i:s\Z'), 'feed_age_seconds' => 0, 'status' => 'current', 'signals' => [
            ['parameter_code' => 'O2', 'last_received_at' => null, 'good_samples_last_minute' => 12, 'expected_samples_per_minute' => 12, 'signal_state' => 'receiving'],
            ['parameter_code' => 'SO2', 'last_received_at' => null, 'good_samples_last_minute' => 0, 'expected_samples_per_minute' => 12, 'signal_state' => 'no_recent_good_data'],
        ]];
        Http::fake(['cems.test/v1/cems/snapshot' => fn () => Http::response($snapshot), 'cems.test/v1/cems/signals' => fn () => Http::response($signals), '*' => fn () => Http::response([], 503)]);
        $user = User::factory()->create(['roles' => ['MANAGER']])->refresh();
        foreach (['/operations/cems', '/operations/cems/refresh'] as $url) {
            $response = $this->actingAs($user)->withSession(['auth_version' => $user->auth_version])->get($url)->assertOk()
                ->assertSee('1 cerobong · 15 parameter')->assertSee('Satu set pengukuran')->assertDontSee('cems-signal-list');
            $previous = libxml_use_internal_errors(true);
            $document = new \DOMDocument;
            $document->loadHTML('<?xml encoding="UTF-8">'.$response->getContent());
            libxml_clear_errors();
            libxml_use_internal_errors($previous);
            $xpath = new \DOMXPath($document);
            $this->assertSame(1, $xpath->query('//*[@data-cems-stack="1"]')->length);
            $this->assertSame(15, $xpath->query('//article[@data-cems-parameter]')->length);
            $this->assertSame(1, $xpath->query('//*[@data-cems-stack]//svg')->length);
            foreach ($codes as $code) {
                $this->assertSame(1, $xpath->query('//article[@data-cems-parameter="'.$code.'"]')->length);
                $this->assertSame(1, $xpath->query('//article[@data-cems-parameter="'.$code.'"]//*[@data-cems-feed="'.$code.'"]')->length);
            }
            $this->assertStringContainsString('0 / 12', $xpath->query('//*[@data-cems-feed="SO2"]')->item(0)->textContent);
            $this->assertStringContainsString('12 / 12', $xpath->query('//*[@data-cems-feed="O2"]')->item(0)->textContent);
            $this->assertStringContainsString('Belum tersedia untuk parameter ini.', $xpath->query('//*[@data-cems-feed="NOx"]')->item(0)->textContent);
        }
    }

    public function test_good_samples_require_real_fresh_consistent_observation_timestamps(): void
    {
        config(['services.cems_live.url' => 'http://cems.test']);
        foreach ([null, '', 'invalid', '2026-02-30T12:00:00Z', '2026-11-08T25:00:00Z', gmdate('Y-m-d\TH:i:s\Z', time() - 15), gmdate('Y-m-d\TH:i:s\Z', time() - 30), gmdate('Y-m-d\TH:i:s\Z', time() + 1)] as $observed) {
            $payload = $this->snapshot();
            $payload['parameters'][0]['observed_at'] = $observed;
            Http::swap(new Factory);
            Http::fake(['*' => Http::response($payload)]);
            $this->assertNull(app(CemsLive::class)->read()['snapshot'], 'Invalid observation accepted: '.($observed ?? 'null'));
        }
        foreach (['future_snapshot', 'lying_age', 'missing_age', 'missing_value', 'future_last_good'] as $case) {
            $payload = $this->snapshot();
            if ($case === 'future_snapshot') {
                $payload['generated_at'] = gmdate('Y-m-d\TH:i:s\Z', time() + 1);
            } elseif ($case === 'lying_age') {
                $payload['parameters'][0]['observed_at'] = gmdate('Y-m-d\TH:i:s\Z', time() - 10);
            } elseif ($case === 'missing_age') {
                $payload['parameters'][0]['age_seconds'] = null;
            } elseif ($case === 'missing_value') {
                $payload['parameters'][0]['value_final'] = null;
            } else {
                $payload['parameters'][0]['last_good_at'] = gmdate('Y-m-d\TH:i:s\Z', time() + 1);
            }
            Http::swap(new Factory);
            Http::fake(['*' => Http::response($payload)]);
            $this->assertNull(app(CemsLive::class)->read()['snapshot'], $case);
        }
    }

    public function test_fresh_fractional_offset_timestamps_and_empty_offline_samples_are_valid(): void
    {
        config(['services.cems_live.url' => 'http://cems.test']);
        $payload = $this->snapshot();
        $stamp = (new \DateTimeImmutable('-3 seconds'))->setTimezone(new \DateTimeZone('Asia/Jakarta'))->format('Y-m-d\TH:i:s.uP');
        $payload['parameters'][0]['observed_at'] = $stamp;
        $payload['parameters'][0]['last_good_at'] = $stamp;
        $payload['parameters'][0]['age_seconds'] = 3;
        Http::fake(['cems.test/v1/cems/snapshot' => Http::response($payload), '*' => Http::response([], 503)]);
        $snapshot = app(CemsLive::class)->read()['snapshot'];
        $this->assertNotNull($snapshot);
        $this->assertGreaterThanOrEqual(3, $snapshot['parameters'][0]['age_seconds']);
        $payload['parameters'][0] = array_replace($payload['parameters'][0], ['quality' => 'offline', 'value_final' => null, 'observed_at' => null, 'last_good_at' => null, 'age_seconds' => null]);
        Http::swap(new Factory);
        Http::fake(['cems.test/v1/cems/snapshot' => Http::response($payload), '*' => Http::response([], 503)]);
        $this->assertNotNull(app(CemsLive::class)->read()['snapshot']);
    }

    public function test_mercury_formats_plain_decimals_without_changing_numeric_values(): void
    {
        foreach ([
            [8.05e-5, '0,0000805'], [8e-5, '0,00008'], [0.00016, '0,00016'],
            [8.05e-12, '0,00000000000805'], [-8.05e-5, '-0,0000805'],
            [1.23456789123, '1,23456789123'], [1e8, '100000000'],
            [0.0, '0'], [-0.0, '0'], [null, '—'],
        ] as [$value, $expected]) {
            $original = $value;
            $formatted = CemsLive::formatValue($value, 'Hg');
            $this->assertSame($expected, $formatted);
            $this->assertSame($original, $value);
            if ($value !== null) {
                $this->assertEquals($value, (float) str_replace(',', '.', $formatted));
            }
        }
        foreach ([PHP_FLOAT_MIN, PHP_FLOAT_MAX, 5e-324] as $value) {
            $formatted = CemsLive::formatValue($value, 'Hg');
            $this->assertStringNotContainsString('e', $formatted);
            $this->assertNotSame('0', $formatted);
            $this->assertSame($value, (float) str_replace(',', '.', $formatted));
        }
        $this->assertSame('—', CemsLive::formatValue(INF, 'Hg'));
        $this->assertSame('—', CemsLive::formatValue(NAN, 'Hg'));
        $this->assertSame('8.05e-5', CemsLive::formatValue(8.05e-5, 'SO2'));
    }

    public function test_mercury_card_and_history_both_render_plain_decimal_and_keep_dto_value(): void
    {
        Http::preventStrayRequests();
        config(['services.cems_live.url' => 'http://cems.test']);
        $payload = $this->snapshot();
        $payload['parameters'][0] = array_replace($payload['parameters'][0], ['parameter_code' => 'Hg', 'name' => 'Mercury', 'value_raw' => 8.05e-5, 'value_final' => 8.05e-5]);
        Http::fake([
            'cems.test/v1/cems/snapshot' => fn () => Http::response($payload),
            'cems.test/v1/cems/history*' => fn () => Http::response(['parameter_code' => 'Hg', 'retention_seconds' => 21600, 'truncated' => false, 'points' => [['observed_at' => gmdate('Y-m-d\TH:i:s\Z'), 'value_final' => 8.05e-12, 'quality' => 'good']]]),
            '*' => fn () => Http::response([], 503),
        ]);
        $data = app(CemsLive::class)->read('Hg');
        $this->assertSame(8.05e-5, $data['snapshot']['parameters'][0]['value_final']);
        $this->assertSame(8.05e-12, $data['history']['points'][0]['value_final']);
        $user = User::factory()->create(['roles' => ['MANAGER']])->refresh();
        foreach (['/operations/cems?parameter=Hg', '/operations/cems/refresh?parameter=Hg'] as $url) {
            $this->actingAs($user)->withSession(['auth_version' => $user->auth_version])->get($url)->assertOk()
                ->assertSee('0,0000805')->assertSee('0,00000000000805')->assertSee('mg/Nm3')
                ->assertDontSee('8.05e-5')->assertDontSee('8.05e-12');
        }
    }
}
