<?php

namespace Tests\Feature;

use App\Models\AssetDisruption;
use App\Models\AssetPriority;
use App\Models\InspectionDraft;
use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Str;
use Tests\TestCase;

class WorkflowJourneyTest extends TestCase
{
    use RefreshDatabase;

    private const ASSET = 'asset:MAXIMO:MXASSET:BSR:IP:QA-JOURNEY';

    protected function setUp(): void
    {
        parent::setUp();
        $this->travelTo(now()->setDate(2026, 11, 7)->setTime(12, 0));
        config(['services.reliability_mart.url' => 'http://journey.test']);
        Http::preventStrayRequests();
        Http::fake([
            'journey.test/v1/reliability/assets/inventory/*' => fn () => Http::response(['canonical_id' => self::ASSET, 'site_code' => 'BSR', 'organization_code' => 'IP', 'source_asset_number' => 'QA-JOURNEY', 'description' => 'Hermetic workflow fixture', 'hierarchy_category' => 'component', 'scope_basis' => 'DIRECT_SOURCE_UNIT', 'registered' => false]),
            'journey.test/*' => Http::response([], 503),
        ]);
        $user = User::factory()->create(['roles' => ['ENGINEER'], 'name' => 'Journey engineer'])->refresh();
        $this->actingAs($user)->withSession(['auth_version' => $user->auth_version]);
    }

    private function recommendation(): array
    {
        return ['request_key' => (string) Str::uuid(), 'inspection_type' => 'routine', 'request_reference' => 'QA-JOURNEY', 'request_summary' => 'Routine vibration review', 'asset_ref' => self::ASSET, 'method' => 'VIBRATION', 'inspected_on' => '2026-11-06', 'finding' => 'Vibration change observed; cause unconfirmed', 'recommendation' => 'Verify alignment at the next safe window', 'target_completion' => '2026-11-08', 'follow_up_status' => 'open'];
    }

    private function judgment(): array
    {
        return ['request_key' => (string) Str::uuid(), 'asset_ref' => self::ASSET, 'urgency' => 'planned', 'observed_condition' => 'Vibration change observed', 'impact' => 'Operational impact remains unknown', 'reasoning' => 'Confirm measurement before deciding maintenance', 'evidence_note' => 'Local inspection and manually observed disruption', 'owner' => 'QA mechanical team', 'due_on' => '2026-11-09', 'review_on' => '2026-11-08'];
    }

