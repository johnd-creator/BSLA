<?php

namespace Tests\Feature;

use App\Models\User;
use App\Services\BsrAssetMapping;
use App\Services\CollectorWorkOrderDescription;
use App\Services\WorkOrderTiming;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Http;
use Tests\TestCase;

class WorkOrderAndMappingTest extends TestCase
{
    use RefreshDatabase;

    private const REFERENCE = 'workorder:MAXIMO:MXWODETAIL:BSR:IP:BSR-TEST';

    private ?string $mappingFile = null;

    protected function setUp(): void
    {
        parent::setUp();
        Http::preventStrayRequests();
        config(['services.reliability_mart.url' => 'http://mart.test', 'services.maximo_collector.url' => 'http://127.0.0.1:8002', 'services.asset_mapping.file' => null]);
    }

    protected function tearDown(): void
    {
        if ($this->mappingFile && is_file($this->mappingFile)) {
            unlink($this->mappingFile);
        }
        parent::tearDown();
    }

    private function signIn(): void
    {
        $user = User::factory()->create(['roles' => ['ENGINEER'], 'active' => true])->refresh();
        $this->actingAs($user)->withSession(['auth_version' => $user->auth_version]);
    }

    private function record(array $changes = []): array
    {
        return array_replace(['canonical_id' => 'maintenance_event:MAXIMO:MXWODETAIL:BSR:IP:BSR-TEST', 'equipment_id' => 'asset:MAXIMO:MXASSET:BSR:IP:A1', 'work_order_id' => self::REFERENCE, 'status' => 'CLOSE', 'actual_start' => null, 'actual_finish' => null, 'duration_hours' => 999,
            'site_code' => 'BSR', 'organization_code' => 'IP', 'source_detail' => ['work_order_number' => 'BSR-TEST', 'asset_number' => 'A1']], $changes);
    }

    private function page(array $record): array
    {
        return ['items' => [$record], 'meta' => ['total' => 1, 'offset' => 0, 'limit' => 25, 'has_more' => false]];
    }

    public function test_new_data_views_require_authentication(): void
    {
        foreach (['/work-orders', '/work-orders/detail?ref='.urlencode(self::REFERENCE), '/assets/mapping'] as $path) {
            $this->get($path)->assertRedirect(route('login'));
        }
        Http::assertNothingSent();
    }

    public function test_actual_duration_requires_close_and_both_zoned_valid_timestamps(): void
    {
        $valid = $this->record(['actual_start' => '2026-01-01T10:00:00+07:00', 'actual_finish' => '2026-01-01T05:30:00Z']);
        $this->assertSame(2.5, WorkOrderTiming::fromRecord($valid)['duration_hours']);
        foreach ([$this->record(['source_changed_at' => '2026-01-01T00:00:00Z', 'scheduled_start' => '2026-01-01T00:00:00Z']), array_replace($valid, ['status' => 'WAPPR']), array_replace($valid, ['actual_start' => '2026-01-01T10:00:00']), array_replace($valid, ['actual_start' => '2026-02-31T00:00:00Z']), array_replace($valid, ['actual_start' => '2026-01-02T00:00:00Z'])] as $invalid) {
            $this->assertNull(WorkOrderTiming::fromRecord($invalid)['duration_hours']);
        }
        $this->assertSame('INVALID_ACTUAL_ORDER', WorkOrderTiming::fromRecord(array_replace($valid, ['actual_start' => '2026-01-02T00:00:00Z']))['state']);
        $this->assertSame(0.0, WorkOrderTiming::fromRecord($this->record(['actual_start' => '2026-01-01T00:00:00Z', 'actual_finish' => '2026-01-01T00:00:00Z']))['duration_hours']);
    }

