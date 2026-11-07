<?php

namespace Tests\Feature;

use App\Models\AssetPriority;
use App\Models\InspectionDraft;
use App\Models\User;
use App\Models\WorkspaceActivity;
use App\Services\HomeFeed;
use App\Services\ReliabilityMart;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Schema;
use Illuminate\Support\Str;
use Tests\TestCase;

class HomeFeedTest extends TestCase
{
    use RefreshDatabase;

    private User $owner;

    protected function setUp(): void
    {
        parent::setUp();
        Http::preventStrayRequests();
        config(['services.reliability_mart.url' => 'http://mart.test']);
        Http::fake(['mart.test/*' => Http::response([], 503)]);
        $this->owner = User::factory()->create(['roles' => ['ENGINEER'], 'name' => 'Recorded engineer'])->refresh();
        $this->actingAs($this->owner)->withSession(['auth_version' => $this->owner->auth_version]);
        $this->travelTo(now()->setDate(2026, 11, 7)->setTime(12, 0));
    }

    private function draft(array $changes = []): InspectionDraft
    {
        return InspectionDraft::create([...['created_by' => $this->owner->id, 'request_reference' => 'TEST', 'request_summary' => 'Synthetic draft', 'asset_ref' => 'asset:TEST:LOCAL', 'recommendation' => 'Test recommendation', 'follow_up_status' => 'open'], ...$changes]);
    }

    private function priority(string $asset, string $urgency, ?string $due = null, ?string $review = null): AssetPriority
    {
        return AssetPriority::create(['asset_ref' => $asset, 'created_by' => $this->owner->id, 'request_key' => (string) Str::uuid(), 'urgency' => $urgency, 'status' => 'active', 'observed_condition' => 'Test observation', 'impact' => 'Unknown', 'reasoning' => 'Review evidence', 'evidence_note' => 'Synthetic fixture', 'owner' => 'Test owner', 'due_on' => $due, 'review_on' => $review]);
    }

    public function test_attention_orders_judgment_then_earliest_date_and_displays_both_deadlines(): void
    {
        $this->priority('asset:MONITOR', 'monitor', '2026-01-01');
        $this->priority('asset:PLANNED', 'planned', '2026-11-06', '2026-12-30');
        $this->priority('asset:IMMEDIATE-LATER', 'immediate', '2026-11-10');
        $this->priority('asset:IMMEDIATE-FIRST', 'immediate', '2026-11-05', '2026-12-30');
        $closed = $this->priority('asset:CLOSED', 'immediate');
        $closed->update(['status' => 'closed']);
        $this->draft(['target_completion' => '2026-11-06']);
        $this->draft(['target_completion' => '2026-11-06', 'follow_up_status' => 'completed']);
        $this->draft(['target_completion' => '2027-01-01']);
        $response = $this->get('/?scope=local')->assertOk()->assertSeeInOrder(['IMMEDIATE-FIRST', 'IMMEDIATE-LATER', 'PLANNED', 'MONITOR'])->assertDontSee('asset:CLOSED');
        $feed = $response->viewData('feed');
        $this->assertCount(4, $feed['priorities']);
        $this->assertCount(1, $feed['followUps']);
        $response->assertSee('05 Nov 2026')->assertSee('30 Dec 2026')->assertSee('· lewat');
    }

    public function test_union_is_bounded_sorted_filterable_and_never_infers_updated_events_from_legacy_rows(): void
    {
        for ($i = 0; $i < 30; $i++) {
            $draft = $this->draft();
            DB::table('inspection_drafts')->where('id', $draft->id)->update(['created_at' => now()->subDays(45), 'updated_at' => now()]);
        }
        $page = app(HomeFeed::class)->activities([]);
        $this->assertCount(12, $page);
        $this->assertTrue($page->hasMorePages());
        foreach ($page as $event) {
            $this->assertTrue($event['legacy']);
            $this->assertSame('Draft inspeksi dibuat', $event['title']);
            $this->assertSame('Recorded engineer', $event['actor']);
            $this->assertTrue($event['at']->lt(now()->subDays(30)));
            $this->assertNull($event['asset_ref']); // Current asset is not asserted as original asset.
        }
        $this->assertCount(0, app(HomeFeed::class)->activities(['period' => '7']));
        $this->assertCount(0, app(HomeFeed::class)->activities(['activity_type' => 'pdm']));
        $this->get('/?activity_type=inspection&period=all&scope=local')->assertOk()->assertSee('activity_page=2')->assertSee('activity_type=inspection');
    }

    public function test_audit_events_show_recorded_actor_status_and_exact_scoped_link_without_duplicate_creation(): void
    {
        $draft = $this->draft();
        $actor = User::factory()->create(['name' => '<script>actor</script>']);
        $entry = WorkspaceActivity::create(['kind' => 'inspection', 'subject_id' => $draft->id, 'version' => 1, 'actor_id' => $actor->id, 'asset_ref' => 'asset:ORIGINAL', 'action' => 'created', 'changes' => ['recommendation' => ['before' => null, 'after' => 'new']], 'created_at' => now()->subMinute()]);
        $update = WorkspaceActivity::create(['kind' => 'inspection', 'subject_id' => $draft->id, 'version' => 2, 'actor_id' => $actor->id, 'asset_ref' => 'asset:ORIGINAL', 'action' => 'updated', 'changes' => ['follow_up_status' => ['before' => 'open', 'after' => 'completed']], 'created_at' => now()]);
        $page = app(HomeFeed::class)->activities([]);
        $this->assertCount(2, $page);
        $this->assertSame('Status tindak lanjut: Terbuka → Selesai', $page[0]['detail']);
        $this->assertSame('<script>actor</script>', $page[0]['actor']);
        $this->assertStringContainsString('activity_id='.$update->id.'#activity-'.$update->id, $page[0]['url']);
        $this->get('/?scope=local')->assertOk()->assertSee('Rekomendasi dicatat')->assertDontSee('<script>actor</script>', false);
        $this->get($page[0]['url'])->assertOk()->assertSee('id="activity-'.$update->id.'"', false)->assertDontSee('id="activity-'.$entry->id.'"', false);
        $other = $this->draft();
        $this->get(route('inspections.show', $other).'?activity_id='.$update->id)->assertOk()->assertDontSee('id="activity-'.$update->id.'"', false);
    }

