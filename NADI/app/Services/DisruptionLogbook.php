<?php

namespace App\Services;

use App\Models\AssetDisruption;

class DisruptionLogbook
{
    public function summary(?string $asset = null): array
    {
        $query = AssetDisruption::where('status', 'recorded')->when($asset, fn ($query) => $query->forAsset($asset));
        $summary = ['total' => 0, 'dated' => 0, 'timed' => 0, 'restored' => 0, 'duration_known' => 0, 'unknown_date' => 0, 'annual' => []];
        // A single event remains one record even when multiple assets are involved.
        foreach ($query->with('members')->lazyById(200) as $event) {
            $summary['total']++;
            $summary['dated'] += $event->occurred_on ? 1 : 0;
            $summary['timed'] += $event->occurred_at ? 1 : 0;
            $summary['restored'] += $event->restored_on ? 1 : 0;
            $duration = $event->durationSeconds();
            $summary['duration_known'] += $duration !== null ? 1 : 0;
            if (! $event->occurred_on) {
                $summary['unknown_date']++;

                continue;
            }
            $year = substr($event->occurred_on, 0, 4);
            $summary['annual'][$year] ??= ['total' => 0, 'cause' => 0, 'affected' => 0, 'unknown' => 0, 'duration_known' => 0, 'seconds' => 0];
            $summary['annual'][$year]['total']++;
            if ($asset) {
                $summary['annual'][$year][$event->roleFor($asset) ?? 'unknown']++;
            }
            if ($duration !== null) {
                $summary['annual'][$year]['duration_known']++;
                $summary['annual'][$year]['seconds'] += $duration;
            }
        }
        krsort($summary['annual']);

        return $summary;
    }
}
