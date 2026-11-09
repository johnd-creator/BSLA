<?php

namespace Tests\Feature;

use App\Models\AssetDisruption;
use App\Models\OperatingLog;
use App\Models\OperatingLogRevision;
use App\Models\ReliabilityApproval;
use App\Models\ReliabilityPolicy;
use App\Models\ReliabilityReview;
use App\Models\ReliabilitySnapshot;
use App\Models\User;
use App\Services\OperatingExposure;
use App\Services\ReliabilityCalculator;
use App\Services\ReliabilityEvidence;
use App\Services\ReliabilityMart;
use App\Services\ReviewedFailureTrends;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Http\Client\Factory;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Str;
use Tests\TestCase;

class OperatingReliabilityTest extends TestCase
{
    use RefreshDatabase;

    private const ASSET = 'asset:MAXIMO:MXASSET:BSR:IP:OPERATING-QA';

    private User $owner;

    protected function setUp(): void
    {
        parent::setUp();
        $this->travelTo(now()->setDateTime(2026, 11, 8, 20, 0, 0));
        config(['services.reliability_mart.url' => 'http://mart.test']);
        Http::preventStrayRequests();
        Http::fake(fn ($r) => str_contains($r->url(), '/assets/') && ! str_contains($r->url(), 'annual-summary') ? Http::response(['canonical_id' => rawurldecode(basename(parse_url($r->url(), PHP_URL_PATH))), 'site_code' => 'BSR', 'organization_code' => 'IP', 'registered' => false, 'scope_basis' => 'DIRECT_SOURCE_UNIT', 'hierarchy_category' => 'equipment', 'description' => 'Synthetic operating asset']) : Http::response([], 503));
        $this->owner = $this->signIn();
    }

    private function signIn(string $role = 'ENGINEER'): User
    {
        $user = User::factory()->create(['roles' => [$role], 'active' => true])->refresh();
        $this->actingAs($user)->withSession(['auth_version' => $user->auth_version]);

        return $user;
    }

    private function payload(array $extra = []): array
    {
        return array_replace(['request_key' => (string) Str::uuid(), 'asset_ref' => self::ASSET, 'version' => 0,
            'started_at' => '2025-01-01T00:00:00+07:00', 'ended_at' => '2025-01-01T02:00:00+07:00', 'state' => 'RUN', 'review_state' => 'verified',
            'source' => 'Synthetic shift log', 'evidence' => 'Synthetic source boundaries checked', 'reason' => 'Synthetic initial observation', 'attestation' => 1], $extra);
    }

    private function log(array $extra = []): OperatingLog
    {
        $this->post(route('reliability.operating.store'), $this->payload($extra))->assertSessionHasNoErrors()->assertRedirect();

        return OperatingLog::latest('id')->firstOrFail();
    }

    private function policy(array $extra = []): array
    {
        return array_replace(['asset_ref' => self::ASSET, 'year' => 2025, 'request_key' => (string) Str::uuid(), 'previous_revision' => 0,
            'status' => 'reviewed_local', 'required_function' => 'Deliver required flow', 'failure_definition' => 'Inability to deliver required flow',
            'exposure_basis' => 'run_only', 'recurrence_policy' => 'restored_before_recurrence', 'mttr_basis' => 'active_repair', 'minimum_coverage' => 100,
            'failure_scope' => 'attested_same_function', 'failure_coverage' => 'attested_complete', 'failure_coverage_evidence' => 'Synthetic reconciled complete local census', 'incomplete_policy' => 'withhold',
            'evidence' => 'Synthetic local method reference', 'reason' => 'Synthetic method selection', 'attestation' => 1], $extra);
    }

    private function failure(array $extra = []): AssetDisruption
    {
        $event = AssetDisruption::create(['created_by' => $this->owner->id, 'request_key' => (string) Str::uuid(), 'asset_ref' => self::ASSET, 'event_type' => 'trip', 'description' => 'Synthetic failure', 'impact' => 'unknown', 'occurred_on' => '2025-01-02']);
        $event->members()->create(['asset_ref' => self::ASSET, 'role' => 'affected']);
        ReliabilityReview::create(array_replace(['asset_disruption_id' => $event->id, 'asset_ref' => self::ASSET, 'revision' => 1, 'event_version' => 1,
            'created_by' => $this->owner->id, 'request_key' => (string) Str::uuid(), 'classification' => 'failure', 'required_function' => 'Deliver required flow',
            'evidence' => 'Synthetic field evidence', 'reason' => 'Synthetic review', 'failure_at' => '2025-01-02 01:00:00', 'restored_at' => '2025-01-02 03:00:00',
            'repair_state' => 'completed', 'active_intervals' => [['start' => '2025-01-02T01:30:00+00:00', 'end' => '2025-01-02T02:30:00+00:00', 'seconds' => 3600]],
            'timing_evidence' => 'Synthetic interval report', 'rule_version' => ReliabilityReview::RULE, 'event_snapshot' => $event->snapshot(), 'created_at' => now()], $extra));

        return $event;
    }

    private function report(int $year = 2025): array
    {
        return app(ReliabilityEvidence::class)->report(self::ASSET, $year, app(ReliabilityMart::class));
    }

    public function test_create_review_correction_and_void_preserve_audit_and_hash(): void
    {
        $log = $this->log(['review_state' => 'draft']);
        $initial = $this->report();
        $this->assertNull($initial['coverage']['operating_seconds']);
        $data = $this->payload(['version' => 1]);
        $this->put(route('reliability.operating.update', $log), $data)->assertSessionHasNoErrors();
        $verified = $this->report();
        $this->assertSame(7200, $verified['coverage']['operating_seconds']);
        $this->assertNotSame($initial['evidence_hash'], $verified['evidence_hash']);
        $this->put(route('reliability.operating.update', $log), $data)->assertRedirect();
        $this->assertSame(2, $log->fresh()->version);
        $this->put(route('reliability.operating.update', $log), $this->payload(['version' => 2, 'review_state' => 'voided']))->assertSessionHasNoErrors();
        $this->assertNull($this->report()['coverage']['operating_seconds']);
        $this->assertSame(3, $log->revisions()->count());
        $this->get(route('reliability.operating.show', $log))->assertOk()->assertSee('Revisi 1')->assertSee('Revisi 3');
    }

