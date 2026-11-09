<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasOne;

class InspectionDraft extends Model
{
    protected $fillable = ['request_reference', 'request_summary', 'asset_ref', 'method', 'inspected_on', 'finding', 'recommendation', 'target_completion', 'wo_reference', 'inspection_type', 'requester_name', 'follow_up_status', 'pdm_activity_id', 'created_by', 'request_key'];

    public const METHODS = ['VISUAL' => 'Visual', 'VIBRATION' => 'Vibration', 'THERMOGRAPHY' => 'Thermography', 'OIL_ANALYSIS' => 'Oil analysis', 'ULTRASOUND' => 'Ultrasound', 'TRIBOLOGY' => 'Tribology / oli', 'MCSA' => 'MCSA', 'CONDITION_MONITORING' => 'Condition monitoring', 'OTHER' => 'Lainnya'];

    public const FOLLOW_UP_STATUSES = ['open' => 'Terbuka', 'in_progress' => 'Sedang ditindaklanjuti', 'completed' => 'Selesai'];

    protected function casts(): array
    {
        return ['inspected_on' => 'date', 'target_completion' => 'date', 'version' => 'integer'];
    }

    public function author(): BelongsTo
    {
        return $this->belongsTo(User::class, 'created_by');
    }

    public function pdmActivity(): BelongsTo
    {
        return $this->belongsTo(PdmActivity::class);
    }

    public function pdmReviewAudit(): HasOne
    {
        return $this->hasOne(WorkspaceActivity::class, 'subject_id')->ofMany(['id' => 'max'], function ($query) {
            $query->where('kind', 'inspection')->whereNotNull('changes->pdm_basis');
        });
    }

    public function pdmReviewedBasis(): ?array
    {
        $changes = $this->pdmReviewAudit?->getAttribute('changes');

        return $changes['pdm_basis']['after'] ?? null;
    }

    public function pdmReviewState(): ?string
    {
        if (! $this->pdm_activity_id || (! $this->finding && ! $this->recommendation)) {
            return null;
        }
        $basis = $this->pdmReviewedBasis();
        if (! is_string($basis['fingerprint'] ?? null)) {
            return 'unknown';
        }

        return $this->pdmActivity && hash_equals($basis['fingerprint'], $this->pdmActivity->analysisBasis()['fingerprint']) ? null : 'stale';
    }

    public function stageLabel(): string
    {
        return $this->recommendation ? 'Rekomendasi draft' : ($this->finding ? 'Hasil inspeksi draft' : 'Permintaan draft');
    }

    public function reference(): string
    {
        return 'INS-DRAFT-'.str_pad((string) $this->id, 5, '0', STR_PAD_LEFT);
    }
}
