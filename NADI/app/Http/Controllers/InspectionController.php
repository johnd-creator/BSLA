<?php

namespace App\Http\Controllers;

use App\Models\InspectionDraft;
use App\Models\PdmActivity;
use App\Services\ReliabilityMart;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Gate;
use Illuminate\Validation\Rule;
use Illuminate\Validation\ValidationException;
use Throwable;

class InspectionController extends Controller
{
    public function index(Request $request)
    {
        $filters = $request->validate(['q' => ['nullable', 'string', 'max:100'], 'stage' => ['nullable', Rule::in(['request', 'finding', 'recommendation'])]]);
        $query = InspectionDraft::query()->with('author:id,name')->orderByDesc('id');
        if (! empty($filters['q'])) {
            $term = '%'.$filters['q'].'%';
            $query->where(fn ($q) => $q->where('request_reference', 'like', $term)->orWhere('request_summary', 'like', $term)->orWhere('finding', 'like', $term)->orWhere('recommendation', 'like', $term));
        }
        match ($filters['stage'] ?? '') {
            'request' => $query->whereNull('finding')->whereNull('recommendation'),
            'finding' => $query->whereNotNull('finding')->whereNull('recommendation'),
            'recommendation' => $query->whereNotNull('recommendation'),
            default => null,
        };
        $counts = [
            'total' => InspectionDraft::count(),
            'request' => InspectionDraft::whereNull('finding')->whereNull('recommendation')->count(),
            'finding' => InspectionDraft::whereNotNull('finding')->whereNull('recommendation')->count(),
            'recommendation' => InspectionDraft::whereNotNull('recommendation')->count(),
        ];

        return view('inspections.index', ['drafts' => $query->paginate(20)->withQueryString(), 'counts' => $counts]);
    }

    public function create(Request $request)
    {
        Gate::authorize('write-inspection-drafts');
        $input = $request->validate(['asset_ref' => ['nullable', 'string', 'max:240'], 'pdm_activity_id' => ['nullable', 'integer', 'min:1']]);
        $activity = ! empty($input['pdm_activity_id']) ? PdmActivity::findOrFail($input['pdm_activity_id']) : null;
        if ($activity) {
            Gate::authorize('update-pdm-activity', $activity);
            if (! $activity->inspection_type) {
                return redirect()->route('pdm.edit', $activity)->with('status', 'Catat dahulu jenis inspeksi rutin atau request pada aktivitas lama ini.');
            }
            if ($activity->inspection) {
                return redirect()->route('inspections.edit', $activity->inspection);
            }
        }
        $inspection = new InspectionDraft($activity ? $this->activityContext($activity) : ['asset_ref' => $input['asset_ref'] ?? null, 'inspection_type' => 'request']);
        if ($activity) {
            $inspection->pdm_activity_id = $activity->id;
            $inspection->setRelation('pdmActivity', $activity);
        }

        return view('inspections.form', compact('inspection'));
    }

    private function activityContext(PdmActivity $activity): array
    {
        return [
            'asset_ref' => $activity->asset_ref, 'method' => $activity->method,
            'inspected_on' => $activity->measurementDate(),
            'inspection_type' => $activity->inspection_type,
            'requester_name' => $activity->requester_name,
            'request_reference' => $activity->request_reference ?: $activity->reference(),
            'request_summary' => $activity->request_summary ?: $activity->title,
        ];
    }

