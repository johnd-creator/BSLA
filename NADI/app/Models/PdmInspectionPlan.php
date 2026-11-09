<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasMany;

class PdmInspectionPlan extends Model
{
    protected $guarded = ['id', 'version'];

    public const FREQUENCIES = ['days' => 'Hari', 'weeks' => 'Minggu', 'months' => 'Bulan kalender'];

    public const STATUSES = ['active' => 'Aktif', 'paused' => 'Dijeda'];

    protected function casts(): array
    {
        return ['template_snapshot' => 'array', 'first_due_on' => 'immutable_date:Y-m-d', 'frequency_value' => 'integer', 'version' => 'integer'];
    }

    public function setFirstDueOnAttribute($value): void
    {
        $this->attributes['first_due_on'] = $value instanceof \DateTimeInterface ? $value->format('Y-m-d') : $value;
    }

    public function author(): BelongsTo
    {
        return $this->belongsTo(User::class, 'created_by');
    }

    public function revisions(): HasMany
    {
        return $this->hasMany(PdmInspectionPlanRevision::class, 'plan_id');
    }

    public function point(): ?array
    {
        return collect($this->template_snapshot['fields'] ?? [])->firstWhere('key', $this->point_key);
    }

    public function reference(): string
    {
        return 'PDM-PLAN-'.str_pad((string) $this->id, 5, '0', STR_PAD_LEFT);
    }
}
