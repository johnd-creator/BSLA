<?php

namespace App\Services;

use Illuminate\Support\Arr;
use Illuminate\Support\Facades\Http;
use RuntimeException;

class ReliabilityMart
{
    private const FIELDS = ['canonical_id', 'contract_version', 'source_asset_number', 'description', 'status', 'location_ref', 'parent_asset_ref', 'site_code', 'organization_code', 'asset_type', 'plant', 'unit', 'source_updated_at'];

    private function get(string $path, array $query = []): array
    {
        $base = rtrim((string) config('services.reliability_mart.url'), '/');
        $url = parse_url($base);
        if (! $url || ! in_array($url['scheme'] ?? '', ['http', 'https'], true) || empty($url['host']) || isset($url['user']) || isset($url['pass']) || isset($url['query']) || isset($url['fragment'])) {
            throw new RuntimeException('Mart is not configured.');
        }
        $response = Http::acceptJson()->connectTimeout(2)->timeout(8)
            ->withOptions(['allow_redirects' => false, 'stream' => true])
            ->get($base.'/v1/reliability/'.$path, $query);
        if ($response->status() === 404) {
            abort(404, 'Asset tidak ditemukan.');
        }
        if (! $response->successful()) {
            throw new RuntimeException('Mart is unavailable.');
        }
        $body = $response->toPsrResponse()->getBody();
        $json = '';
        while (! $body->eof() && strlen($json) <= 1048576) {
            $chunk = $body->read(min(8192, 1048577 - strlen($json)));
            if ($chunk === '') {
                break;
            }
            $json .= $chunk;
        }
        $body->close();
        if (strlen($json) > 1048576) {
            throw new RuntimeException('Mart response exceeds limit.');
        }
        $data = json_decode($json, true, 32, JSON_THROW_ON_ERROR);
        if (! is_array($data)) {
            throw new RuntimeException('Invalid Mart response.');
        }

        return $data;
    }

    private function asset(array $data): array
    {
        if (! is_string($data['canonical_id'] ?? null) || ($data['site_code'] ?? null) !== 'BSR' || ($data['organization_code'] ?? null) !== 'IP') {
            throw new RuntimeException('Invalid asset scope.');
        }
        foreach (self::FIELDS as $field) {
            if (isset($data[$field]) && ! is_string($data[$field])) {
                throw new RuntimeException('Invalid asset field.');
            }
        }

        return Arr::only($data, self::FIELDS);
    }

    public function assets(array $query): array
    {
        $data = $this->get('assets', [...$query, 'limit' => 25, 'site_code' => 'BSR', 'organization_code' => 'IP']);
        if (! is_array($data['items'] ?? null) || count($data['items']) > 25 || ! is_array($data['meta'] ?? null)) {
            throw new RuntimeException('Invalid Mart page.');
        }
        $meta = $data['meta'];
        foreach (['total', 'offset', 'limit'] as $key) {
            if (! is_int($meta[$key] ?? null) || $meta[$key] < 0) {
                throw new RuntimeException('Invalid Mart pagination.');
            }
        }
        if (! is_bool($meta['has_more'] ?? null) || $meta['limit'] !== 25 || $meta['offset'] !== ($query['offset'] ?? 0)) {
            throw new RuntimeException('Invalid Mart pagination.');
        }

        return ['items' => array_map($this->asset(...), $data['items']), 'meta' => Arr::only($meta, ['total', 'offset', 'limit', 'has_more'])];
    }

    public function detail(string $id): array
    {
        $asset = $this->asset($this->get('assets/'.rawurlencode($id)));
        if ($asset['canonical_id'] !== $id) {
            throw new RuntimeException('Asset identity mismatch.');
        }

        return $asset;
    }

