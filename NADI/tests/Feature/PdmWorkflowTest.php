<?php

namespace Tests\Feature;

use App\Models\InspectionDraft;
use App\Models\PdmActivity;
use App\Models\User;
use App\Models\WorkspaceActivity;
use App\Services\PdmFormCatalog;
use Carbon\CarbonImmutable;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Http\Client\Factory;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Str;
use Tests\TestCase;

class PdmWorkflowTest extends TestCase
{
    use RefreshDatabase;

    private const ASSET = 'asset:BSR:TEST';

    private User $owner;

    protected function setUp(): void
    {
        parent::setUp();
        config(['services.reliability_mart.url' => 'http://mart.test']);
        Http::preventStrayRequests();
        Http::fake(['mart.test/*' => fn () => Http::response(['canonical_id' => self::ASSET, 'site_code' => 'BSR', 'organization_code' => 'IP', 'hierarchy_category' => 'component', 'scope_basis' => 'DIRECT_SOURCE_UNIT', 'registered' => false])]);
        $this->owner = User::factory()->create(['roles' => ['ENGINEER'], 'active' => true])->refresh();
        $this->actingAs($this->owner)->withSession(['auth_version' => $this->owner->auth_version]);
    }

    private function measurement(array $changes = []): array
    {
        $catalog = app(PdmFormCatalog::class);
        $template = $catalog->find('SYNTHETIC_MOTOR');

        return array_replace([
            'request_key' => (string) Str::uuid(), 'title' => 'ROUTINE-MEASUREMENT', 'asset_ref' => self::ASSET,
            'template_id' => $template['id'], 'template_fingerprint' => $catalog->fingerprint($template),
            'measured_local' => '2026-01-01T10:00', 'timezone' => 'Asia/Jakarta', 'instrument' => 'TEST meter',
            'measurement_mode' => 'RMS', 'operating_condition' => 'Synthetic condition',
            'asset_selection_note' => 'Synthetic test evidence only', 'acknowledge_draft' => '1',
            'readings' => ['field_c3' => ['value' => '0']], 'inspection_type' => 'routine',
        ], $changes);
    }

    private function requestData(array $changes = []): array
    {
        return array_replace(['request_key' => (string) Str::uuid(), 'request_reference' => 'REQ-TEST', 'request_summary' => 'REQUEST-COMPLAINT', 'requester_name' => 'TEST-REQUESTER', 'inspection_type' => 'request'], $changes);
    }

    private function analysis(PdmActivity $activity, array $changes = []): array
    {
        return array_replace(['request_key' => (string) Str::uuid(), 'pdm_activity_id' => $activity->id, 'pdm_version' => $activity->fresh()->version, 'finding' => 'TEST-FINDING', 'recommendation' => 'TEST-RECOMMENDATION', 'follow_up_status' => 'open'], $changes);
    }

    public function test_routine_and_request_share_one_logbook_and_filters_without_automatic_recommendations(): void
    {
        $this->post('/pdm', $this->measurement())->assertSessionHasNoErrors();
        $request = $this->requestData();
        $this->post('/inspections', $request)->assertSessionHasNoErrors();
        $this->post('/inspections', $request)->assertSessionHasNoErrors();
        $this->assertDatabaseCount('inspection_drafts', 1);
        $this->assertNull(InspectionDraft::first()->recommendation);
        $this->get('/pdm')->assertOk()->assertSee('ROUTINE-MEASUREMENT')->assertSee('REQUEST-COMPLAINT')->assertSee('TEST-REQUESTER')
            ->assertViewHas('activities', fn ($page) => $page->total() === 2);
        $this->get('/pdm?inspection_type=routine')->assertOk()->assertSee('ROUTINE-MEASUREMENT')->assertDontSee('REQUEST-COMPLAINT');
        $this->get('/pdm?inspection_type=request&stage=request')->assertOk()->assertSee('REQUEST-COMPLAINT')->assertDontSee('ROUTINE-MEASUREMENT');
        $this->get('/pdm?q=TEST-REQUESTER')->assertOk()->assertSee('REQUEST-COMPLAINT')->assertDontSee('ROUTINE-MEASUREMENT');
        $this->get('/action-board')->assertOk()->assertDontSee('REQUEST-COMPLAINT')->assertSee('Belum ada rekomendasi pada pilihan ini');
    }

