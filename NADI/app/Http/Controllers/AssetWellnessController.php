<?php

namespace App\Http\Controllers;

use App\Services\AssetWellness;
use App\Services\ReliabilityMart;
use App\Services\ReliabilityPeriod;
use Illuminate\Http\Request;

class AssetWellnessController extends Controller
{
    public function index(Request $request, AssetWellness $wellness, ReliabilityMart $mart)
    {
        $filters = $request->validate([
            'asset_ref' => ['nullable', 'string', 'max:240', 'starts_with:asset:MAXIMO:MXASSET:BSR:IP:', 'not_regex:/[\\\\\/]/'],
            'year' => ['nullable', 'integer', 'between:1900,'.now('Asia/Jakarta')->year],
        ]);
        $assetRef = $filters['asset_ref'] ?? null;
        $period = ReliabilityPeriod::fromRequest($request);
        $year = $period->start->year;
        $report = $assetRef ? $wellness->report($assetRef, $period, $mart) : null;

        return response()->view('wellness.index', compact('assetRef', 'year', 'period', 'report'))->header('Cache-Control', 'no-store, private');
    }
}
