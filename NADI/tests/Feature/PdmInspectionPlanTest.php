<?php

namespace Tests\Feature;

use App\Models\PdmActivity;
use App\Models\PdmInspectionPlan;
use App\Models\PdmInspectionPlanRevision;
use App\Models\User;
use App\Services\PdmFormCatalog;
use App\Services\PdmSchedule;
use Carbon\CarbonImmutable;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Http\Client\Factory;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Str;
use Tests\TestCase;

class PdmInspectionPlanTest extends TestCase
{
    use RefreshDatabase;

    private const ASSET = 'asset:MAXIMO:MXASSET:BSR:IP:SYNTHETIC-PUMP-001';

    private User $owner;

    protected function setUp(): void
    {
        parent::setUp();
        $this->travelTo(CarbonImmutable::parse('2026-11-09 10:00:00', 'Asia/Jakarta'));
        config(['services.reliability_mart.url' => 'http://mart.test']);
        Http::preventStrayRequests();
        Http::fake(['mart.test/*' => fn () => Http::response(['canonical_id' => self::ASSET, 'source_asset_number' => 'SYNTHETIC-PUMP-001', 'site_code' => 'BSR', 'organization_code' => 'IP', 'hierarchy_category' => 'component', 'scope_basis' => 'DIRECT_SOURCE_UNIT', 'registered' => false, 'description' => 'SOURCE-NOT-STORED'])]);
        $this->owner = $this->signIn();
    }

    private function signIn(string $role = 'ENGINEER'): User
    {
        $user = User::factory()->create(['roles' => [$role], 'active' => true])->refresh();
        $this->actingAs($user)->withSession(['auth_version' => $user->auth_version]);

        return $user;
    }

    private function input(array $changes = []): array
    {
        $catalog = app(PdmFormCatalog::class);

        return array_replace(['request_key' => (string) Str::uuid(), 'title' => 'Synthetic point inspection plan', 'asset_ref' => self::ASSET,
            'template_id' => 'SYNTHETIC_MOTOR', 'template_fingerprint' => $catalog->fingerprint($catalog->find('SYNTHETIC_MOTOR')), 'point_key' => 'field_c3',
            'instrument' => 'TEST meter', 'measurement_mode' => 'RMS', 'operating_condition' => 'Test running 50 MW',
            'asset_selection_note' => 'Synthetic exact field selection, not actual field data.', 'acknowledge_draft' => '1',
            'frequency_value' => 7, 'frequency_unit' => 'days', 'first_due_on' => '2026-11-01', 'notes' => 'Synthetic test plan'], $changes);
    }

    private function save(array $changes = []): PdmInspectionPlan
    {
        $this->post(route('pdm.plans.store'), $this->input($changes))->assertSessionHasNoErrors()->assertRedirect();

        return PdmInspectionPlan::latest('id')->firstOrFail();
    }

    private function activity(PdmInspectionPlan $plan, array $changes = []): PdmActivity
    {
        return PdmActivity::create(array_replace($plan->only(['asset_ref', 'template_id', 'template_fingerprint', 'template_snapshot', 'method', 'instrument', 'measurement_mode', 'operating_condition', 'asset_selection_note']),
            ['request_key' => (string) Str::uuid(), 'created_by' => $this->owner->id, 'title' => 'Synthetic measurement', 'inspection_type' => 'routine',
                'time_precision' => 'date', 'measured_on' => '2026-11-07', 'readings' => [$plan->point_key => ['value' => '0', 'unit' => $plan->unit]]], $changes));
    }

    public function test_create_and_pages_preserve_exact_identity_snapshot_and_date(): void
    {
        $this->get(route('pdm.plans.create', ['asset_ref' => self::ASSET]))->assertOk()->assertSee('Template kandidat');
        $this->get(route('pdm.plans.create', ['asset_ref' => self::ASSET, 'template_id' => 'SYNTHETIC_MOTOR']))->assertOk()->assertSee('1V')->assertSee('name="request_key"', false);
        $plan = $this->save(['created_by' => 1234, 'version' => 25, 'method' => 'THERMOGRAPHY']);
        $this->assertSame($this->owner->id, $plan->created_by);
        $this->assertSame(1, $plan->version);
        $this->assertSame('VIBRATION', $plan->method);
        $this->assertSame('mm/s', $plan->unit);
        $this->assertSame('2026-11-01', DB::table('pdm_inspection_plans')->value('first_due_on'));
        $this->assertDatabaseCount('pdm_inspection_plan_revisions', 1);
        $this->assertStringNotContainsString('SOURCE-NOT-STORED', $plan->toJson());
        $this->get(route('pdm.plans.index'))->assertOk()->assertSee('Terlambat')->assertSee('Belum diukur pada konteks ini');
        $this->get(route('pdm.plans.show', $plan))->assertOk()->assertSee('Riwayat perubahan')->assertSee('Synthetic test plan');
        $this->get(route('pdm.plans.edit', $plan))->assertOk()->assertSee('name="version"', false);
        Http::assertNotSent(fn ($request) => $request->method() !== 'GET');
    }