    public function test_request_measurement_requires_requester_and_complaint(): void
    {
        $this->post('/pdm', $this->measurement(['inspection_type' => 'request']))->assertSessionHasErrors(['requester_name', 'request_summary']);
        $this->post('/inspections', $this->requestData(['requester_name' => '']))->assertSessionHasErrors('requester_name');
        $this->assertDatabaseCount('pdm_activities', 0);
        $this->post('/pdm', $this->measurement(['inspection_type' => 'request', 'requester_name' => 'TEST-PERSON', 'request_summary' => 'TEST-COMPLAINT']))->assertSessionHasNoErrors();
        $activity = PdmActivity::firstOrFail();
        $this->assertSame('request', $activity->inspection_type);
        $this->get(route('pdm.show', $activity))->assertOk()->assertSee('TEST-PERSON')->assertSee('TEST-COMPLAINT');
    }

    public function test_recommendation_links_exact_measurement_asset_and_request_context_once(): void
    {
        $this->post('/pdm', $this->measurement())->assertSessionHasNoErrors();
        $activity = PdmActivity::firstOrFail();
        $this->get(route('inspections.create', ['pdm_activity_id' => $activity->id]))->assertOk()->assertSee($activity->reference());
        $data = $this->analysis($activity, ['asset_ref' => 'asset:WRONG', 'method' => 'OTHER', 'inspected_on' => '2020-02-02', 'created_by' => 999]);
        $this->post('/inspections', $data)->assertSessionHasNoErrors();
        $draft = InspectionDraft::firstOrFail();
        $this->assertSame(self::ASSET, $draft->asset_ref);
        $this->assertSame('VIBRATION', $draft->method);
        $this->assertSame('2026-01-01', $draft->inspected_on->format('Y-m-d'));
        $this->assertSame($this->owner->id, $draft->created_by);
        $this->assertSame('routine', $draft->inspection_type);
        $this->post('/inspections', $data)->assertRedirect(route('inspections.show', $draft));
        $this->post('/inspections', $this->analysis($activity))->assertSessionHasNoErrors();
        $this->assertDatabaseCount('inspection_drafts', 1);
        $this->get('/pdm')->assertOk()->assertViewHas('activities', fn ($page) => $page->total() === 1);
        $this->get('/pdm?stage=recommendation')->assertOk()->assertSee('ROUTINE-MEASUREMENT')->assertSee('TEST-RECOMMENDATION');
        $this->get('/action-board')->assertOk()->assertSee('TEST-RECOMMENDATION')->assertSee($activity->reference());
        $this->get(route('pdm.show', $activity))->assertOk()->assertSee('Buka analisis / tindak lanjut');
        Http::assertNotSent(fn ($request) => $request->method() !== 'GET');
    }

    public function test_analysis_can_be_saved_without_recommendation_and_board_remains_empty(): void
    {
        $this->post('/pdm', $this->measurement())->assertSessionHasNoErrors();
        $activity = PdmActivity::firstOrFail();
        $this->post('/inspections', $this->analysis($activity, ['recommendation' => '']))->assertSessionHasNoErrors();
        $this->assertNull(InspectionDraft::firstOrFail()->recommendation);
        $this->get('/pdm?stage=finding')->assertOk()->assertSee('TEST-FINDING');
        $this->get('/action-board')->assertOk()->assertDontSee('TEST-FINDING');
    }

    public function test_standalone_recommendation_requires_verified_asset_and_valid_result(): void
    {
        $this->post('/inspections', $this->requestData(['recommendation' => 'No result yet']))->assertSessionHasErrors(['asset_ref', 'finding', 'method', 'inspected_on']);
        $data = $this->requestData(['asset_ref' => self::ASSET, 'recommendation' => 'TEST-FOLLOW-UP', 'finding' => 'TEST-FINDING', 'method' => 'VISUAL', 'inspected_on' => '2026-01-01']);
        $this->post('/inspections', $data)->assertSessionHasNoErrors();
        Http::swap(new Factory);
        Http::preventStrayRequests();
        Http::fake(['mart.test/*' => fn () => Http::response([], 503)]);
        $this->post('/inspections', [...$data, 'request_key' => (string) Str::uuid()])->assertSessionHasErrors('asset_ref')->assertSessionHasInput('recommendation', 'TEST-FOLLOW-UP');
        $this->assertDatabaseCount('inspection_drafts', 1);
    }

