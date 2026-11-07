<?php

namespace Tests\Feature;

use App\Models\AssetDisruption;
use App\Models\AssetPriority;
use App\Models\InspectionDraft;
use App\Models\User;
use App\Services\AssetAttention;
use App\Services\ReliabilityMart;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Http\Client\Factory;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Str;
use Tests\TestCase;

class AssetPriorityTest extends TestCase
{
    use RefreshDatabase;

    private const ASSET = 'asset:MAXIMO:MXASSET:BSR:IP:SYNTHETIC-A';

    private const OTHER = 'asset:MAXIMO:MXASSET:BSR:IP:SYNTHETIC-B';

    private User $owner;

    protected function setUp(): void
    {
        parent::setUp();
        config(['services.reliability_mart.url' => 'http://mart.test']);
        Http::preventStrayRequests();
        Http::fake([
            'mart.test/v1/reliability/assets/inventory/*' => fn ($request) => Http::response($this->asset(rawurldecode(basename(parse_url($request->url(), PHP_URL_PATH))))),
            'mart.test/v1/reliability/maintenance-investigation*' => fn () => Http::response($this->repeat()),
            'mart.test/*' => Http::response([], 503),
        ]);
        $this->owner = $this->signIn('ENGINEER');
    }

    private function signIn(string $role): User
    {
        $user = User::factory()->create(['roles' => [$role], 'active' => true])->refresh();
        $this->actingAs($user)->withSession(['auth_version' => $user->auth_version]);

        return $user;
    }

    private function asset(string $ref): array
    {
        return ['canonical_id' => $ref, 'site_code' => 'BSR', 'organization_code' => 'IP', 'source_asset_number' => 'SYNTHETIC-A', 'description' => 'Synthetic fixture', 'hierarchy_category' => 'component', 'scope_basis' => 'DIRECT_SOURCE_UNIT', 'registered' => false];
    }

    private function input(array $changes = []): array
    {
        return array_replace(['request_key' => (string) Str::uuid(), 'asset_ref' => self::ASSET, 'urgency' => 'planned', 'observed_condition' => 'Observed vibration, pending confirmation', 'impact' => 'Unknown operation impact', 'reasoning' => 'Review before next maintenance window', 'evidence_note' => 'Manual observation by engineer, instrument check pending', 'owner' => 'Synthetic team', 'review_on' => '2026-12-01'], $changes);
    }

    private function save(array $changes = []): AssetPriority
    {
        $this->post('/priorities', $this->input($changes))->assertSessionHasNoErrors()->assertRedirect();

        return AssetPriority::latest('id')->firstOrFail();
    }

    private function disruption(string $asset = self::ASSET, string $status = 'recorded'): AssetDisruption
    {
        $event = AssetDisruption::create(['created_by' => $this->owner->id, 'request_key' => (string) Str::uuid(), 'asset_ref' => $asset, 'event_type' => 'trip', 'description' => 'Synthetic observation', 'impact' => 'unknown', 'status' => $status]);
        $event->members()->create(['asset_ref' => $asset, 'role' => 'unknown']);

        return $event;
    }

    private function inspection(?string $asset = self::ASSET, string $status = 'open'): InspectionDraft
    {
        return InspectionDraft::create(['created_by' => $this->owner->id, 'asset_ref' => $asset, 'request_reference' => 'SYNTHETIC', 'request_summary' => 'Synthetic review', 'recommendation' => 'Synthetic recommendation', 'follow_up_status' => $status]);
    }

    private function repeat(int $days = 90, int $offset = 0, int $total = 1): array
    {
        return ['scope' => ['site_code' => 'BSR', 'organization_code' => 'IP', 'registry_scope' => 'reliability_asset_registry', 'interpretation' => 'ACTIVITY_NOT_FAILURE', 'date_basis' => 'actual_start of CLOSE WO with verified actual clock and non-task evidence; no timestamp fallback', 'timezone' => 'Asia/Jakarta', 'count_basis' => 'One latest retained WO identity in BSR/IP and the governed Asset Registry; not incidents or labor actions'],
            'window' => ['days' => $days, 'start' => '2026-08-09T00:00:00+07:00', 'as_of' => '2026-11-07T15:00:00+07:00'],
            'activity_evidence' => ['availability' => 'PARTIAL', 'unknown_start_work_orders' => 5, 'unknown_task_work_orders' => 2, 'unknown_status_work_orders' => 0, 'duplicate_records_excluded' => 1],
            'evidence' => ['repeat_failure' => 'BUSINESS_SEMANTICS_REQUIRED'],
            'assets' => $total ? [['asset_ref' => self::OTHER, 'source_asset_number' => 'SYNTHETIC-B', 'description' => '<script>injected</script>', 'event_count' => 3, 'latest_activity' => '2026-11-06T15:00:00+07:00', 'secret' => 'DO-NOT-EXPOSE']] : [],
            'meta' => ['total' => $total, 'offset' => $offset, 'limit' => 10, 'has_more' => false]];
    }

