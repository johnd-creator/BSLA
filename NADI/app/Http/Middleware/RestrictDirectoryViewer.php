<?php

namespace App\Http\Middleware;

use App\Auth\DirectoryAccounts;
use App\Enums\Role;
use Closure;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;
use Symfony\Component\HttpFoundation\Response;

final class RestrictDirectoryViewer
{
    public function handle(Request $request, Closure $next): Response
    {
        $user = $request->user();
        if (! $user || ($user->directory_subject === null && ! in_array(Role::Viewer->value, $user->roles ?? [], true))) {
            return $next($request);
        }
        $until = $request->session()->get('directory_until');
        $group = config('directory.required_group');
        if (! DirectoryAccounts::eligible($user) || ! $request->isSecure()
            || config('directory.enabled') !== true || config('session.secure') !== true || ! is_int($until) || now()->timestamp >= $until
            || $request->session()->get('directory_realm') !== config('directory.realm')
            || ! is_string($group) || trim($group) === ''
            || $request->session()->get('directory_group_hash') !== hash('sha256', $group)) {
            Auth::logout();
            $request->session()->invalidate();
            $request->session()->regenerateToken();

            return redirect()->route('login');
        }

        abort_unless(
            ($request->isMethod('GET') && $request->routeIs('viewer.home'))
            || ($request->isMethod('POST') && $request->routeIs('logout')),
            403,
        );

        return $next($request);
    }
}
