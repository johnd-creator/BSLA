<?php

namespace Tests\Feature;

use App\Models\AssetDisruption;
use App\Models\PdmActivity;
use App\Models\ReliabilityReview;
use App\Models\ReliabilitySnapshot;
use App\Models\User;
use App\Services\ReliabilityEvidence;
use App\Services\ReliabilityMart;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Str;
use Tests\TestCase;

class ReliabilityEvidenceTest extends TestCase
{
    use RefreshDatabase;

    private const ASSET = 'asset:MAXIMO:MXASSET:BSR:IP:RELIABILITY-QA';

    private const OTHER = 'asset:MAXIMO:MXASSET:BSR:IP:OTHER-QA';

    private User $owner;

    private AssetDisruption $event;

    private bool $outage = false;

    protected function setUp(): void
    {
        parent::setUp();
        $this->travelTo(now()->setDateTime(2026, 11, 8, 20, 0, 0));
        config(['services.reliability_mart.url' => 'http://mart.test']);
        Http::preventStrayRequests();
        Http::fake(function ($r) {
            if ($this->outage) {
                return Http::response([], 503);
            }
            if (str_contains($r->url(), 'annual-summary')) {
                return Http::response(['scope' => ['asset_ref' => $r['asset_ref'], 'population' => $r['population'], 'site_code' => 'BSR', 'organization_code' => 'IP', 'date_basis' => 'ACTUAL_START', 'time_zone' => 'Asia/Jakarta', 'count_basis' => 'UNIQUE_WORK_ORDER_ID'],
                    'availability_state' => 'REQUIRES_VALIDATED_DCS_HISTORY', 'counts' => ['record_count' => 2, 'work_order_count' => 2, 'dated_work_order_count' => 1, 'unknown_date_work_order_count' => 1, 'duplicate_work_order_count' => 0, 'duplicate_record_count' => 0, 'missing_identity_record_count' => 0],
                    'years' => [['year' => 2026, 'work_orders' => 1, 'work_types' => [['value' => 'CM', 'count' => 1]], 'statuses' => [['value' => 'CLOSE', 'count' => 1]]]], 'unknown_year' => ['year' => null, 'work_orders' => 1, 'work_types' => [['value' => null, 'count' => 1]], 'statuses' => [['value' => 'WAPPR', 'count' => 1]]]]);
            }
            if (str_contains($r->url(), '/assets/')) {
                return Http::response(['canonical_id' => rawurldecode(basename(parse_url($r->url(), PHP_URL_PATH))), 'site_code' => 'BSR', 'organization_code' => 'IP', 'registered' => false, 'hierarchy_category' => 'equipment', 'scope_basis' => 'DIRECT_SOURCE_UNIT', 'description' => 'Synthetic reliability asset']);
            }

            return Http::response([], 503);
        });
        $this->owner = $this->signIn();
        $this->event = $this->event();
    }

    private function signIn(string $role = 'ENGINEER'): User
    {
        $user = User::factory()->create(['roles' => [$role], 'active' => true])->refresh();
        $this->actingAs($user)->withSession(['auth_version' => $user->auth_version]);

        return $user;
    }

    private function event(array $extra = []): AssetDisruption
    {
        $event = AssetDisruption::create(array_replace(['created_by' => $this->owner->id, 'request_key' => (string) Str::uuid(), 'asset_ref' => self::ASSET, 'event_type' => 'trip', 'description' => 'Synthetic test observation', 'impact' => 'unknown', 'occurred_on' => '2026-02-01'], $extra));
        $event->members()->create(['asset_ref' => $event->asset_ref, 'role' => 'affected']);

        return $event;
    }

    private function payload(AssetDisruption $event, array $extra = []): array
    {
        return array_replace(['request_key' => (string) Str::uuid(), 'asset_ref' => self::ASSET, 'event_version' => $event->fresh()->version, 'previous_revision' => ReliabilityReview::where('asset_disruption_id', $event->id)->where('asset_ref', self::ASSET)->max('revision') ?? 0,
            'classification' => 'failure', 'required_function' => 'Deliver required process flow', 'evidence' => 'Engineer field report QA-1', 'reason' => 'Reviewed the recorded field evidence', 'repair_state' => 'unknown', 'attestation' => '1'], $extra);
    }

