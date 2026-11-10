<?php

namespace App\Http\Controllers;

use App\Models\AssetWellnessPolicy;
use App\Models\PdmActivity;
use App\Services\AssetWellness;
use App\Services\AssetWellnessMethod;
use App\Services\PdmTrend;
use App\Services\ReliabilityMart;
use App\Services\ReliabilityPeriod;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Gate;
use Illuminate\Support\Str;
use Illuminate\Validation\ValidationException;
use Throwable;

class AssetWellnessPolicyController extends Controller
{
    public function index(Request $request, AssetWellnessMethod $method)
    {
        $scope = $this->scope($request);
        $period = ReliabilityPeriod::fromRequest($request);
        $navigation = ['asset_ref' => $scope['asset_ref'], ...$period->query()];
        $report = $method->report($scope['asset_ref'], $period);
        $latest = $report['policy'];
        $anchors = PdmActivity::where('asset_ref', $scope['asset_ref'])->whereBetween('measured_on', [$period->start->toDateString(), $period->end->subDay()->toDateString()])->newestMeasurement()->limit(100)->get();

        return $this->view($scope, $period, $report, $latest, $anchors);
    }

    private function view(array $scope, ReliabilityPeriod $period, array $report, ?AssetWellnessPolicy $latest, $anchors)
    {
        $ids = collect($latest?->rules['pdm_rules'] ?? [])->pluck('anchor_id')->all();
        $anchors = $anchors->merge(PdmActivity::where('asset_ref', $scope['asset_ref'])->whereIn('id', $ids)->get())->unique('id');
        $policies = $report['storage_ready'] ? $period->constrain(AssetWellnessPolicy::where('asset_ref', $scope['asset_ref']))->with('author:id,name')->latest('revision')->paginate(10)->appends(['asset_ref' => $scope['asset_ref'], ...$period->query()]) : null;

        return response()->view('wellness.policy', ['assetRef' => $scope['asset_ref'], 'year' => $scope['year'], 'period' => $period, 'report' => $report,
            'latest' => $latest, 'anchors' => $anchors, 'policies' => $policies, 'requestKey' => (string) Str::uuid()])->header('Cache-Control', 'no-store, private');
    }

