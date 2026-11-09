<?php

namespace Tests\Feature;

use App\Models\AssetDisruption;
use App\Models\User;
use App\Services\DisruptionLogbook;
use App\Services\ReliabilityMart;
use Carbon\CarbonImmutable;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Str;
use Tests\TestCase;

class AssetDisruptionTest extends TestCase
{
    use RefreshDatabase;

    private const ASSET = 'asset:MAXIMO:MXASSET:BSR:IP:SYNTHETIC-MOTOR';

    private const OTHER = 'asset:MAXIMO:MXASSET:BSR:IP:SYNTHETIC-FAN';

    private User $owner;

    protected function setUp(): void
    {
        parent::setUp();
        $this->travelTo(CarbonImmutable::parse('2026-11-07T12:00:00Z'));
        config(['services.reliability_mart.url' => 'http://mart.test', 'services.asset_mapping.file' => null]);
        Http::preventStrayRequests();
        Http::fake(['mart.test/v1/reliability/assets/inventory/*' => fn ($request) => Http::response($this->asset(rawurldecode(basename(parse_url($request->url(), PHP_URL_PATH))))),
            'mart.test/v1/reliability/assets/inventory?*' => fn () => Http::response(['items' => [$this->asset(self::ASSET)], 'meta' => ['total' => 1, 'offset' => 0, 'limit' => 25, 'has_more' => false]])]);
        $this->owner = $this->signIn('ENGINEER');
    }

    private function asset(string $ref): array
    {
        return ['canonical_id' => $ref, 'site_code' => 'BSR', 'organization_code' => 'IP', 'source_asset_number' => 'SYNTHETIC-MOTOR', 'description' => 'Synthetic asset only', 'hierarchy_category' => 'component', 'scope_basis' => 'DIRECT_SOURCE_UNIT', 'registered' => false];
    }

    private function signIn(string $role): User
    {
        $user = User::factory()->create(['roles' => [$role], 'active' => true])->refresh();
        $this->actingAs($user)->withSession(['auth_version' => $user->auth_version]);

        return $user;
    }

    private function input(array $changes = []): array
    {
        return array_replace(['request_key' => (string) Str::uuid(), 'asset_ref' => self::ASSET, 'asset_role' => 'unknown', 'event_type' => 'trip', 'description' => 'Synthetic motor tripped, cause not established.', 'impact' => 'unknown'], $changes);
    }

    private function save(array $changes = []): AssetDisruption
    {
        $this->post('/disruptions', $this->input($changes))->assertSessionHasNoErrors()->assertRedirect();

        return AssetDisruption::latest('id')->firstOrFail();
    }

    public function test_manual_log_needs_no_wo_dcs_date_cause_or_recovery_and_preserves_unknowns(): void
    {
        $event = $this->save();
        $this->assertNull($event->occurred_on);
        $this->assertNull($event->occurred_at);
        $this->assertNull($event->restored_at);
        $this->assertNull($event->timezone);
        $this->assertNull($event->durationSeconds());
        $this->assertNull($event->work_order_ref);
        $this->assertSame(1, $event->version);
        $this->assertDatabaseCount('asset_disruption_revisions', 1);
        $summary = app(DisruptionLogbook::class)->summary(self::ASSET);
        $this->assertSame(1, $summary['unknown_date']);
        $this->assertSame([], $summary['annual']);
        foreach (['/disruptions', route('disruptions.show', $event), route('disruptions.edit', $event), route('assets.show', self::ASSET)] as $url) {
            $this->get($url)->assertOk();
        }
        $this->get(route('disruptions.show', $event))->assertSee('Belum cukup waktu')->assertSee('bukan otomatis masih trip');
        $this->get('/disruptions')->assertSee('1 kejadian tercatat')->assertSee('1 catatan tanpa tanggal');
        Http::assertNotSent(fn ($request) => $request->method() !== 'GET' || ! str_contains($request->url(), '/assets/inventory/'));
    }

