<?php

use App\Enums\Role;
use App\Http\Controllers\ActionBoardController;
use App\Http\Controllers\AssetController;
use App\Http\Controllers\AssetMappingController;
use App\Http\Controllers\InspectionController;
use App\Http\Controllers\OperationsController;
use App\Http\Controllers\SessionController;
use App\Http\Controllers\UserController;
use App\Http\Controllers\WorkOrderController;
use Illuminate\Support\Facades\Route;

Route::middleware('guest')->group(function () {
    Route::get('/login', [SessionController::class, 'create'])->name('login');
    Route::post('/login', [SessionController::class, 'store'])->name('login.store');
});

Route::middleware(['auth', 'current-account'])->group(function () {
    Route::view('/', 'home')->name('home');
    Route::get('/operations', OperationsController::class)->name('operations');
    Route::get('/action-board', ActionBoardController::class)->name('action-board');
    Route::resource('inspections', InspectionController::class)->except(['destroy']);
    Route::post('/logout', [SessionController::class, 'destroy'])->name('logout');
    Route::get('/work-orders', [WorkOrderController::class, 'index'])->name('work-orders.index');
    Route::get('/work-orders/detail', [WorkOrderController::class, 'show'])->name('work-orders.show');
    Route::get('/assets', [AssetController::class, 'index'])->name('assets.index');
    Route::get('/assets/mapping', AssetMappingController::class)->name('assets.mapping');
    Route::get('/assets/{asset}', [AssetController::class, 'show'])->name('assets.show');
    Route::middleware('can:manage-users')->group(function () {
        Route::resource('users', UserController::class)->only(['index', 'create', 'store', 'edit', 'update']);
        Route::get('/roles', fn () => view('users.roles', ['roles' => Role::cases()]))->name('roles.index');
    });
});
