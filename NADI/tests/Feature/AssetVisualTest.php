<?php

namespace Tests\Feature;

use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Http;
use PHPUnit\Framework\Attributes\DataProvider;
use Tests\TestCase;

class AssetVisualTest extends TestCase
{
    use RefreshDatabase;

    public function test_asset_detail_keeps_an_honest_media_slot_and_existing_context(): void
    {
        Http::preventStrayRequests();
        config(['services.reliability_mart.url' => 'http://mart.test', 'services.asset_mapping.file' => null]);
        $asset = [
            'canonical_id' => 'asset:BSR:VISUAL-TEST',
            'source_asset_number' => 'VISUAL-TEST',
            'site_code' => 'BSR',
            'organization_code' => 'IP',
            'description' => 'Synthetic visual test asset',
            'registered' => false,
            'hierarchy_category' => 'equipment',
            'scope_basis' => 'SOURCE_PARENT_CHAIN',
        ];
        Http::fake(['mart.test/v1/reliability/assets/inventory/*' => Http::response($asset)]);
        $user = User::factory()->create(['roles' => ['ENGINEER']])->refresh();
        $this->actingAs($user)->withSession(['auth_version' => $user->auth_version]);

        $this->get(route('assets.show', $asset['canonical_id']))->assertOk()
            ->assertSee('Gambar aset')->assertSee('Belum ada gambar')
            ->assertSee('3D interaktif belum tersedia')->assertSee('Read only')
            ->assertSee('Synthetic visual test asset')->assertSee('Lihat WO untuk Asset ini')
            ->assertSee('Riwayat PdM lokal')->assertSee('Input pengukuran PdM')
            ->assertDontSee('type="file"', false)->assertDontSee('<canvas', false)
            ->assertDontSee('Buka 3D')
            ->assertSee('Reliability score')->assertSee('Belum cukup data')
            ->assertSee('Reliability score belum tersedia.')
            ->assertSee('Kejadian gangguan yang sudah diverifikasi')
            ->assertSee('Jam operasi dan availability dari historian')
            ->assertSee('Riwayat pemeliharaan yang tervalidasi')
            ->assertSee('Hasil PdM yang tervalidasi')
            ->assertSee('Kelengkapan data untuk score:')->assertSee('Belum diverifikasi');
        Http::assertSentCount(1);
        Http::assertNotSent(fn ($request) => $request->method() !== 'GET');
    }

