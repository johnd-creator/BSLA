<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class ReliabilityApproval extends Model
{
    public $timestamps = false;

    protected $guarded = ['id'];

    protected function casts(): array
    {
        return ['year' => 'integer', 'revision' => 'integer', 'policy_id' => 'integer', 'policy_revision' => 'integer', 'method_attestation' => 'boolean', 'result_attestation' => 'boolean', 'metrics' => 'array', 'approved_values' => 'array', 'created_at' => 'immutable_datetime'];
    }

    public function author(): BelongsTo
    {
        return $this->belongsTo(User::class, 'created_by');
    }
}
