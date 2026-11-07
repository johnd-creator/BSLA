<?php

namespace App\Services;

use App\Models\InspectionDraft;
use App\Models\PdmActivity;
use Illuminate\Pagination\LengthAwarePaginator;
use Illuminate\Support\Facades\DB;

class PdmLogbook
{
    // Paginate identities in SQL before loading models. Linked analysis is not a
    // second inspection: only standalone drafts receive their own logbook row.
    public function paginate(array $filters): LengthAwarePaginator
    {
        $activities = DB::table('pdm_activities as p')->leftJoin('inspection_drafts as i', 'i.pdm_activity_id', '=', 'p.id')
            ->selectRaw("p.id, 'pdm' as source, p.measured_on as occurred_on, p.measured_at as occurred_at");
        $drafts = DB::table('inspection_drafts as i')->whereNull('i.pdm_activity_id')
            ->selectRaw("i.id, 'inspection' as source, COALESCE(SUBSTR(i.inspected_on, 1, 10), SUBSTR(i.created_at, 1, 10)) as occurred_on, CASE WHEN i.inspected_on IS NULL THEN i.created_at ELSE NULL END as occurred_at");
        foreach ([[$activities, 'p'], [$drafts, 'i']] as [$query, $alias]) {
            if (! empty($filters['q'])) {
                $term = '%'.$filters['q'].'%';
                $query->where(function ($query) use ($term, $alias) {
                    $query->where($alias.'.asset_ref', 'like', $term)->orWhere($alias.'.request_reference', 'like', $term)
                        ->orWhere($alias.'.request_summary', 'like', $term)->orWhere($alias.'.requester_name', 'like', $term)
                        ->orWhere('i.finding', 'like', $term)->orWhere('i.recommendation', 'like', $term);
                    if ($alias === 'p') {
                        $query->orWhere('p.title', 'like', $term);
                    }
                });
            }
            foreach (['method', 'inspection_type'] as $filter) {
                if (! empty($filters[$filter])) {
                    $query->where($alias.'.'.$filter, $filters[$filter]);
                }
            }
            match ($filters['stage'] ?? '') {
                'request' => $alias === 'p' ? $query->whereRaw('1 = 0') : $query->whereNull('i.finding')->whereNull('i.recommendation'),
                'finding' => $query->whereNull('i.recommendation')->when($alias === 'i', fn ($query) => $query->whereNotNull('i.finding')),
                'recommendation' => $query->whereNotNull('i.recommendation'),
                default => null,
            };
        }
        $page = DB::query()->fromSub($activities->unionAll($drafts), 'logbook')
            ->orderByDesc('occurred_on')->orderByRaw('CASE WHEN occurred_at IS NULL THEN 1 ELSE 0 END')->orderByDesc('occurred_at')->orderBy('source')->orderByDesc('id')->paginate(20)->withQueryString();
        $rows = $page->getCollection();
        $pdm = PdmActivity::with(['author:id,name', 'inspection'])->whereIn('id', $rows->where('source', 'pdm')->pluck('id'))->get()->keyBy('id');
        $inspections = InspectionDraft::with('author:id,name')->whereIn('id', $rows->where('source', 'inspection')->pluck('id'))->get()->keyBy('id');
        $page->setCollection($rows->map(fn ($row) => $row->source === 'pdm' ? $pdm[$row->id] : $inspections[$row->id]));

        return $page;
    }
}
