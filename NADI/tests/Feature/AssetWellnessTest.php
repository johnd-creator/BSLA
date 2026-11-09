<?php

namespace Tests\Feature;

use App\Models\AssetDisruption;
use App\Models\AssetPriority;
use App\Models\InspectionDraft;
use App\Models\PdmActivity;
use App\Models\ReliabilityReview;
use App\Models\User;
use App\Models\WorkspaceActivity;
use App\Services\AssetWellness;
use App\Services\ReliabilityMart;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Str;
use Tests\TestCase;

class AssetWellnessTest extends TestCase
{
    use RefreshDatabase;

    private const ASSET = 'asset:MAXIMO:MXASSET:BSR:IP:WELLNESS-FIXTURE';

    private User $owner;

    private bool $outage = false;

    protected function setUp(): void
    {
        parent::setUp();
        $this->travelTo(now()->setDateTime(2026, 11, 9, 12, 0, 0));
        config(['services.reliability_mart.url' => 'http://mart.test']);
        Http::preventStrayRequests();
        Http::fake(function ($r) {
            if ($this->outage) {
                return Http::response([], 503);
            }
            if (str_contains($r->url(), 'annual-summary')) {
                return Http::response(['scope' => ['asset_ref' => $r['asset_ref'], 'population' => $r['population'], 'site_code' => 'BSR', 'organization_code' => 'IP', 'date_basis' => 'ACTUAL_START', 'time_zone' => 'Asia/Jakarta', 'count_basis' => 'UNIQUE_WORK_ORDER_ID'],
                    'availability_state' => 'REQUIRES_VALIDATED_DCS_HISTORY', 'counts' => ['record_count' => 8, 'work_order_count' => 7, 'dated_work_order_count' => 5, 'unknown_date_work_order_count' => 1, 'duplicate_work_order_count' => 1, 'duplicate_record_count' => 2, 'missing_identity_record_count' => 0],
                    'years' => [['year' => 2026, 'work_orders' => 5, 'work_types' => [['value' => 'CM', 'count' => 5]], 'statuses' => [['value' => 'CLOSE', 'count' => 5]]]], 'unknown_year' => ['year' => null, 'work_orders' => 1, 'work_types' => [['value' => null, 'count' => 1]], 'statuses' => [['value' => 'WAPPR', 'count' => 1]]]]);
            }
            if (str_contains($r->url(), '/assets/')) {
                return Http::response(['canonical_id' => rawurldecode(basename(parse_url($r->url(), PHP_URL_PATH))), 'site_code' => 'BSR', 'organization_code' => 'IP', 'registered' => false, 'hierarchy_category' => 'equipment', 'scope_basis' => 'DIRECT_SOURCE_UNIT', 'description' => 'SYNTHETIC Wellness fixture']);
            }

            return Http::response([], 503);
        });
        $this->owner = User::factory()->create(['roles' => ['ENGINEER'], 'active' => true])->refresh();
        $this->actingAs($this->owner)->withSession(['auth_version' => $this->owner->auth_version]);
    }

    private function report(int $year = 2026, string $asset = self::ASSET): array
    {
        return app(AssetWellness::class)->report($asset, $year, app(ReliabilityMart::class));
    }

    private function page(int $year = 2026)
    {
        return $this->get(route('wellness.index', ['asset_ref' => self::ASSET, 'year' => $year]));
    }

    private function measurement(array $extra = []): PdmActivity
    {
        return PdmActivity::create(array_replace(['asset_ref' => self::ASSET, 'created_by' => $this->owner->id, 'request_key' => (string) Str::uuid(), 'title' => 'SYNTHETIC measurement', 'template_id' => 'fixture', 'template_fingerprint' => str_repeat('a', 64), 'method' => 'VIBRATION', 'time_precision' => 'date', 'measured_on' => '2026-07-08', 'instrument' => 'Synthetic fixture only', 'measurement_mode' => 'test', 'operating_condition' => 'unknown', 'asset_selection_note' => 'exact fixture', 'template_snapshot' => [], 'readings' => ['v' => ['value' => '0', 'unit' => 'mm/s']]], $extra));
    }

    private function failure(array $extra = []): AssetDisruption
    {
        $event = AssetDisruption::create(['asset_ref' => self::ASSET, 'created_by' => $this->owner->id, 'request_key' => (string) Str::uuid(), 'event_type' => 'trip', 'description' => 'SYNTHETIC failure', 'impact' => 'unknown', 'occurred_on' => '2026-02-01']);
        $event->members()->create(['asset_ref' => self::ASSET, 'role' => 'affected']);
        ReliabilityReview::create(array_replace(['asset_disruption_id' => $event->id, 'asset_ref' => self::ASSET, 'revision' => 1, 'event_version' => 1, 'created_by' => $this->owner->id, 'request_key' => (string) Str::uuid(), 'classification' => 'failure', 'required_function' => 'Fixture flow delivery', 'evidence' => 'Synthetic reference', 'reason' => 'Synthetic review only', 'failure_at' => '2026-02-01 01:00:00', 'repair_state' => 'unknown', 'active_intervals' => [], 'rule_version' => ReliabilityReview::RULE, 'event_snapshot' => $event->snapshot(), 'created_at' => now()], $extra));

        return $event;
    }

