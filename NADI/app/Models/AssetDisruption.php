<?php

namespace App\Models;

use Carbon\CarbonImmutable;
use Illuminate\Database\Eloquent\Builder;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasMany;

class AssetDisruption extends Model
{
    public const TYPES = ['trip' => 'Trip', 'failure' => 'Gagal fungsi', 'disturbance' => 'Gangguan', 'other' => 'Lainnya'];

    public const ROLES = ['cause' => 'Penyebab (menurut catatan)', 'affected' => 'Terdampak', 'unknown' => 'Belum dipastikan'];

    public const IMPACTS = ['unavailable' => 'Tidak siap / berhenti', 'degraded' => 'Kemampuan menurun', 'none' => 'Tidak ada dampak operasi yang dicatat', 'unknown' => 'Belum diketahui'];

    public const ZONES = ['Asia/Jakarta' => 'WIB · Asia/Jakarta', 'Asia/Makassar' => 'WITA · Asia/Makassar', 'Asia/Jayapura' => 'WIT · Asia/Jayapura', 'UTC' => 'UTC'];

    protected $guarded = ['id', 'version'];

    protected function casts(): array
    {
        return ['occurred_at' => 'immutable_datetime', 'restored_at' => 'immutable_datetime', 'version' => 'integer'];
    }

    public function author(): BelongsTo
    {
        return $this->belongsTo(User::class, 'created_by');
    }

    public function members(): HasMany
    {
        return $this->hasMany(AssetDisruptionMember::class);
    }

    public function revisions(): HasMany
    {
        return $this->hasMany(AssetDisruptionRevision::class)->orderByDesc('version');
    }

    public function scopeForAsset(Builder $query, string $asset): void
    {
        $query->whereHas('members', fn ($query) => $query->where('asset_ref', $asset));
    }

    public function reference(): string
    {
        return 'GANGGUAN-'.str_pad((string) $this->id, 5, '0', STR_PAD_LEFT);
    }

    public function timeLabel(string $field = 'occurred'): string
    {
        $at = $this->{$field.'_at'};
        $on = $this->{$field.'_on'};

        return $at ? $at->setTimezone($this->timezone)->format('d M Y H:i:s').' · '.$this->timezone
            : ($on ? CarbonImmutable::parse($on)->format('d M Y').' · tanggal saja' : 'Belum diketahui');
    }

    public function durationSeconds(): ?int
    {
        return $this->occurred_at && $this->restored_at ? (int) $this->occurred_at->diffInSeconds($this->restored_at) : null;
    }

    public function roleFor(string $asset): ?string
    {
        return $this->members->firstWhere('asset_ref', $asset)?->role;
    }

    public function snapshot(): array
    {
        return [...$this->only(['asset_ref', 'event_type', 'description', 'known_cause', 'impact', 'impact_note', 'occurred_on', 'restored_on', 'timezone', 'work_order_ref', 'evidence_note', 'status']),
            'occurred_at' => $this->occurred_at?->toIso8601String(), 'restored_at' => $this->restored_at?->toIso8601String(),
            'members' => $this->members()->orderBy('asset_ref')->get(['asset_ref', 'role'])->toArray()];
    }
}
