<?php

namespace Tests\Feature;

use App\Models\AssetDisruption;
use App\Models\ReliabilityReview;
use App\Models\User;
use App\Services\ReliabilityIntake;
use Carbon\CarbonImmutable;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Str;
use PHPUnit\Framework\Attributes\DataProvider;
use Tests\TestCase;

class ReliabilityIntakeTest extends TestCase
{
    use RefreshDatabase;

    private const ASSET = 'asset:MAXIMO:MXASSET:BSR:IP:INTAKE-FIXTURE';

    private User $owner;

    protected function setUp(): void
    {
        parent::setUp();
        $this->travelTo(CarbonImmutable::parse('2026-11-10T12:00:00+07:00'));
        config(['services.reliability_mart.url' => 'http://mart.test']);
        Http::preventStrayRequests();
        Http::fake(['*' => Http::response([], 503)]);
        $this->owner = User::factory()->create(['roles' => ['ENGINEER'], 'active' => true])->refresh();
        $this->login($this->owner);
    }

    private function login(User $user): void
    {
        $this->actingAs($user)->withSession(['auth_version' => $user->auth_version]);
    }

    private function scope(): array
    {
        return ['asset_ref' => self::ASSET, 'period' => 'custom', 'start_date' => '2026-01-01', 'end_date' => '2026-10-31'];
    }

    private function event(?string $date = '2026-01-15'): AssetDisruption
    {
        $event = AssetDisruption::create(['asset_ref' => self::ASSET, 'created_by' => $this->owner->id, 'request_key' => (string) Str::uuid(), 'event_type' => 'trip', 'description' => 'Isolated synthetic intake test', 'impact' => 'unknown', 'occurred_on' => $date]);
        $event->members()->create(['asset_ref' => self::ASSET, 'role' => 'affected']);

        return $event->refresh();
    }

    private function row(AssetDisruption $event, array $changes = []): array
    {
        return array_replace(['event_id' => (string) $event->id, 'event_version' => (string) $event->version, 'review_revision' => '0', 'asset_ref' => self::ASSET,
            'required_function' => 'Synthetic process function', 'evidence' => 'Synthetic log page 3', 'failure_at' => '2026-01-15T08:00:00+07:00', 'restored_at' => '2026-01-15T12:00:00+07:00',
            'repair_state' => 'completed', 'active_intervals_text' => "2026-01-15T09:00:00+07:00 | 2026-01-15T10:00:00+07:00\n2026-01-15T11:00:00+07:00 | 2026-01-15T12:00:00+07:00", 'timing_evidence' => 'Synthetic log pages 3 and 4, waiting excluded', 'reason' => 'Synthetic route test only'], $changes);
    }

    private function csv(array $rows): string
    {
        $stream = fopen('php://temp', 'r+');
        fputcsv($stream, ReliabilityIntake::COLUMNS, ',', '"', '');
        foreach ($rows as $row) {
            fputcsv($stream, array_values($row), ',', '"', '');
        }
        rewind($stream);
        $csv = stream_get_contents($stream);
        fclose($stream);

        return $csv;
    }

    private function preview(array $rows)
    {
        return $this->post(route('reliability.intake.preview'), [...$this->scope(), 'csv_text' => $this->csv($rows)]);
    }

    private function assertNoEvidenceWritten(int $events = 1): void
    {
        $this->assertDatabaseCount('asset_disruptions', $events);
        foreach (['reliability_reviews', 'reliability_snapshots', 'reliability_approvals', 'reliability_policies', 'operating_logs'] as $table) {
            $this->assertDatabaseCount($table, 0);
        }
    }

    public function test_guide_is_scoped_and_preserves_unknown_dates_during_source_outage(): void
    {
        $unknown = $this->event(null);
        $outside = $this->event('2025-12-01');
        $response = $this->get(route('reliability.intake', $this->scope()));
        $response->assertOk()->assertSee('Identitas sumber belum tersedia')->assertSee('Tanggal belum diketahui')->assertSee('Di luar periode pilihan');
        $response->assertSee('start_date=2026-01-01', false)->assertSee('end_date=2026-10-31', false);
        $response->assertViewHas('events', fn ($rows) => $rows->total() === 2 && $rows[0]['event_id'] === $unknown->id && $rows[1]['event_id'] === $outside->id);
        $this->assertNoEvidenceWritten(2);
    }

