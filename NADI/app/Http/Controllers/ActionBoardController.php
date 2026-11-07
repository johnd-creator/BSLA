<?php

namespace App\Http\Controllers;

use App\Models\InspectionDraft;
use App\Services\ReliabilityMart;
use Illuminate\Http\Request;
use Illuminate\Validation\Rule;
use Throwable;

class ActionBoardController extends Controller
{
    public function __invoke(Request $request, ReliabilityMart $mart)
    {
        $query = $request->validate(['backlog_offset' => ['sometimes', 'integer', 'min:0', 'max:1000000'], 'follow_up_status' => ['nullable', Rule::in(array_keys(InspectionDraft::FOLLOW_UP_STATUSES))]]);
        $followUps = InspectionDraft::with(['author:id,name', 'pdmActivity'])->whereNotNull('recommendation');
        if (! empty($query['follow_up_status'])) {
            $followUps->where('follow_up_status', $query['follow_up_status']);
        }
        $followUps = $followUps->orderByRaw('target_completion IS NULL')->orderBy('target_completion')->orderByDesc('id')->paginate(10, ['*'], 'follow_up_page')->withQueryString();
        try {
            $backlog = $mart->waitingApproval((int) ($query['backlog_offset'] ?? 0));
        } catch (Throwable) {
            $backlog = null;
        }

        return view('action-board', compact('backlog', 'followUps'));
    }
}