    public function test_no_plans_is_an_explicit_empty_state(): void
    {
        $this->get(route('pdm.plans.index'))->assertOk()->assertSee('Belum ada rencana inspeksi')->assertSee('0 / 0');
        Http::assertNothingSent();
    }

    public function test_permissions_owner_and_authentication_are_enforced(): void
    {
        $plan = $this->save();
        foreach (['ADMIN', 'SUPERVISOR', 'MANAGER', 'ENGINEER'] as $role) {
            $this->signIn($role);
            $this->get(route('pdm.plans.index'))->assertOk();
            $this->get(route('pdm.plans.show', $plan))->assertOk();
            $this->get(route('pdm.plans.edit', $plan))->assertForbidden();
            $this->put(route('pdm.plans.update', $plan), [])->assertForbidden();
            if ($role !== 'ENGINEER') {
                $this->get(route('pdm.plans.create'))->assertForbidden();
                $this->post(route('pdm.plans.store'), $this->input())->assertForbidden();
            }
        }
        auth()->logout();
        $this->get(route('pdm.plans.index'))->assertRedirect(route('login'));
        $this->post(route('pdm.plans.store'), $this->input())->assertRedirect(route('login'));
    }

    public function test_repeated_post_and_duplicate_context_cannot_double_count_plans(): void
    {
        $input = $this->input();
        $this->post(route('pdm.plans.store'), $input)->assertSessionHasNoErrors()->assertRedirect();
        $plan = PdmInspectionPlan::firstOrFail();
        $this->post(route('pdm.plans.store'), $input)->assertRedirect(route('pdm.plans.show', $plan));
        $this->post(route('pdm.plans.store'), $this->input())->assertSessionHasErrors('point_key');
        $this->assertDatabaseCount('pdm_inspection_plans', 1);
        $this->assertDatabaseCount('pdm_inspection_plan_revisions', 1);
        $this->signIn();
        $this->post(route('pdm.plans.store'), $input)->assertConflict();
        $this->post(route('pdm.plans.store'), $this->input())->assertSessionHasErrors('point_key');
        $this->assertDatabaseCount('pdm_inspection_plans', 1);
    }

    public function test_invalid_frequency_template_point_unit_and_missing_context_are_rejected(): void
    {
        foreach ([['frequency_value' => 0], ['frequency_value' => 366], ['frequency_unit' => 'minutes'], ['first_due_on' => '2026-02-30'],
            ['template_fingerprint' => str_repeat('0', 64)], ['point_key' => 'not-in-template'], ['unit' => 'µm'], ['instrument' => ''],
            ['measurement_mode' => ''], ['operating_condition' => ''], ['asset_selection_note' => ''], ['acknowledge_draft' => '']] as $changes) {
            $this->post(route('pdm.plans.store'), $this->input($changes))->assertSessionHasErrors();
        }
        $catalog = app(PdmFormCatalog::class);
        $this->post(route('pdm.plans.store'), $this->input(['template_id' => 'SYNTHETIC_REVIEW', 'template_fingerprint' => $catalog->fingerprint($catalog->find('SYNTHETIC_REVIEW'))]))->assertSessionHasErrors('template_id');
        $this->post(route('pdm.plans.store'), $this->input(['template_id' => 'SYNTHETIC_UNKNOWN_UNIT', 'template_fingerprint' => $catalog->fingerprint($catalog->find('SYNTHETIC_UNKNOWN_UNIT')), 'point_key' => 'field_b2']))->assertSessionHasErrors('unit');
        $this->assertDatabaseCount('pdm_inspection_plans', 0);
    }

    public function test_update_keeps_identity_audits_revisions_rejects_stale_form_and_works_offline(): void
    {
        $plan = $this->save();
        Http::swap(new Factory);
        Http::preventStrayRequests();
        $data = [...$this->input(), 'status' => 'paused', 'version' => 1, 'change_reason' => 'Synthetic pause for test', 'asset_ref' => 'changed-asset', 'point_key' => 'changed-point', 'frequency_value' => 2];
        $this->put(route('pdm.plans.update', $plan), $data)->assertSessionHasNoErrors()->assertRedirect();
        $plan->refresh();
        $this->assertSame('paused', $plan->status);
        $this->assertSame(2, $plan->version);
        $this->assertSame(self::ASSET, $plan->asset_ref);
        $this->assertSame('field_c3', $plan->point_key);
        $this->assertDatabaseCount('pdm_inspection_plan_revisions', 2);
        $this->get(route('pdm.plans.show', $plan))->assertOk()->assertSee('Tidak dijadwalkan selama jeda');
        $this->put(route('pdm.plans.update', $plan), $data)->assertSessionHasErrors('version');
        $this->assertDatabaseCount('pdm_inspection_plan_revisions', 2);
        Http::assertNothingSent();
    }