    private function review(AssetDisruption $event, array $extra = [])
    {
        return $this->post(route('reliability.reviews.store', $event), $this->payload($event, $extra));
    }

    private function complete(array $extra = []): array
    {
        return array_replace(['failure_at' => '2026-02-01T08:00:00+07:00', 'restored_at' => '2026-02-01T12:00:00+07:00', 'repair_state' => 'completed', 'active_intervals_text' => "2026-02-01T09:00:00+07:00 | 2026-02-01T10:00:00+07:00\n2026-02-01T11:00:00+07:00 | 2026-02-01T11:30:00+07:00", 'timing_evidence' => 'Operator log plus engineer work intervals; waiting excluded'], $extra);
    }

    private function report(int $year = 2026, string $asset = self::ASSET): array
    {
        return app(ReliabilityEvidence::class)->report($asset, $year, app(ReliabilityMart::class));
    }

    public function test_empty_data_is_not_zero_failures_or_calendar_exposure(): void
    {
        $r = $this->report(2025);
        $this->assertNull($r['metrics']['mtbf']['value']);
        $this->assertNull($r['coverage']['operating_seconds']);
        $this->assertNull($r['reviewed_samples']['mean_restoration']['value']);
        $this->assertContains('NO_LOCAL_OBSERVATIONS_IN_PERIOD', $r['blockers']);
        $this->assertSame(0, $r['work_orders']['selected_year']['work_orders']);
        $this->get(route('reliability.index', ['asset_ref' => self::ASSET]))->assertOk()->assertSee('Belum tersedia')->assertSee('Standby bukan rusak')->assertSee('Synthetic reliability asset');
    }

    public function test_review_is_separate_per_asset_and_does_not_promote_observation_or_wo(): void
    {
        $this->event->members()->create(['asset_ref' => self::OTHER, 'role' => 'cause']);
        $this->review($this->event)->assertSessionHasNoErrors();
        $this->assertSame('trip', $this->event->fresh()->event_type);
        $this->assertSame(1, $this->event->fresh()->version);
        $this->assertSame(1, $this->report()['quality']['failure']);
        $this->assertSame(1, $this->report(2026, self::OTHER)['quality']['unreviewed']);
        $this->assertNull($this->report()['metrics']['mttr']['value']);
        Http::assertNotSent(fn ($r) => $r->method() !== 'GET');
    }

    public function test_completed_active_work_and_restoration_use_different_denominators_and_waiting(): void
    {
        $this->review($this->event, $this->complete())->assertSessionHasNoErrors();
        $r = $this->report();
        $this->assertSame(1.5, $r['reviewed_samples']['mean_active_repair']['value']);
        $this->assertSame(5400, $r['reviewed_samples']['mean_active_repair']['numerator_seconds']);
        $this->assertSame(4.0, $r['reviewed_samples']['mean_restoration']['value']);
        $this->assertSame(1, $r['reviewed_samples']['mean_restoration']['denominator_completed_episodes']);
        foreach ($r['metrics'] as $metric) {
            $this->assertNull($metric['value']);
            $this->assertSame('NOT_READY', $metric['status']);
        }
    }

    public function test_zero_proven_duration_is_preserved_but_missing_is_null(): void
    {
        $this->review($this->event, $this->complete(['restored_at' => '2026-02-01T08:00:00+07:00', 'active_intervals_text' => '2026-02-01T08:00:00+07:00 | 2026-02-01T08:00:00+07:00']))->assertSessionHasNoErrors();
        $this->assertSame(0.0, $this->report()['reviewed_samples']['mean_active_repair']['value']);
        $this->assertSame(0.0, $this->report()['reviewed_samples']['mean_restoration']['value']);
    }

    public function test_ongoing_and_unknown_are_not_completed_or_zero(): void
    {
        $this->review($this->event, $this->complete(['restored_at' => null, 'repair_state' => 'ongoing']))->assertSessionHasNoErrors();
        $r = $this->report();
        $this->assertSame(1, $r['quality']['repair_ongoing']);
        $this->assertSame(1, $r['quality']['restoration_missing']);
        $this->assertNull($r['reviewed_samples']['mean_active_repair']['value']);
        $this->assertNull($r['reviewed_samples']['mean_restoration']['value']);
    }