    public function test_idempotency_and_stale_form_and_cross_asset_keys(): void
    {
        $data = $this->payload();
        $this->post(route('reliability.operating.store'), $data)->assertSessionHasNoErrors();
        $this->post(route('reliability.operating.store'), $data)->assertRedirect();
        $this->assertSame(1, OperatingLog::count());
        $this->post(route('reliability.operating.store'), [...$data, 'asset_ref' => self::ASSET.'-OTHER'])->assertConflict();
        $log = OperatingLog::first();
        $this->put(route('reliability.operating.update', $log), $this->payload(['version' => 0]))->assertSessionHasErrors('version');
        $this->assertSame(1, $log->fresh()->version);
    }

    public function test_request_completed_during_identity_check_is_replayed_inside_write_transaction(): void
    {
        foreach ([self::ASSET, self::ASSET.'-OTHER'] as $winnerAsset) {
            $payload = $this->payload();
            $winner = null;
            Http::swap(new Factory);
            Http::preventStrayRequests();
            Http::fake(function () use ($payload, $winnerAsset, &$winner) {
                $winner = OperatingLog::create(['asset_ref' => $winnerAsset, 'created_by' => $this->owner->id, 'version' => 1]);
                $winner->revisions()->create(['revision' => 1, 'created_by' => $this->owner->id, 'request_key' => $payload['request_key'],
                    'started_at' => $payload['started_at'], 'ended_at' => $payload['ended_at'], 'state' => 'RUN', 'review_state' => 'verified',
                    'source' => 'Synthetic concurrent winner', 'evidence' => 'Synthetic boundary evidence', 'reason' => 'Synthetic concurrent save', 'created_at' => now()]);

                return Http::response(['canonical_id' => self::ASSET, 'site_code' => 'BSR', 'organization_code' => 'IP', 'registered' => false,
                    'scope_basis' => 'DIRECT_SOURCE_UNIT', 'hierarchy_category' => 'equipment', 'description' => 'Synthetic operating asset']);
            });
            $count = OperatingLog::count();
            $response = $this->post(route('reliability.operating.store'), $payload);
            if ($winnerAsset === self::ASSET) {
                $response->assertSessionHasNoErrors()->assertRedirect(route('reliability.operating.show', $winner));
            } else {
                $response->assertConflict();
            }
            $this->assertSame($count + 1, OperatingLog::count());
            $this->assertSame(1, OperatingLogRevision::where('request_key', $payload['request_key'])->count());
        }
    }

    public function test_invalid_future_unknown_offset_date_only_reversed_zero_and_unattested_times_are_rejected(): void
    {
        foreach (['2025-01-01', '2025-01-01T00:00:00', '2025-01-01T00:00:00-00:00', '2025-02-30T00:00:00+07:00', '2030-01-01T00:00:00+07:00'] as $bad) {
            $this->post(route('reliability.operating.store'), $this->payload(['started_at' => $bad]))->assertSessionHasErrors('started_at');
        }
        foreach (['2024-01-01T00:00:00+07:00', '2025-01-01T00:00:00+07:00'] as $bad) {
            $this->post(route('reliability.operating.store'), $this->payload(['ended_at' => $bad]))->assertSessionHasErrors('ended_at');
        }
        $this->post(route('reliability.operating.store'), $this->payload(['attestation' => 0]))->assertSessionHasErrors('attestation');
        $this->assertSame(0, OperatingLog::count());
    }

    public function test_roles_and_other_engineer_cannot_mutate(): void
    {
        $log = $this->log();
        foreach (['ADMIN', 'SUPERVISOR', 'MANAGER', 'ENGINEER'] as $role) {
            $this->signIn($role);
            $this->get(route('reliability.operating.show', $log))->assertOk()->assertDontSee('Koreksi / periksa / batalkan');
            $this->get(route('reliability.operating.edit', $log))->assertForbidden();
            $this->put(route('reliability.operating.update', $log), $this->payload(['version' => 1]))->assertForbidden();
            if ($role !== 'ENGINEER') {
                $this->post(route('reliability.operating.store'), $this->payload())->assertForbidden();
                $this->post(route('reliability.policies.store'), $this->policy())->assertForbidden();
            }
        }
    }

    public function test_interval_sweep_excludes_overlap_unknown_and_drafts_without_double_counting(): void
    {
        $this->log(); // RUN 00-02
        $this->log(['started_at' => '2025-01-01T01:00:00+07:00', 'ended_at' => '2025-01-01T03:00:00+07:00', 'state' => 'STOP']);
        $this->log(['started_at' => '2025-01-01T03:00:00+07:00', 'ended_at' => '2025-01-01T04:00:00+07:00', 'state' => 'STANDBY']);
        $this->log(['started_at' => '2025-01-01T04:00:00+07:00', 'ended_at' => '2025-01-01T05:00:00+07:00', 'state' => 'UNKNOWN']);
        $this->log(['started_at' => '2025-01-01T05:00:00+07:00', 'ended_at' => '2025-01-01T06:00:00+07:00', 'review_state' => 'draft']);
        $r = app(OperatingExposure::class)->report(self::ASSET, 2025);
        foreach (['RUN', 'STOP', 'STANDBY', 'UNKNOWN', 'OVERLAP'] as $state) {
            $this->assertSame(3600, $r['seconds'][$state]);
        }
        $this->assertSame(10800, $r['known_seconds']);
        $this->assertSame(365 * 86400, array_sum($r['seconds']));
        $this->assertSame(1, $r['quality']['draft']);
        $this->assertSame('NOT_AVAILABLE', app(OperatingExposure::class)->report(self::ASSET.'-OTHER', 2025)['status']);
    }

