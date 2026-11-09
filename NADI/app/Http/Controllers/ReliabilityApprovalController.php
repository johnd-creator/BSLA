<?php

namespace App\Http\Controllers;

use App\Models\ReliabilityApproval;
use App\Models\ReliabilitySnapshot;
use App\Services\ReliabilityApprovalStatus;
use App\Services\ReliabilityEvidence;
use App\Services\ReliabilityMart;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Gate;
use Illuminate\Support\Facades\Schema;
use Illuminate\Validation\Rule;
use Illuminate\Validation\ValidationException;

class ReliabilityApprovalController extends Controller
{
    public function store(Request $request, ReliabilitySnapshot $snapshot, ReliabilityEvidence $evidence)
    {
        Gate::authorize('approve-reliability');
        abort_unless(Schema::hasTable('reliability_approvals'), 503, 'Penyimpanan pengesahan belum dimigrasikan.');
        $data = $request->validate(['request_key' => ['required', 'uuid'], 'decision' => ['required', Rule::in(['approved', 'revoked'])],
            'previous_revision' => ['required', 'integer', 'min:0'], 'calculation_hash' => ['required', 'string', 'size:64'],
            'metrics' => ['nullable', 'required_if:decision,approved', 'array', 'min:1', 'max:2'], 'metrics.*' => ['required', 'distinct', Rule::in(['mtbf', 'mttr'])],
            'evidence' => ['required', 'string', 'min:5', 'max:4000'], 'reason' => ['required', 'string', 'min:5', 'max:2000'],
            'method_attestation' => ['accepted_if:decision,approved'], 'result_attestation' => ['accepted_if:decision,approved']]);
        if ($saved = ReliabilityApproval::where('request_key', $data['request_key'])->first()) {
            abort_unless($saved->created_by === $request->user()->id && $saved->reliability_snapshot_id === $snapshot->id && $saved->decision === $data['decision'], 409);

            return redirect()->route('reliability.snapshots.show', $snapshot)->with('status', 'Keputusan ini sudah tersimpan sekali.');
        }
        DB::transaction(function () use ($request, $snapshot, $data, $evidence) {
            // SQLite IMMEDIATE transaction serializes the decision with local
            // event/review/log/method edits. No source HTTP runs under this lock.
            $latest = ReliabilityApproval::where('asset_ref', $snapshot->asset_ref)->where('year', $snapshot->year)->latest('revision')->first();
            if (($latest?->revision ?? 0) !== (int) $data['previous_revision']) {
                throw ValidationException::withMessages(['previous_revision' => 'Keputusan lebih baru sudah ada. Buka ulang snapshot sebelum bertindak.']);
            }
            $saved = $snapshot->report['calculation'] ?? null;
            if (! $saved || ! hash_equals($saved['calculation_hash'], $data['calculation_hash'])) {
                throw ValidationException::withMessages(['calculation_hash' => 'Snapshot tidak memiliki engine/basis yang cocok. Buat snapshot pilot baru.']);
            }
            $current = $evidence->localApprovalReport($snapshot->asset_ref, $snapshot->year);
            $values = [];
            if ($data['decision'] === 'approved') {
                if (! hash_equals($saved['calculation_hash'], $current['calculation']['calculation_hash'])) {
                    throw ValidationException::withMessages(['calculation_hash' => 'Bukti, metode atau engine sudah berubah. Rekonsiliasi dan buat snapshot baru sebelum pengesahan.']);
                }
                foreach ($data['metrics'] as $metric) {
                    if ($saved['pilot'][$metric]['status'] !== 'PILOT_CALCULATED' || $saved['pilot'][$metric]['value'] === null) {
                        throw ValidationException::withMessages(['metrics' => strtoupper($metric).' belum memenuhi gerbang data/metode. Metrik ini tidak dapat disahkan.']);
                    }
                    $values[$metric] = $saved['pilot'][$metric];
                }
            } else {
                if (! $latest || $latest->decision !== 'approved' || $latest->reliability_snapshot_id !== $snapshot->id) {
                    throw ValidationException::withMessages(['decision' => 'Hanya keputusan pengesahan terakhir untuk snapshot ini yang dapat dicabut.']);
                }
            }
            ReliabilityApproval::create(['asset_ref' => $snapshot->asset_ref, 'year' => $snapshot->year, 'revision' => ($latest?->revision ?? 0) + 1,
                'reliability_snapshot_id' => $snapshot->id, 'created_by' => $request->user()->id, 'actor_role' => 'SUPERVISOR',
                'request_key' => $data['request_key'], 'decision' => $data['decision'], 'metrics' => $data['decision'] === 'approved' ? array_values($data['metrics']) : $latest->metrics,
                'engine_version' => $saved['engine_version'], 'policy_id' => $saved['policy_id'], 'policy_revision' => $saved['policy_revision'],
                'basis_hash' => $saved['basis_hash'], 'calculation_hash' => $saved['calculation_hash'], 'snapshot_evidence_hash' => $snapshot->evidence_hash,
                'method_attestation' => $data['decision'] === 'approved', 'result_attestation' => $data['decision'] === 'approved',
                'evidence' => $data['evidence'], 'reason' => $data['reason'], 'approved_values' => $values, 'created_at' => now()]);
        });

        return redirect()->route('reliability.snapshots.show', $snapshot)->with('status', $data['decision'] === 'approved' ? 'Pengesahan Supervisor tersimpan untuk metode, metrik dan scope snapshot ini. Bukti asli tidak ditimpa.' : 'Pengesahan dicabut. Keputusan sebelumnya tetap tersimpan dalam audit.');
    }

    public function download(ReliabilitySnapshot $snapshot, ReliabilityEvidence $evidence, ReliabilityMart $mart, ReliabilityApprovalStatus $status)
    {
        abort_unless(Schema::hasTable('reliability_approvals'), 503);
        $current = $evidence->report($snapshot->asset_ref, $snapshot->year, $mart);
        $packet = ['schema_version' => 'nadi.supervisor-approval.v1', 'checked_at' => now()->toIso8601String(), 'snapshot_id' => $snapshot->id,
            'snapshot_evidence_hash' => $snapshot->evidence_hash, 'status' => $status->current($current, $snapshot),
            'decisions' => ReliabilityApproval::where('reliability_snapshot_id', $snapshot->id)->orderBy('revision')->get()->toArray(),
            'original_report' => $snapshot->report];

        return response(json_encode($packet, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_THROW_ON_ERROR), 200, ['Content-Type' => 'application/json', 'Content-Disposition' => 'attachment; filename="nadi-supervisor-approval-'.$snapshot->id.'.json"', 'Cache-Control' => 'no-store, private', 'X-Content-Type-Options' => 'nosniff']);
    }
}
