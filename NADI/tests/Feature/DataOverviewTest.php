<?php

namespace Tests\Feature;

use App\Models\InspectionDraft;
use App\Models\User;
use App\Services\DataOverview;
use App\Services\ReliabilityMart;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Http\Client\Factory;
use Illuminate\Support\Facades\Http;
use Tests\TestCase;

class DataOverviewTest extends TestCase
{
    use RefreshDatabase;

    protected function setUp(): void
    {
        parent::setUp();
        Http::preventStrayRequests();
        config(['services.reliability_mart.url' => 'http://mart.test']);
    }

    private function signIn(string $role = 'ENGINEER'): User
    {
        $user = User::factory()->create(['roles' => [$role]])->refresh();
        $this->actingAs($user)->withSession(['auth_version' => $user->auth_version]);

        return $user;
    }

    private function summary(array $changes = []): array
    {
        return array_replace_recursive([
            'scope' => ['site_code' => 'BSR', 'organization_code' => 'IP', 'unit' => 'CS01', 'population' => 'COLLECTED_HIERARCHY'],
            'counts' => ['total' => 100, 'equipment' => 60, 'component' => 20, 'part' => 10, 'system' => 5, 'unknown' => 5],
            'coverage' => ['state' => 'PARTIAL', 'full_source_baseline_complete' => false, 'last_completed_at' => null, 'pending_projection' => 7],
            'classification' => ['basis' => 'EXACT_SOURCE_ID_WORKBOOK_ROLE', 'status' => 'INDICATIVE_DOCUMENT_ROLE', 'unknown_count' => 5],
            'private' => 'PRIVATE-SOURCE-PAYLOAD',
        ], $changes);
    }

    private function fake(?array $summary = null, int $backlog = 0): void
    {
        Http::fake([
            'mart.test/v1/reliability/maintenance-investigation*' => Http::response([], 503),
            'mart.test/v1/reliability/assets/inventory-summary*' => fn () => Http::response($summary ?? $this->summary()),
            'mart.test/v1/reliability/maintenance-events*' => fn () => Http::response(['items' => [], 'meta' => ['offset' => 0, 'limit' => 10, 'total' => $backlog, 'has_more' => false]]),
        ]);
    }

    public function test_guests_cannot_read_pages_or_download(): void
    {
        foreach (['/', '/data-quality', '/reports', '/reports/summary.csv'] as $path) {
            $this->get($path)->assertRedirect(route('login'));
        }
        Http::assertNothingSent();
    }

    public function test_all_roles_can_read_summary_quality_and_report(): void
    {
        $this->fake();
        foreach (['ADMIN', 'ENGINEER', 'SUPERVISOR', 'MANAGER'] as $role) {
            $this->signIn($role);
            $this->get('/')->assertOk()->assertSee('Ringkasan workspace')->assertSee('Cakupan masih parsial')->assertDontSee('PRIVATE-SOURCE-PAYLOAD');
            $this->get('/data-quality')->assertOk()->assertSee('95,0% berkategori')->assertSee('bukan skor kepercayaan');
            $this->get('/reports')->assertOk()->assertSee('Unduh CSV')->assertSee('bukan laporan tren');
            $this->get('/reports/summary.csv')->assertOk()->assertDownload();
        }
        Http::assertSentCount(36);
        Http::assertNotSent(fn ($request) => $request->method() !== 'GET');
    }

    public function test_counts_use_bounded_approved_endpoints_and_keep_distinct_scopes(): void
    {
        $this->fake();
        $this->signIn();
        $this->get('/')->assertOk()->assertSee('BSR / IP · hierarki CS01')->assertSee('BSR / IP · aset Registry · status WAPPR')
            ->assertSee('bukan total inspeksi unik')->assertSee('7 menunggu proyeksi');
        Http::assertSentCount(3);
        Http::assertSent(fn ($request) => str_contains($request->url(), 'inventory-summary') && $request->data() === ['site_code' => 'BSR', 'organization_code' => 'IP']);
        Http::assertSent(fn ($request) => str_contains($request->url(), 'maintenance-events') && $request->data() === ['status' => 'WAPPR', 'offset' => 0, 'limit' => 10, 'sort' => 'date_desc']);
    }

    public function test_outages_do_not_turn_source_counts_into_zero_or_hide_local_counts(): void
    {
        Http::fake(['mart.test/*' => Http::response('PRIVATE-UPSTREAM', 503)]);
        $this->signIn();
        $this->get('/')->assertOk()->assertSee('Belum tersedia')->assertDontSee('PRIVATE-UPSTREAM');
        $snapshot = app(DataOverview::class)->snapshot(app(ReliabilityMart::class));
        $this->assertNull($snapshot['inventory']);
        $this->assertSame([null, null, 0, 0], array_column($snapshot['metrics'], 'value'));
        $this->assertSame(['UNAVAILABLE', 'UNAVAILABLE', 'AVAILABLE', 'AVAILABLE'], array_column($snapshot['metrics'], 'state'));
    }

    public function test_inventory_failure_does_not_hide_a_valid_backlog_response(): void
    {
        Http::fake([
            'mart.test/v1/reliability/assets/inventory-summary*' => Http::response([], 404),
            'mart.test/v1/reliability/maintenance-events*' => Http::response(['items' => [], 'meta' => ['offset' => 0, 'limit' => 10, 'total' => 0, 'has_more' => false]]),
        ]);
        $snapshot = app(DataOverview::class)->snapshot(app(ReliabilityMart::class));
        $this->assertNull($snapshot['metrics'][0]['value']);
        $this->assertSame(0, $snapshot['metrics'][1]['value']);
    }

