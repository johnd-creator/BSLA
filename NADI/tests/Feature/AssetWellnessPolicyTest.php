<?php

namespace Tests\Feature;

use App\Models\AssetWellnessPolicy;
use App\Models\PdmActivity;
use App\Models\User;
use App\Services\AssetWellness;
use App\Services\AssetWellnessMethod;
use App\Services\ReliabilityMart;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Schema;
use Illuminate\Support\Str;
use Tests\TestCase;

class AssetWellnessPolicyTest extends TestCase
{
    use RefreshDatabase;

    private const ASSET = 'asset:MAXIMO:MXASSET:BSR:IP:WELLNESS-POLICY-FIXTURE';

    private User $owner;

    private bool $outage = false;

    protected function setUp(): void
    {
        parent::setUp();
        $this->travelTo(now()->setDateTime(2026, 11, 9, 12, 0, 0));
        config(['services.reliability_mart.url' => 'http://mart.test']);
        Http::preventStrayRequests();
        Http::fake(fn ($request) => ! $this->outage && str_contains($request->url(), '/assets/')
            ? Http::response(['canonical_id' => rawurldecode(basename(parse_url($request->url(), PHP_URL_PATH))), 'site_code' => 'BSR', 'organization_code' => 'IP', 'registered' => false, 'hierarchy_category' => 'equipment', 'scope_basis' => 'DIRECT_SOURCE_UNIT', 'description' => 'SYNTHETIC policy fixture'])
            : Http::response([], 503));
        $this->owner = User::factory()->create(['roles' => ['ENGINEER'], 'active' => true])->refresh();
        $this->login($this->owner);
    }

    private function login(User $user): void
    {
        $this->actingAs($user)->withSession(['auth_version' => $user->auth_version]);
    }

    private function scope(): array
    {
        return ['asset_ref' => self::ASSET, 'year' => 2026];
    }

    private function payload(array $extra = []): array
    {
        return array_replace(['asset_ref' => self::ASSET, 'year' => 2026, 'request_key' => (string) Str::uuid(), 'previous_revision' => 0,
            'criticality_label' => null, 'criticality_basis' => null,
            'components' => array_fill_keys(array_keys(AssetWellness::COMPONENTS), ['max_age_days' => null, 'required_evidence' => null]),
            'pdm_rules' => [], 'evidence' => 'Synthetic proposed evidence only', 'reason' => 'Synthetic proposal for testing', 'acknowledge_draft' => 1], $extra);
    }

    private function measurement(array $extra = []): PdmActivity
    {
        return PdmActivity::create(array_replace(['asset_ref' => self::ASSET, 'created_by' => $this->owner->id, 'request_key' => (string) Str::uuid(), 'title' => 'SYNTHETIC policy measurement',
            'template_id' => 'fixture', 'template_fingerprint' => str_repeat('b', 64), 'method' => 'VIBRATION', 'time_precision' => 'date', 'measured_on' => '2026-11-08',
            'instrument' => 'Synthetic instrument', 'measurement_mode' => 'Synthetic mode', 'operating_condition' => 'Synthetic load', 'asset_selection_note' => 'Synthetic exact fixture',
            'template_snapshot' => ['id' => 'fixture', 'preview_only' => false, 'fields' => [['key' => 'v', 'label' => 'Synthetic velocity', 'type' => 'number', 'unit' => 'mm/s']]],
            'readings' => ['v' => ['value' => '0', 'unit' => 'mm/s']]], $extra));
    }

    private function withPoint(PdmActivity $anchor, array $point = []): array
    {
        return $this->payload(['pdm_rules' => [array_replace(['anchor_id' => $anchor->id, 'point' => 'v', 'lower' => 0, 'upper' => 4, 'max_age_days' => 1, 'requirement' => 'Synthetic proposed range only'], $point)],
            'anchor_fingerprints' => [$anchor->id => $anchor->analysisBasis()['fingerprint']]]);
    }

    private function save(array $payload)
    {
        return $this->post(route('wellness.policy.store'), $payload);
    }

    private function report(): array
    {
        return app(AssetWellnessMethod::class)->report(self::ASSET, 2026);
    }

    public function test_reading_without_a_policy_does_not_write_or_fetch_external_data(): void
    {
        $this->get(route('wellness.policy', $this->scope()))->assertOk()->assertSee('Belum ada pengaturan tersimpan')->assertSee('Belum ada pengukuran acuan')->assertHeader('Cache-Control', 'no-store, private');
        $this->assertDatabaseCount('asset_wellness_policies', 0);
        Http::assertNothingSent();
    }

