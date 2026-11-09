<?php

namespace Tests\Feature;

use App\Models\AssetDisruption;
use App\Models\PdmActivity;
use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Http\Client\Factory;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Str;
use Tests\TestCase;

class AssetTimelineTest extends TestCase
{
    use RefreshDatabase;

    private const ASSET = 'asset:MAXIMO:MXASSET:BSR:IP:TIMELINE';

    protected function setUp(): void
    {
        parent::setUp();
        config(['services.reliability_mart.url' => 'http://mart.test', 'services.asset_mapping.file' => null]);
        Http::preventStrayRequests();
    }

    private function signIn(string $role = 'ENGINEER'): User
    {
        $user = User::factory()->create(['roles' => [$role], 'active' => true])->refresh();
        $this->actingAs($user)->withSession(['auth_version' => $user->auth_version]);

        return $user;
    }

    private function asset(bool $registered = true): array
    {
        return ['canonical_id' => self::ASSET, 'source_asset_number' => 'TIMELINE', 'site_code' => 'BSR', 'organization_code' => 'IP', 'registered' => $registered, 'hierarchy_category' => 'equipment', 'scope_basis' => 'DIRECT_SOURCE_UNIT'];
    }

    private function row(string $id, array $changes = []): array
    {
        return array_replace(['canonical_id' => $id, 'asset_ref' => self::ASSET, 'equipment_id' => self::ASSET, 'site_code' => 'BSR', 'organization_code' => 'IP', 'description' => 'Record '.$id, 'status_changed_at' => '2026-01-03T00:00:00Z', 'lifecycle_status' => 'ACTIVE'], $changes);
    }

    private function context(array $changes = []): array
    {
        return array_replace(['asset' => $this->asset(), 'maintenance' => [], 'fmea' => [], 'health' => [], 'overhauls' => []], $changes);
    }

    private function fake(array $context, bool $registered = true): void
    {
        Http::fake([
            'mart.test/v1/reliability/assets/inventory/*' => fn () => Http::response($this->asset($registered)),
            'mart.test/v1/reliability/assets/*/context' => fn () => Http::response($context),
        ]);
    }

    private function pdm(User $user, string $asset = self::ASSET, string $date = '2026-01-04 00:00:00'): PdmActivity
    {
        return PdmActivity::create(['created_by' => $user->id, 'request_key' => (string) Str::uuid(), 'title' => 'Synthetic PdM timeline', 'asset_ref' => $asset, 'template_id' => 'test', 'template_fingerprint' => str_repeat('a', 64), 'method' => 'VIBRATION', 'measured_at' => $date, 'timezone' => 'Asia/Jakarta', 'operating_condition' => 'Synthetic', 'instrument' => 'Synthetic', 'measurement_mode' => 'RMS', 'asset_selection_note' => 'Synthetic', 'template_snapshot' => [], 'readings' => []]);
    }