    public function test_engineer_judgment_is_saved_with_links_and_history_without_external_write(): void
    {
        $event = $this->disruption();
        $inspection = $this->inspection();
        $priority = $this->save(['disruption_id' => $event->id, 'inspection_id' => $inspection->id]);
        $this->assertSame(1, $priority->version);
        $this->assertDatabaseCount('asset_priority_revisions', 1);
        $this->get(route('priorities.show', $priority))->assertOk()->assertSee('Observed vibration')->assertSee('Unknown operation impact')->assertSee($event->reference())->assertSee($inspection->reference())->assertSee('Synthetic team');
        $this->get(route('priorities.edit', $priority))->assertOk()->assertSee('name="version"', false);
        $this->get('/action-board')->assertOk()->assertSee('Observed vibration')->assertSee('SYNTHETIC-B')->assertDontSee('<script>injected</script>', false)->assertDontSee('DO-NOT-EXPOSE')->assertSee('Parsial');
        Http::assertNotSent(fn ($request) => $request->method() !== 'GET');
    }

    public function test_work_order_link_is_verified_for_exact_asset_and_inventory_scope(): void
    {
        $ref = 'workorder:MAXIMO:MXWODETAIL:BSR:IP:SYNTHETIC-WO';
        $this->mock(ReliabilityMart::class, function ($mock) use ($ref) {
            $mock->shouldReceive('historyAsset')->once()->with(self::ASSET)->andReturn($this->asset(self::ASSET));
            $mock->shouldReceive('workOrder')->once()->with($ref, null, self::ASSET, true)->andReturn(['work_order_id' => $ref]);
        });
        $priority = $this->save(['work_order_ref' => $ref]);
        $this->get(route('priorities.show', $priority))->assertSee('SYNTHETIC-WO')->assertSee('identitas cocok saat ditautkan');
        $this->mock(ReliabilityMart::class, function ($mock) {
            $mock->shouldReceive('historyAsset')->andReturn($this->asset(self::OTHER));
            $mock->shouldReceive('workOrder')->andThrow(new \RuntimeException('Wrong asset or missing source'));
        });
        $this->post('/priorities', $this->input(['asset_ref' => self::OTHER, 'work_order_ref' => $ref]))->assertSessionHasErrors('work_order_ref');
        $this->assertDatabaseCount('asset_priorities', 1);
    }

    public function test_supported_windows_are_forwarded_without_unbounded_history_fetches(): void
    {
        foreach ([30, 90, 180] as $days) {
            Http::swap(new Factory);
            Http::preventStrayRequests();
            Http::fake(['mart.test/*' => fn () => Http::response($this->repeat(days: $days))]);
            $this->assertSame($days, app(ReliabilityMart::class)->attentionCandidates($days)['window']['days']);
            Http::assertSentCount(1);
            Http::assertSent(fn ($request) => $request['window_days'] === $days && $request['limit'] === 10 && $request['offset'] === 0);
        }
    }

    public function test_duplicate_submit_duplicate_asset_and_competing_engineer_do_not_duplicate_or_overwrite(): void
    {
        $input = $this->input();
        $this->post('/priorities', $input)->assertSessionHasNoErrors();
        $this->post('/priorities', $input)->assertSessionHasNoErrors();
        $priority = AssetPriority::firstOrFail();
        $this->signIn('ENGINEER');
        $this->post('/priorities', $input)->assertStatus(409);
        $this->post('/priorities', $this->input(['observed_condition' => 'Must not overwrite']))->assertRedirect(route('priorities.show', $priority));
        $this->get(route('priorities.create', ['asset_ref' => self::ASSET]))->assertRedirect(route('priorities.show', $priority));
        $this->assertDatabaseCount('asset_priorities', 1);
        $this->assertDatabaseCount('asset_priority_revisions', 1);
        $this->assertSame('Observed vibration, pending confirmation', $priority->fresh()->observed_condition);
    }

