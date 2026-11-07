<?php

namespace App\Services;

use Illuminate\Support\Arr;
use Illuminate\Support\Facades\Http;
use RuntimeException;
use Symfony\Component\HttpKernel\Exception\HttpExceptionInterface;

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
        return $this->assetPage('assets', $query);
    }

    public function inventory(array $query): array
    {
        return $this->assetPage('assets/inventory', $query, true);
    }

    private function inventoryAsset(array $data): array
    {
        $asset = $this->asset($data);
        if (! in_array($data['hierarchy_category'] ?? null, ['system', 'equipment', 'component', 'part', 'unknown'], true)
            || ! in_array($data['scope_basis'] ?? null, ['DIRECT_SOURCE_UNIT', 'SOURCE_PARENT_CHAIN', 'SOURCE_ANCESTOR_CONTEXT'], true)
            || ! is_bool($data['registered'] ?? null)) {
            throw new RuntimeException('Invalid inventory asset.');
        }

        return [...$asset, ...Arr::only($data, ['hierarchy_category', 'scope_basis', 'registered'])];
    }

    public function inventoryDetail(string $id): array
    {
        $asset = $this->inventoryAsset($this->get('assets/inventory/'.rawurlencode($id)));
        if ($asset['canonical_id'] !== $id) {
            throw new RuntimeException('Asset identity mismatch.');
        }

        return $asset;
    }

    private function assetPage(string $path, array $query, bool $inventory = false): array
    {
        $data = $this->get($path, [...$query, 'limit' => 25, 'site_code' => 'BSR', 'organization_code' => 'IP']);
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

        return ['items' => array_map($inventory ? $this->inventoryAsset(...) : $this->asset(...), $data['items']), 'meta' => Arr::only($meta, ['total', 'offset', 'limit', 'has_more'])];
    }

    public function inventorySummary(): array
    {
        $data = $this->get('assets/inventory-summary', ['site_code' => 'BSR', 'organization_code' => 'IP']);
        $scope = $data['scope'] ?? [];
        $counts = $data['counts'] ?? [];
        $coverage = $data['coverage'] ?? [];
        $classification = $data['classification'] ?? [];
        if (! is_array($scope) || ! is_array($counts) || ! is_array($coverage) || ! is_array($classification)
            || ($scope['site_code'] ?? null) !== 'BSR' || ($scope['organization_code'] ?? null) !== 'IP'
            || ($scope['unit'] ?? null) !== 'CS01' || ($scope['population'] ?? null) !== 'COLLECTED_HIERARCHY') {
            throw new RuntimeException('Invalid inventory scope.');
        }
        foreach (['total', 'equipment', 'component', 'part', 'unknown', 'system'] as $key) {
            if (! is_int($counts[$key] ?? null) || $counts[$key] < 0) {
                throw new RuntimeException('Invalid inventory count.');
            }
        }
        if ($counts['total'] !== $counts['equipment'] + $counts['component'] + $counts['part'] + $counts['unknown'] + $counts['system']
            || ($classification['unknown_count'] ?? null) !== $counts['unknown']
            || ($classification['basis'] ?? null) !== 'EXACT_SOURCE_ID_WORKBOOK_ROLE'
            || ($classification['status'] ?? null) !== 'INDICATIVE_DOCUMENT_ROLE') {
            throw new RuntimeException('Invalid inventory classification.');
        }
        $baselineComplete = $coverage['full_source_baseline_complete'] ?? null;
        $pending = $coverage['pending_projection'] ?? 0;
        $complete = ($coverage['state'] ?? null) === 'COMPLETE_AS_OF_MANUAL_SCAN';
        if (! is_bool($baselineComplete) || ! is_int($pending) || $pending < 0
            || ! in_array($coverage['state'] ?? null, ['PARTIAL', 'COMPLETE_AS_OF_MANUAL_SCAN'], true)
            || $complete !== ($baselineComplete && $pending === 0)
            || ! array_key_exists('last_completed_at', $coverage)
            || ($coverage['last_completed_at'] !== null && (! is_string($coverage['last_completed_at'])
                || ! preg_match('/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/', $coverage['last_completed_at'])))
            || ($baselineComplete && $coverage['last_completed_at'] === null)) {
            throw new RuntimeException('Invalid inventory coverage.');
        }

        return [
            ...Arr::only($counts, ['total', 'equipment', 'component', 'part', 'unknown', 'system']),
            'complete' => $complete,
            'pending_projection' => $pending,
            'last_completed_at' => $coverage['last_completed_at'],
        ];
    }

    public function detail(string $id): array
    {
        $asset = $this->asset($this->get('assets/'.rawurlencode($id)));
        if ($asset['canonical_id'] !== $id) {
            throw new RuntimeException('Asset identity mismatch.');
        }

        return $asset;
    }

    public function historyAsset(string $id): array
    {
        try {
            return $this->inventoryDetail($id);
        } catch (HttpExceptionInterface $error) {
            if ($error->getStatusCode() !== 404) {
                throw $error;
            }

            return [...$this->detail($id), 'registered' => true];
        }
    }

    /** Bounded Registry context, never a total history or a score. */
    public function assetContext(string $asset): array
    {
        $data = $this->get('assets/'.rawurlencode($asset).'/context');
        if (! is_array($data['asset'] ?? null) || $this->asset($data['asset'])['canonical_id'] !== $asset) {
            throw new RuntimeException('Asset context identity mismatch.');
        }
        $fields = [
            'maintenance' => ['equipment_id', 'work_order_id', 'description', 'event_type', 'status', 'actual_start', 'source_changed_at'],
            'fmea' => ['asset_ref', 'source_number', 'description', 'lifecycle_status', 'status_changed_at', 'source_updated_at'],
            'health' => ['asset_ref', 'description', 'lifecycle_status', 'status_changed_at', 'source_updated_at', 'source_created_at'],
            'overhauls' => ['asset_ref', 'source_number', 'lifecycle_status', 'actual_start_at', 'planned_start_at'],
        ];
        $context = [];
        foreach ($fields as $section => $allowed) {
            if (! is_array($data[$section] ?? null) || ! array_is_list($data[$section]) || count($data[$section]) > 5) {
                throw new RuntimeException('Invalid bounded asset context.');
            }
            $seen = [];
            $context[$section] = [];
            foreach ($data[$section] as $row) {
                if (! is_array($row) || ($row['site_code'] ?? null) !== 'BSR' || ($row['organization_code'] ?? null) !== 'IP'
                    || ($row[$section === 'maintenance' ? 'equipment_id' : 'asset_ref'] ?? null) !== $asset
                    || ! is_string($row['canonical_id'] ?? null) || $row['canonical_id'] === '' || isset($seen[$row['canonical_id']])) {
                    throw new RuntimeException('Invalid asset context scope or identity.');
                }
                $seen[$row['canonical_id']] = true;
                $item = Arr::only($row, ['canonical_id', ...$allowed]);
                foreach ($item as $value) {
                    if ($value !== null && ! is_string($value)) {
                        throw new RuntimeException('Invalid asset context field.');
                    }
                }
                $context[$section][] = $item;
            }
        }

        return $context;
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

    public function workOrders(array $query, bool $inventory = false): array
    {
        if ($inventory && empty($query['asset_ref'])) {
            throw new RuntimeException('Inventory WO reads require an exact asset.');
        }
        $year = $query['year'] ?? null;
        if ($year !== null) {
            if (empty($query['asset_ref'])) {
                throw new RuntimeException('Annual WO reads require an exact asset.');
            }
            $data = $this->get('asset-work-orders/year', [...$query, 'limit' => 25, 'population' => $inventory ? 'COLLECTED_HIERARCHY' : 'REGISTRY']);
            $this->annualScope($data, $query['asset_ref'], $inventory);
            if (($data['selected_year'] ?? null) !== (string) $year) {
                throw new RuntimeException('Annual WO year mismatch.');
            }
        } else {
            $data = $this->get($inventory ? 'inventory-maintenance-events' : 'maintenance-events', [...$query, 'limit' => 25]);
        }
        if ($year === null && $inventory && (($data['scope']['population'] ?? null) !== 'COLLECTED_HIERARCHY'
            || ($data['scope']['asset_ref'] ?? null) !== $query['asset_ref']
            || ($data['scope']['site_code'] ?? null) !== 'BSR'
            || ($data['scope']['organization_code'] ?? null) !== 'IP'
            || ($data['scope']['date_basis'] ?? null) !== 'ACTUAL_START_OR_SOURCE_CHANGED')) {
            throw new RuntimeException('Invalid inventory WO scope.');
        }
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
            $item = array_fill_keys(['canonical_id', 'equipment_id', 'work_order_id', 'event_type', 'status', 'actual_start', 'actual_finish', 'source_changed_at', 'failure_code'], null);
            $item = array_replace($item, Arr::only($record, array_keys($item)));
            $item['description'] = $record['description'] ?? null;
            $item['actual_timing_state'] = $record['actual_timing_state'] ?? null;
            $classification = $record['classification'] ?? [];
            $sourceDetail = $record['source_detail'] ?? [];
            if (! is_array($classification) || ! is_array($sourceDetail)) {
                throw new RuntimeException('Invalid work order evidence.');
            }
            foreach (['raw_work_type', 'canonical_category', 'state', 'origin', 'confidence'] as $field) {
                $item['classification_'.$field] = $classification[$field] ?? null;
            }
            $item['reported_at'] = $sourceDetail['reported_at'] ?? null;
            $item['work_order_number'] = $record['source_detail']['work_order_number'] ?? null;
            $item['asset_number'] = $record['source_detail']['asset_number'] ?? null;
            foreach ($item as $value) {
                if ($value !== null && ! is_string($value)) {
                    throw new RuntimeException('Invalid work order field.');
                }
            }

            return $item;
        }, $data['items']);

        $seen = [];
        foreach ($items as $item) {
            if ($year !== null) {
                $actual = $item['actual_start'];
                if ($year === 'unknown' ? $actual !== null : (! is_string($actual)
                    || ! preg_match('/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/', $actual)
                    || (int) (new \DateTimeImmutable($actual))->setTimezone(new \DateTimeZone('Asia/Jakarta'))->format('Y') !== (int) $year)) {
                    throw new RuntimeException('Work order actual year mismatch.');
                }
            }
            if (($query['asset_ref'] ?? null) !== null && $item['equipment_id'] !== $query['asset_ref']) {
                throw new RuntimeException('Work order asset mismatch.');
            }
            if (($query['status'] ?? null) !== null && $item['status'] !== $query['status']) {
                throw new RuntimeException('Work order status mismatch.');
            }
            // Reject ambiguous pages rather than silently double-counting or dropping records.
            foreach (['canonical_id', 'work_order_id'] as $field) {
                $id = $item[$field];
                if ($id !== null && $id !== '') {
                    if (isset($seen[$field][$id])) {
                        throw new RuntimeException('Duplicate work order identity.');
                    }
                    $seen[$field][$id] = true;
                }
            }
        }

        return ['items' => $items, 'meta' => Arr::only($meta, ['total', 'offset', 'limit', 'has_more'])];
    }

    private function annualScope(array $data, string $asset, bool $inventory): void
    {
        $scope = $data['scope'] ?? [];
        foreach (['asset_ref' => $asset, 'population' => $inventory ? 'COLLECTED_HIERARCHY' : 'REGISTRY',
            'site_code' => 'BSR', 'organization_code' => 'IP', 'date_basis' => 'ACTUAL_START',
            'time_zone' => 'Asia/Jakarta', 'count_basis' => 'UNIQUE_WORK_ORDER_ID'] as $key => $value) {
            if (($scope[$key] ?? null) !== $value) {
                throw new RuntimeException('Invalid annual WO scope.');
            }
        }
    }

    public function annualWorkOrders(string $asset, bool $inventory): array
    {
        $data = $this->get('asset-work-orders/annual-summary', ['asset_ref' => $asset, 'population' => $inventory ? 'COLLECTED_HIERARCHY' : 'REGISTRY']);
        $this->annualScope($data, $asset, $inventory);
        $counts = $data['counts'] ?? [];
        foreach (['record_count', 'work_order_count', 'duplicate_work_order_count', 'duplicate_record_count', 'missing_identity_record_count', 'dated_work_order_count', 'unknown_date_work_order_count'] as $key) {
            if (! is_int($counts[$key] ?? null) || $counts[$key] < 0) {
                throw new RuntimeException('Invalid annual WO counts.');
            }
        }
        if (($data['availability_state'] ?? null) !== 'REQUIRES_VALIDATED_DCS_HISTORY'
            || ! is_array($data['years'] ?? null) || ! array_is_list($data['years']) || count($data['years']) > 9999
            || ! is_array($data['unknown_year'] ?? null) || ! array_key_exists('year', $data['unknown_year'])
            || $data['unknown_year']['year'] !== null) {
            throw new RuntimeException('Invalid annual WO summary.');
        }
        $previous = 10000;
        $total = 0;
        foreach ([...$data['years'], $data['unknown_year']] as $bucket) {
            if (! is_array($bucket) || ! is_int($bucket['work_orders'] ?? null) || $bucket['work_orders'] < 0
                || ! array_key_exists('year', $bucket)) {
                throw new RuntimeException('Invalid annual WO bucket.');
            }
            if ($bucket['year'] !== null) {
                if (! is_int($bucket['year']) || $bucket['year'] < 1 || $bucket['year'] >= $previous || $bucket['work_orders'] === 0) {
                    throw new RuntimeException('Invalid annual WO year.');
                }
                $previous = $bucket['year'];
                $total += $bucket['work_orders'];
            }
            foreach (['work_types', 'statuses'] as $dimension) {
                if (! is_array($bucket[$dimension] ?? null) || ! array_is_list($bucket[$dimension])) {
                    throw new RuntimeException('Invalid annual WO distribution.');
                }
                $sum = 0;
                $seen = [];
                foreach ($bucket[$dimension] as $group) {
                    if (! is_array($group) || ! array_key_exists('value', $group)
                        || ($group['value'] !== null && (! is_string($group['value']) || trim($group['value']) === ''))
                        || ! is_int($group['count'] ?? null) || $group['count'] <= 0
                        || in_array($group['value'], $seen, true)) {
                        throw new RuntimeException('Invalid annual WO distribution entry.');
                    }
                    $seen[] = $group['value'];
                    $sum += $group['count'];
                }
                if ($sum !== $bucket['work_orders']) {
                    throw new RuntimeException('Annual WO distribution does not reconcile.');
                }
            }
        }
        if (count(array_filter($data['years'], fn ($bucket) => $bucket['year'] === null)) > 0
            || $total !== $counts['dated_work_order_count']
            || $data['unknown_year']['work_orders'] !== $counts['unknown_date_work_order_count']
            || $counts['work_order_count'] !== $total + $counts['unknown_date_work_order_count'] + $counts['duplicate_work_order_count']
            || $counts['record_count'] !== $total + $counts['unknown_date_work_order_count'] + $counts['duplicate_record_count'] + $counts['missing_identity_record_count']
            || $counts['duplicate_record_count'] < 2 * $counts['duplicate_work_order_count']) {
            throw new RuntimeException('Annual WO counts do not reconcile.');
        }

        return Arr::only($data, ['counts', 'years', 'unknown_year']);
    }

    public function workOrder(string $reference, ?string $event, ?string $asset = null, bool $inventory = false): array
    {
        $page = $this->workOrders(array_filter(['work_order_id' => $reference, 'offset' => 0, 'asset_ref' => $asset], fn ($value) => $value !== null), $inventory);
        if ($page['meta']['total'] === 0) {
            abort(404, 'Work Order tidak ditemukan pada cakupan yang dipilih.');
        }
        if ($page['meta']['total'] !== 1 || count($page['items']) !== 1 || $page['items'][0]['work_order_id'] !== $reference
            || ($event !== null && $page['items'][0]['canonical_id'] !== $event)) {
            throw new RuntimeException('Ambiguous work order identity.');
        }

        return $page['items'][0];
    }
}