    public function waitingApproval(int $offset): array
    {
        $data = $this->get('maintenance-events', ['status' => 'WAPPR', 'offset' => $offset, 'limit' => 10, 'sort' => 'date_desc']);
        $meta = $data['meta'] ?? null;
        if (! is_array($data['items'] ?? null) || count($data['items']) > 10 || ! is_array($meta)
            || ! is_int($meta['total'] ?? null) || $meta['total'] < 0 || ($meta['offset'] ?? null) !== $offset
            || ($meta['limit'] ?? null) !== 10 || ! is_bool($meta['has_more'] ?? null)) {
            throw new RuntimeException('Invalid WAPPR page.');
        }
        $items = array_map(function (array $record): array {
            if (($record['status'] ?? null) !== 'WAPPR' || ($record['site_code'] ?? null) !== 'BSR'
                || ($record['organization_code'] ?? null) !== 'IP' || ! is_string($record['equipment_id'] ?? null)
                || strlen($record['equipment_id']) > 240 || preg_match('/[\\\\\/]/', $record['equipment_id'])) {
                throw new RuntimeException('Invalid WAPPR scope or status.');
            }
            $item = Arr::only($record, ['canonical_id', 'equipment_id', 'work_order_id', 'event_type', 'status', 'source_changed_at']);
            $item['work_order_number'] = $record['source_detail']['work_order_number'] ?? null;
            $item['asset_number'] = $record['source_detail']['asset_number'] ?? null;
            $item['raw_work_type'] = $record['classification']['raw_work_type'] ?? null;
            foreach ($item as $value) {
                if ($value !== null && ! is_string($value)) {
                    throw new RuntimeException('Invalid WAPPR field.');
                }
            }

            return $item;
        }, $data['items']);

        return ['items' => $items, 'meta' => Arr::only($meta, ['total', 'offset', 'limit', 'has_more'])];
    }

    public function workOrders(array $query): array
    {
        $data = $this->get('maintenance-events', [...$query, 'limit' => 25]);
        $meta = $data['meta'] ?? null;
        if (! is_array($data['items'] ?? null) || count($data['items']) > 25 || ! is_array($meta)
            || ! is_int($meta['total'] ?? null) || $meta['total'] < 0 || ($meta['offset'] ?? null) !== ($query['offset'] ?? 0)
            || ($meta['limit'] ?? null) !== 25 || ! is_bool($meta['has_more'] ?? null)) {
            throw new RuntimeException('Invalid work order page.');
        }
        $items = array_map(function (array $record): array {
            if (($record['site_code'] ?? null) !== 'BSR' || ($record['organization_code'] ?? null) !== 'IP'
                || ! is_string($record['canonical_id'] ?? null) || ! is_string($record['equipment_id'] ?? null)) {
                throw new RuntimeException('Invalid work order scope.');
            }
            $item = Arr::only($record, ['canonical_id', 'equipment_id', 'work_order_id', 'event_type', 'status', 'actual_start', 'actual_finish', 'source_changed_at']);
            $item['description'] = $record['description'] ?? null;
            $item['actual_timing_state'] = $record['actual_timing_state'] ?? null;
            $item['work_order_number'] = $record['source_detail']['work_order_number'] ?? null;
            $item['asset_number'] = $record['source_detail']['asset_number'] ?? null;
            foreach ($item as $value) {
                if ($value !== null && ! is_string($value)) {
                    throw new RuntimeException('Invalid work order field.');
                }
            }

            return $item;
        }, $data['items']);

        return ['items' => $items, 'meta' => Arr::only($meta, ['total', 'offset', 'limit', 'has_more'])];
    }

    public function workOrder(string $reference, ?string $event): array
    {
        $page = $this->workOrders(['work_order_id' => $reference, 'offset' => 0]);
        if ($page['meta']['total'] === 0) {
            abort(404, 'Work Order tidak ditemukan di Registry scope.');
        }
        if ($page['meta']['total'] !== 1 || count($page['items']) !== 1 || $page['items'][0]['work_order_id'] !== $reference
            || ($event !== null && $page['items'][0]['canonical_id'] !== $event)) {
            throw new RuntimeException('Ambiguous work order identity.');
        }

        return $page['items'][0];
    }
}
