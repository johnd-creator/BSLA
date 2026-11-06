<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::table('users', function (Blueprint $table) {
            $table->string('username', 32)->nullable()->unique();
            $table->boolean('development_only')->default(false);
        });
        // Preserve existing Laravel development identities and revoke stale grants.
        // No connection or migration to the existing FastAPI application store.
        foreach (DB::table('users')->get(['id', 'roles', 'auth_version']) as $user) {
            $before = json_decode($user->roles, true, flags: JSON_THROW_ON_ERROR);
            $after = array_values(array_unique(array_map(fn ($role) => match ($role) {
                'AUTHOR' => 'ENGINEER', 'REVIEWER' => 'SUPERVISOR', default => $role,
            }, $before)));
            if ($before !== $after) {
                DB::table('users')->where('id', $user->id)->update(['roles' => json_encode($after), 'auth_version' => $user->auth_version + 1]);
            }
        }
    }

    public function down(): void
    {
        // Never rewrite role grants backwards automatically.
        Schema::table('users', fn (Blueprint $table) => $table->dropColumn(['username', 'development_only']));
    }
};
