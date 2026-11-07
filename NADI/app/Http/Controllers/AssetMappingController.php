<?php

namespace App\Http\Controllers;

use App\Services\BsrAssetMapping;
use Illuminate\Http\Request;
use Illuminate\Pagination\LengthAwarePaginator;
use Illuminate\Validation\Rule;

class AssetMappingController extends Controller
{
    public function __invoke(Request $request, BsrAssetMapping $mapping)
    {
        $filters = $request->validate(['q' => ['nullable', 'string', 'max:100'], 'state' => ['nullable', Rule::in(['EXACT_UNIQUE', 'EXACT_AMBIGUOUS', 'NO_EXACT_MATCH'])], 'page' => ['sometimes', 'integer', 'min:1', 'max:10000']]);
        $snapshot = $mapping->snapshot();
        $items = collect($snapshot['assets'] ?? []);
        if (! empty($filters['state'])) {
            $items = $items->where('mapping_state', $filters['state']);
        }
        if (! empty($filters['q'])) {
            $term = mb_strtolower($filters['q']);
            $items = $items->filter(fn ($item) => str_contains(mb_strtolower(($item['source']['source_asset_number'] ?? '').' '.($item['source']['description'] ?? '')), $term));
        }
        $page = (int) ($filters['page'] ?? 1);
        $entries = new LengthAwarePaginator($items->forPage($page, 25)->values(), $items->count(), 25, $page, ['path' => route('assets.mapping'), 'query' => $request->only(['q', 'state'])]);

        return view('assets.mapping', compact('snapshot', 'entries'));
    }
}