    public function test_engineer_can_record_trip_when_symptoms_are_not_yet_known(): void
    {
        $input = $this->input();
        unset($input['description']);
        $this->post('/disruptions', $input)->assertSessionHasNoErrors();
        $this->assertSame('', AssetDisruption::firstOrFail()->description);
        $this->get('/disruptions')->assertSee('Gejala belum dicatat');
    }

    public function test_date_only_never_gets_midnight_or_fabricated_duration_and_year_is_local_date(): void
    {
        $event = $this->save(['occurred_on' => '2025-12-31', 'restored_on' => '2026-01-01']);
        $this->assertSame('2025-12-31', $event->getRawOriginal('occurred_on'));
        $this->assertNull($event->occurred_at);
        $this->assertNull($event->durationSeconds());
        $this->get(route('disruptions.show', $event))->assertSee('31 Dec 2025 · tanggal saja')->assertDontSee('31 Dec 2025 00:00');
        $event = $this->save(['occurred_on' => '2026-01-01', 'occurred_time' => '00:10:30', 'restored_on' => '2026-01-01', 'restored_time' => '01:10:30', 'timezone' => 'Asia/Jakarta']);
        $this->assertSame('2025-12-31 17:10:30', $event->occurred_at->format('Y-m-d H:i:s'));
        $this->assertSame(3600, $event->durationSeconds());
        $summary = app(DisruptionLogbook::class)->summary(self::ASSET);
        $this->assertSame(1, $summary['annual'][2026]['total']);
        $this->assertSame(1, $summary['annual'][2025]['total']);
        $this->assertSame(3600, $summary['annual'][2026]['seconds']);
        $this->get(route('disruptions.edit', $event))->assertSee('value="00:10:30"', false)->assertSee('value="2026-01-01"', false);
    }

    public function test_linked_assets_share_one_event_without_counting_impacted_asset_as_cause(): void
    {
        $event = $this->save(['asset_role' => 'cause', 'affected_refs' => self::OTHER, 'occurred_on' => '2026-02-02']);
        $this->assertSame(2, $event->members()->count());
        $this->assertSame(1, app(DisruptionLogbook::class)->summary()['total']);
        $cause = app(DisruptionLogbook::class)->summary(self::ASSET);
        $affected = app(DisruptionLogbook::class)->summary(self::OTHER);
        $this->assertSame(1, $cause['annual'][2026]['cause']);
        $this->assertSame(0, $cause['annual'][2026]['affected']);
        $this->assertSame(1, $affected['annual'][2026]['affected']);
        $this->assertSame(0, $affected['annual'][2026]['cause']);
        $this->get(route('assets.show', self::OTHER))->assertOk()->assertSee($event->reference());
        $this->get(route('disruptions.index', ['asset_ref' => self::OTHER]))->assertViewHas('events', fn ($events) => $events->total() === 1);
    }

    public function test_repeated_submit_is_idempotent_and_other_user_cannot_reuse_key(): void
    {
        $input = $this->input();
        $this->post('/disruptions', $input)->assertSessionHasNoErrors();
        $this->post('/disruptions', $input)->assertSessionHasNoErrors();
        $this->assertDatabaseCount('asset_disruptions', 1);
        $this->assertDatabaseCount('asset_disruption_revisions', 1);
        $this->signIn('ENGINEER');
        $this->post('/disruptions', $input)->assertStatus(409);
    }

    public function test_only_engineer_can_create_and_only_owner_can_correct(): void
    {
        $event = $this->save();
        foreach (['ADMIN', 'SUPERVISOR', 'MANAGER'] as $role) {
            $this->signIn($role);
            $this->get('/disruptions')->assertOk()->assertDontSee('>Catat gangguan</a>', false);
            $this->get(route('disruptions.show', $event))->assertOk()->assertDontSee('Koreksi catatan');
            $this->get('/disruptions/create')->assertForbidden();
            $this->post('/disruptions', $this->input())->assertForbidden();
            $this->get(route('disruptions.edit', $event))->assertForbidden();
            $this->put(route('disruptions.update', $event), [])->assertForbidden();
        }
        $this->signIn('ENGINEER');
        $this->get(route('disruptions.edit', $event))->assertForbidden();
        $this->put(route('disruptions.update', $event), [])->assertForbidden();
        $this->delete(route('disruptions.show', $event))->assertStatus(405);
        $this->assertDatabaseCount('asset_disruption_revisions', 1);
    }

