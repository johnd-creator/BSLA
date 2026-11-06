<?php

namespace App\Support;

use App\Models\User;
use Illuminate\Http\Request;

class DevelopmentAccess
{
    public static function allowed(User $user, Request $request): bool
    {
        if (! $user->development_only) {
            return true;
        }

        return app()->environment('local')
            && in_array($request->ip(), ['127.0.0.1', '::1'], true)
            && in_array($request->getHost(), ['127.0.0.1', 'localhost', '::1', '[::1]'], true);
    }
}
