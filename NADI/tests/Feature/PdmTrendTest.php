<?php

namespace Tests\Feature;

use App\Models\PdmActivity;
use App\Models\User;
use App\Services\PdmFormCatalog;
use App\Services\PdmTrend;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Str;
use Tests\TestCase;

class PdmTrendTest extends TestCase
{
    use RefreshDatabase;

    private const ASSET = 'asset:MAXIMO:MXASSET:BSR:IP:SYNTHETIC-PUMP-001';

    private User $owner;

    protected function setUp(): void
    {
        parent::setUp();
        Http::preventStrayRequests();
        Http::fake();
        $this->owner = User::factory()->create(['roles' => ['ENGINEER'], 'active' => true])->refresh();
        $this->actingAs($this->owner)->withSession(['auth_version' => $this->owner->auth_version]);
    }

    private function activity(array $changes = [], string $templateId = 'SYNTHETIC_MOTOR'): PdmActivity
    {
        $catalog = app(PdmFormCatalog::class);
        $template = $catalog->snapshot($catalog->find($templateId));
        $readings = [];
        foreach ($template['fields'] as $field) {
            $readings[$field['key']] = ['value' => null, 'unit' => $field['unit']];
        }
        $readings[$template['fields'][0]['key']]['value'] = '2.4';

        return PdmActivity::create(array_replace([
            'created_by' => $this->owner->id, 'request_key' => (string) Str::uuid(), 'title' => 'QA only, not field approval',
            'asset_ref' => self::ASSET, 'template_id' => $templateId, 'template_fingerprint' => $catalog->fingerprint($template),
            'method' => $template['method'], 'template_snapshot' => $template, 'readings' => $readings,
            'time_precision' => 'date', 'measured_on' => '2026-07-15', 'measurement_mode' => 'RMS QA only',
            'instrument' => 'QA meter', 'operating_condition' => 'Synthetic operating context',
            'asset_selection_note' => 'QA only. OLD/NEW mapping remains unverified.',
        ], $changes));
    }

    private function trend(PdmActivity $anchor, string $point = 'field_c3'): array
    {
        return app(PdmTrend::class)->forPoint($anchor, $point);
    }

    public function test_one_synthetic_date_is_not_a_meaningful_trend_and_remains_date_only(): void
    {
        // Deliberately fictional measurements, not source workbook values.
        $motor = $this->activity();
        $fan = $this->activity(['asset_ref' => str_replace('PUMP-001', 'FAN-002', self::ASSET), 'readings' => ['field_i3' => ['value' => '3.6', 'unit' => 'mm/s']]], 'SYNTHETIC_FAN');
        $this->assertSame(['2026-07-15'], $this->trend($motor)['dates']);
        $this->assertSame([2.4], array_column($this->trend($motor)['chart'], 'value'));
        $this->assertSame([3.6], array_column($this->trend($fan, 'field_i3')['chart'], 'value'));
        $this->get(route('pdm.trends', ['activity' => $motor->id, 'point' => 'field_c3']))->assertOk()
            ->assertSee('Data belum cukup untuk tren bermakna')->assertSee('jam/zona tidak dicatat')
            ->assertSee('OLD/NEW')->assertSee('Pemetaan &amp; hasil belum disahkan', false)->assertSee('Tidak ada garis interpolasi')
            ->assertDontSee('2026-07-15 00:00')->assertDontSee($fan->reference());
        $this->assertDatabaseHas('pdm_activities', ['id' => $motor->id, 'measured_on' => '2026-07-15', 'measured_at' => null, 'timezone' => null]);
        Http::assertNothingSent();
    }

    public function test_exact_identity_method_template_version_and_context_never_mix(): void
    {
        $anchor = $this->activity();
        foreach ([
            ['asset_ref' => str_replace('PUMP-001', 'PUMP-OTHER', self::ASSET)],
            ['template_id' => 'duplicate-workbook'], ['template_fingerprint' => str_repeat('a', 64)],
            ['method' => 'MCSA'], ['measurement_mode' => 'Peak'], ['instrument' => 'Other meter'],
            ['operating_condition' => 'Stopped'], ['asset_selection_note' => 'Other location, still unverified'],
        ] as $change) {
            $this->activity($change);
        }
        $this->activity([], 'SYNTHETIC_FAN'); // Even manually selecting the same asset cannot merge motor and fan.
        $trend = $this->trend($anchor);
        $this->assertCount(1, $trend['rows']);
        $this->assertSame($anchor->id, $trend['rows'][0]['activity']->id);
        $this->assertSame('1V', $trend['field']['label']);
        Http::assertNothingSent();
    }

