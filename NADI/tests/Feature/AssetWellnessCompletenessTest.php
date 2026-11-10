<?php

namespace Tests\Feature;

use App\Models\ActionEffectivenessReview;
use App\Models\InspectionDraft;
use App\Models\PdmActivity;
use App\Models\PdmInspectionPlan;
use App\Models\User;
use App\Models\WorkspaceActivity;
use App\Services\ActionEffectiveness;
use App\Services\AssetWellnessCompleteness;
use Carbon\CarbonImmutable;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Schema;
use Illuminate\Support\Str;
use Tests\TestCase;

class AssetWellnessCompletenessTest extends TestCase
{
    use RefreshDatabase;

    private const ASSET = 'asset:MAXIMO:MXASSET:BSR:IP:WELLNESS-MATRIX-FIXTURE';

    private User $owner;

    protected function setUp(): void
    {
        parent::setUp();
        $this->travelTo(CarbonImmutable::parse('2026-11-10 10:00:00', 'Asia/Jakarta'));
        Http::preventStrayRequests();
        Http::fake(['*' => Http::response([], 503)]);
        $this->owner = User::factory()->create(['roles' => ['ENGINEER'], 'active' => true])->refresh();
        $this->actingAs($this->owner)->withSession(['auth_version' => $this->owner->auth_version]);
    }

    private function report(): array
    {
        return app(AssetWellnessCompleteness::class)->report(self::ASSET);
    }

    private function plan(array $changes = []): PdmInspectionPlan
    {
        return PdmInspectionPlan::create(array_replace([
            'request_key' => (string) Str::uuid(), 'identity_key' => hash('sha256', (string) Str::uuid()),
            'created_by' => $this->owner->id, 'title' => 'Synthetic matrix plan', 'asset_ref' => self::ASSET,
            'template_id' => 'test-matrix', 'template_fingerprint' => str_repeat('a', 64),
            'template_snapshot' => ['preview_only' => false, 'fields' => [['key' => 'point', 'label' => 'Synthetic point', 'type' => 'number', 'unit' => 'mm/s']]],
            'point_key' => 'point', 'method' => 'VIBRATION', 'unit' => 'mm/s', 'instrument' => 'Test meter',
            'measurement_mode' => 'RMS', 'operating_condition' => 'Synthetic load', 'asset_selection_note' => 'Synthetic location',
            'frequency_value' => 7, 'frequency_unit' => 'days', 'first_due_on' => '2026-11-01', 'status' => 'active',
        ], $changes));
    }

    private function measurement(PdmInspectionPlan $plan, array $changes = []): PdmActivity
    {
        return PdmActivity::create(array_replace($plan->only(['asset_ref', 'template_id', 'template_fingerprint', 'template_snapshot', 'method', 'instrument', 'measurement_mode', 'operating_condition', 'asset_selection_note']), [
            'request_key' => (string) Str::uuid(), 'created_by' => $this->owner->id, 'title' => 'Synthetic measurement',
            'inspection_type' => 'routine', 'time_precision' => 'date', 'measured_on' => '2026-11-09',
            'readings' => ['point' => ['value' => '0', 'unit' => 'mm/s']],
        ], $changes))->refresh();
    }

    private function analysis(PdmActivity $activity, array $changes = [], bool $reviewed = true): InspectionDraft
    {
        $inspection = InspectionDraft::create(array_replace([
            'created_by' => $this->owner->id, 'asset_ref' => self::ASSET, 'pdm_activity_id' => $activity->id,
            'request_reference' => 'Synthetic only', 'request_summary' => 'Synthetic test', 'method' => 'VIBRATION',
            'finding' => 'Synthetic observation', 'recommendation' => 'Synthetic recommendation', 'follow_up_status' => 'completed',
        ], $changes))->refresh();
        if ($reviewed) {
            WorkspaceActivity::create(['kind' => 'inspection', 'subject_id' => $inspection->id, 'version' => $inspection->version,
                'actor_id' => $this->owner->id, 'asset_ref' => self::ASSET, 'action' => 'created',
                'changes' => ['pdm_basis' => ['after' => $activity->analysisBasis()]], 'created_at' => now()]);
        }

        return $inspection;
    }

    public function test_missing_denominator_and_paused_plans_are_not_full_coverage(): void
    {
        $this->plan(['status' => 'paused']);
        $this->plan(['asset_ref' => self::ASSET.'-OTHER']);
        $report = $this->report();
        $this->assertSame(0, $report['required_count']);
        $this->assertSame(1, $report['paused_count']);
        $this->assertSame([], $report['rows']);
        $this->assertNull($report['score']);
        $this->get(route('wellness.index', ['asset_ref' => self::ASSET]))->assertOk()->assertSee('Penyebut titik wajib belum ditentukan.');
    }

