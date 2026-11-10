<?php

namespace Tests\Feature;

use App\Models\AssetPriority;
use App\Models\InspectionDraft;
use App\Models\User;
use Carbon\CarbonImmutable;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Str;
use Tests\TestCase;

class ActionBoardFollowUpTest extends TestCase
{
    use RefreshDatabase;

    private User $owner;

    protected function setUp(): void
    {
        parent::setUp();
        $this->travelTo(CarbonImmutable::parse('2026-11-09 00:30:00', 'Asia/Jakarta'));
        config(['services.reliability_mart.url' => 'http://mart.test']);
        Http::preventStrayRequests();
        Http::fake(['mart.test/*' => fn () => Http::response([], 503)]);
        $this->owner = User::factory()->create(['roles' => ['ENGINEER'], 'active' => true])->refresh();
        $this->actingAs($this->owner)->withSession(['auth_version' => $this->owner->auth_version]);
    }

    private function draft(?string $date, string $status = 'open', array $changes = []): InspectionDraft
    {
        return InspectionDraft::create(['created_by' => $this->owner->id, 'request_reference' => 'QA-reference', 'request_summary' => 'QA request',
            'recommendation' => 'QA follow-up', 'target_completion' => $date, 'follow_up_status' => $status, ...$changes]);
    }

    private function xpath(string $html): \DOMXPath
    {
        $document = new \DOMDocument;
        @$document->loadHTML($html);

        return new \DOMXPath($document);
    }

    public function test_queue_counts_all_pending_rows_not_only_page_and_excludes_completed_or_missing_recommendations(): void
    {
        for ($i = 0; $i < 12; $i++) {
            $this->draft('2026-11-08', $i % 2 ? 'in_progress' : 'open');
        }
        $this->draft('2026-11-09');
        $this->draft('2026-11-10');
        $this->draft(null);
        $this->draft('2026-11-07', 'completed');
        $this->draft(null, 'completed');
        $this->draft('2026-11-08', 'open', ['recommendation' => null]);
        $response = $this->get('/action-board?follow_up_target=overdue')->assertOk()->assertSee('hari WIB 2026-11-09')
            ->assertSee('15 belum selesai')->assertSee('12 terlambat')->assertSee('Backlog belum terhubung');
        $this->assertSame(['pending' => 15, 'overdue' => 12, 'today' => 1, 'upcoming' => 1, 'undated' => 1], $response->viewData('followUpSummary'));
        $this->assertSame(12, $response->viewData('followUps')->total());
        $this->assertCount(10, $response->viewData('followUps'));
        foreach ($response->viewData('followUps') as $row) {
            $this->assertNotSame('completed', $row->follow_up_status);
        }
        $next = $this->get('/action-board?follow_up_target=overdue&follow_up_page=2')->assertOk();
        $this->assertCount(2, $next->viewData('followUps'));
        $this->assertSame($response->viewData('followUpSummary'), $next->viewData('followUpSummary'));
    }

    public function test_target_filters_and_status_intersection_are_exact_without_status_mutation(): void
    {
        $overdue = $this->draft('2026-11-08');
        $today = $this->draft('2026-11-09', 'in_progress');
        $upcoming = $this->draft('2026-11-10');
        $undated = $this->draft(null);
        $completed = $this->draft('2026-11-08', 'completed');
        foreach (['overdue' => $overdue, 'today' => $today, 'upcoming' => $upcoming, 'undated' => $undated] as $filter => $expected) {
            $response = $this->get('/action-board?follow_up_target='.$filter)->assertOk();
            $this->assertSame([$expected->id], $response->viewData('followUps')->pluck('id')->all());
        }
        $response = $this->get('/action-board?follow_up_target=overdue&follow_up_status=completed')->assertOk();
        $this->assertCount(0, $response->viewData('followUps'));
        $all = $this->get('/action-board?follow_up_status=completed')->assertOk();
        $this->assertSame([$completed->id], $all->viewData('followUps')->pluck('id')->all());
        $this->assertSame('completed', $completed->fresh()->follow_up_status);
        $this->assertDatabaseCount('inspection_drafts', 5);
        $this->assertDatabaseCount('workspace_activities', 0);
    }

