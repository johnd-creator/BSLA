<?php

namespace App\Http\Middleware;

use App\Support\DevelopmentAccess;
use Closure;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;
use Symfony\Component\HttpFoundation\Response;

class CurrentAccount
{
    public function handle(Request $request, Closure $next): Response
    {
        $user = $request->user();
        if (! $user || ! $user->active || ! DevelopmentAccess::allowed($user, $request) || ! is_int($request->session()->get('auth_version')) || $request->session()->get('auth_version') !== $user->auth_version) {
            Auth::logout();
            $request->session()->invalidate();
            $request->session()->regenerateToken();

            return redirect()->route('login')->with('status', 'Sesi berakhir. Silakan masuk kembali.');
        }

        return $next($request);
    }
}