    public function test_missing_clock_provenance_is_applied_only_to_the_selected_field(): void
    {
        $valid = '2026-01-01T00:00:00Z';
        foreach (['INVALID', 'NAIVE', 'UNAVAILABLE'] as $reason) {
            foreach (['START', 'FINISH'] as $field) {
                $matching = $reason.'_ACTUAL_'.$field;
                $record = $this->record(['actual_start' => $field === 'START' ? null : $valid, 'actual_timing_state' => $matching]);
                $timing = WorkOrderTiming::fromRecord($record);
                $this->assertSame($matching, $timing['state']);
                $this->assertSame($reason, $timing[strtolower($field).'_state']);
                $this->assertNull($timing['duration_hours']);
            }
            $this->assertSame('MISSING_ACTUAL_START', WorkOrderTiming::fromRecord($this->record(['actual_timing_state' => $reason.'_ACTUAL_FINISH']))['state']);
            $this->assertSame('MISSING_ACTUAL_FINISH', WorkOrderTiming::fromRecord($this->record(['actual_start' => $valid, 'actual_timing_state' => $reason.'_ACTUAL_START']))['state']);
        }
        $this->assertSame('INVALID_ACTUAL_START', WorkOrderTiming::fromRecord($this->record(['actual_start' => 'invalid', 'actual_timing_state' => 'UNAVAILABLE_ACTUAL_START']))['state']);
        $this->assertSame('NOT_CLOSED', WorkOrderTiming::fromRecord($this->record(['status' => 'WAPPR', 'actual_timing_state' => 'UNAVAILABLE_ACTUAL_START']))['state']);
    }

    public function test_wo_detail_labels_unavailable_clock_evidence(): void
    {
        Http::fake(['mart.test/*' => Http::response($this->page($this->record(['description' => 'Synthetic description', 'actual_timing_state' => 'UNAVAILABLE_ACTUAL_START'])))]);
        $this->signIn();
        $this->get(route('work-orders.show', ['ref' => self::REFERENCE]))->assertOk()->assertSee('Bukti timestamp belum tersedia')->assertSee('Bukti actual timestamp belum tersedia. Durasi tidak dihitung.')->assertSee('Belum dapat dihitung');
        Http::assertSentCount(1);
    }

    public function test_wo_detail_enriches_only_description_on_exact_collector_identity_match(): void
    {
        Http::fake(['mart.test/*' => Http::response($this->page($this->record())), '127.0.0.1:8002/*' => Http::response([['id' => 'BSR-TEST', 'equipment_id' => 'A1', 'description' => 'Verified synthetic description', 'reported_by' => 'PRIVATE-PERSON', 'sources' => ['raw' => 'PRIVATE-RAW']]])]);
        $this->signIn();
        $this->get(route('work-orders.show', ['ref' => self::REFERENCE]))->assertOk()->assertSee('Verified synthetic description')->assertSee('Belum dapat dihitung')->assertDontSee('999')->assertDontSee('PRIVATE-PERSON')->assertDontSee('PRIVATE-RAW');
        Http::assertSentCount(2);
        Http::assertSent(fn ($r) => $r->method() === 'GET' && str_contains($r->url(), '/work-orders') && $r['q'] === 'BSR-TEST' && $r['equipment_id'] === 'A1');
    }

    public function test_collector_description_rejects_fuzzy_and_cross_asset_matches(): void
    {
        Http::fake(['127.0.0.1:8002/*' => Http::response([['id' => 'BSR-TEST', 'equipment_id' => 'OTHER', 'description' => 'wrong asset'], ['id' => 'BSR-TEST-X', 'equipment_id' => 'A1', 'description' => 'fuzzy wrong WO']])]);
        $record = ['work_order_number' => 'BSR-TEST', 'asset_number' => 'A1'];
        $this->assertNull(app(CollectorWorkOrderDescription::class)->forRecord($record));
        config(['services.maximo_collector.url' => 'http://production.invalid']);
        $this->assertNull(app(CollectorWorkOrderDescription::class)->forRecord($record));
        Http::assertSentCount(1);
    }

