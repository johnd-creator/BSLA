<?php

namespace Tests\Feature;

use App\Models\InspectionDraft;
use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Validator;
use Illuminate\Support\Str;
use Tests\TestCase;

class WorkspaceUiTest extends TestCase
{
    use RefreshDatabase;

    private function engineer(): static
    {
        Http::preventStrayRequests();
        Http::fake(['*' => Http::response([], 503)]);
        $user = User::factory()->create(['roles' => ['ENGINEER']])->refresh();

        return $this->actingAs($user)->withSession(['auth_version' => $user->auth_version]);
    }

    public function test_validation_summary_and_fields_are_linked_without_losing_old_input(): void
    {
        $this->engineer();
        $this->from('/inspections/create')->post('/inspections', [
            'request_key' => (string) Str::uuid(),
            'inspection_type' => 'request', 'request_reference' => 'UI-ONLY',
            'request_summary' => 'Retained test request',
        ])->assertSessionHasErrors('requester_name');
        $this->withViewErrors(session('errors')->getMessages())
            ->view('inspections.form', ['inspection' => new InspectionDraft(['inspection_type' => 'request'])])
            ->assertSee('data-error-field="requester_name"', false)
            ->assertSee('aria-describedby="error-requester-name"', false)
            ->assertSee('id="error-requester-name"', false)
            ->assertSee('Retained test request')
            ->assertSee('aria-invalid="true"', false);
        $this->assertDatabaseCount('inspection_drafts', 0);
    }

    public function test_active_filter_removal_resets_pagination_and_preserves_other_filters(): void
    {
        $this->engineer();
        $response = $this->get('/assets?q=motor&unit=CS01&offset=25')->assertOk();
        $response->assertSee('Filter aktif')->assertSee('Hapus filter Pencarian: motor')
            ->assertSee('href="http://127.0.0.1:8010/assets?unit=CS01"', false)
            ->assertSee('href="http://127.0.0.1:8010/assets?q=motor"', false);
    }

    public function test_form_validation_uses_human_indonesian_labels_without_changing_rules(): void
    {
        foreach (['en', 'id'] as $locale) {
            app()->setLocale($locale);
            $validator = Validator::make([
                'inspection_type' => 'request', 'request_reference' => str_repeat('x', 101),
                'inspected_on' => now()->addDay()->format('Y-m-d'),
            ], [
                'requester_name' => 'required_if:inspection_type,request',
                'request_reference' => 'string|max:100', 'inspected_on' => 'date_format:Y-m-d|before_or_equal:today',
                'readings.point.unit' => 'required',
            ]);
            $this->assertTrue($validator->fails());
            $this->assertSame('Nama peminta wajib diisi untuk inspeksi berdasarkan permintaan.', $validator->errors()->first('requester_name'));
            $this->assertSame('Referensi permintaan maksimal 100 karakter.', $validator->errors()->first('request_reference'));
            $this->assertSame('Tanggal inspeksi tidak boleh setelah hari ini.', $validator->errors()->first('inspected_on'));
            $this->assertSame('Satuan pengukuran wajib diisi.', $validator->errors()->first('readings.point.unit'));
        }
    }

    public function test_optional_pdm_filters_have_an_explicit_mobile_disclosure(): void
    {
        $this->engineer();
        $this->get('/pdm')->assertOk()->assertSee('data-mobile-filters', false)
            ->assertSee('data-active="false"', false)->assertSee('Jenis, metode & tahap', false);
        $this->get('/pdm?method=VIBRATION')->assertOk()->assertSee('data-active="true"', false);
    }
}