    public function test_equal_state_overlap_is_conflict_and_adjacent_edges_are_not(): void
    {
        $this->log();
        $this->log();
        $this->log(['started_at' => '2025-01-01T02:00:00+07:00', 'ended_at' => '2025-01-01T03:00:00+07:00']);
        $r = app(OperatingExposure::class)->report(self::ASSET, 2025);
        $this->assertSame(7200, $r['seconds']['OVERLAP']);
        $this->assertSame(3600, $r['seconds']['RUN']);
    }

    public function test_cross_year_clipping_and_leap_year_denominator(): void
    {
        $this->log(['started_at' => '2024-12-31T23:00:00+07:00', 'ended_at' => '2025-01-01T01:00:00+07:00']);
        $a = app(OperatingExposure::class)->report(self::ASSET, 2024);
        $b = app(OperatingExposure::class)->report(self::ASSET, 2025);
        $this->assertSame(3600, $a['seconds']['RUN']);
        $this->assertSame(3600, $b['seconds']['RUN']);
        $this->assertSame(366 * 86400, $a['period_seconds']);
    }

    public function test_policies_are_append_only_scoped_and_do_not_approve_organization(): void
    {
        $before = $this->report();
        $data = $this->policy();
        $this->post(route('reliability.policies.store'), $data)->assertSessionHasNoErrors();
        $this->post(route('reliability.policies.store'), $data)->assertRedirect();
        $this->assertSame(1, ReliabilityPolicy::count());
        $this->post(route('reliability.policies.store'), $this->policy(['previous_revision' => 1, 'mttr_basis' => 'restoration']))->assertSessionHasNoErrors();
        $this->post(route('reliability.policies.store'), $this->policy())->assertSessionHasErrors('previous_revision');
        $this->assertSame('active_repair', ReliabilityPolicy::first()->rules['mttr_basis']);
        $r = $this->report();
        $this->assertSame(2, $r['readiness']['policy']['revision']);
        $this->assertSame('SEPARATE_SUPERVISOR_DECISION', $r['readiness']['policy']['rules']['organization_approval']);
        $this->assertNotSame($before['evidence_hash'], $r['evidence_hash']);
        $this->assertNull($this->report(2026)['readiness']['policy']);
        $this->signIn();
        $this->post(route('reliability.policies.store'), $this->policy(['previous_revision' => 2]))->assertForbidden();
    }

    public function test_undecided_policy_and_census_without_evidence_stay_insufficient(): void
    {
        $this->post(route('reliability.policies.store'), $this->policy(['failure_coverage_evidence' => '']))->assertSessionHasErrors('failure_coverage_evidence');
        $this->post(route('reliability.policies.store'), $this->policy(['status' => 'draft', 'minimum_coverage' => null, 'failure_coverage' => 'unknown', 'required_function' => null, 'mttr_basis' => 'undecided']))->assertSessionHasNoErrors();
        $r = $this->report();
        $this->assertContains('LOCAL_METHOD_NOT_REVIEWED', $r['readiness']['mttr']['blockers']);
        $this->assertContains('REQUIRED_FUNCTION_UNDECIDED', $r['readiness']['mttr']['blockers']);
        $this->assertContains('MINIMUM_OPERATING_COVERAGE_UNDECIDED', $r['readiness']['mtbf']['blockers']);
    }

    public function test_mttr_can_be_locally_ready_without_operating_logs_historian_or_wo_source(): void
    {
        $this->failure();
        $this->post(route('reliability.policies.store'), $this->policy())->assertSessionHasNoErrors();
        $r = $this->report();
        $this->assertSame('LOCAL_EVIDENCE_READY', $r['readiness']['mttr']['status']);
        $this->assertSame('ATTESTED_LOCAL', $r['coverage']['observation_coverage']);
        $this->assertFalse($r['readiness']['mttr']['operating_exposure_required']);
        $this->assertSame('INSUFFICIENT_LOCAL_EVIDENCE', $r['readiness']['mtbf']['status']);
        $this->assertSame('UNAVAILABLE', $r['work_orders']['state']);
        $this->assertSame(1.0, $r['reviewed_samples']['mean_active_repair']['value']);
        $this->assertSame(2.0, $r['reviewed_samples']['mean_restoration']['value']);
        $this->assertNull($r['metrics']['mttr']['value']);
    }

    public function test_active_and_restoration_have_independent_readiness(): void
    {
        $this->failure(['repair_state' => 'not_applicable', 'active_intervals' => []]);
        $this->post(route('reliability.policies.store'), $this->policy(['mttr_basis' => 'restoration']))->assertSessionHasNoErrors();
        $r = $this->report();
        $this->assertSame('LOCAL_EVIDENCE_READY', $r['readiness']['mttr']['status']);
        $this->assertSame('INSUFFICIENT_LOCAL_EVIDENCE', $r['readiness']['active_repair']['status']);
        $this->assertNull($r['reviewed_samples']['mean_active_repair']['value']);
        $this->assertSame(2.0, $r['reviewed_samples']['mean_restoration']['value']);
    }

    public function test_open_previous_episode_blocks_recurrence_even_without_overlap_intervals(): void
    {
        $this->failure(['failure_at' => '2024-12-31 01:00:00', 'restored_at' => null, 'repair_state' => 'ongoing', 'active_intervals' => []]);
        $this->failure();
        $this->post(route('reliability.policies.store'), $this->policy())->assertSessionHasNoErrors();
        $this->assertContains('RECURRENCE_NOT_ESTABLISHED', $this->report()['readiness']['mttr']['blockers']);
    }

    public function test_zero_failure_never_yields_zero_or_infinite_mtbf_and_state_coverage_is_not_census(): void
    {
        $this->log(['ended_at' => '2026-01-01T00:00:00+07:00']);
        $this->post(route('reliability.policies.store'), $this->policy(['failure_coverage' => 'unknown']))->assertSessionHasNoErrors();
        $r = $this->report();
        $this->assertSame(100.0, $r['coverage']['coverage_percent']);
        $this->assertContains('FAILURE_OBSERVATION_COVERAGE_UNKNOWN', $r['readiness']['mtbf']['blockers']);
        $this->assertContains('NO_REVIEWED_FAILURES', $r['readiness']['mtbf']['blockers']);
        $this->assertNull($r['metrics']['mtbf']['value']);
    }

