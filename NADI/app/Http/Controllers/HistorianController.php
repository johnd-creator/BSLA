<?php

namespace App\Http\Controllers;

use App\Services\HistorianDemand;
use Illuminate\Http\Request;
use Illuminate\Validation\Rule;

class HistorianController extends Controller
{
    public function index(Request $request, HistorianDemand $demand)
    {
        $pages = config('historian.pages');
        $input = $request->validate(['page' => ['sometimes', 'string', Rule::in(array_keys($pages))]]);
        $pageKey = $input['page'] ?? array_key_first($pages);

        return view('operations.historian', ['pages' => $pages, 'pageKey' => $pageKey, 'configured' => $demand->configured()]);
    }

    public function action(Request $request, HistorianDemand $demand, string $action)
    {
        $rules = match ($action) {
            'subscribe' => ['page' => ['required', 'string', Rule::in(array_keys(config('historian.pages')))], 'client' => ['required', 'string', 'regex:/^[A-Za-z0-9_.-]{1,64}$/D']],
            'heartbeat', 'release' => ['subscription' => ['required', 'string', 'regex:/^[a-f0-9]{48}$/D']],
            'history' => ['subscription' => ['required', 'string', 'regex:/^[a-f0-9]{48}$/D'], 'tag' => ['required', 'string', Rule::in(array_unique(array_merge(...array_column(config('historian.pages'), 'tags'))))],
                'start' => ['required', 'date_format:Y-m-d\TH:i:s\Z'], 'end' => ['required', 'date_format:Y-m-d\TH:i:s\Z', 'after:start'], 'limit' => ['required', 'integer', 'min:1', 'max:1000']],
            default => abort(404),
        };
        $input = $request->validate($rules);
        if ($action === 'history') {
            abort_if(strtotime($input['end']) - strtotime($input['start']) > 3600 || strtotime($input['end']) > time() + 1 || strtotime($input['start']) < 0, 422);
            $input['limit'] = (int) $input['limit'];
        }
        // Bind private leases to the authenticated account AND session. Never send either identifier.
        $input['owner'] = hash_hmac('sha256', $request->user()->getAuthIdentifier().'|'.$request->session()->getId(), (string) config('app.key'));
        $result = $demand->call($action, $input);

        return $result === null ? response()->json(['error' => 'historian_unavailable'], 503) : response()->json($result);
    }
}