    public function test_revision_link_opens_exact_old_version_and_snapshot_state(): void
    {
        $priority = $this->priority('asset:TEST', 'planned');
        for ($i = 1; $i <= 15; $i++) {
            $priority->revisions()->create(['version' => $i, 'changed_by' => $this->owner->id, 'reason' => 'Revision '.$i, 'snapshot' => [...$priority->snapshot(), 'status' => $i === 1 ? 'active' : 'closed'], 'created_at' => now()->subMinutes($i)]);
        }
        $page = app(HomeFeed::class)->activities(['activity_type' => 'priority']);
        $this->assertStringContainsString('Aktif', $page[0]['detail']);
        $this->get($page[0]['url'])->assertOk()->assertSee('id="revision-1"', false)->assertDontSee('id="revision-15"', false);
    }

    public function test_local_candidate_is_not_a_failure_and_assessed_even_closed_assets_are_excluded(): void
    {
        $this->draft();
        $this->draft(['asset_ref' => 'asset:ASSESSED']);
        $priority = $this->priority('asset:ASSESSED', 'monitor');
        $priority->update(['status' => 'closed']);
        $response = $this->get('/?scope=local')->assertOk();
        $this->assertSame(['asset:TEST:LOCAL'], $response->viewData('feed')['candidates']->pluck('asset_ref')->all());
        $response->assertSee('Bukan diagnosis')->assertSee('Daftar kosong bukan berarti');
        Http::assertSentCount(2);
    }

    public function test_registry_preview_is_bounded_partial_and_excludes_assessed_assets(): void
    {
        $this->priority('asset:ASSESSED', 'planned');
        $this->mock(ReliabilityMart::class, function ($mock) {
            $mock->shouldReceive('inventorySummary')->once()->andThrow(new \RuntimeException);
            $mock->shouldReceive('waitingApproval')->once()->with(0)->andThrow(new \RuntimeException);
            $mock->shouldReceive('attentionCandidates')->once()->with(90, 0)->andReturn(['assets' => [
                ['asset_ref' => 'asset:ASSESSED', 'source_asset_number' => 'ASSESSED', 'event_count' => 8],
                ['asset_ref' => 'asset:REVIEW', 'source_asset_number' => 'REVIEW', 'event_count' => 3],
            ], 'coverage' => ['availability' => 'PARTIAL', 'unknown_start_work_orders' => 2, 'unknown_task_work_orders' => 1, 'unknown_status_work_orders' => 0], 'window' => ['start' => '2026-08-09T00:00:00+07:00', 'as_of' => '2026-11-07T19:00:00+07:00']]);
        });
        $response = $this->get('/?scope=registry')->assertOk()->assertSee('Bukti parsial')->assertSee('WO berulang bukan failure berulang')->assertSee('REVIEW')->assertDontSee('>ASSESSED<', false);
        $this->assertFalse($response->viewData('feed')['local']);
        $this->assertNull($response->viewData('feed')['activities']);
    }

    public function test_outage_and_unknown_freshness_never_show_safe_or_fake_zero_counts(): void
    {
        $this->get('/')->assertOk()->assertSee('Jumlah tidak diketahui, bukan nol')->assertSee('Belum dapat dipastikan')->assertSee('Data kosong / belum tersedia bukan aman');
        $response = $this->get('/?freshness=unknown')->assertOk();
        $this->assertFalse($response->viewData('feed')['local']);
        $this->assertTrue($response->viewData('feed')['registry']);
        $this->get('/?scope=local&freshness=unknown')->assertOk()->assertSee('Tidak ada sumber yang cocok');
        Schema::drop('workspace_activities');
        $response = $this->get('/?scope=local')->assertOk()->assertSee('Riwayat aktivitas belum dapat dibaca');
        $this->assertNotNull($response->viewData('feed')['priorities']);
    }

    public function test_filters_are_validated_before_reads_and_all_roles_have_read_only_feed(): void
    {
        foreach (['activity_type=sql', 'scope=admin', 'freshness=fresh', 'period=3650', 'activity_page=1001'] as $query) {
            $this->getJson('/?'.$query)->assertUnprocessable();
        }
        Http::assertNothingSent();
        foreach (['ADMIN', 'ENGINEER', 'SUPERVISOR', 'MANAGER'] as $role) {
            $user = User::factory()->create(['roles' => [$role]])->refresh();
            $this->actingAs($user)->withSession(['auth_version' => $user->auth_version]);
            $this->get('/')->assertOk()->assertSee('Perlu perhatian')->assertSee('Aktivitas terbaru')->assertSee('Kandidat untuk ditinjau')->assertSee('Kualitas data');
        }
        Http::assertNotSent(fn ($request) => $request->method() !== 'GET');
    }
}
