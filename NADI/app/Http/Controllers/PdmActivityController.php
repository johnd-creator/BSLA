<?php

namespace App\Http\Controllers;

use App\Models\InspectionDraft;
use App\Models\PdmActivity;
use App\Services\PdmFormCatalog;
use App\Services\PdmLogbook;
use App\Services\ReliabilityMart;
use Carbon\CarbonImmutable;
use Illuminate\Http\Request;
use Illuminate\Pagination\LengthAwarePaginator;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Gate;
use Illuminate\Support\Str;
use Illuminate\Validation\Rule;
use Illuminate\Validation\ValidationException;
use Throwable;

class PdmActivityController extends Controller
{
    public function index(Request $request, PdmLogbook $logbook)
    {
        $filters = $request->validate([
            'q' => ['nullable', 'string', 'max:120'],
            'method' => ['nullable', Rule::in(array_keys(InspectionDraft::METHODS))],
            'inspection_type' => ['nullable', Rule::in(['routine', 'request'])],
            'stage' => ['nullable', Rule::in(['request', 'finding', 'recommendation'])],
        ]);

        return view('pdm.index', ['activities' => $logbook->paginate($filters)]);
    }

    public function templates(Request $request, PdmFormCatalog $catalog)
    {
        $filters = $request->validate(['q' => ['nullable', 'string', 'max:120'], 'method' => ['nullable', Rule::in(array_keys(PdmFormCatalog::METHODS))], 'page' => ['sometimes', 'integer', 'min:1', 'max:10000'], 'asset_ref' => ['nullable', 'string', 'max:240', 'not_regex:/[\\\\\/]/']]);
        $templates = array_values(array_filter($catalog->all(), function ($template) use ($filters) {
            return (empty($filters['method']) || $template['method'] === $filters['method'])
                && (empty($filters['q']) || Str::contains(mb_strtolower(json_encode([$template['title'], $template['source'], $template['candidates']], JSON_UNESCAPED_UNICODE)), mb_strtolower($filters['q'])));
        }));
        $page = (int) ($filters['page'] ?? 1);

        return view('pdm.templates', ['templates' => new LengthAwarePaginator(array_slice($templates, ($page - 1) * 20, 20), count($templates), 20, $page, ['path' => $request->url(), 'query' => $request->query()]), 'totalTemplates' => count($catalog->all())]);
    }

    public function create(Request $request, ReliabilityMart $mart, PdmFormCatalog $catalog)
    {
        Gate::authorize('write-pdm-activities');
        $filters = $request->validate(['q' => ['nullable', 'string', 'max:120'], 'offset' => ['sometimes', 'integer', 'min:0', 'max:1000000'], 'asset_ref' => ['nullable', 'string', 'max:240', 'not_regex:/[\\\\\/]/'], 'template_id' => ['nullable', 'string', 'max:100']]);
        $asset = null;
        $page = null;
        $unavailable = false;
        try {
            if (! empty($filters['asset_ref'])) {
                $asset = $mart->historyAsset($filters['asset_ref']);
            } else {
                $page = $mart->inventory(['q' => $filters['q'] ?? '', 'offset' => (int) ($filters['offset'] ?? 0)]);
            }
        } catch (Throwable) {
            $unavailable = true;
        }
        $template = ! empty($filters['template_id']) ? $catalog->find($filters['template_id']) : null;
        // Keep a rejected submission editable during a Mart outage. Do not replace
        // its identity with sample data; saving still requires a fresh Mart check.
        $recoveringInput = $unavailable && $template
            && $request->old('asset_ref') === ($filters['asset_ref'] ?? null)
            && $request->old('template_id') === $template['id']
            && $request->old('template_fingerprint') === $catalog->fingerprint($template);
        if (($asset || $recoveringInput) && $template && ! ($template['preview_only'] ?? true) && count($template['fields'])) {
            return view('pdm.form', ['activity' => new PdmActivity(['asset_ref' => $asset['canonical_id'] ?? $filters['asset_ref']]), 'asset' => $asset, 'template' => $template, 'fingerprint' => $catalog->fingerprint($template), 'requestKey' => (string) Str::uuid(), 'unavailable' => $unavailable]);
        }

        return view('pdm.choose', compact('asset', 'page', 'unavailable', 'template') + ['templates' => $asset ? $catalog->forAsset($asset['canonical_id']) : []]);
    }