    public function test_follow_up_status_is_owner_only_versioned_and_independent_of_wo(): void
    {
        $this->post('/pdm', $this->measurement())->assertSessionHasNoErrors();
        $activity = PdmActivity::firstOrFail();
        $data = $this->analysis($activity);
        $this->post('/inspections', $data)->assertSessionHasNoErrors();
        $draft = InspectionDraft::firstOrFail();
        $this->put(route('inspections.update', $draft), [...$data, 'version' => 1, 'follow_up_status' => 'in_progress'])->assertSessionHasNoErrors();
        $this->assertSame('in_progress', $draft->fresh()->follow_up_status);
        $this->get('/action-board?follow_up_status=open')->assertOk()->assertDontSee('TEST-RECOMMENDATION');
        $this->get('/action-board?follow_up_status=in_progress')->assertOk()->assertSee('TEST-RECOMMENDATION');
        $this->put(route('inspections.update', $draft), [...$data, 'version' => 1, 'follow_up_status' => 'completed'])->assertSessionHasErrors('version');
        $this->put(route('inspections.update', $draft), [...$data, 'version' => 2, 'follow_up_status' => 'completed'])->assertSessionHasNoErrors();
        foreach (['ADMIN', 'SUPERVISOR', 'MANAGER', 'ENGINEER'] as $role) {
            $user = User::factory()->create(['roles' => [$role], 'active' => true])->refresh();
            $this->actingAs($user)->withSession(['auth_version' => $user->auth_version]);
            $this->get('/action-board')->assertOk()->assertSee('Selesai');
            $this->get(route('inspections.create', ['pdm_activity_id' => $activity->id]))->assertForbidden();
            $this->post('/inspections', $this->analysis($activity))->assertForbidden();
            $this->put(route('inspections.update', $draft), [...$data, 'version' => 3])->assertForbidden();
        }
        Http::assertNotSent(fn ($request) => $request->method() !== 'GET');
    }

    public function test_links_and_measured_date_cannot_be_reassigned_after_analysis(): void
    {
        $measurement = $this->measurement();
        $this->post('/pdm', $measurement)->assertSessionHasNoErrors();
        $activity = PdmActivity::firstOrFail();
        $data = $this->analysis($activity);
        $this->post('/inspections', $data)->assertSessionHasNoErrors();
        $draft = InspectionDraft::firstOrFail();
        $this->put(route('inspections.update', $draft), [...$data, 'version' => 1, 'pdm_activity_id' => 999])->assertSessionHasErrors('pdm_activity_id');
        $this->put(route('pdm.update', $activity), [...$measurement, 'version' => 1, 'measured_local' => '2026-01-02T10:00'])->assertSessionHasErrors('measured_local');
        $this->put(route('pdm.update', $activity), [...$measurement, 'version' => 1, 'inspection_type' => 'request', 'requester_name' => 'tampered', 'request_summary' => 'tampered'])->assertSessionHasNoErrors();
        $this->assertSame('routine', $activity->fresh()->inspection_type);
        $this->assertNull($activity->fresh()->requester_name);
    }

    public function test_old_measurements_do_not_get_an_invented_routine_or_request_type(): void
    {
        $this->post('/pdm', $this->measurement())->assertSessionHasNoErrors();
        $activity = PdmActivity::firstOrFail();
        $activity->inspection_type = null;
        $activity->save();
        $this->get('/pdm')->assertOk()->assertSee('Jenis belum dicatat');
        $this->get(route('inspections.create', ['pdm_activity_id' => $activity->id]))->assertRedirect(route('pdm.edit', $activity));
        $this->get(route('pdm.edit', $activity))->assertOk()->assertSee('Pilih jenis inspeksi');
        $this->assertNull($activity->fresh()->inspection_type);
    }

