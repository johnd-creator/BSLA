<?php

namespace App\Services;

use Carbon\CarbonImmutable;
use Illuminate\Validation\ValidationException;

class ReliabilityTiming
{
    public function instant(?string $value, string $field): ?CarbonImmutable
    {
        if ($value === null || trim($value) === '') {
            return null;
        }
        if (! preg_match('/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2})$/D', $value)) {
            throw ValidationException::withMessages([$field => 'Gunakan waktu ISO-8601 lengkap dengan zona, contoh 2026-01-15T08:30:00+07:00. Tanggal saja tidak diberi jam buatan.']);
        }
        // RFC 3339 -00:00 means the local offset is unknown, not verified UTC.
        if (str_ends_with($value, '-00:00')) {
            throw ValidationException::withMessages([$field => 'Offset -00:00 berarti zona belum diketahui. Gunakan Z/+00:00 hanya bila UTC terverifikasi, atau offset sumber yang benar.']);
        }
        try {
            $time = CarbonImmutable::createFromFormat('!Y-m-d\TH:i:sP', $value);
            $errors = CarbonImmutable::getLastErrors();
            $offset = substr($value, -6);
            if (($errors !== false && ($errors['warning_count'] || $errors['error_count'])) || $time->isFuture()
                || ($value[-1] !== 'Z' && (abs((int) substr($offset, 0, 3)) > 14 || (int) substr($offset, 4, 2) > 59 || (abs((int) substr($offset, 0, 3)) === 14 && substr($offset, 4, 2) !== '00')))) {
                throw new \RuntimeException('Invalid instant');
            }

            return $time->utc();
        } catch (\Throwable) {
            throw ValidationException::withMessages([$field => 'Waktu invalid atau di masa depan. Periksa tanggal, jam dan offset zona.']);
        }
    }

    public function intervals(?string $text, ?CarbonImmutable $failure, ?CarbonImmutable $restored): array
    {
        $intervals = [];
        foreach (preg_split('/\r?\n/', trim($text ?? ''), -1, PREG_SPLIT_NO_EMPTY) as $line) {
            $parts = array_map('trim', explode(' | ', $line));
            if (count($parts) !== 2 || count($intervals) >= 20) {
                throw ValidationException::withMessages(['active_intervals_text' => 'Maksimal 20 interval, satu baris per interval: awal | akhir.']);
            }
            $start = $this->instant($parts[0], 'active_intervals_text');
            $end = $this->instant($parts[1], 'active_intervals_text');
            if (! $start || ! $end || $end->lt($start) || ($failure && $start->lt($failure)) || ($restored && $end->gt($restored))) {
                throw ValidationException::withMessages(['active_intervals_text' => 'Interval harus lengkap, urut, tidak sebelum failure atau sesudah kembali siap.']);
            }
            $intervals[] = ['start' => $start->toIso8601String(), 'end' => $end->toIso8601String(), 'seconds' => (int) $start->diffInSeconds($end)];
        }
        usort($intervals, fn ($a, $b) => strcmp($a['start'], $b['start']));
        foreach ($intervals as $i => $interval) {
            if ($i && ($interval['start'] < $intervals[$i - 1]['end'] || $interval === $intervals[$i - 1])) {
                throw ValidationException::withMessages(['active_intervals_text' => 'Interval berulang atau tumpang tindih. Jangan menjumlahkan waktu kru paralel.']);
            }
        }

        return $intervals;
    }
}
