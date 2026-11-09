<?php

namespace Tests\Feature;

use App\Models\ActionEffectivenessReview;
use App\Models\InspectionDraft;
use App\Models\PdmActivity;
use App\Models\User;
use App\Services\ActionEffectiveness;
use App\Services\PdmFormCatalog;
use App\Services\WorkspaceActivityLog;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Str;
use Tests\TestCase;

class ActionEffectivenessTest extends TestCase
{
    use RefreshDatabase;

    private User $owner;

    private InspectionDraft $inspection;

    private PdmActivity $before;

    private PdmActivity $after;

    protected function setUp(): void
    {
        parent::setUp();
        Http::preventStrayRequests();
        Http::fake();
        $this->owner = User::factory()->create(['roles' => ['ENGINEER'], 'active' => true])->refresh();
        $this->actingAs($this->owner)->withSession(['auth_version' => $this->owner->auth_version]);
        $this->inspection = InspectionDraft::create(['created_by' => $this->owner->id, 'asset_ref' => 'asset:QA:EFFECTIVENESS',
            'request_reference' => 'Synthetic QA', 'request_summary' => 'Synthetic recommendation', 'method' => 'VIBRATION',
            'inspected_on' => '2026-01-01', 'finding' => 'QA observation', 'recommendation' => 'QA follow-up', 'follow_up_status' => 'completed']);
        $catalog = app(PdmFormCatalog::class);
        $template = $catalog->snapshot($catalog->find('SYNTHETIC_MOTOR'));
        $attributes = ['created_by' => $this->owner->id, 'title' => 'Synthetic evidence only', 'asset_ref' => $this->inspection->asset_ref,
            'template_id' => 'SYNTHETIC_MOTOR', 'template_fingerprint' => $catalog->fingerprint($template), 'template_snapshot' => $template,
            'method' => $template['method'], 'time_precision' => 'date', 'measured_on' => '2026-01-01',
            'measurement_mode' => 'RMS', 'instrument' => 'QA instrument', 'operating_condition' => 'QA load',
            'asset_selection_note' => 'QA location only', 'readings' => ['field_c3' => ['value' => '10', 'unit' => 'mm/s']]];
        $this->before = PdmActivity::create([...$attributes, 'request_key' => (string) Str::uuid()]);
        $this->after = PdmActivity::create([...$attributes, 'request_key' => (string) Str::uuid(), 'measured_on' => '2026-01-03', 'readings' => ['field_c3' => ['value' => '0', 'unit' => 'mm/s']]]);
        $this->inspection->refresh();
        $this->before->refresh();
        $this->after->refresh();
    }

    private function data(array $changes = []): array
    {
        return array_replace(['request_key' => (string) Str::uuid(), 'inspection_version' => $this->inspection->version,
            'latest_review_id' => 0, 'before_id' => $this->before->id, 'after_id' => $this->after->id,
            'before_version' => $this->before->version, 'after_version' => $this->after->version,
            'action_taken' => 'Synthetic alignment check', 'completed_on' => '2026-01-02', 'point' => 'field_c3',
            'decision' => 'effective', 'reason' => 'Synthetic engineer criterion and review, not field approval', 'acknowledge_review' => 1], $changes);
    }

    private function url(): string
    {
        return route('inspections.effectiveness.store', $this->inspection);
    }

    public function test_completed_alone_is_unassessed_and_selected_evidence_has_no_source_calls(): void
    {
        $this->get($this->url())->assertOk()->assertSee('Efektivitas belum dinilai')->assertSee('Selesai bukan bukti efektif');
        $this->get($this->url().'?before_id='.$this->before->id.'&after_id='.$this->after->id)->assertOk()
            ->assertSee('Tanggal saja')->assertSee('QA instrument')->assertSee('0')->assertDontSee('2026-01-01 00:00');
        $this->assertDatabaseCount('action_effectiveness_reviews', 0);
        Http::assertNothingSent();
    }