    public function store(Request $request, ReliabilityMart $mart)
    {
        Gate::authorize('write-wellness-policies');
        $scope = $this->scope($request);
        $period = ReliabilityPeriod::fromRequest($request);
        $navigation = ['asset_ref' => $scope['asset_ref'], ...$period->query()];
        if (! $period->storageReady('asset_wellness_policies')) {
            throw ValidationException::withMessages(['previous_revision' => 'Penyimpanan pengaturan belum diaktifkan. Draft tidak tersimpan; isian dipertahankan.']);
        }
        $key = $request->validate(['request_key' => ['required', 'uuid']])['request_key'];
        if ($saved = AssetWellnessPolicy::where('request_key', $key)->first()) {
            abort_unless($saved->created_by === $request->user()->id && $saved->asset_ref === $scope['asset_ref'] && $period->matchesRecord($saved), 409);

            return redirect()->route('wellness.policy', $navigation)->with('status', 'Form ini sudah tersimpan. Tidak dibuat revisi ganda.');
        }
        $latest = $period->constrain(AssetWellnessPolicy::where('asset_ref', $scope['asset_ref']))->latest('revision')->first();
        abort_if($latest && $latest->created_by !== $request->user()->id, 403);
        $data = $request->validate([
            'previous_revision' => ['required', 'integer', 'min:0'],
            'criticality_label' => ['nullable', 'string', 'max:80'],
            'criticality_basis' => ['nullable', 'required_with:criticality_label', 'string', 'min:5', 'max:2000'],
            'components' => ['required', 'array:pdm,operations,failure,maintenance'],
            'components.*' => ['array:max_age_days,required_evidence,weight,normalization'],
            'components.*.weight' => ['nullable', 'numeric', 'between:0,100'],
            'components.*.normalization' => ['nullable', 'string', 'max:2000'],
            'components.*.max_age_days' => ['nullable', 'integer', 'between:0,36500'],
            'components.*.required_evidence' => ['nullable', 'string', 'max:2000'],
            'pdm_rules' => ['nullable', 'array', 'max:10'],
            'pdm_rules.*' => ['array:anchor_id,point,lower,upper,max_age_days,requirement,remove'],
            'pdm_rules.*.remove' => ['nullable', 'boolean'],
            'pdm_rules.*.anchor_id' => ['nullable', 'integer', 'min:1'],
            'pdm_rules.*.point' => ['nullable', 'string', 'max:100'],
            'pdm_rules.*.lower' => ['nullable', 'numeric'],
            'pdm_rules.*.upper' => ['nullable', 'numeric'],
            'pdm_rules.*.max_age_days' => ['nullable', 'integer', 'between:0,36500'],
            'pdm_rules.*.requirement' => ['nullable', 'string', 'max:2000'],
            'anchor_fingerprints' => ['nullable', 'array', 'max:110'],
            'anchor_fingerprints.*' => ['string', 'size:64'],
            'evidence' => ['required', 'string', 'min:5', 'max:4000'],
            'reason' => ['required', 'string', 'min:5', 'max:2000'],
            'acknowledge_draft' => ['accepted'],
            'status' => ['prohibited'], 'score' => ['prohibited'], 'approved_by' => ['prohibited'],
        ]);
        foreach (array_keys(AssetWellness::COMPONENTS) as $component) {
            if (! array_key_exists($component, $data['components'])) {
                throw ValidationException::withMessages(['components' => 'Empat komponen wajib tetap terlihat. Keputusan boleh kosong.']);
            }
        }
        if (! $latest) {
            try {
                $mart->historyAsset($scope['asset_ref']);
            } catch (Throwable) {
                throw ValidationException::withMessages(['asset_ref' => 'Identitas aset belum dapat diverifikasi. Isian dipertahankan; coba lagi setelah sumber tersedia.']);
            }
        }
        DB::transaction(function () use ($request, $scope, $data, $key, $period) {
            $current = $period->constrain(AssetWellnessPolicy::where('asset_ref', $scope['asset_ref']))->latest('revision')->first();
            abort_if($current && $current->created_by !== $request->user()->id, 403);
            if (($current?->revision ?? 0) !== (int) $data['previous_revision']) {
                throw ValidationException::withMessages(['previous_revision' => 'Pengaturan sudah berubah. Buka ulang halaman; versi lama tidak ditimpa.']);
            }
            $rules = ['schema_version' => AssetWellnessPolicy::SCHEMA, 'status' => 'DRAFT_NOT_APPROVED',
                'scope' => $period->annual ? 'exact_asset_calendar_year_Asia_Jakarta' : 'exact_asset_date_range_Asia_Jakarta', 'age_basis' => $period->annual ? 'calendar_date_as_of_today_Asia_Jakarta' : 'calendar_date_relative_to_period_end_using_current_revisions',
                'criticality_label' => $data['criticality_label'] ?? null, 'criticality_basis' => $data['criticality_basis'] ?? null,
                'components' => $data['components'], 'pdm_rules' => $this->pointRules($data, $scope, $period)];
            if (! $period->annual) {
                $rules['period_key'] = $period->key();
                $rules['period'] = $period->metadata();
            }
            AssetWellnessPolicy::create([...$scope, ...$period->attributes(), 'revision' => (AssetWellnessPolicy::where($scope)->max('revision') ?? 0) + 1, 'created_by' => $request->user()->id,
                'request_key' => $key, 'rules' => $rules, 'evidence' => $data['evidence'], 'reason' => $data['reason'], 'created_at' => now()]);
        });

        return redirect()->route('wellness.policy', $navigation)->with('status', 'Usulan pengaturan tersimpan sebagai draft. Belum ada metode, criticality, alarm atau skor yang disahkan.');
    }

