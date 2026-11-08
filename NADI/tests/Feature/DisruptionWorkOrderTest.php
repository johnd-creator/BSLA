<?php

namespace Tests\Feature;

use App\Models\AssetDisruption;
use App\Models\AssetDisruptionWorkOrder;
use App\Models\User;
use App\Services\DisruptionLogbook;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Str;
use Tests\TestCase;

class DisruptionWorkOrderTest extends TestCase
{
    use RefreshDatabase;

    private const ASSET = 'asset:MAXIMO:MXASSET:BSR:IP:SYNTHETIC-MOTOR';

    private const WO = 'workorder:MAXIMO:MXWODETAIL:BSR:IP:';

    private AssetDisruption $event;

    private User $owner;

    private bool $registered = false;

    private bool $outage = false;

    private array $override = [];

    protected function setUp(): void
    {
        parent::setUp();
        config(['services.reliability_mart.url' => 'http://mart.test']);
        Http::preventStrayRequests();
        Http::fake(function ($request) {
            if ($this->outage) {
                return Http::response([], 503);
            }
            if (str_contains($request->url(), '/assets/')) {
                return Http::response(['canonical_id' => self::ASSET, 'site_code' => 'BSR', 'organization_code' => 'IP', 'registered' => $this->registered, 'hierarchy_category' => 'equipment', 'scope_basis' => 'DIRECT_SOURCE_UNIT']);
            }
            if (str_contains($request->url(), 'maintenance-events')) {
                $ref = $request['work_order_id'] ?? self::WO.'QA-1';
                $record = array_replace(['canonical_id' => 'maintenance_event:'.substr($ref, strlen('workorder:')), 'work_order_id' => $ref, 'equipment_id' => self::ASSET, 'site_code' => 'BSR', 'organization_code' => 'IP', 'status' => 'WAPPR', 'description' => 'Synthetic WO, not failure', 'source_detail' => ['work_order_number' => substr($ref, strlen(self::WO))], 'private_payload' => 'DO-NOT-COPY'], $this->override);

                return Http::response(['items' => [$record], 'meta' => ['total' => 1, 'offset' => (int) ($request['offset'] ?? 0), 'limit' => 25, 'has_more' => false], 'scope' => ['population' => 'COLLECTED_HIERARCHY', 'asset_ref' => self::ASSET, 'site_code' => 'BSR', 'organization_code' => 'IP', 'date_basis' => 'ACTUAL_START_OR_SOURCE_CHANGED']]);
            }

            return Http::response([], 503);
        });
        $this->owner = $this->signIn();
        $this->event = AssetDisruption::create(['created_by' => $this->owner->id, 'request_key' => (string) Str::uuid(), 'asset_ref' => self::ASSET, 'event_type' => 'disturbance', 'description' => 'Synthetic observation', 'impact' => 'unknown', 'work_order_ref' => 'old free text']);
        $this->event->members()->create(['asset_ref' => self::ASSET, 'role' => 'unknown']);
        $this->event->revisions()->create(['version' => 1, 'changed_by' => $this->owner->id, 'reason' => 'Original observation', 'snapshot' => $this->event->snapshot(), 'created_at' => now()]);
    }

    private function signIn(string $role = 'ENGINEER'): User
    {
        $user = User::factory()->create(['roles' => [$role], 'active' => true])->refresh();
        $this->actingAs($user)->withSession(['auth_version' => $user->auth_version]);

        return $user;
    }

    private function attach(string $number = 'QA-1', array $extra = [])
    {
        return $this->post(route('disruptions.work-orders.store', $this->event), array_replace(['version' => $this->event->fresh()->version, 'work_order_ref' => self::WO.$number, 'note' => 'Possible follow-up, not established'], $extra));
    }

    private function correct(AssetDisruptionWorkOrder $link, array $extra = [])
    {
        return $this->put(route('disruptions.work-orders.update', [$this->event, $link]), array_replace(['version' => $this->event->fresh()->version, 'link_id' => $link->id, 'relation_state' => 'related', 'note' => 'Engineer evidence reference', 'correction_reason' => 'Engineer checked the supporting report'], $extra));
    }

