<?php

namespace App\Services;

use App\Models\ActionEffectivenessReview;
use App\Models\InspectionDraft;
use App\Models\PdmInspectionPlan;
use Illuminate\Support\Facades\Schema;

/** Current local evidence obligations, never a health or historical compliance score. */
class AssetWellnessCompleteness
{
    public const PLAN_LIMIT = 20;

    public const ACTION_LIMIT = 20;

    public function report(string $asset): array
    {
        $available = Schema::hasTable('pdm_inspection_plans');
        $plans = $available ? PdmInspectionPlan::where('asset_ref', $asset) : null;
        $active = $plans ? (clone $plans)->where('status', 'active')->count() : null;
        $paused = $plans ? (clone $plans)->where('status', 'paused')->count() : null;
        $rows = [];
        $counts = ['current' => 0, 'expired' => 0, 'missing' => 0, 'unknown' => 0, 'overdue' => 0, 'due' => 0,
            'current_analysis' => 0, 'stale_analysis' => 0, 'unknown_analysis' => 0, 'missing_analysis' => 0];
        foreach ($plans ? (clone $plans)->where('status', 'active')->orderBy('first_due_on')->orderBy('id')->limit(self::PLAN_LIMIT)->get() : [] as $plan) {
            $coverage = app(PdmSchedule::class)->coverage($plan);
            $measurement = $coverage['latest'];
            $state = $coverage['truncated'] ? 'unknown' : (! $measurement ? 'missing' : ($coverage['covered'] ? 'current' : 'expired'));
            $counts[$state]++;
            if (in_array($coverage['state'], ['overdue', 'due'], true)) {
                $counts[$coverage['state']]++;
            }
            $inspection = $measurement?->inspection;
            if ($inspection && $inspection->asset_ref === $asset) {
                $inspection->setRelation('pdmActivity', $measurement);
            } else {
                $inspection = null;
            }
            $analysis = $this->analysis($inspection);
            $counts[$analysis.'_analysis']++;
            $rows[] = ['plan' => $plan, 'measurement' => $measurement, 'state' => $state, 'schedule' => $coverage,
                'analysis_state' => $analysis, 'inspection' => $inspection,
                'follow_up' => $inspection && trim((string) $inspection->recommendation) !== '' ? $this->followUp($inspection) : null];
        }

        // Keep older/unlinked recommendations visible even after a newer reading arrives.
        $actions = InspectionDraft::where('asset_ref', $asset)->whereNotNull('recommendation')->whereRaw("TRIM(recommendation) <> ''");
        $actionCount = (clone $actions)->count();
        $followUps = $actions->with(['pdmActivity', 'pdmReviewAudit'])->orderByDesc('updated_at')->orderByDesc('id')->limit(self::ACTION_LIMIT)
            ->get()->map(fn ($inspection) => $this->followUp($inspection))->all();

        return ['observed_on' => now('Asia/Jakarta')->toDateString(), 'scope' => 'CURRENT_LOCAL_PLANS',
            'available' => $available, 'required_count' => $active, 'paused_count' => $paused,
            'rows' => $rows, 'inspected_count' => count($rows), 'truncated' => $active > self::PLAN_LIMIT,
            'counts' => $counts, 'score' => null, 'follow_ups' => $followUps,
            'follow_up_count' => $actionCount, 'follow_ups_truncated' => $actionCount > self::ACTION_LIMIT];
    }

    private function analysis(?InspectionDraft $inspection): string
    {
        if (! $inspection || (! trim((string) $inspection->finding) && ! trim((string) $inspection->recommendation))) {
            return 'missing';
        }

        return $inspection->pdmReviewState() ?? 'current';
    }

    private function followUp(InspectionDraft $inspection): array
    {
        $available = Schema::hasTable('action_effectiveness_reviews');
        $review = $available ? ActionEffectivenessReview::where('inspection_draft_id', $inspection->id)
            ->with(['beforeMeasurement', 'afterMeasurement'])->latest('revision')->first() : null;
        $service = app(ActionEffectiveness::class);
        $state = $available ? $service->state($review, $inspection) : 'unavailable';

        return ['inspection' => $inspection, 'review' => $review, 'state' => $state,
            'analysis_state' => $inspection->pdm_activity_id ? $this->analysis($inspection) : 'unlinked',
            'label' => $available ? $service->label($state) : 'Penyimpanan review efektivitas belum tersedia'];
    }
}
