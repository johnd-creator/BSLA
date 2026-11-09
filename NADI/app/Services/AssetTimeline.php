<?php

namespace App\Services;

use App\Models\AssetDisruption;
use App\Models\PdmActivity;
use Carbon\CarbonImmutable;
use Illuminate\Support\Str;
use Throwable;

class AssetTimeline
{
    public const LABELS = ['maintenance' => 'Work Order', 'pdm' => 'PdM lokal', 'disruptions' => 'Log gangguan manual', 'fmea' => 'FMEA', 'health' => 'Kondisi aset', 'overhauls' => 'Overhaul'];

    public function __construct(private ReliabilityMart $mart) {}

    public function forAsset(array $asset): array
    {
        $reference = $asset['canonical_id'];
        $events = [];
        $states = array_fill_keys(array_keys(self::LABELS), 'unavailable');
        $counts = array_fill_keys(array_keys(self::LABELS), 0);
        if (! $asset['registered']) {
            foreach (['fmea', 'health', 'overhauls'] as $source) {
                $states[$source] = 'registry_required';
            }
        }
        try {
            if ($asset['registered']) {
                $context = $this->mart->assetContext($reference);
            } else {
                // Non-Registry history remains scoped to the exact inventory asset.
                $context = ['maintenance' => $this->mart->workOrders(['asset_ref' => $reference, 'offset' => 0, 'sort' => 'date_desc'], true)['items']];
            }
            foreach ($context as $source => $rows) {
                $states[$source] = count($rows) ? 'available' : 'empty';
                $counts[$source] = count($rows);
                foreach ($rows as $row) {
                    $events[] = $this->sourceEvent($source, $row, $reference);
                }
            }
        } catch (Throwable) {
            // A source outage never becomes an empty/healthy history.
        }
        try {
            // Select only the fields used here, not large template/reading snapshots.
            $activities = PdmActivity::query()->where('asset_ref', $reference)
                ->newestMeasurement()->limit(25)
                ->get(['id', 'title', 'method', 'measured_at', 'measured_on', 'time_precision', 'timezone']);
            $states['pdm'] = $activities->isEmpty() ? 'empty' : 'available';
            $counts['pdm'] = $activities->count();
            foreach ($activities as $activity) {
                $events[] = [
                    'source' => 'pdm', 'reference' => $activity->reference(), 'title' => $activity->title,
                    'status' => 'Draft lokal · belum tervalidasi', 'at' => $activity->measured_at,
                    'date_only' => $activity->time_precision === 'date' ? $activity->measurementDate() : null,
                    'basis' => $activity->time_precision === 'date' ? 'Tanggal pengukuran · jam/zona tidak dicatat' : 'Waktu pengukuran', 'note' => 'Metode: '.$activity->method.'. Bukan diagnosis atau kondisi aset tervalidasi.',
                    'url' => route('pdm.show', $activity), 'link_label' => 'Buka aktivitas',
                ];
            }
        } catch (Throwable) {
            $states['pdm'] = 'unavailable';
            $counts['pdm'] = 0;
            $events = array_values(array_filter($events, fn ($event) => $event['source'] !== 'pdm'));
        }
        try {
            // Exact membership includes affected/cause assets, not just the
            // primary asset. Keep cancellations visible, without reading audit
            // snapshots, WO relationships or inferring an asset operating state.
            $observations = AssetDisruption::forAsset($reference)
                ->with(['members' => fn ($query) => $query->where('asset_ref', $reference)->select(['id', 'asset_disruption_id', 'asset_ref', 'role'])])
                ->orderByDesc('occurred_on')->orderByRaw('CASE WHEN occurred_at IS NULL THEN 1 ELSE 0 END')
                ->orderByDesc('occurred_at')->orderByDesc('id')->limit(25)
                ->get(['id', 'event_type', 'description', 'occurred_on', 'occurred_at', 'status']);
            $states['disruptions'] = $observations->isEmpty() ? 'empty' : 'available';
            $counts['disruptions'] = $observations->count();
            foreach ($observations as $observation) {
                $role = AssetDisruption::ROLES[$observation->roleFor($reference) ?? 'unknown'];
                $events[] = [
                    'source' => 'disruptions', 'reference' => $observation->reference(),
                    'title' => Str::limit($observation->description ?: AssetDisruption::TYPES[$observation->event_type], 180),
                    'status' => $observation->status === 'voided' ? 'Dibatalkan · histori dipertahankan' : 'Observasi manual · bukan validasi failure',
                    'at' => $observation->occurred_at, 'date_only' => $observation->occurred_at ? null : $observation->occurred_on,
                    'basis' => $observation->occurred_at ? 'Waktu observasi gangguan' : ($observation->occurred_on ? 'Tanggal observasi · jam/zona tidak dicatat' : 'Tanggal observasi belum diketahui'),
                    'note' => 'Peran aset: '.$role.'. Catatan ini bukan status operasi saat ini. Satu kejadian bisa melibatkan beberapa aset; jangan dijumlahkan sebagai total plant.',
                    'url' => route('disruptions.show', $observation), 'link_label' => 'Buka log gangguan',
                ];
            }
        } catch (Throwable) {
            $states['disruptions'] = 'unavailable';
            $counts['disruptions'] = 0;
            $events = array_values(array_filter($events, fn ($event) => $event['source'] !== 'disruptions'));
        }
        usort($events, function ($left, $right) {
            $leftDate = $left['date_only'] ?? $left['at']?->setTimezone('Asia/Jakarta')->format('Y-m-d');
            $rightDate = $right['date_only'] ?? $right['at']?->setTimezone('Asia/Jakarta')->format('Y-m-d');

            // Calendar grouping is not a fabricated midnight instant. Within a
            // date, timed records display first; date-only order is unspecified.
            return strcmp($rightDate ?? '', $leftDate ?? '')
                ?: (($right['at'] !== null) <=> ($left['at'] !== null))
                ?: ($right['at'] <=> $left['at'])
                ?: strcmp($left['source'].$left['reference'], $right['source'].$right['reference']);
        });

        return compact('events', 'states', 'counts');
    }