    public function test_precise_repair_without_failure_time_is_retained_but_not_cohort_mean(): void
    {
        $this->review($this->event, $this->complete(['failure_at' => null, 'restored_at' => null]))->assertSessionHasNoErrors();
        $this->assertSame(1, $this->report()['quality']['missing_failure_time']);
        $this->assertNull($this->report()['reviewed_samples']['mean_active_repair']['value']);
    }

    public function test_bad_naive_date_only_future_and_reversed_timestamps_fail(): void
    {
        foreach (['2026-02-01', '2026-02-01T08:00:00', '2026-02-30T08:00:00+07:00', '2026-02-01T25:00:00+07:00', '2026-02-01T08:00:00+15:00', '2026-02-01T08:00:00+07:65', '2027-01-01T08:00:00Z'] as $bad) {
            $this->review($this->event, ['failure_at' => $bad, 'timing_evidence' => 'Test timing evidence'])->assertSessionHasErrors('failure_at');
        }
        $this->review($this->event, $this->complete(['restored_at' => '2026-02-01T07:00:00+07:00']))->assertSessionHasErrors('restored_at');
        $this->review($this->event, $this->complete(['failure_at' => null]))->assertSessionHasErrors('restored_at');
        $this->assertDatabaseCount('reliability_reviews', 0);
    }

    public function test_overlap_duplicate_intervals_and_outside_bounds_fail(): void
    {
        foreach (['2026-02-01T09:00:00Z | 2026-02-01T08:00:00Z', "2026-02-01T02:00:00Z | 2026-02-01T04:00:00Z\n2026-02-01T03:00:00Z | 2026-02-01T04:30:00Z", "2026-02-01T01:00:00Z | 2026-02-01T01:00:00Z\n2026-02-01T01:00:00Z | 2026-02-01T01:00:00Z", '2026-02-01T00:00:00Z | 2026-02-01T02:00:00Z', '2026-02-01T03:00:00Z | 2026-02-01T06:00:00Z'] as $bad) {
            $this->review($this->event, $this->complete(['active_intervals_text' => $bad]))->assertSessionHasErrors('active_intervals_text');
        }
        $this->assertDatabaseCount('reliability_reviews', 0);
    }

    public function test_required_evidence_attestation_function_and_state_consistency(): void
    {
        foreach (['evidence', 'reason', 'required_function', 'attestation'] as $field) {
            $this->review($this->event, [$field => ''])->assertSessionHasErrors($field);
        }
        $this->review($this->event, $this->complete(['timing_evidence' => '']))->assertSessionHasErrors('timing_evidence');
        $this->review($this->event, $this->complete(['repair_state' => 'unknown']))->assertSessionHasErrors('repair_state');
        $this->review($this->event, $this->complete(['active_intervals_text' => '']))->assertSessionHasErrors('repair_state');
        $this->review($this->event, $this->complete(['repair_state' => 'ongoing']))->assertSessionHasErrors('repair_state');
        $this->review($this->event, $this->complete(['classification' => 'not_failure']))->assertSessionHasErrors('classification');
    }

    public function test_owner_only_write_with_no_admin_bypass_and_all_roles_can_read(): void
    {
        foreach (['ADMIN', 'MANAGER', 'SUPERVISOR', 'ENGINEER'] as $role) {
            $this->signIn($role);
            $this->review($this->event)->assertForbidden();
            $this->get(route('reliability.reviews', $this->event))->assertOk()->assertDontSee('Simpan review lokal');
            $this->get(route('reliability.index', ['asset_ref' => self::ASSET]))->assertOk();
        }
        $this->assertDatabaseCount('reliability_reviews', 0);
    }