    public function test_legacy_records_are_preserved_with_missing_requester_label_and_pagination_is_bounded(): void
    {
        for ($i = 0; $i < 22; $i++) {
            InspectionDraft::create(['created_by' => $this->owner->id, 'request_reference' => 'LEGACY-'.$i, 'request_summary' => 'Legacy request '.$i]);
        }
        $this->get('/pdm')->assertOk()->assertSee('Peminta belum dicatat')->assertViewHas('activities', fn ($page) => $page->total() === 22 && $page->count() === 20);
        $this->get('/pdm?page=2')->assertOk()->assertViewHas('activities', fn ($page) => $page->count() === 2);
        Http::assertNothingSent();
    }

    public function test_activity_audit_is_atomic_idempotent_and_uses_authenticated_actor(): void
    {
        $measurement = $this->measurement();
        $this->post('/pdm', $measurement)->assertSessionHasNoErrors();
        $this->post('/pdm', $measurement)->assertSessionHasNoErrors();
        $activity = PdmActivity::firstOrFail();
        $this->assertDatabaseCount('workspace_activities', 1);
        $this->assertDatabaseHas('workspace_activities', ['kind' => 'pdm', 'subject_id' => $activity->id, 'version' => 1, 'action' => 'created', 'actor_id' => $this->owner->id]);
        $this->put(route('pdm.update', $activity), [...$measurement, 'version' => 1, 'actor_id' => 999])->assertSessionHasNoErrors();
        $this->assertDatabaseCount('workspace_activities', 2);
        $this->put(route('pdm.update', $activity), [...$measurement, 'version' => 1])->assertSessionHasErrors('version');
        $this->assertDatabaseCount('workspace_activities', 2);
        $data = $this->analysis($activity);
        $this->post('/inspections', $data)->assertSessionHasNoErrors();
        $this->post('/inspections', $data)->assertSessionHasNoErrors();
        $this->assertDatabaseCount('workspace_activities', 3);
        $draft = InspectionDraft::firstOrFail();
        $this->put(route('inspections.update', $draft), [...$data, 'version' => 1, 'follow_up_status' => 'completed'])->assertSessionHasNoErrors();
        $audit = WorkspaceActivity::latest('id')->firstOrFail();
        $this->assertSame($this->owner->id, $audit->actor_id);
        $this->assertSame(['before' => 'open', 'after' => 'completed'], $audit->changes['follow_up_status']);
        $this->assertArrayNotHasKey('recommendation', $audit->changes);
        $this->assertSame(2, $audit->version);
        $this->put(route('inspections.update', $draft), [...$data, 'version' => 1])->assertSessionHasErrors('version');
        $this->assertDatabaseCount('workspace_activities', 4);
        WorkspaceActivity::creating(fn () => throw new \RuntimeException('Audit write failed'));
        try {
            $this->withoutExceptionHandling()->put(route('inspections.update', $draft), [...$data, 'version' => 2, 'follow_up_status' => 'open']);
            $this->fail('Audit failure must abort the write.');
        } catch (\RuntimeException $e) {
            $this->assertSame('Audit write failed', $e->getMessage());
        } finally {
            WorkspaceActivity::flushEventListeners();
        }
        $this->assertSame(2, $draft->fresh()->version);
        $this->assertSame('completed', $draft->fresh()->follow_up_status);
        $this->assertDatabaseCount('workspace_activities', 4);
    }

