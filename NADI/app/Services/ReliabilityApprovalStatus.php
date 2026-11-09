<?php

namespace App\Services;

use App\Models\ReliabilityApproval;
use App\Models\ReliabilitySnapshot;
use Illuminate\Support\Facades\Schema;

class ReliabilityApprovalStatus
{
    public function current(array $report, ?ReliabilitySnapshot $snapshot = null): array
    {
        $record = Schema::hasTable('reliability_approvals') ? ReliabilityApproval::where('asset_ref', $report['asset_ref'])->where('year', $report['period']['year'])->latest('revision')->first() : null;
        $calculation = $report['calculation'] ?? null;
        $status = ! $record ? 'AWAITING_SUPERVISOR' : ($record->decision === 'revoked' ? 'REVOKED' : 'APPROVED');
        if ($record && $record->decision === 'approved' && (! $calculation || $record->engine_version !== ReliabilityCalculator::VERSION || ! hash_equals($record->calculation_hash, $calculation['calculation_hash']))) {
            $status = 'STALE';
        }
        if ($snapshot && $record && $record->reliability_snapshot_id !== $snapshot->id) {
            $status = 'OTHER_SNAPSHOT';
        }
        $metrics = [];
        foreach (['mtbf', 'mttr'] as $key) {
            $eligible = $status === 'APPROVED' && in_array($key, $record->metrics, true) && ($calculation['pilot'][$key]['status'] ?? null) === 'PILOT_CALCULATED';
            $metrics[$key] = ['value' => $eligible ? $record->approved_values[$key]['value'] : null, 'unit' => 'hours',
                'status' => $eligible ? 'OFFICIAL_APPROVED' : 'NOT_READY',
                'blocker' => $eligible ? null : ($status === 'APPROVED' ? 'METRIC_NOT_INCLUDED_IN_APPROVAL' : $status)];
        }

        return ['status' => $status, 'metrics' => $metrics, 'approval' => $record ? [
            ...$record->only(['id', 'asset_ref', 'year', 'revision', 'reliability_snapshot_id', 'created_by', 'actor_role', 'decision', 'method_attestation', 'result_attestation', 'metrics', 'engine_version', 'policy_id', 'policy_revision', 'basis_hash', 'calculation_hash', 'snapshot_evidence_hash', 'evidence', 'reason', 'approved_values']),
            'created_at' => $record->created_at->toIso8601String(),
        ] : null, 'scope' => 'One exact asset, onset calendar year in Asia/Jakarta, selected metric definitions, immutable snapshot and method/engine/evidence versions. No hierarchy or other-year approval.'];
    }

    public function apply(array $report): array
    {
        $report['approval'] = $this->current($report);
        foreach (['mtbf', 'mttr'] as $key) {
            $report['metrics'][$key] = $report['approval']['metrics'][$key];
        }

        return $report;
    }
}
