<?php

namespace App\Http\Controllers;

use App\Services\CemsAssetMapping;
use App\Services\CemsLive;
use App\Services\ReliabilityMart;
use Illuminate\Http\Request;

class CemsController extends Controller
{
    public function index(Request $request, CemsLive $cems, CemsAssetMapping $mapping, ReliabilityMart $mart)
    {
        $parameter = $request->query('parameter');
        $data = $cems->read(is_string($parameter) && strlen($parameter) <= 64 ? $parameter : null);

        $data['signals'] = $cems->signals($data['snapshot']['parameters'] ?? [], $data['snapshot']['source_mode'] ?? null);
        $data['assetLinks'] = $mapping->resolve($data['snapshot']['parameters'] ?? [], $mart);

        return response()->view($request->routeIs('operations.cems.refresh') ? 'operations.cems-data' : 'operations.cems', $data)
            ->header('Cache-Control', 'no-store, private')->header('X-Cems-Fragment', '1');
    }
}
