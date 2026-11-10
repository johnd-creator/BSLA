<?php

namespace Tests\Feature;

use App\Models\AssetDisruption;
use App\Models\AssetWellnessPolicy;
use App\Models\OperatingLog;
use App\Models\PdmActivity;
use App\Models\ReliabilityApproval;
use App\Models\ReliabilityPolicy;
use App\Models\ReliabilityReview;
use App\Models\ReliabilitySnapshot;
use App\Models\User;
use App\Services\AssetWellness;
use App\Services\OperatingExposure;
use App\Services\ReliabilityEvidence;
use App\Services\ReliabilityMart;
use App\Services\ReliabilityPeriod;
use App\Services\ReviewedFailureTrends;
use Carbon\CarbonImmutable;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Schema;
use Illuminate\Support\Str;
use PHPUnit\Framework\Attributes\DataProvider;
use Tests\TestCase;

class ReliabilityPeriodTest extends TestCase
{
    use RefreshDatabase;

    private const ASSET = 'asset:MAXIMO:MXASSET:BSR:IP:PERIOD-FIXTURE';

    private User $owner;

    private bool $outage = true;

    protected function setUp(): void
    {
        parent::setUp();
        $this->travelTo(CarbonImmutable::parse('2026-11-09T12:00:00+07:00'));
        config(['services.reliability_mart.url' => 'http://mart.test']);
        Http::preventStrayRequests();
        Http::fake(function ($request) {
            if (! $this->outage && str_contains($request->url(), '/assets/')) {
                return Http::response(['canonical_id' => self::ASSET, 'site_code' => 'BSR', 'organization_code' => 'IP', 'registered' => false, 'hierarchy_category' => 'equipment', 'scope_basis' => 'DIRECT_SOURCE_UNIT', 'description' => 'Synthetic period fixture']);
            }

            return Http::response([], 503);
        });
        $this->owner = User::factory()->create(['roles' => ['ENGINEER'], 'active' => true])->refresh();
        $this->actingAs($this->owner)->withSession(['auth_version' => $this->owner->auth_version]);
    }

    private function period(string $start, string $end): ReliabilityPeriod
    {
        return ReliabilityPeriod::fromRequest(Request::create('/', 'GET', ['period' => 'custom', 'start_date' => $start, 'end_date' => $end]));
    }

    private function report(ReliabilityPeriod $period): array
    {
        return app(ReliabilityEvidence::class)->report(self::ASSET, $period, app(ReliabilityMart::class));
    }

    private function failure(string $onset, ?string $restored = null): AssetDisruption
    {
        $start = CarbonImmutable::parse($onset)->utc();
        $finish = $restored ? CarbonImmutable::parse($restored)->utc() : $start->addHour();
        $event = AssetDisruption::create(['asset_ref' => self::ASSET, 'created_by' => $this->owner->id, 'request_key' => (string) Str::uuid(), 'event_type' => 'trip', 'description' => 'Synthetic period fixture only', 'impact' => 'unknown', 'occurred_on' => $start->setTimezone('Asia/Jakarta')->toDateString()]);
        $event->members()->create(['asset_ref' => self::ASSET, 'role' => 'affected']);
        $event->refresh();
        ReliabilityReview::create(['asset_disruption_id' => $event->id, 'asset_ref' => self::ASSET, 'revision' => 1, 'event_version' => $event->version, 'created_by' => $this->owner->id, 'request_key' => (string) Str::uuid(), 'classification' => 'failure', 'required_function' => 'Synthetic process function', 'evidence' => 'Synthetic timing evidence', 'reason' => 'Isolated test only', 'failure_at' => $start, 'restored_at' => $finish, 'repair_state' => 'completed', 'active_intervals' => [['start' => $start->toIso8601String(), 'end' => $finish->toIso8601String(), 'seconds' => (int) $start->diffInSeconds($finish)]], 'rule_version' => ReliabilityReview::RULE, 'event_snapshot' => $event->snapshot(), 'created_at' => now()]);

        return $event;
    }

    private function log(string $start, string $end, string $state = 'RUN', string $review = 'verified'): void
    {
        $log = OperatingLog::create(['asset_ref' => self::ASSET, 'created_by' => $this->owner->id]);
        $log->revisions()->create(['revision' => 1, 'created_by' => $this->owner->id, 'request_key' => (string) Str::uuid(), 'started_at' => CarbonImmutable::parse($start)->utc(), 'ended_at' => CarbonImmutable::parse($end)->utc(), 'state' => $state, 'review_state' => $review, 'source' => 'Synthetic test source', 'evidence' => 'Synthetic evidence', 'reason' => 'Isolated test only', 'created_at' => now()]);
    }