    public function test_roles_are_independent_and_only_author_engineer_can_edit(): void
    {
        $priority = $this->save();
        foreach (['ADMIN', 'SUPERVISOR', 'MANAGER'] as $role) {
            $this->signIn($role);
            $this->get('/action-board')->assertOk()->assertDontSee('>Nilai prioritas aset</a>', false);
            $this->get(route('priorities.show', $priority))->assertOk()->assertDontSee('Perbarui penilaian');
            $this->get('/priorities/create')->assertForbidden();
            $this->post('/priorities', $this->input())->assertForbidden();
            $this->get(route('priorities.edit', $priority))->assertForbidden();
            $this->put(route('priorities.update', $priority), [])->assertForbidden();
        }
        $this->signIn('ENGINEER');
        $this->put(route('priorities.update', $priority), [])->assertForbidden();
        $this->delete(route('priorities.show', $priority))->assertStatus(405);
    }

    public function test_updates_retain_history_reject_stale_forms_and_allow_reopen_without_duplicates(): void
    {
        $priority = $this->save();
        $input = $this->input(['version' => 1, 'status' => 'closed', 'change_reason' => 'Action completed after review', 'observed_condition' => 'Reviewed condition']);
        $this->put(route('priorities.update', $priority), $input)->assertSessionHasNoErrors();
        $this->assertSame('closed', $priority->fresh()->status);
        $this->put(route('priorities.update', $priority), $input)->assertSessionHasErrors('version');
        $this->assertDatabaseCount('asset_priority_revisions', 2);
        $this->assertSame('Observed vibration, pending confirmation', $priority->revisions()->where('version', 1)->first()->snapshot['observed_condition']);
        $this->put(route('priorities.update', $priority), array_replace($input, ['version' => 2, 'status' => 'active']))->assertSessionHasNoErrors();
        $this->get(route('priorities.show', $priority))->assertSee('Observed vibration')->assertSee('Reviewed condition');
        $this->assertDatabaseCount('asset_priorities', 1);
        $this->assertDatabaseCount('asset_priority_revisions', 3);
    }

    public function test_required_judgment_dates_identity_and_evidence_are_validated(): void
    {
        foreach ([['urgency' => 'critical_score'], ['owner' => ''], ['review_on' => null], ['review_on' => '2026-02-30'], ['observed_condition' => ''], ['impact' => ''], ['reasoning' => ''], ['evidence_note' => ''], ['asset_ref' => '../bad'], ['work_order_ref' => 'javascript:alert(1)']] as $changes) {
            $this->post('/priorities', $this->input($changes))->assertSessionHasErrors();
        }
        $otherEvent = $this->disruption(self::OTHER);
        $otherInspection = $this->inspection(self::OTHER);
        $this->post('/priorities', $this->input(['disruption_id' => $otherEvent->id]))->assertSessionHasErrors('disruption_id');
        $this->post('/priorities', $this->input(['inspection_id' => $otherInspection->id]))->assertSessionHasErrors('inspection_id');
        $this->assertDatabaseCount('asset_priorities', 0);
        $priority = $this->save();
        $this->put(route('priorities.update', $priority), $this->input(['version' => 1, 'status' => 'active']))->assertSessionHasErrors('change_reason');
        $this->put(route('priorities.update', $priority), $this->input(['version' => 1, 'status' => 'active', 'change_reason' => 'Attempt change', 'asset_ref' => self::OTHER]))->assertSessionHasErrors('asset_ref');
    }

    public function test_local_candidates_merge_sources_by_asset_and_exclude_assessed_voided_completed_unlinked(): void
    {
        $this->disruption();
        $this->disruption();
        $this->inspection();
        $this->inspection(self::OTHER, 'completed');
        $this->disruption(self::OTHER, 'voided');
        $this->inspection(null);
        $page = app(AssetAttention::class)->candidates();
        $this->assertSame(1, $page->total());
        $this->assertSame(2, (int) $page->first()->disruption_count);
        $this->assertSame(1, (int) $page->first()->pdm_count);
        $this->get('/action-board')->assertSee('1 rekomendasi tertunda belum tertaut')->assertSee('2 catatan gangguan manual');
        $this->save();
        $this->assertSame(0, app(AssetAttention::class)->candidates()->total());
    }

    public function test_impacted_asset_is_a_candidate_without_being_inferred_as_cause(): void
    {
        $event = $this->disruption();
        $event->members()->create(['asset_ref' => self::OTHER, 'role' => 'affected']);
        $this->assertSame(2, app(AssetAttention::class)->candidates()->total());
        $this->get('/action-board')->assertSee('Termasuk aset terdampak / peran belum dipastikan');
    }