    public function test_full_exposure_is_ready_only_with_matching_failure_evidence_and_no_gap(): void
    {
        $this->failure();
        $this->log(['ended_at' => '2026-01-01T00:00:00+07:00']);
        $this->post(route('reliability.policies.store'), $this->policy())->assertSessionHasNoErrors();
        $this->assertSame('LOCAL_EVIDENCE_READY', $this->report()['readiness']['mtbf']['status']);
        $this->log(['started_at' => '2025-01-02T07:00:00+07:00', 'ended_at' => '2025-01-02T09:00:00+07:00', 'state' => 'STOP']);
        $r = $this->report();
        $this->assertContains('OPERATING_OVERLAP', $r['readiness']['mtbf']['blockers']);
        $this->assertContains('FAILURE_OUTSIDE_VERIFIED_EXPOSURE', $r['readiness']['mtbf']['blockers']);
        $this->assertSame('LOCAL_EVIDENCE_READY', $r['readiness']['mttr']['status']);
    }

    public function test_trends_exclude_unreviewed_stale_duplicates_and_unknown_onset(): void
    {
        $this->failure();
        $stale = $this->failure();
        $stale->increment('version');
        $this->failure(['classification' => 'not_failure', 'failure_at' => null, 'restored_at' => null, 'repair_state' => 'unknown', 'active_intervals' => []]);
        $this->failure(['failure_at' => null, 'restored_at' => null, 'repair_state' => 'unknown', 'active_intervals' => []]);
        $r = $this->report();
        $this->assertSame(1, $r['trends']['reviewed_count']);
        $this->assertSame(1, $r['trends']['monthly_counts'][1]);
        $this->assertSame(1, $r['trends']['excluded_missing_onset']);
        $this->assertSame(100.0, $r['trends']['pareto'][0]['cumulative_percent']);
        $this->assertArrayHasKey('review_rule_version', $r['events'][0]);
    }

    public function test_new_evidence_makes_scope_attestation_stale_without_mutating_policy(): void
    {
        $this->failure();
        $this->post(route('reliability.policies.store'), $this->policy())->assertSessionHasNoErrors();
        $this->assertSame('LOCAL_EVIDENCE_READY', $this->report()['readiness']['mttr']['status']);
        $rules = ReliabilityPolicy::first()->rules;
        $this->failure(['failure_at' => '2025-01-03 01:00:00', 'restored_at' => '2025-01-03 02:00:00', 'active_intervals' => [['start' => '2025-01-03T01:00:00+00:00', 'end' => '2025-01-03T02:00:00+00:00', 'seconds' => 3600]]]);
        $this->assertContains('FAILURE_SCOPE_ATTESTATION_STALE', $this->report()['readiness']['mttr']['blockers']);
        $this->assertSame('STALE', $this->report()['coverage']['observation_coverage']);
        $this->assertSame($rules, ReliabilityPolicy::first()->rules);
    }

    public function test_outage_blocks_new_identity_but_preserves_existing_local_correction(): void
    {
        $log = $this->log();
        Http::swap(new Factory);
        Http::preventStrayRequests();
        Http::fake(fn () => Http::response([], 503));
        $this->post(route('reliability.operating.store'), $this->payload())->assertSessionHasErrors('asset_ref');
        $this->put(route('reliability.operating.update', $log), $this->payload(['version' => 1, 'state' => 'STOP']))->assertSessionHasNoErrors();
        $this->post(route('reliability.policies.store'), $this->policy())->assertSessionHasErrors('asset_ref');
        $this->assertSame(1, OperatingLog::count());
        $this->assertSame(2, $log->revisions()->count());
    }

    public function test_unknown_only_exposure_is_not_zero_runtime(): void
    {
        $this->log(['state' => 'UNKNOWN']);
        $r = app(OperatingExposure::class)->report(self::ASSET, 2025);
        $this->assertNull($r['operating_seconds']);
        $this->assertSame(0.0, $r['coverage_percent']);
        $this->assertSame(7200, $r['seconds']['UNKNOWN']);
    }

    public function test_failed_revision_rolls_back_new_log_atomically(): void
    {
        OperatingLogRevision::creating(fn () => throw new \RuntimeException('Synthetic failure'));
        $this->withoutExceptionHandling();
        try {
            $this->post(route('reliability.operating.store'), $this->payload());
            $this->fail('Expected synthetic failure');
        } catch (\RuntimeException $error) {
            $this->assertSame('Synthetic failure', $error->getMessage());
        } finally {
            OperatingLogRevision::flushEventListeners();
        }
        $this->assertSame(0, OperatingLog::count());
        $this->assertSame(0, OperatingLogRevision::count());
    }

    public function test_operating_limit_withholds_values_instead_of_claiming_complete_coverage(): void
    {
        $rows = [];
        for ($i = 1; $i <= OperatingExposure::LIMIT + 1; $i++) {
            $rows[] = ['id' => $i, 'asset_ref' => self::ASSET, 'created_by' => $this->owner->id, 'version' => 1, 'created_at' => now(), 'updated_at' => now()];
        }
        foreach (array_chunk($rows, 200) as $chunk) {
            OperatingLog::insert($chunk);
        }
        $r = app(OperatingExposure::class)->report(self::ASSET, 2025);
        $this->assertTrue($r['truncated']);
        $this->assertSame('PARTIAL', $r['status']);
        $this->assertNull($r['operating_seconds']);
        $this->assertNull($r['coverage_percent']);
    }

    public function test_census_attested_before_year_end_does_not_auto_cover_later_exposure(): void
    {
        $this->failure();
        $this->travelTo(now()->setDateTime(2025, 12, 30, 12, 0, 0));
        $this->post(route('reliability.policies.store'), $this->policy())->assertSessionHasNoErrors();
        $this->travelTo(now()->setDateTime(2026, 11, 8, 20, 0, 0));
        $this->log(['ended_at' => '2026-01-01T00:00:00+07:00']);
        $r = $this->report();
        $this->assertContains('FAILURE_CENSUS_DOES_NOT_COVER_FULL_YEAR', $r['readiness']['mtbf']['blockers']);
        $this->assertSame('LOCAL_EVIDENCE_READY', $r['readiness']['mttr']['status']);
    }