    private function pointRules(array $data, array $scope, ReliabilityPeriod $period): array
    {
        $rules = [];
        $seen = [];
        foreach ($data['pdm_rules'] ?? [] as $i => $rule) {
            if (! empty($rule['remove'])) {
                continue;
            }
            unset($rule['remove']);
            if (collect($rule)->every(fn ($value) => $value === null || $value === '')) {
                continue;
            }
            $fail = fn ($message) => throw ValidationException::withMessages(["pdm_rules.$i.point" => $message]);
            $anchor = PdmActivity::whereKey($rule['anchor_id'] ?? 0)->where('asset_ref', $scope['asset_ref'])->whereBetween('measured_on', [$period->start->toDateString(), $period->end->subDay()->toDateString()])->first();
            if (! $anchor) {
                $fail('Pilih pengukuran acuan pada aset dan periode yang sama.');
            }
            $basis = $anchor->analysisBasis();
            if (! hash_equals($basis['fingerprint'], $data['anchor_fingerprints'][$anchor->id] ?? '')) {
                $fail('Pengukuran acuan berubah atau tidak ada pada form. Buka ulang untuk memeriksa konteks terbaru.');
            }
            $field = collect($anchor->template_snapshot['fields'] ?? [])->firstWhere('key', $rule['point'] ?? '');
            $unit = $anchor->readings[$rule['point'] ?? '']['unit'] ?? $field['unit'] ?? null;
            if (! $field || ($field['type'] ?? null) !== 'number' || ($anchor->template_snapshot['preview_only'] ?? true) || ! is_string($unit) || trim($unit) === '' || (! empty($field['unit']) && $field['unit'] !== $unit)) {
                $fail('Titik harus numerik, satuan jelas dan berasal dari snapshot form yang bisa digunakan.');
            }
            foreach (PdmTrend::CONTEXT as $context) {
                if (trim((string) $anchor->$context) === '') {
                    $fail('Konteks pengukuran belum lengkap. Lengkapi mode, alat, kondisi operasi dan dasar pemilihan aset terlebih dahulu.');
                }
            }
            $lower = $rule['lower'] ?? null;
            $upper = $rule['upper'] ?? null;
            if (($lower === null && $upper === null) || ($lower !== null && ! is_finite((float) $lower)) || ($upper !== null && ! is_finite((float) $upper)) || ($lower !== null && $upper !== null && (float) $lower > (float) $upper) || mb_strlen(trim($rule['requirement'] ?? '')) < 5) {
                $fail('Isi minimal satu batas hingga, batas bawah ≤ atas, dan dasar usulan minimal 5 karakter.');
            }
            $context = $anchor->only(['template_id', 'template_fingerprint', 'method', ...PdmTrend::CONTEXT]);
            $context['template_snapshot'] = $anchor->template_snapshot;
            $identity = hash('sha256', json_encode([$context, $rule['point'], $unit], JSON_THROW_ON_ERROR));
            if (isset($seen[$identity])) {
                $fail('Titik dan konteks exact ini sudah memiliki usulan. Jangan menduplikasi batas.');
            }
            $seen[$identity] = true;
            $rules[] = ['anchor_id' => $anchor->id, 'anchor_version' => $anchor->version, 'anchor_fingerprint' => $basis['fingerprint'],
                'scope' => $context, 'point' => $rule['point'], 'field' => $field, 'unit' => $unit,
                'lower' => $lower === null ? null : (float) $lower, 'upper' => $upper === null ? null : (float) $upper,
                'max_age_days' => isset($rule['max_age_days']) ? (int) $rule['max_age_days'] : null, 'requirement' => $rule['requirement']];
        }

        return $rules;
    }

    private function scope(Request $request): array
    {
        $scope = $request->validate(['asset_ref' => ['required', 'string', 'max:240', 'starts_with:asset:MAXIMO:MXASSET:BSR:IP:', 'not_regex:/[\\\\\/]/'], 'year' => ['nullable', 'integer', 'between:1900,'.now('Asia/Jakarta')->year]]);
        $scope['year'] = ReliabilityPeriod::fromRequest($request)->start->year;

        return $scope;
    }
}