    public function test_candidates_and_history_are_paginated(): void
    {
        for ($i = 0; $i < 13; $i++) {
            $this->disruption(self::ASSET.$i);
        }
        $page = app(AssetAttention::class)->candidates();
        $this->assertSame(13, $page->total());
        $this->assertCount(10, $page->items());
        $this->get('/action-board?candidate_page=2')->assertViewHas('candidates', fn ($items) => count($items) === 3);
    }

    public function test_source_failure_keeps_local_judgment_readable_and_editable_but_blocks_new_unverified_asset(): void
    {
        $priority = $this->save();
        $this->mock(ReliabilityMart::class, fn ($mock) => $mock->shouldReceive('historyAsset', 'attentionCandidates', 'waitingApproval')->andThrow(new \RuntimeException('Unavailable')));
        $this->get('/action-board')->assertOk()->assertSee('Observed vibration')->assertSee('Sumber kandidat WO belum tersedia');
        $url = route('priorities.create', ['asset_ref' => self::OTHER]);
        $this->from($url)->post('/priorities', $this->input(['asset_ref' => self::OTHER, 'observed_condition' => 'Keep failed input']))->assertSessionHasErrors('asset_ref');
        $this->get($url)->assertOk()->assertSee('Keep failed input')->assertSee('Isian tetap ada');
        $this->put(route('priorities.update', $priority), $this->input(['version' => 1, 'status' => 'active', 'change_reason' => 'Local review during outage']))->assertSessionHasNoErrors();
        $this->assertDatabaseCount('asset_priorities', 1);
    }

    public function test_candidate_api_contract_is_bounded_and_rejects_wrong_or_older_semantics(): void
    {
        $result = app(ReliabilityMart::class)->attentionCandidates();
        $this->assertCount(1, $result['assets']);
        $this->assertArrayNotHasKey('secret', $result['assets'][0]);
        Http::assertSent(fn ($request) => $request->method() === 'GET' && $request['window_days'] === 90 && $request['limit'] === 10 && $request['min_events'] === 2);
        foreach ([['scope.site_code', 'OTHER'], ['scope.date_basis', 'actual_start or source_changed_at'], ['scope.registry_scope', 'all_assets'], ['activity_evidence.availability', 'HEALTHY'], ['activity_evidence.availability', 'UNAVAILABLE'], ['assets.0.latest_activity', '2026-11-06T12:00:00'], ['assets.0.latest_activity', '2030-11-06T12:00:00Z'], ['meta.total', '1'], ['assets.0.event_count', -1], ['assets.0.asset_ref', self::OTHER.'/bad'], ['window.days', 30]] as [$key, $value]) {
            $payload = $this->repeat();
            data_set($payload, $key, $value);
            Http::swap(new Factory);
            Http::preventStrayRequests();
            Http::fake(['mart.test/*' => fn () => Http::response($payload)]);
            $rejected = false;
            try {
                app(ReliabilityMart::class)->attentionCandidates();
            } catch (\RuntimeException) {
                $rejected = true;
            }
            $this->assertTrue($rejected, 'Invalid contract accepted: '.$key);
        }
    }

    public function test_empty_verified_source_differs_from_unavailable_and_never_means_healthy(): void
    {
        Http::swap(new Factory);
        Http::preventStrayRequests();
        Http::fake(['mart.test/*' => fn () => Http::response($this->repeat(total: 0))]);
        $this->assertSame([], app(ReliabilityMart::class)->attentionCandidates()['assets']);
        $this->get('/action-board')->assertOk()->assertSee('Tidak ada kandidat WO yang belum dinilai')->assertDontSee('Sumber kandidat WO belum tersedia')->assertSee('Bukan bukti tidak ada gangguan atau aset sehat');
        Http::swap(new Factory);
        Http::preventStrayRequests();
        Http::fake(['mart.test/*' => Http::response([], 500)]);
        $this->get('/action-board')->assertOk()->assertSee('Sumber kandidat WO belum tersedia')->assertDontSee('0 kandidat WO Registry');
        $this->get('/action-board?window_days=365')->assertSessionHasErrors('window_days');
        $this->get('/action-board?candidate_offset=-1')->assertSessionHasErrors('candidate_offset');
    }

    public function test_assessed_repeat_candidate_is_not_reoffered_as_unassessed(): void
    {
        $this->save(['asset_ref' => self::OTHER]);
        $this->get('/action-board')->assertOk()->assertSee('1 aset sudah dinilai disembunyikan')->assertDontSee('3 WO dalam 90 hari');
    }
}
