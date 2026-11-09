<?php

namespace App\Services;

use App\Models\AssetDisruption;
use App\Models\ReliabilityReview;

class ReliabilityScope
{
    public function currentHash(string $asset): string
    {
        $events = AssetDisruption::forAsset($asset)->orderBy('id')->limit(ReliabilityEvidence::LIMIT + 1)->get();
        $ids = ReliabilityReview::where('asset_ref', $asset)->whereIn('asset_disruption_id', $events->pluck('id'))->selectRaw('MAX(id) as id')->groupBy('asset_disruption_id')->pluck('id');
        $reviews = ReliabilityReview::whereIn('id', $ids)->get()->keyBy('asset_disruption_id');
        $rows = $events->map(function ($event) use ($reviews) {
            $r = $reviews->get($event->id);

            return ['event_id' => $event->id, 'event_version' => $event->version, 'review_id' => $r?->id, 'review_revision' => $r?->revision, 'review_rule_version' => $r?->rule_version];
        })->all();

        return $this->hashRows($rows);
    }

    public function hashRows(array $rows): string
    {
        return hash('sha256', json_encode(array_map(fn ($row) => [$row['event_id'], $row['event_version'], $row['review_id'], $row['review_revision'], $row['review_rule_version']], $rows), JSON_THROW_ON_ERROR));
    }
}