    private function validated(Request $request, ReliabilityMart $mart, ?InspectionDraft $inspection = null): array
    {
        $link = $request->validate(['pdm_activity_id' => ['nullable', 'integer', 'min:1']]);
        $activity = $inspection?->pdmActivity;
        if (! $inspection && ! empty($link['pdm_activity_id'])) {
            $activity = PdmActivity::findOrFail($link['pdm_activity_id']);
            Gate::authorize('update-pdm-activity', $activity);
        }
        if ($inspection && ($link['pdm_activity_id'] ?? null) != $inspection->pdm_activity_id) {
            throw ValidationException::withMessages(['pdm_activity_id' => 'Hubungan aktivitas tidak boleh diganti.']);
        }
        if ($activity) {
            // Asset, date, method and request identity come from the stored measurement.
            $request->merge($this->activityContext($activity));
        }
        $request->merge(['inspection_type' => $request->input('inspection_type', $inspection?->inspection_type ?? 'request'), 'follow_up_status' => $request->input('follow_up_status', $inspection?->follow_up_status ?? 'open')]);
        $data = $request->validate([
            'inspection_type' => ['required', Rule::in(['routine', 'request'])],
            'requester_name' => ['nullable', 'required_if:inspection_type,request', 'string', 'max:200'],
            'follow_up_status' => ['sometimes', 'required', Rule::in(array_keys(InspectionDraft::FOLLOW_UP_STATUSES))],
            'pdm_activity_id' => ['nullable', 'integer'],
            'request_reference' => ['required', 'string', 'max:100'],
            'request_summary' => ['required', 'string', 'max:200'],
            'asset_ref' => ['nullable', 'required_with:recommendation', 'string', 'max:240', 'not_regex:/[\\\\\/]/'],
            'method' => ['nullable', 'required_with:finding,recommendation', Rule::in(array_keys(InspectionDraft::METHODS))],
            'inspected_on' => ['nullable', 'required_with:finding,recommendation', 'date_format:Y-m-d', ...($activity ? [] : ['before_or_equal:today'])],
            'finding' => ['nullable', 'required_with:recommendation', 'string', 'max:4000'],
            'recommendation' => ['nullable', 'string', 'max:4000'],
            'target_completion' => ['nullable', 'date_format:Y-m-d'],
            'wo_reference' => ['nullable', 'string', 'max:100'],
            'version' => [$inspection ? 'required' : 'nullable', 'integer', 'min:1'],
        ]);
        if (! empty($data['recommendation']) && ! empty($inspection?->recommendation) && $data['asset_ref'] !== $inspection->asset_ref) {
            throw ValidationException::withMessages(['asset_ref' => 'Aset rekomendasi yang sudah tersimpan tidak boleh diganti. Buat inspeksi baru untuk aset lain.']);
        }
        if (($data['follow_up_status'] ?? 'open') !== 'open' && empty($data['recommendation'])) {
            throw ValidationException::withMessages(['follow_up_status' => 'Catat rekomendasi sebelum mengubah status tindak lanjut.']);
        }
        if (! empty($data['asset_ref']) && (! empty($data['recommendation']) || $data['asset_ref'] !== $inspection?->asset_ref)) {
            try {
                $mart->historyAsset($data['asset_ref']);
            } catch (Throwable) {
                throw ValidationException::withMessages(['asset_ref' => 'Referensi Asset belum dapat diverifikasi di Mart. Pilih dari Master Asset, atau simpan draft tanpa Asset terlebih dahulu.']);
            }
        }

        $data['pdm_activity_id'] = $activity?->id;

        return $data;
    }

    public function store(Request $request, ReliabilityMart $mart)
    {
        Gate::authorize('write-inspection-drafts');
        $key = $request->validate(['request_key' => ['required', 'uuid']])['request_key'];
        if ($existing = InspectionDraft::where('request_key', $key)->first()) {
            abort_unless($existing->created_by === $request->user()->id, 409);

            return redirect()->route('inspections.show', $existing)->with('status', 'Form ini sudah tersimpan. Gunakan Lanjutkan draft untuk mengubahnya.');
        }
        $data = [...$this->validated($request, $mart), 'request_key' => $key];
        if (! empty($data['pdm_activity_id'])) {
            $inspection = InspectionDraft::firstOrCreate(['pdm_activity_id' => $data['pdm_activity_id']], [...$data, 'created_by' => $request->user()->id]);
            abort_unless($inspection->created_by === $request->user()->id, 409);
        } else {
            $inspection = InspectionDraft::firstOrCreate(['request_key' => $key], [...$data, 'created_by' => $request->user()->id]);
            abort_unless($inspection->created_by === $request->user()->id, 409);
        }

        return redirect()->route('inspections.show', $inspection)->with('status', 'Draft permintaan/hasil inspeksi tersimpan secara lokal. Belum dikirim atau disetujui.');
    }

    public function show(InspectionDraft $inspection)
    {
        $inspection->load(['author:id,name', 'pdmActivity']);

        return view('inspections.show', compact('inspection'));
    }

    public function edit(InspectionDraft $inspection)
    {
        Gate::authorize('update-inspection-draft', $inspection);

        return view('inspections.form', compact('inspection'));
    }

    public function update(Request $request, InspectionDraft $inspection, ReliabilityMart $mart)
    {
        Gate::authorize('update-inspection-draft', $inspection);
        $data = $this->validated($request, $mart, $inspection);
        DB::transaction(function () use ($data, $inspection) {
            $current = InspectionDraft::whereKey($inspection->id)->lockForUpdate()->firstOrFail();
            if ($current->version !== (int) $data['version']) {
                throw ValidationException::withMessages(['version' => 'Draft sudah berubah. Muat ulang sebelum menyimpan.']);
            }
            $current->fill($data);
            $current->version++;
            $current->save();
        });

        return redirect()->route('inspections.show', $inspection)->with('status', 'Draft diperbarui. Rekomendasi belum dikirim atau disetujui.');
    }
}
