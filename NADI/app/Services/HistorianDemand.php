<?php

namespace App\Services;

use Illuminate\Support\Facades\Http;
use Throwable;

/** Internal lease writes only; no source writes, source URLs, DB or persisted samples. */
class HistorianDemand
{
    private const QUALITY = ['good', 'bad', 'uncertain', 'no_data', 'invalid', 'read_error', 'stale'];

    public function configured(): bool
    {
        return $this->base() !== null;
    }

    public function call(string $action, array $payload): ?array
    {
        if (! in_array($action, ['subscribe', 'heartbeat', 'release', 'history'], true) || ($base = $this->base()) === null) {
            return null;
        }
        try {
            $response = Http::acceptJson()->connectTimeout(1)->timeout(3)
                ->withOptions(['stream' => true, 'allow_redirects' => false])
                ->post($base.'/v1/historian/'.$action, $payload);
            $stream = $response->toPsrResponse()->getBody();
            try {
                if (! $response->successful()) {
                    return null;
                }
                $body = '';
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
            if (! is_array($data)) {
                return null;
            }
            if ($action === 'release') {
                return ($data['released'] ?? null) === true ? ['released' => true] : null;
            }
            if ($action === 'history') {
                return $this->history($data, $payload);
            }
            $result = $this->snapshot($data);
            if ($result !== null && (($action === 'subscribe' && $result['page'] !== ($payload['page'] ?? null))
                || ($action === 'heartbeat' && $result['subscription'] !== ($payload['subscription'] ?? null)))) {
                return null;
            }

            return $result;
        } catch (Throwable) {
            return null;
        }
    }

    private function base(): ?string
    {
        $base = rtrim((string) config('historian.url'), '/');
        $url = parse_url($base);
        // No DNS, credentials, remote IP, arbitrary path or user-controlled target.
        if (! $url || ($url['scheme'] ?? null) !== 'http' || ($url['host'] ?? null) !== '127.0.0.1'
            || ! isset($url['port']) || $url['port'] < 1024 || $url['port'] > 65535
            || isset($url['user']) || isset($url['pass']) || isset($url['query']) || isset($url['fragment']) || isset($url['path'])) {
            return null;
        }

        return $base;
    }

    private function timestamp(mixed $value): ?int
    {
        if (! is_string($value) || strlen($value) > 40 || ! preg_match('/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/D', $value)) {
            return null;
        }
        $stamp = strtotime($value);

        return $stamp === false ? null : $stamp;
    }

    private function number(mixed $value): bool
    {
        return (is_int($value) || is_float($value)) && is_finite((float) $value);
    }

    private function snapshot(array $data): ?array
    {
        $page = $data['page'] ?? null;
        $pages = config('historian.pages', []);
        if (! is_string($page) || ! isset($pages[$page]) || ($data['source_mode'] ?? null) !== 'simulation'
            || ! is_string($data['subscription'] ?? null) || ! preg_match('/^[a-f0-9]{48}$/D', $data['subscription'])
            || ($generated = $this->timestamp($data['generated_at'] ?? null)) === null || abs(time() - $generated) > 5
            || ! is_int($data['sample_seconds'] ?? null) || $data['sample_seconds'] < 3 || $data['sample_seconds'] > 5
            || ! is_int($data['lease_seconds'] ?? null) || $data['lease_seconds'] < 15 || $data['lease_seconds'] > 60
            || ! is_int($data['grace_seconds'] ?? null) || $data['grace_seconds'] < 0 || $data['grace_seconds'] > 30
            || ! is_bool($data['context_enabled'] ?? null) || ! in_array($data['status'] ?? null, ['current', 'partial', 'no_data', 'degraded'], true)
            || ! is_array($data['tags'] ?? null) || ! array_is_list($data['tags']) || count($data['tags']) !== count($pages[$page]['tags'])) {
            return null;
        }
        $tags = [];
        foreach ($data['tags'] as $row) {
            if (! is_array($row) || ! is_string($row['tag'] ?? null) || ! in_array($row['tag'], $pages[$page]['tags'], true) || isset($tags[$row['tag']])
                || ! is_string($row['label'] ?? null) || strlen($row['label']) > 160 || ! is_string($row['unit'] ?? null) || strlen($row['unit']) > 40
                || count(array_intersect(['value', 'source_at', 'received_at', 'age_seconds'], array_keys($row))) !== 4
                || ! in_array($row['quality'] ?? null, self::QUALITY, true) || ! in_array($row['source_quality'] ?? null, self::QUALITY, true)
                || ! in_array($row['freshness'] ?? null, ['fresh', 'stale', 'no_data'], true)
                || ($row['value'] !== null && ! $this->number($row['value']))
                || ($row['age_seconds'] !== null && (! $this->number($row['age_seconds']) || $row['age_seconds'] < 0))
                || ($row['source_at'] !== null && ($this->timestamp($row['source_at']) === null || $this->timestamp($row['source_at']) > time() + 1))
                || ($row['received_at'] !== null && ($this->timestamp($row['received_at']) === null || $this->timestamp($row['received_at']) > time() + 1))) {
                return null;
            }
            $sourceAt = $this->timestamp($row['source_at']);
            if (($sourceAt === null) !== ($row['age_seconds'] === null)
                || ($sourceAt !== null && abs(max(0, time() - $sourceAt) - $row['age_seconds']) > 3)
                || ($row['value'] !== null && ($row['quality'] !== 'good' || $row['source_quality'] !== 'good' || $row['freshness'] !== 'fresh' || $sourceAt === null
                    || time() - $sourceAt >= $data['sample_seconds'] * 3 || $row['age_seconds'] >= $data['sample_seconds'] * 3))) {
                return null;
            }
            $expectedFreshness = $sourceAt === null ? 'no_data' : ($row['age_seconds'] < $data['sample_seconds'] * 3 ? 'fresh' : 'stale');
            if ($row['freshness'] !== $expectedFreshness || ($row['quality'] === 'good' && $row['value'] === null)
                || ($sourceAt !== null && ($row['received_at'] === null || $sourceAt > $this->timestamp($row['received_at']) + 1))) {
                return null;
            }
            $tags[$row['tag']] = array_intersect_key($row, array_flip(['tag', 'label', 'unit', 'value', 'source_at', 'received_at', 'source_quality', 'quality', 'freshness', 'age_seconds']));
        }
        $good = count(array_filter($tags, fn ($row) => $row['quality'] === 'good'));
        $hasSource = count(array_filter($tags, fn ($row) => $row['source_at'] !== null));
        $expectedStatus = $good === count($tags) ? 'current' : ($good > 0 ? 'partial' : ($hasSource === 0 ? 'no_data' : 'degraded'));
        if ($data['status'] !== $expectedStatus) {
            return null;
        }
        $clean = array_intersect_key($data, array_flip(['subscription', 'page', 'source_mode', 'generated_at', 'sample_seconds', 'lease_seconds', 'grace_seconds', 'context_enabled', 'status']));
        $clean['tags'] = array_values($tags);

        return $clean;
    }

    private function history(array $data, array $request): ?array
    {
        $start = $this->timestamp($request['start'] ?? null);
        $end = $this->timestamp($request['end'] ?? null);
        if (($data['source_mode'] ?? null) !== 'simulation' || ($data['tag'] ?? null) !== ($request['tag'] ?? null)
            || $this->timestamp($data['start'] ?? null) !== $start || $this->timestamp($data['end'] ?? null) !== $end
            || ($data['limit'] ?? null) !== ($request['limit'] ?? null) || ($data['coverage'] ?? null) !== 'not_asserted'
            || ($stamp = $this->timestamp($data['generated_at'] ?? null)) === null || abs(time() - $stamp) > 5
            || ! is_array($data['points'] ?? null) || ! array_is_list($data['points']) || count($data['points']) > min(1000, $request['limit'] ?? 0)) {
            return null;
        }
        $points = [];
        $last = null;
        foreach ($data['points'] as $point) {
            $time = $this->timestamp($point['source_at'] ?? null);
            if (! is_array($point) || ! array_key_exists('value', $point) || ! in_array($point['quality'] ?? null, self::QUALITY, true)
                || $time === null || $time < $start || $time > $end || ($last !== null && $time <= $last)
                || ($point['value'] !== null && (! $this->number($point['value']) || $point['quality'] !== 'good'))) {
                return null;
            }
            $points[] = array_intersect_key($point, array_flip(['value', 'source_at', 'quality']));
            $last = $time;
        }

        return ['source_mode' => 'simulation', 'tag' => $data['tag'], 'start' => $data['start'], 'end' => $data['end'], 'coverage' => 'not_asserted', 'points' => $points];
    }
}