    public function test_review_saves_exact_snapshot_zero_and_idempotent_submission_without_changing_status(): void
    {
        $data = $this->data();
        $this->post($this->url(), $data)->assertSessionHasNoErrors()->assertRedirect($this->url());
        $this->post($this->url(), $data)->assertSessionHasNoErrors();
        $this->assertDatabaseCount('action_effectiveness_reviews', 1);
        $review = ActionEffectivenessReview::firstOrFail();
        $this->assertSame('0', $review->evidence['after']['readings']['field_c3']['value']);
        $this->assertSame('10', $review->evidence['before']['readings']['field_c3']['value']);
        $this->assertSame('completed', $this->inspection->fresh()->follow_up_status);
        $this->assertSame('2026-01-02', $review->completed_on);
        $this->assertSame('effective', app(ActionEffectiveness::class)->state($review, $this->inspection));
        $this->assertNull($this->before->fresh()->measured_at);
        $this->get($this->url())->assertOk()->assertSee('Efektif menurut engineer')->assertSee('Review 1');
        Http::assertNothingSent();
    }

    public function test_missing_evidence_can_only_be_saved_as_inconclusive(): void
    {
        $missing = ['before_id' => null, 'after_id' => null, 'before_version' => null, 'after_version' => null, 'point' => null];
        foreach (['effective', 'needs_action'] as $decision) {
            $this->post($this->url(), $this->data([...$missing, 'decision' => $decision]))->assertSessionHasErrors('decision');
        }
        $this->post($this->url(), $this->data([...$missing, 'decision' => 'inconclusive']))->assertSessionHasNoErrors();
        $review = ActionEffectivenessReview::firstOrFail();
        $this->assertFalse($review->evidence['comparison']['valid']);
        $this->assertNull($review->evidence['before']);
        $this->get($this->url())->assertOk()->assertSee('Belum dapat dinilai');
    }

    public function test_values_are_not_imputed_or_units_converted(): void
    {
        foreach ([null, '', 'NaN', '1e999', 'text'] as $raw) {
            $this->after->update(['readings' => ['field_c3' => ['value' => $raw, 'unit' => 'mm/s']]]);
            $this->post($this->url(), $this->data())->assertSessionHasErrors('decision');
        }
        $this->after->update(['readings' => ['field_c3' => ['value' => '1000', 'unit' => 'µm']]]);
        $this->post($this->url(), $this->data())->assertSessionHasErrors('decision');
        $this->assertDatabaseCount('action_effectiveness_reviews', 0);
    }

    public function test_same_day_reversed_and_same_measurement_cannot_prove_effectiveness(): void
    {
        foreach ([['completed_on' => '2026-01-01'], ['completed_on' => '2026-01-03'], ['completed_on' => '2025-12-31'],
            ['before_id' => $this->after->id, 'after_id' => $this->before->id], ['after_id' => $this->before->id]] as $change) {
            $this->post($this->url(), $this->data($change))->assertSessionHasErrors('decision');
        }
        $this->assertDatabaseCount('action_effectiveness_reviews', 0);
    }

    public function test_asset_template_context_and_point_mismatches_are_rejected(): void
    {
        foreach (['template_id', 'template_fingerprint', 'method', 'measurement_mode', 'instrument', 'operating_condition', 'asset_selection_note'] as $key) {
            $original = $this->after->$key;
            foreach (['Different', ''] as $value) {
                $this->after->update([$key => $value]);
                $this->post($this->url(), $this->data())->assertSessionHasErrors('decision');
            }
            $this->after->update([$key => $original]);
        }
        $template = $this->after->template_snapshot;
        $changed = $template;
        $changed['fields'][0]['label'] = 'Changed identity despite same fingerprint';
        $this->after->update(['template_snapshot' => $changed]);
        $this->post($this->url(), $this->data())->assertSessionHasErrors('decision');
        $this->after->update(['template_snapshot' => $template]);
        $this->post($this->url(), $this->data(['point' => 'unrecognized']))->assertSessionHasErrors('decision');
        $this->after->update(['asset_ref' => 'asset:OTHER']);
        $this->post($this->url(), $this->data(['decision' => 'inconclusive']))->assertSessionHasErrors('after_id');
        $this->get($this->url().'?after_id='.$this->after->id)->assertStatus(422);
        $this->assertDatabaseCount('action_effectiveness_reviews', 0);
    }