    public function test_repeated_submission_is_idempotent_and_stale_review_is_rejected(): void
    {
        $payload = $this->payload($this->event);
        $this->post(route('reliability.reviews.store', $this->event), $payload)->assertSessionHasNoErrors();
        $this->post(route('reliability.reviews.store', $this->event), $payload)->assertSessionHasNoErrors();
        $this->review($this->event, ['previous_revision' => 0])->assertSessionHasErrors('previous_revision');
        $this->review($this->event, ['classification' => 'uncertain', 'reason' => 'Further field evidence still needed'])->assertSessionHasNoErrors();
        $this->assertDatabaseCount('reliability_reviews', 2);
        $this->assertSame('failure', ReliabilityReview::oldest('id')->first()->classification);
        $this->assertSame(1, $this->report()['quality']['uncertain']);
    }

    public function test_observation_or_wo_version_change_invalidates_review(): void
    {
        $this->review($this->event, $this->complete())->assertSessionHasNoErrors();
        DB::table('asset_disruptions')->where('id', $this->event->id)->update(['version' => 2]);
        $r = $this->report();
        $this->assertSame(1, $r['quality']['stale']);
        $this->assertSame(0, $r['quality']['failure']);
        $this->assertNull($r['reviewed_samples']['mean_restoration']['value']);
        $this->review($this->event, ['event_version' => 1])->assertSessionHasErrors('event_version');
        $this->review($this->event)->assertSessionHasNoErrors();
        $this->assertSame(1, $this->report()['quality']['failure']);
    }

    public function test_cancelled_event_stays_in_audit_and_cannot_be_reviewed(): void
    {
        $this->review($this->event, $this->complete())->assertSessionHasNoErrors();
        $this->event->update(['status' => 'voided']);
        $this->review($this->event)->assertSessionHasErrors('event_version');
        $this->assertSame(1, $this->report()['quality']['voided']);
        $this->assertNull($this->report()['reviewed_samples']['mean_active_repair']['value']);
        $this->get(route('reliability.reviews', $this->event))->assertOk()->assertSee('Review 1')->assertDontSee('Simpan review lokal');
    }

    public function test_duplicate_has_exact_root_and_becomes_stale_after_root_review_change(): void
    {
        $duplicate = $this->event();
        $this->review($duplicate, ['classification' => 'duplicate', 'duplicate_of' => $this->event->id])->assertSessionHasErrors('duplicate_of');
        $this->review($this->event)->assertSessionHasNoErrors();
        $this->review($duplicate, ['classification' => 'duplicate', 'duplicate_of' => $this->event->id])->assertSessionHasNoErrors();
        $this->assertSame(1, $this->report()['quality']['duplicate']);
        $this->assertSame(1, $this->report()['quality']['failure']);
        $third = $this->event();
        $this->review($third, ['classification' => 'duplicate', 'duplicate_of' => $duplicate->id])->assertSessionHasErrors('duplicate_of');
        $this->review($this->event, ['classification' => 'not_failure'])->assertSessionHasNoErrors();
        $this->assertSame(1, $this->report()['quality']['stale']);
        $this->review($this->event, ['classification' => 'duplicate', 'duplicate_of' => $third->id])->assertSessionHasErrors('duplicate_of');
    }

    public function test_cross_asset_nonmember_and_cross_event_request_keys_fail(): void
    {
        $payload = $this->payload($this->event);
        $this->post(route('reliability.reviews.store', $this->event), $payload)->assertSessionHasNoErrors();
        $other = $this->event();
        $this->post(route('reliability.reviews.store', $other), $payload)->assertStatus(409);
        $this->review($this->event, ['asset_ref' => self::OTHER])->assertNotFound();
        $this->get(route('reliability.reviews', [$this->event, 'asset_ref' => self::OTHER]))->assertNotFound();
    }

    public function test_year_cohort_uses_jakarta_onset_not_observation_date_or_finish(): void
    {
        $this->review($this->event, $this->complete(['failure_at' => '2025-12-31T16:00:00Z', 'restored_at' => '2026-01-01T01:00:00Z', 'active_intervals_text' => '2025-12-31T17:00:00Z | 2025-12-31T18:00:00Z']))->assertSessionHasNoErrors();
        $old = $this->report(2025);
        $new = $this->report(2026);
        $this->assertSame(1, $old['quality']['failure']);
        $this->assertSame(1, $old['quality']['cross_year_restoration']);
        $this->assertSame(9.0, $old['reviewed_samples']['mean_restoration']['value']);
        $this->assertSame(0, $new['quality']['failure']);
        $this->assertNull($new['reviewed_samples']['mean_restoration']['value']);
    }

