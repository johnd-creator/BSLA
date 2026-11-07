<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasMany;

class AssetPriority extends Model
{
    public const URGENCIES = ['immediate' => 'Segera', 'planned' => 'Terencana', 'monitor' => 'Pantau'];

    public const STATUSES = ['active' => 'Aktif', 'closed' => 'Selesai', 'voided' => 'Dibatalkan'];

    protected $guarded = ['id', 'version'];

    protected function casts(): array
    {
        return ['due_on' => 'immutable_date', 'review_on' => 'immutable_date', 'version' => 'integer'];
    }

    public function author(): BelongsTo
    {
        return $this->belongsTo(User::class, 'created_by');
    }

    public function disruption(): BelongsTo
    {
        return $this->belongsTo(AssetDisruption::class, 'disruption_id');
    }

    public function inspection(): BelongsTo
    {
        return $this->belongsTo(InspectionDraft::class, 'inspection_id');
    }

    public function revisions(): HasMany
    {
        return $this->hasMany(AssetPriorityRevision::class)->orderByDesc('version');
    }

    public function reference(): string
    {
        return 'PRIORITAS-'.str_pad((string) $this->id, 5, '0', STR_PAD_LEFT);
    }

    public function snapshot(): array
    {
        return [...$this->only(['asset_ref', 'urgency', 'status', 'observed_condition', 'impact', 'reasoning', 'evidence_note', 'owner', 'disruption_id', 'inspection_id', 'work_order_ref']),
            'due_on' => $this->due_on?->format('Y-m-d'), 'review_on' => $this->review_on?->format('Y-m-d')];
    }
}