    public function test_units_and_changed_field_semantics_are_excluded_even_with_reused_fingerprint(): void
    {
        $anchor = $this->activity();
        $this->activity(['readings' => ['field_c3' => ['value' => '1300', 'unit' => 'µm']]]);
        foreach (['label', 'group', 'source_cell', 'type'] as $key) {
            $snapshot = $anchor->template_snapshot;
            $snapshot['fields'][0][$key] = 'Changed';
            $this->activity(['template_snapshot' => $snapshot]);
        }
        $snapshot = $anchor->template_snapshot;
        $snapshot['source']['sha256'] = str_repeat('b', 64);
        $this->activity(['template_snapshot' => $snapshot]);
        $trend = $this->trend($anchor);
        $this->assertSame(6, $trend['excluded']);
        $this->assertSame(1, $trend['count']);
        $this->assertSame('mm/s', $trend['unit']);
    }

    public function test_missing_zero_invalid_and_negative_values_are_not_imputed(): void
    {
        $anchor = $this->activity(['readings' => ['field_c3' => ['value' => '0', 'unit' => 'mm/s']]]);
        foreach ([null, '', 'NaN', '1e999', 'text', '-2.5'] as $value) {
            $this->activity(['readings' => ['field_c3' => ['value' => $value, 'unit' => 'mm/s']]]);
        }
        $trend = $this->trend($anchor);
        $this->assertSame(2, $trend['count']);
        $this->assertSame(5, $trend['missing']);
        $this->assertSame(-2.5, $trend['minimum']);
        $this->assertSame(0.0, $trend['maximum']);
        $this->assertCount(7, $trend['rows']);
        $this->assertCount(1, $trend['dates']);
        $this->assertSame([360.0, 360.0], array_column($trend['chart'], 'x'));
    }

    public function test_calendar_spacing_keeps_gaps_and_same_day_precision_without_sequence_claims(): void
    {
        $anchor = $this->activity(['measured_on' => '2026-07-01']);
        $this->activity(['measured_on' => '2026-07-02']);
        $this->activity(['time_precision' => 'datetime', 'measured_at' => '2026-07-10 17:15:37', 'timezone' => 'Asia/Jakarta']);
        $this->activity(['measured_on' => '2026-07-11']);
        $trend = $this->trend($anchor);
        $this->assertSame(['2026-07-01', '2026-07-02', '2026-07-11'], $trend['dates']);
        $this->assertSame(9, $trend['max_gap']);
        $this->assertSame([54.0, 115.2, 666.0, 666.0], array_column($trend['chart'], 'x'));
        $this->get(route('pdm.trends', ['activity' => $anchor->id]))->assertOk()->assertSee('bukan keterlambatan jadwal')
            ->assertSee('00:15:37')->assertSee('Banyaknya titik saja tidak membuktikan tren bermakna')->assertSee('bukan urutan intrahari');
    }

    public function test_extreme_finite_values_do_not_generate_invalid_svg_coordinates(): void
    {
        $anchor = $this->activity(['readings' => ['field_c3' => ['value' => '-1e308', 'unit' => 'mm/s']]]);
        $this->activity(['readings' => ['field_c3' => ['value' => '1e308', 'unit' => 'mm/s']]]);
        $this->assertSame([200.0, 40.0], array_column($this->trend($anchor)['chart'], 'y'));
    }

    public function test_review_only_or_incomplete_context_keeps_evidence_without_plot(): void
    {
        $anchor = $this->activity(['instrument' => '']);
        $this->assertTrue($this->trend($anchor)['incomplete']);
        $this->assertSame([], $this->trend($anchor)['chart']);
        $this->assertCount(1, $this->trend($anchor)['rows']);
        $extra = $this->activity(['readings' => ['field_b2' => ['value' => '2', 'unit' => 'mm/s']]], 'SYNTHETIC_REVIEW');
        $this->assertSame([], $this->trend($extra, 'field_b2')['chart']);
    }

