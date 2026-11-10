<?php

namespace App\Services;

use Carbon\CarbonImmutable;
use Illuminate\Database\Eloquent\Builder;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Schema;
use Illuminate\Validation\Rule;
use Illuminate\Validation\ValidationException;

/** Whole local dates, represented by a half-open Asia/Jakarta interval. */
final class ReliabilityPeriod
{
    public const OPTIONS = ['year' => 'Tahun kalender', '3m' => '3 bulan terakhir', '6m' => '6 bulan terakhir', '12m' => '12 bulan terakhir', 'custom' => 'Rentang tanggal'];

    private function __construct(public readonly CarbonImmutable $start, public readonly CarbonImmutable $end, public readonly bool $annual) {}

    public static function year(int $year): self
    {
        $start = CarbonImmutable::create($year, 1, 1, 0, 0, 0, ReliabilityEvidence::ZONE);

        return new self($start, $start->addYear(), true);
    }

    public static function fromRequest(Request $request): self
    {
        $today = now(ReliabilityEvidence::ZONE)->toDateString();
        $data = $request->validate([
            'period' => ['nullable', Rule::in(array_keys(self::OPTIONS))],
            'year' => ['nullable', 'integer', 'between:1900,'.now(ReliabilityEvidence::ZONE)->year],
            'start_date' => ['nullable', 'required_if:period,custom', 'date_format:Y-m-d', 'after_or_equal:1900-01-01'],
            'end_date' => ['nullable', 'required_if:period,custom', 'date_format:Y-m-d', 'after_or_equal:1900-01-01', 'before:'.$today],
        ]);
        $mode = $data['period'] ?? 'year';
        if ($mode === 'year') {
            return self::year((int) ($data['year'] ?? now(ReliabilityEvidence::ZONE)->year));
        }
        $end = isset($data['end_date']) ? CarbonImmutable::createFromFormat('!Y-m-d', $data['end_date'], ReliabilityEvidence::ZONE)->addDay() : CarbonImmutable::today(ReliabilityEvidence::ZONE);
        $start = $mode === 'custom' ? CarbonImmutable::createFromFormat('!Y-m-d', $data['start_date'], ReliabilityEvidence::ZONE) : $end->subMonthsNoOverflow((int) $mode);
        if ($start->gte($end) || $start->year < 1900) {
            throw ValidationException::withMessages(['start_date' => 'Tanggal awal harus paling lambat tanggal akhir, mulai 1900.']);
        }

        return new self($start, $end, false);
    }

    public static function fromReport(array $report): self
    {
        $period = $report['period'];
        if (($period['kind'] ?? 'year') === 'year') {
            return self::year((int) $period['year']);
        }

        return new self(CarbonImmutable::parse($period['start_inclusive']), CarbonImmutable::parse($period['end_exclusive']), false);
    }

    public function key(): ?string
    {
        return $this->annual ? null : 'range:'.hash('sha256', json_encode([$this->start->toIso8601String(), $this->end->toIso8601String(), ReliabilityEvidence::ZONE], JSON_THROW_ON_ERROR));
    }

    public function storageReady(string $table): bool
    {
        return Schema::hasTable($table) && ($this->annual || Schema::hasColumn($table, 'period_key'));
    }

    public function constrain(Builder $query): Builder
    {
        $query->where('year', $this->start->year);
        if (Schema::hasColumn($query->getModel()->getTable(), 'period_key')) {
            return $this->annual ? $query->whereNull('period_key') : $query->where('period_key', $this->key());
        }

        return $this->annual ? $query : $query->whereRaw('0 = 1');
    }

    public function attributes(): array
    {
        return $this->annual ? [] : ['period_key' => $this->key()];
    }

    public function matchesRecord(object $record): bool
    {
        return $record->year === $this->start->year && $record->period_key === $this->key();
    }

    public function containsDate(?string $date): bool
    {
        return $date !== null && $date >= $this->start->toDateString() && $date < $this->end->toDateString();
    }

    public function query(): array
    {
        // Resolve rolling selections once. Pagination, downloads and POSTs keep
        // these exact boundaries even after midnight or when revisited later.
        return $this->annual ? ['year' => $this->start->year] : ['period' => 'custom', 'start_date' => $this->start->toDateString(), 'end_date' => $this->end->subDay()->toDateString()];
    }

    public function label(): string
    {
        return $this->annual ? (string) $this->start->year : $this->start->toDateString().' sampai '.$this->end->subDay()->toDateString();
    }

    public function metadata(): array
    {
        // Retain the original annual basis byte-for-byte. Existing snapshot and
        // approval hashes must not change merely because range reports exist.
        $legacy = ['year' => $this->start->year, 'timezone' => ReliabilityEvidence::ZONE, 'start_inclusive' => $this->start->toIso8601String(), 'end_exclusive' => $this->end->toIso8601String(), 'is_closed_calendar_year' => $this->end->lte(now()), 'episode_basis' => 'Reviewed failure onset when known; otherwise observation date for review queue. Full completed episode belongs to onset year, never clipped or double-counted in later year.'];
        if ($this->annual) {
            return $legacy;
        }

        return [...$legacy, 'kind' => 'range', 'label' => $this->label(), 'is_closed_calendar_year' => false, 'is_closed_period' => $this->end->lte(now()),
            'episode_basis' => 'Reviewed onset in [start, end); full completed episode retained, including restoration after end. Exposure alone is clipped. Overlapping reports are not additive.',
            'knowledge_basis' => 'CURRENT_REVIEW_OF_HISTORICAL_EVENTS', 'quality_key_compatibility' => 'in_year/out_of_year/unknown_year and cross_year_restoration refer to the selected period, not an annual cohort.',
            'governance' => 'EXACT_RANGE_GOVERNANCE: independent local method, census attestation and Supervisor snapshot decision; annual approvals are not inherited.'];
    }
}