    public function test_correction_retains_old_snapshot_and_stale_update_cannot_overwrite(): void
    {
        $event = $this->save(['asset_role' => 'cause', 'affected_refs' => self::OTHER]);
        $input = $this->input(['version' => 1, 'description' => 'Corrected observation', 'status' => 'recorded', 'correction_reason' => 'Engineer corrected the observation.']);
        $this->put(route('disruptions.update', $event), $input)->assertSessionHasNoErrors();
        $event->refresh();
        $this->assertSame(2, $event->version);
        $this->assertSame(1, $event->members()->count());
        $original = $event->revisions()->where('version', 1)->firstOrFail();
        $this->assertSame('Synthetic motor tripped, cause not established.', $original->snapshot['description']);
        $this->assertCount(2, $original->snapshot['members']);
        $this->put(route('disruptions.update', $event), $input)->assertSessionHasErrors('version');
        $this->assertDatabaseCount('asset_disruption_revisions', 2);
        $this->put(route('disruptions.update', $event), array_replace($input, ['version' => 2, 'status' => 'voided']))->assertSessionHasNoErrors();
        $this->assertSame(0, app(DisruptionLogbook::class)->summary()['total']);
        $this->get('/disruptions?status=voided')->assertSee($event->reference());
        $this->get(route('disruptions.show', $event))->assertSee('Synthetic motor tripped, cause not established.')->assertSee('Corrected observation')->assertSee('Dibatalkan · tidak dihitung');
        $this->assertDatabaseCount('asset_disruptions', 1);
        $this->assertDatabaseCount('asset_disruption_revisions', 3);
    }

    public function test_validation_rejects_invalid_dates_roles_members_times_and_missing_edit_reason(): void
    {
        foreach ([['occurred_on' => '2026-02-30'], ['occurred_on' => '2099-01-01'], ['occurred_time' => '10:00'], ['occurred_on' => '2026-01-01', 'occurred_time' => '10:00'], ['occurred_on' => '2026-01-01', 'occurred_time' => '25:00', 'timezone' => 'UTC'], ['occurred_on' => '2026-01-02', 'restored_on' => '2026-01-01'], ['occurred_on' => '2026-01-01', 'occurred_time' => '10:00', 'restored_on' => '2026-01-01', 'restored_time' => '09:00', 'timezone' => 'UTC'], ['asset_role' => 'fake'], ['event_type' => 'fake'], ['impact' => 'fake'], ['affected_refs' => self::ASSET], ['affected_refs' => self::OTHER."\n".self::OTHER], ['asset_role' => 'cause', 'cause_ref' => self::OTHER], ['cause_ref' => self::ASSET], ['affected_refs' => 'bad/id']] as $changes) {
            $this->post('/disruptions', $this->input($changes))->assertSessionHasErrors();
        }
        $this->assertDatabaseCount('asset_disruptions', 0);
        $event = $this->save();
        $this->put(route('disruptions.update', $event), $this->input(['version' => 1, 'status' => 'recorded']))->assertSessionHasErrors('correction_reason');
        $this->put(route('disruptions.update', $event), $this->input(['version' => 1, 'status' => 'recorded', 'correction_reason' => 'Change identity', 'asset_ref' => self::OTHER]))->assertSessionHasErrors('asset_ref');
    }