    public function test_filtered_and_paginated_panels_stay_open_and_forms_preserve_other_filters(): void
    {
        foreach (['follow_up_status=', 'follow_up_target=today', 'follow_up_page=2', 'backlog_offset=0'] as $query) {
            $response = $this->get('/action-board?'.$query.'&priority_status=closed&window_days=30')->assertOk();
            $xpath = $this->xpath($response->getContent());
            $this->assertCount(1, $xpath->query('//details[contains(@class,"attention-secondary") and @open]'));
            $this->assertCount(1, $xpath->query('//input[@type="hidden" and @name="priority_status" and @value="closed"]'));
            $this->assertCount(1, $xpath->query('//input[@type="hidden" and @name="window_days" and @value="30"]'));
            $this->assertCount(4, $xpath->query('//nav[@aria-label="Target rekomendasi belum selesai"]//a'));
            foreach ($xpath->query('//nav[@aria-label="Target rekomendasi belum selesai"]//a') as $link) {
                $this->assertStringContainsString('priority_status=closed', $link->getAttribute('href'));
                $this->assertStringNotContainsString('follow_up_page=', $link->getAttribute('href'));
            }
        }
    }

    public function test_invalid_filters_fail_before_source_reads_and_all_read_roles_can_use_queue(): void
    {
        $this->get('/action-board?follow_up_target=unsafe')->assertSessionHasErrors('follow_up_target');
        $this->get('/action-board?follow_up_page=-1')->assertSessionHasErrors('follow_up_page');
        $this->get('/action-board?priority_page=100001')->assertSessionHasErrors('priority_page');
        Http::assertNothingSent();
        foreach (['ADMIN', 'SUPERVISOR', 'MANAGER', 'ENGINEER'] as $role) {
            $user = User::factory()->create(['roles' => [$role], 'active' => true])->refresh();
            $this->actingAs($user)->withSession(['auth_version' => $user->auth_version]);
            $this->get('/action-board?follow_up_target=overdue')->assertOk()->assertSee('0 belum selesai')->assertSee('0 terlambat');
        }
        Http::assertNotSent(fn ($request) => $request->method() !== 'GET');
        auth()->logout();
        $this->get('/action-board?follow_up_target=overdue')->assertRedirect(route('login'));
    }

    public function test_home_and_priority_deadlines_share_wib_calendar_at_midnight_boundary(): void
    {
        $late = $this->draft('2026-11-08');
        $edge = $this->draft('2026-11-16');
        $outside = $this->draft('2026-11-17');
        AssetPriority::create(['asset_ref' => 'asset:QA:DATE', 'created_by' => $this->owner->id, 'request_key' => (string) Str::uuid(),
            'urgency' => 'planned', 'status' => 'active', 'observed_condition' => 'QA observation', 'impact' => 'QA only',
            'reasoning' => 'QA date boundary', 'evidence_note' => 'Synthetic fixture', 'owner' => 'QA owner', 'due_on' => '2026-11-08']);
        $home = $this->get('/?scope=local')->assertOk();
        $this->assertSame([$late->id, $edge->id], $home->viewData('feed')['followUps']->pluck('id')->all());
        $this->assertNotContains($outside->id, $home->viewData('feed')['followUps']->pluck('id'));
        $xpath = $this->xpath($home->getContent());
        $this->assertCount(2, $xpath->query('//*[contains(@class,"attention-overdue")]'));
        $board = $this->get('/action-board')->assertOk()->assertSee('Tanggal review / target telah lewat');
        $this->assertSame(1, $board->viewData('followUpSummary')['overdue']);
    }
}