    public function test_multiple_exact_asset_links_start_uncertain_and_never_change_event_semantics(): void
    {
        $this->attach()->assertSessionHasNoErrors();
        $this->attach('QA-2', ['relation_state' => 'related'])->assertSessionHasNoErrors();
        $this->event->refresh();
        $this->assertSame(3, $this->event->version);
        $this->assertSame(['uncertain', 'uncertain'], $this->event->workOrders->pluck('relation_state')->all());
        $this->assertSame('old free text', $this->event->work_order_ref);
        $this->assertSame('disturbance', $this->event->event_type);
        $this->assertNull($this->event->durationSeconds());
        $this->assertNull($this->event->occurred_at);
        $this->assertSame(1, app(DisruptionLogbook::class)->summary()['total']);
        $snapshot = $this->event->revisions()->first()->snapshot;
        $this->assertCount(2, $snapshot['work_orders']);
        $this->assertStringNotContainsString('DO-NOT-COPY', json_encode($snapshot));
        $this->assertStringNotContainsString('Synthetic WO', json_encode($snapshot));
        $this->get(route('disruptions.show', $this->event))->assertOk()->assertSee('Belum dipastikan')->assertSee('Referensi WO manual (belum dicocokkan)')->assertSee('bukan validasi failure');
        Http::assertNotSent(fn ($r) => $r->method() !== 'GET');
    }

    public function test_duplicate_submission_keeps_one_link_and_one_new_revision(): void
    {
        $this->attach()->assertSessionHasNoErrors();
        $this->attach('QA-1', ['version' => 1])->assertSessionHasNoErrors()->assertSessionHas('status', fn ($message) => str_contains($message, 'sudah ditautkan'));
        $this->assertDatabaseCount('asset_disruption_work_orders', 1);
        $this->assertDatabaseCount('asset_disruption_revisions', 2);
        Http::assertSentCount(2);
    }

    public function test_mismatched_asset_scope_or_ambiguous_identity_cannot_be_linked(): void
    {
        foreach ([['equipment_id' => 'asset:MAXIMO:MXASSET:BSR:IP:OTHER'], ['work_order_id' => self::WO.'OTHER'], ['canonical_id' => 'forged-event'], ['site_code' => 'OTHER'], ['organization_code' => 'OTHER']] as $override) {
            $this->override = $override;
            $this->attach()->assertSessionHasErrors('work_order_ref');
        }
        $this->assertDatabaseCount('asset_disruption_work_orders', 0);
        $this->assertSame(1, $this->event->fresh()->version);
    }

    public function test_invalid_requests_are_rejected_before_any_source_read(): void
    {
        foreach (['workorder:OTHER:QA-1', self::WO.'bad/id', self::WO.'bad\\id', '', ['bad']] as $ref) {
            $this->attach('QA-1', ['work_order_ref' => $ref])->assertSessionHasErrors('work_order_ref');
        }
        $this->attach('QA-1', ['version' => 0])->assertSessionHasErrors('version');
        Http::assertNothingSent();
    }

    public function test_picker_is_scoped_paginated_and_exact_number_search_is_not_fuzzy(): void
    {
        $url = route('disruptions.work-orders', [$this->event, 'wo_number' => 'QA-9', 'offset' => 25]);
        $this->get($url)->assertOk()->assertSee('QA-9')->assertSee('Belum ada hubungan WO aktif')->assertSee('Cari nomor WO persis');
        Http::assertSent(fn ($r) => str_contains($r->url(), 'inventory-maintenance-events') && $r['asset_ref'] === self::ASSET && $r['work_order_id'] === self::WO.'QA-9' && $r['offset'] === 25 && $r['limit'] === 25);
        $this->getJson(route('disruptions.work-orders', [$this->event, 'wo_number' => ['bad']]))->assertUnprocessable();
        $this->override = ['equipment_id' => 'asset:OTHER'];
        $this->get(route('disruptions.work-orders', $this->event))->assertSee('Daftar WO belum dapat diverifikasi')->assertDontSee('Synthetic WO');
    }

