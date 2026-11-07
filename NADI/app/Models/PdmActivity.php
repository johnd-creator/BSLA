<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Builder;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasOne;

class PdmActivity extends Model
{
    protected $guarded = ['id', 'version'];

    protected function casts(): array
    {
        return ['measured_on' => 'immutable_date:Y-m-d', 'measured_at' => 'immutable_datetime', 'template_snapshot' => 'array', 'readings' => 'array', 'version' => 'integer'];
    }

    protected static function booted(): void
    {
        static::saving(function (self $activity) {
            $activity->time_precision ??= 'datetime';
            if ($activity->time_precision === 'date') {
                $activity->measured_at = null;
                $activity->timezone = null;
            }
            if ($activity->time_precision === 'datetime' && $activity->measured_at && $activity->timezone) {
                $activity->measured_on = $activity->measured_at->setTimezone($activity->timezone)->format('Y-m-d');
            }
        });
    }

    public function setMeasuredOnAttribute($value): void
    {
        // SQLite DATE columns accept timestamp strings; keep the stored value
        // date-only too, rather than letting Eloquent append midnight.
        $this->attributes['measured_on'] = $value instanceof \DateTimeInterface ? $value->format('Y-m-d') : $value;
    }

    public function scopeNewestMeasurement(Builder $query): void
    {
        $query->orderByDesc('measured_on')
            ->orderByRaw('CASE WHEN measured_at IS NULL THEN 1 ELSE 0 END')
            ->orderByDesc('measured_at')->orderByDesc('id');
    }

    public function measurementDate(): string
    {
        return $this->measured_on?->format('Y-m-d')
            ?? $this->measured_at->setTimezone($this->timezone)->format('Y-m-d');
    }

    public function measurementLabel(): string
    {
        return $this->time_precision === 'date'
            ? $this->measured_on->format('d M Y')
            : $this->measured_at->setTimezone($this->timezone)->format('d M Y H:i:s');
    }

    public function precisionLabel(): string
    {
        return $this->time_precision === 'date' ? 'Tanggal saja · jam/zona tidak dicatat' : $this->timezone;
    }

    public function author(): BelongsTo
    {
        return $this->belongsTo(User::class, 'created_by');
    }

    public function inspection(): HasOne
    {
        return $this->hasOne(InspectionDraft::class);
    }

    public function reference(): string
    {
        return 'PDM-DRAFT-'.str_pad((string) $this->id, 5, '0', STR_PAD_LEFT);
    }
}
