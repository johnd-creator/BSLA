<?php

namespace App\Providers;

use App\Enums\Role;
use App\Models\InspectionDraft;
use App\Models\PdmActivity;
use App\Models\User;
use Illuminate\Support\Facades\Gate;
use Illuminate\Support\ServiceProvider;

class AppServiceProvider extends ServiceProvider
{
    /**
     * Register any application services.
     */
    public function register(): void
    {
        //
    }

    /**
     * Bootstrap any application services.
     */
    public function boot(): void
    {
        Gate::define('write-pdm-activities', fn (User $user) => $user->hasRole(Role::Engineer));
        Gate::define('update-pdm-activity', fn (User $user, PdmActivity $activity) => $user->hasRole(Role::Engineer) && $activity->created_by === $user->id);
        Gate::define('manage-users', fn (User $user) => $user->hasRole(Role::Admin));
        Gate::define('write-inspection-drafts', fn (User $user) => $user->hasRole(Role::Engineer));
        Gate::define('update-inspection-draft', fn (User $user, InspectionDraft $draft) => $user->hasRole(Role::Engineer) && $draft->created_by === $user->id);
    }
}
