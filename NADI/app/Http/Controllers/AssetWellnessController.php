<?php

namespace App\Http\Controllers;

use App\Services\AssetWellness;
use App\Services\ReliabilityMart;
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
        $year = (int) ($filters['year'] ?? now('Asia/Jakarta')->year);
        $report = $assetRef ? $wellness->report($assetRef, $year, $mart) : null;

        return response()->view('wellness.index', compact('assetRef', 'year', 'report'))->header('Cache-Control', 'no-store, private');
    }
}