    public function test_calculator_reconciles_mtbf_and_two_independent_mttr_numerators(): void
    {
        $this->failure();
        $this->failure(['failure_at' => '2025-02-02 01:00:00', 'restored_at' => '2025-02-02 05:00:00', 'active_intervals' => [['start' => '2025-02-02T02:00:00+00:00', 'end' => '2025-02-02T04:00:00+00:00', 'seconds' => 7200]]]);
        foreach ([['2025-01-01T00:00:00+07:00', '2025-01-02T08:00:00+07:00', 'RUN'], ['2025-01-02T08:00:00+07:00', '2025-01-02T10:00:00+07:00', 'STOP'], ['2025-01-02T10:00:00+07:00', '2025-02-02T08:00:00+07:00', 'RUN'], ['2025-02-02T08:00:00+07:00', '2025-02-02T12:00:00+07:00', 'STOP'], ['2025-02-02T12:00:00+07:00', '2026-01-01T00:00:00+07:00', 'RUN']] as [$start, $end, $state]) {
            $this->log(['started_at' => $start, 'ended_at' => $end, 'state' => $state]);
        }
        $this->post(route('reliability.policies.store'), $this->policy())->assertSessionHasNoErrors();
        $r = $this->report();
        $c = $r['calculation'];
        $this->assertSame(4377.0, $c['pilot']['mtbf']['value']);
        $this->assertSame(8754 * 3600, $c['pilot']['mtbf']['numerator_seconds']);
        $this->assertSame(2, $c['pilot']['mtbf']['denominator_episodes']);
        $this->assertSame(1.5, $c['pilot']['mttr']['value']);
        $this->assertSame(3.0, $c['pilot']['restoration']['value']);
        $this->assertSame('PILOT_CALCULATED', $c['pilot']['mttr']['status']);
        $this->assertNull($c['official']['mttr']['value']);
        $this->assertTrue($c['official']['mtbf']['data_ready']);
        $this->assertSame($c, app(ReliabilityCalculator::class)->calculate($r));
        $this->assertSame(5, count($c['exposure_trace']));
    }

    public function test_calculator_missing_policy_differs_from_descriptive_complete_sample(): void
    {
        $this->failure();
        $r = $this->report();
        $this->assertSame(1.0, $r['reviewed_samples']['mean_active_repair']['value']);
        $this->assertNull($r['calculation']['pilot']['mttr']['value']);
        $this->assertContains('MTTR_BASIS_UNDECIDED', $r['calculation']['pilot']['mttr']['blockers']);
        $this->assertNull($r['calculation']['pilot']['mtbf']['numerator_seconds']);
    }

    public function test_calculator_mttr_does_not_need_operating_data_and_zero_is_explicit(): void
    {
        $this->failure(['restored_at' => '2025-01-02 01:00:00', 'active_intervals' => [['start' => '2025-01-02T01:00:00+00:00', 'end' => '2025-01-02T01:00:00+00:00', 'seconds' => 0]]]);
        $this->post(route('reliability.policies.store'), $this->policy())->assertSessionHasNoErrors();
        $c = $this->report()['calculation'];
        $this->assertSame(0.0, $c['pilot']['mttr']['value']);
        $this->assertSame(0, $c['pilot']['mttr']['numerator_seconds']);
        $this->assertSame(1, $c['pilot']['mttr']['denominator_episodes']);
        $this->assertNull($c['pilot']['mtbf']['value']);
        $trend = app(ReviewedFailureTrends::class)->select($this->report()['trends'], 'active_repair');
        $this->assertSame(0, $trend['total']);
        $this->assertNull($trend['pareto'][0]['cumulative_percent']);
    }

    public function test_calculator_rejects_inconsistent_stored_arithmetic_and_exposure_sequences(): void
    {
        $this->failure();
        $this->log(['ended_at' => '2026-01-01T00:00:00+07:00']);
        $this->post(route('reliability.policies.store'), $this->policy())->assertSessionHasNoErrors();
        $r = $this->report();
        $r['events'][0]['active_intervals'][0]['seconds'] = 999;
        $r['manual_operating']['segments'][0]['seconds'] = 1;
        $c = app(ReliabilityCalculator::class)->calculate($r);
        $this->assertNull($c['pilot']['mttr']['value']);
        $this->assertContains('INVALID_TIMING_EVIDENCE', $c['pilot']['mttr']['blockers']);
        $this->assertNull($c['pilot']['mtbf']['value']);
        $this->assertContains('INVALID_EXPOSURE_SEQUENCE', $c['pilot']['mtbf']['blockers']);
    }

    public function test_trend_durations_have_separate_complete_populations_and_conflicts_are_excluded(): void
    {
        $this->failure();
        $this->failure(['failure_at' => '2025-02-02 01:00:00', 'restored_at' => '2025-02-02 05:00:00', 'repair_state' => 'unknown', 'active_intervals' => []]);
        $t = $this->report()['trends'];
        $service = app(ReviewedFailureTrends::class);
        $this->assertSame(2, $service->select($t)['included_episodes']);
        $this->assertSame(1, $service->select($t, 'active_repair')['included_episodes']);
        $this->assertSame(1, $service->select($t, 'active_repair')['excluded_incomplete']);
        $this->assertSame(6, $service->select($t, 'restoration')['total']);
        $this->assertSame(4, $service->select($t, 'restoration', 2)['total']);
        $this->failure();
        $t = $this->report()['trends'];
        $this->assertSame(1, $t['reviewed_count']);
        $this->assertSame(2, $t['excluded_conflicting_episodes']);
    }