    public function test_presets_use_calendar_months_and_complete_local_dates_with_explicit_anchor(): void
    {
        foreach (['3m' => '2026-08-09', '6m' => '2026-05-09', '12m' => '2025-11-09'] as $preset => $start) {
            $p = ReliabilityPeriod::fromRequest(Request::create('/', 'GET', ['period' => $preset]));
            $this->assertSame($start, $p->start->toDateString());
            $this->assertSame('2026-11-09T00:00:00+07:00', $p->end->toIso8601String());
            $this->assertSame('2026-11-08', $p->query()['end_date']);
            $this->assertSame($p->metadata(), ReliabilityPeriod::fromReport(['period' => $p->metadata()])->metadata());
        }
        $historical = ReliabilityPeriod::fromRequest(Request::create('/', 'GET', ['period' => '12m', 'end_date' => '2025-12-31']));
        $this->assertSame('2025-01-01', $historical->start->toDateString());
        $this->assertFalse($historical->annual);
        $monthEnd = ReliabilityPeriod::fromRequest(Request::create('/', 'GET', ['period' => '3m', 'end_date' => '2024-05-30']));
        $this->assertSame('2024-02-29', $monthEnd->start->toDateString());
    }

    public function test_legacy_annual_metadata_and_hash_are_identical_to_integer_entrypoint(): void
    {
        $this->failure('2025-12-31T10:00:00+07:00');
        $old = app(ReliabilityEvidence::class)->report(self::ASSET, 2025, app(ReliabilityMart::class));
        $new = $this->report(ReliabilityPeriod::year(2025));
        $this->assertSame($old['evidence_hash'], $new['evidence_hash']);
        $this->assertSame($old['calculation']['calculation_hash'], $new['calculation']['calculation_hash']);
        $this->assertArrayNotHasKey('kind', $new['period']);
        $this->assertSame('nadi.reliability-evidence.v1', $new['schema_version']);
    }

    public function test_exact_half_open_boundaries_and_complete_cross_boundary_episode(): void
    {
        $before = $this->failure('2026-06-30T22:00:00+07:00');
        $first = $this->failure('2026-07-01T00:00:00+07:00');
        $last = $this->failure('2026-09-30T23:00:00+07:00', '2026-10-01T04:00:00+07:00');
        $r = $this->report($this->period('2026-07-01', '2026-09-30'));
        $this->assertSame(2, $r['quality']['failure']);
        $this->assertSame([$first->id, $last->id], $r['reviewed_samples']['mean_restoration']['event_ids']);
        $this->assertSame(21600, $r['reviewed_samples']['mean_restoration']['numerator_seconds']);
        $this->assertSame(1, $r['quality']['cross_year_restoration']);
        $this->assertSame(3.0, $r['reviewed_samples']['mean_restoration']['value']);
        $next = $this->report($this->period('2026-10-01', '2026-10-31'));
        $this->assertSame(0, $next['quality']['failure']);
        $this->assertSame(0, $next['reviewed_samples']['mean_restoration']['denominator_completed_episodes']);
        $this->assertNotContains($before->id, $r['trends']['event_ids']);
    }

    public function test_outside_period_overlap_still_blocks_selected_episode(): void
    {
        $this->failure('2026-06-30T22:00:00+07:00', '2026-07-01T02:00:00+07:00');
        $inside = $this->failure('2026-07-01T01:00:00+07:00');
        $r = $this->report($this->period('2026-07-01', '2026-07-31'));
        $this->assertContains($inside->id, $r['overlap_event_ids']);
        $this->assertNull($r['reviewed_samples']['mean_restoration']['value']);
        $this->assertNotContains($inside->id, $r['trends']['event_ids']);
    }

    public function test_exposure_is_clipped_without_calendar_extrapolation_or_duplicate_sum(): void
    {
        $this->log('2026-06-30T00:00:00+07:00', '2026-07-02T12:00:00+07:00');
        $this->log('2026-07-01T04:00:00+07:00', '2026-07-01T06:00:00+07:00');
        $r = app(OperatingExposure::class)->report(self::ASSET, $this->period('2026-07-01', '2026-07-01'));
        $this->assertSame(86400, $r['period_seconds']);
        $this->assertSame(79200, $r['operating_seconds']);
        $this->assertSame(7200, $r['seconds']['OVERLAP']);
        $this->assertSame(0, $r['seconds']['GAP']);
        $this->assertSame(91.666667, $r['coverage_percent']);
        $this->assertSame('2026-06-30T17:00:00+00:00', $r['segments'][0]['start']);
        $empty = app(OperatingExposure::class)->report(self::ASSET, $this->period('2026-08-01', '2026-08-01'));
        $this->assertNull($empty['operating_seconds']);
        $this->assertSame(86400, $empty['seconds']['GAP']);
    }

    public function test_annual_method_is_not_inherited_and_official_values_remain_null(): void
    {
        ReliabilityPolicy::create(['asset_ref' => self::ASSET, 'year' => 2026, 'revision' => 1, 'created_by' => $this->owner->id, 'request_key' => (string) Str::uuid(), 'rules' => ['status' => 'reviewed_local'], 'evidence' => 'Annual fixture only', 'reason' => 'Test scope', 'created_at' => now()]);
        $this->failure('2026-07-01T08:00:00+07:00');
        $r = $this->report($this->period('2026-07-01', '2026-09-30'));
        $this->assertNull($r['readiness']['policy']);
        $this->assertContains('LOCAL_METHOD_NOT_REVIEWED', $r['calculation']['pilot']['mttr']['blockers']);
        $this->assertSame('AWAITING_SUPERVISOR', $r['approval']['status']);
        $this->assertNull($r['approval']['approval']);
        $this->assertNull($r['metrics']['mttr']['value']);
        $this->assertSame(1.0, $r['reviewed_samples']['mean_restoration']['value']);
    }

