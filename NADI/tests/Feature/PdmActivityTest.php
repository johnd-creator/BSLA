<?php

namespace Tests\Feature;

use App\Models\PdmActivity;
use App\Models\User;
use App\Services\PdmFormCatalog;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Http\Client\Factory;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Str;
use Tests\TestCase;

class PdmActivityTest extends TestCase
{
    use RefreshDatabase;

    private const ASSET = 'asset:MAXIMO:MXASSET:BSR:IP:SYNTHETIC-PUMP-001';

    protected function setUp(): void
    {
        parent::setUp();
        Http::preventStrayRequests();
        config(['services.reliability_mart.url' => 'http://mart.test']);
        Http::fake(['mart.test/*' => fn () => Http::response(['canonical_id' => self::ASSET, 'source_asset_number' => 'SYNTHETIC-PUMP-001', 'site_code' => 'BSR', 'organization_code' => 'IP', 'hierarchy_category' => 'component', 'scope_basis' => 'DIRECT_SOURCE_UNIT', 'registered' => false, 'description' => 'SOURCE-DESCRIPTION-NOT-STORED'])]);
    }

    private function signIn(string $role = 'ENGINEER'): User
    {
        $user = User::factory()->create(['roles' => [$role], 'active' => true])->refresh();
        $this->actingAs($user)->withSession(['auth_version' => $user->auth_version]);

        return $user;
    }

    private function data(string $templateId = 'SYNTHETIC_MOTOR', array $changes = []): array
    {
        $catalog = app(PdmFormCatalog::class);
        $template = $catalog->find($templateId);

        return array_replace([
            'request_key' => (string) Str::uuid(), 'title' => 'Synthetic PdM activity', 'asset_ref' => self::ASSET,
            'template_id' => $templateId, 'template_fingerprint' => $catalog->fingerprint($template),
            'measured_local' => '2026-01-01T10:00', 'timezone' => 'Asia/Jakarta', 'instrument' => 'TEST meter',
            'measurement_mode' => 'RMS', 'operating_condition' => 'Test running 50 MW',
            'asset_selection_note' => 'Synthetic selection evidence, not a real field verification.', 'acknowledge_draft' => '1',
            'readings' => [$template['fields'][0]['key'] => ['value' => '0', 'unit' => $template['fields'][0]['unit'] ?? 'test-unit']],
        ], $changes);
    }

    public function test_pages_require_authentication(): void
    {
        foreach (['/pdm', '/pdm/create', '/pdm/templates', '/pdm/history?asset_ref=test'] as $path) {
            $this->get($path)->assertRedirect(route('login'));
        }
        Http::assertNothingSent();
    }

    public function test_catalog_keeps_all_sources_and_uncertainties_without_activating_limits(): void
    {
        $catalog = app(PdmFormCatalog::class);
        $templates = $catalog->all();
        $this->assertCount(5, $templates);
        $this->assertCount(1, array_filter($templates, fn ($t) => $t['preview_only']));
        $this->assertCount(5, array_unique(array_column($templates, 'id')));
        foreach ($templates as $template) {
            $keys = array_column($template['fields'], 'key');
            $this->assertSame(count($keys), count(array_unique($keys)));
            $this->assertArrayNotHasKey('threshold', $template);
            $this->assertSame(64, strlen($template['source']['sha256']));
        }
        $motor = $catalog->find('SYNTHETIC_MOTOR');
        $fan = $catalog->find('SYNTHETIC_FAN');
        $this->assertSame(['1V', '1H', '1A', '2V', '2H', '2A'], array_column($motor['fields'], 'label'));
        $this->assertSame(['3V', '3H', '3A', '4V', '4H', '4A'], array_column($fan['fields'], 'label'));
        $this->assertSame(['mm/s'], array_values(array_unique(array_column($motor['fields'], 'unit'))));
        $this->assertTrue($catalog->find('SYNTHETIC_REVIEW')['preview_only']);
        $this->signIn();
        $this->get('/pdm/templates?q=SYNTHETIC+PUMP&method=VIBRATION')->assertOk()->assertSee('Katalog form PdM')->assertSee('Kanal tambahan perlu review');
    }

    public function test_unregistered_inventory_component_can_be_selected_without_registry_change(): void
    {
        $this->signIn();
        $this->get(route('pdm.create', ['asset_ref' => self::ASSET]))->assertOk()->assertSee('Identitas tersedia di inventori')->assertSee('Vibrasi motor utama');
        $this->get(route('pdm.create', ['asset_ref' => self::ASSET, 'template_id' => 'SYNTHETIC_MOTOR']))->assertOk()->assertSee('Catat pengukuran PdM')->assertSee('1V')->assertSee('2A')->assertDontSee('name="readings[field_i3]', false);
        Http::assertSent(fn ($request) => $request->method() === 'GET' && str_contains($request->url(), '/assets/inventory/'));
    }