    public function test_inspection_and_disruption_flow_into_one_judgment_then_status_and_home_audit(): void
    {
        $inspectionInput = $this->recommendation();
        $this->post('/inspections', $inspectionInput)->assertSessionHasNoErrors()->assertRedirect();
        $inspection = InspectionDraft::firstOrFail();
        $this->post('/inspections', $inspectionInput)->assertRedirect(route('inspections.show', $inspection));
        $home = $this->get('/?scope=local')->assertOk();
        $this->assertSame([self::ASSET], $home->viewData('feed')['candidates']->pluck('asset_ref')->all());
        $this->assertSame([$inspection->id], $home->viewData('feed')['followUps']->pluck('id')->all());

        $disruptionInput = ['request_key' => (string) Str::uuid(), 'asset_ref' => self::ASSET, 'asset_role' => 'unknown', 'event_type' => 'trip', 'description' => 'Synthetic observed trip; cause unknown', 'impact' => 'unknown'];
        $this->post('/disruptions', $disruptionInput)->assertSessionHasNoErrors()->assertRedirect();
        $disruption = AssetDisruption::firstOrFail();
        $this->post('/disruptions', $disruptionInput)->assertRedirect(route('disruptions.show', $disruption));
        $board = $this->get('/action-board')->assertOk();
        $candidate = $board->viewData('candidates')->sole();
        $this->assertSame(self::ASSET, $candidate->asset_ref);
        $this->assertSame(1, (int) $candidate->pdm_count);
        $this->assertSame(1, (int) $candidate->disruption_count);

        $input = [...$this->judgment(), 'inspection_id' => $inspection->id, 'disruption_id' => $disruption->id];
        $this->post('/priorities', $input)->assertSessionHasNoErrors()->assertRedirect();
        $priority = AssetPriority::firstOrFail();
        $this->post('/priorities', $input)->assertRedirect(route('priorities.show', $priority));
        $this->get(route('priorities.show', $priority))->assertOk()->assertSee($inspection->reference())->assertSee($disruption->reference())->assertSee('QA mechanical team');
        $home = $this->get('/?scope=local')->assertOk()->assertSee('QA mechanical team')->assertSee('09 Nov 2026')->assertSee('08 Nov 2026');
        $this->assertCount(0, $home->viewData('feed')['candidates']);
        $this->assertSame([$priority->id], $home->viewData('feed')['priorities']->pluck('id')->all());

        $this->put(route('inspections.update', $inspection), [...$inspectionInput, 'version' => 1, 'follow_up_status' => 'in_progress'])->assertSessionHasNoErrors();
        $this->put(route('inspections.update', $inspection), [...$inspectionInput, 'version' => 2, 'follow_up_status' => 'completed'])->assertSessionHasNoErrors();
        $close = [...$input, 'version' => 1, 'status' => 'closed', 'change_reason' => 'Work reviewed and local follow-up finished'];
        $this->put(route('priorities.update', $priority), $close)->assertSessionHasNoErrors();
        $this->put(route('priorities.update', $priority), $close)->assertSessionHasErrors('version');
        $home = $this->get('/?scope=local')->assertOk()->assertSee('Status tindak lanjut: Sedang ditindaklanjuti → Selesai');
        $feed = $home->viewData('feed');
        $this->assertCount(0, $feed['priorities']);
        $this->assertCount(0, $feed['followUps']);
        $this->assertCount(0, $feed['candidates']);
        $this->assertCount(6, $feed['activities']);
        foreach ($feed['activities'] as $event) {
            $this->get($event['url'])->assertOk();
        }
        $this->get(route('priorities.create', ['asset_ref' => self::ASSET]))->assertRedirect(route('priorities.show', $priority));
        $this->put(route('priorities.update', $priority), [...$input, 'version' => 2, 'status' => 'active', 'change_reason' => 'Reopen for another verification'])->assertSessionHasNoErrors();
        $home = $this->get('/?scope=local')->assertOk();
        $this->assertSame([$priority->id], $home->viewData('feed')['priorities']->pluck('id')->all());
        $this->assertCount(0, $home->viewData('feed')['candidates']);
        $this->assertDatabaseCount('inspection_drafts', 1);
        $this->assertDatabaseCount('asset_disruptions', 1);
        $this->assertDatabaseCount('asset_priorities', 1);
        $this->assertDatabaseCount('asset_priority_revisions', 3);
        $this->assertDatabaseCount('asset_disruption_revisions', 1);
        $this->assertDatabaseCount('workspace_activities', 3);
        Http::assertNotSent(fn ($request) => $request->method() !== 'GET');
    }

    public function test_disruption_only_candidate_is_removed_when_voided_and_history_remains(): void
    {
        $input = ['request_key' => (string) Str::uuid(), 'asset_ref' => self::ASSET, 'asset_role' => 'unknown', 'event_type' => 'trip', 'description' => 'Synthetic observation', 'impact' => 'unknown'];
        $this->post('/disruptions', $input)->assertSessionHasNoErrors();
        $event = AssetDisruption::firstOrFail();
        $home = $this->get('/?scope=local')->assertOk();
        $this->assertSame([self::ASSET], $home->viewData('feed')['candidates']->pluck('asset_ref')->all());
        $this->put(route('disruptions.update', $event), [...$input, 'version' => 1, 'status' => 'voided', 'correction_reason' => 'Duplicate observation confirmed'])->assertSessionHasNoErrors();
        $home = $this->get('/?scope=local')->assertOk();
        $this->assertCount(0, $home->viewData('feed')['candidates']);
        $this->assertCount(2, $home->viewData('feed')['activities']);
        $this->assertDatabaseCount('asset_disruptions', 1);
        $this->assertDatabaseCount('asset_disruption_revisions', 2);
        Http::assertNotSent(fn ($request) => $request->method() !== 'GET');
    }
}