    public function test_context_merges_real_domains_and_exact_local_pdm_in_time_order(): void
    {
        $user = $this->signIn();
        $activity = $this->pdm($user);
        $this->pdm($user, 'asset:OTHER')->update(['title' => 'OTHER ASSET PRIVATE']);
        $this->fake($this->context([
            'maintenance' => [$this->row('maintenance:1', ['description' => 'Synthetic WO', 'actual_start' => '2026-01-02T00:00:00Z', 'status' => 'WAPPR', 'work_order_id' => 'workorder:MAXIMO:MXWODETAIL:BSR:IP:WO-1'])],
            'fmea' => [$this->row('fmea:1', ['description' => '<script>FMEA</script>', 'raw_payload' => 'PRIVATE-RAW'])],
            'health' => [$this->row('health:1', ['description' => 'Synthetic health', 'status_changed_at' => null, 'source_created_at' => '2026-01-01T00:00:00Z'])],
            'overhauls' => [$this->row('overhaul:1', ['description' => null, 'source_number' => 'OH-NUMBER', 'planned_start_at' => '2026-02-01T00:00:00Z'])],
        ]));
        $response = $this->get(route('assets.timeline', self::ASSET));
        $response->assertOk()->assertSeeInOrder(['OH-NUMBER', 'Synthetic PdM timeline', '&lt;script&gt;FMEA&lt;/script&gt;', 'Synthetic WO', 'Synthetic health'], false)
            ->assertSee('Maksimal 5 record per domain')->assertSee('bukan seluruh riwayat')
            ->assertSee('Rencana mulai overhaul · bukan pelaksanaan')->assertSee('Menunggu persetujuan/backlog')
            ->assertSee('Draft lokal · belum tervalidasi')->assertSee('Pembuatan record kondisi aset')
            ->assertSee(route('pdm.show', $activity), false)->assertDontSee('OTHER ASSET PRIVATE')->assertDontSee('PRIVATE-RAW')->assertDontSee('<script>FMEA', false);
        Http::assertSentCount(2);
        Http::assertNotSent(fn ($request) => $request->method() !== 'GET');
    }

    public function test_invalid_cross_asset_cross_org_and_duplicate_context_fail_closed(): void
    {
        $user = $this->signIn();
        $this->pdm($user);
        foreach ([
            $this->context(['asset' => $this->asset() + ['extra' => 'ok'], 'fmea' => [$this->row('fmea:1', ['asset_ref' => 'asset:OTHER'])]]),
            $this->context(['health' => [$this->row('health:1', ['organization_code' => 'OTHER'])]]),
            $this->context(['overhauls' => [$this->row('overhaul:1', ['asset_ref' => null])]]),
            $this->context(['fmea' => [$this->row('fmea:1'), $this->row('fmea:1')]]),
            $this->context(['fmea' => array_fill(0, 6, $this->row('fmea:1'))]),
            $this->context(['health' => [$this->row('health:1', ['description' => ['bad']])]]),
        ] as $context) {
            Http::swap(new Factory);
            Http::preventStrayRequests();
            $this->fake($context);
            $this->get(route('assets.timeline', self::ASSET))->assertOk()->assertSee('Belum terhubung / respons tidak valid')->assertSee('Synthetic PdM timeline')->assertDontSee('Record fmea:1')->assertDontSee('Record health:1');
        }
    }

    public function test_remote_outage_keeps_local_pdm_but_asset_outage_reads_no_timeline(): void
    {
        $user = $this->signIn();
        $this->pdm($user);
        Http::fake(['mart.test/v1/reliability/assets/inventory/*' => Http::response($this->asset()), 'mart.test/*' => Http::response([], 503)]);
        $this->get(route('assets.timeline', self::ASSET))->assertOk()->assertSee('Synthetic PdM timeline')->assertSee('Belum terhubung / respons tidak valid');
        Http::swap(new Factory);
        Http::fake(['mart.test/*' => Http::response([], 503)]);
        $this->get(route('assets.timeline', self::ASSET))->assertOk()->assertSee('Aset belum terverifikasi')->assertDontSee('Synthetic PdM timeline');
        Http::assertSentCount(1);
    }

    public function test_nonregistry_inventory_reads_only_exact_scoped_work_orders(): void
    {
        $this->signIn();
        Http::fake([
            'mart.test/v1/reliability/assets/inventory/*' => Http::response($this->asset(false)),
            'mart.test/v1/reliability/inventory-maintenance-events*' => Http::response([
                'items' => [$this->row('maintenance:1', ['status_changed_at' => null, 'source_changed_at' => '2026-01-01T00:00:00Z'])],
                'meta' => ['total' => 1, 'limit' => 25, 'offset' => 0, 'has_more' => false],
                'scope' => ['population' => 'COLLECTED_HIERARCHY', 'asset_ref' => self::ASSET, 'site_code' => 'BSR', 'organization_code' => 'IP', 'date_basis' => 'ACTUAL_START_OR_SOURCE_CHANGED'],
            ]),
        ]);
        $this->get(route('assets.timeline', self::ASSET))->assertOk()->assertSee('Record maintenance:1')->assertSee('Memerlukan Registry')->assertSee('Maksimal 25 WO')->assertSee('Perubahan record WO · bukan waktu kejadian');
        Http::assertSent(fn ($request) => str_contains($request->url(), 'inventory-maintenance-events') && $request['asset_ref'] === self::ASSET && $request['limit'] === 25);
        Http::assertSentCount(2);
    }

