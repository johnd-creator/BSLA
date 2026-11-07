<?php

namespace App\Http\Controllers;

use App\Models\User;
use App\Support\DevelopmentAccess;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;
use Illuminate\Support\Facades\RateLimiter;
use Illuminate\Support\Str;
use Illuminate\Validation\ValidationException;

class SessionController extends Controller
{
    public function create()
    {
        return view('auth.login');
    }

    public function store(Request $request)
    {
        // Keep existing email-based clients working during the username addition.
        if (! $request->has('login') && is_string($request->input('email'))) {
            $request->merge(['login' => $request->input('email')]);
        }
        if (is_string($request->input('login'))) {
            $request->merge(['login' => Str::lower(trim($request->input('login')))]);
        }
        $data = $request->validate(['login' => ['required', 'string', 'max:254'], 'password' => ['required', 'string', 'max:256']]);
        $key = 'login:'.hash('sha256', $data['login'].'|'.$request->ip());
        $ipKey = 'login-ip:'.hash('sha256', (string) $request->ip());
        if (RateLimiter::tooManyAttempts($key, 5) || RateLimiter::tooManyAttempts($ipKey, 30)) {
            throw ValidationException::withMessages(['login' => 'Terlalu banyak percobaan. Coba lagi dalam satu menit.']);
        }
        RateLimiter::hit($ipKey, 60);
        $field = filter_var($data['login'], FILTER_VALIDATE_EMAIL) ? 'email' : 'username';
        $credentials = [$field => $data['login'], 'password' => $data['password'], 'active' => true];
        if (! Auth::attemptWhen($credentials, fn (User $user) => DevelopmentAccess::allowed($user, $request))) {
            RateLimiter::hit($key, 60);
            throw ValidationException::withMessages(['login' => 'Username/email atau kata sandi tidak sesuai.']);
        }
        RateLimiter::clear($key);
        $request->session()->regenerate();
        $request->session()->put('auth_version', $request->user()->auth_version);

        return redirect()->intended(route('home'));
    }

    public function destroy(Request $request)
    {
        Auth::logout();
        $request->session()->invalidate();
        $request->session()->regenerateToken();

        return redirect()->route('login');
    }
}