    public function test_revisions_are_append_only_and_stale_tabs_cannot_overwrite(): void
    {
        $this->post($this->url(), $this->data())->assertSessionHasNoErrors();
        $first = ActionEffectivenessReview::firstOrFail();
        $this->post($this->url(), $this->data(['decision' => 'needs_action']))->assertSessionHasErrors('inspection_version');
        $this->post($this->url(), $this->data(['decision' => 'needs_action', 'latest_review_id' => $first->id]))->assertSessionHasNoErrors();
        $this->assertDatabaseCount('action_effectiveness_reviews', 2);
        $this->assertSame('effective', $first->fresh()->decision);
        $this->assertSame(2, ActionEffectivenessReview::latest('id')->first()->revision);
        $this->get($this->url())->assertOk()->assertSee('Perlu tindakan lagi')->assertSee('Review 1')->assertSee('Review 2');
        $this->delete($this->url())->assertStatus(405);
        $this->put($this->url(), $this->data())->assertStatus(405);
    }

    public function test_measurement_and_inspection_edits_invalidate_saved_judgment_without_rewriting_snapshot(): void
    {
        $this->post($this->url(), $this->data())->assertSessionHasNoErrors();
        $review = ActionEffectivenessReview::firstOrFail();
        $service = app(ActionEffectiveness::class);
        $this->after->update(['readings' => ['field_c3' => ['value' => '4', 'unit' => 'mm/s']]]);
        $this->assertSame('stale', $service->state($review->fresh(), $this->inspection));
        $this->assertSame('0', $review->fresh()->evidence['after']['readings']['field_c3']['value']);
        $this->get($this->url())->assertOk()->assertSee('Bukti berubah · tinjau ulang');
        $this->after->update(['readings' => ['field_c3' => ['value' => '0', 'unit' => 'mm/s']]]);
        $this->inspection->update(['recommendation' => 'Changed recommendation']);
        $this->assertSame('stale', $service->state($review->fresh(), $this->inspection->fresh()));
        $this->assertSame('QA follow-up', $review->fresh()->evidence['inspection']['record']['recommendation']);
    }

    public function test_noop_version_change_does_not_falsely_invalidate_but_template_change_does(): void
    {
        $this->post($this->url(), $this->data())->assertSessionHasNoErrors();
        $review = ActionEffectivenessReview::firstOrFail();
        $this->after->version++;
        $this->after->save();
        $this->assertSame('effective', app(ActionEffectiveness::class)->state($review->fresh(), $this->inspection));
        $snapshot = $this->after->template_snapshot;
        $snapshot['fields'][0]['unit'] = 'Different';
        $this->after->update(['template_snapshot' => $snapshot]);
        $this->assertSame('stale', app(ActionEffectiveness::class)->state($review->fresh(), $this->inspection));
    }

    public function test_stale_measurement_and_inspection_versions_are_rejected(): void
    {
        $data = $this->data();
        $this->after->version++;
        $this->after->save();
        $this->post($this->url(), $data)->assertSessionHasErrors('after_id');
        $this->inspection->version++;
        $this->inspection->save();
        $this->post($this->url(), $data)->assertSessionHasErrors('inspection_version');
        $this->assertDatabaseCount('action_effectiveness_reviews', 0);
    }

