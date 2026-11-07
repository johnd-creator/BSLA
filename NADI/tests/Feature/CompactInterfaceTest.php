<?php

namespace Tests\Feature;

use App\Models\User;
use DOMDocument;
use DOMXPath;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Http;
use Tests\TestCase;

class CompactInterfaceTest extends TestCase
{
    use RefreshDatabase;

    private function document(string $html): DOMXPath
    {
        $previous = libxml_use_internal_errors(true);
        $document = new DOMDocument;
        $document->loadHTML('<?xml encoding="utf-8" ?>'.$html);
        libxml_clear_errors();
        libxml_use_internal_errors($previous);

        return new DOMXPath($document);
    }

    private function signIn(): void
    {
        $user = User::factory()->create(['roles' => ['ENGINEER']])->refresh();
        $this->actingAs($user)->withSession(['auth_version' => $user->auth_version]);
    }

    public function test_login_is_a_single_form_without_a_marketing_panel(): void
    {
        $response = $this->get('/login')->assertOk()
            ->assertDontSee('login-story')->assertDontSee('story-content');
        $document = $this->document($response->getContent());

        $this->assertSame(1, $document->query('//main')->length);
        $this->assertSame(1, $document->query('//h1')->length);
        $this->assertSame(1, $document->query('//form[@method="post"]')->length);
        $this->assertSame(1, $document->query('//input[@name="_token"]')->length);
        $this->assertSame(1, $document->query('//label[@for="login"]')->length);
        $this->assertSame(1, $document->query('//input[@autocomplete="current-password"]')->length);
    }

    public function test_workspace_has_one_heading_and_keyboard_access_to_content(): void
    {
        $this->signIn();
        $response = $this->get('/')->assertOk()
            ->assertDontSee('page-heading')->assertDontSee('workspace-label');
        $document = $this->document($response->getContent());

        $this->assertSame(1, $document->query('//h1')->length);
        $this->assertSame('Beranda', $document->query('//h1')->item(0)->textContent);
        $this->assertSame(1, $document->query('//a[@href="#content"]')->length);
        $this->assertSame(1, $document->query('//main[@id="content"][@tabindex="-1"]')->length);
    }

    public function test_mobile_navigation_has_native_no_script_fallback(): void
    {
        $this->signIn();
        $document = $this->document($this->get('/')->assertOk()->getContent());

        $this->assertSame(1, $document->query('//details[@class="navigation"][@open]/summary')->length);
        $this->assertSame(1, $document->query('//details[@class="navigation"]//nav')->length);
        $this->assertSame(0, $document->query('//details[@class="navigation"]//form[@method="post"]')->length);
    }

    public function test_logout_is_available_in_the_header_outside_the_mobile_menu(): void
    {
        $this->signIn();
        $document = $this->document($this->get('/')->assertOk()->getContent());

        $forms = $document->query('//header//form[@method="post"][@action="'.route('logout').'"]');
        $this->assertSame(1, $forms->length);
        $this->assertSame(1, $document->query('//header//form//input[@name="_token"]')->length);
        $this->assertSame(1, $document->query('//header//form//button[@type="submit"]')->length);
        $this->assertStringContainsString('Keluar', $forms->item(0)->textContent);
        $this->assertSame(0, $document->query('//aside//form')->length);
        $this->assertSame(1, $document->query('//header//div[@aria-label="Akun saat ini"]')->length);
        $this->assertSame(1, $document->query('//header//svg[@aria-hidden="true"][@focusable="false"]')->length);
    }

    public function test_work_orders_keeps_asset_menu_open_and_marks_its_own_link(): void
    {
        Http::preventStrayRequests();
        config(['services.reliability_mart.url' => 'http://mart.test']);
        Http::fake(['mart.test/*' => Http::response([], 503)]);
        $this->signIn();
        $document = $this->document($this->get('/work-orders')->assertOk()->getContent());

        $this->assertSame(1, $document->query('//details[@class="asset-menu"][@open]')->length);
        $this->assertSame(1, $document->query('//nav//a[@aria-current="page"]')->length);
        $this->assertSame('Work Orders', $document->query('//nav//a[@aria-current="page"]')->item(0)->textContent);
    }
}
