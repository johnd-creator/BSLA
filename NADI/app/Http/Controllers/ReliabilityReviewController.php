<?php

namespace App\Http\Controllers;

use App\Models\AssetDisruption;
use App\Models\ReliabilityReview;
use App\Services\ReliabilityTiming;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Gate;
use Illuminate\Support\Str;
use Illuminate\Validation\Rule;
use Illuminate\Validation\ValidationException;

class ReliabilityReviewController extends Controller
{
    public function index(Request $request, AssetDisruption $disruption)
    {
        $data = $request->validate(['asset_ref' => ['nullable', 'string', 'max:240']]);
        $asset = $data['asset_ref'] ?? $disruption->asset_ref;
        abort_unless($disruption->members()->where('asset_ref', $asset)->exists(), 404);
        $reviews = ReliabilityReview::where('asset_disruption_id', $disruption->id)->where('asset_ref', $asset);

        return view('reliability.review', ['event' => $disruption->load('members'), 'assetRef' => $asset, 'latest' => (clone $reviews)->latest('revision')->first(), 'reviews' => $reviews->with('author:id,name')->latest('revision')->paginate(10), 'requestKey' => (string) Str::uuid()]);
    }

    public function store(Request $request, AssetDisruption $disruption, ReliabilityTiming $timing)
    {
        Gate::authorize('update-asset-disruption', $disruption);
        $key = $request->validate(['request_key' => ['required', 'uuid']])['request_key'];
        if ($existing = ReliabilityReview::where('request_key', $key)->first()) {
            abort_unless($existing->created_by === $request->user()->id && $existing->asset_disruption_id === $disruption->id, 409);

            return redirect()->route('reliability.reviews', [$disruption, 'asset_ref' => $existing->asset_ref])->with('status', 'Review ini sudah tersimpan sekali.');
        }
        $data = $request->validate([
            'asset_ref' => ['required', 'string', 'max:240'], 'event_version' => ['required', 'integer', 'min:1'],
            'previous_revision' => ['required', 'integer', 'min:0'],
            'classification' => ['required', Rule::in(array_keys(ReliabilityReview::CLASSIFICATIONS))],
            'required_function' => ['nullable', 'required_if:classification,failure', 'string', 'min:5', 'max:2000'],
            'evidence' => ['required', 'string', 'min:5', 'max:4000'], 'reason' => ['required', 'string', 'min:5', 'max:2000'],
            'duplicate_of' => ['nullable', 'required_if:classification,duplicate', 'integer', 'min:1'],
            'failure_at' => ['nullable', 'string', 'max:40'], 'restored_at' => ['nullable', 'string', 'max:40'],
            'repair_state' => ['required', Rule::in(array_keys(ReliabilityReview::REPAIR_STATES))],
            'active_intervals_text' => ['nullable', 'string', 'max:2500'], 'timing_evidence' => ['nullable', 'string', 'max:4000'],
            'attestation' => ['accepted'],
        ]);
        abort_unless($disruption->members()->where('asset_ref', $data['asset_ref'])->exists(), 404);
        $failure = $timing->instant($data['failure_at'] ?? null, 'failure_at');
        $restored = $timing->instant($data['restored_at'] ?? null, 'restored_at');
        if ($restored && (! $failure || $restored->lt($failure))) {
            throw ValidationException::withMessages(['restored_at' => 'Kembali siap memerlukan failure onset tepat dan tidak boleh mendahuluinya.']);
        }
        $intervals = $timing->intervals($data['active_intervals_text'] ?? null, $failure, $restored);
        if ($data['classification'] !== 'failure' && ($failure || $restored || $intervals || $data['repair_state'] !== 'unknown')) {
            throw ValidationException::withMessages(['classification' => 'Batas waktu reliability hanya untuk kehilangan fungsi yang dikonfirmasi. Kosongkan batas waktu dan pilih status perbaikan belum diketahui.']);
        }
        if ($data['classification'] !== 'duplicate' && ! empty($data['duplicate_of'])) {
            throw ValidationException::withMessages(['duplicate_of' => 'Target duplikat hanya berlaku untuk klasifikasi duplikat.']);
        }
        if (($failure || $restored || $intervals || $data['repair_state'] !== 'unknown') && mb_strlen(trim($data['timing_evidence'] ?? '')) < 5) {
            throw ValidationException::withMessages(['timing_evidence' => 'Referensi bukti waktu/status perbaikan wajib; waktu WO bukan bukti perbaikan otomatis.']);
        }
        if (($data['repair_state'] === 'completed' && ! $intervals) || (in_array($data['repair_state'], ['unknown', 'not_applicable'], true) && $intervals) || ($data['repair_state'] === 'ongoing' && $restored)) {
            throw ValidationException::withMessages(['repair_state' => 'Status perbaikan tidak sesuai interval. Selesai memerlukan interval; ongoing tidak boleh sudah kembali siap.']);
        }
        DB::transaction(function () use ($request, $disruption, $data, $key, $failure, $restored, $intervals) {
            // Serialize reviews against observation/WO edits on the owning event.
            if (! AssetDisruption::whereKey($disruption->id)->where('version', $data['event_version'])->where('status', 'recorded')->update(['version' => DB::raw('version')])) {
                throw ValidationException::withMessages(['event_version' => 'Catatan berubah atau dibatalkan. Buka ulang review sebelum menyimpan.']);
            }
            $event = $disruption->fresh();
            $current = ReliabilityReview::where('asset_disruption_id', $event->id)->where('asset_ref', $data['asset_ref'])->max('revision') ?? 0;
            if ((int) $current !== (int) $data['previous_revision']) {
                throw ValidationException::withMessages(['previous_revision' => 'Review lebih baru sudah tersimpan. Buka ulang halaman.']);
            }
            $duplicate = $targetReview = null;
            if ($data['classification'] === 'duplicate') {
                $duplicate = AssetDisruption::whereKey($data['duplicate_of'])->where('status', 'recorded')->forAsset($data['asset_ref'])->first();
                $targetReview = $duplicate ? ReliabilityReview::where('asset_disruption_id', $duplicate->id)->where('asset_ref', $data['asset_ref'])->latest('revision')->first() : null;
                if (! $duplicate || $duplicate->id >= $event->id || ! $targetReview || $targetReview->classification !== 'failure' || $targetReview->event_version !== $duplicate->version || $targetReview->rule_version !== ReliabilityReview::RULE) {
                    throw ValidationException::withMessages(['duplicate_of' => 'Pilih ID kejadian lebih awal pada aset yang sama dengan review failure masih berlaku. Rantai duplikat tidak diperbolehkan.']);
                }
            }
            ReliabilityReview::create([
                'asset_disruption_id' => $event->id, 'asset_ref' => $data['asset_ref'], 'revision' => $current + 1,
                'event_version' => $event->version, 'created_by' => $request->user()->id, 'request_key' => $key,
                'classification' => $data['classification'], 'duplicate_of' => $duplicate?->id, 'duplicate_version' => $duplicate?->version, 'duplicate_review_revision' => $targetReview?->revision,
                'required_function' => $data['required_function'] ?? null, 'evidence' => $data['evidence'], 'reason' => $data['reason'],
                'failure_at' => $failure, 'restored_at' => $restored, 'repair_state' => $data['repair_state'], 'active_intervals' => $intervals,
                'timing_evidence' => $data['timing_evidence'] ?? null, 'rule_version' => ReliabilityReview::RULE, 'event_snapshot' => $event->snapshot(), 'created_at' => now(),
            ]);
        });

        return redirect()->route('reliability.reviews', [$disruption, 'asset_ref' => $data['asset_ref']])->with('status', 'Review lokal tersimpan. Versi sebelumnya tetap ada; ini bukan approval KPI organisasi.');
    }
}