    public function test_readers_other_engineers_and_disabled_sessions_cannot_write(): void
    {
        foreach (['ADMIN', 'SUPERVISOR', 'MANAGER', 'ENGINEER'] as $role) {
            $other = User::factory()->create(['roles' => [$role], 'active' => true])->refresh();
            $this->actingAs($other)->withSession(['auth_version' => $other->auth_version]);
            $this->get($this->url())->assertOk()->assertDontSee('Simpan review baru');
            $this->post($this->url(), $this->data())->assertForbidden();
        }
        $this->owner->forceFill(['active' => false])->save();
        $this->actingAs($this->owner)->withSession(['auth_version' => $this->owner->auth_version]);
        $this->post($this->url(), $this->data())->assertRedirect(route('login'));
        $this->assertDatabaseCount('action_effectiveness_reviews', 0);
    }

    public function test_required_action_dates_reason_attestation_and_recommendation_are_enforced(): void
    {
        foreach (['action_taken', 'reason', 'acknowledge_review'] as $key) {
            $this->post($this->url(), $this->data([$key => null]))->assertSessionHasErrors($key);
        }
        foreach (['2026-02-30', now('Asia/Jakarta')->addDay()->toDateString()] as $date) {
            $this->post($this->url(), $this->data(['completed_on' => $date]))->assertSessionHasErrors('completed_on');
        }
        $this->inspection->update(['recommendation' => null]);
        $this->get($this->url())->assertNotFound();
        $this->post($this->url(), $this->data())->assertStatus(422);
        $this->assertDatabaseCount('action_effectiveness_reviews', 0);
    }

    public function test_saved_content_is_escaped_and_board_uses_latest_review_not_completed_status(): void
    {
        $this->post($this->url(), $this->data(['reason' => '<script>alert(1)</script>']))->assertSessionHasNoErrors();
        $this->get($this->url())->assertOk()->assertDontSee('<script>alert(1)</script>', false)->assertSee('&lt;script&gt;alert(1)&lt;/script&gt;', false);
        $this->get('/action-board')->assertOk()->assertSee('Efektif menurut engineer');
        $this->after->update(['readings' => ['field_c3' => ['value' => '2', 'unit' => 'mm/s']]]);
        $this->get('/action-board')->assertOk()->assertSee('Bukti berubah · tinjau ulang')->assertDontSee('Efektif menurut engineer');
    }

    public function test_linked_analysis_must_be_reviewed_and_later_source_changes_invalidate_effectiveness(): void
    {
        $this->inspection->update(['pdm_activity_id' => $this->before->id]);
        $this->post($this->url(), $this->data())->assertSessionHasErrors('decision');
        WorkspaceActivityLog::record($this->inspection->fresh(), $this->owner->id, [], ['pdm_basis' => ['before' => null, 'after' => $this->before->analysisBasis()]]);
        $this->post($this->url(), $this->data())->assertSessionHasNoErrors();
        $review = ActionEffectivenessReview::firstOrFail();
        $this->assertSame('effective', app(ActionEffectiveness::class)->state($review, $this->inspection->fresh()));
        $this->before->update(['readings' => ['field_c3' => ['value' => '11', 'unit' => 'mm/s']]]);
        $this->assertSame('stale', app(ActionEffectiveness::class)->state($review->fresh(), $this->inspection->fresh()));
        $this->get($this->url())->assertOk()->assertSee('Analisis perlu ditinjau');
        $this->post($this->url(), $this->data(['latest_review_id' => $review->id]))->assertSessionHasErrors('decision');
    }

    public function test_explicit_empty_selection_clears_saved_measurement_and_guests_cannot_read(): void
    {
        $this->post($this->url(), $this->data())->assertSessionHasNoErrors();
        $this->get($this->url().'?before_id=&after_id=')->assertOk()->assertViewHas('before', null)->assertViewHas('after', null);
        auth()->logout();
        $this->get($this->url())->assertRedirect(route('login'));
    }

    public function test_replay_token_cannot_be_reused_for_another_recommendation(): void
    {
        $data = $this->data();
        $this->post($this->url(), $data)->assertSessionHasNoErrors();
        $other = $this->inspection->replicate();
        $other->save();
        $this->post(route('inspections.effectiveness.store', $other), $data)->assertStatus(409);
        $this->assertDatabaseCount('action_effectiveness_reviews', 1);
    }
}