    public function test_header_template_contains_no_synthetic_operational_data(): void
    {
        $this->get(route('reliability.intake.template'))->assertOk()->assertContent(implode(',', ReliabilityIntake::COLUMNS)."\n");
        $this->assertNoEvidenceWritten(0);
    }

    public function test_valid_multiline_csv_preview_and_repeat_have_no_business_writes(): void
    {
        $row = $this->row($this->event(), ['evidence' => 'Synthetic "quoted" reference, page 5']);
        for ($i = 0; $i < 2; $i++) {
            $this->preview([$row])->assertOk()->assertViewHas('preview', fn ($rows) => count($rows) === 1 && $rows[0]['errors'] === [] && $rows[0]['warnings'] === [])->assertSee('Buka draft untuk diperiksa');
        }
        $this->assertNoEvidenceWritten();
    }

    public function test_draft_prefills_review_but_does_not_classify_attest_or_save(): void
    {
        $row = $this->row($this->event());
        $response = $this->followingRedirects()->post(route('reliability.intake.draft'), [...$this->scope(), 'draft' => $row]);
        $response->assertOk()->assertSee('Draft dari pratinjau')->assertSee('Synthetic process function');
        $response->assertViewHas('intakeDraft', fn ($draft) => $draft['classification'] === 'uncertain' && $draft['duplicate_of'] === null);
        $this->assertDoesNotMatchRegularExpression('/name="attestation"[^>]*checked/', $response->getContent());
        $this->assertNoEvidenceWritten();
    }

    public function test_draft_blank_fields_do_not_inherit_previous_failure_or_timing(): void
    {
        $event = $this->event();
        ReliabilityReview::create(['asset_disruption_id' => $event->id, 'asset_ref' => self::ASSET, 'revision' => 1, 'event_version' => $event->version, 'created_by' => $this->owner->id, 'request_key' => (string) Str::uuid(), 'classification' => 'failure', 'required_function' => 'Previous function', 'evidence' => 'Previous evidence', 'reason' => 'Isolated fixture', 'failure_at' => CarbonImmutable::parse('2026-01-15T08:00:00+07:00'), 'repair_state' => 'unknown', 'active_intervals' => [], 'rule_version' => ReliabilityReview::RULE, 'event_snapshot' => $event->snapshot(), 'created_at' => now()]);
        $row = $this->row($event, ['review_revision' => '1', 'required_function' => '', 'failure_at' => '', 'restored_at' => '', 'repair_state' => 'unknown', 'active_intervals_text' => '', 'timing_evidence' => '']);
        $response = $this->followingRedirects()->post(route('reliability.intake.draft'), [...$this->scope(), 'draft' => $row]);
        $response->assertOk();
        $this->assertMatchesRegularExpression('/id="failure_at"[^>]*value=""/', $response->getContent());
        $this->assertMatchesRegularExpression('/id="required_function"[^>]*>\s*<\/textarea>/', $response->getContent());
        $this->assertDatabaseCount('reliability_reviews', 1);
    }

    public function test_existing_save_requires_manual_classification_and_attestation_after_draft(): void
    {
        $event = $this->event();
        $row = $this->row($event);
        $this->post(route('reliability.intake.draft'), [...$this->scope(), 'draft' => $row])->assertRedirect(route('reliability.reviews', [$event, ...$this->scope()]));
        $payload = [...$row, 'request_key' => (string) Str::uuid(), 'previous_revision' => 0, 'classification' => 'uncertain'];
        $this->post(route('reliability.reviews.store', $event), $payload)->assertSessionHasErrors('attestation');
        $payload['attestation'] = '1';
        $this->post(route('reliability.reviews.store', $event), $payload)->assertSessionHasErrors('classification');
        $this->assertNoEvidenceWritten();
        $payload['classification'] = 'failure';
        $this->post(route('reliability.reviews.store', $event), $payload)->assertRedirect();
        $this->post(route('reliability.reviews.store', $event), $payload)->assertRedirect();
        $this->assertDatabaseCount('reliability_reviews', 1);
        $this->assertDatabaseCount('reliability_snapshots', 0);
        $this->assertDatabaseCount('reliability_approvals', 0);
    }

