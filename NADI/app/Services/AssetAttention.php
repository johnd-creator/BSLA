<?php

namespace App\Services;

use Illuminate\Support\Facades\DB;

class AssetAttention
{
    /** Aggregate and paginate in SQL; no source asset or entire history hydration. */
    public function candidates()
    {
        return $this->query()->paginate(10, ['*'], 'candidate_page')->withQueryString();
    }

    public function query()
    {
        $disruptions = DB::table('asset_disruption_members as m')->join('asset_disruptions as d', 'd.id', '=', 'm.asset_disruption_id')
            ->where('d.status', 'recorded')->selectRaw('m.asset_ref, COUNT(DISTINCT d.id) as disruption_count, 0 as pdm_count')->groupBy('m.asset_ref');
        $pdm = DB::table('inspection_drafts')->whereNotNull('asset_ref')->where('asset_ref', '!=', '')
            ->whereNotNull('recommendation')->where('recommendation', '!=', '')->whereIn('follow_up_status', ['open', 'in_progress'])
            ->selectRaw('asset_ref, 0 as disruption_count, COUNT(*) as pdm_count')->groupBy('asset_ref');

        return DB::query()->fromSub($disruptions->unionAll($pdm), 'signals')
            ->whereNotExists(fn ($query) => $query->selectRaw('1')->from('asset_priorities')->whereColumn('asset_priorities.asset_ref', 'signals.asset_ref'))
            ->selectRaw('signals.asset_ref, SUM(disruption_count) as disruption_count, SUM(pdm_count) as pdm_count')
            ->groupBy('signals.asset_ref')->orderBy('signals.asset_ref');
    }
}