    public function test_trend_buckets_keep_different_years_separate_and_trace_retains_range(): void
    {
        $a = $this->failure('2025-01-02T08:00:00+07:00');
        $b = $this->failure('2026-01-02T08:00:00+07:00');
        $p = $this->period('2025-01-01', '2026-02-28');
        $r = $this->report($p);
        $this->assertSame(1, $r['trends']['monthly_counts']['2025-01']);
        $this->assertSame(1, $r['trends']['monthly_counts']['2026-01']);
        $this->assertCount(14, $r['trends']['monthly_counts']);
        $filtered = app(ReviewedFailureTrends::class)->select($r['trends'], 'count', null, '2026-01');
        $this->assertSame([$b->id], $filtered['months']['2026-01']['event_ids']);
        $this->assertSame([], $filtered['months']['2025-01']['event_ids']);
        $this->get(route('reliability.index', ['asset_ref' => self::ASSET, ...$p->query()]))->assertOk()->assertSee('2025-01')->assertSee('2026-01')->assertSee('trace_period_month=2026-01', false)->assertSee('start_date=2025-01-01', false);
        $response = $this->get(route('reliability.calculation', ['asset_ref' => self::ASSET, ...$p->query(), 'trace_period_month' => '2026-01']));
        $response->assertOk()->assertViewHas('traceRows', fn ($rows) => $rows->count() === 1 && $rows[0]['event_id'] === $b->id);
    }

    public function test_snapshot_round_trip_is_immutable_scoped_and_idempotent(): void
    {
        $this->failure('2026-07-01T08:00:00+07:00');
        $p = $this->period('2026-07-01', '2026-09-30');
        $payload = ['asset_ref' => self::ASSET, ...$p->query(), 'request_key' => (string) Str::uuid()];
        $this->post(route('reliability.snapshots.store'), $payload)->assertRedirect();
        $saved = ReliabilitySnapshot::sole();
        $hash = $saved->evidence_hash;
        $this->post(route('reliability.snapshots.store'), $payload)->assertRedirect();
        $this->assertDatabaseCount('reliability_snapshots', 1);
        $this->post(route('reliability.snapshots.store'), [...$payload, 'end_date' => '2026-10-31'])->assertStatus(409);
        $this->get(route('reliability.index', ['asset_ref' => self::ASSET, ...$p->query()]))->assertOk()->assertViewHas('snapshots', fn ($list) => $list->total() === 1);
        $this->get(route('reliability.index', ['asset_ref' => self::ASSET, 'year' => 2026]))->assertOk()->assertViewHas('snapshots', fn ($list) => $list->total() === 0);
        $this->travel(2)->days();
        $this->get(route('reliability.snapshots.show', $saved))->assertOk()->assertViewHas('changed', false)->assertSee('Pengesahan metode & hasil oleh Supervisor', false);
        $this->failure('2026-08-01T08:00:00+07:00');
        $this->get(route('reliability.snapshots.show', $saved))->assertOk()->assertViewHas('changed', true);
        $this->assertSame($hash, $saved->fresh()->evidence_hash);
        $this->get(route('reliability.snapshots.download', $saved))->assertOk()->assertJsonPath('quality.failure', 1);
    }

    public function test_range_approval_post_is_rejected_server_side_and_read_only_role_cannot_snapshot(): void
    {
        $this->failure('2026-07-01T08:00:00+07:00');
        $p = $this->period('2026-07-01', '2026-07-31');
        $this->post(route('reliability.snapshots.store'), ['asset_ref' => self::ASSET, ...$p->query(), 'request_key' => (string) Str::uuid()])->assertRedirect();
        $saved = ReliabilitySnapshot::sole();
        $user = User::factory()->create(['roles' => ['SUPERVISOR'], 'active' => true])->refresh();
        $this->actingAs($user)->withSession(['auth_version' => $user->auth_version]);
        $this->postJson(route('reliability.approvals.store', $saved), [])->assertStatus(422);
        $this->post(route('reliability.snapshots.store'), ['asset_ref' => self::ASSET, ...$p->query(), 'request_key' => (string) Str::uuid()])->assertForbidden();
        $this->assertDatabaseCount('reliability_approvals', 0);
        $this->get(route('reliability.approvals.download', $saved))->assertOk()->assertJsonPath('status.status', 'AWAITING_SUPERVISOR');
    }

