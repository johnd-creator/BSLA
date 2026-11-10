<?php

namespace App\Services;

use App\Models\AssetPriority;
use App\Models\PdmActivity;

/** Read-only draft. No raw reading, WO count or absence of data is a health score. */
class AssetWellness
{
    public const VERSION = 'asset-wellness-draft-v2';

    public const PDM_LIMIT = 500;

    public const COMPONENTS = [
        'pdm' => ['label' => 'Kondisi PdM', 'weight' => 45],
        'operations' => ['label' => 'Kondisi operasi', 'weight' => 25],
        'failure' => ['label' => 'Failure tervalidasi', 'weight' => 20],
        'maintenance' => ['label' => 'Pemeliharaan', 'weight' => 10],
    ];

    public function report(string $asset, int|ReliabilityPeriod $year, ReliabilityMart $mart): array
    {
        $period = $year instanceof ReliabilityPeriod ? $year : ReliabilityPeriod::year($year);
        $year = $period->start->year;
        $reliability = app(ReliabilityEvidence::class)->report($asset, $period, $mart);
        $pdm = $this->pdm($asset, $period);
        $exposure = $reliability['manual_operating'];
        $failures = collect($reliability['events'])->filter(fn ($event) => $event['state'] === 'failure' && $event['failure_at'] !== null && $event['in_year'])->values();
        $priority = AssetPriority::where('asset_ref', $asset)->where('status', 'active')->first();
        $wo = $reliability['work_orders'];
        $components = [
            'pdm' => [...self::COMPONENTS['pdm'], 'score' => null, 'evidence' => $pdm,
                'coverage' => 'Matriks saat ini memakai titik/konteks dalam rencana PdM lokal aktif. Jumlah pengukuran periode ini bukan persen cakupan atau jaminan semua titik wajib aset telah dipetakan.',
                'freshness' => $pdm['latest_measurement'] ? 'Pengukuran terakhir: '.$pdm['latest_measurement'].'. Batas usia yang diterima belum ditentukan.' : 'Tanggal pengukuran belum tersedia.',
                'confidence' => 'Belum dinilai: analisis lokal yang sesuai versi belum mengesahkan batas kondisi, kualitas alat atau cakupan.',
                'blocker' => 'Perlu batas kondisi per aset/titik, unit, mode operasi, kualitas alat dan normalisasi skor yang disepakati.',
                'url' => route('pdm.history', ['asset_ref' => $asset])],
            'operations' => [...self::COMPONENTS['operations'], 'score' => null,
                'evidence' => ['status' => $exposure['status'], 'coverage_percent' => $exposure['coverage_percent'], 'known_seconds' => $exposure['known_seconds'], 'operating_seconds' => $exposure['operating_seconds'], 'seconds' => $exposure['seconds'], 'quality' => $exposure['quality'], 'truncated' => $exposure['truncated'],
                    'latest_ended_at' => collect($exposure['records'])->where('review_state', 'verified')->max('ended_at')],
                'coverage' => 'Cakupan waktu log manual terhadap periode terpilih (tahun kalender tetap termasuk sisa tahun jika belum tutup). UNKNOWN, GAP dan OVERLAP dikecualikan; bukan persen kesehatan atau cakupan parameter proses.',
                'freshness' => 'Akhir log terverifikasi bukan jaminan kondisi saat ini. Historian belum menjadi input Wellness; tidak ada polling baru.',
                'confidence' => 'Belum dinilai: verifikasi log RUN/STOP/STANDBY tidak membuktikan parameter proses berada dalam batas sehat.',
                'blocker' => 'Perlu parameter operasi, mapping aset, batas per mode, kualitas/usia sinyal dan aturan cakupan. STOP/STANDBY tidak otomatis buruk.',
                'url' => $period->annual ? route('reliability.operating.index', ['asset_ref' => $asset, 'year' => $year]) : route('reliability.calculation', ['asset_ref' => $asset, ...$period->query()]).'#calculation-exposure'],
            'failure' => [...self::COMPONENTS['failure'], 'score' => null,
                'evidence' => ['status' => $reliability['coverage']['local_rows_truncated'] ? 'PARTIAL' : 'LOCAL_REVIEW_ONLY', 'reviewed_onset_count' => $failures->count(), 'quality' => $reliability['quality'], 'coverage_status' => $reliability['coverage']['observation_coverage'],
                    'latest_failure_at' => $failures->max('failure_at'), 'latest_reviewed_at' => $failures->max('reviewed_at'), 'overlap_event_ids' => $reliability['overlap_event_ids'],
                    'rows' => $failures->sortByDesc('failure_at')->take(8)->map(fn ($event) => array_intersect_key($event, array_flip(['event_id', 'reference', 'event_version', 'review_revision', 'failure_at', 'reviewed_at'])))->values()->all()],
                'coverage' => 'Klasifikasi failure direview lokal dengan onset pasti di periode terpilih; tidak termasuk duplicate, stale, uncertain atau tanggal onset kosong. Bukan sensus failure lengkap.',
                'freshness' => 'Waktu kejadian dan waktu review ditampilkan terpisah; review baru tidak membuat kejadian lama menjadi kondisi terbaru.',
                'confidence' => 'Belum dinilai untuk Wellness: validasi kejadian lokal dan pengesahan KPI Reliability tidak mengesahkan model Wellness.',
                'blocker' => 'Perlu cakupan sensus, dampak, periode, aturan recurrence dan normalisasi. Konflik interval tetap ditelusuri di Reliability.',
                'url' => route('reliability.index', ['asset_ref' => $asset, ...$period->query()])],
            'maintenance' => [...self::COMPONENTS['maintenance'], 'score' => null,
                'evidence' => ['status' => $wo['state'], 'work_order_count' => $wo['selected_year']['work_orders'] ?? null, 'all_year_counts' => $wo['all_year_counts']],
                'coverage' => ($period->annual ? '' : 'Agregat rentang belum tersedia; jumlah WO ditahan, tidak diprorata dari tahun. ').'WO unik yang tersimpan di Mart, tahun actual start WIB. Bukan seluruh pekerjaan yang seharusnya dikerjakan dan bukan jumlah failure.',
                'freshness' => 'Kesegaran koleksi sumber belum diketahui. HTTP berhasil atau waktu baca laporan bukan bukti data baru.',
                'confidence' => 'Belum dinilai: WAPPR, CLOSE, volume WO, labor dan durasi actual tidak membuktikan efektivitas pemeliharaan.',
                'blocker' => 'Perlu rencana/jatuh tempo, penyelesaian tervalidasi dan bukti efektivitas. WO hanya konteks, tidak menjadi penalti failure kedua.',
                'url' => route('work-orders.index', ['asset_ref' => $asset, 'year' => $year])],
        ];

        $methodDraft = app(AssetWellnessMethod::class)->report($asset, $period);
        if (! $period->annual) {
            foreach ($components as $key => &$component) {
                $component['weight'] = $methodDraft['policy']?->rules['components'][$key]['weight'] ?? null;
            }
            unset($component);
        }

        return ['schema_version' => self::VERSION, 'observed_at' => now()->toIso8601String(), 'asset_ref' => $asset, 'asset' => $reliability['asset'], 'year' => $year,
            'status' => 'INSUFFICIENT_DATA', 'status_label' => 'Belum cukup data', 'score' => null, 'official_score' => null, 'method_status' => 'DRAFT_NOT_APPROVED',
            'period' => $period->metadata(),
            'method_draft' => $methodDraft,
            'completeness' => app(AssetWellnessCompleteness::class)->report($asset),
            'method_note' => $period->annual ? 'Bobot 45/25/20/10 hanya ilustrasi draft untuk diskusi engineer. Usulan threshold dicatat terpisah. Belum ada normalisasi, kategori sehat atau metode yang disahkan.' : 'Bobot rentang hanya berasal dari usulan engineer untuk scope exact ini. Kosong berarti belum diputuskan. Bobot, teks normalisasi dan threshold masih draft; tidak menghasilkan skor atau kategori sehat.',
            'components' => $components, 'scored_components' => 0, 'confidence' => 'Belum dapat dinilai', 'criticality' => 'Belum dipetakan',
            'attention_required' => $priority?->urgency === 'immediate',
            'priority' => $priority ? ['id' => $priority->id, 'reference' => $priority->reference(), 'version' => $priority->version, 'urgency' => $priority->urgency, 'observed_condition' => $priority->observed_condition, 'reasoning' => $priority->reasoning, 'updated_at' => $priority->updated_at->toIso8601String()] : null,
            'reliability_evidence_hash' => $reliability['evidence_hash'], 'reliability_observed_at' => $reliability['observed_at'],
            'trace_note' => 'Laporan baca-saja, bukan snapshot immutable lintas sumber. Bukti Reliability memakai snapshot lokalnya sendiri; ringkasan PdM/prioritas dibaca sesudahnya. Tautan merujuk versi terbaru.',
        ];
    }