    public function test_backlog_failure_does_not_hide_inventory(): void
    {
        Http::fake([
            'mart.test/v1/reliability/assets/inventory-summary*' => Http::response($this->summary()),
            'mart.test/v1/reliability/maintenance-events*' => Http::response([], 503),
        ]);
        $snapshot = app(DataOverview::class)->snapshot(app(ReliabilityMart::class));
        $this->assertSame(100, $snapshot['metrics'][0]['value']);
        $this->assertNull($snapshot['metrics'][1]['value']);
    }

    public function test_verified_zero_population_is_not_a_hundred_percent_quality_score(): void
    {
        $this->fake($this->summary(['counts' => ['total' => 0, 'equipment' => 0, 'component' => 0, 'part' => 0, 'system' => 0, 'unknown' => 0], 'classification' => ['unknown_count' => 0]]));
        $this->signIn();
        $this->get('/data-quality')->assertOk()->assertSee('Tidak ada populasi')->assertDontSee('100,0%');
        $snapshot = app(DataOverview::class)->snapshot(app(ReliabilityMart::class));
        $this->assertSame(0, $snapshot['metrics'][0]['value']);
    }

    public function test_invalid_scope_counts_or_calendar_timestamp_never_become_verified(): void
    {
        foreach ([['scope' => ['unit' => 'CS02']], ['counts' => ['total' => 999]], ['coverage' => ['last_completed_at' => '2026-02-31T12:00:00Z']]] as $change) {
            Http::swap(new Factory);
            Http::preventStrayRequests();
            $this->fake($this->summary($change));
            $snapshot = app(DataOverview::class)->snapshot(app(ReliabilityMart::class));
            $this->assertNull($snapshot['inventory']);
            $this->assertSame('UNAVAILABLE', $snapshot['metrics'][0]['state']);
        }
    }

    public function test_completed_scan_is_distinct_from_current_freshness(): void
    {
        $this->fake($this->summary(['coverage' => ['state' => 'COMPLETE_AS_OF_MANUAL_SCAN', 'full_source_baseline_complete' => true, 'last_completed_at' => '2026-11-06T12:00:00Z', 'pending_projection' => 0]]));
        $this->signIn();
        $this->get('/data-quality')->assertOk()->assertSee('Lengkap saat scan')->assertSee('2026-11-06T12:00:00Z')
            ->assertSee('Belum dapat dipastikan')->assertSee('Bukan waktu sinkronisasi sumber');
    }

    public function test_local_recommendation_count_excludes_empty_drafts_without_exposing_contents(): void
    {
        $this->fake();
        $user = $this->signIn();
        foreach ([null, '', 'PRIVATE-RECOMMENDATION'] as $recommendation) {
            $draft = new InspectionDraft(['request_reference' => 'PRIVATE-REF', 'request_summary' => 'PRIVATE-REQUEST', 'recommendation' => $recommendation]);
            $draft->created_by = $user->id;
            $draft->save();
        }
        $snapshot = app(DataOverview::class)->snapshot(app(ReliabilityMart::class));
        $this->assertSame(1, $snapshot['metrics'][3]['value']);
        $this->get('/reports')->assertOk()->assertDontSee('PRIVATE-RECOMMENDATION')->assertDontSee('PRIVATE-REQUEST');
        $csv = $this->get('/reports/summary.csv')->assertDownload()->streamedContent();
        $this->assertStringNotContainsString('PRIVATE-RECOMMENDATION', $csv);
        $this->assertStringNotContainsString($user->email, $csv);
    }

    public function test_csv_contains_provenance_scope_and_missing_not_zero(): void
    {
        Http::fake(['mart.test/*' => Http::response('PRIVATE-ERROR', 503)]);
        $this->signIn();
        $this->travelTo(now()->setDate(2026, 11, 7)->setTime(10, 0));
        $response = $this->get('/reports/summary.csv')->assertOk()->assertDownload('nadi-ringkasan-20261107-100000.csv');
        $this->assertStringContainsString('no-store', $response->headers->get('Cache-Control'));
        $csv = $response->streamedContent();
        $rows = array_map(fn ($line) => str_getcsv($line, ',', '"', ''), explode("\n", trim(substr($csv, 3))));
        $this->assertSame(['metric', 'value', 'unit', 'state', 'source', 'scope', 'definition_and_limits', 'observed_at'], $rows[0]);
        $this->assertSame(['inventory_total', '', 'aset', 'UNAVAILABLE'], array_slice($rows[1], 0, 4));
        $this->assertSame(['pdm_entries', '0', 'draft', 'AVAILABLE'], array_slice($rows[3], 0, 4));
        $this->assertStringContainsString('BSR / IP', $csv);
        $this->assertStringContainsString('observed_at adalah waktu baca laporan', $csv);
        $this->assertStringNotContainsString('PRIVATE-ERROR', $csv);
        $this->assertSame(1, count(array_unique(array_column(array_slice($rows, 1), 7))));
    }

    public function test_pages_and_download_have_no_write_routes(): void
    {
        $this->signIn();
        foreach (['/', '/data-quality', '/reports', '/reports/summary.csv'] as $path) {
            $this->post($path)->assertStatus(405);
        }
        Http::assertNothingSent();
    }
}