    private function sourceEvent(string $source, array $row, string $asset): array
    {
        $dates = match ($source) {
            'maintenance' => ['actual_start' => 'Actual start WO', 'source_changed_at' => 'Perubahan record WO · bukan waktu kejadian'],
            'fmea' => ['status_changed_at' => 'Perubahan status FMEA', 'source_updated_at' => 'Pembaruan record FMEA'],
            'health' => ['status_changed_at' => 'Perubahan status kondisi aset', 'source_updated_at' => 'Pembaruan record kondisi aset', 'source_created_at' => 'Pembuatan record kondisi aset'],
            'overhauls' => ['actual_start_at' => 'Mulai aktual overhaul', 'planned_start_at' => 'Rencana mulai overhaul · bukan pelaksanaan'],
        };
        $at = null;
        $basis = 'Tanggal belum tersedia';
        foreach ($dates as $field => $label) {
            if (! empty($row[$field])) {
                $at = $this->date($row[$field]);
                $basis = $at ? $label : 'Tanggal tidak valid / zona waktu belum jelas';
                break;
            }
        }
        $title = ($row['description'] ?? null) ?: ($row['source_number'] ?? null) ?: ($row['event_type'] ?? null) ?: self::LABELS[$source];
        $url = null;
        if ($source === 'maintenance') {
            $wo = $row['work_order_id'] ?? null;
            $url = is_string($wo) && str_starts_with($wo, 'workorder:MAXIMO:MXWODETAIL:BSR:IP:')
                ? route('work-orders.show', ['ref' => $wo, 'event' => $row['canonical_id'], 'asset_ref' => $asset])
                : route('work-orders.index', ['asset_ref' => $asset]);
        }

        return [
            'source' => $source, 'reference' => $row['canonical_id'], 'title' => $title,
            'status' => ($row['status'] ?? $row['lifecycle_status'] ?? null) ?: 'Status belum tersedia',
            'at' => $at, 'basis' => $basis, 'url' => $url, 'link_label' => 'Buka WO',
            'note' => match ($source) {
                'maintenance' => ($row['status'] ?? null) === 'WAPPR' ? 'Menunggu persetujuan/backlog; bukan gangguan tervalidasi.' : 'Record pekerjaan, bukan kejadian gangguan tervalidasi.',
                'fmea' => 'Record kajian sumber; tidak otomatis menjadi nilai risiko atau diagnosis.',
                'health' => 'Status record sumber, bukan bukti kondisi realtime atau skor Asset Wellness.',
                'overhauls' => 'Relasi aset berasal dari Mart. Rencana dan status bukan bukti penyelesaian.',
            },
        ];
    }

    private function date(string $value): ?CarbonImmutable
    {
        if (! preg_match('/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/D', $value)) {
            return null;
        }
        // -00:00 explicitly means unknown offset, not verified UTC. Reject
        // impossible offsets without rejecting valid future planning dates.
        if (str_ends_with($value, '-00:00')) {
            return null;
        }
        if (! str_ends_with($value, 'Z')) {
            $hours = (int) substr($value, -5, 2);
            $minutes = (int) substr($value, -2);
            if ($hours > 14 || $minutes > 59 || ($hours === 14 && $minutes !== 0)) {
                return null;
            }
        }
        try {
            $date = CarbonImmutable::parse($value);
            $errors = CarbonImmutable::getLastErrors();

            return is_array($errors) && ($errors['warning_count'] || $errors['error_count']) ? null : $date;
        } catch (Throwable) {
            return null;
        }
    }
}
