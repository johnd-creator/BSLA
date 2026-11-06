<?php

namespace App\Http\Controllers;

use App\Services\BsrAssetMapping;
use App\Services\ReliabilityMart;
use Illuminate\Http\Request;
use Illuminate\Validation\Rule;
use Symfony\Component\HttpKernel\Exception\HttpExceptionInterface;
use Throwable;

class AssetController extends Controller
{
    public function index(Request $request, ReliabilityMart $mart)
    {
        $query = $request->validate([
            'offset' => ['sometimes', 'integer', 'min:0', 'max:1000000'],
            'status' => ['nullable', 'string', 'max:60'],
            'unit' => ['nullable', 'string', 'max:60'],
            'asset_type' => ['nullable', 'string', 'max:100'],
            'sort' => ['nullable', Rule::in(['updated_desc', 'updated_asc', 'status'])],
        ]);
        $query['offset'] = (int) ($query['offset'] ?? 0);
        try {
            $page = $mart->assets(array_filter($query, fn ($value) => $value !== null && $value !== ''));
        } catch (Throwable) {
            $page = null;
        }

        return view('assets.index', compact('page'));
    }

    public function show(string $asset, ReliabilityMart $mart, BsrAssetMapping $mapping)
    {
        abort_if(strlen($asset) > 240 || str_contains($asset, '/') || str_contains($asset, '\\'), 404);
        try {
            $record = $mart->detail($asset);
        } catch (Throwable $error) {
            if ($error instanceof HttpExceptionInterface && $error->getStatusCode() === 404) {
                throw $error;
            }
            $record = null;
        }

        $draftMapping = $record ? $mapping->forAsset($record) : null;

        return view('assets.show', compact('record', 'draftMapping'));
    }
}
