<?php

namespace Tests\Feature;

use App\Models\PdmActivity;
use App\Models\PdmInspectionPlan;
use App\Models\User;
use App\Services\PdmFormCatalog;
use App\Services\PdmSchedule;
use Carbon\CarbonImmutable;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Http\Client\Factory;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Str;
use Tests\TestCase;

class PdmPlanMeasurementTest extends TestCase
{
    use RefreshDatabase;

    private const ASSET = 'asset:MAXIMO:MXASSET:BSR:IP:SYNTHETIC-PUMP-001';

    private User $owner;

    private PdmInspectionPlan $plan;

    protected function setUp(): void
    {
        parent::setUp();
        $this->travelTo(CarbonImmutable::parse('2026-11-09 10:00:00', 'Asia/Jakarta'));
        $this->owner = $this->signIn();
        config(['services.reliability_mart.url' => 'http://mart.test']);
        $this->fakeSource();
        $catalog = app(PdmFormCatalog::class);
        $template = $catalog->find('SYNTHETIC_MOTOR');
        $this->plan = PdmInspectionPlan::create([
            'created_by' => $this->owner->id, 'request_key' => (string) Str::uuid(), 'identity_key' => hash('sha256', 'synthetic-plan'),
            'title' => 'Synthetic routine point', 'asset_ref' => self::ASSET, 'template_id' => $template['id'],
            'template_fingerprint' => $catalog->fingerprint($template), 'template_snapshot' => $catalog->snapshot($template),
            'method' => $template['method'], 'point_key' => 'field_c3', 'unit' => 'mm/s', 'instrument' => 'QA meter',
            'measurement_mode' => 'RMS', 'operating_condition' => 'QA operating context', 'asset_selection_note' => 'Exact QA sampling location',
            'frequency_value' => 7, 'frequency_unit' => 'days', 'first_due_on' => '2026-11-01', 'status' => 'active',
            'notes' => 'PLAN-NOTES-NOT-MEASUREMENT',
        ])->refresh();
    }

    private function signIn(string $role = 'ENGINEER'): User
    {
        $user = User::factory()->create(['roles' => [$role], 'active' => true])->refresh();
        $this->actingAs($user)->withSession(['auth_version' => $user->auth_version]);

        return $user;
    }

    private function fakeSource(bool $available = true): void
    {
        Http::swap(new Factory);
        Http::preventStrayRequests();
        Http::fake(['mart.test/*' => fn () => Http::response($available ? ['canonical_id' => self::ASSET, 'source_asset_number' => 'QA-ASSET',
            'site_code' => 'BSR', 'organization_code' => 'IP', 'registered' => false, 'hierarchy_category' => 'component', 'scope_basis' => 'DIRECT_SOURCE_UNIT'] : [], $available ? 200 : 503)]);
    }

    private function url(array $extra = []): string
    {
        return route('pdm.create', ['plan_id' => $this->plan->id, ...$extra]);
    }

    private function input(array $extra = []): array
    {
        return array_replace($this->plan->only(['title', 'asset_ref', 'template_id', 'template_fingerprint', 'instrument', 'measurement_mode', 'operating_condition', 'asset_selection_note']),
            ['request_key' => (string) Str::uuid(), 'time_precision' => 'date', 'measured_on' => '2026-11-09', 'inspection_type' => 'routine',
                'readings' => ['field_c3' => ['value' => '0', 'unit' => 'mm/s']], 'acknowledge_draft' => '1'], $extra);
    }

    private function document(string $html): \DOMXPath
    {
        $document = new \DOMDocument;
        @$document->loadHTML($html);

        return new \DOMXPath($document);
    }

