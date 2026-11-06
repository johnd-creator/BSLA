<?php

namespace App\Http\Controllers;

use App\Models\InspectionDraft;
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
        $input = $request->validate(['asset_ref' => ['nullable', 'string', 'max:240']]);
        $inspection = new InspectionDraft(['asset_ref' => $input['asset_ref'] ?? null]);

        return view('inspections.form', compact('inspection'));
    }

    private function validated(Request $request, ReliabilityMart $mart, ?InspectionDraft $inspection = null): array
    {
        $data = $request->validate([
            'request_reference' => ['required', 'string', 'max:100'],
            'request_summary' => ['required', 'string', 'max:200'],
            'asset_ref' => ['nullable', 'string', 'max:240', 'not_regex:/[\\\\\/]/'],
            'method' => ['nullable', 'required_with:finding,recommendation', Rule::in(array_keys(InspectionDraft::METHODS))],
            'inspected_on' => ['nullable', 'required_with:finding,recommendation', 'date_format:Y-m-d', 'before_or_equal:today'],
            'finding' => ['nullable', 'required_with:recommendation', 'string', 'max:4000'],
            'recommendation' => ['nullable', 'string', 'max:4000'],
            'target_completion' => ['nullable', 'date_format:Y-m-d'],
            'wo_reference' => ['nullable', 'string', 'max:100'],
            'version' => [$inspection ? 'required' : 'nullable', 'integer', 'min:1'],
        ]);
        if (! empty($data['asset_ref']) && $data['asset_ref'] !== $inspection?->asset_ref) {
            try {
                $mart->detail($data['asset_ref']);
            } catch (Throwable) {
                throw ValidationException::withMessages(['asset_ref' => 'Referensi Asset belum dapat diverifikasi di Mart. Pilih dari Master Asset, atau simpan draft tanpa Asset terlebih dahulu.']);
            }
        }

        return $data;
    }

    public function store(Request $request, ReliabilityMart $mart)
    {
        Gate::authorize('write-inspection-drafts');
        $data = $this->validated($request, $mart);
        $inspection = new InspectionDraft($data);
        $inspection->created_by = $request->user()->id;
        $inspection->save();

        return redirect()->route('inspections.show', $inspection)->with('status', 'Draft permintaan/hasil inspeksi tersimpan secara lokal. Belum dikirim atau disetujui.');
    }

    public function show(InspectionDraft $inspection)
    {
        $inspection->load('author:id,name');

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
