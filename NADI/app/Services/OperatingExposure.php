<?php

namespace App\Services;

use App\Models\OperatingLog;
use Carbon\CarbonImmutable;
use Illuminate\Support\Facades\Schema;

class OperatingExposure
{
    public const LIMIT = 5000;

    public function report(string $asset, int $year): array
    {
        $start = CarbonImmutable::create($year, 1, 1, 0, 0, 0, ReliabilityEvidence::ZONE)->timestamp;
        $end = CarbonImmutable::create($year + 1, 1, 1, 0, 0, 0, ReliabilityEvidence::ZONE)->timestamp;
        $logs = Schema::hasTable('operating_logs') ? OperatingLog::where('asset_ref', $asset)->with('latestRevision')->orderBy('id')->limit(self::LIMIT + 1)->get() : collect();
        $truncated = $logs->count() > self::LIMIT;
        $rows = $changes = [];
        $quality = ['draft' => 0, 'verified' => 0, 'voided' => 0, 'outside_period' => 0];
        foreach ($logs->take(self::LIMIT) as $log) {
            $r = $log->latestRevision;
            if (! $r) {
                continue;
            }
            $a = max($start, $r->started_at->timestamp);
            $b = min($end, $r->ended_at->timestamp);
            if ($b <= $a) {
                $quality['outside_period']++;

                continue;
            }
            $quality[$r->review_state]++;
            $rows[] = ['id' => $log->id, 'version' => $log->version, 'revision_id' => $r->id, 'actor_id' => $r->created_by,
                'started_at' => $r->started_at->toIso8601String(), 'ended_at' => $r->ended_at->toIso8601String(), 'state' => $r->state,
                'review_state' => $r->review_state, 'source' => $r->source, 'evidence' => $r->evidence, 'reason' => $r->reason, 'reviewed_at' => $r->created_at->toIso8601String()];
            if ($r->review_state !== 'verified') {
                continue;
            }
            $changes[$a][] = ['id' => $log->id, 'state' => $r->state, 'add' => true];
            $changes[$b][] = ['id' => $log->id, 'state' => $r->state, 'add' => false];
        }
        $changes[$start] ??= [];
        $changes[$end] ??= [];
        ksort($changes, SORT_NUMERIC);
        $active = [];
        $last = $start;
        $seconds = array_fill_keys(['RUN', 'STOP', 'STANDBY', 'UNKNOWN', 'GAP', 'OVERLAP'], 0);
        $segments = [];
        foreach ($changes as $time => $items) {
            if ($time > $last) {
                $state = count($active) > 1 ? 'OVERLAP' : ($active ? reset($active) : 'GAP');
                $duration = $time - $last;
                $seconds[$state] += $duration;
                // Half-open segments: adjacent endpoints do not overlap. Even
                // agreeing duplicate records are conflicts, never summed.
                $segments[] = ['start' => CarbonImmutable::createFromTimestamp($last, 'UTC')->toIso8601String(), 'end' => CarbonImmutable::createFromTimestamp($time, 'UTC')->toIso8601String(), 'state' => $state, 'seconds' => $duration, 'log_ids' => array_keys($active)];
            }
            foreach ($items as $item) {
                if ($item['add']) {
                    $active[$item['id']] = $item['state'];
                } else {
                    unset($active[$item['id']]);
                }
            }
            $last = $time;
        }
        $known = $seconds['RUN'] + $seconds['STOP'] + $seconds['STANDBY'];
        $hasVerified = $quality['verified'] > 0;

        return ['schema_version' => 'manual-operating-evidence-v1', 'period_seconds' => $end - $start,
            'status' => $truncated ? 'PARTIAL' : ($hasVerified ? 'LOCAL_REVIEWED_EVIDENCE' : 'NOT_AVAILABLE'),
            'truncated' => $truncated, 'seconds' => $seconds, 'operating_seconds' => $truncated || ! $hasVerified || $known === 0 ? null : $seconds['RUN'],
            'known_seconds' => $truncated || ! $hasVerified ? null : $known,
            'coverage_percent' => $truncated || ! $hasVerified ? null : round($known / ($end - $start) * 100, 6),
            'quality' => $quality, 'records' => $rows, 'segments' => $segments,
            'meaning' => 'Exact asset, clipped half-open annual window. Known coverage excludes UNKNOWN, gaps and all overlaps. RUN only is observed operating exposure; no extrapolation. Draft/voided records excluded.'];
    }
}
