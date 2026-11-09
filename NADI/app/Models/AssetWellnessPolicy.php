<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

/** Append-only local proposals. Saving does not validate an engineering method. */
class AssetWellnessPolicy extends Model
{
    public const SCHEMA = 'asset-wellness-policy-draft-v1';

    public $timestamps = false;

    protected $guarded = ['id'];

    protected function casts(): array
    {
        return ['revision' => 'integer', 'year' => 'integer', 'rules' => 'array', 'created_at' => 'immutable_datetime'];
    }

    public function author(): BelongsTo
    {
        return $this->belongsTo(User::class, 'created_by');
    }
}
