<?php

namespace App\Http\Controllers;

use App\Models\PdmActivity;
use App\Services\PdmTrend;
use Illuminate\Http\Request;

class PdmTrendController extends Controller
{
    public function __invoke(Request $request, PdmTrend $service)
    {
        $filters = $request->validate([
            'asset_ref' => ['nullable', 'string', 'max:240', 'not_regex:/[\\\\\/]/'],
            'activity' => ['nullable', 'integer', 'min:1'],
            'point' => ['nullable', 'string', 'max:100'],
            'q' => ['nullable', 'string', 'max:120'],
        ]);
        $assetRef = $filters['asset_ref'] ?? null;
        $anchor = null;
        if (! empty($filters['activity'])) {
            $anchor = PdmActivity::findOrFail($filters['activity']);
            abort_if($assetRef && $assetRef !== $anchor->asset_ref, 422);
            $assetRef = $anchor->asset_ref;
        } elseif ($assetRef) {
            $anchor = PdmActivity::where('asset_ref', $assetRef)->newestMeasurement()->first();
        }
        $assets = null;
        if (! $assetRef) {
            $assets = PdmActivity::query()->select('asset_ref')->distinct()
                ->when(! empty($filters['q']), fn ($q) => $q->where('asset_ref', 'like', '%'.$filters['q'].'%'))
                ->orderBy('asset_ref')->paginate(20)->withQueryString();
        }
        $variants = $assetRef ? PdmActivity::where('asset_ref', $assetRef)
            ->selectRaw('MAX(id) as id')->addSelect(['template_id', 'template_fingerprint', 'method', ...PdmTrend::CONTEXT])
            ->groupBy(['template_id', 'template_fingerprint', 'method', ...PdmTrend::CONTEXT])->orderByDesc('id')->limit(51)->get() : collect();
        $variantsLimited = $variants->count() > 50;
        $variants = $variants->take(50);
        $points = $anchor ? collect($anchor->template_snapshot['fields'] ?? [])->where('type', 'number')->values() : collect();
        $point = $filters['point'] ?? ($points->first()['key'] ?? null);
        $trend = $anchor && $point ? $service->forPoint($anchor, $point) : null;

        return view('pdm.trends', compact('assetRef', 'assets', 'anchor', 'variants', 'variantsLimited', 'points', 'point', 'trend'));
    }
}
