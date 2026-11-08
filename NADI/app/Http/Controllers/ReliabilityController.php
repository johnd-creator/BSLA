<?php

namespace App\Http\Controllers;

use App\Models\AssetDisruption;
use App\Models\ReliabilityReview;
use App\Models\ReliabilitySnapshot;
use App\Services\ReliabilityEvidence;
use App\Services\ReliabilityMart;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Gate;
use Illuminate\Support\Str;

class ReliabilityController extends Controller
{
    private function filters(Request $request): array
    {
        return $request->validate(['asset_ref' => ['nullable', 'string', 'max:240', 'starts_with:asset:MAXIMO:MXASSET:BSR:IP:', 'not_regex:/[\\\\\/]/'], 'year' => ['nullable', 'integer', 'between:1900,'.now('Asia/Jakarta')->year]]);
    }

    public function index(Request $request, ReliabilityEvidence $evidence, ReliabilityMart $mart)
    {
        $filters = $this->filters($request);
        $asset = $filters['asset_ref'] ?? null;
        $year = (int) ($filters['year'] ?? now('Asia/Jakarta')->year);

        return view('reliability.index', ['assetRef' => $asset, 'year' => $year, 'report' => $asset ? $evidence->report($asset, $year, $mart) : null,
            'snapshots' => $asset ? ReliabilitySnapshot::where('asset_ref', $asset)->where('year', $year)->latest('id')->paginate(10) : null,
            'localAssets' => AssetDisruption::query()->select('asset_ref')->distinct()->limit(100)->pluck('asset_ref'), 'requestKey' => (string) Str::uuid()]);
    }

    public function download(Request $request, ReliabilityEvidence $evidence, ReliabilityMart $mart)
    {
        $filters = $this->filters($request);
        abort_unless(! empty($filters['asset_ref']), 422);
        $report = $evidence->report($filters['asset_ref'], (int) ($filters['year'] ?? now('Asia/Jakarta')->year), $mart);

        return $this->jsonDownload($report, 'nadi-reliability-'.$report['period']['year'].'.json');
    }

    public function store(Request $request, ReliabilityEvidence $evidence, ReliabilityMart $mart)
    {
        Gate::authorize('write-asset-disruptions');
        $data = $request->validate(['request_key' => ['required', 'uuid']]);
        if ($existing = ReliabilitySnapshot::where('request_key', $data['request_key'])->first()) {
            abort_unless($existing->created_by === $request->user()->id, 409);

            return redirect()->route('reliability.snapshots.show', $existing);
        }
        $filters = $this->filters($request);
        abort_unless(! empty($filters['asset_ref']), 422);
        $report = $evidence->report($filters['asset_ref'], (int) ($filters['year'] ?? now('Asia/Jakarta')->year), $mart);
        abort_unless($report['asset'] !== null || $report['quality']['all_local_observations'] > 0, 422);
        $snapshot = ReliabilitySnapshot::create(['created_by' => $request->user()->id, 'request_key' => $data['request_key'], 'asset_ref' => $filters['asset_ref'], 'year' => $report['period']['year'], 'rule_version' => ReliabilityReview::RULE, 'evidence_hash' => $report['evidence_hash'], 'report' => $report, 'created_at' => now()]);

        return redirect()->route('reliability.snapshots.show', $snapshot)->with('status', 'Snapshot immutable tersimpan. Koreksi berikutnya tidak menimpa hasil ini.');
    }

    public function show(ReliabilitySnapshot $snapshot, ReliabilityEvidence $evidence, ReliabilityMart $mart)
    {
        $current = $evidence->report($snapshot->asset_ref, $snapshot->year, $mart);

        return view('reliability.snapshot', ['snapshot' => $snapshot, 'report' => $snapshot->report, 'changed' => ! hash_equals($snapshot->evidence_hash, $current['evidence_hash'])]);
    }

    public function snapshotDownload(ReliabilitySnapshot $snapshot)
    {
        return $this->jsonDownload($snapshot->report, 'nadi-reliability-snapshot-'.$snapshot->id.'.json');
    }

    private function jsonDownload(array $report, string $name)
    {
        return response(json_encode($report, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_THROW_ON_ERROR), 200, ['Content-Type' => 'application/json; charset=UTF-8', 'Content-Disposition' => 'attachment; filename="'.$name.'"', 'Cache-Control' => 'no-store, private', 'X-Content-Type-Options' => 'nosniff']);
    }
}