    public function test_an_empty_proposal_keeps_unknowns_and_scores_null(): void
    {
        $this->save($this->payload())->assertSessionHasNoErrors()->assertRedirect(route('wellness.policy', $this->scope()));
        $policy = AssetWellnessPolicy::sole();
        $this->assertNull($policy->rules['criticality_label']);
        $this->assertSame('DRAFT_NOT_APPROVED', $policy->rules['status']);
        $this->assertSame([], $policy->rules['pdm_rules']);
        $this->assertNull($policy->rules['components']['pdm']['max_age_days']);
        $this->assertSame('NOT_ASSESSED', $this->report()['evidence_completeness']);
        $this->assertNull($this->report()['score']);
        $report = app(AssetWellness::class)->report(self::ASSET, 2026, app(ReliabilityMart::class));
        $this->assertNull($report['score']);
        $this->assertNull($report['official_score']);
        $this->assertSame('Belum dipetakan', $report['criticality']);
        $this->get(route('wellness.index', $this->scope()))->assertOk()->assertSee('Draft revisi 1')->assertSee('Belum dinilai engineer');
        Http::assertNotSent(fn ($request) => $request->method() !== 'GET');
    }

    public function test_only_engineer_owner_writes_and_other_roles_read(): void
    {
        foreach (['ADMIN', 'SUPERVISOR', 'MANAGER'] as $role) {
            $this->login(User::factory()->create(['roles' => [$role], 'active' => true])->refresh());
            $this->get(route('wellness.policy', $this->scope()))->assertOk()->assertDontSee('Simpan revisi draft');
            $this->save($this->payload())->assertForbidden();
        }
        $this->login($this->owner);
        $this->save($this->payload())->assertSessionHasNoErrors();
        $this->login(User::factory()->create(['roles' => ['ENGINEER'], 'active' => true])->refresh());
        $this->get(route('wellness.policy', $this->scope()))->assertOk()->assertSee('engineer lain')->assertDontSee('Simpan revisi draft');
        $this->save($this->payload(['previous_revision' => 1]))->assertForbidden();
        $this->assertDatabaseCount('asset_wellness_policies', 1);
    }

    public function test_repeated_post_is_idempotent_and_revisions_are_append_only(): void
    {
        $payload = $this->payload();
        $this->save($payload)->assertSessionHasNoErrors();
        $original = AssetWellnessPolicy::sole()->getAttributes();
        $this->save($payload)->assertSessionHasNoErrors();
        $this->assertDatabaseCount('asset_wellness_policies', 1);
        $this->save($this->payload(['previous_revision' => 1, 'criticality_label' => 'Synthetic high consequence', 'criticality_basis' => 'Synthetic consequence basis']))->assertSessionHasNoErrors();
        $this->assertDatabaseCount('asset_wellness_policies', 2);
        $this->assertSame($original, AssetWellnessPolicy::find($original['id'])->getAttributes());
        $this->save($this->payload(['previous_revision' => 1]))->assertSessionHasErrors('previous_revision');
        $this->assertSame(2, $this->report()['policy']->revision);
        $this->assertNull(app(AssetWellnessMethod::class)->report(self::ASSET, 2025)['policy']);
    }

    public function test_idempotency_key_cannot_be_reused_for_another_scope_or_author(): void
    {
        $payload = $this->payload();
        $this->save($payload)->assertSessionHasNoErrors();
        $this->save([...$payload, 'year' => 2025])->assertStatus(409);
        $this->login(User::factory()->create(['roles' => ['ENGINEER'], 'active' => true])->refresh());
        $this->save($payload)->assertStatus(409);
    }

    public function test_criticality_needs_a_basis_and_cannot_become_approval_or_score(): void
    {
        $this->save($this->payload(['criticality_label' => 'High']))->assertSessionHasErrors('criticality_basis');
        foreach (['status' => 'APPROVED', 'score' => 100, 'approved_by' => 1] as $key => $value) {
            $this->save($this->payload([$key => $value]))->assertSessionHasErrors($key);
        }
        $this->save($this->payload(['acknowledge_draft' => 0]))->assertSessionHasErrors('acknowledge_draft');
        $this->assertDatabaseCount('asset_wellness_policies', 0);
    }

    public function test_missing_components_bad_identity_year_and_age_are_rejected(): void
    {
        $this->save($this->payload(['components' => ['pdm' => []]]))->assertSessionHasErrors('components');
        $data = $this->payload();
        $data['components']['pdm']['max_age_days'] = -1;
        $this->save($data)->assertSessionHasErrors('components.pdm.max_age_days');
        $this->save($this->payload(['asset_ref' => self::ASSET.'/../wrong']))->assertSessionHasErrors('asset_ref');
        $this->save($this->payload(['year' => 2027]))->assertSessionHasErrors('year');
    }