    public function test_wellness_pdm_is_scoped_without_fabricated_score_or_historical_knowledge_claim(): void
    {
        foreach (['2026-06-30', '2026-07-01', '2026-09-30', '2026-10-01'] as $date) {
            PdmActivity::create(['asset_ref' => self::ASSET, 'created_by' => $this->owner->id, 'request_key' => (string) Str::uuid(), 'title' => 'Synthetic measurement only', 'template_id' => 'fixture', 'template_fingerprint' => str_repeat('a', 64), 'method' => 'VIBRATION', 'time_precision' => 'date', 'measured_on' => $date, 'instrument' => 'Synthetic fixture', 'measurement_mode' => 'test', 'operating_condition' => 'unknown', 'asset_selection_note' => 'Exact fixture', 'template_snapshot' => [], 'readings' => []]);
        }
        $p = $this->period('2026-07-01', '2026-09-30');
        $r = app(AssetWellness::class)->report(self::ASSET, $p, app(ReliabilityMart::class));
        $this->assertSame(2, $r['components']['pdm']['evidence']['count']);
        $this->assertSame(2, $r['components']['pdm']['evidence']['quality']['date_only']);
        $this->assertNull($r['method_draft']['policy']);
        $this->assertSame('2026-09-30', $r['method_draft']['as_of_date']);
        $this->assertNull($r['score']);
        $this->assertNull($r['components']['maintenance']['evidence']['work_order_count']);
        $this->get(route('wellness.index', ['asset_ref' => self::ASSET, ...$p->query()]))->assertOk()->assertSee('bukan penilaian kondisi yang telah diketahui')->assertSee('2026-07-01 sampai 2026-09-30');
    }

    public function test_rolling_links_and_snapshot_pagination_resolve_to_fixed_boundaries(): void
    {
        $this->failure('2026-09-01T08:00:00+07:00');
        $period = ReliabilityPeriod::fromRequest(Request::create('/', 'GET', ['period' => '3m']));
        $report = $this->report($period);
        for ($i = 0; $i < 11; $i++) {
            ReliabilitySnapshot::create(['asset_ref' => self::ASSET, 'year' => 2026, 'created_by' => $this->owner->id, 'request_key' => (string) Str::uuid(), 'rule_version' => ReliabilityReview::RULE, 'evidence_hash' => $report['evidence_hash'], 'report' => $report, 'created_at' => now()]);
        }
        $response = $this->get(route('reliability.index', ['asset_ref' => self::ASSET, 'period' => '3m']));
        $response->assertOk()->assertSee('period=custom', false)->assertSee('end_date=2026-11-08', false)->assertDontSee('period=3m', false);
        $this->travel(2)->days();
        $this->get(route('reliability.index', ['asset_ref' => self::ASSET, ...$period->query(), 'page' => 2]))->assertOk()->assertViewHas('snapshots', fn ($list) => $list->total() === 11 && $list->count() === 1);
    }

    private function methodPayload(ReliabilityPeriod $period, array $extra = []): array
    {
        $latest = $period->constrain(ReliabilityPolicy::where('asset_ref', self::ASSET))->latest('revision')->first();

        return array_replace(['asset_ref' => self::ASSET, ...$period->query(), 'request_key' => (string) Str::uuid(), 'previous_revision' => $latest?->revision ?? 0,
            'status' => 'reviewed_local', 'required_function' => 'Synthetic required flow', 'failure_definition' => 'Synthetic inability to deliver flow',
            'exposure_basis' => 'run_only', 'recurrence_policy' => 'restored_before_recurrence', 'mttr_basis' => 'active_repair', 'minimum_coverage' => 100,
            'failure_scope' => 'attested_same_function', 'failure_coverage' => 'attested_complete', 'failure_coverage_evidence' => 'Synthetic full census evidence',
            'incomplete_policy' => 'withhold', 'evidence' => 'Synthetic method reference', 'reason' => 'Isolated test only', 'attestation' => 1], $extra);
    }

    private function saveMethod(ReliabilityPeriod $period, array $extra = []): ReliabilityPolicy
    {
        $this->outage = false;
        $this->post(route('reliability.policies.store'), $this->methodPayload($period, $extra))->assertSessionHasNoErrors()->assertRedirect();

        return $period->constrain(ReliabilityPolicy::where('asset_ref', self::ASSET))->latest('revision')->firstOrFail();
    }

    private function snapshot(ReliabilityPeriod $period): ReliabilitySnapshot
    {
        $this->post(route('reliability.snapshots.store'), ['asset_ref' => self::ASSET, ...$period->query(), 'request_key' => (string) Str::uuid()])->assertSessionHasNoErrors()->assertRedirect();

        return ReliabilitySnapshot::latest('id')->firstOrFail();
    }

    private function supervisor(): User
    {
        $user = User::factory()->create(['roles' => ['SUPERVISOR'], 'active' => true])->refresh();
        $this->actingAs($user)->withSession(['auth_version' => $user->auth_version]);

        return $user;
    }

    private function decision(ReliabilitySnapshot $snapshot, array $extra = []): array
    {
        $period = ReliabilityPeriod::fromReport($snapshot->report);
        $latest = $period->constrain(ReliabilityApproval::where('asset_ref', self::ASSET))->latest('revision')->first();

        return array_replace(['request_key' => (string) Str::uuid(), 'decision' => 'approved', 'previous_revision' => $latest?->revision ?? 0,
            'calculation_hash' => $snapshot->report['calculation']['calculation_hash'], 'metrics' => ['mttr'], 'evidence' => 'Synthetic Supervisor reconciliation',
            'reason' => 'Synthetic exact-period approval', 'method_attestation' => 1, 'result_attestation' => 1], $extra);
    }