    public function test_changed_readings_keep_analysis_and_require_explicit_review_of_current_evidence(): void
    {
        $this->travelTo(CarbonImmutable::parse('2026-11-08T01:00:00Z'));
        $measurement = $this->measurement(['readings' => ['field_c3' => ['value' => '10']]]);
        $this->post('/pdm', $measurement)->assertSessionHasNoErrors();
        $activity = PdmActivity::firstOrFail();
        $analysis = $this->analysis($activity);
        $this->post('/inspections', $analysis)->assertSessionHasNoErrors();
        $draft = InspectionDraft::firstOrFail();
        $this->assertNull($draft->pdmReviewState());
        $this->assertSame(1, $draft->pdmReviewedBasis()['version']);

        $corrected = [...$measurement, 'version' => 1, 'readings' => ['field_c3' => ['value' => '1']]];
        $this->put(route('pdm.update', $activity), $corrected)->assertSessionHasNoErrors();
        $audit = WorkspaceActivity::where('kind', 'pdm')->latest('id')->firstOrFail();
        $this->assertSame('10', json_decode($audit->changes['readings']['before'], true)['field_c3']['value']);
        $this->assertSame('1', json_decode($audit->changes['readings']['after'], true)['field_c3']['value']);
        $this->assertSame('stale', $draft->fresh()->pdmReviewState());
        $this->assertSame('TEST-FINDING', $draft->fresh()->finding);
        $this->assertSame('TEST-RECOMMENDATION', $draft->fresh()->recommendation);
        foreach ([route('pdm.show', $activity), route('inspections.show', $draft), '/pdm', '/inspections', '/action-board'] as $url) {
            $this->get($url)->assertOk()->assertSee('Analisis perlu ditinjau');
        }
        $this->get(route('pdm.show', $activity))->assertSee('Sebelum: 10')->assertSee('Sesudah: 1');
        $this->get(route('inspections.edit', $draft))->assertOk()->assertSee('name="pdm_version" value="2"', false)->assertSee('name="acknowledge_pdm_review"', false);

        // Saving a manual follow-up status is not an evidence review.
        $current = [...$analysis, 'version' => 1, 'pdm_version' => 2, 'follow_up_status' => 'completed'];
        $this->put(route('inspections.update', $draft), $current)->assertSessionHasNoErrors();
        $this->assertSame('stale', $draft->fresh()->pdmReviewState());
        $this->assertSame('completed', $draft->fresh()->follow_up_status);
        $this->put(route('inspections.update', $draft), [...$current, 'version' => 2, 'acknowledge_pdm_review' => '1'])->assertSessionHasNoErrors();
        $this->assertNull($draft->fresh()->pdmReviewState());
        $this->assertSame(2, $draft->fresh()->pdmReviewedBasis()['version']);
        $this->get(route('inspections.show', $draft))->assertOk()->assertDontSee('Analisis perlu ditinjau');

        // A no-op save does not change the evidence, even though the draft version advances.
        $this->put(route('pdm.update', $activity), [...$corrected, 'version' => 2])->assertSessionHasNoErrors();
        $this->assertNull($draft->fresh()->pdmReviewState());
        $this->put(route('pdm.update', $activity), [...$corrected, 'version' => 3, 'instrument' => 'Corrected instrument'])->assertSessionHasNoErrors();
        $this->assertSame('stale', $draft->fresh()->pdmReviewState());
        Http::assertNotSent(fn ($request) => $request->method() !== 'GET');
    }

    public function test_analysis_rejects_missing_or_outdated_measurement_versions_and_keeps_idempotency(): void
    {
        $measurement = $this->measurement();
        $this->post('/pdm', $measurement)->assertSessionHasNoErrors();
        $activity = PdmActivity::firstOrFail();
        $old = $this->analysis($activity);
        $missing = $old;
        unset($missing['pdm_version']);
        $this->post('/inspections', $missing)->assertSessionHasErrors('pdm_version');
        $this->put(route('pdm.update', $activity), [...$measurement, 'version' => 1, 'instrument' => 'New instrument'])->assertSessionHasNoErrors();
        $this->post('/inspections', $old)->assertSessionHasErrors('pdm_version');
        $this->assertDatabaseCount('inspection_drafts', 0);
        $current = [...$old, 'pdm_version' => 2];
        $this->post('/inspections', $current)->assertSessionHasNoErrors();
        $draft = InspectionDraft::firstOrFail();
        $this->put(route('pdm.update', $activity), [...$measurement, 'version' => 2, 'instrument' => 'Changed again'])->assertSessionHasNoErrors();
        $before = WorkspaceActivity::count();
        $this->from(route('inspections.edit', $draft))->put(route('inspections.update', $draft), [...$current, 'version' => 1, 'acknowledge_pdm_review' => '1'])->assertSessionHasErrors('pdm_version')->assertSessionHasInput('pdm_version', 2);
        $this->assertSame(1, $draft->fresh()->version);
        $this->assertSame($before, WorkspaceActivity::count());
        $this->post('/inspections', $current)->assertRedirect(route('inspections.show', $draft));
        $this->assertDatabaseCount('inspection_drafts', 1);
        $this->assertSame('stale', $draft->fresh()->pdmReviewState());
    }

