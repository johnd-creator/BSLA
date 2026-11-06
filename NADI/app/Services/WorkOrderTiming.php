<?php

namespace App\Services;

use DateTimeImmutable;
use Throwable;

class WorkOrderTiming
{
    private static function clock(?string $value): array
    {
        if ($value === null || $value === '') {
            return ['state' => 'MISSING', 'date' => null];
        }
        if (! preg_match('/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/D', $value)) {
            return ['state' => preg_match('/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?$/D', $value) ? 'NAIVE' : 'INVALID', 'date' => null];
        }
        try {
            $date = new DateTimeImmutable($value);
            $errors = DateTimeImmutable::getLastErrors();
            if ($errors && ($errors['warning_count'] || $errors['error_count'])) {
                return ['state' => 'INVALID', 'date' => null];
            }

            return ['state' => 'VALID', 'date' => $date];
        } catch (Throwable) {
            return ['state' => 'INVALID', 'date' => null];
        }
    }

    public static function fromRecord(array $record): array
    {
        $start = self::clock($record['actual_start'] ?? null);
        $finish = self::clock($record['actual_finish'] ?? null);
        $state = 'NOT_CLOSED';
        $hours = null;
        if (($record['status'] ?? null) === 'CLOSE') {
            $state = $start['state'] !== 'VALID' ? $start['state'].'_ACTUAL_START' : ($finish['state'] !== 'VALID' ? $finish['state'].'_ACTUAL_FINISH' : 'AVAILABLE');
            if ($state === 'AVAILABLE') {
                $seconds = (float) $finish['date']->format('U.u') - (float) $start['date']->format('U.u');
                $state = $seconds < 0 ? 'INVALID_ACTUAL_ORDER' : 'AVAILABLE';
                $hours = $seconds < 0 ? null : $seconds / 3600;
            }
            foreach (['START', 'FINISH'] as $name) {
                if ($state === 'MISSING_ACTUAL_'.$name) {
                    $reasons = array_map(fn ($reason) => $reason.'_ACTUAL_'.$name, ['INVALID', 'NAIVE', 'UNAVAILABLE']);
                    if (in_array($record['actual_timing_state'] ?? null, $reasons, true)) {
                        $state = $record['actual_timing_state'];
                        if ($name === 'START') {
                            $start['state'] = explode('_', $state, 2)[0];
                        } else {
                            $finish['state'] = explode('_', $state, 2)[0];
                        }
                    }
                    break;
                }
            }
        }
        $message = match ($state) {
            'AVAILABLE' => 'Dihitung dari actual finish dikurangi actual start.',
            'NOT_CLOSED' => 'Durasi final belum dihitung karena status sumber bukan CLOSE.',
            'INVALID_ACTUAL_ORDER' => 'Actual finish lebih awal daripada actual start. Durasi tidak dihitung.',
            'NAIVE_ACTUAL_START', 'NAIVE_ACTUAL_FINISH' => 'Zona waktu actual timestamp belum jelas. Durasi tidak dihitung.',
            'INVALID_ACTUAL_START', 'INVALID_ACTUAL_FINISH' => 'Actual timestamp tidak valid. Durasi tidak dihitung.',
            'UNAVAILABLE_ACTUAL_START', 'UNAVAILABLE_ACTUAL_FINISH' => 'Bukti actual timestamp belum tersedia. Durasi tidak dihitung.',
            default => 'Actual start/finish belum lengkap atau belum tersedia. Durasi tidak dihitung.',
        };

        return ['state' => $state, 'duration_hours' => $hours, 'message' => $message, 'start_state' => $start['state'], 'finish_state' => $finish['state']];
    }
}
