<?php

namespace App\Http\Controllers;

use App\Models\ActionEffectivenessReview;
use App\Models\AssetPriority;
use App\Models\InspectionDraft;
use App\Services\ActionEffectiveness;
use App\Services\AssetAttention;
use App\Services\ReliabilityMart;
use Illuminate\Http\Request;
use Illuminate\Validation\Rule;
use Throwable;

class ActionBoardController extends Controller
{
    public function __invoke(Request $request, ReliabilityMart $mart)
    {
        $query = $request->validate(['window_days' => ['nullable', Rule::in([30, 90, 180])], 'candidate_offset' => ['nullable', 'integer', 'between:0,1000000'], 'priority_status' => ['nullable', Rule::in(array_keys(AssetPriority::STATUSES))], 'backlog_offset' => ['sometimes', 'integer', 'min:0', 'max:1000000'], 'follow_up_status' => ['nullable', Rule::in(array_keys(InspectionDraft::FOLLOW_UP_STATUSES))]]);
        $followUps = InspectionDraft::with(['author:id,name', 'pdmActivity', 'pdmReviewAudit'])->whereNotNull('recommendation')->where('recommendation', '!=', '');
        if (! empty($query['follow_up_status'])) {
            $followUps->where('follow_up_status', $query['follow_up_status']);
        }
        $followUps = $followUps->orderByRaw('target_completion IS NULL')->orderBy('target_completion')->orderByDesc('id')->paginate(10, ['*'], 'follow_up_page')->withQueryString();
        try {
            $backlog = $mart->waitingApproval((int) ($query['backlog_offset'] ?? 0));
        } catch (Throwable) {
            $backlog = null;
        }

        $priorities = AssetPriority::with('author:id,name')->where('status', $query['priority_status'] ?? 'active')
            ->orderByRaw("CASE urgency WHEN 'immediate' THEN 0 WHEN 'planned' THEN 1 ELSE 2 END")
            ->orderByRaw('COALESCE(review_on, due_on) IS NULL')->orderByRaw('COALESCE(review_on, due_on)')->orderBy('id')
            ->paginate(10, ['*'], 'priority_page')->withQueryString();
        $candidates = app(AssetAttention::class)->candidates();
        $windowDays = (int) ($query['window_days'] ?? 90);
        try {
            $repeat = $mart->attentionCandidates($windowDays, (int) ($query['candidate_offset'] ?? 0));
            $assessed = AssetPriority::whereIn('asset_ref', array_column($repeat['assets'], 'asset_ref'))->pluck('id', 'asset_ref')->all();
            $repeat['assessed'] = $assessed;
        } catch (Throwable) {
            $repeat = null;
        }
        $unlinkedPdm = InspectionDraft::whereNotNull('recommendation')->where('recommendation', '!=', '')->whereIn('follow_up_status', ['open', 'in_progress'])
            ->where(fn ($query) => $query->whereNull('asset_ref')->orWhere('asset_ref', ''))->count();

        $effectivenessReviews = ActionEffectivenessReview::with(['beforeMeasurement', 'afterMeasurement'])->whereIn('id',
            ActionEffectivenessReview::selectRaw('MAX(id)')->whereIn('inspection_draft_id', $followUps->pluck('id'))->groupBy('inspection_draft_id')
        )->get()->keyBy('inspection_draft_id');
        $effectiveness = app(ActionEffectiveness::class);

        return view('action-board', compact('effectivenessReviews', 'effectiveness', 'backlog', 'followUps', 'priorities', 'candidates', 'windowDays', 'repeat', 'unlinkedPdm'));
    }
}
