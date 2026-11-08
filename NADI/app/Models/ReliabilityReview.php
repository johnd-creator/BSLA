<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class ReliabilityReview extends Model
{
    public const RULE = 'local-evidence-v1';

    public const CLASSIFICATIONS = ['uncertain' => 'Belum dipastikan', 'failure' => 'Kehilangan fungsi menurut engineer', 'not_failure' => 'Bukan failure aset ini', 'duplicate' => 'Duplikat kejadian lain'];

    public const REPAIR_STATES = ['unknown' => 'Belum diketahui', 'ongoing' => 'Perbaikan masih berlangsung menurut bukti', 'completed' => 'Perbaikan aktif selesai menurut bukti', 'not_applicable' => 'Tidak ada perbaikan aktif'];

    public $timestamps = false;

    protected $guarded = ['id'];

    protected function casts(): array
    {
        return ['revision' => 'integer', 'event_version' => 'integer', 'duplicate_version' => 'integer', 'duplicate_review_revision' => 'integer', 'active_intervals' => 'array', 'event_snapshot' => 'array', 'failure_at' => 'immutable_datetime', 'restored_at' => 'immutable_datetime', 'created_at' => 'immutable_datetime'];
    }

    public function author(): BelongsTo
    {
        return $this->belongsTo(User::class, 'created_by');
    }

    public function event(): BelongsTo
    {
        return $this->belongsTo(AssetDisruption::class, 'asset_disruption_id');
    }
}