    public function test_range_mtbf_and_mttr_calculate_and_can_be_approved_with_exact_evidence(): void
    {
        $period = $this->period('2026-07-01', '2026-07-01');
        $this->failure('2026-07-01T08:00:00+07:00');
        $this->log('2026-07-01T00:00:00+07:00', '2026-07-01T08:00:00+07:00');
        $this->log('2026-07-01T08:00:00+07:00', '2026-07-01T09:00:00+07:00', 'STOP');
        $this->log('2026-07-01T09:00:00+07:00', '2026-07-02T00:00:00+07:00');
        $method = $this->saveMethod($period);
        $this->assertSame($period->key(), $method->period_key);
        $this->assertSame(ReliabilityPolicy::RANGE_SCHEMA, $method->rules['schema_version']);
        $report = $this->report($period);
        $this->assertSame(23.0, $report['calculation']['pilot']['mtbf']['value']);
        $this->assertSame(1.0, $report['calculation']['pilot']['mttr']['value']);
        $this->assertSame(100.0, $report['coverage']['coverage_percent']);
        $snapshot = $this->snapshot($period);
        $original = $snapshot->report;
        $this->supervisor();
        $payload = $this->decision($snapshot, ['metrics' => ['mtbf', 'mttr']]);
        $this->get(route('reliability.snapshots.show', $snapshot))->assertOk()->assertSee('Sahkan metode & metrik terpilih', false);
        $this->post(route('reliability.approvals.store', $snapshot), $payload)->assertSessionHasNoErrors();
        $this->post(route('reliability.approvals.store', $snapshot), $payload)->assertSessionHasNoErrors();
        $this->assertDatabaseCount('reliability_approvals', 1);
        $approved = $this->report($period);
        $this->assertSame('APPROVED', $approved['approval']['status']);
        $this->assertEquals(23.0, $approved['metrics']['mtbf']['value']);
        $this->assertEquals(1.0, $approved['metrics']['mttr']['value']);
        $this->assertSame($original, $snapshot->fresh()->report);
        $this->get(route('reliability.approvals.download', $snapshot))->assertOk()->assertJsonPath('status.approval.period_key', $period->key());
        $this->get(route('reliability.operating.index', ['asset_ref' => self::ASSET, ...$period->query()]))->assertOk()->assertViewHas('coverage', fn ($value) => $value['period_seconds'] === 86400);
    }

    public function test_range_mttr_needs_no_operating_logs_and_incomplete_exposure_never_scales(): void
    {
        $period = $this->period('2026-07-01', '2026-07-31');
        $this->failure('2026-07-01T08:00:00+07:00');
        $this->saveMethod($period, ['minimum_coverage' => 1]);
        $r = $this->report($period);
        $this->assertSame(1.0, $r['calculation']['pilot']['mttr']['value']);
        $this->assertNull($r['calculation']['pilot']['mtbf']['value']);
        $this->log('2026-07-01T00:00:00+07:00', '2026-07-01T08:00:00+07:00');
        $r = $this->report($period);
        $this->assertContains('OPERATING_GAP', $r['calculation']['pilot']['mtbf']['blockers']);
        $this->assertNull($r['calculation']['pilot']['mtbf']['value']);
        $snapshot = $this->snapshot($period);
        $this->supervisor();
        $this->post(route('reliability.approvals.store', $snapshot), $this->decision($snapshot, ['metrics' => ['mtbf']]))->assertSessionHasErrors('metrics');
        $this->post(route('reliability.approvals.store', $snapshot), $this->decision($snapshot))->assertSessionHasNoErrors();
        $this->assertSame('OFFICIAL_APPROVED', $this->report($period)['metrics']['mttr']['status']);
    }

    public function test_annual_and_overlapping_range_methods_and_approvals_remain_independent(): void
    {
        $this->failure('2026-07-01T08:00:00+07:00');
        $annual = ReliabilityPeriod::year(2026);
        $july = $this->period('2026-07-01', '2026-07-31');
        $quarter = $this->period('2026-07-01', '2026-09-30');
        $annualMethod = $this->saveMethod($annual);
        $annualSnapshot = $this->snapshot($annual);
        $this->supervisor();
        $this->post(route('reliability.approvals.store', $annualSnapshot), $this->decision($annualSnapshot))->assertSessionHasNoErrors();
        $annualHash = $this->report($annual)['calculation']['calculation_hash'];
        $this->assertNull($this->report($july)['readiness']['policy']);
        $this->actingAs($this->owner)->withSession(['auth_version' => $this->owner->auth_version]);
        $rangeMethod = $this->saveMethod($july);
        $rangeSnapshot = $this->snapshot($july);
        $this->saveMethod($quarter, ['status' => 'draft']);
        $this->assertSame($annualMethod->id, $this->report($annual)['readiness']['policy']['id']);
        $this->assertSame($rangeMethod->id, $this->report($july)['readiness']['policy']['id']);
        $this->assertSame($annualHash, $this->report($annual)['calculation']['calculation_hash']);
        $this->supervisor();
        $this->post(route('reliability.approvals.store', $rangeSnapshot), $this->decision($rangeSnapshot))->assertSessionHasNoErrors();
        $this->assertSame('APPROVED', $this->report($annual)['approval']['status']);
        $this->assertSame('APPROVED', $this->report($july)['approval']['status']);
        $this->assertSame('AWAITING_SUPERVISOR', $this->report($quarter)['approval']['status']);
        $this->post(route('reliability.approvals.store', $rangeSnapshot), $this->decision($rangeSnapshot, ['decision' => 'revoked', 'metrics' => null, 'method_attestation' => 0, 'result_attestation' => 0]))->assertSessionHasNoErrors();
        $this->assertSame('REVOKED', $this->report($july)['approval']['status']);
        $this->assertSame('APPROVED', $this->report($annual)['approval']['status']);
        $this->assertSame($annualHash, $this->report($annual)['calculation']['calculation_hash']);
    }