    public function test_plan_launch_prefills_only_editable_context_and_never_measurement_evidence(): void
    {
        $this->get(route('pdm.plans.show', $this->plan))->assertOk()->assertSee($this->url(), false);
        $response = $this->get($this->url())->assertOk()->assertSee('Konteks awal dari rencana inspeksi')->assertSee('Titik rencana')
            ->assertDontSee('PLAN-NOTES-NOT-MEASUREMENT');
        $activity = $response->viewData('activity');
        foreach (['instrument', 'measurement_mode', 'operating_condition', 'asset_selection_note', 'asset_ref', 'title'] as $key) {
            $this->assertSame($this->plan->$key, $activity->$key);
        }
        $this->assertNull($activity->measured_on);
        $this->assertNull($activity->measured_at);
        $this->assertNull($activity->readings['field_c3']['value']);
        $this->assertSame('mm/s', $activity->readings['field_c3']['unit']);
        $xpath = $this->document($response->getContent());
        $this->assertCount(0, $xpath->query('//input[starts-with(@name,"readings[") and contains(@name,"[value]") and string-length(@value)>0]'));
        $this->assertCount(0, $xpath->query('//input[@name="measured_on" and string-length(@value)>0] | //input[@name="acknowledge_draft" and @checked]'));
        $this->assertCount(1, $xpath->query('//*[contains(@class,"pdm-planned-point")]'));
        $this->assertDatabaseCount('pdm_activities', 0);
        $this->assertSame(1, $this->plan->fresh()->version);
        Http::assertNotSent(fn ($request) => $request->method() !== 'GET');
    }

    public function test_a_real_zero_measurement_counts_only_after_explicit_save_and_replay_is_idempotent(): void
    {
        $this->assertFalse(app(PdmSchedule::class)->coverage($this->plan)['covered']);
        $data = $this->input();
        $this->from($this->url())->post(route('pdm.store'), $data)->assertSessionHasNoErrors()->assertRedirect();
        $this->post(route('pdm.store'), $data)->assertSessionHasNoErrors();
        $this->assertDatabaseCount('pdm_activities', 1);
        $this->assertTrue(app(PdmSchedule::class)->coverage($this->plan)['covered']);
        $activity = PdmActivity::firstOrFail();
        $this->assertSame('0', $activity->readings['field_c3']['value']);
        $this->assertNull($activity->measured_at);
        $this->assertNull($activity->notes);
        $this->assertSame('active', $this->plan->fresh()->status);
        $this->assertSame(1, $this->plan->fresh()->version);
    }

    public function test_changed_actual_context_can_be_saved_but_is_not_claimed_as_plan_coverage(): void
    {
        $this->post(route('pdm.store'), $this->input(['instrument' => 'Different real instrument']))->assertSessionHasNoErrors();
        $this->assertFalse(app(PdmSchedule::class)->coverage($this->plan)['covered']);
        $this->assertNull(app(PdmSchedule::class)->coverage($this->plan)['latest']);
    }

    public function test_known_plan_unit_prefills_a_source_point_whose_unit_is_not_yet_defined(): void
    {
        $catalog = app(PdmFormCatalog::class);
        $template = $catalog->find('SYNTHETIC_UNKNOWN_UNIT');
        $this->plan->update(['template_id' => $template['id'], 'template_snapshot' => $catalog->snapshot($template),
            'template_fingerprint' => $catalog->fingerprint($template), 'method' => $template['method'], 'point_key' => 'field_b2', 'unit' => 'QA-unit']);
        $response = $this->get($this->url())->assertOk();
        $xpath = $this->document($response->getContent());
        $this->assertCount(1, $xpath->query('//input[@id="unit-field_b2" and @value="QA-unit"]'));
        $this->assertCount(1, $xpath->query('//input[@id="reading-field_b2" and @value=""]'));
    }

