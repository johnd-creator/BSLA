<?php

namespace App\Http\Controllers;

use App\Services\ReliabilityMart;
use Illuminate\Http\Request;
use Throwable;

class ActionBoardController extends Controller
{
    public function __invoke(Request $request, ReliabilityMart $mart)
    {
        $query = $request->validate(['backlog_offset' => ['sometimes', 'integer', 'min:0', 'max:1000000']]);
        try {
            $backlog = $mart->waitingApproval((int) ($query['backlog_offset'] ?? 0));
        } catch (Throwable) {
            $backlog = null;
        }

        return view('action-board', compact('backlog'));
    }
}