    public function test_source_outage_keeps_create_input_and_requires_new_identity_verification(): void
    {
        Http::swap(new Factory);
        Http::preventStrayRequests();
        Http::fake(['mart.test/*' => Http::response([], 503)]);
        $url = route('pdm.plans.create', ['asset_ref' => self::ASSET, 'template_id' => 'SYNTHETIC_MOTOR']);
        $input = $this->input();
        $this->from($url)->post(route('pdm.plans.store'), $input)->assertRedirect($url)->assertSessionHasErrors('asset_ref')->assertSessionHasInput('title', $input['title']);
        $this->get($url)->assertOk()->assertSee('name="frequency_value"', false)->assertSee($input['title'])->assertSee($input['request_key']);
        $this->assertDatabaseCount('pdm_inspection_plans', 0);
    }

    public function test_zero_counts_missing_does_not_and_corrected_values_recompute_coverage(): void
    {
        $plan = $this->save();
        $activity = $this->activity($plan);
        $coverage = app(PdmSchedule::class)->coverage($plan);
        $this->assertTrue($coverage['covered']);
        $this->assertSame($activity->id, $coverage['latest']->id);
        $this->assertSame('2026-11-14', $coverage['next_due_on']->toDateString());
        $activity->update(['readings' => [$plan->point_key => ['value' => null, 'unit' => $plan->unit]]]);
        $coverage = app(PdmSchedule::class)->coverage($plan);
        $this->assertNull($coverage['latest']);
        $this->assertFalse($coverage['covered']);
        $this->assertSame('overdue', $coverage['state']);
        $this->assertSame('2026-11-01', $coverage['next_due_on']->toDateString());
    }

    public function test_blank_latest_uses_previous_valid_measurement_and_rejects_mismatched_identity_context(): void
    {
        $plan = $this->save();
        $older = $this->activity($plan, ['measured_on' => '2026-11-02']);
        $this->activity($plan, ['readings' => [$plan->point_key => ['value' => '', 'unit' => $plan->unit]]]);
        foreach ([['asset_ref' => self::ASSET.'-OTHER'], ['template_id' => 'SYNTHETIC_FAN'], ['template_fingerprint' => str_repeat('a', 64)],
            ['method' => 'MCSA'], ['instrument' => 'different'], ['measurement_mode' => 'different'], ['operating_condition' => 'different'],
            ['asset_selection_note' => 'different'], ['inspection_type' => 'request'], ['measured_on' => '2026-11-10'],
            ['readings' => [$plan->point_key => ['value' => '1', 'unit' => 'µm']]],
            ['readings' => [$plan->point_key => ['value' => 'NaN', 'unit' => $plan->unit]]],
            ['template_snapshot' => [...$plan->template_snapshot, 'title' => 'different']]] as $changes) {
            $this->activity($plan, $changes);
        }
        $coverage = app(PdmSchedule::class)->coverage($plan);
        $this->assertSame($older->id, $coverage['latest']->id);
        $this->assertSame('due', $coverage['state']);
        $this->assertSame('2026-11-09', $coverage['next_due_on']->toDateString());
        $this->assertFalse($coverage['covered']);
    }

    public function test_week_month_end_and_first_due_floor_use_calendar_dates(): void
    {
        $plan = $this->save(['frequency_value' => 1, 'frequency_unit' => 'months', 'first_due_on' => '2026-01-01']);
        $activity = $this->activity($plan, ['measured_on' => '2026-01-31']);
        $this->assertSame('2026-02-28', app(PdmSchedule::class)->coverage($plan)['next_due_on']->toDateString());
        $plan->update(['frequency_unit' => 'weeks', 'frequency_value' => 2]);
        $this->assertSame('2026-02-14', app(PdmSchedule::class)->coverage($plan)['next_due_on']->toDateString());
        $plan->update(['first_due_on' => '2026-12-01']);
        $coverage = app(PdmSchedule::class)->coverage($plan);
        $this->assertSame('2026-12-01', $coverage['next_due_on']->toDateString());
        $this->assertFalse($coverage['covered'], 'A future first due date must not make an old sample fresh.');
        $this->assertNull($activity->measured_at);
        $this->assertNull($activity->timezone);
    }