    public function test_valid_zero_and_exact_context_use_existing_schedule_and_preserve_date_precision(): void
    {
        $plan = $this->plan();
        $activity = $this->measurement($plan);
        foreach ([['asset_ref' => self::ASSET.'-OTHER'], ['instrument' => 'Other meter'], ['inspection_type' => 'request'],
            ['readings' => ['point' => ['value' => 'NaN', 'unit' => 'mm/s']]], ['readings' => ['point' => ['value' => '1', 'unit' => 'micron']]],
            ['measured_on' => '2026-11-11']] as $change) {
            $this->measurement($plan, $change);
        }
        $row = $this->report()['rows'][0];
        $this->assertSame('current', $row['state']);
        $this->assertSame($activity->id, $row['measurement']->id);
        $this->assertSame('0', $row['measurement']->readings['point']['value']);
        $this->assertSame('2026-11-16', $row['schedule']['next_due_on']->toDateString());
        $this->assertSame('missing', $row['analysis_state']);
        Http::assertNothingSent();
        $this->get(route('wellness.index', ['asset_ref' => self::ASSET]))->assertOk()->assertSee('Tanggal saja')->assertSee('Bukti masih berlaku')->assertDontSee('09 Nov 2026 00:00');
    }

    public function test_expiration_due_today_overdue_and_first_due_do_not_reset_measurement_age(): void
    {
        $due = $this->plan();
        $this->measurement($due, ['measured_on' => '2026-11-03']);
        $overdue = $this->plan(['instrument' => 'Other meter']);
        $this->measurement($overdue, ['measured_on' => '2026-11-02']);
        $futurePlan = $this->plan(['instrument' => 'Third meter', 'first_due_on' => '2026-12-01']);
        $this->measurement($futurePlan, ['measured_on' => '2026-11-01']);
        $report = $this->report();
        $this->assertSame(3, $report['counts']['expired']);
        $this->assertSame(1, $report['counts']['due']);
        $this->assertSame(1, $report['counts']['overdue']);
        $this->assertSame('upcoming', $report['rows'][2]['schedule']['state']);
        $this->assertSame('expired', $report['rows'][2]['state']);
    }

    public function test_empty_latest_reading_uses_older_valid_schedule_evidence_and_shows_limits(): void
    {
        $plan = $this->plan();
        $older = $this->measurement($plan, ['measured_on' => '2026-11-01']);
        $this->measurement($plan, ['readings' => ['point' => ['value' => '', 'unit' => 'mm/s']]]);
        $row = $this->report()['rows'][0];
        $this->assertSame($older->id, $row['measurement']->id);
        $this->assertSame('expired', $row['state']);
        $this->get(route('wellness.index', ['asset_ref' => self::ASSET]))->assertOk()->assertSee('bukti valid sebelumnya');
    }

    public function test_analysis_is_versioned_and_completed_is_not_effectiveness_evidence(): void
    {
        $activity = $this->measurement($this->plan());
        $inspection = $this->analysis($activity);
        $report = $this->report();
        $this->assertSame('current', $report['rows'][0]['analysis_state']);
        $this->assertSame('unassessed', $report['rows'][0]['follow_up']['state']);
        $this->assertSame($inspection->id, $report['follow_ups'][0]['inspection']->id);
        $activity->update(['readings' => ['point' => ['value' => '2', 'unit' => 'mm/s']]]);
        $report = $this->report();
        $this->assertSame('stale', $report['rows'][0]['analysis_state']);
        $this->assertSame(1, $report['counts']['stale_analysis']);
        $this->get(route('wellness.index', ['asset_ref' => self::ASSET]))->assertOk()->assertSee('Analisis stale')->assertSee('Efektivitas belum dinilai')->assertSee('Status Selesai bukan bukti efektif')->assertDontSee('@else')->assertDontSee('Belum ada rekomendasi tertaut pada pengukuran ini.');
    }

    public function test_unknown_analysis_and_foreign_asset_analysis_do_not_count_as_current(): void
    {
        $activity = $this->measurement($this->plan());
        $inspection = $this->analysis($activity, [], false);
        $this->assertSame('unknown', $this->report()['rows'][0]['analysis_state']);
        $inspection->update(['asset_ref' => self::ASSET.'-OTHER']);
        $report = $this->report();
        $this->assertSame('missing', $report['rows'][0]['analysis_state']);
        $this->assertNull($report['rows'][0]['inspection']);
        $this->assertSame(0, $report['follow_up_count']);
    }

