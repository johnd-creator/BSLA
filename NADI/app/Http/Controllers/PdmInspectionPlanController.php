<?php

namespace App\Http\Controllers;

use App\Models\PdmInspectionPlan;
use App\Services\PdmFormCatalog;
use App\Services\PdmSchedule;
use App\Services\PdmTrend;
use App\Services\ReliabilityMart;
use Illuminate\Database\UniqueConstraintViolationException;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Gate;
use Illuminate\Support\Str;
use Illuminate\Validation\Rule;
use Illuminate\Validation\ValidationException;
use Throwable;

class PdmInspectionPlanController extends Controller
{
    public function index(Request $request, PdmSchedule $schedule)
    {
        $filters = $request->validate([
            'asset_ref' => ['nullable', 'string', 'max:240'],
            'method' => ['nullable', Rule::in(array_keys(PdmFormCatalog::METHODS))],
            'status' => ['nullable', Rule::in(array_keys(PdmInspectionPlan::STATUSES))],
            'page' => ['nullable', 'integer', 'between:1,100000'],
        ]);
        $query = PdmInspectionPlan::query()->with('author:id,name');
        foreach (['asset_ref', 'method', 'status'] as $key) {
            if (! empty($filters[$key])) {
                $query->where($key, $filters[$key]);
            }
        }
        $plans = $query->orderBy('first_due_on')->orderBy('id')->paginate(20)->withQueryString();
        $coverage = $plans->getCollection()->mapWithKeys(fn ($plan) => [$plan->id => $schedule->coverage($plan)]);

        return view('pdm.plans.index', compact('plans', 'coverage'));
    }

    public function create(Request $request, ReliabilityMart $mart, PdmFormCatalog $catalog)
    {
        Gate::authorize('write-pdm-activities');
        $data = $request->validate([
            'asset_ref' => ['nullable', 'string', 'max:240', 'not_regex:/[\\\\\/]/'],
            'template_id' => ['nullable', 'string', 'max:100'],
            'q' => ['nullable', 'string', 'max:120'],
            'offset' => ['nullable', 'integer', 'between:0,1000000'],
        ]);
        $asset = $page = null;
        $unavailable = false;
        try {
            if (! empty($data['asset_ref'])) {
                $asset = $mart->historyAsset($data['asset_ref']);
            } else {
                $page = $mart->inventory(['q' => $data['q'] ?? '', 'offset' => (int) ($data['offset'] ?? 0)]);
            }
        } catch (Throwable) {
            $unavailable = true;
        }
        $template = ! empty($data['template_id']) ? $catalog->find($data['template_id']) : null;
        $recovering = $unavailable && $request->old('asset_ref') === ($data['asset_ref'] ?? null)
            && $template && $request->old('template_id') === $template['id'];
        if (($asset || $recovering) && $template) {
            abort_if(($template['preview_only'] ?? true) || ! count($template['fields']), 422, 'Template ini masih perlu review.');

            return view('pdm.plans.form', ['plan' => new PdmInspectionPlan(['asset_ref' => $data['asset_ref'], 'template_id' => $template['id'], 'status' => 'active']),
                'template' => $template, 'fingerprint' => $catalog->fingerprint($template), 'requestKey' => (string) Str::uuid(), 'unavailable' => $unavailable]);
        }
        $templates = $asset ? array_values(array_filter($catalog->all(), function ($item) use ($data, $asset) {
            if (($item['preview_only'] ?? true) || ! count($item['fields'])) {
                return false;
            }

            return empty($data['q']) ? in_array($asset['canonical_id'], array_column($item['candidates'], 'canonical_id'), true)
                : Str::contains(mb_strtolower(json_encode([$item['title'], $item['source']], JSON_UNESCAPED_UNICODE)), mb_strtolower($data['q']));
        })) : [];

        return view('pdm.plans.choose', compact('asset', 'page', 'unavailable', 'templates'));
    }