    public function test_draft_validation_returns_to_get_review_and_keeps_exact_period_and_input(): void
    {
        $event = $this->event();
        $row = $this->row($event);
        $url = route('reliability.reviews', [$event, ...$this->scope()]);
        $this->post(route('reliability.intake.draft'), [...$this->scope(), 'draft' => $row])->assertRedirect($url);
        $this->get($url)->assertOk()->assertSee('name="start_date" value="2026-01-01"', false);
        $payload = [...$this->scope(), ...$row, 'request_key' => (string) Str::uuid(), 'previous_revision' => 0, 'classification' => 'failure'];
        $this->from($url)->post(route('reliability.reviews.store', $event), $payload)->assertRedirect($url)->assertSessionHasErrors('attestation');
        $this->get($url)->assertOk()->assertSee('Synthetic process function')->assertSee('2026-01-15T08:00:00+07:00', false)->assertDontSee('Draft dari pratinjau');
        $this->assertNoEvidenceWritten();
        $this->post(route('reliability.reviews.store', $event), [...$payload, 'attestation' => '1'])->assertRedirect($url);
        $this->assertDatabaseCount('reliability_reviews', 1);
    }

    public function test_temporary_draft_cannot_prefill_another_asset_or_event(): void
    {
        $first = $this->event();
        $second = $this->event();
        $this->post(route('reliability.intake.draft'), [...$this->scope(), 'draft' => $this->row($first)])->assertRedirect();
        $this->get(route('reliability.reviews', [$second, ...$this->scope()]))->assertOk()->assertDontSee('Draft dari pratinjau')->assertDontSee('Synthetic process function');
        $this->assertNoEvidenceWritten(2);
    }

    public function test_duplicate_event_rows_block_all_occurrences_without_merging(): void
    {
        $row = $this->row($this->event());
        $this->preview([$row, $row])->assertOk()->assertViewHas('preview', fn ($rows) => count($rows[0]['errors']) === 1 && count($rows[1]['errors']) === 1)->assertDontSee('Buka draft untuk diperiksa');
        $this->assertNoEvidenceWritten();
    }

    #[DataProvider('invalidTimes')]
    public function test_invalid_time_data_blocks_preview(string $field, string $value): void
    {
        $row = $this->row($this->event(), [$field => $value]);
        $this->preview([$row])->assertOk()->assertViewHas('preview', fn ($rows) => count($rows[0]['errors']) > 0)->assertDontSee('Buka draft untuk diperiksa');
        $this->assertNoEvidenceWritten();
    }

    public static function invalidTimes(): array
    {
        return [['failure_at', '2026-01-15'], ['failure_at', '2026-01-15T08:00:00'], ['failure_at', '2026-01-15T08:00:00-00:00'], ['failure_at', '2026-02-30T08:00:00+07:00'], ['failure_at', '2099-01-15T08:00:00+07:00'], ['restored_at', '2026-01-15T07:00:00+07:00'], ['active_intervals_text', '2026-01-15T07:00:00+07:00 | 2026-01-15T10:00:00+07:00'], ['active_intervals_text', "2026-01-15T09:00:00+07:00 | 2026-01-15T11:00:00+07:00\n2026-01-15T10:00:00+07:00 | 2026-01-15T12:00:00+07:00"]];
    }

    public function test_unknown_and_outside_period_times_are_not_invented_or_silently_dropped(): void
    {
        $row = $this->row($this->event(), ['failure_at' => '', 'restored_at' => '', 'active_intervals_text' => '', 'repair_state' => 'unknown']);
        $this->preview([$row])->assertOk()->assertViewHas('preview', fn ($rows) => $rows[0]['errors'] === [] && count($rows[0]['warnings']) === 2);
        $row = $this->row(AssetDisruption::first(), ['failure_at' => '2025-12-31T08:00:00+07:00']);
        $this->preview([$row])->assertOk()->assertSee('Onset di luar periode dipilih');
        $this->assertNoEvidenceWritten();
    }