    public function test_trend_filters_are_display_only_and_snapshot_trace_uses_original_engine(): void
    {
        $this->failure();
        $this->post(route('reliability.policies.store'), $this->policy())->assertSessionHasNoErrors();
        $scope = ['asset_ref' => self::ASSET, 'year' => 2025];
        $report = $this->report();
        $this->get(route('reliability.index', [...$scope, 'trend_basis' => 'restoration', 'trend_month' => 1]))->assertOk()->assertViewHas('report', fn ($r) => $r['evidence_hash'] === $report['evidence_hash'])->assertSee('Telusuri pembilang');
        $this->get(route('reliability.calculation', $scope))->assertOk()->assertSee('PILOT')->assertSee('Jejak exposure');
        $this->post(route('reliability.snapshots.store'), [...$scope, 'request_key' => (string) Str::uuid()])->assertRedirect();
        $snapshot = ReliabilitySnapshot::firstOrFail();
        $hash = $snapshot->report['calculation']['calculation_hash'];
        $this->failure();
        $this->get(route('reliability.snapshots.calculation', $snapshot))->assertOk()->assertViewHas('report', fn ($r) => $r['calculation']['calculation_hash'] === $hash);
        $this->assertNotSame($hash, $this->report()['calculation']['calculation_hash']);
        $this->get(route('reliability.snapshots.show', [$snapshot, 'trend_basis' => 'active_repair']))->assertOk();
    }

    public function test_legacy_snapshot_does_not_acquire_new_calculation_or_trend_evidence(): void
    {
        $r = $this->report();
        unset($r['calculation'], $r['trends']['points']);
        $snapshot = ReliabilitySnapshot::create(['created_by' => $this->owner->id, 'request_key' => (string) Str::uuid(), 'asset_ref' => self::ASSET, 'year' => 2025, 'rule_version' => ReliabilityReview::RULE, 'evidence_hash' => $r['evidence_hash'], 'report' => $r, 'created_at' => now()]);
        $this->get(route('reliability.snapshots.calculation', $snapshot))->assertOk()->assertSee('Snapshot lama ini belum menyimpan jejak mesin hitung');
        $this->get(route('reliability.snapshots.show', $snapshot))->assertOk()->assertSee('Snapshot lama menyimpan ringkasan tren');
        $this->assertArrayNotHasKey('calculation', $snapshot->fresh()->report);
    }

    public function test_invalid_trace_and_trend_filters_are_rejected_and_read_only_roles_can_inspect(): void
    {
        $scope = ['asset_ref' => self::ASSET, 'year' => 2025];
        foreach ([['trend_basis' => 'wo'], ['trend_month' => 13]] as $bad) {
            $this->get(route('reliability.index', [...$scope, ...$bad]))->assertSessionHasErrors(array_key_first($bad));
        }
        $this->get(route('reliability.calculation', [...$scope, 'trace_metric' => 'raw']))->assertSessionHasErrors('trace_metric');
        Http::assertNothingSent();
        foreach (['ADMIN', 'MANAGER', 'SUPERVISOR'] as $role) {
            $this->signIn($role);
            $this->get(route('reliability.calculation', $scope))->assertOk()->assertSee('KPI resmi: belum disahkan');
        }
    }

    public function test_bad_repair_arithmetic_does_not_invent_a_blocker_for_mtbf_or_restoration(): void
    {
        $this->failure();
        $this->log(['ended_at' => '2026-01-01T00:00:00+07:00']);
        $this->post(route('reliability.policies.store'), $this->policy())->assertSessionHasNoErrors();
        $r = $this->report();
        $r['events'][0]['active_intervals'][0]['seconds'] = 999;
        $c = app(ReliabilityCalculator::class)->calculate($r);
        $this->assertNull($c['pilot']['active_repair']['value']);
        $this->assertSame(8760.0, $c['pilot']['mtbf']['value']);
        $this->assertSame(2.0, $c['pilot']['restoration']['value']);
        $this->assertSame('INVALID_TIMING_EVIDENCE', $c['event_trace'][0]['active_repair_exclusion']);
    }

    public function test_all_new_pages_render_and_escape_and_snapshot_remains_immutable(): void
    {
        $log = $this->log(['source' => '<script>alert(1)</script>']);
        $scope = ['asset_ref' => self::ASSET, 'year' => 2025];
        foreach (['reliability.index', 'reliability.operating.index', 'reliability.operating.create', 'reliability.policies'] as $route) {
            $this->get(route($route, $scope))->assertOk()->assertDontSee('<script>alert(1)</script>', false);
        }
        $this->get(route('reliability.operating.edit', $log))->assertOk();
        $this->get(route('reliability.operating.show', $log))->assertOk()->assertSee('&lt;script&gt;', false);
        $this->post(route('reliability.snapshots.store'), [...$scope, 'request_key' => (string) Str::uuid()])->assertRedirect();
        $snapshot = ReliabilitySnapshot::firstOrFail();
        $hash = $snapshot->evidence_hash;
        $this->put(route('reliability.operating.update', $log), $this->payload(['version' => 1, 'state' => 'STOP']))->assertSessionHasNoErrors();
        $this->assertSame($hash, $snapshot->fresh()->evidence_hash);
        $this->assertNotSame($hash, $this->report()['evidence_hash']);
        $this->get(route('reliability.snapshots.show', $snapshot))->assertOk();
        Http::assertNotSent(fn ($r) => $r->method() !== 'GET');
    }

    private function approvalSnapshot(): ReliabilitySnapshot
    {
        $this->failure();
        $this->post(route('reliability.policies.store'), $this->policy())->assertSessionHasNoErrors();
        $this->post(route('reliability.snapshots.store'), ['asset_ref' => self::ASSET, 'year' => 2025, 'request_key' => (string) Str::uuid()])->assertRedirect();

        return ReliabilitySnapshot::latest('id')->firstOrFail();
    }

    private function approvalPayload(ReliabilitySnapshot $snapshot, array $extra = []): array
    {
        return array_replace(['request_key' => (string) Str::uuid(), 'decision' => 'approved', 'previous_revision' => 0,
            'calculation_hash' => $snapshot->report['calculation']['calculation_hash'], 'metrics' => ['mttr'],
            'evidence' => 'Synthetic Supervisor checks exact function, scope and arithmetic', 'reason' => 'Synthetic approval after review',
            'method_attestation' => 1, 'result_attestation' => 1], $extra);
    }