    public function store(Request $request, ReliabilityMart $mart, PdmFormCatalog $catalog)
    {
        Gate::authorize('write-pdm-activities');
        $key = $request->validate(['request_key' => ['required', 'uuid']])['request_key'];
        if ($existing = PdmInspectionPlan::where('request_key', $key)->first()) {
            abort_unless($existing->created_by === $request->user()->id, 409);

            return redirect()->route('pdm.plans.show', $existing)->with('status', 'Rencana ini sudah tersimpan.');
        }
        $data = $request->validate([
            ...$this->scheduleRules(),
            'asset_ref' => ['required', 'string', 'max:240', 'not_regex:/[\\\\\/]/'],
            'template_id' => ['required', 'string', 'max:100'],
            'template_fingerprint' => ['required', 'string', 'size:64'],
            'point_key' => ['required', 'string', 'max:100'],
            'unit' => ['nullable', 'string', 'max:40'],
            'instrument' => ['required', 'string', 'max:200'],
            'measurement_mode' => ['required', 'string', 'max:200'],
            'operating_condition' => ['required', 'string', 'max:200'],
            'asset_selection_note' => ['required', 'string', 'min:10', 'max:2000'],
            'acknowledge_draft' => ['accepted'],
        ]);
        $template = $catalog->find($data['template_id']);
        $fingerprint = $catalog->fingerprint($template);
        if (($template['preview_only'] ?? true) || ! hash_equals($fingerprint, $data['template_fingerprint'])) {
            throw ValidationException::withMessages(['template_id' => 'Template berubah atau perlu review. Buka ulang pilihan template.']);
        }
        $field = collect($template['fields'])->firstWhere('key', $data['point_key']);
        if (! $field) {
            throw ValidationException::withMessages(['point_key' => 'Pilih titik yang tercantum pada template.']);
        }
        if (! empty($field['unit']) && ! empty($data['unit']) && $data['unit'] !== $field['unit']) {
            throw ValidationException::withMessages(['unit' => 'Satuan harus sama dengan satuan titik sumber.']);
        }
        $data['unit'] = $field['unit'] ?: ($data['unit'] ?? null);
        if ($field['type'] === 'number' && ! $data['unit']) {
            throw ValidationException::withMessages(['unit' => 'Satuan numerik yang belum diketahui harus ditentukan secara eksplisit.']);
        }
        try {
            $mart->historyAsset($data['asset_ref']);
        } catch (Throwable) {
            throw ValidationException::withMessages(['asset_ref' => 'Identitas aset belum dapat diverifikasi. Isian tetap ada; coba kembali setelah Mart tersedia.']);
        }
        unset($data['acknowledge_draft']);
        $data['method'] = $template['method'];
        $data['template_snapshot'] = $catalog->snapshot($template);
        $data['status'] = 'active';
        $identity = array_intersect_key($data, array_flip(['asset_ref', 'template_id', 'template_fingerprint', 'point_key', 'unit', ...PdmTrend::CONTEXT]));
        ksort($identity);
        $data['identity_key'] = hash('sha256', json_encode($identity, JSON_THROW_ON_ERROR));
        try {
            $plan = DB::transaction(function () use ($data, $key, $request) {
                if (PdmInspectionPlan::where('identity_key', $data['identity_key'])->exists()) {
                    throw ValidationException::withMessages(['point_key' => 'Rencana dengan identitas titik dan konteks yang sama sudah ada. Perbarui rencana tersebut, jangan menggandakan cakupan.']);
                }
                $plan = PdmInspectionPlan::firstOrCreate(['request_key' => $key], [...$data, 'created_by' => $request->user()->id]);
                abort_unless($plan->created_by === $request->user()->id, 409);
                if ($plan->wasRecentlyCreated) {
                    $this->record($plan->refresh(), $request->user()->id, 'Rencana dibuat.');
                }

                return $plan;
            });
        } catch (UniqueConstraintViolationException) {
            throw ValidationException::withMessages(['point_key' => 'Rencana sudah tersimpan oleh kiriman lain. Periksa daftar sebelum mengulang.']);
        }

        return redirect()->route('pdm.plans.show', $plan)->with('status', 'Rencana inspeksi lokal tersimpan. Tidak ada notifikasi atau pengukuran otomatis.');
    }

    public function show(PdmInspectionPlan $plan, PdmSchedule $schedule)
    {
        return view('pdm.plans.show', ['plan' => $plan->load('author:id,name'), 'coverage' => $schedule->coverage($plan),
            'revisions' => $plan->revisions()->with('actor:id,name')->orderByDesc('version')->simplePaginate(10)]);
    }

    public function edit(PdmInspectionPlan $plan)
    {
        $this->authorizeOwner($plan);

        return view('pdm.plans.form', ['plan' => $plan, 'template' => $plan->template_snapshot,
            'fingerprint' => $plan->template_fingerprint, 'requestKey' => null, 'unavailable' => false]);
    }

    public function update(Request $request, PdmInspectionPlan $plan)
    {
        $this->authorizeOwner($plan);
        $data = $request->validate([...$this->scheduleRules(), 'status' => ['required', Rule::in(array_keys(PdmInspectionPlan::STATUSES))],
            'version' => ['required', 'integer', 'min:1'], 'change_reason' => ['required', 'string', 'min:5', 'max:2000']]);
        DB::transaction(function () use ($plan, $request, $data) {
            $current = PdmInspectionPlan::whereKey($plan->id)->lockForUpdate()->firstOrFail();
            if ($current->version !== (int) $data['version']) {
                throw ValidationException::withMessages(['version' => 'Rencana sudah berubah. Muat ulang agar perubahan sebelumnya tidak tertimpa.']);
            }
            $current->fill(array_diff_key($data, array_flip(['version', 'change_reason'])));
            $current->version++;
            $current->save();
            $this->record($current, $request->user()->id, $data['change_reason']);
        });

        return redirect()->route('pdm.plans.show', $plan)->with('status', 'Rencana diperbarui dan revisi tersimpan.');
    }

    private function scheduleRules(): array
    {
        return ['title' => ['required', 'string', 'max:200'], 'frequency_value' => ['required', 'integer', 'between:1,365'],
            'frequency_unit' => ['required', Rule::in(array_keys(PdmInspectionPlan::FREQUENCIES))],
            'first_due_on' => ['required', 'date_format:Y-m-d', 'after_or_equal:1900-01-01', 'before_or_equal:2100-12-31'],
            'notes' => ['nullable', 'string', 'max:4000']];
    }

    private function authorizeOwner(PdmInspectionPlan $plan): void
    {
        Gate::authorize('write-pdm-activities');
        abort_unless($plan->created_by === auth()->id(), 403);
    }

    private function record(PdmInspectionPlan $plan, int $actor, string $reason): void
    {
        $plan->revisions()->create(['actor_id' => $actor, 'version' => $plan->version, 'reason' => $reason,
            'snapshot' => $plan->only(['title', 'asset_ref', 'template_id', 'template_fingerprint', 'point_key', 'unit', ...PdmTrend::CONTEXT,
                'frequency_value', 'frequency_unit', 'first_due_on', 'status', 'notes']), 'created_at' => now()]);
    }
}