    public function test_earlier_recommendation_stays_visible_after_new_measurement_and_review_becomes_stale(): void
    {
        $plan = $this->plan();
        $before = $this->measurement($plan, ['measured_on' => '2026-11-01']);
        $inspection = $this->analysis($before);
        $after = $this->measurement($plan);
        $service = app(ActionEffectiveness::class);
        ActionEffectivenessReview::create(['inspection_draft_id' => $inspection->id, 'revision' => 1,
            'created_by' => $this->owner->id, 'request_key' => (string) Str::uuid(), 'before_activity_id' => $before->id, 'after_activity_id' => $after->id,
            'action_taken' => 'Synthetic alignment', 'completed_on' => '2026-11-05', 'point' => 'point', 'decision' => 'effective', 'reason' => 'Synthetic criterion',
            'evidence' => ['inspection' => $service->inspectionBasis($inspection), 'before' => $service->snapshot($before), 'after' => $service->snapshot($after)], 'created_at' => now()]);
        $report = $this->report();
        $this->assertSame('missing', $report['rows'][0]['analysis_state']);
        $this->assertNull($report['rows'][0]['follow_up']);
        $this->assertSame('effective', $report['follow_ups'][0]['state']);
        $after->update(['readings' => ['point' => ['value' => '3', 'unit' => 'mm/s']]]);
        $this->assertSame('stale', $this->report()['follow_ups'][0]['state']);
    }

    public function test_matrix_is_current_not_filtered_by_historical_report_period_and_remains_read_only_on_outage(): void
    {
        $this->measurement($this->plan());
        foreach (['MANAGER', 'ADMIN', 'SUPERVISOR', 'ENGINEER'] as $role) {
            $user = User::factory()->create(['roles' => [$role], 'active' => true])->refresh();
            $this->actingAs($user)->withSession(['auth_version' => $user->auth_version]);
            $response = $this->get(route('wellness.index', ['asset_ref' => self::ASSET, 'year' => 2025]));
            $response->assertOk()->assertSee('2026-11-10')->assertSee('Matriks saat ini tidak dibatasi periode laporan')->assertSee('09 Nov 2026')->assertHeader('Cache-Control', 'no-store, private');
            $this->assertNull($response['report']['score']);
            $this->assertNull($response['report']['official_score']);
            $this->assertSame(0, $response['report']['components']['pdm']['evidence']['count']);
        }
        $this->assertDatabaseCount('pdm_inspection_plans', 1);
        $this->assertDatabaseCount('pdm_activities', 1);
        $this->assertDatabaseCount('action_effectiveness_reviews', 0);
        Http::assertNotSent(fn ($request) => $request->method() !== 'GET');
    }

    public function test_plan_and_action_limits_do_not_claim_complete_asset_coverage(): void
    {
        for ($i = 0; $i < 21; $i++) {
            $activity = $this->measurement($this->plan(['instrument' => 'Meter '.$i]));
            $this->analysis($activity);
        }
        $report = $this->report();
        $this->assertSame(21, $report['required_count']);
        $this->assertSame(20, $report['inspected_count']);
        $this->assertTrue($report['truncated']);
        $this->assertSame(20, $report['counts']['current']);
        $this->assertSame(21, $report['follow_up_count']);
        $this->assertCount(20, $report['follow_ups']);
        $this->assertTrue($report['follow_ups_truncated']);
        $this->get(route('wellness.index', ['asset_ref' => self::ASSET]))->assertOk()->assertSee('Parsial: hanya 20 dari 21')->assertSee('Parsial: 20 dari 21 rekomendasi');
    }

    public function test_measurement_search_limit_is_unknown_not_missing(): void
    {
        $plan = $this->plan();
        for ($i = 0; $i < 251; $i++) {
            $this->measurement($plan, ['readings' => ['point' => ['value' => '', 'unit' => 'mm/s']]]);
        }
        $report = $this->report();
        $this->assertSame('unknown', $report['rows'][0]['state']);
        $this->assertSame(1, $report['counts']['unknown']);
        $this->assertSame(0, $report['counts']['missing']);
        $this->assertNull($report['rows'][0]['schedule']['next_due_on']);
    }

    public function test_missing_plan_or_effectiveness_storage_is_unavailable_not_zero(): void
    {
        $activity = $this->measurement($this->plan());
        $this->analysis($activity);
        Schema::drop('action_effectiveness_reviews');
        $this->assertSame('unavailable', $this->report()['follow_ups'][0]['state']);
        Schema::drop('pdm_inspection_plan_revisions');
        Schema::drop('pdm_inspection_plans');
        $report = $this->report();
        $this->assertFalse($report['available']);
        $this->assertNull($report['required_count']);
        $this->get(route('wellness.index', ['asset_ref' => self::ASSET]))->assertOk()->assertSee('Penyebut titik wajib belum dapat dibaca, bukan nol.')->assertSee('Penyimpanan review efektivitas belum tersedia');
    }
}