    public function test_old_analysis_without_review_basis_is_unknown_until_explicitly_reviewed(): void
    {
        $this->post('/pdm', $this->measurement())->assertSessionHasNoErrors();
        $activity = PdmActivity::firstOrFail();
        $draft = InspectionDraft::create(['created_by' => $this->owner->id, 'pdm_activity_id' => $activity->id, 'asset_ref' => self::ASSET, 'request_reference' => 'LEGACY', 'request_summary' => 'Legacy analysis', 'inspection_type' => 'routine', 'finding' => 'Retained finding', 'recommendation' => 'Retained recommendation']);
        $this->assertSame('unknown', $draft->pdmReviewState());
        $this->get(route('inspections.show', $draft))->assertOk()->assertSee('Versi pengukuran yang mendasari analisis lama belum tercatat');
        $input = $this->analysis($activity, ['version' => 1, 'finding' => 'Retained finding', 'recommendation' => 'Retained recommendation']);
        $this->put(route('inspections.update', $draft), $input)->assertSessionHasNoErrors();
        $this->assertSame('unknown', $draft->fresh()->pdmReviewState());
        $this->put(route('inspections.update', $draft), [...$input, 'version' => 2, 'acknowledge_pdm_review' => '1'])->assertSessionHasNoErrors();
        $this->assertNull($draft->fresh()->pdmReviewState());
        $this->assertSame('Retained finding', $draft->fresh()->finding);
    }

    public function test_pdm_audit_failure_rolls_back_readings_and_version(): void
    {
        $measurement = $this->measurement(['readings' => ['field_c3' => ['value' => '10']]]);
        $this->post('/pdm', $measurement)->assertSessionHasNoErrors();
        $activity = PdmActivity::firstOrFail();
        WorkspaceActivity::creating(fn () => throw new \RuntimeException('Pdm audit failed'));
        try {
            $this->withoutExceptionHandling()->put(route('pdm.update', $activity), [...$measurement, 'version' => 1, 'readings' => ['field_c3' => ['value' => '1']]]);
            $this->fail('Audit failure must abort measurement corrections.');
        } catch (\RuntimeException $e) {
            $this->assertSame('Pdm audit failed', $e->getMessage());
        } finally {
            WorkspaceActivity::flushEventListeners();
        }
        $this->assertSame(1, $activity->fresh()->version);
        $this->assertSame('10', $activity->fresh()->readings['field_c3']['value']);
        $this->assertDatabaseCount('workspace_activities', 1);
    }

