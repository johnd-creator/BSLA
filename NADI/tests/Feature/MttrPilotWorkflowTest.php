<?php

namespace Tests\Feature;

use App\Models\AssetDisruption;
use App\Models\OperatingLog;
use App\Models\ReliabilityApproval;
use App\Models\ReliabilityReview;
use App\Models\ReliabilitySnapshot;
use App\Models\User;
use App\Services\ReliabilityEvidence;
use App\Services\ReliabilityMart;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Http\Client\Factory;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Str;
use Tests\TestCase;

/** Synthetic fixtures stay in the PHPUnit in-memory store, never the preview. */
class MttrPilotWorkflowTest extends TestCase
{
    use RefreshDatabase;

    private const ASSET = 'asset:MAXIMO:MXASSET:BSR:IP:MTTR-PILOT-QA';

    private const OTHER = 'asset:MAXIMO:MXASSET:BSR:IP:MTTR-PILOT-OTHER-QA';

    private User $engineer;

    protected function setUp(): void
    {
        parent::setUp();
        $this->travelTo(now()->setDateTime(2026, 11, 9, 8, 0, 0));
        config(['services.reliability_mart.url' => 'http://mart.test']);
        Http::preventStrayRequests();
        Http::fake(fn ($request) => str_contains($request->url(), '/assets/')
            ? Http::response(['canonical_id' => rawurldecode(basename(parse_url($request->url(), PHP_URL_PATH))), 'site_code' => 'BSR', 'organization_code' => 'IP', 'registered' => false, 'scope_basis' => 'DIRECT_SOURCE_UNIT', 'hierarchy_category' => 'equipment', 'description' => 'Synthetic MTTR pilot asset'])
            : Http::response([], 503));
        $this->engineer = User::factory()->create(['roles' => ['ENGINEER'], 'active' => true])->refresh();
        $this->asUser($this->engineer);
    }

    private function asUser(User $user): void
    {
        $this->actingAs($user)->withSession(['auth_version' => $user->auth_version]);
    }

    private function observation(string $date, bool $multiAsset = false): AssetDisruption
    {
        $this->post(route('disruptions.store'), ['request_key' => (string) Str::uuid(), 'asset_ref' => self::ASSET,
            'asset_role' => 'affected', 'affected_refs' => $multiAsset ? self::OTHER : null,
            'event_type' => 'trip', 'impact' => 'unknown', 'occurred_on' => $date,
            'description' => 'Synthetic observation, not an operational event', 'evidence_note' => 'Synthetic operator record'])
            ->assertSessionHasNoErrors()->assertRedirect();

        return AssetDisruption::latest('id')->firstOrFail();
    }

    private function reviewPayload(AssetDisruption $event, string $onset, string $restored): array
    {
        return ['request_key' => (string) Str::uuid(), 'asset_ref' => self::ASSET,
            'event_version' => $event->fresh()->version,
            'previous_revision' => ReliabilityReview::where('asset_disruption_id', $event->id)->where('asset_ref', self::ASSET)->max('revision') ?? 0,
            'classification' => 'failure', 'required_function' => 'Supply required process air',
            'evidence' => 'Synthetic signed operator log and functional check', 'reason' => 'Synthetic loss of required function confirmed',
            'failure_at' => $onset, 'restored_at' => $restored, 'repair_state' => 'unknown',
            'timing_evidence' => 'Synthetic onset and return-to-service log, explicit WIB clock; active labor time unknown', 'attestation' => 1];
    }

    private function policy(int $revision = 0): void
    {
        $this->post(route('reliability.policies.store'), ['request_key' => (string) Str::uuid(), 'asset_ref' => self::ASSET, 'year' => 2026,
            'previous_revision' => $revision, 'status' => 'reviewed_local', 'required_function' => 'Supply required process air',
            'failure_definition' => 'Loss of required process air confirmed by operator', 'exposure_basis' => 'undecided',
            'mttr_basis' => 'restoration', 'recurrence_policy' => 'restored_before_recurrence', 'incomplete_policy' => 'withhold',
            'failure_scope' => 'attested_same_function', 'failure_coverage' => 'attested_complete',
            'failure_coverage_evidence' => 'Synthetic observed episode population reconciled, no unresolved episode',
            'evidence' => 'Synthetic restoration definition includes waiting and return-to-service checks',
            'reason' => 'Synthetic selected local method, no operating exposure claimed', 'attestation' => 1])
            ->assertSessionHasNoErrors()->assertRedirect();
    }

    private function snapshot(array $payload = []): ReliabilitySnapshot
    {
        $this->post(route('reliability.snapshots.store'), [...['request_key' => (string) Str::uuid(), 'asset_ref' => self::ASSET, 'year' => 2026], ...$payload])
            ->assertSessionHasNoErrors()->assertRedirect();

        return ReliabilitySnapshot::latest('id')->firstOrFail();
    }

    private function approval(ReliabilitySnapshot $snapshot, int $revision = 0): array
    {
        return ['request_key' => (string) Str::uuid(), 'previous_revision' => $revision, 'decision' => 'approved',
            'calculation_hash' => $snapshot->report['calculation']['calculation_hash'], 'metrics' => ['mttr'],
            'evidence' => 'Synthetic Supervisor checked exact episode population and restoration arithmetic',
            'reason' => 'Synthetic scope-limited decision', 'method_attestation' => 1, 'result_attestation' => 1];
    }

    private function report(): array
    {
        return app(ReliabilityEvidence::class)->report(self::ASSET, 2026, app(ReliabilityMart::class));
    }