    public function test_boundary_second_at_jakarta_new_year_enters_new_cohort(): void
    {
        $this->review($this->event, ['failure_at' => '2025-12-31T17:00:00Z', 'timing_evidence' => 'Verified precise onset'])->assertSessionHasNoErrors();
        $this->assertSame(1, $this->report(2026)['quality']['failure']);
        $this->assertSame(0, $this->report(2025)['quality']['failure']);
    }

    public function test_unknown_date_and_date_only_are_separate_not_midnight(): void
    {
        $unknown = $this->event(['occurred_on' => null]);
        $this->review($unknown)->assertSessionHasNoErrors();
        $r = $this->report();
        $this->assertSame(1, $r['quality']['unknown_year']);
        $this->assertSame(1, $r['quality']['date_only']);
        $this->assertNull($r['events'][1]['failure_at']);
        $this->assertSame('OBSERVATION_LITERAL_DATE', $r['events'][0]['date_basis']);
    }

    public function test_overlapping_distinct_events_are_excluded_not_double_counted(): void
    {
        $this->review($this->event, $this->complete())->assertSessionHasNoErrors();
        $other = $this->event();
        $this->review($other, $this->complete())->assertSessionHasNoErrors();
        $r = $this->report();
        $this->assertSame(2, $r['quality']['conflicting_intervals']);
        $this->assertNull($r['reviewed_samples']['mean_restoration']['value']);
        $this->assertSame(2, $r['reviewed_samples']['mean_restoration']['excluded_overlap_episodes']);
    }

    public function test_overlap_with_prior_year_episode_is_also_excluded(): void
    {
        $this->review($this->event, $this->complete(['failure_at' => '2025-12-31T16:00:00Z']))->assertSessionHasNoErrors();
        $other = $this->event();
        $this->review($other, $this->complete())->assertSessionHasNoErrors();
        $r = $this->report();
        $this->assertSame(1, $r['quality']['failure']);
        $this->assertNull($r['reviewed_samples']['mean_restoration']['value']);
        $this->assertSame(1, $r['reviewed_samples']['mean_restoration']['excluded_overlap_episodes']);
    }

    public function test_source_outage_keeps_local_evidence_without_fabricating_wo_zero(): void
    {
        $this->review($this->event)->assertSessionHasNoErrors();
        $this->outage = true;
        $r = $this->report();
        $this->assertNull($r['work_orders']['selected_year']);
        $this->assertSame('UNAVAILABLE', $r['work_orders']['state']);
        $this->assertSame(1, $r['quality']['failure']);
        $this->get(route('reliability.index', ['asset_ref' => self::ASSET]))->assertOk()->assertSee('Identitas sumber belum tersedia');
    }

    public function test_snapshot_is_immutable_replay_safe_and_change_detected(): void
    {
        $this->review($this->event)->assertSessionHasNoErrors();
        $payload = ['request_key' => (string) Str::uuid(), 'asset_ref' => self::ASSET, 'year' => 2026];
        $this->post(route('reliability.snapshots.store'), $payload)->assertRedirect();
        $this->post(route('reliability.snapshots.store'), $payload)->assertRedirect();
        $snapshot = ReliabilitySnapshot::first();
        $this->assertDatabaseCount('reliability_snapshots', 1);
        $this->get(route('reliability.snapshots.show', $snapshot))->assertOk()->assertSee('Basis bukti saat ini sama');
        $this->review($this->event, ['classification' => 'not_failure'])->assertSessionHasNoErrors();
        $this->get(route('reliability.snapshots.show', $snapshot))->assertOk()->assertSee('Bukti atau ketersediaan sumber berubah');
        $this->assertSame('failure', $snapshot->fresh()->report['events'][0]['state']);
        $this->get(route('reliability.snapshots.download', $snapshot))->assertOk()->assertHeader('Content-Type', 'application/json; charset=UTF-8');
        $this->assertSame($snapshot->report, $this->get(route('reliability.snapshots.download', $snapshot))->json());
    }

