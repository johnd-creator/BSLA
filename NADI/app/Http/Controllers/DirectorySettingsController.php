<?php

namespace App\Http\Controllers;

use App\Support\DirectorySettingsDraft;
use Illuminate\Http\Request;
use Illuminate\Support\Arr;
use Illuminate\Support\Facades\Validator;

final class DirectorySettingsController
{
    public function show(Request $request, DirectorySettingsDraft $draft)
    {
        $this->requireLocalAdminTransport($request);

        return response()->view('settings.directory', ['draft' => $draft->read()])
            ->header('Cache-Control', 'no-store, private');
    }

    public function update(Request $request, DirectorySettingsDraft $draft)
    {
        $this->requireLocalAdminTransport($request);
        // Never flash or process unsupported fields (including any bind password).
        abort_if($request->query->count() > 0, 422);
        abort_if(array_diff(array_keys($request->all()), ['_token', 'current_password', ...DirectorySettingsDraft::FIELDS]) !== [], 422);

        $validation = Validator::make($request->all(), [
            'host' => ['bail', 'nullable', 'string', 'max:253', function (string $attribute, string $host, \Closure $fail): void {
                if (! str_contains($host, '.') || filter_var($host, FILTER_VALIDATE_IP) || ! filter_var($host, FILTER_VALIDATE_DOMAIN, FILTER_FLAG_HOSTNAME)) {
                    $fail('Masukkan FQDN server AD saja, tanpa IP, skema, atau port.');
                }
            }],
            'base_dn' => ['bail', 'nullable', 'string', 'max:512', $this->validateDn(...)],
            'group_dn' => ['bail', 'nullable', 'string', 'max:512', $this->validateDn(...)],
            'bind_name' => ['bail', 'nullable', 'string', 'max:512', function (string $attribute, string $value, \Closure $fail): void {
                if (! $this->isDn($value)
                    && ! preg_match('/\A(?:[A-Za-z0-9_.-]+@[A-Za-z0-9.-]+|[A-Za-z0-9_.-]+\\\\[A-Za-z0-9_.-]+)\z/', $value)) {
                    $fail('Masukkan UPN, DOMAIN\\username, atau DN akun bind.');
                }
            }],
            'current_password' => ['required', 'string', 'max:256', 'current_password:web'],
        ], ['current_password.current_password' => 'Kata sandi akun lokal NADI tidak sesuai.']);

        if ($validation->fails()) {
            // Keep both the current password and all attempted values out of session flash.
            return to_route('settings.directory')->withErrors($validation);
        }
        $draft->save(Arr::only($validation->validated(), DirectorySettingsDraft::FIELDS));

        return to_route('settings.directory')->with('status', 'Draft disimpan. Konfigurasi login LDAP tidak berubah.');
    }

    private function validateDn(string $attribute, string $value, \Closure $fail): void
    {
        if (! $this->isDn($value)) {
            $fail('Masukkan DN lengkap, misalnya OU=People,DC=example,DC=internal.');
        }
    }

    private function isDn(string $value): bool
    {
        // Conservative DN syntax for the AD pilot; an escaped comma is retained.
        $rdn = '(?:[a-z][a-z0-9-]*=[^,+\p{C}\\\\]*(?:\\\\[^\p{C}][^,+\p{C}\\\\]*)*)';

        return preg_match('/\A(?:'.$rdn.'[,+])*DC=[a-z0-9-]+(?:,DC=[a-z0-9-]+)+\z/iu', $value) === 1;
    }

    private function requireLocalAdminTransport(Request $request): void
    {
        abort_unless($request->user()->directory_subject === null, 403);
        $loopback = app()->environment('local') && in_array($request->ip(), ['127.0.0.1', '::1'], true)
            && in_array($request->getHost(), ['127.0.0.1', 'localhost', '::1', '[::1]'], true);
        abort_unless($request->isSecure() || $loopback, 403);
    }
}