    public function test_exact_source_number_with_slash_uses_encoded_identity_and_readable_label(): void
    {
        $this->get(route('disruptions.work-orders', [$this->event, 'wo_number' => 'QA26/123']))->assertOk();
        Http::assertSent(fn ($r) => str_contains($r->url(), 'maintenance-events') && $r['work_order_id'] === self::WO.'QA26%2F123');
        $this->attach('QA26%2F123')->assertSessionHasNoErrors();
        $this->assertSame('QA26/123', $this->event->workOrders()->first()->number());
        $this->get(route('disruptions.show', $this->event))->assertOk()->assertSee('WO QA26/123');
    }

    public function test_registry_asset_uses_registry_read_route(): void
    {
        $this->registered = true;
        $this->attach()->assertSessionHasNoErrors();
        Http::assertSent(fn ($r) => str_contains($r->url(), '/maintenance-events?') && $r['asset_ref'] === self::ASSET);
        Http::assertNotSent(fn ($r) => str_contains($r->url(), '/inventory-maintenance-events'));
    }

    public function test_outage_retains_input_and_existing_links_without_accepting_new_identity(): void
    {
        $this->attach()->assertSessionHasNoErrors();
        $this->outage = true;
        $url = route('disruptions.work-orders', $this->event);
        $this->from($url)->attach('QA-2', ['note' => 'Preserve this unsaved note'])->assertRedirect($url)->assertSessionHasErrors('work_order_ref');
        $this->get($url)->assertOk()->assertSee('Preserve this unsaved note')->assertSee('QA-2')->assertSee('QA-1')->assertSee('Daftar WO belum dapat diverifikasi');
        $this->get(route('disruptions.show', $this->event))->assertOk()->assertSee('QA-1');
        $this->assertDatabaseCount('asset_disruption_work_orders', 1);
    }

    public function test_owner_gate_applies_to_picker_and_both_writes_without_admin_bypass(): void
    {
        $this->attach()->assertSessionHasNoErrors();
        $link = $this->event->workOrders()->first();
        foreach (['ADMIN', 'SUPERVISOR', 'MANAGER', 'ENGINEER'] as $role) {
            $this->signIn($role);
            $this->get(route('disruptions.work-orders', $this->event))->assertForbidden();
            $this->attach('QA-2')->assertForbidden();
            $this->correct($link)->assertForbidden();
            $this->get(route('disruptions.show', $this->event))->assertOk()->assertSee('QA-1')->assertDontSee('Pilih / koreksi hubungan WO');
        }
        $this->assertDatabaseCount('asset_disruption_work_orders', 1);
    }

    public function test_stale_forms_cannot_overwrite_link_or_event_corrections(): void
    {
        $this->attach()->assertSessionHasNoErrors();
        $link = $this->event->workOrders()->first();
        $this->attach('QA-2', ['version' => 1])->assertSessionHasErrors('version');
        $this->correct($link, ['version' => 1])->assertSessionHasErrors('version');
        $this->put(route('disruptions.update', $this->event), ['version' => 1, 'asset_ref' => self::ASSET, 'asset_role' => 'unknown', 'event_type' => 'trip', 'impact' => 'unknown', 'status' => 'recorded', 'correction_reason' => 'Outdated observation form'])->assertSessionHasErrors('version');
        $this->assertSame('uncertain', $link->fresh()->relation_state);
        $this->assertSame('disturbance', $this->event->fresh()->event_type);
        $this->assertDatabaseCount('asset_disruption_revisions', 2);
    }