    public function test_empty_context_and_invalid_dates_are_not_health_or_event_evidence(): void
    {
        $this->signIn();
        $this->fake($this->context([
            'fmea' => [$this->row('fmea:1', ['status_changed_at' => '2026-02-30T00:00:00Z'])],
            'health' => [$this->row('health:1', ['status_changed_at' => '2026-01-01T00:00:00'])],
            'overhauls' => [$this->row('overhaul:1', ['source_number' => 'UNDATED-OH'])],
        ]));
        $this->get(route('assets.timeline', self::ASSET))->assertOk()->assertSee('Tanggal tidak valid / zona waktu belum jelas')->assertSee('Tanggal belum tersedia')->assertSee('Tanpa waktu terverifikasi')->assertSee('Tidak ada record bukan bukti aset sehat')->assertDontSee('<time', false);
    }

    public function test_local_preview_is_bounded_and_uses_exact_identity(): void
    {
        $user = $this->signIn();
        $oldest = $this->pdm($user, date: '2025-01-01 00:00:00');
        $oldest->update(['title' => 'OLDEST-NOT-IN-PREVIEW']);
        for ($i = 0; $i < 25; $i++) {
            $this->pdm($user);
        }
        $this->fake($this->context());
        $this->get(route('assets.timeline', self::ASSET))->assertOk()->assertSee('25 record pada cuplikan')->assertDontSee('OLDEST-NOT-IN-PREVIEW');
        $this->assertDatabaseCount('pdm_activities', 26);
    }

    public function test_all_roles_have_read_only_timeline_and_guests_are_redirected(): void
    {
        $this->get(route('assets.timeline', self::ASSET))->assertRedirect(route('login'));
        Http::assertNothingSent();
        $this->fake($this->context());
        foreach (['ADMIN', 'ENGINEER', 'SUPERVISOR', 'MANAGER'] as $role) {
            $this->signIn($role);
            $this->get(route('assets.timeline', self::ASSET))->assertOk()->assertSee('Belum ada record yang dapat ditampilkan');
        }
        $this->post(route('assets.timeline', self::ASSET))->assertStatus(405);
    }

    public function test_missing_asset_stays_404_and_does_not_guess_identity(): void
    {
        $this->signIn();
        Http::fake(['mart.test/*' => Http::response([], 404)]);
        $this->get(route('assets.timeline', self::ASSET))->assertNotFound();
        Http::assertSentCount(2);
    }

    private function disruption(User $owner, array $values = [], ?array $members = null): AssetDisruption
    {
        $event = AssetDisruption::create(array_replace(['created_by' => $owner->id, 'request_key' => (string) Str::uuid(), 'asset_ref' => self::ASSET, 'event_type' => 'trip', 'description' => 'Synthetic manual observation', 'impact' => 'unknown', 'occurred_on' => '2026-01-05'], $values));
        $event->members()->createMany($members ?? [['asset_ref' => $event->asset_ref, 'role' => 'unknown']]);

        return $event;
    }

