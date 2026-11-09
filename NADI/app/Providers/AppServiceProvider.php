<?php

namespace App\Providers;

use App\Enums\Role;
use App\Models\AssetDisruption;
use App\Models\AssetPriority;
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
        Gate::define('write-wellness-policies', fn (User $user) => $user->hasRole(Role::Engineer));
        Gate::define('approve-reliability', fn (User $user) => $user->hasRole(Role::Supervisor));
        Gate::define('write-asset-priorities', fn (User $user) => $user->hasRole(Role::Engineer));
        Gate::define('update-asset-priority', fn (User $user, AssetPriority $priority) => $user->hasRole(Role::Engineer) && $priority->created_by === $user->id);
        Gate::define('write-asset-disruptions', fn (User $user) => $user->hasRole(Role::Engineer));
        Gate::define('update-asset-disruption', fn (User $user, AssetDisruption $event) => $user->hasRole(Role::Engineer) && $event->created_by === $user->id);
        Gate::define('write-pdm-activities', fn (User $user) => $user->hasRole(Role::Engineer));
        Gate::define('update-pdm-activity', fn (User $user, PdmActivity $activity) => $user->hasRole(Role::Engineer) && $activity->created_by === $user->id);
        Gate::define('manage-users', fn (User $user) => $user->hasRole(Role::Admin));
        Gate::define('write-inspection-drafts', fn (User $user) => $user->hasRole(Role::Engineer));
        Gate::define('update-inspection-draft', fn (User $user, InspectionDraft $draft) => $user->hasRole(Role::Engineer) && $draft->created_by === $user->id);
    }
}
