<?php

namespace App\Http\Controllers;

use App\Models\AssetDisruptionWorkOrder;
use App\Services\CollectorWorkOrderDescription;
use App\Services\ReliabilityMart;
use App\Services\WorkOrderEvidence;
use App\Services\WorkOrderTiming;
use Illuminate\Http\Request;
use Illuminate\Validation\Rule;
use Symfony\Component\HttpKernel\Exception\HttpExceptionInterface;
use Throwable;

class WorkOrderController extends Controller
{
    public function index(Request $request, ReliabilityMart $mart)
    {
        $query = $request->validate([
            'offset' => ['sometimes', 'integer', 'min:0', 'max:1000000'],
            'asset_ref' => ['nullable', 'required_with:year', 'string', 'max:240'],
            'status' => ['nullable', 'string', 'max:40'],
            'year' => ['nullable', 'regex:/^(unknown|[1-9][0-9]{0,3})$/'],
            'from' => ['nullable', Rule::prohibitedIf($request->filled('year')), 'date_format:Y-m-d'],
            'to' => ['nullable', Rule::prohibitedIf($request->filled('year')), 'date_format:Y-m-d', Rule::when($request->filled('from'), 'after_or_equal:from')],
            'sort' => ['nullable', Rule::in(['date_desc', 'date_asc'])],
            'view' => ['nullable', Rule::in(['work-orders', 'disturbances'])],
        ]);
        $query['offset'] = (int) ($query['offset'] ?? 0);
        $mode = $query['view'] ?? 'work-orders';
        $asset = null;
        $summary = null;
        $annual = null;
        $inventory = false;
        $inventoryUnavailable = false;
        try {
            if (! empty($query['asset_ref'])) {
                $asset = $mart->historyAsset($query['asset_ref']);
                $inventory = ! $asset['registered'];
            }
            $filters = array_filter(collect($query)->only(['offset', 'asset_ref', 'status', 'sort', 'year'])->all(), fn ($value) => $value !== null && $value !== '');
            // Existing API date basis: actual_start, otherwise source_changed_at.
            // The UI names this mixed basis explicitly; it is never a failure-date filter.
            if (! empty($query['from'])) {
                $filters['date_from'] = $query['from'].'T00:00:00+07:00';
            }
            if (! empty($query['to'])) {
                $filters['date_to'] = $query['to'].'T23:59:59.999999+07:00';
            }
            $page = $mart->workOrders($filters, $inventory);
            $summary = ['candidate' => 0, 'maintenance' => 0, 'unknown' => 0];
            foreach ($page['items'] as &$item) {
                $item['evidence'] = WorkOrderEvidence::fromRecord($item);
                $summary[$item['evidence']['review']]++;
            }
            unset($item);
        } catch (Throwable $error) {
            $inventoryUnavailable = $inventory && $error instanceof HttpExceptionInterface && $error->getStatusCode() === 404;
            $page = null;
        }

        if ($asset !== null) {
            try {
                // Full asset population, independent of list filters and pagination.
                $annual = $mart->annualWorkOrders($asset['canonical_id'], $inventory);
            } catch (Throwable) {
                $annual = null;
            }
        }

        return view('work-orders.index', compact('page', 'asset', 'summary', 'annual', 'mode', 'inventory', 'inventoryUnavailable'));
    }

    public function show(Request $request, ReliabilityMart $mart, CollectorWorkOrderDescription $collector)
    {
        $query = $request->validate(['ref' => ['required', 'string', 'max:200'], 'event' => ['nullable', 'string', 'max:200'], 'asset_ref' => ['nullable', 'string', 'max:240']]);
        abort_unless(str_starts_with($query['ref'], 'workorder:MAXIMO:MXWODETAIL:BSR:IP:'), 404);
        $descriptionOrigin = 'Belum tersedia';
        $inventory = false;
        try {
            if (! empty($query['asset_ref'])) {
                $asset = $mart->historyAsset($query['asset_ref']);
                $inventory = ! $asset['registered'];
            }
            $record = $mart->workOrder($query['ref'], $query['event'] ?? null, $query['asset_ref'] ?? null, $inventory);
            if ($record['description']) {
                $descriptionOrigin = 'Reliability Mart';
            } else {
                $record['description'] = $collector->forRecord($record);
                if ($record['description']) {
                    $descriptionOrigin = 'Maximo Collector lokal · nomor WO dan Asset cocok persis';
                }
            }
            $timing = WorkOrderTiming::fromRecord($record);
            $evidence = WorkOrderEvidence::fromRecord($record);
        } catch (Throwable $error) {
            if ($error instanceof HttpExceptionInterface && $error->getStatusCode() === 404) {
                throw $error;
            }
            $record = $timing = $evidence = null;
        }

        $disruptionLinks = $record ? AssetDisruptionWorkOrder::with('disruption')
            ->where('work_order_ref', $record['work_order_id'])->where('asset_ref', $record['equipment_id'])
            ->where('relation_state', '!=', 'removed')->orderByDesc('id')->simplePaginate(10) : null;

        return view('work-orders.show', compact('record', 'timing', 'descriptionOrigin', 'evidence', 'inventory', 'disruptionLinks'));
    }
}