    public function test_mart_description_and_actual_duration_need_no_collector_fallback(): void
    {
        Http::fake(['mart.test/*' => Http::response($this->page($this->record(['description' => 'Safe <script>description</script>', 'actual_start' => '2026-01-01T01:00:00Z', 'actual_finish' => '2026-01-01T03:30:00Z'])))]);
        $this->signIn();
        $this->get(route('work-orders.show', ['ref' => self::REFERENCE]))->assertOk()->assertSee('2.50')->assertSee('&lt;script&gt;', false)->assertDontSee('<script>description</script>', false)->assertDontSee('999');
        Http::assertSentCount(1);
    }

    public function test_cross_scope_work_order_responses_are_not_exposed(): void
    {
        Http::fake(['mart.test/*' => Http::response($this->page($this->record(['site_code' => 'OTHER', 'description' => 'OUTSIDE-SCOPE'])))]);
        $this->signIn();
        $this->get(route('work-orders.show', ['ref' => self::REFERENCE]))->assertOk()->assertSee('Detail WO belum terhubung')->assertDontSee('OUTSIDE-SCOPE');
        $this->get(route('work-orders.show', ['ref' => 'workorder:OTHER:123']))->assertNotFound();
        Http::assertSentCount(1);
    }

    private function mapping(): array
    {
        return ['schema_version' => 1, 'state' => 'DRAFT_NOT_APPLIED', 'scope' => ['site_code' => 'BSR', 'organization_code' => 'IP', 'unit' => 'CS01'], 'source_snapshot_at' => '2026-11-05T00:00:00Z', 'reference' => ['name' => 'synthetic.xlsx', 'sheet' => 'HIRARKI REVISI', 'populated_rows' => 1], 'summary' => ['in_scope_assets' => 1, 'excluded_assets' => 1, 'mapping_states' => ['EXACT_UNIQUE' => 1, 'EXACT_AMBIGUOUS' => 0, 'NO_EXACT_MATCH' => 0]], 'assets' => [['canonical_id' => 'asset:BSR:A1', 'source' => ['source_asset_number' => 'A1', 'description' => 'Synthetic Pump', 'site_code' => 'BSR', 'organization_code' => 'IP', 'unit' => 'CS01'], 'mapping_state' => 'EXACT_UNIQUE', 'engineering_group' => ['label' => 'Peralatan berputar', 'status' => 'ENGINEERING_INFERENCE', 'basis' => 'Description keyword: Pump'], 'document_candidates' => [['row' => 2, 'match_columns' => ['old_kks'], 'new_kks' => 'PROPOSED-A1', 'alias' => null, 'new_parent' => 'DOCUMENT-PARENT', 'document_role_code' => 'E']]]]];
    }

    private function writeMapping(array $data): void
    {
        $this->mappingFile = tempnam(sys_get_temp_dir(), 'nadi-mapping-test-');
        file_put_contents($this->mappingFile, json_encode($data));
        config(['services.asset_mapping.file' => $this->mappingFile]);
    }

    public function test_mapping_distinguishes_source_proposals_and_inference(): void
    {
        $this->writeMapping($this->mapping());
        $this->signIn();
        $this->get('/assets/mapping')->assertOk()->assertSee('Synthetic Pump')->assertSee('PROPOSED-A1')->assertSee('Inferensi engineering')->assertSee('tidak diterapkan');
        $this->get('/assets/mapping?state=NO_EXACT_MATCH')->assertOk()->assertDontSee('PROPOSED-A1');
        $source = $this->mapping()['assets'][0]['source'] + ['canonical_id' => 'asset:BSR:A1'];
        $this->assertNotNull(app(BsrAssetMapping::class)->forAsset($source));
        $this->assertNull(app(BsrAssetMapping::class)->forAsset(array_replace($source, ['unit' => 'CS02'])));
        Http::assertNothingSent();
    }

    public function test_mapping_fails_closed_on_other_unit_or_wrong_identity(): void
    {
        $data = $this->mapping();
        $data['assets'][0]['source']['unit'] = 'CS03';
        $this->writeMapping($data);
        $this->assertNull(app(BsrAssetMapping::class)->snapshot());
        $this->signIn();
        $this->get('/assets/mapping')->assertOk()->assertSee('Draft mapping belum tersedia')->assertDontSee('PROPOSED-A1');
    }
}