    public function test_changed_missing_or_review_only_templates_fail_closed_before_source_reads(): void
    {
        $original = $this->plan->getAttributes();
        $changed = $this->plan->template_snapshot;
        $changed['fields'][0]['label'] = 'Different definition despite same fingerprint';
        foreach ([['template_snapshot' => $changed], ['template_fingerprint' => str_repeat('0', 64)], ['template_id' => 'no-longer-present'], ['method' => 'OTHER'], ['point_key' => 'missing-point']] as $change) {
            $this->plan->setRawAttributes($original);
            $this->plan->fill($change)->save();
            $this->get($this->url())->assertStatus(409)->assertSee('Template rencana tidak sama')->assertDontSee('Simpan draft lokal');
        }
        $catalog = app(PdmFormCatalog::class);
        $preview = $catalog->find('SYNTHETIC_REVIEW');
        $this->plan->update(['template_id' => $preview['id'], 'template_snapshot' => $catalog->snapshot($preview),
            'template_fingerprint' => $catalog->fingerprint($preview), 'method' => $preview['method']]);
        $this->get($this->url())->assertStatus(409)->assertDontSee('Simpan draft lokal');
        $this->assertDatabaseCount('pdm_activities', 0);
        Http::assertNothingSent();
    }

    public function test_plan_identity_cannot_be_overridden_in_the_url(): void
    {
        $this->get($this->url(['asset_ref' => 'asset:OTHER']))->assertSessionHasErrors('asset_ref');
        $this->get($this->url(['template_id' => 'SYNTHETIC_UNKNOWN_UNIT']))->assertSessionHasErrors('template_id');
        $this->get(route('pdm.create', ['plan_id' => 999999]))->assertNotFound();
        $this->get('/pdm/create?plan_id[]=1')->assertSessionHasErrors('plan_id');
        Http::assertNothingSent();
    }

    public function test_paused_plan_remains_paused_and_cannot_gain_active_coverage(): void
    {
        $this->plan->update(['status' => 'paused']);
        $this->get($this->url())->assertOk()->assertSee('Rencana dijeda.');
        $this->post(route('pdm.store'), $this->input())->assertSessionHasNoErrors();
        $this->assertSame('paused', $this->plan->fresh()->status);
        $this->assertFalse(app(PdmSchedule::class)->coverage($this->plan)['covered']);
    }

    public function test_source_outage_keeps_plan_context_and_failed_input_but_does_not_bypass_verification(): void
    {
        $this->fakeSource(false);
        $this->get($this->url())->assertOk()->assertSee('Mart tidak tersedia')->assertSee('Simpan draft lokal');
        $data = $this->input(['title' => 'Retained actual measurement', 'instrument' => 'Actual instrument revision']);
        $this->from($this->url())->post(route('pdm.store'), $data)->assertSessionHasErrors('asset_ref')->assertRedirect($this->url());
        $this->get($this->url())->assertOk()->assertSee($data['title'])->assertSee($data['instrument'])->assertSee($data['request_key']);
        $this->assertDatabaseCount('pdm_activities', 0);
        $this->fakeSource();
        $this->post(route('pdm.store'), $data)->assertSessionHasNoErrors();
        $this->assertDatabaseCount('pdm_activities', 1);
    }

    public function test_generic_create_stays_unprefilled_and_roles_keep_existing_boundaries(): void
    {
        $response = $this->get(route('pdm.create', ['asset_ref' => self::ASSET, 'template_id' => 'SYNTHETIC_MOTOR']))->assertOk()
            ->assertDontSee('Konteks awal dari rencana inspeksi');
        $this->assertNull($response->viewData('activity')->instrument);
        foreach (['ADMIN', 'MANAGER', 'SUPERVISOR'] as $role) {
            $this->signIn($role);
            $this->get($this->url())->assertForbidden();
            $this->post(route('pdm.store'), $this->input())->assertForbidden();
        }
        $this->signIn();
        $this->get($this->url())->assertOk();
        $this->assertSame($this->owner->id, $this->plan->fresh()->created_by);
        auth()->logout();
        $this->get($this->url())->assertRedirect(route('login'));
        $this->assertDatabaseCount('pdm_activities', 0);
    }
}