    public function test_new_asset_verification_fails_closed_but_existing_draft_can_be_revised_during_outage(): void
    {
        $this->save($this->payload())->assertSessionHasNoErrors();
        $this->outage = true;
        $this->save($this->payload(['previous_revision' => 1]))->assertSessionHasNoErrors();
        $this->save($this->payload(['asset_ref' => self::ASSET.'-OTHER']))->assertSessionHasErrors('asset_ref');
        $this->assertDatabaseCount('asset_wellness_policies', 2);
    }

    public function test_point_range_is_exact_nullable_draft_and_preserves_zero_and_date_precision(): void
    {
        $anchor = $this->measurement();
        $this->save($this->withPoint($anchor))->assertSessionHasNoErrors();
        $check = $this->report()['checks'][0];
        $this->assertSame(0.0, $check['value']);
        $this->assertSame('WITHIN_PROPOSED_RANGE', $check['range']);
        $this->assertSame('WITHIN_PROPOSED_AGE', $check['freshness']);
        $this->assertSame(1, $check['age_days']);
        $this->assertNull($anchor->fresh()->measured_at);
        $this->get(route('wellness.policy', $this->scope()))->assertOk()->assertSee('Di dalam usulan rentang')->assertSee('Tanggal saja')->assertDontSee('08 Nov 2026 00:00');
        $this->assertNull($this->report()['score']);
    }

    public function test_same_day_date_only_order_and_future_time_do_not_guess_latest_value(): void
    {
        $anchor = $this->measurement();
        $this->save($this->withPoint($anchor))->assertSessionHasNoErrors();
        $this->measurement(['readings' => ['v' => ['value' => '999', 'unit' => 'mm/s']]]);
        $this->assertTrue($this->report()['checks'][0]['order_ambiguous']);
        $this->assertSame('NOT_COMPARED', $this->report()['checks'][0]['range']);
        $this->get(route('wellness.policy', $this->scope()))->assertSee('Urutan pengukuran pada tanggal yang sama tidak pasti');
        $this->measurement(['time_precision' => 'datetime', 'measured_at' => '2026-11-09T23:59:00Z', 'timezone' => 'UTC']);
        $this->assertSame('UNKNOWN', $this->report()['checks'][0]['freshness']);
        $this->assertSame('NOT_COMPARED', $this->report()['checks'][0]['range']);
    }

    public function test_unknown_age_does_not_inherit_component_threshold(): void
    {
        $anchor = $this->measurement();
        $data = $this->withPoint($anchor, ['max_age_days' => null]);
        $data['components']['pdm']['max_age_days'] = 10;
        $this->save($data)->assertSessionHasNoErrors();
        $this->assertSame('UNDECIDED', $this->report()['checks'][0]['freshness']);
    }

    public function test_range_and_age_exceptions_are_separate_and_never_health_labels(): void
    {
        $anchor = $this->measurement(['measured_on' => '2026-11-01', 'readings' => ['v' => ['value' => '9', 'unit' => 'mm/s']]]);
        $this->save($this->withPoint($anchor))->assertSessionHasNoErrors();
        $check = $this->report()['checks'][0];
        $this->assertSame('OUTSIDE_PROPOSED_RANGE', $check['range']);
        $this->assertSame('OLDER_THAN_PROPOSAL', $check['freshness']);
        $this->get(route('wellness.policy', $this->scope()))->assertSee('Di luar usulan rentang')->assertSee('bukan kategori sehat atau alarm');
    }

    public function test_different_asset_year_mode_unit_or_snapshot_cannot_fill_an_exact_point(): void
    {
        $anchor = $this->measurement();
        $this->save($this->withPoint($anchor))->assertSessionHasNoErrors();
        foreach ([['asset_ref' => self::ASSET.'-OTHER'], ['measured_on' => '2025-11-09'], ['measurement_mode' => 'Other mode']] as $extra) {
            $this->measurement([...$extra, 'readings' => ['v' => ['value' => '999', 'unit' => 'mm/s']]]);
        }
        $this->assertSame($anchor->id, $this->report()['checks'][0]['activity']->id);
        $this->measurement(['measured_on' => '2026-11-09', 'readings' => ['v' => ['value' => '999', 'unit' => 'm/s']]]);
        $check = $this->report()['checks'][0];
        $this->assertNull($check['value']);
        $this->assertSame('NOT_COMPARED', $check['range']);
    }

    public function test_latest_missing_value_is_not_replaced_with_older_numeric_reading(): void
    {
        $anchor = $this->measurement();
        $this->save($this->withPoint($anchor))->assertSessionHasNoErrors();
        $new = $this->measurement(['measured_on' => '2026-11-09', 'readings' => ['v' => ['value' => null, 'unit' => 'mm/s']]]);
        $check = $this->report()['checks'][0];
        $this->assertSame($new->id, $check['activity']->id);
        $this->assertNull($check['value']);
        $this->assertSame('NOT_COMPARED', $check['range']);
    }

