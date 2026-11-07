<?php

namespace Tests\Feature;

use App\Models\User;
use App\Services\PdmFormCatalog;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Http;
use Tests\TestCase;

class PrivateCatalogTest extends TestCase
{
    use RefreshDatabase;

    public function test_missing_private_catalog_does_not_load_synthetic_or_source_data(): void
    {
        Http::preventStrayRequests();
        config(['pdm.catalog' => storage_path('app/private/not-provisioned.json')]);
        $this->assertSame([], app(PdmFormCatalog::class)->all());
        $user = User::factory()->create(['roles' => ['ENGINEER'], 'active' => true])->refresh();
        $this->actingAs($user)->withSession(['auth_version' => $user->auth_version]);
        $this->get('/pdm/templates')->assertOk()->assertSee('Katalog lokal belum tersedia')->assertDontSee('SYNTHETIC PUMP');
        Http::assertNothingSent();
    }

    public function test_test_catalog_is_explicitly_synthetic_and_selected_for_tests(): void
    {
        $catalog = json_decode(file_get_contents(base_path('tests/Fixtures/pdm-catalog.json')), true);
        $this->assertSame('SYNTHETIC_TEST_FIXTURE', $catalog['state']);
        $this->assertSame(base_path('tests/Fixtures/pdm-catalog.json'), config('pdm.catalog'));
        foreach ($catalog['templates'] as $template) {
            $this->assertStringStartsWith('SYNTHETIC_', $template['id']);
            $this->assertStringContainsString('SYNTHETIC-', $template['candidates'][0]['canonical_id']);
        }
    }
}