    public function test_supervisor_approves_mttr_without_runtime_and_snapshot_is_immutable(): void
    {
        $snapshot = $this->approvalSnapshot();
        $original = $snapshot->report;
        $before = $this->report();
        $supervisor = $this->signIn('SUPERVISOR');
        $this->get(route('reliability.snapshots.show', $snapshot))->assertOk()->assertSee('Sahkan metode & metrik terpilih', false);
        $this->post(route('reliability.approvals.store', $snapshot), $this->approvalPayload($snapshot))->assertSessionHasNoErrors()->assertRedirect();
        $after = $this->report();
        $this->assertSame('APPROVED', $after['approval']['status']);
        $this->assertEquals(1, $after['metrics']['mttr']['value']);
        $this->assertSame('OFFICIAL_APPROVED', $after['metrics']['mttr']['status']);
        $this->assertNull($after['metrics']['mtbf']['value']);
        $this->assertSame('METRIC_NOT_INCLUDED_IN_APPROVAL', $after['metrics']['mtbf']['blocker']);
        $this->assertSame($before['evidence_hash'], $after['evidence_hash']);
        $this->assertSame($before['calculation'], $after['calculation']);
        $this->assertSame($original, $snapshot->fresh()->report);
        $this->assertSame($supervisor->id, ReliabilityApproval::first()->created_by);
        $this->get(route('reliability.index', ['asset_ref' => self::ASSET, 'year' => 2025]))->assertOk()->assertSee('OFFICIAL_APPROVED');
        $this->get(route('reliability.snapshots.calculation', $snapshot))->assertOk()->assertSee('pengesahan Supervisor aktif');
        $packet = $this->get(route('reliability.approvals.download', $snapshot))->assertOk()->json();
        $this->assertSame('APPROVED', $packet['status']['status']);
        $this->assertSame($original, $packet['original_report']);
        $this->assertCount(1, $packet['decisions']);
        $this->get(route('reliability.snapshots.download', $snapshot))->assertExactJson($original);
    }

    public function test_only_supervisor_can_approve_and_does_not_gain_engineer_rights(): void
    {
        $snapshot = $this->approvalSnapshot();
        foreach (['ENGINEER', 'ADMIN', 'MANAGER'] as $role) {
            $this->signIn($role);
            $this->get(route('reliability.snapshots.show', $snapshot))->assertOk()->assertDontSee('type="submit">Sahkan', false);
            $this->post(route('reliability.approvals.store', $snapshot), $this->approvalPayload($snapshot))->assertForbidden();
        }
        $this->signIn('SUPERVISOR');
        $this->post(route('reliability.policies.store'), $this->policy())->assertForbidden();
        $this->post(route('reliability.snapshots.store'), ['request_key' => (string) Str::uuid(), 'asset_ref' => self::ASSET, 'year' => 2025])->assertForbidden();
        $this->assertSame(0, ReliabilityApproval::count());
    }

    public function test_supervisor_must_attest_method_result_and_select_only_ready_metrics(): void
    {
        $snapshot = $this->approvalSnapshot();
        $this->signIn('SUPERVISOR');
        foreach (['method_attestation', 'result_attestation'] as $key) {
            $data = $this->approvalPayload($snapshot);
            unset($data[$key]);
            $this->post(route('reliability.approvals.store', $snapshot), $data)->assertSessionHasErrors($key);
        }
        foreach ([[], ['mtbf'], ['mtbf', 'mttr'], ['availability'], ['mttr', 'mttr']] as $metrics) {
            $this->post(route('reliability.approvals.store', $snapshot), $this->approvalPayload($snapshot, ['metrics' => $metrics]))->assertSessionHasErrors();
        }
        $this->assertSame(0, ReliabilityApproval::count());
    }

    public function test_supervisor_decision_is_idempotent_and_stale_forms_do_not_replace_it(): void
    {
        $snapshot = $this->approvalSnapshot();
        $this->signIn('SUPERVISOR');
        $data = $this->approvalPayload($snapshot);
        $this->post(route('reliability.approvals.store', $snapshot), $data)->assertSessionHasNoErrors();
        $this->post(route('reliability.approvals.store', $snapshot), $data)->assertSessionHasNoErrors();
        $this->post(route('reliability.approvals.store', $snapshot), $this->approvalPayload($snapshot))->assertSessionHasErrors('previous_revision');
        $this->post(route('reliability.approvals.store', $snapshot), [...$data, 'decision' => 'revoked'])->assertConflict();
        $this->assertSame(1, ReliabilityApproval::count());
        $this->signIn('SUPERVISOR');
        $this->post(route('reliability.approvals.store', $snapshot), $data)->assertConflict();
    }

    public function test_correction_invalidates_official_values_and_blocks_stale_snapshot_approval(): void
    {
        $snapshot = $this->approvalSnapshot();
        $supervisor = $this->signIn('SUPERVISOR');
        $this->post(route('reliability.approvals.store', $snapshot), $this->approvalPayload($snapshot))->assertSessionHasNoErrors();
        AssetDisruption::first()->increment('version');
        $current = $this->report();
        $this->assertSame('STALE', $current['approval']['status']);
        $this->assertNull($current['metrics']['mttr']['value']);
        $this->get(route('reliability.snapshots.show', $snapshot))->assertOk()->assertSee('basisnya sudah berubah')->assertDontSee('type="submit">Sahkan', false);
        $this->get(route('reliability.snapshots.calculation', $snapshot))->assertOk()->assertDontSee('pengesahan Supervisor aktif');
        $this->post(route('reliability.approvals.store', $snapshot), $this->approvalPayload($snapshot, ['previous_revision' => 1]))->assertSessionHasErrors('calculation_hash');
        $this->assertSame(1, ReliabilityApproval::count());
        $this->assertEquals(1, ReliabilityApproval::first()->approved_values['mttr']['value']);
    }

