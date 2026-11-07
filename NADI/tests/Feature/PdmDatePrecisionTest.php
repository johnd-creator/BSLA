<?php

namespace Tests\Feature;

use App\Models\InspectionDraft;
use App\Models\PdmActivity;
use App\Models\User;
use App\Services\AssetTimeline;
use App\Services\PdmFormCatalog;
use Carbon\CarbonImmutable;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Http\Client\Factory;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Str;
use Tests\TestCase;

class PdmDatePrecisionTest extends TestCase
{
    use RefreshDatabase;

    private const ASSET = 'asset:MAXIMO:MXASSET:BSR:IP:SYNTHETIC-PUMP-001';

    private User $owner;

    protected function setUp(): void
    {
        parent::setUp();
        $this->travelTo(CarbonImmutable::parse('2026-11-07T12:00:00Z'));
        config(['services.reliability_mart.url' => 'http://mart.test']);
        Http::preventStrayRequests();
        Http::fake([
            'mart.test/v1/reliability/assets/*/context' => fn () => Http::response(['asset' => $this->asset(), 'maintenance' => [], 'fmea' => [], 'health' => [], 'overhauls' => []]),
            'mart.test/v1/reliability/assets/inventory/*' => fn () => Http::response($this->asset()),
        ]);
        $this->owner = User::factory()->create(['roles' => ['ENGINEER'], 'active' => true])->refresh();
        $this->actingAs($this->owner)->withSession(['auth_version' => $this->owner->auth_version]);
    }

    private function asset(): array
    {
        return ['canonical_id' => self::ASSET, 'site_code' => 'BSR', 'organization_code' => 'IP', 'hierarchy_category' => 'component', 'scope_basis' => 'DIRECT_SOURCE_UNIT', 'registered' => true];
    }

    private function input(array $changes = []): array
    {
        $catalog = app(PdmFormCatalog::class);
        $template = $catalog->find('SYNTHETIC_MOTOR');

        return array_replace([
            'request_key' => (string) Str::uuid(), 'title' => 'EXCEL-DATE-ONLY', 'asset_ref' => self::ASSET,
            'template_id' => $template['id'], 'template_fingerprint' => $catalog->fingerprint($template),
            'time_precision' => 'date', 'measured_on' => '2026-07-15',
            'instrument' => 'Synthetic meter; fictional offline fixture',
            'measurement_mode' => 'Tidak dicatat pada sumber', 'operating_condition' => 'Synthetic operating context',
            'asset_selection_note' => 'QA only: candidate motor identity, not engineering approval.', 'acknowledge_draft' => '1',
            'readings' => ['field_c3' => ['value' => '2.4'], 'field_d3' => ['value' => '0.25'], 'field_e3' => ['value' => '4.5'], 'field_f3' => ['value' => '2.75'], 'field_g3' => ['value' => '0.5'], 'field_h3' => ['value' => '1.25']],
            'inspection_type' => 'routine',
        ], $changes);
    }

    private function saveActivity(array $changes = []): PdmActivity
    {
        $this->post('/pdm', $this->input($changes))->assertSessionHasNoErrors();

        return PdmActivity::latest('id')->firstOrFail();
    }

    public function test_date_only_stores_literal_date_and_null_instant_and_zone_and_preserves_synthetic_values(): void
    {
        $input = $this->input(['measured_local' => '2099-01-01T12:00:00', 'timezone' => 'Invalid/Zone']);
        $this->post('/pdm', $input)->assertSessionHasNoErrors();
        $activity = PdmActivity::firstOrFail();
        $this->assertSame('date', $activity->time_precision);
        $this->assertSame('2026-07-15', $activity->getRawOriginal('measured_on'));
        $this->assertSame('2026-07-15', $activity->toArray()['measured_on']);
        $this->assertNull($activity->measured_at);
        $this->assertNull($activity->timezone);
        foreach ($input['readings'] as $key => $reading) {
            $this->assertSame($reading['value'], $activity->readings[$key]['value']);
            $this->assertSame('mm/s', $activity->readings[$key]['unit']);
        }
        foreach (['/pdm', route('pdm.show', $activity), route('pdm.history', ['asset_ref' => self::ASSET])] as $url) {
            $this->get($url)->assertOk()->assertSee('15 Jul 2026')->assertSee('Tanggal saja')->assertDontSee('15 Jul 2026 00:00')->assertDontSee('15 Jul 2026 UTC');
            // Audit save timestamps have their own UTC clock; the measurement stays date-only.
            if ($url !== route('pdm.show', $activity)) {
                $this->get($url)->assertDontSee('UTC');
            }
        }
        $this->get(route('pdm.edit', $activity))->assertOk()->assertSee('value="2026-07-15"', false);
        $this->post('/pdm', $input)->assertRedirect(route('pdm.show', $activity));
        $this->assertDatabaseCount('pdm_activities', 1);
        Http::assertNotSent(fn ($request) => $request->method() !== 'GET');
    }