    public function test_range_method_stale_forms_ownership_and_cross_period_idempotency(): void
    {
        $this->outage = false;
        $a = $this->period('2026-07-01', '2026-07-31');
        $b = $this->period('2026-08-01', '2026-08-31');
        $payload = $this->methodPayload($a);
        $this->post(route('reliability.policies.store'), $payload)->assertSessionHasNoErrors();
        $this->post(route('reliability.policies.store'), $payload)->assertSessionHasNoErrors();
        $this->assertDatabaseCount('reliability_policies', 1);
        $this->post(route('reliability.policies.store'), [...$payload, ...$b->query()])->assertStatus(409);
        $stale = $this->methodPayload($a);
        $this->saveMethod($b);
        $this->post(route('reliability.policies.store'), $stale)->assertSessionHasNoErrors();
        $this->post(route('reliability.policies.store'), [...$stale, 'request_key' => (string) Str::uuid()])->assertSessionHasErrors('previous_revision');
        $other = User::factory()->create(['roles' => ['ENGINEER'], 'active' => true])->refresh();
        $this->actingAs($other)->withSession(['auth_version' => $other->auth_version]);
        $this->post(route('reliability.policies.store'), $this->methodPayload($a))->assertForbidden();
        $this->get(route('reliability.policies', ['asset_ref' => self::ASSET, ...$a->query()]))->assertOk()->assertSee('Hanya engineer pemilik aturan');
    }

    public function test_approved_range_becomes_stale_after_evidence_or_method_revision_without_rewriting_snapshot(): void
    {
        $p = $this->period('2026-07-01', '2026-07-31');
        $event = $this->failure('2026-07-01T08:00:00+07:00');
        $this->saveMethod($p);
        $snapshot = $this->snapshot($p);
        $original = $snapshot->report;
        $this->supervisor();
        $this->post(route('reliability.approvals.store', $snapshot), $this->decision($snapshot))->assertSessionHasNoErrors();
        $event->increment('version');
        $this->assertSame('STALE', $this->report($p)['approval']['status']);
        $this->assertNull($this->report($p)['metrics']['mttr']['value']);
        $this->post(route('reliability.approvals.store', $snapshot), $this->decision($snapshot))->assertSessionHasErrors('calculation_hash');
        $this->assertSame($original, $snapshot->fresh()->report);
    }

    public function test_range_pilot_full_episode_can_end_after_selected_window(): void
    {
        $p = $this->period('2026-07-01', '2026-07-01');
        $this->failure('2026-07-01T23:00:00+07:00', '2026-07-02T04:00:00+07:00');
        $this->log('2026-07-01T00:00:00+07:00', '2026-07-01T23:00:00+07:00');
        $this->log('2026-07-01T23:00:00+07:00', '2026-07-02T00:00:00+07:00', 'STOP');
        $this->saveMethod($p, ['mttr_basis' => 'restoration']);
        $r = $this->report($p);
        $this->assertSame(5.0, $r['calculation']['pilot']['mttr']['value']);
        $this->assertSame(23.0, $r['calculation']['pilot']['mtbf']['value']);
        $this->assertSame(86400, $r['manual_operating']['period_seconds']);
        $this->assertSame(1, $r['quality']['cross_year_restoration']);
    }

    private function wellnessPayload(ReliabilityPeriod $period, array $extra = []): array
    {
        $current = $period->constrain(AssetWellnessPolicy::where('asset_ref', self::ASSET))->latest('revision')->first();

        return array_replace(['asset_ref' => self::ASSET, ...$period->query(), 'request_key' => (string) Str::uuid(), 'previous_revision' => $current?->revision ?? 0,
            'criticality_label' => null, 'criticality_basis' => null, 'components' => array_fill_keys(array_keys(AssetWellness::COMPONENTS), ['max_age_days' => null, 'required_evidence' => null]),
            'pdm_rules' => [], 'evidence' => 'Synthetic draft requirements', 'reason' => 'Isolated fixture only', 'acknowledge_draft' => 1], $extra);
    }