    public function test_operating_and_method_revisions_invalidate_approval_without_changing_snapshot(): void
    {
        $snapshot = $this->approvalSnapshot();
        $supervisor = $this->signIn('SUPERVISOR');
        $this->post(route('reliability.approvals.store', $snapshot), $this->approvalPayload($snapshot))->assertSessionHasNoErrors();
        $this->actingAs($this->owner)->withSession(['auth_version' => $this->owner->auth_version]);
        $this->log();
        $this->assertSame('STALE', $this->report()['approval']['status']);
        $this->post(route('reliability.policies.store'), $this->policy(['previous_revision' => 1, 'mttr_basis' => 'restoration']))->assertSessionHasNoErrors();
        $this->post(route('reliability.snapshots.store'), ['asset_ref' => self::ASSET, 'year' => 2025, 'request_key' => (string) Str::uuid()])->assertRedirect();
        $new = ReliabilitySnapshot::latest('id')->firstOrFail();
        $this->actingAs($supervisor)->withSession(['auth_version' => $supervisor->auth_version]);
        $this->post(route('reliability.approvals.store', $new), $this->approvalPayload($new, ['previous_revision' => 1]))->assertSessionHasNoErrors();
        $this->assertEquals(2, $this->report()['metrics']['mttr']['value']);
        $this->get(route('reliability.snapshots.show', $snapshot))->assertOk()->assertViewHas('approvalStatus', fn ($v) => $v['status'] === 'OTHER_SNAPSHOT');
        $this->assertSame(2, ReliabilityApproval::count());
    }

    public function test_revocation_is_append_only_and_retains_historical_approved_values(): void
    {
        $snapshot = $this->approvalSnapshot();
        $this->signIn('SUPERVISOR');
        $this->post(route('reliability.approvals.store', $snapshot), $this->approvalPayload($snapshot))->assertSessionHasNoErrors();
        AssetDisruption::first()->increment('version'); // Stale decisions can still be revoked.
        $this->post(route('reliability.approvals.store', $snapshot), $this->approvalPayload($snapshot, ['decision' => 'revoked', 'metrics' => null, 'method_attestation' => 0, 'result_attestation' => 0, 'previous_revision' => 1]))->assertSessionHasNoErrors();
        $this->assertSame('REVOKED', $this->report()['approval']['status']);
        $this->assertNull($this->report()['metrics']['mttr']['value']);
        $this->assertSame(2, ReliabilityApproval::count());
        $this->assertEquals(1, ReliabilityApproval::first()->approved_values['mttr']['value']);
        $this->post(route('reliability.approvals.store', $snapshot), $this->approvalPayload($snapshot, ['decision' => 'revoked', 'previous_revision' => 2]))->assertSessionHasErrors('decision');
    }

    public function test_approval_is_local_source_outage_safe_and_exact_asset_year_only(): void
    {
        $snapshot = $this->approvalSnapshot();
        $this->signIn('SUPERVISOR');
        Http::swap(new Factory);
        Http::preventStrayRequests();
        $this->post(route('reliability.approvals.store', $snapshot), $this->approvalPayload($snapshot))->assertSessionHasNoErrors();
        Http::assertNothingSent();
        Http::fake(fn () => Http::response([], 503));
        $this->assertSame('APPROVED', $this->report()['approval']['status']);
        $this->assertSame('AWAITING_SUPERVISOR', $this->report(2024)['approval']['status']);
        $other = app(ReliabilityEvidence::class)->report(self::ASSET.'-OTHER', 2025, app(ReliabilityMart::class));
        $this->assertSame('AWAITING_SUPERVISOR', $other['approval']['status']);
    }

    public function test_legacy_snapshots_and_tampered_hashes_cannot_be_approved(): void
    {
        $snapshot = $this->approvalSnapshot();
        $this->signIn('SUPERVISOR');
        $this->post(route('reliability.approvals.store', $snapshot), $this->approvalPayload($snapshot, ['calculation_hash' => str_repeat('0', 64)]))->assertSessionHasErrors('calculation_hash');
        $report = $snapshot->report;
        unset($report['calculation']);
        $snapshot->update(['report' => $report]); // Synthetic retained old schema only.
        $this->post(route('reliability.approvals.store', $snapshot), ['request_key' => (string) Str::uuid(), 'decision' => 'approved', 'previous_revision' => 0, 'calculation_hash' => str_repeat('0', 64), 'metrics' => ['mttr'], 'evidence' => 'Synthetic evidence', 'reason' => 'Synthetic reason', 'method_attestation' => 1, 'result_attestation' => 1])->assertSessionHasErrors('calculation_hash');
        $this->assertSame(0, ReliabilityApproval::count());
    }

    public function test_supervisor_can_approve_both_ready_metrics_with_separate_populations(): void
    {
        $this->log(['ended_at' => '2026-01-01T00:00:00+07:00']);
        $snapshot = $this->approvalSnapshot();
        $this->signIn('SUPERVISOR');
        $this->post(route('reliability.approvals.store', $snapshot), $this->approvalPayload($snapshot, ['metrics' => ['mtbf', 'mttr']]))->assertSessionHasNoErrors();
        $report = $this->report();
        $this->assertEquals(8760, $report['metrics']['mtbf']['value']);
        $this->assertEquals(1, $report['metrics']['mttr']['value']);
        $this->assertTrue(ReliabilityApproval::first()->method_attestation);
        $this->assertTrue(ReliabilityApproval::first()->result_attestation);
        $this->assertSame(1, ReliabilityApproval::first()->approved_values['mtbf']['denominator_episodes']);
    }

    public function test_prior_engine_snapshot_cannot_approve_even_when_its_pilot_is_numeric(): void
    {
        $snapshot = $this->approvalSnapshot();
        $report = $snapshot->report;
        $report['calculation']['engine_version'] = 'nadi-reliability-calculation-v1';
        unset($report['calculation']['calculation_hash']);
        $report['calculation']['calculation_hash'] = hash('sha256', json_encode($report['calculation'], JSON_THROW_ON_ERROR));
        $snapshot->update(['report' => $report]); // Synthetic retained old engine snapshot.
        $this->signIn('SUPERVISOR');
        $this->post(route('reliability.approvals.store', $snapshot), $this->approvalPayload($snapshot))->assertSessionHasErrors('calculation_hash');
        $this->assertSame(0, ReliabilityApproval::count());
    }
}
