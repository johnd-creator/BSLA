<?php

namespace App\Services;

use DateTimeImmutable;
use Illuminate\Support\Facades\Http;
use Throwable;

/** Read only the shared RAM service. Never collect, persist, or fall back to the legacy API. */
class CemsLive
{
    private const QUALITY = ['good', 'read_error', 'invalid', 'dependency_missing', 'stale', 'offline', 'unknown'];

    public function read(?string $parameter = null): array
    {
        $snapshot = $this->get('/v1/cems/snapshot');
        $unavailable = ['snapshot' => null, 'history' => null, 'parameter' => null];
        if (! $snapshot || ! array_key_exists('last_cycle_at', $snapshot) || ! in_array($snapshot['source_mode'] ?? null, ['plc', 'simulation'], true)
            || ! in_array($snapshot['status'] ?? null, ['warming_up', 'live', 'degraded', 'offline'], true)
            || ($snapshot['poll_interval_seconds'] ?? null) !== 5 || ($snapshot['retention_seconds'] ?? null) !== 21600
            || ! is_string($snapshot['stack_id'] ?? null) || strlen($snapshot['stack_id']) > 80
            || ! $this->date($snapshot['generated_at'] ?? null) || ! $this->date($snapshot['cache_started_at'] ?? null)
            || ! $this->nullableDate($snapshot['last_cycle_at'] ?? null)
            || ! is_int($snapshot['samples_retained'] ?? null) || $snapshot['samples_retained'] < 0 || $snapshot['samples_retained'] > 138240
            || ! is_array($snapshot['parameters'] ?? null) || ! array_is_list($snapshot['parameters']) || count($snapshot['parameters']) > 32) {
            return $unavailable;
        }
        $now = microtime(true);
        $generated = $this->timestamp($snapshot['generated_at']);
        if ($generated > $now || $now - $generated >= 15
            || $this->timestamp($snapshot['cache_started_at']) > $generated
            || ($snapshot['last_cycle_at'] !== null && $this->timestamp($snapshot['last_cycle_at']) > $generated)) {
            return $unavailable;
        }
        $parameters = [];
        foreach ($snapshot['parameters'] as $row) {
            if (! is_array($row) || count(array_intersect(['value_raw', 'value_final', 'age_seconds', 'observed_at', 'last_good_at'], array_keys($row))) !== 5 || ! is_string($row['parameter_code'] ?? null) || ! preg_match('/^[A-Za-z0-9_.-]{1,64}$/D', $row['parameter_code'])
                || isset($parameters[$row['parameter_code']]) || ! is_string($row['name'] ?? null) || strlen($row['name']) > 160
                || ! is_string($row['unit'] ?? null) || strlen($row['unit']) > 40
                || ! in_array($row['quality'] ?? null, self::QUALITY, true)
                || (($row['value_final'] ?? null) !== null && ($row['quality'] !== 'good' || ($row['age_seconds'] ?? 15) >= 15))
                || ! $this->number($row['value_raw'] ?? null) || ! $this->number($row['value_final'] ?? null)
                || ! $this->number($row['age_seconds'] ?? null) || ($row['age_seconds'] ?? 0) < 0
                || ! $this->nullableDate($row['observed_at'] ?? null) || ! $this->nullableDate($row['last_good_at'] ?? null)) {
                return $unavailable;
            }
            $observed = $row['observed_at'] === null ? null : $this->timestamp($row['observed_at']);
            $lastGood = $row['last_good_at'] === null ? null : $this->timestamp($row['last_good_at']);
            if (($observed !== null && $observed > $generated) || ($lastGood !== null && $lastGood > $generated)) {
                return $unavailable;
            }
            if ($row['quality'] === 'good') {
                // age_seconds is monotonic source metadata, not proof of wall-clock
                // freshness. A good value also needs a real, current observation.
                if ($row['value_final'] === null || $observed === null || $row['age_seconds'] === null
                    || $now - $observed >= 15 || $row['age_seconds'] + ($now - $generated) >= 15
                    || abs(($generated - $observed) - $row['age_seconds']) > 2) {
                    return $unavailable;
                }
                $row['age_seconds'] = max($now - $observed, $row['age_seconds'] + ($now - $generated));
            }
            $parameters[$row['parameter_code']] = array_intersect_key($row, array_flip(['parameter_code', 'name', 'unit', 'value_raw', 'value_final', 'observed_at', 'last_good_at', 'quality', 'age_seconds']));
        }
        $snapshot = array_intersect_key($snapshot, array_flip(['stack_id', 'source_mode', 'poll_interval_seconds', 'retention_seconds', 'status', 'generated_at', 'last_cycle_at', 'cache_started_at', 'samples_retained']));
        $snapshot['parameters'] = array_values($parameters);
        $parameter = isset($parameters[$parameter ?? '']) ? $parameter : array_key_first($parameters);
        $history = $parameter === null ? null : $this->get('/v1/cems/history', ['parameter' => $parameter, 'limit' => 360]);
        if (! $history || ($history['parameter_code'] ?? null) !== $parameter || ($history['retention_seconds'] ?? null) !== 21600
            || ! is_bool($history['truncated'] ?? null) || ! is_array($history['points'] ?? null) || ! array_is_list($history['points']) || count($history['points']) > 360) {
            $history = null;
        } else {
            $points = [];
            foreach ($history['points'] as $point) {
                if (! is_array($point) || ! array_key_exists('value_final', $point) || ! $this->date($point['observed_at'] ?? null) || (($point['value_final'] ?? null) !== null && ($point['quality'] ?? null) !== 'good') || ! $this->number($point['value_final'] ?? null) || ! in_array($point['quality'] ?? null, self::QUALITY, true)) {
                    $history = null;
                    break;
                }
                $points[] = array_intersect_key($point, array_flip(['observed_at', 'value_final', 'quality']));
            }
            if ($history !== null) {
                $history = ['points' => $points, 'truncated' => $history['truncated']];
            }
        }

        return compact('snapshot', 'history', 'parameter');
    }