    public function test_draft_saves_zero_distinct_from_missing_and_retains_source_snapshot(): void
    {
        $owner = $this->signIn();
        $data = $this->data(changes: ['created_by' => 999, 'version' => 99]);
        $this->post('/pdm', $data)->assertRedirect();
        $activity = PdmActivity::firstOrFail();
        $this->assertSame($owner->id, $activity->created_by);
        $this->assertSame(1, $activity->version);
        $this->assertSame('0', $activity->readings['field_c3']['value']);
        $this->assertNull($activity->readings['field_d3']['value']);
        $this->assertSame('mm/s', $activity->readings['field_c3']['unit']);
        $this->assertSame('03:00', $activity->measured_at->format('H:i'));
        $this->assertStringNotContainsString('SOURCE-DESCRIPTION-NOT-STORED', $activity->toJson());
        $this->get('/pdm')->assertOk()->assertSee('Synthetic PdM activity');
        $this->get('/pdm/'.$activity->id)->assertOk()->assertSee('Belum diukur')->assertSee('synthetic-pdm-example.xlsx');
        $this->post('/pdm', $data)->assertRedirect(route('pdm.show', $activity));
        $this->assertDatabaseCount('pdm_activities', 1);
    }

    public function test_server_rejects_unknown_points_invalid_numeric_and_changed_source_unit(): void
    {
        $this->signIn();
        foreach ([['not_in_template' => ['value' => '1']], ['field_c3' => ['value' => 'NaN']], ['field_c3' => ['value' => '1e999']], ['field_c3' => ['value' => '1,2']], ['field_c3' => ['value' => '1', 'unit' => 'µm']]] as $readings) {
            $this->post('/pdm', $this->data(changes: ['readings' => $readings]))->assertSessionHasErrors();
        }
        $this->assertDatabaseCount('pdm_activities', 0);
    }

    public function test_unitless_source_needs_explicit_unit_and_review_only_template_is_blocked(): void
    {
        $this->signIn();
        $this->post('/pdm', $this->data('SYNTHETIC_UNKNOWN_UNIT', ['readings' => ['field_b2' => ['value' => '1']]]))->assertSessionHasErrors('readings.field_b2.unit');
        $this->post('/pdm', $this->data('SYNTHETIC_REVIEW'))->assertSessionHasErrors('template_id');
        $this->post('/pdm', $this->data('SYNTHETIC_UNKNOWN_UNIT'))->assertRedirect();
        $this->assertDatabaseCount('pdm_activities', 1);
    }

    public function test_required_context_acknowledgment_future_time_and_stale_template_are_rejected(): void
    {
        $this->signIn();
        foreach (['instrument', 'measurement_mode', 'operating_condition', 'asset_selection_note', 'acknowledge_draft', 'timezone'] as $field) {
            $this->post('/pdm', $this->data(changes: [$field => '']))->assertSessionHasErrors($field);
        }
        $this->post('/pdm', $this->data(changes: ['measured_local' => '2099-01-01T00:00']))->assertSessionHasErrors('measured_local');
        $this->post('/pdm', $this->data(changes: ['template_fingerprint' => str_repeat('0', 64)]))->assertSessionHasErrors('template_id');
        $this->post('/pdm', $this->data(changes: ['readings' => ['field_c3' => ['value' => '']]]))->assertSessionHasErrors('readings');
        $this->assertDatabaseCount('pdm_activities', 0);
    }

    public function test_permissions_owner_and_optimistic_version_are_enforced(): void
    {
        $owner = $this->signIn();
        $data = $this->data();
        $this->post('/pdm', $data)->assertRedirect();
        $activity = PdmActivity::firstOrFail();
        foreach (['ADMIN', 'SUPERVISOR', 'MANAGER', 'ENGINEER'] as $role) {
            $this->signIn($role);
            $this->get('/pdm')->assertOk();
            $this->get('/pdm/'.$activity->id.'/edit')->assertForbidden();
            $this->put('/pdm/'.$activity->id, [...$data, 'version' => 1])->assertForbidden();
            if ($role !== 'ENGINEER') {
                $this->get('/pdm/create')->assertForbidden();
                $this->post('/pdm', $this->data())->assertForbidden();
            }
        }
        $this->actingAs($owner)->withSession(['auth_version' => $owner->auth_version]);
        $this->get('/pdm/'.$activity->id.'/edit')->assertOk();
        $this->put('/pdm/'.$activity->id, [...$data, 'version' => 1, 'title' => 'Updated draft'])->assertRedirect();
        $this->assertSame(2, $activity->fresh()->version);
        $this->put('/pdm/'.$activity->id, [...$data, 'version' => 1, 'title' => 'Stale overwrite'])->assertSessionHasErrors('version');
        $this->assertSame('Updated draft', $activity->fresh()->title);
        $this->put('/pdm/'.$activity->id, [...$data, 'version' => 2, 'asset_ref' => 'asset:other'])->assertSessionHasErrors('asset_ref');
    }

