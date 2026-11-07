<?php

namespace App\Services;

use App\Models\AssetPriority;
use App\Models\InspectionDraft;
use Carbon\CarbonImmutable;
use Illuminate\Support\Facades\DB;
use Throwable;

class HomeFeed
{
    public const TYPES = ['all' => 'Semua aktivitas', 'disruption' => 'Log gangguan', 'pdm' => 'Pengukuran PdM', 'inspection' => 'Inspeksi & rekomendasi', 'priority' => 'Penilaian prioritas'];

    public function snapshot(ReliabilityMart $mart, array $filters): array
    {
        $local = ($filters['scope'] ?? 'all') !== 'registry' && ($filters['freshness'] ?? 'all') !== 'unknown';
        $registry = ($filters['scope'] ?? 'all') !== 'local' && ($filters['freshness'] ?? 'all') !== 'recorded';
        $priorities = $followUps = $candidates = $activities = $repeat = null;
        if ($local) {
            $priorities = $this->read(fn () => AssetPriority::query()->with('author:id,name')->where('status', 'active')
                ->orderByRaw("CASE urgency WHEN 'immediate' THEN 0 WHEN 'planned' THEN 1 ELSE 2 END")
                ->orderByRaw('due_on IS NULL AND review_on IS NULL')
                ->orderByRaw('CASE WHEN due_on IS NULL THEN review_on WHEN review_on IS NULL THEN due_on WHEN due_on < review_on THEN due_on ELSE review_on END')
                ->orderBy('id')->limit(6)->get());
            $followUps = $this->read(fn () => InspectionDraft::query()->whereNotNull('recommendation')->where('recommendation', '!=', '')
                ->whereIn('follow_up_status', ['open', 'in_progress'])->whereNotNull('target_completion')
                ->where('target_completion', '<=', today()->addDays(7)->endOfDay())->orderBy('target_completion')->orderBy('id')->limit(4)
                ->get(['id', 'asset_ref', 'target_completion', 'follow_up_status']));
            $candidates = $this->read(fn () => app(AssetAttention::class)->query()->limit(5)->get());
            $activities = $this->read(fn () => $this->activities($filters));
        }
        if ($registry) {
            $repeat = $this->read(function () use ($mart): array {
                $page = $mart->attentionCandidates(90, 0);
                $assessed = AssetPriority::whereIn('asset_ref', array_column($page['assets'], 'asset_ref'))->pluck('asset_ref')->all();
                $page['unassessed'] = array_values(array_filter($page['assets'], fn ($row) => ! in_array($row['asset_ref'], $assessed, true)));

                return $page;
            });
        }

        return compact('local', 'registry', 'priorities', 'followUps', 'candidates', 'activities', 'repeat');
    }

    /** One bounded SQL union. Never hydrate full histories or PdM measurement payloads. */
    public function activities(array $filters)
    {
        $queries = [];
        foreach (['disruption' => ['asset_disruption_revisions', 'asset_disruption_id'], 'priority' => ['asset_priority_revisions', 'asset_priority_id']] as $kind => [$table, $subject]) {
            $queries[] = DB::table($table)->selectRaw("id, '$kind' as kind, $subject as subject_id, version, changed_by as actor_id, NULL as asset_ref, CASE WHEN version = 1 THEN 'created' ELSE 'updated' END as action, snapshot as payload, created_at, 'revision' as basis");
        }
        $queries[] = DB::table('workspace_activities')->selectRaw("id, kind, subject_id, version, actor_id, asset_ref, action, changes as payload, created_at, 'audit' as basis");
        foreach (['pdm' => 'pdm_activities', 'inspection' => 'inspection_drafts'] as $kind => $table) {
            // Only creation metadata is known for older rows. updated_at is NOT an actor/event history.
            $queries[] = DB::table($table)->whereNotExists(fn ($q) => $q->selectRaw('1')->from('workspace_activities as a')
                ->where('a.kind', $kind)->whereColumn('a.subject_id', "$table.id")->where('a.action', 'created'))
                ->selectRaw("id, '$kind' as kind, id as subject_id, 1 as version, created_by as actor_id, NULL as asset_ref, 'created' as action, '{}' as payload, created_at, 'legacy' as basis");
        }
        // Each branch contributes at most the requested prefix. Filtering must
        // happen before that limit, so an old matching event is not lost.
        $prefix = min(100, max(1, (int) ($filters['activity_page'] ?? 1))) * 12 + 1;
        $queries = array_map(function ($source) use ($filters, $prefix) {
            $branch = DB::query()->fromSub($source, 'source_events')->whereNotNull('created_at');
            if (($filters['activity_type'] ?? 'all') !== 'all') {
                $branch->where('kind', $filters['activity_type']);
            }
            if (($filters['period'] ?? 'all') !== 'all') {
                $branch->where('created_at', '>=', now()->subDays((int) $filters['period']));
            }

            return DB::query()->fromSub($branch->orderByDesc('created_at')->orderBy('kind')->orderByDesc('id')->limit($prefix), 'bounded_events');
        }, $queries);
        $union = array_shift($queries);
        foreach ($queries as $query) {
            $union->unionAll($query);
        }
        $query = DB::query()->fromSub($union, 'events')->leftJoin('users', 'users.id', '=', 'events.actor_id')
            ->select('events.*', 'users.name as actor');
        $page = $query->orderByDesc('events.created_at')->orderBy('events.kind')->orderByDesc('events.id')->orderBy('events.basis')
            ->simplePaginate(12, ['*'], 'activity_page')->withQueryString();
        if ((int) ($filters['activity_page'] ?? 1) >= 100) {
            $page->hasMorePagesWhen(false);
        }
        $page->setCollection($page->getCollection()->map(fn ($event) => $this->event($event)));

        return $page;
    }