    public function test_changed_anchor_invalidates_preview_and_stale_form_is_rejected(): void
    {
        $anchor = $this->measurement();
        $data = $this->withPoint($anchor);
        $this->save($data)->assertSessionHasNoErrors();
        $anchor->update(['instrument' => 'Corrected synthetic instrument']);
        $this->assertFalse($this->report()['checks'][0]['basis_current']);
        $this->assertSame('NOT_COMPARED', $this->report()['checks'][0]['range']);
        $this->save([...$data, 'request_key' => (string) Str::uuid(), 'previous_revision' => 1])->assertSessionHasErrors('pdm_rules.0.point');
    }

    public function test_invalid_point_bounds_context_or_anchor_is_rejected(): void
    {
        $anchor = $this->measurement();
        foreach ([['point' => 'not-a-point'], ['lower' => 5, 'upper' => 4], ['lower' => '1e999'], ['lower' => null, 'upper' => null], ['requirement' => ''], ['anchor_id' => 99999]] as $point) {
            $this->save($this->withPoint($anchor, $point))->assertSessionHasErrors('pdm_rules.0.point');
        }
        $other = $this->measurement(['asset_ref' => self::ASSET.'-OTHER']);
        $this->save($this->withPoint($other))->assertSessionHasErrors('pdm_rules.0.point');
        $anchor->update(['instrument' => '']);
        $this->save($this->withPoint($anchor))->assertSessionHasErrors('pdm_rules.0.point');
        $this->assertDatabaseCount('asset_wellness_policies', 0);
    }

    public function test_unknown_units_and_preview_only_templates_cannot_produce_thresholds(): void
    {
        $anchor = $this->measurement(['template_snapshot' => ['preview_only' => true, 'fields' => [['key' => 'v', 'type' => 'number', 'unit' => 'mm/s']]]]);
        $this->save($this->withPoint($anchor))->assertSessionHasErrors('pdm_rules.0.point');
        $mismatch = $this->measurement(['readings' => ['v' => ['value' => '3', 'unit' => 'm/s']]]);
        $this->save($this->withPoint($mismatch))->assertSessionHasErrors('pdm_rules.0.point');
        $anchor->update(['template_snapshot' => ['preview_only' => false, 'fields' => [['key' => 'v', 'type' => 'number', 'unit' => null]]], 'readings' => ['v' => ['value' => '3', 'unit' => null]]]);
        $this->save($this->withPoint($anchor))->assertSessionHasErrors('pdm_rules.0.point');
    }

    public function test_duplicate_rules_are_rejected_and_removal_retains_old_revision(): void
    {
        $anchor = $this->measurement();
        $data = $this->withPoint($anchor);
        $data['pdm_rules'][] = $data['pdm_rules'][0];
        $this->save($data)->assertSessionHasErrors('pdm_rules.1.point');
        $data = $this->withPoint($anchor);
        $this->save($data)->assertSessionHasNoErrors();
        $data['pdm_rules'][0]['remove'] = 1;
        $this->save([...$data, 'request_key' => (string) Str::uuid(), 'previous_revision' => 1])->assertSessionHasNoErrors();
        $this->assertSame([], $this->report()['checks']);
        $this->assertCount(1, AssetWellnessPolicy::where('revision', 1)->sole()->rules['pdm_rules']);
    }

    public function test_html_is_escaped_and_blank_point_rows_do_not_create_defaults(): void
    {
        $data = $this->payload(['criticality_label' => '<script>bad</script>', 'criticality_basis' => 'Synthetic basis', 'pdm_rules' => [['anchor_id' => '', 'point' => '', 'lower' => '', 'upper' => '', 'max_age_days' => '', 'requirement' => '']]]);
        $this->save($data)->assertSessionHasNoErrors();
        $this->get(route('wellness.policy', $this->scope()))->assertOk()->assertDontSee('<script>bad</script>', false)->assertSee('&lt;script&gt;bad&lt;/script&gt;', false);
        $this->assertSame([], $this->report()['checks']);
    }

    public function test_missing_migration_is_a_visible_blocker_not_a_broken_existing_page(): void
    {
        Schema::drop('asset_wellness_policies');
        $this->get(route('wellness.policy', $this->scope()))->assertOk()->assertSee('Penyimpanan pengaturan belum diaktifkan');
        $this->get(route('wellness.index', $this->scope()))->assertOk();
        $this->save($this->payload())->assertSessionHasErrors('previous_revision');
    }

    public function test_guest_must_log_in_and_no_update_or_delete_history_route_exists(): void
    {
        $this->put('/asset-wellness/policy')->assertStatus(405);
        $this->delete('/asset-wellness/policy')->assertStatus(405);
        auth()->logout();
        $this->get(route('wellness.policy', $this->scope()))->assertRedirect('/login');
        $this->save($this->payload())->assertRedirect('/login');
    }
}
