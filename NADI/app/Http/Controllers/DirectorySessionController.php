<?php

namespace App\Http\Controllers;

use App\Auth\DirectoryAccounts;
use App\Auth\DirectoryAuthenticator;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;
use Illuminate\Support\Facades\RateLimiter;
use Illuminate\Validation\ValidationException;

final class DirectorySessionController
{
    public function create(Request $request)
    {
        abort_unless(config('directory.enabled') === true && config('session.secure') === true && $request->isSecure(), 404);

        return view('auth.directory');
    }

    public function store(Request $request, DirectoryAuthenticator $directory, DirectoryAccounts $accounts)
    {
        abort_unless(config('directory.enabled') === true && config('session.secure') === true && $request->isSecure(), 404);
        $ipKey = 'directory-login-ip:'.hash('sha256', (string) $request->ip());
        // Consume the shared IP budget even for malformed credentials.
        if (RateLimiter::tooManyAttempts($ipKey, 20)) {
            throw ValidationException::withMessages(['login' => 'Terlalu banyak percobaan. Coba lagi dalam satu menit.']);
        }
        RateLimiter::hit($ipKey, 60);
        $credentials = $request->validate(['login' => ['required', 'string', 'max:254'], 'password' => ['required', 'string', 'max:256']]);
        $group = config('directory.required_group');
        $realm = config('directory.realm');
        $user = null;
        if (is_string($group) && trim($group) !== '' && is_string($realm) && preg_match('/\A[a-z0-9._-]{1,64}\z/', $realm)) {
            try {
                $identity = $directory->authenticate($credentials['login'], $credentials['password'], $group);
                if ($identity !== null && hash_equals($group, $identity->authorizedGroup)) {
                    $user = $accounts->resolve($identity, $realm);
                }
            } catch (\Exception) {
                // Keep exception details, directory attributes, and passwords out of the response and logs.
            }
        }
        if (! $user) {
            throw ValidationException::withMessages(['login' => 'Tidak dapat masuk dengan akun direktori.']);
        }
        Auth::login($user);
        $request->session()->regenerate();
        $request->session()->forget('url.intended');
        $request->session()->put([
            'auth_version' => $user->auth_version,
            'directory_until' => now()->addMinutes(15)->timestamp,
            'directory_realm' => $realm,
            'directory_group_hash' => hash('sha256', $group),
        ]);

        return redirect()->route('viewer.home');
    }
}