    public function test_timestamp_uses_actual_instant_even_when_wit_source_date_is_tomorrow_in_wib(): void
    {
        $plan = $this->save();
        $this->travelTo(CarbonImmutable::parse('2026-11-09 22:30:00', 'Asia/Jakarta'));
        $actual = $this->activity($plan, ['time_precision' => 'datetime', 'measured_at' => '2026-11-09 15:15:00', 'timezone' => 'Asia/Jayapura']);
        $this->activity($plan, ['time_precision' => 'datetime', 'measured_at' => '2026-11-09 16:00:00', 'timezone' => 'Asia/Jakarta']);
        $coverage = app(PdmSchedule::class)->coverage($plan);
        $this->assertSame($actual->id, $coverage['latest']->id);
        $this->assertSame('2026-11-10', $actual->measurementDate());
        $this->assertSame('2026-11-17', $coverage['next_due_on']->toDateString());
    }

    public function test_unknown_coverage_is_explicit_when_search_limit_is_reached(): void
    {
        $plan = $this->save();
        $this->activity($plan, ['measured_on' => '2026-10-01']);
        for ($i = 0; $i <= PdmSchedule::LIMIT; $i++) {
            $this->activity($plan, ['readings' => [$plan->point_key => ['value' => '', 'unit' => $plan->unit]]]);
        }
        $coverage = app(PdmSchedule::class)->coverage($plan);
        $this->assertSame('unknown', $coverage['state']);
        $this->assertTrue($coverage['truncated']);
        $this->assertNull($coverage['next_due_on']);
        $this->get(route('pdm.plans.index'))->assertOk()->assertSee('Cakupan belum pasti');
    }

    public function test_pause_is_excluded_from_coverage_and_lists_are_paginated(): void
    {
        $plan = $this->save(['status' => 'paused']);
        $this->assertSame('active', $plan->status, 'Create cannot smuggle a lifecycle state.');
        $this->activity($plan);
        $plan->update(['status' => 'paused']);
        $this->assertFalse(app(PdmSchedule::class)->coverage($plan)['covered']);
        for ($i = 0; $i < 20; $i++) {
            $copy = $plan->replicate();
            $copy->request_key = (string) Str::uuid();
            $copy->identity_key = hash('sha256', (string) $i);
            $copy->save();
        }
        $this->get(route('pdm.plans.index'))->assertOk()->assertViewHas('plans', fn ($rows) => $rows->total() === 21 && $rows->count() === 20);
        $this->get(route('pdm.plans.index', ['status' => 'active']))->assertOk()->assertSee('Belum ada rencana inspeksi');
    }

    public function test_audit_failure_rolls_back_the_plan_and_routes_cannot_delete_history(): void
    {
        $plan = $this->save();
        PdmInspectionPlanRevision::creating(function () {
            throw new \RuntimeException('Synthetic audit failure');
        });
        try {
            $this->put(route('pdm.plans.update', $plan), [...$this->input(), 'status' => 'paused', 'version' => 1, 'change_reason' => 'Test atomic audit'])->assertServerError();
            $this->assertSame(1, $plan->fresh()->version);
            $this->assertSame('active', $plan->fresh()->status);
            $this->assertDatabaseCount('pdm_inspection_plan_revisions', 1);
        } finally {
            PdmInspectionPlanRevision::flushEventListeners();
        }
        $this->delete(route('pdm.plans.show', $plan))->assertStatus(405);
    }

    public function test_migration_refuses_to_rollback_populated_plan_history(): void
    {
        $this->save();
        $migration = require database_path('migrations/2026_11_09_000002_create_pdm_inspection_plans.php');
        try {
            $migration->down();
            $this->fail('Populated schedule history must never be dropped by rollback.');
        } catch (\RuntimeException $exception) {
            $this->assertStringContainsString('Rollback ditolak', $exception->getMessage());
        }
        $this->assertDatabaseCount('pdm_inspection_plans', 1);
        $this->assertDatabaseCount('pdm_inspection_plan_revisions', 1);
    }

    public function test_untrusted_text_is_escaped_and_wib_day_boundary_is_used(): void
    {
        $plan = $this->save(['title' => '<script>bad()</script>', 'first_due_on' => '2026-11-10']);
        $this->get(route('pdm.plans.show', $plan))->assertOk()->assertSee('&lt;script&gt;bad()&lt;/script&gt;', false)->assertDontSee('<script>bad()</script>', false);
        $this->travelTo(CarbonImmutable::parse('2026-11-09 18:00:00', 'UTC'));
        $this->assertSame('due', app(PdmSchedule::class)->coverage($plan)['state']);
    }
}