    public function test_pdm_corrections_and_linked_analysis_use_saved_identity_during_mart_outage(): void
    {
        $measurement = $this->measurement(['readings' => ['field_c3' => ['value' => '10']]]);
        $this->post('/pdm', $measurement)->assertSessionHasNoErrors();
        $activity = PdmActivity::firstOrFail();
        Http::swap(new Factory);
        Http::preventStrayRequests();
        Http::fake(['mart.test/*' => Http::response([], 503)]);

        // A new analysis of this exact saved measurement adds no new source identity.
        $analysis = $this->analysis($activity);
        $this->post('/inspections', $analysis)->assertSessionHasNoErrors();
        $draft = InspectionDraft::firstOrFail();
        $corrected = [...$measurement, 'version' => 1, 'readings' => ['field_c3' => ['value' => '1']]];
        $this->get(route('pdm.edit', $activity))->assertOk();
        $this->put(route('pdm.update', $activity), $corrected)->assertSessionHasNoErrors();
        $this->assertSame('1', $activity->fresh()->readings['field_c3']['value']);
        $this->assertSame('stale', $draft->fresh()->pdmReviewState());
        $this->put(route('pdm.update', $activity), $corrected)->assertSessionHasErrors('version');
        $this->put(route('inspections.update', $draft), [...$analysis, 'version' => 1, 'pdm_version' => 2, 'follow_up_status' => 'in_progress'])->assertSessionHasNoErrors();
        $this->assertSame('stale', $draft->fresh()->pdmReviewState());
        $this->put(route('inspections.update', $draft), [...$analysis, 'version' => 2, 'pdm_version' => 2, 'acknowledge_pdm_review' => '1'])->assertSessionHasNoErrors();
        $this->assertNull($draft->fresh()->pdmReviewState());
        Http::assertNothingSent();
        $audit = WorkspaceActivity::where('kind', 'pdm')->latest('id')->firstOrFail();
        $this->assertSame('10', json_decode($audit->changes['readings']['before'], true)['field_c3']['value']);
        $this->assertSame('1', json_decode($audit->changes['readings']['after'], true)['field_c3']['value']);

        // Offline editing does not authorize a different measurement identity or new record.
        $this->put(route('pdm.update', $activity), [...$corrected, 'version' => 2, 'asset_ref' => 'asset:OTHER'])->assertSessionHasErrors('asset_ref');
        Http::assertNothingSent();
        $this->post('/pdm', [...$measurement, 'request_key' => (string) Str::uuid()])->assertSessionHasErrors('asset_ref');
        $this->assertDatabaseCount('pdm_activities', 1);
        $this->assertDatabaseCount('inspection_drafts', 1);
        Http::assertNotSent(fn ($request) => $request->method() !== 'GET');
    }

    public function test_standalone_inspection_keeps_local_edits_available_but_requires_mart_for_new_identity(): void
    {
        $known = $this->requestData(['asset_ref' => self::ASSET]);
        $this->post('/inspections', $known)->assertSessionHasNoErrors();
        $draft = InspectionDraft::latest('id')->firstOrFail();
        $unbound = $this->requestData();
        $this->post('/inspections', $unbound)->assertSessionHasNoErrors();
        $unboundDraft = InspectionDraft::latest('id')->firstOrFail();
        $this->post('/inspections', $this->requestData(['asset_ref' => self::ASSET]))->assertSessionHasNoErrors();
        $reassignableDraft = InspectionDraft::latest('id')->firstOrFail();
        Http::swap(new Factory);
        Http::preventStrayRequests();
        Http::fake(['mart.test/*' => Http::response([], 503)]);

        $result = [...$known, 'version' => 1, 'method' => 'VISUAL', 'inspected_on' => '2026-01-01', 'finding' => 'Local observation', 'recommendation' => 'Local follow-up'];
        $this->put(route('inspections.update', $draft), $result)->assertSessionHasNoErrors();
        $this->put(route('inspections.update', $draft), [...$result, 'version' => 2, 'follow_up_status' => 'completed'])->assertSessionHasNoErrors();
        $this->assertSame('completed', $draft->fresh()->follow_up_status);
        $this->put(route('inspections.update', $draft), [...$result, 'version' => 1])->assertSessionHasErrors('version');
        Http::assertNothingSent();

        $url = route('inspections.edit', $unboundDraft);
        $this->from($url)->put(route('inspections.update', $unboundDraft), [...$result, 'version' => 1])->assertSessionHasErrors('asset_ref')->assertSessionHasInput('finding', 'Local observation');
        $this->assertNull($unboundDraft->fresh()->asset_ref);
        $this->put(route('inspections.update', $reassignableDraft), [...$known, 'version' => 1, 'asset_ref' => 'asset:NEW'])->assertSessionHasErrors('asset_ref');
        $this->assertSame(self::ASSET, $reassignableDraft->fresh()->asset_ref);
        $this->post('/inspections', [...$result, 'request_key' => (string) Str::uuid()])->assertSessionHasErrors('asset_ref');
        $this->assertDatabaseCount('inspection_drafts', 3);
        Http::assertNotSent(fn ($request) => $request->method() !== 'GET');
    }
}