    #[DataProvider('actionContexts')]
    public function test_asset_sidebar_keeps_each_context_link_once_and_preserves_access(string $role, bool $registered): void
    {
        Http::preventStrayRequests();
        config(['services.reliability_mart.url' => 'http://mart.test', 'services.asset_mapping.file' => null]);
        $asset = [
            'canonical_id' => 'asset:BSR:SIDEBAR-TEST',
            'source_asset_number' => 'SIDEBAR-TEST',
            'site_code' => 'BSR',
            'organization_code' => 'IP',
            'description' => 'Synthetic sidebar test asset',
            'registered' => $registered,
            'hierarchy_category' => 'equipment',
            'scope_basis' => 'SOURCE_PARENT_CHAIN',
        ];
        Http::fake(['mart.test/v1/reliability/assets/inventory/*' => Http::response($asset)]);
        $user = User::factory()->create(['roles' => [$role]])->refresh();
        $response = $this->actingAs($user)->withSession(['auth_version' => $user->auth_version])
            ->get(route('assets.show', $asset['canonical_id']))->assertOk();

        $previous = libxml_use_internal_errors(true);
        $document = new \DOMDocument;
        $document->loadHTML('<?xml encoding="utf-8" ?>'.$response->getContent());
        libxml_clear_errors();
        libxml_use_internal_errors($previous);
        $xpath = new \DOMXPath($document);
        $sidebar = '//aside[@class="asset-detail-sidebar"]';
        $menu = $sidebar.'//nav[@aria-label="Menu Asset"]';
        $this->assertSame(1, $xpath->query($sidebar)->length);
        $this->assertSame(1, $xpath->query($menu)->length);
        $this->assertSame(1, $xpath->query($menu.'/preceding-sibling::figure[@class="asset-visual"]')->length);

        // Task actions precede read-only history, with every existing permission preserved.
        $expected = $role === 'ENGINEER' ? [
            route('pdm.create', ['asset_ref' => $asset['canonical_id']]),
            route('disruptions.create', ['asset_ref' => $asset['canonical_id']]),
            route('priorities.create', ['asset_ref' => $asset['canonical_id']]),
        ] : [];
        if ($registered && $role === 'ENGINEER') {
            $expected[] = route('inspections.create', ['asset_ref' => $asset['canonical_id']]);
        }
        $expected[] = route('work-orders.index', ['asset_ref' => $asset['canonical_id']]);
        $expected[] = route('assets.timeline', $asset['canonical_id']);
        $expected[] = route('pdm.history', ['asset_ref' => $asset['canonical_id']]);
        $expected[] = route('pdm.trends', ['asset_ref' => $asset['canonical_id']]);
        $expected[] = route('work-orders.index', ['asset_ref' => $asset['canonical_id'], 'view' => 'disturbances']);
        if ($registered) {
            $expected[] = route('operations', ['equipment' => $asset['canonical_id']]);
        }
        $links = iterator_to_array($xpath->query($menu.'//a'));
        $this->assertSame($expected, array_map(fn ($link) => $link->getAttribute('href'), $links));
        foreach ($expected as $href) {
            $this->assertSame(1, $xpath->query('//a[@href="'.$href.'"]')->length);
        }
        $this->assertSame(0, $xpath->query('//div[@class="asset-draft-action"]')->length);
        $this->assertSame(1, $xpath->query('//section[@aria-labelledby="asset-reliability-title"]')->length);
        $this->assertSame('Belum cukup data', $xpath->query('//span[@class="asset-reliability-pending"]')->item(0)->textContent);
        $this->assertSame(4, $xpath->query('//ul[@class="asset-reliability-inputs"]/li')->length);
        $this->assertSame(0, $xpath->query('//section[@aria-labelledby="asset-reliability-title"]//meter | //section[@aria-labelledby="asset-reliability-title"]//progress')->length);
        $response->assertSee('Canonical ID')->assertSee('Registry keandalan')
            ->assertSee($registered ? 'Terdaftar' : 'Belum terdaftar');
        Http::assertSentCount(1);
        Http::assertNotSent(fn ($request) => $request->method() !== 'GET');
    }

    public static function actionContexts(): array
    {
        $contexts = [];
        foreach (['ADMIN', 'ENGINEER', 'SUPERVISOR', 'MANAGER'] as $role) {
            foreach ([false, true] as $registered) {
                $contexts[$role.($registered ? ' Registry' : ' inventory')] = [$role, $registered];
            }
        }

        return $contexts;
    }

    public function test_media_component_can_render_a_png_without_an_upload_or_viewer(): void
    {
        $this->blade('<x-asset-visual asset-name="Motor & pump" thumbnail="/images/assets/motor.png" />')
            ->assertSee('src="/images/assets/motor.png"', false)
            ->assertSee('alt="Gambar Motor &amp; pump"', false)
            ->assertSee('width="320" height="180"', false)
            ->assertSee('3D interaktif belum tersedia')
            ->assertDontSee('Belum ada gambar')->assertDontSee('<button', false)
            ->assertDontSee('<a ', false)->assertDontSee('type="file"', false);
    }

    public function test_empty_media_slot_avoids_a_broken_image_and_fake_action(): void
    {
        $this->blade('<x-asset-visual asset-name="Motor" />')
            ->assertSee('Belum ada gambar')->assertSee('aria-label="Gambar aset"', false)
            ->assertDontSee('<img', false)->assertDontSee('<button', false)
            ->assertDontSee('<a ', false);
    }
}