    public function test_manual_observations_join_timeline_by_exact_member_with_distinct_roles(): void
    {
        $owner = $this->signIn();
        $cause = $this->disruption($owner, ['description' => 'PRIMARY-CAUSE'], [['asset_ref' => self::ASSET, 'role' => 'cause']]);
        $affected = $this->disruption($owner, ['asset_ref' => 'asset:OTHER', 'description' => 'AFFECTED-MEMBER'], [['asset_ref' => 'asset:OTHER', 'role' => 'cause'], ['asset_ref' => self::ASSET, 'role' => 'affected']]);
        $this->disruption($owner, ['asset_ref' => 'asset:OTHER', 'description' => 'UNRELATED-MANUAL-OBSERVATION']);
        $this->fake($this->context());
        $response = $this->get(route('assets.timeline', self::ASSET))->assertOk()->assertSee('PRIMARY-CAUSE')->assertSee('AFFECTED-MEMBER')->assertDontSee('UNRELATED-MANUAL-OBSERVATION')
            ->assertSee('Penyebab (menurut catatan)')->assertSee('Terdampak')->assertSee('Log gangguan manual')
            ->assertSee(route('disruptions.show', $cause), false)->assertSee(route('disruptions.show', $affected), false);
        $preview = $response->viewData('preview');
        $this->assertSame(2, $preview['counts']['disruptions']);
        $this->assertSame('available', $preview['states']['disruptions']);
        $this->assertDatabaseCount('asset_disruptions', 3);
        Http::assertSentCount(2);
        Http::assertNotSent(fn ($request) => $request->method() !== 'GET');
    }

    public function test_manual_dates_remain_literal_cancellation_visible_and_unknown_times_sort_last(): void
    {
        $owner = $this->signIn();
        $this->disruption($owner, ['description' => 'DATE-ONLY-OBSERVATION']);
        $this->disruption($owner, ['description' => 'EXACT-TIME-OBSERVATION', 'occurred_at' => '2026-01-04T17:15:23Z', 'timezone' => 'Asia/Jakarta']);
        $this->disruption($owner, ['description' => 'UNKNOWN-TIME-OBSERVATION', 'occurred_on' => null]);
        $this->disruption($owner, ['description' => 'VOIDED-OBSERVATION', 'occurred_on' => '2026-01-03', 'status' => 'voided']);
        $this->fake($this->context());
        $response = $this->get(route('assets.timeline', self::ASSET))->assertOk()->assertSeeInOrder(['EXACT-TIME-OBSERVATION', 'DATE-ONLY-OBSERVATION', 'VOIDED-OBSERVATION', 'UNKNOWN-TIME-OBSERVATION'])
            ->assertSee('05 Jan 2026 00:15:23')->assertSee('Dibatalkan · histori dipertahankan')->assertSee('Tanggal observasi · jam/zona tidak dicatat')->assertSee('Tanpa waktu terverifikasi');
        $rows = collect($response->viewData('preview')['events'])->keyBy('title');
        $this->assertNull($rows['DATE-ONLY-OBSERVATION']['at']);
        $this->assertSame('2026-01-05', $rows['DATE-ONLY-OBSERVATION']['date_only']);
        $this->assertNull($rows['UNKNOWN-TIME-OBSERVATION']['at']);
        $this->assertNull($rows['UNKNOWN-TIME-OBSERVATION']['date_only']);
        $this->assertStringContainsString('bukan status operasi saat ini', $rows['EXACT-TIME-OBSERVATION']['note']);
    }

    public function test_manual_preview_is_bounded_and_reads_small_fields_without_history_snapshots(): void
    {
        $owner = $this->signIn();
        $this->disruption($owner, ['description' => 'OLDEST-MANUAL-OUTSIDE-CUPLIKAN', 'occurred_on' => '2025-01-01']);
        for ($i = 0; $i < 25; $i++) {
            $this->disruption($owner);
        }
        $this->fake($this->context());
        DB::enableQueryLog();
        $response = $this->get(route('assets.timeline', self::ASSET))->assertOk()->assertDontSee('OLDEST-MANUAL-OUTSIDE-CUPLIKAN')->assertSee('25 log gangguan manual');
        $queries = DB::getQueryLog();
        DB::disableQueryLog();
        $this->assertSame(25, $response->viewData('preview')['counts']['disruptions']);
        $this->assertDatabaseCount('asset_disruptions', 26);
        $this->assertFalse(collect($queries)->contains(fn ($q) => str_contains($q['query'], 'asset_disruption_revisions')));
        $eventQuery = collect($queries)->first(fn ($q) => str_contains($q['query'], 'from "asset_disruptions"'));
        $this->assertDoesNotMatchRegularExpression('/^select \*/', $eventQuery['query']);
        $this->assertStringContainsString('limit 25', $eventQuery['query']);
    }