    public function test_landing_is_read_only_and_does_not_fetch_sources_without_asset(): void
    {
        $this->get('/asset-wellness')->assertOk()->assertSee('Pilih aset untuk mulai')->assertSee('Bobot ilustratif');
        Http::assertNothingSent();
        $this->post('/asset-wellness')->assertStatus(405);
    }

    public function test_missing_data_never_becomes_100_or_a_health_category(): void
    {
        $report = $this->report();
        $this->assertNull($report['score']);
        $this->assertNull($report['official_score']);
        $this->assertSame('DRAFT_NOT_APPROVED', $report['method_status']);
        $this->assertSame([45, 25, 20, 10], array_column($report['components'], 'weight'));
        $this->assertSame([null, null, null, null], array_column($report['components'], 'score'));
        $this->assertNull($report['components']['operations']['evidence']['coverage_percent']);
        $this->assertSame(0, $report['components']['failure']['evidence']['reviewed_onset_count']);
        $this->page()->assertOk()->assertSee('Belum cukup data')->assertSee('Belum dapat dinilai')->assertSee('Criticality aset')->assertSee('Belum dipetakan')->assertHeader('Cache-Control', 'no-store, private');
    }

    public function test_wo_counts_and_close_status_do_not_become_failure_or_wellness(): void
    {
        $report = $this->report();
        $this->assertSame(5, $report['components']['maintenance']['evidence']['work_order_count']);
        $this->assertSame(0, $report['components']['failure']['evidence']['reviewed_onset_count']);
        $this->assertNull($report['score']);
        $this->assertNull($report['components']['maintenance']['score']);
        $this->assertStringNotContainsString('view=annual', $report['components']['maintenance']['url']);
        Http::assertNotSent(fn ($r) => $r->method() !== 'GET');
    }

    public function test_source_outage_stays_null_while_local_evidence_remains(): void
    {
        $this->measurement();
        $this->outage = true;
        $report = $this->report();
        $this->assertNull($report['asset']);
        $this->assertNull($report['components']['maintenance']['evidence']['work_order_count']);
        $this->assertSame(1, $report['components']['pdm']['evidence']['count']);
        $this->page()->assertOk()->assertSee('Sumber WO tidak tersedia, bukan nol.')->assertSee('Identitas sumber belum dapat dibaca');
    }

    public function test_date_only_and_exact_asset_year_are_preserved(): void
    {
        $activity = $this->measurement();
        $this->measurement(['asset_ref' => self::ASSET.'-OTHER']);
        $this->measurement(['measured_on' => '2025-07-08']);
        $pdm = $this->report()['components']['pdm']['evidence'];
        $this->assertSame(1, $pdm['count']);
        $this->assertSame(1, $pdm['quality']['date_only']);
        $this->assertSame($activity->id, $pdm['rows'][0]['id']);
        $this->page()->assertSee('08 Jul 2026')->assertSee('Tanggal saja')->assertDontSee('08 Jul 2026 00:00');
    }

    public function test_current_then_corrected_pdm_analysis_becomes_stale_without_guessing_condition(): void
    {
        $activity = $this->measurement();
        $inspection = InspectionDraft::create(['asset_ref' => self::ASSET, 'created_by' => $this->owner->id, 'pdm_activity_id' => $activity->id, 'request_reference' => 'FIXTURE', 'request_summary' => 'Synthetic request', 'finding' => 'Synthetic finding', 'follow_up_status' => 'open']);
        WorkspaceActivity::create(['kind' => 'inspection', 'subject_id' => $inspection->id, 'version' => 1, 'actor_id' => $this->owner->id, 'asset_ref' => self::ASSET, 'action' => 'updated', 'changes' => ['pdm_basis' => ['after' => $activity->analysisBasis()]], 'created_at' => now()]);
        $this->assertSame(1, $this->report()['components']['pdm']['evidence']['quality']['current_analysis']);
        $activity->update(['instrument' => 'Corrected synthetic instrument']);
        $report = $this->report();
        $this->assertSame(1, $report['components']['pdm']['evidence']['quality']['stale_analysis']);
        $this->assertNull($report['components']['pdm']['score']);
    }

    public function test_pdm_limit_is_visible_not_silent_full_coverage(): void
    {
        $first = $this->measurement();
        for ($i = 0; $i < AssetWellness::PDM_LIMIT; $i++) {
            $copy = $first->replicate();
            $copy->request_key = (string) Str::uuid();
            $copy->save();
        }
        $pdm = $this->report()['components']['pdm']['evidence'];
        $this->assertTrue($pdm['truncated']);
        $this->assertSame(501, $pdm['count']);
        $this->assertSame(500, $pdm['inspected_count']);
        $this->assertCount(8, $pdm['rows']);
        $this->page()->assertSee('Parsial: kualitas diperiksa hanya pada 500');
    }