    public function test_wellness_range_drafts_remain_independent_and_not_scores(): void
    {
        $this->outage = false;
        $p = $this->period('2026-07-01', '2026-09-30');
        $annual = ReliabilityPeriod::year(2026);
        $this->post(route('wellness.policy.store'), $this->wellnessPayload($annual, ['criticality_label' => 'Annual fixture', 'criticality_basis' => 'Synthetic annual basis']))->assertSessionHasNoErrors();
        $payload = $this->wellnessPayload($p);
        $this->post(route('wellness.policy.store'), $payload)->assertSessionHasNoErrors();
        $this->post(route('wellness.policy.store'), $payload)->assertSessionHasNoErrors();
        $this->assertDatabaseCount('asset_wellness_policies', 2);
        $this->post(route('wellness.policy.store'), [...$payload, 'end_date' => '2026-08-31'])->assertStatus(409);
        $r = app(AssetWellness::class)->report(self::ASSET, $p, app(ReliabilityMart::class));
        $this->assertNull($r['method_draft']['policy']->rules['criticality_label']);
        $this->assertSame($p->key(), $r['method_draft']['policy']->period_key);
        $this->assertSame('DRAFT_NOT_APPROVED', $r['method_draft']['status']);
        $this->assertNull($r['score']);
        $this->get(route('wellness.policy', ['asset_ref' => self::ASSET, ...$p->query()]))->assertOk()->assertSee('2026-07-01 sampai 2026-09-30')->assertDontSee('Annual fixture');
        $this->get(route('wellness.policy', ['asset_ref' => self::ASSET, ...$annual->query()]))->assertOk()->assertSee('Annual fixture');
    }

    public function test_period_migration_refuses_to_remove_persisted_range_history(): void
    {
        $this->saveMethod($this->period('2026-07-01', '2026-07-31'));
        $migration = require database_path('migrations/2026_11_10_000001_add_exact_reliability_period_scopes.php');
        try {
            $migration->down();
            $this->fail('Must preserve period identity');
        } catch (\RuntimeException $error) {
            $this->assertStringContainsString('Period history exists', $error->getMessage());
        }
        foreach (['reliability_policies', 'reliability_approvals', 'asset_wellness_policies'] as $table) {
            $this->assertTrue(Schema::hasColumn($table, 'period_key'));
        }
        $this->assertDatabaseCount('reliability_policies', 1);
    }

    public function test_wellness_period_thresholds_use_exact_context_and_end_date_without_assuming_weights(): void
    {
        $this->outage = false;
        $period = $this->period('2026-07-01', '2026-09-30');
        $measurement = PdmActivity::create(['asset_ref' => self::ASSET, 'created_by' => $this->owner->id, 'request_key' => (string) Str::uuid(), 'title' => 'Synthetic threshold fixture',
            'template_id' => 'fixture', 'template_fingerprint' => str_repeat('b', 64), 'method' => 'VIBRATION', 'time_precision' => 'date', 'measured_on' => '2026-09-29',
            'instrument' => 'Synthetic instrument', 'measurement_mode' => 'Synthetic mode', 'operating_condition' => 'Synthetic load', 'asset_selection_note' => 'Synthetic exact fixture',
            'template_snapshot' => ['id' => 'fixture', 'preview_only' => false, 'fields' => [['key' => 'v', 'label' => 'Synthetic velocity', 'type' => 'number', 'unit' => 'mm/s']]],
            'readings' => ['v' => ['value' => '0', 'unit' => 'mm/s']]]);
        $payload = $this->wellnessPayload($period, ['pdm_rules' => [['anchor_id' => $measurement->id, 'point' => 'v', 'lower' => 0, 'upper' => 4, 'max_age_days' => 1, 'requirement' => 'Synthetic proposed bounds']], 'anchor_fingerprints' => [$measurement->id => $measurement->analysisBasis()['fingerprint']]]);
        $this->post(route('wellness.policy.store'), $payload)->assertSessionHasNoErrors();
        $r = app(AssetWellness::class)->report(self::ASSET, $period, app(ReliabilityMart::class));
        $this->assertSame([null, null, null, null], array_column($r['components'], 'weight'));
        $this->assertSame(0.0, $r['method_draft']['checks'][0]['value']);
        $this->assertSame(1, $r['method_draft']['checks'][0]['age_days']);
        $this->assertSame('WITHIN_PROPOSED_AGE', $r['method_draft']['checks'][0]['freshness']);
        $this->assertSame('WITHIN_PROPOSED_RANGE', $r['method_draft']['checks'][0]['range']);
        $this->assertSame('2026-09-30', $r['method_draft']['as_of_date']);
        $this->travel(10)->days();
        $later = app(AssetWellness::class)->report(self::ASSET, $period, app(ReliabilityMart::class));
        $this->assertSame(1, $later['method_draft']['checks'][0]['age_days']);
        $measurement->update(['instrument' => 'Corrected synthetic instrument', 'version' => $measurement->version + 1]);
        $changed = app(AssetWellness::class)->report(self::ASSET, $period, app(ReliabilityMart::class));
        $this->assertFalse($changed['method_draft']['checks'][0]['basis_current']);
        $this->assertNull($changed['method_draft']['checks'][0]['value']);
        $this->assertNull($changed['score']);
    }

