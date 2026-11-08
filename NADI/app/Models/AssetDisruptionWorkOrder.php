<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class AssetDisruptionWorkOrder extends Model
{
    public const STATES = ['uncertain' => 'Belum dipastikan', 'related' => 'Terkait menurut engineer', 'removed' => 'Hubungan dilepas'];

    protected $guarded = ['id'];

    protected function casts(): array
    {
        return ['identity_checked_at' => 'immutable_datetime'];
    }

    public function disruption(): BelongsTo
    {
        return $this->belongsTo(AssetDisruption::class, 'asset_disruption_id');
    }

    public function number(): string
    {
        return rawurldecode(substr($this->work_order_ref, strlen('workorder:MAXIMO:MXWODETAIL:BSR:IP:')));
    }
}