    public static function formatValue(?float $value): string
    {
        if ($value === null) {
            return '—';
        }
        if ($value === 0.0) {
            return '0';
        }

        return sprintf('%.8g', $value);
    }

    public function signals(array $parameters, ?string $sourceMode): ?array
    {
        if ($sourceMode === null) {
            return null;
        }
        $data = $this->get('/v1/cems/signals');
        if (! $data || ($data['source_mode'] ?? null) !== $sourceMode || ($data['feed_interval_seconds'] ?? null) !== 60
            || ($data['window_seconds'] ?? null) !== 60 || ($data['meaning'] ?? null) !== 'signal_data_only'
            || ! in_array($data['status'] ?? null, ['warming_up', 'current', 'stale'], true)
            || ! array_key_exists('generated_at', $data) || ! $this->nullableDate($data['generated_at'])
            || ! array_key_exists('feed_age_seconds', $data) || ! $this->number($data['feed_age_seconds']) || ($data['feed_age_seconds'] ?? 0) < 0
            || ! is_array($data['signals'] ?? null) || ! array_is_list($data['signals']) || count($data['signals']) > 32) {
            return null;
        }
        if ($data['status'] === 'current' && ($data['generated_at'] === null || $data['feed_age_seconds'] === null
            || abs(time() - strtotime($data['generated_at'])) >= 75 || $data['feed_age_seconds'] >= 75
            || abs((time() - strtotime($data['generated_at'])) - $data['feed_age_seconds']) > 5)) {
            return null;
        }
        $codes = array_column($parameters, 'parameter_code');
        $signals = [];
        foreach ($data['signals'] as $row) {
            if (! is_array($row) || ! in_array($row['parameter_code'] ?? null, $codes, true) || isset($signals[$row['parameter_code']])
                || ! array_key_exists('last_received_at', $row) || ! $this->nullableDate($row['last_received_at'])
                || ! is_int($row['good_samples_last_minute'] ?? null) || $row['good_samples_last_minute'] < 0 || $row['good_samples_last_minute'] > 13
                || ($row['expected_samples_per_minute'] ?? null) !== 12 || ! in_array($row['signal_state'] ?? null, ['receiving', 'no_recent_good_data'], true)) {
                return null;
            }
            $signals[$row['parameter_code']] = array_intersect_key($row, array_flip(['parameter_code', 'last_received_at', 'good_samples_last_minute', 'expected_samples_per_minute', 'signal_state']));
        }

        return ['status' => $data['status'], 'generated_at' => $data['generated_at'], 'feed_age_seconds' => $data['feed_age_seconds'], 'signals' => array_values($signals)];
    }

    private function number(mixed $value): bool
    {
        return $value === null || ((is_int($value) || is_float($value)) && is_finite((float) $value));
    }

    private function date(mixed $value): bool
    {
        if (! is_string($value) || ! preg_match('/^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(?:\.(\d{1,6}))?(Z|[+-](?:0\d|1[0-4]):[0-5]\d)$/D', $value, $parts)) {
            return false;
        }
        $zone = $parts[3] === 'Z' ? '+00:00' : $parts[3];
        if (substr($zone, 1, 2) === '14' && substr($zone, 4, 2) !== '00') {
            return false;
        }
        $parsed = DateTimeImmutable::createFromFormat('!Y-m-d\TH:i:s.uP', $parts[1].'.'.str_pad($parts[2], 6, '0').$zone);
        $errors = DateTimeImmutable::getLastErrors();

        return $parsed !== false && ($errors === false || ($errors['warning_count'] === 0 && $errors['error_count'] === 0));
    }

    private function timestamp(string $value): float
    {
        return (float) (new DateTimeImmutable($value))->format('U.u');
    }

    private function nullableDate(mixed $value): bool
    {
        return $value === null || $this->date($value);
    }

    private function get(string $path, array $query = []): ?array
    {
        $base = rtrim((string) config('services.cems_live.url'), '/');
        $url = parse_url($base);
        if (! $url || ! in_array($url['scheme'] ?? null, ['http', 'https'], true) || empty($url['host'])
            || isset($url['user']) || isset($url['pass']) || isset($url['query']) || isset($url['fragment'])) {
            return null;
        }
        try {
            $response = Http::acceptJson()->connectTimeout(1)->timeout(3)->withOptions(['stream' => true, 'allow_redirects' => false])->get($base.$path, $query);
            if (! $response->successful()) {
                $response->toPsrResponse()->getBody()->close();

                return null;
            }
            $stream = $response->toPsrResponse()->getBody();
            $body = '';
            try {
                while (! $stream->eof() && strlen($body) <= 1048576) {
                    $chunk = $stream->read(min(8192, 1048577 - strlen($body)));
                    if ($chunk === '') {
                        break;
                    }
                    $body .= $chunk;
                }
            } finally {
                $stream->close();
            }
            if (strlen($body) > 1048576) {
                return null;
            }
            $data = json_decode($body, true, 16, JSON_THROW_ON_ERROR);

            return is_array($data) ? $data : null;
        } catch (Throwable) {
            return null;
        }
    }
}