    public function test_date_precision_validation_rejects_missing_invalid_and_future_dates(): void
    {
        foreach (['', '2026-02-30', '2026-07-15T00:00:00', '2026-11-08'] as $date) {
            $this->post('/pdm', $this->input(['measured_on' => $date]))->assertSessionHasErrors('measured_on');
        }
        $this->post('/pdm', $this->input(['time_precision' => 'estimated']))->assertSessionHasErrors('time_precision');
        $this->assertDatabaseCount('pdm_activities', 0);
    }

    public function test_precise_time_retains_seconds_zone_and_local_date_across_utc_midnight(): void
    {
        $activity = $this->saveActivity(['time_precision' => 'datetime', 'measured_local' => '2026-07-15T00:15:37', 'timezone' => 'Asia/Jakarta', 'measured_on' => '1999-01-01']);
        $this->assertSame('datetime', $activity->time_precision);
        $this->assertSame('2026-07-14 17:15:37', $activity->measured_at->format('Y-m-d H:i:s'));
        $this->assertSame('2026-07-15', $activity->getRawOriginal('measured_on'));
        $this->assertSame('Asia/Jakarta', $activity->timezone);
        $this->get(route('pdm.show', $activity))->assertOk()->assertSee('15 Jul 2026 00:15:37')->assertSee('Asia/Jakarta');
        $this->get(route('pdm.edit', $activity))->assertOk()->assertSee('2026-07-15T00:15:37');
        $this->get(route('inspections.create', ['pdm_activity_id' => $activity->id]))->assertOk()->assertSee('value="2026-07-15"', false);
    }

    public function test_legacy_minute_precision_post_still_works_but_datetime_requires_zone_and_valid_time(): void
    {
        $legacy = $this->input(['measured_local' => '2026-07-15T10:15', 'timezone' => 'Asia/Jayapura']);
        unset($legacy['time_precision']);
        $this->post('/pdm', $legacy)->assertSessionHasNoErrors();
        $this->assertSame('2026-07-15 01:15:00', PdmActivity::first()->measured_at->format('Y-m-d H:i:s'));
        foreach ([['timezone' => ''], ['timezone' => 'Mars/Test'], ['measured_local' => ''], ['measured_local' => '2026-02-30T10:00'], ['measured_local' => '2099-01-01T10:00']] as $invalid) {
            $this->post('/pdm', $this->input([...['time_precision' => 'datetime', 'measured_local' => '2026-07-15T10:15', 'timezone' => 'Asia/Jakarta'], ...$invalid]))->assertSessionHasErrors();
        }
        $this->assertDatabaseCount('pdm_activities', 1);
    }

    public function test_precision_can_change_before_analysis_and_stale_edits_remain_blocked(): void
    {
        $activity = $this->saveActivity();
        $timed = $this->input(['version' => 1, 'time_precision' => 'datetime', 'measured_local' => '2026-07-15T10:00:23', 'timezone' => 'Asia/Jakarta']);
        $this->put(route('pdm.update', $activity), $timed)->assertSessionHasNoErrors();
        $this->assertSame('datetime', $activity->fresh()->time_precision);
        $this->put(route('pdm.update', $activity), $this->input(['version' => 1]))->assertSessionHasErrors('version');
        $this->put(route('pdm.update', $activity), $this->input(['version' => 2]))->assertSessionHasNoErrors();
        $this->assertNull($activity->fresh()->measured_at);
        $this->assertNull($activity->fresh()->timezone);
        $this->assertSame('2026-07-15', $activity->fresh()->getRawOriginal('measured_on'));
    }