    public function test_outage_preserves_failed_form_and_readable_local_history(): void
    {
        $event = $this->save();
        $this->mock(ReliabilityMart::class, function ($mock) {
            $mock->shouldReceive('historyAsset', 'inventoryDetail', 'inventory')->andThrow(new \RuntimeException('Unavailable'));
        });
        $input = $this->input(['description' => 'Keep this unsaved observation']);
        $url = route('disruptions.create', ['asset_ref' => self::ASSET]);
        $this->from($url)->post('/disruptions', $input)->assertRedirect($url)->assertSessionHasErrors('asset_ref');
        $this->get($url)->assertOk()->assertSee('Keep this unsaved observation')->assertSee('Isian tetap ada');
        $this->get(route('assets.show', self::ASSET))->assertOk()->assertSee('Belum terhubung')->assertSee($event->reference());
        $this->get(route('disruptions.show', $event))->assertOk();
        $this->assertDatabaseCount('asset_disruptions', 1);
    }

    public function test_summary_is_separate_from_pagination_filter_and_empty_never_means_healthy(): void
    {
        $this->get('/disruptions')->assertSee('Belum ada catatan bukan berarti aset sehat');
        $this->get('/disruptions/create')->assertOk()->assertSee('SYNTHETIC-MOTOR');
        $this->get(route('disruptions.create', ['asset_ref' => self::ASSET]))->assertOk()->assertSee('Simpan log gangguan');
        for ($i = 0; $i < 21; $i++) {
            $this->save(['occurred_on' => $i < 20 ? '2025-01-01' : '2026-01-01']);
        }
        $this->get('/disruptions')->assertViewHas('events', fn ($events) => $events->total() === 21 && $events->count() === 20)->assertSee('21 kejadian tercatat');
        $this->get('/disruptions?year=2026')->assertViewHas('events', fn ($events) => $events->total() === 1)->assertSee('21 kejadian tercatat');
        $this->get('/disruptions?page=2')->assertViewHas('events', fn ($events) => $events->count() === 1);
    }

    public function test_untrusted_notes_render_as_text_and_atomic_audit_failure_rolls_back(): void
    {
        $event = $this->save(['description' => '<script>alert(1)</script>', 'evidence_note' => 'javascript:alert(1)']);
        $this->get(route('disruptions.show', $event))->assertSee('&lt;script&gt;alert(1)&lt;/script&gt;', false)->assertDontSee('<script>alert(1)</script>', false)->assertDontSee('href="javascript:', false);
        DB::statement("CREATE TRIGGER fail_revision BEFORE INSERT ON asset_disruption_revisions BEGIN SELECT RAISE(ABORT, 'test rollback'); END");
        $this->put(route('disruptions.update', $event), $this->input(['version' => 1, 'status' => 'recorded', 'description' => 'Must roll back', 'correction_reason' => 'Synthetic rollback test']))->assertStatus(500);
        $this->assertSame(1, $event->fresh()->version);
        $this->assertSame('<script>alert(1)</script>', $event->fresh()->description);
        $this->assertDatabaseCount('asset_disruption_revisions', 1);
    }

    public function test_date_only_accepts_today_wib_without_fabricating_time_and_rejects_tomorrow(): void
    {
        $this->travelTo(CarbonImmutable::parse('2026-11-07T17:15:00Z'));
        $event = $this->save(['occurred_on' => '2026-11-08', 'restored_on' => '2026-11-08']);
        $this->assertSame('2026-11-08', $event->occurred_on);
        $this->assertNull($event->occurred_at);
        $this->assertNull($event->restored_at);
        $this->assertNull($event->timezone);
        foreach (['occurred_on', 'restored_on'] as $field) {
            $this->post('/disruptions', $this->input([$field => '2026-11-09']))->assertSessionHasErrors($field);
        }
        $this->assertDatabaseCount('asset_disruptions', 1);
    }