    public function test_duplicate_stale_and_missing_onset_do_not_inflate_reviewed_failure_count(): void
    {
        $root = $this->failure();
        $this->failure(['classification' => 'duplicate', 'duplicate_of' => $root->id, 'duplicate_version' => 1, 'duplicate_review_revision' => 1]);
        $this->failure(['event_version' => 99]);
        $this->failure(['failure_at' => null]);
        $evidence = $this->report()['components']['failure']['evidence'];
        $this->assertSame(1, $evidence['reviewed_onset_count']);
        $this->assertSame(1, $evidence['quality']['duplicate']);
        $this->assertSame(1, $evidence['quality']['stale']);
        $this->assertSame(1, $evidence['quality']['missing_failure_time']);
        $this->assertCount(1, $evidence['rows']);
        $root->version = 2;
        $root->save();
        $this->assertSame(0, $this->report()['components']['failure']['evidence']['reviewed_onset_count']);
    }

    public function test_priority_is_independent_of_year_score_criticality_and_source_availability(): void
    {
        $priority = AssetPriority::create(['asset_ref' => self::ASSET, 'created_by' => $this->owner->id, 'request_key' => (string) Str::uuid(), 'urgency' => 'immediate', 'status' => 'active', 'observed_condition' => '<script>fixture</script>', 'impact' => 'Synthetic impact', 'reasoning' => 'Synthetic evidence review', 'evidence_note' => 'Synthetic only', 'owner' => 'Test']);
        $this->outage = true;
        $report = $this->report(2025);
        $this->assertTrue($report['attention_required']);
        $this->assertSame('Belum dipetakan', $report['criticality']);
        $this->assertNull($report['score']);
        $this->page(2025)->assertSee('Perlu perhatian segera')->assertDontSee('<script>fixture</script>', false)->assertSee('&lt;script&gt;fixture&lt;/script&gt;', false);
        $priority->update(['status' => 'closed']);
        $this->assertFalse($this->report()['attention_required']);
        $this->page()->assertSee('Ini bukan pernyataan aman');
    }

    public function test_verified_operating_coverage_does_not_score_process_condition(): void
    {
        $this->post(route('reliability.operating.store'), ['asset_ref' => self::ASSET, 'version' => 0, 'request_key' => (string) Str::uuid(), 'started_at' => '2025-01-01T00:00:00+07:00', 'ended_at' => '2026-01-01T00:00:00+07:00', 'state' => 'STANDBY', 'review_state' => 'verified', 'source' => 'Synthetic only', 'evidence' => 'Synthetic complete calendar interval', 'reason' => 'Fixture, not operational evidence', 'attestation' => 1])->assertSessionHasNoErrors();
        $report = $this->report(2025);
        $this->assertEquals(100, $report['components']['operations']['evidence']['coverage_percent']);
        $this->assertSame(0, $report['components']['operations']['evidence']['operating_seconds']);
        $this->assertNull($report['components']['operations']['score']);
        $this->assertNull($report['score']);
    }

    public function test_all_active_roles_can_read_but_no_wellness_write_route_exists(): void
    {
        foreach (['ADMIN', 'SUPERVISOR', 'MANAGER', 'ENGINEER'] as $role) {
            $user = User::factory()->create(['roles' => [$role], 'active' => true])->refresh();
            $this->actingAs($user)->withSession(['auth_version' => $user->auth_version]);
            $this->page()->assertOk();
            $this->put('/asset-wellness')->assertStatus(405);
        }
    }

    public function test_guest_and_invalid_identity_cannot_read_an_asset_report(): void
    {
        foreach (['asset:MAXIMO:MXASSET:BSR:IP:../../x', 'wrong', str_repeat('x', 241)] as $bad) {
            $this->getJson(route('wellness.index', ['asset_ref' => $bad]))->assertUnprocessable();
        }
        $this->getJson(route('wellness.index', ['asset_ref' => self::ASSET, 'year' => 2027]))->assertUnprocessable();
        Http::assertNothingSent();
        auth()->logout();
        $this->page()->assertRedirect('/login');
    }

    public function test_repeated_get_does_not_create_or_mutate_engineering_records(): void
    {
        $activity = $this->measurement();
        $before = $activity->fresh()->getAttributes();
        $this->page()->assertOk();
        $this->page()->assertOk();
        $this->assertSame($before, $activity->fresh()->getAttributes());
        foreach (['reliability_snapshots', 'reliability_approvals', 'asset_priorities', 'reliability_reviews'] as $table) {
            $this->assertDatabaseCount($table, 0);
        }
    }
}