    public function test_correction_removal_and_relink_keep_every_prior_snapshot(): void
    {
        $this->attach()->assertSessionHasNoErrors();
        $link = $this->event->workOrders()->first();
        $this->correct($link)->assertSessionHasNoErrors();
        $this->correct($link, ['relation_state' => 'removed'])->assertSessionHasNoErrors();
        $this->assertSame('removed', $link->fresh()->relation_state);
        $this->correct($link)->assertStatus(409);
        $this->attach()->assertSessionHasNoErrors();
        $this->assertSame('uncertain', $link->fresh()->relation_state);
        $this->assertDatabaseCount('asset_disruption_work_orders', 1);
        $this->assertSame(['uncertain', 'removed', 'related', 'uncertain'], $this->event->revisions()->where('version', '>', 1)->get()->map(fn ($r) => $r->snapshot['work_orders'][0]['relation_state'])->all());
    }

    public function test_link_ownership_and_required_correction_reason_are_enforced(): void
    {
        $this->attach()->assertSessionHasNoErrors();
        $link = $this->event->workOrders()->first();
        $this->correct($link, ['correction_reason' => ''])->assertSessionHasErrors('correction_reason');
        $this->correct($link, ['relation_state' => 'failure'])->assertSessionHasErrors('relation_state');
        $other = $this->event->replicate();
        $other->request_key = (string) Str::uuid();
        $other->save();
        $this->put(route('disruptions.work-orders.update', [$other, $link]), [])->assertNotFound();
        $this->assertSame('uncertain', $link->fresh()->relation_state);
    }

    public function test_failed_audit_rolls_back_link_version_and_correction(): void
    {
        $this->attach()->assertSessionHasNoErrors();
        $link = $this->event->workOrders()->first();
        DB::statement("CREATE TRIGGER fail_wo_revision BEFORE INSERT ON asset_disruption_revisions BEGIN SELECT RAISE(ABORT, 'test rollback'); END");
        $this->attach('QA-2')->assertStatus(500);
        $this->correct($link)->assertStatus(500);
        $this->assertSame(2, $this->event->fresh()->version);
        $this->assertSame('uncertain', $link->fresh()->relation_state);
        $this->assertDatabaseCount('asset_disruption_work_orders', 1);
        $this->assertDatabaseCount('asset_disruption_revisions', 2);
    }

    public function test_bidirectional_links_include_cancelled_event_label_but_do_not_increase_counts(): void
    {
        $this->attach()->assertSessionHasNoErrors();
        $url = route('work-orders.show', ['ref' => self::WO.'QA-1', 'asset_ref' => self::ASSET]);
        $this->get($url)->assertOk()->assertSee($this->event->reference())->assertSee('WAPPR')->assertSee('bukan bukti beberapa failure');
        $this->event->update(['status' => 'voided']);
        $this->get($url)->assertOk()->assertSee('Catatan dibatalkan');
        $this->assertSame(0, app(DisruptionLogbook::class)->summary()['total']);
        $this->correct($this->event->workOrders()->first(), ['relation_state' => 'removed'])->assertSessionHasNoErrors();
        $this->get($url)->assertOk()->assertDontSee($this->event->reference());
    }

    public function test_notes_and_old_snapshots_render_safely_without_promoting_manual_reference(): void
    {
        $revision = $this->event->revisions()->first();
        $snapshot = $revision->snapshot;
        unset($snapshot['work_orders']);
        $revision->update(['snapshot' => $snapshot]);
        $this->get(route('disruptions.show', $this->event))->assertOk()->assertSee('Belum ada hubungan terstruktur pada versi ini.')->assertSee('old free text');
        $this->attach('QA-1', ['note' => '<script>bad()</script>'])->assertSessionHasNoErrors();
        $this->get(route('disruptions.show', $this->event))->assertSee('&lt;script&gt;bad()', false)->assertDontSee('<script>bad()', false);
    }

    public function test_twenty_link_limit_rolls_back_without_extra_revision(): void
    {
        for ($i = 1; $i <= 20; $i++) {
            $this->attach('QA-'.$i)->assertSessionHasNoErrors();
        }
        $this->attach('QA-21')->assertSessionHasErrors('work_order_ref');
        $this->assertDatabaseCount('asset_disruption_work_orders', 20);
        $this->assertDatabaseCount('asset_disruption_revisions', 21);
        $this->assertSame(21, $this->event->fresh()->version);
    }
}