    public function test_wellness_weight_and_normalization_proposals_never_create_a_score(): void
    {
        $this->outage = false;
        $p = $this->period('2026-07-01', '2026-09-30');
        $components = array_fill_keys(array_keys(AssetWellness::COMPONENTS), ['max_age_days' => null, 'required_evidence' => 'Synthetic evidence requirements', 'weight' => 25, 'normalization' => 'Synthetic proposed mapping, not validated']);
        $this->post(route('wellness.policy.store'), $this->wellnessPayload($p, ['components' => $components]))->assertSessionHasNoErrors();
        $r = app(AssetWellness::class)->report(self::ASSET, $p, app(ReliabilityMart::class));
        $this->assertSame([25, 25, 25, 25], array_column($r['components'], 'weight'));
        $this->assertSame('DRAFT_TOTAL_100', $r['method_draft']['draft_weights']['status']);
        $this->assertNull($r['score']);
        $this->assertNull($r['official_score']);
        $this->assertSame('NOT_ASSESSED', $r['method_draft']['evidence_completeness']);
        $components['pdm']['weight'] = 20;
        $this->post(route('wellness.policy.store'), $this->wellnessPayload($p, ['components' => $components]))->assertSessionHasNoErrors();
        $r = app(AssetWellness::class)->report(self::ASSET, $p, app(ReliabilityMart::class));
        $this->assertSame('SUM_NOT_100', $r['method_draft']['draft_weights']['status']);
        $this->assertNull($r['score']);
        $components['pdm']['weight'] = -1;
        $this->post(route('wellness.policy.store'), $this->wellnessPayload($p, ['components' => $components]))->assertSessionHasErrors('components.pdm.weight');
        $this->get(route('wellness.index', ['asset_ref' => self::ASSET, ...$p->query()]))->assertOk()->assertSee('Total belum 100%')->assertDontSee('45%');
    }

    public function test_missing_period_migration_fails_closed_without_affecting_annual_records(): void
    {
        $annual = $this->saveMethod(ReliabilityPeriod::year(2026));
        $original = $annual->getAttributes();
        unset($original['period_key']);
        $migration = require database_path('migrations/2026_11_10_000001_add_exact_reliability_period_scopes.php');
        $migration->down();
        $period = $this->period('2026-07-01', '2026-07-31');
        $this->assertFalse($period->storageReady('reliability_policies'));
        $this->get(route('reliability.policies', ['asset_ref' => self::ASSET, ...$period->query()]))->assertOk()->assertDontSee('Simpan versi aturan');
        $this->post(route('reliability.policies.store'), $this->methodPayload($period))->assertSessionHasErrors('previous_revision');
        $this->post(route('wellness.policy.store'), $this->wellnessPayload($period))->assertSessionHasErrors('previous_revision');
        $this->assertSame($annual->id, $this->report(ReliabilityPeriod::year(2026))['readiness']['policy']['id']);
        $migration->up();
        $after = $annual->fresh()->getAttributes();
        $this->assertNull($after['period_key']);
        unset($after['period_key']);
        $this->assertSame($original, $after);
    }

    public function test_unqualified_range_and_wrong_roles_cannot_approve(): void
    {
        $period = $this->period('2026-07-01', '2026-07-31');
        $this->failure('2026-07-01T08:00:00+07:00');
        $snapshot = $this->snapshot($period);
        foreach (['ENGINEER', 'ADMIN', 'MANAGER'] as $role) {
            $user = User::factory()->create(['roles' => [$role], 'active' => true])->refresh();
            $this->actingAs($user)->withSession(['auth_version' => $user->auth_version]);
            $this->post(route('reliability.approvals.store', $snapshot), $this->decision($snapshot))->assertForbidden();
        }
        $this->supervisor();
        $this->post(route('reliability.approvals.store', $snapshot), $this->decision($snapshot))->assertSessionHasErrors('metrics');
        $this->assertDatabaseCount('reliability_approvals', 0);
    }

    public static function invalidPeriods(): array
    {
        return [
            'bad mode' => [['period' => '7m']],
            'missing dates' => [['period' => 'custom']],
            'invalid calendar' => [['period' => 'custom', 'start_date' => '2026-02-30', 'end_date' => '2026-03-01']],
            'reversed' => [['period' => 'custom', 'start_date' => '2026-10-02', 'end_date' => '2026-10-01']],
            'open day' => [['period' => 'custom', 'start_date' => '2026-11-01', 'end_date' => '2026-11-09']],
            'future anchor' => [['period' => '3m', 'end_date' => '2027-01-01']],
        ];
    }

    #[DataProvider('invalidPeriods')]
    public function test_invalid_periods_fail_closed_on_both_reports(array $query): void
    {
        foreach (['reliability.index', 'wellness.index', 'reliability.download'] as $route) {
            $this->getJson(route($route, ['asset_ref' => self::ASSET, ...$query]))->assertUnprocessable();
        }
        Http::assertNothingSent();
    }
}
