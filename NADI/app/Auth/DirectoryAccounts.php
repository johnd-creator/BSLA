<?php

namespace App\Auth;

use App\Enums\Role;
use App\Models\User;
use Illuminate\Database\QueryException;

final class DirectoryAccounts
{
    public function resolve(DirectoryIdentity $identity, string $realm): ?User
    {
        if (! preg_match('/\A[a-z0-9._-]{1,64}\z/', $realm) || ! preg_match('/\A[a-z0-9._-]{1,128}\z/', $identity->stableId)) {
            return null;
        }
        $subject = hash('sha256', $realm.':'.$identity->stableId);
        try {
            $user = User::query()->where('directory_subject', $subject)->first() ?? new User;
            if (! $user->exists) {
                $user->directory_subject = $subject;
                $user->name = 'Pengguna direktori';
                // Never copy or match a directory email/username to a local account.
                $user->email = 'viewer-'.$subject.'@directory.invalid';
                $user->password = bin2hex(random_bytes(32)); // Unusable local placeholder, not the directory password.
                $user->roles = [Role::Viewer->value];
                $user->active = true;
                $user->save();
                $user->refresh();
            }
        } catch (QueryException) {
            // Missing migration, collision, or concurrent first login: deny, don't link.
            return null;
        }

        return self::eligible($user) ? $user : null;
    }

    public static function eligible(User $user): bool
    {
        return $user->active && ! $user->development_only
            && is_string($user->directory_subject) && preg_match('/\A[a-f0-9]{64}\z/', $user->directory_subject)
            && $user->roles === [Role::Viewer->value];
    }
}