    public function test_restoration_pilot_through_forms_review_snapshot_approval_and_reconciliation_without_historian(): void
    {
        $first = $this->observation('2026-02-01');
        $second = $this->observation('2026-02-03');
        foreach ([[$first, '2026-02-01T08:00:00+07:00', '2026-02-01T12:00:00+07:00'], [$second, '2026-02-03T08:00:00+07:00', '2026-02-03T10:00:00+07:00']] as [$event, $onset, $restored]) {
            $this->get(route('reliability.reviews', [$event, 'asset_ref' => self::ASSET]))->assertOk();
            $data = $this->reviewPayload($event, $onset, $restored);
            $this->post(route('reliability.reviews.store', $event), $data)->assertSessionHasNoErrors();
            $this->post(route('reliability.reviews.store', $event), $data)->assertSessionHasNoErrors();
        }
        $this->assertSame(2, ReliabilityReview::count());
        $this->assertNull($first->fresh()->restored_at); // A per-asset review never rewrites the observation.
        $this->policy();
        $snapshot = $this->snapshot();
        $original = $snapshot->report;
        $metric = $original['calculation']['pilot']['mttr'];
        $this->assertSame('PILOT_CALCULATED', $metric['status']);
        $this->assertEquals(3, $metric['value']);
        $this->assertSame(21600, $metric['numerator_seconds']);
        $this->assertSame(2, $metric['denominator_episodes']);
        $this->assertSame([$first->id, $second->id], $metric['event_ids']);
        $this->assertNull($original['calculation']['pilot']['active_repair']['value']);
        $this->assertNull($original['calculation']['pilot']['mtbf']['value']);
        $this->assertSame('UNAVAILABLE', $original['work_orders']['state']);
        $this->assertSame(0, OperatingLog::count());
        $this->assertNull($original['metrics']['mttr']['value']);
        $this->post(route('reliability.approvals.store', $snapshot), $this->approval($snapshot))->assertForbidden();
        $supervisor = User::factory()->create(['roles' => ['SUPERVISOR'], 'active' => true])->refresh();
        $this->asUser($supervisor);
        $decision = $this->approval($snapshot);
        $this->post(route('reliability.approvals.store', $snapshot), $decision)->assertSessionHasNoErrors();
        $this->post(route('reliability.approvals.store', $snapshot), $decision)->assertSessionHasNoErrors();
        $this->assertSame(1, ReliabilityApproval::count());
        $this->assertSame('OFFICIAL_APPROVED', $this->report()['metrics']['mttr']['status']);
        $this->assertNull($this->report()['metrics']['mtbf']['value']);
        $packet = $this->get(route('reliability.approvals.download', $snapshot))->assertOk()->json();
        $this->assertSame('APPROVED', $packet['status']['status']);
        $this->assertSame($original, $packet['original_report']);

        $this->asUser($this->engineer);
        $this->post(route('reliability.reviews.store', $first), $this->reviewPayload($first, '2026-02-01T08:00:00+07:00', '2026-02-01T14:00:00+07:00'))->assertSessionHasNoErrors();
        $this->assertSame('STALE', $this->report()['approval']['status']);
        $this->assertNull($this->report()['metrics']['mttr']['value']);
        $this->assertContains('FAILURE_SCOPE_ATTESTATION_STALE', $this->report()['calculation']['pilot']['mttr']['blockers']);
        $this->policy(1);
        $new = $this->snapshot();
        $this->asUser($supervisor);
        $this->post(route('reliability.approvals.store', $snapshot), $this->approval($snapshot, 1))->assertSessionHasErrors('calculation_hash');
        $this->post(route('reliability.approvals.store', $new), $this->approval($new, 1))->assertSessionHasNoErrors();
        $this->assertEquals(4, $this->report()['metrics']['mttr']['value']);
        $this->assertSame($original, $snapshot->fresh()->report);
        $this->assertEquals(3, ReliabilityApproval::first()->approved_values['mttr']['value']);
        $this->assertSame(0, OperatingLog::count());
        Http::assertNotSent(fn ($request) => $request->method() !== 'GET' || parse_url($request->url(), PHP_URL_HOST) !== 'mart.test');
    }

    public function test_snapshot_replay_is_bound_to_exact_asset_and_year_before_source_reads(): void
    {
        $payload = ['request_key' => (string) Str::uuid(), 'asset_ref' => self::ASSET, 'year' => 2026];
        $snapshot = $this->snapshot($payload);
        Http::swap(new Factory);
        Http::preventStrayRequests();
        Http::fake(fn () => Http::response([], 503));
        $this->post(route('reliability.snapshots.store'), $payload)->assertRedirect(route('reliability.snapshots.show', $snapshot));
        $this->post(route('reliability.snapshots.store'), [...$payload, 'asset_ref' => self::OTHER])->assertConflict();
        $this->post(route('reliability.snapshots.store'), [...$payload, 'year' => 2025])->assertConflict();
        $this->post(route('reliability.snapshots.store'), ['request_key' => $payload['request_key']])->assertUnprocessable();
        $this->assertSame(1, ReliabilitySnapshot::count());
        Http::assertNothingSent();
    }

    public function test_review_replay_cannot_claim_a_different_member_asset_was_reviewed(): void
    {
        $event = $this->observation('2026-02-01', true);
        $payload = $this->reviewPayload($event, '2026-02-01T08:00:00+07:00', '2026-02-01T12:00:00+07:00');
        $this->post(route('reliability.reviews.store', $event), $payload)->assertSessionHasNoErrors();
        $this->post(route('reliability.reviews.store', $event), $payload)->assertSessionHasNoErrors();
        $this->post(route('reliability.reviews.store', $event), [...$payload, 'asset_ref' => self::OTHER])->assertConflict();
        $this->assertSame(1, ReliabilityReview::count());
        $this->assertSame(self::ASSET, ReliabilityReview::first()->asset_ref);
    }
}
