<?php

namespace App\Http\Controllers;

use App\Services\CollectorWorkOrderDescription;
use App\Services\ReliabilityMart;
use App\Services\WorkOrderTiming;
use Illuminate\Http\Request;
use Symfony\Component\HttpKernel\Exception\HttpExceptionInterface;
use Throwable;

class WorkOrderController extends Controller
{
    public function index(Request $request, ReliabilityMart $mart)
    {
        $query = $request->validate(['offset' => ['sometimes', 'integer', 'min:0', 'max:1000000'], 'asset_ref' => ['nullable', 'string', 'max:240'], 'status' => ['nullable', 'string', 'max:40']]);
        $query['offset'] = (int) ($query['offset'] ?? 0);
        try {
            $page = $mart->workOrders(array_filter($query, fn ($value) => $value !== null && $value !== ''));
        } catch (Throwable) {
            $page = null;
        }

        return view('work-orders.index', compact('page'));
    }

    public function show(Request $request, ReliabilityMart $mart, CollectorWorkOrderDescription $collector)
    {
        $query = $request->validate(['ref' => ['required', 'string', 'max:200'], 'event' => ['nullable', 'string', 'max:200']]);
        abort_unless(str_starts_with($query['ref'], 'workorder:MAXIMO:MXWODETAIL:BSR:IP:'), 404);
        $descriptionOrigin = 'Belum tersedia';
        try {
            $record = $mart->workOrder($query['ref'], $query['event'] ?? null);
            if ($record['description']) {
                $descriptionOrigin = 'Reliability Mart';
            } else {
                $record['description'] = $collector->forRecord($record);
                if ($record['description']) {
                    $descriptionOrigin = 'Maximo Collector lokal · nomor WO dan Asset cocok persis';
                }
            }
            $timing = WorkOrderTiming::fromRecord($record);
        } catch (Throwable $error) {
            if ($error instanceof HttpExceptionInterface && $error->getStatusCode() === 404) {
                throw $error;
            }
            $record = $timing = null;
        }

        return view('work-orders.show', compact('record', 'timing', 'descriptionOrigin'));
    }
}