    public function test_unknown_point_and_mismatched_asset_are_rejected_not_silently_substituted(): void
    {
        $anchor = $this->activity();
        $this->get(route('pdm.trends', ['activity' => $anchor->id, 'point' => 'field_i3']))->assertUnprocessable();
        $this->get(route('pdm.trends', ['activity' => $anchor->id, 'asset_ref' => 'other']))->assertUnprocessable();
        $this->get(route('pdm.trends', ['activity' => 99999]))->assertNotFound();
        $this->get(route('pdm.trends', ['activity' => -1]))->assertRedirect();
    }

    public function test_bounded_history_is_visible_and_no_result_is_claimed_complete(): void
    {
        $anchor = $this->activity();
        $raw = $anchor->getAttributes();
        unset($raw['id']);
        $rows = [];
        for ($i = 0; $i < 250; $i++) {
            $rows[] = array_replace($raw, ['request_key' => (string) Str::uuid()]);
        }
        DB::table('pdm_activities')->insert($rows);
        $trend = $this->trend($anchor);
        $this->assertTrue($trend['truncated']);
        $this->assertCount(250, $trend['rows']);
        $this->get(route('pdm.trends', ['activity' => $anchor->id]))->assertOk()->assertSee('Bukan seluruh histori.');
    }

    public function test_asset_chooser_empty_states_links_and_context_switch_are_read_only(): void
    {
        $this->get(route('pdm.trends'))->assertOk()->assertSee('Belum ada pengukuran lokal');
        $anchor = $this->activity();
        $this->activity(['instrument' => 'Other QA meter'], 'SYNTHETIC_FAN');
        $this->get(route('pdm.trends'))->assertOk()->assertSee(self::ASSET);
        $this->get(route('pdm.trends', ['q' => 'absent']))->assertOk()->assertDontSee(self::ASSET);
        $this->get(route('pdm.trends', ['asset_ref' => 'missing']))->assertOk()->assertSee('Belum ada pengukuran lokal untuk identitas aset ini');
        $this->get(route('pdm.trends', ['activity' => $anchor->id]))->assertOk()->assertSee('Other QA meter')->assertSee('Tampilkan titik');
        $this->get(route('pdm.show', $anchor))->assertOk()->assertSee('Tren titik');
        $this->get(route('pdm.history', ['asset_ref' => self::ASSET]))->assertOk()->assertSee('Tren per titik');
        Http::assertNothingSent();
        $this->assertDatabaseCount('pdm_activities', 2);
    }

    public function test_all_existing_reader_roles_can_read_but_guests_and_disabled_sessions_cannot(): void
    {
        $anchor = $this->activity();
        foreach (['ADMIN', 'ENGINEER', 'SUPERVISOR', 'MANAGER'] as $role) {
            $user = User::factory()->create(['roles' => [$role], 'active' => true])->refresh();
            $this->actingAs($user)->withSession(['auth_version' => $user->auth_version])
                ->get(route('pdm.trends', ['activity' => $anchor->id]))->assertOk();
        }
        auth()->logout();
        $this->get(route('pdm.trends'))->assertRedirect(route('login'));
        $disabled = User::factory()->create(['roles' => ['ENGINEER'], 'active' => false])->refresh();
        $this->actingAs($disabled)->withSession(['auth_version' => $disabled->auth_version])->get(route('pdm.trends'))->assertRedirect(route('login'));
    }

    public function test_stored_labels_notes_and_numeric_values_are_escaped(): void
    {
        $anchor = $this->activity(['instrument' => '<script>alert(1)</script>', 'asset_selection_note' => '<img src=x onerror=alert(1)>', 'readings' => ['field_c3' => ['value' => '<svg onload=alert(1)>', 'unit' => 'mm/s']]]);
        $this->get(route('pdm.trends', ['activity' => $anchor->id]))->assertOk()->assertSee('&lt;script&gt;', false)
            ->assertDontSee('<script>alert(1)', false)->assertDontSee('<img src=x', false)->assertDontSee('<svg onload=', false);
        $this->assertSame(0, $this->trend($anchor)['count']);
    }
}