    private function event(object $event): array
    {
        $payload = json_decode($event->payload, true, 512, JSON_THROW_ON_ERROR);
        $created = $event->action === 'created';
        $title = match ($event->kind) {
            'disruption' => $created ? 'Log gangguan dicatat' : 'Log gangguan dikoreksi',
            'priority' => $created ? 'Prioritas dinilai' : 'Penilaian prioritas diperbarui',
            'pdm' => $created ? 'Draft pengukuran PdM dibuat' : 'Draft pengukuran PdM diperbarui',
            'inspection' => $created ? 'Draft inspeksi dibuat' : 'Draft inspeksi diperbarui',
        };
        $detail = '';
        if ($event->kind === 'inspection' && isset($payload['recommendation'])) {
            $title = empty($payload['recommendation']['after']) ? 'Rekomendasi dihapus dari draft' : (empty($payload['recommendation']['before']) ? 'Rekomendasi dicatat' : 'Rekomendasi diperbarui');
        }
        if ($event->kind === 'inspection' && isset($payload['follow_up_status'])) {
            $states = InspectionDraft::FOLLOW_UP_STATUSES;
            $detail = 'Status tindak lanjut: '.($states[$payload['follow_up_status']['before']] ?? 'Belum dicatat').' → '.($states[$payload['follow_up_status']['after']] ?? 'Belum diketahui');
        }
        if ($event->kind === 'priority') {
            $detail = (AssetPriority::URGENCIES[$payload['urgency'] ?? ''] ?? 'Urgensi belum diketahui').' · '.(AssetPriority::STATUSES[$payload['status'] ?? ''] ?? 'Status belum diketahui').' · penilaian saat versi ini dicatat';
        }
        if ($event->kind === 'disruption') {
            $detail = ($payload['status'] ?? '') === 'voided' ? 'Catatan dibatalkan pada versi ini' : 'Catatan manual, bukan bukti masih terganggu';
        }
        $route = ['disruption' => 'disruptions.show', 'priority' => 'priorities.show', 'pdm' => 'pdm.show', 'inspection' => 'inspections.show'][$event->kind];
        $url = route($route, $event->subject_id);
        if ($event->basis === 'audit') {
            $url .= '?activity_id='.$event->id.'#activity-'.$event->id;
        } elseif ($event->basis === 'revision') {
            $url .= '?revision='.$event->version.'#revision-'.$event->version;
        }

        return ['kind' => $event->kind, 'title' => $title, 'detail' => $detail, 'at' => CarbonImmutable::parse($event->created_at, 'UTC'),
            'actor' => $event->actor ?? 'Pelaku tidak tersedia', 'asset_ref' => $payload['asset_ref'] ?? $event->asset_ref,
            'version' => $event->version, 'legacy' => $event->basis === 'legacy', 'url' => $url,
            'reference' => ['disruption' => 'GANGGUAN-', 'priority' => 'PRIORITAS-', 'pdm' => 'PDM-DRAFT-', 'inspection' => 'INS-DRAFT-'][$event->kind].str_pad((string) $event->subject_id, 5, '0', STR_PAD_LEFT)];
    }

    private function read(callable $query): mixed
    {
        try {
            return $query();
        } catch (Throwable) {
            return null;
        }
    }
}
