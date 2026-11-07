<?php

namespace App\Http\Controllers;

use App\Models\AssetDisruption;
use App\Models\AssetPriority;
use App\Models\InspectionDraft;
use App\Services\ReliabilityMart;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Gate;
use Illuminate\Support\Str;
use Illuminate\Validation\Rule;
use Illuminate\Validation\ValidationException;
use Throwable;

class AssetPriorityController extends Controller
{
    public function create(Request $request, ReliabilityMart $mart)
    {
        Gate::authorize('write-asset-priorities');
        $filters = $request->validate(['asset_ref' => ['nullable', 'string', 'max:240', 'not_regex:/[\\\\\/]/'], 'q' => ['nullable', 'string', 'max:120'], 'offset' => ['nullable', 'integer', 'between:0,1000000']]);
        $assetRef = $filters['asset_ref'] ?? null;
        if ($assetRef && ($existing = AssetPriority::where('asset_ref', $assetRef)->first())) {
            return redirect()->route('priorities.show', $existing)->with('status', 'Aset ini sudah memiliki penilaian. Perbarui catatan yang sama agar tidak ganda.');
        }
        $asset = $page = null;
        $unavailable = false;
        try {
            if ($assetRef) {
                $asset = $mart->historyAsset($assetRef);
            } else {
                $page = $mart->inventory(['q' => $filters['q'] ?? '', 'offset' => (int) ($filters['offset'] ?? 0)]);
            }
        } catch (Throwable) {
            $unavailable = true;
        }
        if ($assetRef) {
            return $this->form(new AssetPriority(['asset_ref' => $assetRef]), $asset, $unavailable);
        }

        return view('priorities.choose', compact('page', 'unavailable'));
    }

    private function form(AssetPriority $priority, ?array $asset = null, bool $unavailable = false)
    {
        $disruptions = AssetDisruption::forAsset($priority->asset_ref)->orderByDesc('id')->limit(20)->get();
        $inspections = InspectionDraft::where('asset_ref', $priority->asset_ref)->orderByDesc('id')->limit(20)->get();
        if ($priority->disruption && ! $disruptions->contains('id', $priority->disruption_id)) {
            $disruptions->push($priority->disruption);
        }
        if ($priority->inspection && ! $inspections->contains('id', $priority->inspection_id)) {
            $inspections->push($priority->inspection);
        }

        return view('priorities.form', compact('priority', 'asset', 'unavailable', 'disruptions', 'inspections') + ['requestKey' => (string) Str::uuid()]);
    }

    private function validated(Request $request, ReliabilityMart $mart, ?AssetPriority $priority = null): array
    {
        $data = $request->validate([
            'asset_ref' => ['required', 'string', 'max:240', 'not_regex:/[\\\\\/]/'],
            'urgency' => ['required', Rule::in(array_keys(AssetPriority::URGENCIES))],
            'observed_condition' => ['required', 'string', 'max:4000'],
            'impact' => ['required', 'string', 'max:2000'],
            'reasoning' => ['required', 'string', 'max:4000'],
            'evidence_note' => ['required', 'string', 'max:4000'],
            'owner' => ['required', 'string', 'max:120'],
            'due_on' => ['nullable', 'required_without:review_on', 'date_format:Y-m-d'],
            'review_on' => ['nullable', 'required_without:due_on', 'date_format:Y-m-d'],
            'disruption_id' => ['nullable', 'integer', 'min:1'],
            'inspection_id' => ['nullable', 'integer', 'min:1'],
            'work_order_ref' => ['nullable', 'string', 'max:200', 'starts_with:workorder:MAXIMO:MXWODETAIL:BSR:IP:'],
            'version' => [$priority ? 'required' : 'nullable', 'integer', 'min:1'],
            'status' => [$priority ? 'required' : 'nullable', Rule::in(array_keys(AssetPriority::STATUSES))],
            'change_reason' => [$priority ? 'required' : 'nullable', 'string', 'min:5', 'max:2000'],
        ]);
        if ($priority && $priority->asset_ref !== $data['asset_ref']) {
            throw ValidationException::withMessages(['asset_ref' => 'Identitas aset tidak dapat diganti.']);
        }
        // Existing local judgments remain editable when the read-only source is down.
        $asset = null;
        $verifyWorkOrder = ! empty($data['work_order_ref']) && (! $priority || $data['work_order_ref'] !== $priority->work_order_ref);
        if (! $priority || $verifyWorkOrder) {
            try {
                $asset = $mart->historyAsset($data['asset_ref']);
            } catch (Throwable) {
                throw ValidationException::withMessages(['asset_ref' => 'Identitas aset belum dapat diverifikasi. Isian dipertahankan; coba kembali setelah sumber tersedia.']);
            }
        }
        if (! empty($data['disruption_id']) && ! AssetDisruption::forAsset($data['asset_ref'])->whereKey($data['disruption_id'])->exists()) {
            throw ValidationException::withMessages(['disruption_id' => 'Catatan gangguan harus terkait dengan aset yang sama.']);
        }
        if (! empty($data['inspection_id']) && ! InspectionDraft::where('asset_ref', $data['asset_ref'])->whereKey($data['inspection_id'])->exists()) {
            throw ValidationException::withMessages(['inspection_id' => 'Inspeksi harus terkait dengan aset yang sama.']);
        }
        if ($verifyWorkOrder) {
            try {
                $mart->workOrder($data['work_order_ref'], null, $data['asset_ref'], ! $asset['registered']);
            } catch (Throwable) {
                throw ValidationException::withMessages(['work_order_ref' => 'WO belum dapat dicocokkan dengan aset ini. Gunakan Canonical ID WO dari detail WO.']);
            }
        }

        return collect($data)->except(['version', 'change_reason'])->all() + ['status' => 'active'];
    }