    public function test_exact_asset_template_and_point_version_keep_history_separate(): void
    {
        $this->signIn();
        $this->post('/pdm', $this->data())->assertRedirect();
        $first = PdmActivity::firstOrFail();
        $this->post('/pdm', $this->data('SYNTHETIC_COPY', ['title' => 'COPY-WORKBOOK-RECORD']))->assertRedirect();
        $this->get(route('pdm.history', ['asset_ref' => self::ASSET, 'template_id' => $first->template_id, 'point' => 'field_c3', 'fingerprint' => $first->template_fingerprint]))
            ->assertOk()->assertSee($first->reference())->assertDontSee(PdmActivity::latest('id')->first()->reference());
        $this->get(route('pdm.history', ['asset_ref' => 'asset:other']))->assertOk()->assertDontSee($first->reference());
        $this->get(route('pdm.history', ['asset_ref' => self::ASSET, 'point' => 'field_c3']))->assertSessionHasErrors('fingerprint');
    }

    public function test_missing_asset_or_unavailable_mart_blocks_save_without_losing_user_input(): void
    {
        $this->signIn();
        Http::swap(new Factory);
        Http::preventStrayRequests();
        Http::fake(['mart.test/*' => fn () => Http::response([], 503)]);
        $data = $this->data();
        $this->from(route('pdm.create', ['asset_ref' => self::ASSET, 'template_id' => 'SYNTHETIC_MOTOR']))
            ->post('/pdm', $data)->assertSessionHasErrors('asset_ref')->assertSessionHasInput('title', $data['title']);
        $this->assertDatabaseCount('pdm_activities', 0);
        $this->get(route('pdm.create', ['asset_ref' => self::ASSET]))->assertOk()->assertSee('Aset belum dapat dibaca dari Mart');
    }

    public function test_mart_failure_keeps_the_measurement_form_and_all_input_available_for_retry(): void
    {
        $this->signIn();
        Http::swap(new Factory);
        Http::preventStrayRequests();
        Http::fake(['mart.test/*' => Http::sequence()
            ->push([], 503)
            ->push([], 503)
            ->push(['canonical_id' => self::ASSET, 'source_asset_number' => 'SYNTHETIC-PUMP-001', 'site_code' => 'BSR', 'organization_code' => 'IP', 'hierarchy_category' => 'component', 'scope_basis' => 'DIRECT_SOURCE_UNIT', 'registered' => false])]);
        $data = $this->data(changes: ['readings' => ['field_c3' => ['value' => '2.5']]]);
        $url = route('pdm.create', ['asset_ref' => self::ASSET, 'template_id' => 'SYNTHETIC_MOTOR']);

        $this->from($url)->post('/pdm', $data)->assertRedirect($url)->assertSessionHasErrors('asset_ref');
        $this->get($url)->assertOk()
            ->assertSee('Catat pengukuran PdM')
            ->assertSee('name="readings[field_c3][value]"', false)
            ->assertSee('value="2.5"', false)
            ->assertSee('value="'.$data['request_key'].'"', false)
            ->assertSee('value="'.$data['title'].'"', false)
            ->assertSee('Identitas aset belum dapat diverifikasi');
        $this->assertDatabaseCount('pdm_activities', 0);

        $this->post('/pdm', $data)->assertRedirect();
        $this->assertDatabaseCount('pdm_activities', 1);
        $this->assertSame('2.5', PdmActivity::firstOrFail()->readings['field_c3']['value']);
    }

    public function test_all_input_catalog_templates_render_their_source_fields_without_guessing_units(): void
    {
        $this->signIn();
        foreach (app(PdmFormCatalog::class)->all() as $template) {
            $response = $this->get(route('pdm.create', ['asset_ref' => self::ASSET, 'template_id' => $template['id']]));
            $response->assertOk();
            if ($template['preview_only']) {
                $response->assertDontSee('name="readings[', false);

                continue;
            }
            foreach ($template['fields'] as $field) {
                $response->assertSee('name="readings['.$field['key'].'][value]"', false);
                if (! $field['unit'] && $field['type'] === 'number') {
                    $response->assertSee('name="readings['.$field['key'].'][unit]"', false);
                }
            }
        }
        $this->assertDatabaseCount('pdm_activities', 0);
        Http::assertNotSent(fn ($request) => $request->method() !== 'GET');
    }

    public function test_post_rejects_asset_identity_mismatch_even_when_response_is_successful(): void
    {
        $this->signIn();
        $this->post('/pdm', $this->data(changes: ['asset_ref' => 'asset:wrong-id']))->assertSessionHasErrors('asset_ref');
        $this->assertDatabaseCount('pdm_activities', 0);
    }

    public function test_text_is_escaped_and_no_production_write_is_sent(): void
    {
        $this->signIn();
        $this->post('/pdm', $this->data(changes: ['title' => '<script>unsafe</script>']))->assertRedirect();
        $activity = PdmActivity::firstOrFail();
        $this->get('/pdm/'.$activity->id)->assertOk()->assertSee('&lt;script&gt;', false)->assertDontSee('<script>unsafe</script>', false);
        Http::assertNotSent(fn ($request) => $request->method() !== 'GET');
    }
}
