<?php

use App\Enums\Role;
use App\Http\Controllers\ActionBoardController;
use App\Http\Controllers\AssetController;
use App\Http\Controllers\AssetDisruptionController;
use App\Http\Controllers\AssetMappingController;
use App\Http\Controllers\AssetPriorityController;
use App\Http\Controllers\CemsController;
use App\Http\Controllers\DisruptionWorkOrderController;
use App\Http\Controllers\HistorianController;
use App\Http\Controllers\InspectionController;
use App\Http\Controllers\OperationsController;
use App\Http\Controllers\OverviewController;
use App\Http\Controllers\PdmActivityController;
use App\Http\Controllers\PdmTrendController;
use App\Http\Controllers\ReliabilityController;
use App\Http\Controllers\ReliabilityReviewController;
use App\Http\Controllers\SessionController;
use App\Http\Controllers\UserController;
use App\Http\Controllers\WorkOrderController;
use Illuminate\Support\Facades\Route;

Route::middleware('guest')->group(function () {
    Route::get('/login', [SessionController::class, 'create'])->name('login');
    Route::post('/login', [SessionController::class, 'store'])->name('login.store');
});

Route::middleware(['auth', 'current-account'])->group(function () {
    Route::get('/', [OverviewController::class, 'index'])->name('home');
    Route::get('/reliability', [ReliabilityController::class, 'index'])->name('reliability.index');
    Route::get('/reliability/evidence.json', [ReliabilityController::class, 'download'])->name('reliability.download');
    Route::post('/reliability/snapshots', [ReliabilityController::class, 'store'])->name('reliability.snapshots.store');
    Route::get('/reliability/snapshots/{snapshot}', [ReliabilityController::class, 'show'])->name('reliability.snapshots.show');
    Route::get('/reliability/snapshots/{snapshot}/evidence.json', [ReliabilityController::class, 'snapshotDownload'])->name('reliability.snapshots.download');
    Route::get('/disruptions/{disruption}/reliability', [ReliabilityReviewController::class, 'index'])->name('reliability.reviews');
    Route::post('/disruptions/{disruption}/reliability', [ReliabilityReviewController::class, 'store'])->name('reliability.reviews.store');
    Route::get('/data-quality', [OverviewController::class, 'quality'])->name('data-quality');
    Route::get('/reports', [OverviewController::class, 'reports'])->name('reports.index');
    Route::get('/reports/summary.csv', [OverviewController::class, 'download'])->name('reports.download');
    Route::get('/operations/cems', [CemsController::class, 'index'])->name('operations.cems');
    Route::get('/operations/cems/refresh', [CemsController::class, 'index'])->name('operations.cems.refresh');
    Route::get('/operations/historian', [HistorianController::class, 'index'])->name('operations.historian');
    Route::post('/operations/historian/{action}', [HistorianController::class, 'action'])->whereIn('action', ['subscribe', 'heartbeat', 'release', 'history'])->name('operations.historian.action');
    Route::get('/operations', OperationsController::class)->name('operations');
    Route::get('/action-board', ActionBoardController::class)->name('action-board');
    Route::resource('priorities', AssetPriorityController::class)->except(['index', 'destroy']);
    Route::get('/pdm/trends', PdmTrendController::class)->name('pdm.trends');
    Route::get('/pdm/templates', [PdmActivityController::class, 'templates'])->name('pdm.templates');
    Route::get('/pdm/history', [PdmActivityController::class, 'history'])->name('pdm.history');
    Route::get('/disruptions/{disruption}/work-orders', [DisruptionWorkOrderController::class, 'index'])->name('disruptions.work-orders');
    Route::post('/disruptions/{disruption}/work-orders', [DisruptionWorkOrderController::class, 'store'])->name('disruptions.work-orders.store');
    Route::put('/disruptions/{disruption}/work-orders/{link}', [DisruptionWorkOrderController::class, 'update'])->name('disruptions.work-orders.update');
    Route::resource('disruptions', AssetDisruptionController::class)->except(['destroy']);
    Route::resource('pdm', PdmActivityController::class)->parameters(['pdm' => 'activity'])->except(['destroy']);
    Route::resource('inspections', InspectionController::class)->except(['destroy']);
    Route::post('/logout', [SessionController::class, 'destroy'])->name('logout');
    Route::get('/work-orders', [WorkOrderController::class, 'index'])->name('work-orders.index');
    Route::get('/work-orders/detail', [WorkOrderController::class, 'show'])->name('work-orders.show');
    Route::get('/assets', [AssetController::class, 'index'])->name('assets.index');
    Route::get('/assets/mapping', AssetMappingController::class)->name('assets.mapping');
    Route::get('/assets/{asset}/timeline', [AssetController::class, 'timeline'])->name('assets.timeline');
    Route::get('/assets/{asset}', [AssetController::class, 'show'])->name('assets.show');
    Route::middleware('can:manage-users')->group(function () {
        Route::resource('users', UserController::class)->only(['index', 'create', 'store', 'edit', 'update']);
        Route::get('/roles', fn () => view('users.roles', ['roles' => Role::cases()]))->name('roles.index');
    });
});