    private function pdm(string $asset, ReliabilityPeriod $period): array
    {
        $query = PdmActivity::where('asset_ref', $asset)->whereBetween('measured_on', [$period->start->toDateString(), $period->end->subDay()->toDateString()]);
        $count = (clone $query)->count();
        $activities = $query->with(['inspection.pdmReviewAudit'])->newestMeasurement()->limit(self::PDM_LIMIT)->get();
        $quality = ['current_analysis' => 0, 'stale_analysis' => 0, 'unknown_analysis' => 0, 'no_analysis' => 0, 'date_only' => 0];
        $rows = [];
        foreach ($activities as $activity) {
            $inspection = $activity->inspection;
            if ($inspection) {
                $inspection->setRelation('pdmActivity', $activity);
            }
            $hasAnalysis = $inspection && $inspection->asset_ref === $asset && ($inspection->finding || $inspection->recommendation);
            $state = ! $hasAnalysis ? 'no_analysis' : match ($inspection->pdmReviewState()) {
                'stale' => 'stale_analysis', 'unknown' => 'unknown_analysis', default => 'current_analysis',
            };
            $quality[$state]++;
            $quality['date_only'] += $activity->time_precision === 'date' ? 1 : 0;
            if (count($rows) < 8) {
                $rows[] = ['id' => $activity->id, 'reference' => $activity->reference(), 'version' => $activity->version, 'measurement' => $activity->measurementLabel(), 'precision' => $activity->precisionLabel(), 'state' => $state, 'analysis_id' => $hasAnalysis ? $inspection->id : null];
            }
        }

        return ['count' => $count, 'inspected_count' => $activities->count(), 'truncated' => $count > self::PDM_LIMIT, 'quality' => $quality, 'rows' => $rows,
            'latest_measurement' => $activities->first() ? $activities->first()->measurementLabel().' · '.$activities->first()->precisionLabel() : null];
    }
}