    private function validated(Request $request, ReliabilityMart $mart, PdmFormCatalog $catalog, ?PdmActivity $activity = null): array
    {
        // Older clients that provide a datetime remain compatible. New forms default to a date.
        $request->merge(['time_precision' => $request->input('time_precision', $activity?->time_precision ?? ($request->filled('measured_local') ? 'datetime' : 'date'))]);
        $request->merge(['inspection_type' => $request->input('inspection_type', $activity?->inspection_type ?? 'routine')]);
        if ($activity?->inspection) {
            // Linked analysis keeps its request identity; the form shows these as read-only.
            $request->merge($activity->only(['inspection_type', 'requester_name', 'request_reference', 'request_summary']));
        }
        $data = $request->validate([
            'title' => ['required', 'string', 'max:200'],
            'inspection_type' => ['sometimes', 'required', Rule::in(['routine', 'request'])],
            'requester_name' => ['nullable', 'required_if:inspection_type,request', 'string', 'max:200'],
            'request_reference' => ['nullable', 'string', 'max:100'],
            'request_summary' => ['nullable', 'required_if:inspection_type,request', 'string', 'max:200'],
            'asset_ref' => ['required', 'string', 'max:240', 'not_regex:/[\\\\\/]/'],
            'template_id' => ['required', 'string', 'max:100'],
            'template_fingerprint' => ['required', 'string', 'size:64'],
            'time_precision' => ['required', Rule::in(['date', 'datetime'])],
            'measured_on' => ['exclude_unless:time_precision,date', 'required_if:time_precision,date', 'date_format:Y-m-d', 'before_or_equal:today'],
            'measured_local' => ['exclude_unless:time_precision,datetime', 'required_if:time_precision,datetime', 'date_format:Y-m-d\TH:i,Y-m-d\TH:i:s'],
            'timezone' => ['exclude_unless:time_precision,datetime', 'required_if:time_precision,datetime', Rule::in(['Asia/Jakarta', 'Asia/Makassar', 'Asia/Jayapura', 'UTC'])],
            'instrument' => ['required', 'string', 'max:200'],
            'measurement_mode' => ['required', 'string', 'max:200'],
            'operating_condition' => ['required', 'string', 'max:200'],
            'asset_selection_note' => ['required', 'string', 'min:10', 'max:2000'],
            'acknowledge_draft' => ['accepted'],
            'notes' => ['nullable', 'string', 'max:4000'],
            'readings' => ['required', 'array', 'max:200'],
            'readings.*' => ['array:value,unit'],
            'readings.*.value' => ['nullable', 'string', 'max:500'],
            'readings.*.unit' => ['nullable', 'string', 'max:40'],
            'version' => [$activity ? 'required' : 'nullable', 'integer', 'min:1'],
        ]);
        if ($activity && ($activity->asset_ref !== $data['asset_ref'] || $activity->template_id !== $data['template_id'])) {
            throw ValidationException::withMessages(['asset_ref' => 'Aset dan template draft ini tidak boleh diganti. Buat aktivitas terpisah agar riwayat tidak bercampur.']);
        }
        $template = $activity ? $activity->template_snapshot : $catalog->find($data['template_id']);
        $fingerprint = $activity ? $activity->template_fingerprint : $catalog->fingerprint($template);
        if (($template['preview_only'] ?? true) || count($template['fields']) === 0) {
            throw ValidationException::withMessages(['template_id' => 'Struktur sumber ini masih perlu review sebelum digunakan untuk input.']);
        }
        if (! hash_equals($fingerprint, $data['template_fingerprint'])) {
            throw ValidationException::withMessages(['template_id' => 'Template berubah. Buka ulang form untuk memeriksa titik dan satuan terbaru.']);
        }
        try {
            $mart->historyAsset($data['asset_ref']);
        } catch (Throwable) {
            throw ValidationException::withMessages(['asset_ref' => 'Identitas aset belum dapat diverifikasi melalui Mart. Isian tetap ada; coba lagi setelah koneksi tersedia.']);
        }
        $measuredAt = null;
        $timezone = null;
        $measuredOn = $data['measured_on'] ?? null;
        if ($data['time_precision'] === 'datetime') {
            $timezone = $data['timezone'];
            $format = strlen($data['measured_local']) === 19 ? '!Y-m-d\TH:i:s' : '!Y-m-d\TH:i';
            $local = CarbonImmutable::createFromFormat($format, $data['measured_local'], $timezone);
            $measuredAt = $local->utc();
            $measuredOn = $local->format('Y-m-d');
            if ($measuredAt->isFuture()) {
                throw ValidationException::withMessages(['measured_local' => 'Waktu pengukuran tidak boleh di masa depan. Periksa zona waktu.']);
            }
        }
        if ($activity?->inspection && ($data['time_precision'] !== $activity->time_precision
            || $measuredOn !== $activity->measurementDate()
            || $measuredAt?->format('Y-m-d H:i:s') !== $activity->measured_at?->format('Y-m-d H:i:s')
            || $timezone !== $activity->timezone)) {
            throw ValidationException::withMessages([$data['time_precision'] === 'date' ? 'measured_on' : 'measured_local' => 'Tanggal, waktu dan presisi sudah menjadi dasar analisis terkait. Gunakan aktivitas baru untuk pengukuran berbeda.']);
        }
        $fields = array_column($template['fields'], null, 'key');
        if (array_diff(array_keys($data['readings']), array_keys($fields))) {
            throw ValidationException::withMessages(['readings' => 'Ada parameter yang tidak termasuk dalam template ini.']);
        }
        $readings = [];
        $filled = 0;
        foreach ($fields as $key => $field) {
            $value = $data['readings'][$key]['value'] ?? null;
            $unit = $field['unit'] ?: ($data['readings'][$key]['unit'] ?? null);
            if ($value !== null && $value !== '') {
                $filled++;
                if ($field['type'] === 'number' && (! is_numeric($value) || ! is_finite((float) $value))) {
                    throw ValidationException::withMessages(["readings.$key.value" => $field['label'].': gunakan angka hingga (desimal titik), bukan NaN/Infinity.']);
                }
                if ($field['type'] === 'number' && empty($unit)) {
                    throw ValidationException::withMessages(["readings.$key.unit" => $field['label'].': satuan belum pasti di sumber. Isi satuan sesuai alat/laporan sebelum menyimpan nilai.']);
                }
                if ($field['unit'] && isset($data['readings'][$key]['unit']) && $data['readings'][$key]['unit'] !== $field['unit']) {
                    throw ValidationException::withMessages(["readings.$key.unit" => 'Satuan sumber tidak boleh diubah untuk titik '.$field['label'].'.']);
                }
            }
            $readings[$key] = ['value' => $value, 'unit' => $unit];
        }
        if (! $filled) {
            throw ValidationException::withMessages(['readings' => 'Isi minimal satu hasil pengukuran. Titik yang belum diukur tetap kosong, bukan nol.']);
        }

        return [
            ...array_intersect_key($data, array_flip(['title', 'asset_ref', 'timezone', 'instrument', 'measurement_mode', 'operating_condition', 'asset_selection_note', 'notes', 'inspection_type', 'requester_name', 'request_reference', 'request_summary'])),
            'template_id' => $template['id'], 'template_fingerprint' => $fingerprint, 'method' => $template['method'],
            'time_precision' => $data['time_precision'], 'measured_on' => $measuredOn, 'measured_at' => $measuredAt, 'timezone' => $timezone, 'template_snapshot' => $catalog->snapshot($template), 'readings' => $readings,
        ];
    }

