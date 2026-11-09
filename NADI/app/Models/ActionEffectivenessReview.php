<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class ActionEffectivenessReview extends Model
{
    public const DECISIONS = ['inconclusive' => 'Belum dapat dinilai', 'effective' => 'Efektif menurut engineer', 'needs_action' => 'Perlu tindakan lagi'];

    public $timestamps = false;

    protected $guarded = ['id'];

    protected function casts(): array
    {
        return ['evidence' => 'array', 'created_at' => 'immutable_datetime', 'revision' => 'integer'];
    }

    public function author(): BelongsTo
    {
        return $this->belongsTo(User::class, 'created_by');
    }

    public function beforeMeasurement(): BelongsTo
    {
        return $this->belongsTo(PdmActivity::class, 'before_activity_id');
    }

    public function afterMeasurement(): BelongsTo
    {
        return $this->belongsTo(PdmActivity::class, 'after_activity_id');
    }
}
