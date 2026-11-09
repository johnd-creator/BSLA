<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasMany;
use Illuminate\Database\Eloquent\Relations\HasOne;

class OperatingLog extends Model
{
    public const STATES = ['RUN' => 'RUN · beroperasi', 'STOP' => 'STOP · berhenti', 'STANDBY' => 'STANDBY · siaga', 'UNKNOWN' => 'UNKNOWN · belum diketahui'];

    public const REVIEWS = ['draft' => 'Belum diperiksa', 'verified' => 'Bukti diperiksa engineer pemilik', 'voided' => 'Dibatalkan, histori tetap ada'];

    protected $guarded = ['id'];

    protected function casts(): array
    {
        return ['version' => 'integer'];
    }

    public function revisions(): HasMany
    {
        return $this->hasMany(OperatingLogRevision::class);
    }

    public function latestRevision(): HasOne
    {
        return $this->hasOne(OperatingLogRevision::class)->latestOfMany('revision');
    }

    public function author(): BelongsTo
    {
        return $this->belongsTo(User::class, 'created_by');
    }
}