    public function store(Request $request, ReliabilityMart $mart, PdmFormCatalog $catalog)
    {
        Gate::authorize('write-pdm-activities');
        $key = $request->validate(['request_key' => ['required', 'uuid']])['request_key'];
        // A repeated browser submission must not create another activity.
        $existing = PdmActivity::where('request_key', $key)->first();
        if ($existing) {
            abort_unless($existing->created_by === $request->user()->id, 409);

            return redirect()->route('pdm.show', $existing)->with('status', 'Form ini sudah tersimpan. Gunakan Edit draft untuk mengubahnya.');
        }
        $data = $this->validated($request, $mart, $catalog);
        $activity = PdmActivity::firstOrCreate(['request_key' => $key], [...$data, 'created_by' => $request->user()->id]);
        abort_unless($activity->created_by === $request->user()->id, 409);

        return redirect()->route('pdm.show', $activity)->with('status', 'Aktivitas PdM tersimpan sebagai draft lokal. Pemetaan aset, diagnosis dan alarm belum disahkan.');
    }

    public function show(PdmActivity $activity)
    {
        return view('pdm.show', ['activity' => $activity->load(['author:id,name', 'inspection'])]);
    }

    public function edit(PdmActivity $activity)
    {
        Gate::authorize('update-pdm-activity', $activity);

        return view('pdm.form', ['activity' => $activity, 'asset' => null, 'template' => $activity->template_snapshot, 'fingerprint' => $activity->template_fingerprint, 'requestKey' => null]);
    }

    public function update(Request $request, PdmActivity $activity, ReliabilityMart $mart, PdmFormCatalog $catalog)
    {
        Gate::authorize('update-pdm-activity', $activity);
        $data = $this->validated($request, $mart, $catalog, $activity);
        $updated = PdmActivity::whereKey($activity->id)->where('version', $request->integer('version'))->update([...$data, 'template_snapshot' => json_encode($data['template_snapshot'], JSON_THROW_ON_ERROR), 'readings' => json_encode($data['readings'], JSON_THROW_ON_ERROR), 'version' => DB::raw('version + 1')]);
        if (! $updated) {
            throw ValidationException::withMessages(['version' => 'Draft sudah berubah. Muat ulang sebelum menyimpan agar perubahan sebelumnya tidak tertimpa.']);
        }

        return redirect()->route('pdm.show', $activity)->with('status', 'Draft aktivitas PdM diperbarui.');
    }

    public function history(Request $request, PdmFormCatalog $catalog)
    {
        $filters = $request->validate(['asset_ref' => ['required', 'string', 'max:240', 'not_regex:/[\\\\\/]/'], 'template_id' => ['nullable', 'string', 'max:100'], 'point' => ['nullable', 'string', 'max:100', 'required_with:fingerprint'], 'fingerprint' => ['nullable', 'string', 'size:64', 'required_with:point']]);
        $query = PdmActivity::where('asset_ref', $filters['asset_ref'])->newestMeasurement();
        if (! empty($filters['template_id'])) {
            $query->where('template_id', $filters['template_id']);
        }

        if (! empty($filters['point'])) {
            $query->where('template_fingerprint', $filters['fingerprint']);
        }

        return view('pdm.history', ['activities' => $query->paginate(30)->withQueryString(), 'assetRef' => $filters['asset_ref'], 'point' => $filters['point'] ?? null]);
    }
}