    public function test_wrong_asset_foreign_owner_and_voided_event_cannot_open_draft(): void
    {
        $event = $this->event();
        $row = $this->row($event, ['asset_ref' => 'asset:MAXIMO:MXASSET:BSR:IP:OTHER']);
        $this->post(route('reliability.intake.draft'), [...$this->scope(), 'draft' => $row])->assertSessionHasErrors('draft');
        $other = User::factory()->create(['roles' => ['ENGINEER'], 'active' => true])->refresh();
        $this->login($other);
        $this->post(route('reliability.intake.draft'), [...$this->scope(), 'draft' => $this->row($event)])->assertSessionHasErrors('draft');
        $this->login($this->owner);
        $event->update(['status' => 'voided']);
        $this->post(route('reliability.intake.draft'), [...$this->scope(), 'draft' => $this->row($event)])->assertSessionHasErrors('draft');
        $this->assertNoEvidenceWritten();
    }

    public function test_version_rechecked_when_opening_draft_after_preview(): void
    {
        $event = $this->event();
        $row = $this->row($event);
        $this->preview([$row])->assertOk();
        $event->increment('version');
        $this->post(route('reliability.intake.draft'), [...$this->scope(), 'draft' => $row])->assertSessionHasErrors('draft');
        $this->assertNoEvidenceWritten();
    }

    public function test_wrong_review_revision_unknown_columns_and_non_string_fields_rejected(): void
    {
        $row = $this->row($this->event(), ['review_revision' => '1']);
        $this->post(route('reliability.intake.draft'), [...$this->scope(), 'draft' => $row])->assertSessionHasErrors('draft');
        $row['classification'] = 'failure';
        $this->post(route('reliability.intake.draft'), [...$this->scope(), 'draft' => $row])->assertSessionHasErrors('draft');
        unset($row['classification']);
        $row['failure_at'] = ['unexpected'];
        $this->post(route('reliability.intake.draft'), [...$this->scope(), 'draft' => $row])->assertSessionHasErrors('draft');
        $this->assertNoEvidenceWritten();
    }

    public function test_limits_bad_header_and_escaped_html(): void
    {
        $row = $this->row($this->event(), ['evidence' => '<script>alert("test")</script>']);
        $this->preview([$row])->assertOk()->assertSee('&lt;script&gt;', false)->assertDontSee('<script>alert', false);
        $this->preview(array_fill(0, 51, $row))->assertSessionHasErrors('csv_text');
        $this->post(route('reliability.intake.preview'), [...$this->scope(), 'csv_text' => 'not,a,header'])->assertSessionHasErrors('csv_text');
        $this->post(route('reliability.intake.preview'), [...$this->scope(), 'csv_text' => str_repeat('x', 65537)])->assertSessionHasErrors('csv_text');
        $this->post(route('reliability.intake.preview'), [...$this->scope(), 'csv_text' => implode(',', ReliabilityIntake::COLUMNS)."\n"])->assertSessionHasErrors('csv_text');
        $this->assertNoEvidenceWritten();
    }

    public function test_read_only_roles_can_read_guide_but_not_stage_csv_or_drafts(): void
    {
        $row = $this->row($this->event());
        foreach (['ADMIN', 'SUPERVISOR', 'MANAGER'] as $role) {
            $user = User::factory()->create(['roles' => [$role], 'active' => true])->refresh();
            $this->login($user);
            $this->get(route('reliability.intake', $this->scope()))->assertOk()->assertDontSee('Tempel CSV')->assertDontSee('Catat observasi asli');
            $this->preview([$row])->assertForbidden();
            $this->get(route('reliability.intake.template'))->assertForbidden();
            $this->post(route('reliability.intake.draft'), [...$this->scope(), 'draft' => $row])->assertForbidden();
        }
        $this->assertNoEvidenceWritten();
    }
}