    public function test_source_context_and_download_are_bounded_and_no_private_payload(): void
    {
        $r = $this->get(route('reliability.download', ['asset_ref' => self::ASSET, 'year' => 2026]))->assertOk()->assertHeader('Cache-Control', 'no-store, private')->json();
        $this->assertSame('ACTUAL_START', $r['work_orders']['date_basis']);
        $this->assertSame('UNKNOWN', $r['source_freshness']);
        $this->assertNull($r['metrics']['mtbf']['value']);
        $this->assertArrayNotHasKey('sources', $r['asset']);

    }

    public function test_invalid_filter_and_snapshot_roles_fail_closed(): void
    {
        foreach ([['asset_ref' => 'asset:OTHER'], ['asset_ref' => self::ASSET, 'year' => 2027], ['asset_ref' => self::ASSET, 'year' => 1800]] as $query) {
            $this->getJson(route('reliability.index', $query))->assertUnprocessable();
        }
        foreach (['ADMIN', 'MANAGER', 'SUPERVISOR'] as $role) {
            $this->signIn($role);
            $this->post(route('reliability.snapshots.store'), ['asset_ref' => self::ASSET, 'year' => 2026, 'request_key' => (string) Str::uuid()])->assertForbidden();
        }
    }

    public function test_review_insert_failure_rolls_back_without_changing_observation(): void
    {
        DB::statement("CREATE TRIGGER fail_review BEFORE INSERT ON reliability_reviews BEGIN SELECT RAISE(ABORT, 'test rollback'); END");
        $this->review($this->event)->assertStatus(500);
        $this->assertDatabaseCount('reliability_reviews', 0);
        $this->assertSame(1, $this->event->fresh()->version);
    }

    public function test_user_entered_evidence_is_escaped_in_review_and_report(): void
    {
        $this->review($this->event, ['evidence' => '<script>alert(1)</script>'])->assertSessionHasNoErrors();
        foreach ([route('reliability.reviews', $this->event), route('reliability.index', ['asset_ref' => self::ASSET])] as $url) {
            $this->get($url)->assertOk()->assertSee('&lt;script&gt;', false)->assertDontSee('<script>alert(1)</script>', false);
        }
    }

    public function test_wo_multiplicity_does_not_increase_event_denominator(): void
    {
        foreach (['1', '2'] as $number) {
            $this->event->workOrders()->create(['asset_ref' => self::ASSET, 'work_order_ref' => 'workorder:MAXIMO:MXWODETAIL:BSR:IP:'.$number, 'record_ref' => 'maintenance_event:'.$number, 'relation_state' => 'related', 'identity_checked_at' => now()]);
        }
        $this->review($this->event, $this->complete())->assertSessionHasNoErrors();
        $r = $this->report();
        $this->assertSame(2, count($r['events'][0]['work_orders']));
        $this->assertSame(1, $r['reviewed_samples']['mean_active_repair']['denominator_completed_episodes']);
        $this->assertSame(1, $r['quality']['failure']);
    }

    public function test_sample_denominator_excludes_unfinished_without_hiding_it(): void
    {
        $this->review($this->event, $this->complete())->assertSessionHasNoErrors();
        $unfinished = $this->event();
        $this->review($unfinished, ['failure_at' => '2026-03-01T01:00:00Z', 'repair_state' => 'ongoing', 'timing_evidence' => 'Still under repair at observation time'])->assertSessionHasNoErrors();
        $r = $this->report();
        $this->assertSame(2, $r['quality']['failure']);
        $this->assertSame(1, $r['quality']['repair_ongoing']);
        $this->assertSame(1, $r['quality']['restoration_missing']);
        $this->assertSame(1, $r['reviewed_samples']['mean_active_repair']['denominator_completed_episodes']);
        $this->assertSame(1.5, $r['reviewed_samples']['mean_active_repair']['value']);
        $this->assertContains('REPAIR_ONGOING', $r['blockers']);
    }

