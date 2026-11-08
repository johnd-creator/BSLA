<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class ReliabilitySnapshot extends Model
{
    public $timestamps = false;

    protected $guarded = ['id'];

    protected function casts(): array
    {
        return ['report' => 'array', 'year' => 'integer', 'created_at' => 'immutable_datetime'];
    }
}
