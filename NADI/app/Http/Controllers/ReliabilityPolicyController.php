<?php

namespace App\Http\Controllers;

use App\Models\ReliabilityPolicy;
use App\Services\ReliabilityMart;
use App\Services\ReliabilityPeriod;
use App\Services\ReliabilityScope;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Gate;
use Illuminate\Support\Str;
use Illuminate\Validation\Rule;
use Illuminate\Validation\ValidationException;
use Throwable;

class ReliabilityPolicyController extends Controller
{
    public function index(Request $request)
    {
        $scope = $this->scope($request);
        $period = ReliabilityPeriod::fromRequest($request);
        $navigation = ['asset_ref' => $scope['asset_ref'], ...$period->query()];
        $query = $period->constrain(ReliabilityPolicy::where('asset_ref', $scope['asset_ref']));

        return view('reliability.policy', ['assetRef' => $scope['asset_ref'], 'year' => $scope['year'], 'period' => $period, 'storageReady' => $period->storageReady('reliability_policies'), 'latest' => (clone $query)->latest('revision')->first(),
            'policies' => $query->with('author:id,name')->latest('revision')->paginate(10)->appends($navigation), 'requestKey' => (string) Str::uuid()]);
    }

    public function store(Request $request, ReliabilityMart $mart)
    {
        Gate::authorize('write-asset-disruptions');
        $scope = $this->scope($request);
        $period = ReliabilityPeriod::fromRequest($request);
        $navigation = ['asset_ref' => $scope['asset_ref'], ...$period->query()];
        if (! $period->storageReady('reliability_policies')) {
            throw ValidationException::withMessages(['previous_revision' => 'Penyimpanan metode per rentang belum diaktifkan. Tidak ada draft tersimpan.']);
        }
        $key = $request->validate(['request_key' => ['required', 'uuid']])['request_key'];
        if ($saved = ReliabilityPolicy::where('request_key', $key)->first()) {
            abort_unless($saved->created_by === $request->user()->id && $saved->asset_ref === $scope['asset_ref'] && $period->matchesRecord($saved), 409);

            return redirect()->route('reliability.policies', $navigation);
        }
        $latest = $period->constrain(ReliabilityPolicy::where('asset_ref', $scope['asset_ref']))->latest('revision')->first();
        abort_if($latest && $latest->created_by !== $request->user()->id, 403);
        $data = $request->validate([
            'previous_revision' => ['required', 'integer', 'min:0'], 'status' => ['required', Rule::in(['draft', 'reviewed_local'])],
            'required_function' => ['nullable', 'string', 'max:2000'], 'failure_definition' => ['nullable', 'string', 'max:2000'],
            'exposure_basis' => ['required', Rule::in(['undecided', 'run_only', 'run_and_standby'])],
            'recurrence_policy' => ['required', Rule::in(['undecided', 'restored_before_recurrence'])],
            'mttr_basis' => ['required', Rule::in(['undecided', 'active_repair', 'restoration'])],
            'minimum_coverage' => ['nullable', 'numeric', 'between:0,100'],
            'failure_scope' => ['required', Rule::in(['unknown', 'attested_same_function'])],
            'failure_coverage' => ['required', Rule::in(['unknown', 'attested_complete'])],
            'failure_coverage_evidence' => ['nullable', 'required_if:failure_coverage,attested_complete', 'string', 'min:5', 'max:4000'],
            'incomplete_policy' => ['required', Rule::in(['undecided', 'withhold'])],
            'evidence' => ['required', 'string', 'min:5', 'max:4000'], 'reason' => ['required', 'string', 'min:5', 'max:2000'],
            'attestation' => ['accepted_if:status,reviewed_local', 'accepted_if:failure_coverage,attested_complete', 'accepted_if:failure_scope,attested_same_function'],
        ]);
        if (! $latest) {
            try {
                $mart->historyAsset($scope['asset_ref']);
            } catch (Throwable) {
                throw ValidationException::withMessages(['asset_ref' => 'Identitas aset belum dapat diverifikasi. Isian tetap ada; coba lagi setelah sumber tersedia.']);
            }
        }
        DB::transaction(function () use ($request, $scope, $data, $key, $period) {
            $current = $period->constrain(ReliabilityPolicy::where('asset_ref', $scope['asset_ref']))->latest('revision')->first();
            abort_if($current && $current->created_by !== $request->user()->id, 403);
            if (($current?->revision ?? 0) !== (int) $data['previous_revision']) {
                throw ValidationException::withMessages(['previous_revision' => 'Aturan lebih baru sudah tersimpan. Buka ulang halaman.']);
            }
            $rules = collect($data)->except(['previous_revision', 'evidence', 'reason', 'attestation'])->all();
            $rules['schema_version'] = $period->annual ? ReliabilityPolicy::SCHEMA : ReliabilityPolicy::RANGE_SCHEMA;
            $rules['scope'] = $period->annual ? 'exact_asset_calendar_year_Asia_Jakarta' : 'exact_asset_date_range_Asia_Jakarta';
            if (! $period->annual) {
                $rules['period_key'] = $period->key();
                $rules['period'] = $period->metadata();
            }
            $rules['cohort'] = 'reviewed_failure_onset_full_completed_episode';
            $rules['organization_approval'] = 'SEPARATE_SUPERVISOR_DECISION';
            $rules['failure_scope_hash'] = app(ReliabilityScope::class)->currentHash($scope['asset_ref']);
            $rules['failure_scope_checked_at'] = now()->toIso8601String();
            ReliabilityPolicy::create([...$scope, ...$period->attributes(), 'revision' => (ReliabilityPolicy::where($scope)->max('revision') ?? 0) + 1, 'created_by' => $request->user()->id,
                'request_key' => $key, 'rules' => $rules, 'evidence' => $data['evidence'], 'reason' => $data['reason'], 'created_at' => now()]);
        });

        return redirect()->route('reliability.policies', $navigation)->with('status', 'Versi aturan lokal tersimpan. Keputusan kosong tetap belum diputuskan; ini bukan approval organisasi.');
    }

    private function scope(Request $request): array
    {
        $data = $request->validate(['asset_ref' => ['required', 'string', 'max:240', 'starts_with:asset:MAXIMO:MXASSET:BSR:IP:', 'not_regex:/[\\\\\/]/'], 'year' => ['nullable', 'integer', 'between:1900,'.now('Asia/Jakarta')->year]]);
        $data['year'] = ReliabilityPeriod::fromRequest($request)->start->year;

        return $data;
    }
}