    public function test_zoned_disruption_uses_actual_instant_instead_of_the_utc_or_wib_date(): void
    {
        $this->travelTo(CarbonImmutable::parse('2026-11-07T16:15:00Z'));
        $event = $this->save(['occurred_on' => '2026-11-08', 'occurred_time' => '00:30:00', 'restored_on' => '2026-11-08', 'restored_time' => '01:00:00', 'timezone' => 'Asia/Jayapura']);
        $this->assertSame('2026-11-07 15:30:00', $event->occurred_at->format('Y-m-d H:i:s'));
        $this->assertSame('2026-11-08', $event->occurred_on);
        $this->post('/disruptions', $this->input(['occurred_on' => '2026-11-08', 'occurred_time' => '01:30:00', 'timezone' => 'Asia/Jayapura']))->assertSessionHasErrors('occurred_time');
        $this->post('/disruptions', $this->input(['restored_on' => '2026-11-08', 'restored_time' => '01:30:00', 'timezone' => 'Asia/Jayapura']))->assertSessionHasErrors('restored_time');
        $this->assertDatabaseCount('asset_disruptions', 1);
    }

    public function test_existing_disruption_members_can_be_corrected_and_cancelled_without_mart(): void
    {
        $event = $this->save(['affected_refs' => self::OTHER]);
        $this->mock(ReliabilityMart::class, function ($mock) {
            $mock->shouldNotReceive('historyAsset');
        });
        $input = $this->input(['version' => 1, 'status' => 'recorded', 'description' => 'Corrected offline observation', 'affected_refs' => self::OTHER, 'correction_reason' => 'Review retained local observation']);
        $this->get(route('disruptions.edit', $event))->assertOk();
        $this->put(route('disruptions.update', $event), $input)->assertSessionHasNoErrors();
        $this->assertSame('Corrected offline observation', $event->fresh()->description);
        $this->assertSame(2, $event->fresh()->version);
        $this->assertSame(2, $event->members()->count());
        $this->put(route('disruptions.update', $event), $input)->assertSessionHasErrors('version');
        $this->put(route('disruptions.update', $event), [...$input, 'version' => 2, 'status' => 'voided'])->assertSessionHasNoErrors();
        $this->assertSame('voided', $event->fresh()->status);
        $this->assertDatabaseCount('asset_disruption_revisions', 3);
        $this->assertSame('Synthetic motor tripped, cause not established.', $event->revisions()->where('version', 1)->firstOrFail()->snapshot['description']);
        $this->assertSame('Corrected offline observation', $event->revisions()->where('version', 3)->firstOrFail()->snapshot['description']);
    }

    public function test_new_or_readded_disruption_identity_requires_verification_during_outage(): void
    {
        $event = $this->save(['affected_refs' => self::OTHER]);
        $newAsset = 'asset:MAXIMO:MXASSET:BSR:IP:NEW-MEMBER';
        $this->mock(ReliabilityMart::class, function ($mock) use ($newAsset) {
            $mock->shouldReceive('historyAsset')->with(self::ASSET)->never();
            $mock->shouldReceive('historyAsset')->with($newAsset)->twice()->andThrow(new \RuntimeException('Unavailable'));
            $mock->shouldReceive('historyAsset')->with(self::OTHER)->once()->andThrow(new \RuntimeException('Unavailable'));
        });
        $input = $this->input(['version' => 1, 'status' => 'recorded', 'affected_refs' => self::OTHER, 'correction_reason' => 'Review local identities']);
        $url = route('disruptions.edit', $event);
        $this->from($url)->put(route('disruptions.update', $event), [...$input, 'affected_refs' => self::OTHER."\n".$newAsset])->assertSessionHasErrors('affected_refs')->assertSessionHasInput('affected_refs', self::OTHER."\n".$newAsset);
        $this->put(route('disruptions.update', $event), [...$input, 'cause_ref' => $newAsset])->assertSessionHasErrors('cause_ref');
        $this->assertSame(1, $event->fresh()->version);
        $this->assertSame(2, $event->members()->count());
        // Removing a member is local. Historical snapshots are not an identity cache for re-adding it.
        $this->put(route('disruptions.update', $event), [...$input, 'affected_refs' => null])->assertSessionHasNoErrors();
        $this->put(route('disruptions.update', $event), [...$input, 'version' => 2])->assertSessionHasErrors('affected_refs');
        $this->assertSame(2, $event->fresh()->version);
        $this->assertSame(1, $event->members()->count());
        $this->assertDatabaseCount('asset_disruption_revisions', 2);
    }
}
