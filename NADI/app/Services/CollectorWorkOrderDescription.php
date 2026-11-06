<?php

namespace App\Services;

use Illuminate\Support\Facades\Http;
use Throwable;

class CollectorWorkOrderDescription
{
    public function forRecord(array $record): ?string
    {
        $number = $record['work_order_number'] ?? null;
        $asset = $record['asset_number'] ?? null;
        if (! is_string($number) || ! is_string($asset) || strlen($number) > 100 || strlen($asset) > 160) {
            return null;
        }
        $base = rtrim((string) config('services.maximo_collector.url'), '/');
        $url = parse_url($base);
        if (! $url || ($url['scheme'] ?? null) !== 'http' || ! in_array($url['host'] ?? null, ['127.0.0.1', 'localhost', '::1', '[::1]'], true) || isset($url['user']) || isset($url['pass']) || isset($url['query']) || isset($url['fragment'])) {
            return null;
        }
        try {
            $response = Http::acceptJson()->connectTimeout(2)->timeout(8)->withOptions(['stream' => true, 'allow_redirects' => false])
                ->get($base.'/work-orders', ['q' => $number, 'equipment_id' => $asset, 'limit' => 25]);
            if (! $response->successful()) {
                return null;
            }
            $stream = $response->toPsrResponse()->getBody();
            $body = '';
            while (! $stream->eof() && strlen($body) <= 1048576) {
                $chunk = $stream->read(min(8192, 1048577 - strlen($body)));
                if ($chunk === '') {
                    break;
                }
                $body .= $chunk;
            }
            $stream->close();
            if (strlen($body) > 1048576) {
                return null;
            }
            $rows = json_decode($body, true, 32, JSON_THROW_ON_ERROR);
            if (! is_array($rows) || ! array_is_list($rows) || count($rows) > 25) {
                return null;
            }
            $matches = array_values(array_filter($rows, fn ($row) => is_array($row) && ($row['id'] ?? null) === $number && ($row['equipment_id'] ?? null) === $asset));
            if (count($matches) !== 1 || ! is_string($matches[0]['description'] ?? null)) {
                return null;
            }

            return $matches[0]['description'];
        } catch (Throwable) {
            return null;
        }
    }
}
