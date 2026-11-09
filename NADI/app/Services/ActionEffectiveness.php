<?php

namespace App\Services;

use App\Models\ActionEffectivenessReview;
use App\Models\InspectionDraft;
use App\Models\PdmActivity;
use Illuminate\Validation\ValidationException;

class ActionEffectiveness
{
    public function inspectionBasis(InspectionDraft $inspection): array
    {
        // Progress/target changes alone do not invalidate the engineer's judgment.
        $basis = $inspection->only(['asset_ref', 'pdm_activity_id', 'method', 'finding', 'recommendation']);
        $basis['inspected_on'] = $inspection->inspected_on?->format('Y-m-d');
        if ($inspection->pdm_activity_id) {
            $measurement = $inspection->pdmActivity;
            $source = $measurement ? $this->measurementBasis($measurement) : null;
            $basis['pdm_source'] = $source ? array_diff_key($source, ['version' => true]) : null;
            $basis['pdm_review_fingerprint'] = $inspection->pdmReviewedBasis()['fingerprint'] ?? null;
        }

        return ['version' => $inspection->version, 'fingerprint' => hash('sha256', json_encode($basis, JSON_THROW_ON_ERROR)), 'record' => $basis];
    }

    public function measurementBasis(PdmActivity $activity): array
    {
        return $activity->analysisBasis() + ['template_hash' => hash('sha256', json_encode($activity->template_snapshot, JSON_THROW_ON_ERROR))];
    }

    public function snapshot(PdmActivity $activity): array
    {
        return ['id' => $activity->id, 'reference' => $activity->reference(), 'basis' => $this->measurementBasis($activity),
            'asset_ref' => $activity->asset_ref, 'measured_on' => $activity->measurementDate(), 'measurement_label' => $activity->measurementLabel(),
            'precision_label' => $activity->precisionLabel(), 'template_id' => $activity->template_id,
            'method' => $activity->method, 'context' => $activity->only(PdmTrend::CONTEXT),
            'template_snapshot' => $activity->template_snapshot, 'readings' => $activity->readings];
    }

    public function state(?ActionEffectivenessReview $review, InspectionDraft $inspection): string
    {
        if (! $review) {
            return 'unassessed';
        }
        if (($review->evidence['inspection']['fingerprint'] ?? null) !== $this->inspectionBasis($inspection)['fingerprint']) {
            return 'stale';
        }
        foreach (['before' => 'beforeMeasurement', 'after' => 'afterMeasurement'] as $key => $relation) {
            $saved = $review->evidence[$key] ?? null;
            if ($saved) {
                $activity = $review->$relation;
                $basis = $activity ? $this->measurementBasis($activity) : null;
                if (! $basis || ($saved['basis']['fingerprint'] ?? null) !== $basis['fingerprint'] || ($saved['basis']['template_hash'] ?? null) !== $basis['template_hash']) {
                    return 'stale';
                }
            }
        }

        return $review->decision;
    }

    public function label(string $state): string
    {
        return ['unassessed' => 'Efektivitas belum dinilai', 'stale' => 'Bukti berubah · tinjau ulang'][$state] ?? ActionEffectivenessReview::DECISIONS[$state];
    }

    public function comparison(InspectionDraft $inspection, ?PdmActivity $before, ?PdmActivity $after, ?string $point, string $completedOn): array
    {
        if ($inspection->pdmReviewState()) {
            return ['valid' => false, 'blocker' => 'Analisis rekomendasi belum ditinjau terhadap pengukuran terkini. Tinjau ulang analisis sebelum menyatakan efektivitas.'];
        }
        if (! $before || ! $after || ! $point) {
            return ['valid' => false, 'blocker' => 'Pilih dua pengukuran dan satu titik numerik untuk menilai efektivitas.'];
        }
        if ($before->id === $after->id || ! $inspection->asset_ref || $before->asset_ref !== $inspection->asset_ref || $after->asset_ref !== $inspection->asset_ref) {
            return ['valid' => false, 'blocker' => 'Dua pengukuran harus berbeda dan berasal dari aset rekomendasi yang sama.'];
        }
        // Action time is a literal date. Same-day evidence cannot establish intraday sequence.
        if ($before->measurementDate() >= $completedOn || $after->measurementDate() <= $completedOn) {
            return ['valid' => false, 'blocker' => 'Pengukuran sebelum harus bertanggal lebih awal, dan sesudah lebih akhir dari tanggal tindakan. Urutan pada hari yang sama belum dapat dibuktikan.'];
        }
        foreach (['template_id', 'template_fingerprint', 'method', ...PdmTrend::CONTEXT] as $key) {
            if (trim((string) $before->$key) === '' || $before->$key !== $after->$key) {
                return ['valid' => false, 'blocker' => 'Template, metode, alat, mode, kondisi operasi dan titik/lokasi harus lengkap dan identik.'];
            }
        }
        $field = collect($before->template_snapshot['fields'] ?? [])->firstWhere('key', $point);
        $otherField = collect($after->template_snapshot['fields'] ?? [])->firstWhere('key', $point);
        if (! $field || ($field['type'] ?? null) !== 'number' || $otherField !== $field || $before->template_snapshot !== $after->template_snapshot || ($before->template_snapshot['preview_only'] ?? true)) {
            return ['valid' => false, 'blocker' => 'Titik numerik dan snapshot template harus identik serta bukan template review-only.'];
        }
        $values = [];
        foreach (['before' => $before, 'after' => $after] as $key => $activity) {
            $reading = $activity->readings[$point] ?? [];
            $raw = $reading['value'] ?? null;
            if ($raw === null || $raw === '' || ! is_numeric($raw) || ! is_finite((float) $raw) || empty($field['unit']) || ($reading['unit'] ?? null) !== $field['unit']) {
                return ['valid' => false, 'blocker' => 'Kedua nilai harus terukur, finite dan memakai satuan titik yang sama. Nilai kosong bukan nol.'];
            }
            $values[$key] = $raw;
        }

        return ['valid' => true, 'point_label' => $field['label'], 'unit' => $field['unit'], ...$values];
    }

    public function validateDecision(array $comparison, string $decision): void
    {
        if ($decision !== 'inconclusive' && ! $comparison['valid']) {
            throw ValidationException::withMessages(['decision' => $comparison['blocker']]);
        }
    }
}
