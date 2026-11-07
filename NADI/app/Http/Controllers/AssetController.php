<?php

namespace App\Http\Controllers;

use App\Models\AssetDisruption;
use App\Services\AssetIllustration;
use App\Services\AssetTimeline;
use App\Services\BsrAssetMapping;
use App\Services\DisruptionLogbook;
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
            'q' => ['nullable', 'string', 'max:120'],
            'category' => ['nullable', Rule::in(['system', 'equipment', 'component', 'part', 'unknown'])],
            'asset_type' => ['nullable', 'string', 'max:100'],
            'sort' => ['nullable', Rule::in(['updated_desc', 'updated_asc', 'status'])],
        ]);
        $query['offset'] = (int) ($query['offset'] ?? 0);
        $population = 'inventory';
        $filters = array_filter($query, fn ($value) => $value !== null && $value !== '');
        try {
            try {
                $page = $mart->inventory($filters);
            } catch (HttpExceptionInterface $error) {
                if ($error->getStatusCode() !== 404) {
                    throw $error;
                }
                if ($request->filled('q') || $request->filled('category')) {
                    throw $error;
                }
                $population = 'registry';
                $page = $mart->assets($filters);
            }
        } catch (Throwable) {
            $page = null;
        }

        try {
            $summary = $mart->inventorySummary();
        } catch (Throwable) {
            $summary = null;
        }

        return view('assets.index', compact('page', 'summary', 'population'));
    }

    public function timeline(string $asset, ReliabilityMart $mart, AssetTimeline $timeline)
    {
        abort_if(strlen($asset) > 240 || str_contains($asset, '/') || str_contains($asset, '\\'), 404);
        try {
            $record = $mart->historyAsset($asset);
        } catch (Throwable $error) {
            if ($error instanceof HttpExceptionInterface && $error->getStatusCode() === 404) {
                throw $error;
            }
            $record = null;
        }

        $preview = $record ? $timeline->forAsset($record) : null;

        return view('assets.timeline', compact('record', 'preview', 'asset'));
    }

    public function show(string $asset, ReliabilityMart $mart, BsrAssetMapping $mapping, AssetIllustration $illustrations, DisruptionLogbook $disruptions)
    {
        abort_if(strlen($asset) > 240 || str_contains($asset, '/') || str_contains($asset, '\\'), 404);
        try {
            try {
                $record = $mart->inventoryDetail($asset);
            } catch (HttpExceptionInterface $error) {
                if ($error->getStatusCode() !== 404) {
                    throw $error;
                }
                // Preserve links from existing Registry-only workflows.
                $record = [...$mart->detail($asset), 'registered' => true];
            }
        } catch (Throwable $error) {
            if ($error instanceof HttpExceptionInterface && $error->getStatusCode() === 404) {
                throw $error;
            }
            $record = null;
        }

        $draftMapping = $record ? $mapping->forAsset($record) : null;
        $illustration = $record ? $illustrations->forAsset($record) : null;

        $disruptionSummary = $disruptions->summary($asset);
        $disruptionEvents = AssetDisruption::forAsset($asset)->where('status', 'recorded')->with(['members', 'author:id,name'])->orderByDesc('occurred_on')->orderByDesc('id')->limit(5)->get();

        return view('assets.show', compact('record', 'draftMapping', 'illustration', 'disruptionSummary', 'disruptionEvents', 'asset'));
    }
}
