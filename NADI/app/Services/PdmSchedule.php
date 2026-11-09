<?php

namespace App\Services;

use App\Models\PdmActivity;
use App\Models\PdmInspectionPlan;
use Carbon\CarbonImmutable;

class PdmSchedule
{
    public const LIMIT = 250;

    public const LABELS = ['paused' => 'Dijeda', 'overdue' => 'Terlambat', 'due' => 'Jatuh tempo hari ini', 'upcoming' => 'Terjadwal', 'unknown' => 'Cakupan belum pasti'];

    public function coverage(PdmInspectionPlan $plan): array
    {
        $today = CarbonImmutable::today('Asia/Jakarta');
        $query = PdmActivity::query()->where('asset_ref', $plan->asset_ref)
            ->where('template_id', $plan->template_id)->where('template_fingerprint', $plan->template_fingerprint)
            ->where('method', $plan->method)->where('inspection_type', 'routine')
            ->where(function ($query) use ($today) {
                $query->where(function ($date) use ($today) {
                    $date->where('time_precision', 'date')->whereDate('measured_on', '<=', $today->toDateString());
                })->orWhere(function ($datetime) {
                    $datetime->where('time_precision', 'datetime')->whereNotNull('measured_at')->where('measured_at', '<=', now()->utc());
                });
            });
        foreach (PdmTrend::CONTEXT as $key) {
            $query->where($key, $plan->$key);
        }
        $candidates = $query->newestMeasurement()->limit(self::LIMIT + 1)->get();
        $latest = null;
        $field = $plan->point();
        foreach ($candidates->take(self::LIMIT) as $activity) {
            $reading = $activity->readings[$plan->point_key] ?? [];
            $value = $reading['value'] ?? null;
            if (! $field || ($plan->template_snapshot['preview_only'] ?? true)
                || $activity->template_snapshot !== $plan->template_snapshot
                || ($reading['unit'] ?? $field['unit'] ?? null) !== $plan->unit
                || $value === null || trim((string) $value) === ''
                || (($field['type'] ?? null) === 'number' && (! is_numeric($value) || ! is_finite((float) $value)))) {
                continue;
            }
            $latest = $activity;
            break;
        }
        $truncated = ! $latest && $candidates->count() > self::LIMIT;
        $next = $plan->first_due_on;
        $freshUntil = null;
        if ($latest) {
            $date = CarbonImmutable::parse($latest->measurementDate(), 'Asia/Jakarta');
            $next = match ($plan->frequency_unit) {
                'weeks' => $date->addWeeks($plan->frequency_value),
                'months' => $date->addMonthsNoOverflow($plan->frequency_value),
                default => $date->addDays($plan->frequency_value),
            };
            $freshUntil = $next;
            // The explicit first due date is the earliest activation of this plan.
            $next = $next->max($plan->first_due_on);
        }
        $state = $plan->status === 'paused' ? 'paused' : ($truncated ? 'unknown' : ($next->lessThan($today) ? 'overdue' : ($next->isSameDay($today) ? 'due' : 'upcoming')));

        return ['latest' => $latest, 'next_due_on' => $truncated ? null : $next, 'state' => $state,
            'label' => self::LABELS[$state], 'truncated' => $truncated,
            'covered' => $plan->status === 'active' && $latest && ! $truncated && $freshUntil->greaterThan($today)];
    }
}
