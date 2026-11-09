<?php

namespace App\Http\Controllers;

use App\Models\OperatingLog;
use App\Models\OperatingLogRevision;
use App\Services\OperatingExposure;
use App\Services\ReliabilityMart;
use App\Services\ReliabilityTiming;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Gate;
use Illuminate\Support\Str;
use Illuminate\Validation\Rule;
use Illuminate\Validation\ValidationException;
use Throwable;

class OperatingLogController extends Controller
{
    public function index(Request $request, OperatingExposure $exposure)
    {
        $data = $this->scope($request);
        $asset = $data['asset_ref'];
        $year = (int) ($data['year'] ?? now('Asia/Jakarta')->year);

        return view('reliability.operating-index', ['assetRef' => $asset, 'year' => $year, 'coverage' => $exposure->report($asset, $year),
            'logs' => OperatingLog::where('asset_ref', $asset)->with(['latestRevision', 'author:id,name'])->latest('id')->paginate(20)->withQueryString()]);
    }

    public function create(Request $request)
    {
        Gate::authorize('write-asset-disruptions');
        $data = $this->scope($request);

        return $this->form(new OperatingLog(['asset_ref' => $data['asset_ref']]));
    }

    public function edit(OperatingLog $operatingLog)
    {
        Gate::authorize('write-asset-disruptions');
        abort_unless($operatingLog->created_by === auth()->id(), 403);

        return $this->form($operatingLog);
    }

    private function form(OperatingLog $log)
    {
        return view('reliability.operating-form', ['log' => $log, 'latest' => $log->exists ? $log->latestRevision : null,
            'revisions' => $log->exists ? $log->revisions()->with('author:id,name')->latest('revision')->paginate(10) : collect(), 'requestKey' => (string) Str::uuid()]);
    }

    public function show(OperatingLog $operatingLog)
    {
        return view('reliability.operating-history', ['log' => $operatingLog, 'revisions' => $operatingLog->revisions()->with('author:id,name')->latest('revision')->paginate(10)]);
    }

    public function store(Request $request, ReliabilityTiming $timing, ReliabilityMart $mart)
    {
        return $this->save($request, null, $timing, $mart);
    }

    public function update(Request $request, OperatingLog $operatingLog, ReliabilityTiming $timing, ReliabilityMart $mart)
    {
        return $this->save($request, $operatingLog, $timing, $mart);
    }

    private function save(Request $request, ?OperatingLog $log, ReliabilityTiming $timing, ReliabilityMart $mart)
    {
        Gate::authorize('write-asset-disruptions');
        abort_if($log && $log->created_by !== $request->user()->id, 403);
        $key = $request->validate(['request_key' => ['required', 'uuid']])['request_key'];
        if ($saved = OperatingLogRevision::where('request_key', $key)->first()) {
            $savedLog = OperatingLog::findOrFail($saved->operating_log_id);
            abort_unless($saved->created_by === $request->user()->id && ($log ? $log->id === $savedLog->id : $request->input('asset_ref') === $savedLog->asset_ref), 409);

            return redirect()->route('reliability.operating.show', $savedLog);
        }
        $scope = $this->scope($request);
        abort_if($log && $log->asset_ref !== $scope['asset_ref'], 422);
        $data = $request->validate([
            'version' => ['required', 'integer', 'min:0'], 'started_at' => ['required', 'string', 'max:40'], 'ended_at' => ['required', 'string', 'max:40'],
            'state' => ['required', Rule::in(array_keys(OperatingLog::STATES))], 'review_state' => ['required', Rule::in(array_keys(OperatingLog::REVIEWS))],
            'source' => ['required', 'string', 'min:3', 'max:1000'], 'evidence' => ['required', 'string', 'min:5', 'max:4000'], 'reason' => ['required', 'string', 'min:5', 'max:2000'],
            'attestation' => ['accepted_if:review_state,verified'],
        ]);
        $start = $timing->instant($data['started_at'], 'started_at');
        $end = $timing->instant($data['ended_at'], 'ended_at');
        if ($end->lte($start)) {
            throw ValidationException::withMessages(['ended_at' => 'Akhir harus sesudah awal. Catat hanya interval selesai dengan batas tepat dari bukti.']);
        }
        if (! $log) {
            // Verify exact identity through the existing bounded GET-only Mart.
            // A source outage blocks only new identities, never local corrections.
            try {
                $mart->historyAsset($scope['asset_ref']);
            } catch (Throwable) {
                throw ValidationException::withMessages(['asset_ref' => 'Identitas aset belum dapat diverifikasi. Isian tetap ada; coba lagi setelah sumber tersedia.']);
            }
        }
        $saved = DB::transaction(function () use ($request, $log, $scope, $data, $key, $start, $end) {
            // Another request may finish after the optimistic replay check and
            // before the owning SQLite store grants this write transaction.
            if ($replay = OperatingLogRevision::where('request_key', $key)->first()) {
                $replayedLog = OperatingLog::findOrFail($replay->operating_log_id);
                abort_unless($replay->created_by === $request->user()->id && ($log ? $log->id === $replayedLog->id : $scope['asset_ref'] === $replayedLog->asset_ref), 409);

                return $replayedLog;
            }
            if ($log) {
                if (! OperatingLog::whereKey($log->id)->where('version', $data['version'])->update(['version' => DB::raw('version + 1'), 'updated_at' => now()])) {
                    throw ValidationException::withMessages(['version' => 'Log berubah. Buka ulang sebelum membuat koreksi.']);
                }
                $log = $log->fresh();
            } else {
                if ((int) $data['version'] !== 0 || $data['review_state'] === 'voided') {
                    throw ValidationException::withMessages(['version' => 'Log baru mulai versi 0 dan tidak dapat langsung dibatalkan.']);
                }
                $log = OperatingLog::create(['asset_ref' => $scope['asset_ref'], 'created_by' => $request->user()->id, 'version' => 1]);
            }
            $log->revisions()->create(['revision' => $log->version, 'created_by' => $request->user()->id, 'request_key' => $key,
                'started_at' => $start, 'ended_at' => $end, 'state' => $data['state'], 'review_state' => $data['review_state'],
                'source' => $data['source'], 'evidence' => $data['evidence'], 'reason' => $data['reason'], 'created_at' => now()]);

            return $log;
        });

        return redirect()->route('reliability.operating.show', $saved)->with('status', 'Revisi log operasi tersimpan. Tidak mengklasifikasikan failure atau mengesahkan KPI organisasi.');
    }

    private function scope(Request $request): array
    {
        return $request->validate(['asset_ref' => ['required', 'string', 'max:240', 'starts_with:asset:MAXIMO:MXASSET:BSR:IP:', 'not_regex:/[\\\\\/]/'], 'year' => ['nullable', 'integer', 'between:1900,'.now('Asia/Jakarta')->year]]);
    }
}