    public function test_interval_limit_and_nonfailure_duplicate_field_fail_closed(): void
    {
        $intervals = implode("\n", array_fill(0, 21, '2026-02-01T01:00:00Z | 2026-02-01T01:00:00Z'));
        $this->review($this->event, $this->complete(['active_intervals_text' => $intervals]))->assertSessionHasErrors('active_intervals_text');
        $this->review($this->event, ['duplicate_of' => $this->event->id])->assertSessionHasErrors('duplicate_of');
        $this->review($this->event, ['classification' => 'not_failure', 'repair_state' => 'not_applicable'])->assertSessionHasErrors('classification');
    }

    public function test_pdm_correction_changes_evidence_hash_without_becoming_failure(): void
    {
        $activity = PdmActivity::create(['created_by' => $this->owner->id, 'request_key' => (string) Str::uuid(), 'title' => 'Synthetic PdM', 'asset_ref' => self::ASSET, 'template_id' => 'qa', 'template_fingerprint' => str_repeat('a', 64), 'method' => 'VIBRATION', 'time_precision' => 'date', 'measured_on' => '2026-02-01', 'operating_condition' => 'Unknown', 'instrument' => 'QA', 'measurement_mode' => 'QA', 'asset_selection_note' => 'Exact synthetic identity', 'template_snapshot' => [], 'readings' => []]);
        $before = $this->report();
        $activity->forceFill(['version' => 2, 'notes' => 'Corrected observation'])->save();
        $after = $this->report();
        $this->assertSame(1, $after['pdm']['count']);
        $this->assertSame(1, $after['pdm']['date_only']);
        $this->assertNotSame($before['pdm']['evidence_hash'], $after['pdm']['evidence_hash']);
        $this->assertNotSame($before['evidence_hash'], $after['evidence_hash']);
        $this->assertSame(0, $after['quality']['failure']);
    }

    public function test_local_limit_is_explicit_and_withholds_all_sample_values(): void
    {
        $this->review($this->event, $this->complete())->assertSessionHasNoErrors();
        $prototype = $this->event->getAttributes();
        unset($prototype['id']);
        $rows = [];
        for ($i = 0; $i < ReliabilityEvidence::LIMIT; $i++) {
            $rows[] = [...$prototype, 'request_key' => (string) Str::uuid()];
        }
        foreach (array_chunk($rows, 100) as $chunk) {
            DB::table('asset_disruptions')->insert($chunk);
        }
        $members = AssetDisruption::where('id', '>', $this->event->id)->pluck('id')->map(fn ($id) => ['asset_disruption_id' => $id, 'asset_ref' => self::ASSET, 'role' => 'unknown'])->all();
        foreach (array_chunk($members, 100) as $chunk) {
            DB::table('asset_disruption_members')->insert($chunk);
        }
        $r = $this->report();
        $this->assertTrue($r['coverage']['local_rows_truncated']);
        $this->assertSame(ReliabilityEvidence::LIMIT, count($r['events']));
        $this->assertNull($r['reviewed_samples']['mean_active_repair']['value']);
        $this->assertNull($r['reviewed_samples']['mean_active_repair']['numerator_seconds']);
        $this->assertContains('LOCAL_EVIDENCE_LIMIT_REACHED', $r['blockers']);
    }

    public function test_unknown_offset_is_not_silently_treated_as_verified_utc(): void
    {
        $this->review($this->event, $this->complete(['failure_at' => '2026-02-01T01:00:00-00:00']))->assertSessionHasErrors('failure_at');
        $this->review($this->event, $this->complete(['restored_at' => '2026-02-01T05:00:00-00:00']))->assertSessionHasErrors('restored_at');
        $this->review($this->event, $this->complete(['active_intervals_text' => '2026-02-01T02:00:00-00:00 | 2026-02-01T03:00:00Z']))->assertSessionHasErrors('active_intervals_text');
        $this->assertDatabaseCount('reliability_reviews', 0);
        $this->review($this->event, $this->complete(['failure_at' => '2026-02-01T01:00:00Z', 'restored_at' => '2026-02-01T05:00:00+00:00']))->assertSessionHasNoErrors();
        $this->assertSame(4.0, $this->report()['reviewed_samples']['mean_restoration']['value']);
    }