    public function store(Request $request, ReliabilityMart $mart)
    {
        Gate::authorize('write-asset-priorities');
        $key = $request->validate(['request_key' => ['required', 'uuid']])['request_key'];
        if ($existing = AssetPriority::where('request_key', $key)->first()) {
            abort_unless($existing->created_by === $request->user()->id, 409);

            return redirect()->route('priorities.show', $existing);
        }
        $data = $this->validated($request, $mart);
        $data['status'] = 'active';
        $priority = DB::transaction(function () use ($request, $key, $data) {
            $priority = AssetPriority::firstOrCreate(['asset_ref' => $data['asset_ref']], [...$data, 'request_key' => $key, 'created_by' => $request->user()->id]);
            if ($priority->wasRecentlyCreated) {
                $this->revision($priority->fresh(), $request->user()->id, 'Penilaian awal');
            }

            return $priority;
        });

        return redirect()->route('priorities.show', $priority)->with('status', 'Satu penilaian per aset. Penilaian engineer tersimpan, bukan skor risiko otomatis.');
    }

    public function show(AssetPriority $priority)
    {
        $input = request()->validate(['revision' => ['nullable', 'integer', 'min:1'], 'page' => ['nullable', 'integer', 'between:1,1000']]);

        return view('priorities.show', ['priority' => $priority->load(['author:id,name', 'disruption', 'inspection']), 'revisions' => $priority->revisions()->with('author:id,name')->when(! empty($input['revision']), fn ($q) => $q->where('version', $input['revision']))->paginate(10)->withQueryString()]);
    }

    public function edit(AssetPriority $priority)
    {
        Gate::authorize('update-asset-priority', $priority);

        return $this->form($priority);
    }

    public function update(Request $request, AssetPriority $priority, ReliabilityMart $mart)
    {
        Gate::authorize('update-asset-priority', $priority);
        $data = $this->validated($request, $mart, $priority);
        DB::transaction(function () use ($request, $priority, $data) {
            $updated = AssetPriority::whereKey($priority->id)->where('version', $request->integer('version'))->update([...$data, 'version' => DB::raw('version + 1')]);
            if (! $updated) {
                throw ValidationException::withMessages(['version' => 'Penilaian sudah berubah. Buka ulang form agar versi sebelumnya tidak tertimpa.']);
            }
            $this->revision($priority->fresh(), $request->user()->id, $request->string('change_reason')->toString());
        });

        return redirect()->route('priorities.show', $priority)->with('status', 'Penilaian diperbarui. Semua versi sebelumnya tetap tersimpan.');
    }

    private function revision(AssetPriority $priority, int $author, string $reason): void
    {
        $priority->revisions()->create(['version' => $priority->version, 'changed_by' => $author, 'reason' => $reason, 'snapshot' => $priority->snapshot(), 'created_at' => now()]);
    }
}