    public function test_manual_observations_remain_during_source_outage_but_still_require_asset_verification(): void
    {
        $owner = $this->signIn();
        $this->disruption($owner);
        Http::fake(['mart.test/v1/reliability/assets/inventory/*' => Http::response($this->asset()), 'mart.test/*' => Http::response([], 503)]);
        $this->get(route('assets.timeline', self::ASSET))->assertOk()->assertSee('Synthetic manual observation')
            ->assertViewHas('preview', fn ($preview) => $preview['states']['disruptions'] === 'available' && $preview['states']['maintenance'] === 'unavailable');
        Http::swap(new Factory);
        Http::preventStrayRequests();
        Http::fake(['mart.test/*' => Http::response([], 503)]);
        $this->get(route('assets.timeline', self::ASSET))->assertOk()->assertSee('Aset belum terverifikasi')->assertDontSee('Synthetic manual observation');
        Http::assertSentCount(1);
    }

    public function test_manual_timeline_supports_nonregistry_and_all_read_roles_without_engineering_writes(): void
    {
        $owner = $this->signIn();
        $this->disruption($owner, ['description' => '<script>MANUAL</script>']);
        Http::fake(['mart.test/v1/reliability/assets/inventory/*' => fn () => Http::response($this->asset(false)), 'mart.test/*' => fn () => Http::response([], 503)]);
        foreach (['ADMIN', 'ENGINEER', 'SUPERVISOR', 'MANAGER'] as $role) {
            $this->signIn($role);
            $this->get(route('assets.timeline', self::ASSET))->assertOk()->assertSee('&lt;script&gt;MANUAL&lt;/script&gt;', false)
                ->assertDontSee('<script>MANUAL</script>', false)->assertSee('Memerlukan Registry')->assertSee('Log gangguan manual');
        }
        $this->assertDatabaseCount('asset_disruptions', 1);
        $this->assertDatabaseCount('asset_disruption_revisions', 0);
        Http::assertNotSent(fn ($request) => $request->method() !== 'GET');
    }

    public function test_source_unknown_or_impossible_offsets_are_not_verified_times_and_future_plans_stay_valid(): void
    {
        $this->signIn();
        $this->fake($this->context(['fmea' => [
            $this->row('fmea:unknown-offset', ['status_changed_at' => '2026-01-01T00:00:00-00:00']),
            $this->row('fmea:impossible-offset', ['status_changed_at' => '2026-01-01T00:00:00+14:30']),
            $this->row('fmea:invalid-minute', ['status_changed_at' => '2026-01-01T00:00:00+07:65']),
        ], 'overhauls' => [$this->row('overhaul:future-plan', ['planned_start_at' => '2099-02-01T00:00:00+07:00'])]]));
        $response = $this->get(route('assets.timeline', self::ASSET))->assertOk();
        $rows = collect($response->viewData('preview')['events'])->keyBy('reference');
        foreach (['fmea:unknown-offset', 'fmea:impossible-offset', 'fmea:invalid-minute'] as $id) {
            $this->assertNull($rows[$id]['at'], $id);
        }
        $this->assertSame('2099-02-01', $rows['overhaul:future-plan']['at']->format('Y-m-d'));
        $this->assertSame('Rencana mulai overhaul · bukan pelaksanaan', $rows['overhaul:future-plan']['basis']);
    }
}