    public function test_multi_asset_export_identifies_wo_owner_without_propagating_evidence(): void
    {
        $this->event->members()->create(['asset_ref' => self::OTHER, 'role' => 'affected']);
        $this->event->workOrders()->create(['asset_ref' => self::ASSET, 'work_order_ref' => 'workorder:MAXIMO:MXWODETAIL:BSR:IP:QA-MAIN', 'record_ref' => 'maintenance_event:QA-MAIN', 'relation_state' => 'related', 'identity_checked_at' => now()]);
        $main = $this->report();
        $affected = $this->report(2026, self::OTHER);
        $this->assertSame(self::ASSET, $affected['events'][0]['work_orders'][0]['asset_ref']);
        $this->assertFalse($affected['events'][0]['work_orders'][0]['matches_selected_asset']);
        $this->assertTrue($main['events'][0]['work_orders'][0]['matches_selected_asset']);
        $this->assertSame(0, $affected['quality']['failure']);
        $this->get(route('reliability.index', ['asset_ref' => self::OTHER]))->assertOk()->assertSee('0 WO aset ini · 1 WO aset lain dalam kejadian')->assertDontSee('kepemilikan aset tidak dicatat')->assertDontSee('@if', false);
        $this->get(route('reliability.index', ['asset_ref' => self::ASSET]))->assertOk()->assertSee('1 WO aset ini · 0 WO aset lain dalam kejadian');
    }

    public function test_legacy_snapshot_without_wo_asset_identity_does_not_guess_ownership(): void
    {
        $this->event->workOrders()->create(['asset_ref' => self::ASSET, 'work_order_ref' => 'workorder:MAXIMO:MXWODETAIL:BSR:IP:QA-OLD', 'record_ref' => 'maintenance_event:QA-OLD', 'relation_state' => 'related', 'identity_checked_at' => now()]);
        $report = $this->report();
        unset($report['events'][0]['work_orders'][0]['asset_ref'], $report['events'][0]['work_orders'][0]['matches_selected_asset']);
        $snapshot = ReliabilitySnapshot::create(['created_by' => $this->owner->id, 'request_key' => (string) Str::uuid(), 'asset_ref' => self::ASSET, 'year' => 2026, 'rule_version' => ReliabilityReview::RULE, 'evidence_hash' => $report['evidence_hash'], 'report' => $report, 'created_at' => now()]);
        $this->get(route('reliability.snapshots.show', $snapshot))->assertOk()->assertSee('0 WO aset ini · 0 WO aset lain dalam kejadian')->assertSee('1 kepemilikan aset tidak dicatat pada snapshot lama')->assertDontSee('@if', false);
        $this->assertArrayNotHasKey('asset_ref', $snapshot->fresh()->report['events'][0]['work_orders'][0]);
    }

    public function test_duplicate_root_with_old_rule_cannot_be_accepted_or_remain_current(): void
    {
        $this->review($this->event)->assertSessionHasNoErrors();
        $duplicate = $this->event();
        $this->review($duplicate, ['classification' => 'duplicate', 'duplicate_of' => $this->event->id])->assertSessionHasNoErrors();
        ReliabilityReview::where('asset_disruption_id', $this->event->id)->update(['rule_version' => 'superseded-rule']);
        $new = $this->event();
        $this->review($new, ['classification' => 'duplicate', 'duplicate_of' => $this->event->id])->assertSessionHasErrors('duplicate_of');
        $this->assertSame(0, $this->report()['quality']['duplicate']);
        $this->assertSame(2, $this->report()['quality']['stale']);
    }

    public function test_local_report_reads_use_one_transaction_and_release_it_afterwards(): void
    {
        $baseline = DB::connection()->transactionLevel();
        $levels = [];
        DB::listen(function ($query) use (&$levels) {
            if (str_starts_with(strtolower(ltrim($query->sql)), 'select')) {
                $levels[] = $query->connection->transactionLevel();
            }
        });
        $this->report();
        $this->assertNotEmpty($levels);
        $this->assertSame([$baseline + 1], array_values(array_unique($levels)));
        $this->assertSame($baseline, DB::connection()->transactionLevel());
    }
}