    public function test_linked_analysis_uses_date_only_and_locks_precision_date_and_time(): void
    {
        $activity = $this->saveActivity();
        $this->post('/inspections', ['request_key' => (string) Str::uuid(), 'pdm_activity_id' => $activity->id, 'finding' => 'Source-derived result', 'recommendation' => 'QA review only'])->assertSessionHasNoErrors();
        $analysis = InspectionDraft::firstOrFail();
        $this->assertSame('2026-07-15', $analysis->inspected_on->format('Y-m-d'));
        $this->assertSame(self::ASSET, $analysis->asset_ref);
        $this->assertSame('routine', $analysis->inspection_type);
        $this->get('/pdm')->assertOk()->assertViewHas('activities', fn ($page) => $page->total() === 1);
        $this->get('/action-board')->assertOk()->assertSee('QA review only');
        $this->put(route('pdm.update', $activity), $this->input(['version' => 1, 'measured_on' => '2026-07-16']))->assertSessionHasErrors('measured_on');
        $this->put(route('pdm.update', $activity), $this->input(['version' => 1, 'time_precision' => 'datetime', 'measured_local' => '2026-07-15T00:00:00', 'timezone' => 'UTC']))->assertSessionHasErrors('measured_local');
        $this->put(route('pdm.update', $activity), $this->input(['version' => 1, 'title' => 'Updated description']))->assertSessionHasNoErrors();
        $this->assertNull($activity->fresh()->measured_at);
    }

    public function test_history_and_logbook_mix_date_and_datetime_without_midnight_assumptions(): void
    {
        $this->saveActivity(['title' => 'OLDER-TIMED', 'time_precision' => 'datetime', 'measured_local' => '2026-07-14T23:59:59', 'timezone' => 'UTC']);
        $this->saveActivity(['title' => 'TODAY-DATE-ONLY']);
        $this->saveActivity(['title' => 'TODAY-EARLY', 'time_precision' => 'datetime', 'measured_local' => '2026-07-15T00:15:37', 'timezone' => 'Asia/Jakarta']);
        $this->saveActivity(['title' => 'TODAY-LATER', 'time_precision' => 'datetime', 'measured_local' => '2026-07-15T11:00:00', 'timezone' => 'Asia/Jakarta']);
        $this->saveActivity(['title' => 'NEWEST-DATE-ONLY', 'measured_on' => '2026-07-16']);
        foreach (['/pdm', route('pdm.history', ['asset_ref' => self::ASSET])] as $url) {
            $this->get($url)->assertOk()->assertSeeInOrder(['NEWEST-DATE-ONLY', 'TODAY-LATER', 'TODAY-EARLY', 'TODAY-DATE-ONLY', 'OLDER-TIMED'])
                ->assertSee('bukan urutan kejadian')->assertSee('tidak berarti pengukuran setiap hari');
        }
    }

    public function test_timeline_date_only_has_no_instant_and_dates_are_not_timezone_shifted(): void
    {
        $this->saveActivity(['title' => 'DATE-ONLY-TIMELINE']);
        $this->saveActivity(['title' => 'PRECISE-TIMELINE', 'time_precision' => 'datetime', 'measured_local' => '2026-07-15T00:15:37', 'timezone' => 'Asia/Jakarta']);
        $preview = app(AssetTimeline::class)->forAsset($this->asset());
        $dated = collect($preview['events'])->firstWhere('title', 'DATE-ONLY-TIMELINE');
        $this->assertNull($dated['at']);
        $this->assertSame('2026-07-15', $dated['date_only']);
        $this->get(route('assets.timeline', self::ASSET))->assertOk()->assertSeeInOrder(['PRECISE-TIMELINE', 'DATE-ONLY-TIMELINE'])
            ->assertSee('datetime="2026-07-15"', false)->assertSee('jam/zona tidak dicatat')->assertDontSee('15 Jul 2026 00:00:00');
    }

    public function test_date_only_mart_failure_preserves_form_precision_date_and_values(): void
    {
        Http::swap(new Factory);
        Http::preventStrayRequests();
        Http::fake(['mart.test/*' => fn () => Http::response([], 503)]);
        $url = route('pdm.create', ['asset_ref' => self::ASSET, 'template_id' => 'SYNTHETIC_MOTOR']);
        $data = $this->input();
        $this->from($url)->post('/pdm', $data)->assertSessionHasErrors('asset_ref')->assertSessionHasInput('measured_on', '2026-07-15');
        $this->get($url)->assertOk()->assertSee('value="2026-07-15"', false)->assertSee('value="0.25"', false)->assertSee('value="'.$data['request_key'].'"', false);
        $this->assertDatabaseCount('pdm_activities', 0);
    }

    public function test_date_only_rollback_refuses_to_lose_records_or_fabricate_time(): void
    {
        $this->saveActivity();
        $migration = require database_path('migrations/2026_11_07_000002_support_pdm_date_precision.php');
        try {
            $migration->down();
            $this->fail('Rollback must refuse date-only data');
        } catch (\RuntimeException $e) {
            $this->assertStringContainsString('preservation plan', $e->getMessage());
        }
        $this->assertDatabaseCount('pdm_activities', 1);
        $this->assertNull(PdmActivity::first()->measured_at);
        $this->assertSame('date', DB::table('pdm_activities')->value('time_precision'));
    }
}
