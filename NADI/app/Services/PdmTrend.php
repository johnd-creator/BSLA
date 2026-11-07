<?php

namespace App\Services;

use App\Models\PdmActivity;
use Carbon\CarbonImmutable;

class PdmTrend
{
    public const LIMIT = 250;

    public const CONTEXT = ['measurement_mode', 'instrument', 'operating_condition', 'asset_selection_note'];

    public function forPoint(PdmActivity $anchor, string $point): array
    {
        $field = collect($anchor->template_snapshot['fields'] ?? [])->firstWhere('key', $point);
        abort_unless($field && ($field['type'] ?? null) === 'number', 422, 'Pilih titik numerik dari snapshot aktivitas ini.');
        $unit = $anchor->readings[$point]['unit'] ?? $field['unit'] ?? null;
        $query = PdmActivity::where('asset_ref', $anchor->asset_ref)
            ->where('template_id', $anchor->template_id)->where('template_fingerprint', $anchor->template_fingerprint)
            ->where('method', $anchor->method);
        foreach (self::CONTEXT as $key) {
            $query->where($key, $anchor->$key);
        }
        $activities = $query->newestMeasurement()->limit(self::LIMIT + 1)->get();
        $truncated = $activities->count() > self::LIMIT;
        $activities = $activities->take(self::LIMIT);
        $rows = [];
        $excluded = 0;
        $incomplete = ! is_string($unit) || trim($unit) === '' || ($anchor->template_snapshot['preview_only'] ?? true);
        foreach (self::CONTEXT as $key) {
            $incomplete = $incomplete || trim((string) $anchor->$key) === '';
        }
        foreach ($activities as $activity) {
            $candidate = collect($activity->template_snapshot['fields'] ?? [])->firstWhere('key', $point);
            $reading = $activity->readings[$point] ?? ['value' => null, 'unit' => null];
            // Do not trust a reused fingerprint alone, or convert supposedly equivalent units.
            if ($activity->template_snapshot !== $anchor->template_snapshot || $candidate !== $field || ($reading['unit'] ?? $candidate['unit'] ?? null) !== $unit) {
                $excluded++;

                continue;
            }
            $raw = $reading['value'] ?? null;
            $valid = ! $incomplete && $raw !== null && $raw !== '' && is_numeric($raw) && is_finite((float) $raw);
            $date = $activity->measured_on?->format('Y-m-d');
            $rows[] = ['activity' => $activity, 'date' => $date, 'raw' => $raw, 'value' => $valid && $date ? (float) $raw : null,
                'gap' => $raw === null || $raw === '' ? 'Belum diukur' : ($valid && $date ? null : 'Tidak diplot: angka / tanggal / konteks belum lengkap')];
        }
        usort($rows, fn ($a, $b) => strcmp($a['date'] ?? '', $b['date'] ?? '') ?: $a['activity']->id <=> $b['activity']->id);
        $valid = array_values(array_filter($rows, fn ($r) => $r['value'] !== null));
        $dates = array_values(array_unique(array_column($valid, 'date')));
        $gaps = [];
        for ($i = 1; $i < count($dates); $i++) {
            $gaps[] = (int) CarbonImmutable::parse($dates[$i - 1], 'UTC')->diffInDays(CarbonImmutable::parse($dates[$i], 'UTC'));
        }
        $chart = $this->chart($valid);

        return compact('field', 'unit', 'rows', 'excluded', 'incomplete', 'truncated', 'dates', 'chart') + [
            'count' => count($valid), 'missing' => count($rows) - count($valid), 'max_gap' => $gaps ? max($gaps) : null,
            'minimum' => $valid ? min(array_column($valid, 'value')) : null,
            'maximum' => $valid ? max(array_column($valid, 'value')) : null,
        ];
    }

    private function chart(array $rows): array
    {
        if (! $rows) {
            return [];
        }
        // Plot literal source calendar dates, never invented intraday timestamps.
        $days = array_map(fn ($r) => CarbonImmutable::parse($r['date'], 'UTC')->getTimestamp() / 86400, $rows);
        $first = min($days);
        $span = max($days) - $first;
        $values = array_column($rows, 'value');
        // Normalize before subtraction to avoid overflow for valid extreme floats.
        $scale = max(abs(min($values)), abs(max($values)), 1);
        $low = min($values) / $scale;
        $range = max($values) / $scale - $low;

        return array_map(fn ($row, $i) => $row + [
            'x' => round($span ? 54 + (($days[$i] - $first) / $span) * 612 : 360, 2),
            'y' => round($range ? 200 - (($row['value'] / $scale - $low) / $range) * 160 : 120, 2),
        ], $rows, array_keys($rows));
    }
}
