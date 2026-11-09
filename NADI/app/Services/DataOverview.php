<?php

namespace App\Services;

use App\Models\InspectionDraft;
use App\Models\PdmActivity;
use DateTimeImmutable;
use Throwable;

class DataOverview
{
    public function snapshot(ReliabilityMart $mart): array
    {
        $inventory = $this->read(function () use ($mart): array {
            $summary = $mart->inventorySummary();
            if ($summary['last_completed_at'] !== null) {
                new DateTimeImmutable($summary['last_completed_at']);
                $errors = DateTimeImmutable::getLastErrors();
                if ($errors !== false && ($errors['warning_count'] || $errors['error_count'])) {
                    throw new \RuntimeException('Invalid scan timestamp.');
                }
            }

            return $summary;
        });
        $backlog = $this->read(fn () => $mart->waitingApproval(0));
        $pdm = $this->read(fn () => PdmActivity::query()->count());
        $recommendations = $this->read(fn () => InspectionDraft::query()->whereNotNull('recommendation')->where('recommendation', '!=', '')->count());
        $classified = $inventory === null ? null : $inventory['total'] - $inventory['unknown'];
        $classificationPercent = $inventory !== null && $inventory['total'] > 0
            ? round(100 * $classified / $inventory['total'], 1) : null;

        $metrics = [
            $this->metric('inventory_total', 'Asset terkumpul', $inventory['total'] ?? null, 'aset', 'Reliability Mart · inventory-summary', 'BSR / IP · hierarki CS01', 'Termasuk System dan kategori belum diketahui. Bukan seluruh aset BSR.', 'assets.index'),
            $this->metric('wappr_records', 'WO menunggu approval', $backlog['meta']['total'] ?? null, 'record WO', 'Reliability Mart · maintenance-events', 'BSR / IP · aset Registry · status WAPPR', 'Jumlah record, bukan WO unik atau kejadian gangguan. Tidak sebanding langsung dengan inventaris CS01.', 'action-board'),
            $this->metric('pdm_entries', 'Entri pengukuran PdM', $pdm, 'draft', 'SQLite development · PdM', 'Seluruh draft PdM lokal', 'Entri lokal, bukan bukti kondisi sehat atau hasil approval.', 'pdm.index'),
            $this->metric('inspection_recommendations', 'Rekomendasi inspeksi', $recommendations, 'draft', 'SQLite development · inspeksi', 'Draft lokal dengan rekomendasi terisi', 'Dapat terkait entri PdM. Kedua jumlah draft tidak dijumlahkan sebagai inspeksi unik.', 'inspections.index'),
        ];
        $quality = [
            ['label' => 'Cakupan inventaris', 'state' => $inventory === null ? 'Belum tersedia' : ($inventory['complete'] ? 'Lengkap saat scan' : 'Parsial'),
                'detail' => $inventory === null ? 'Respons agregat belum tersedia atau tidak lolos validasi cakupan dan jumlah.' : ($inventory['complete'] ? 'Baseline lengkap dan tidak ada proyeksi tertunda pada scan yang dilaporkan.' : 'Belum ada bukti baseline lengkap dengan seluruh proyeksi selesai.'),
                'source' => 'inventory-summary · coverage'],
            ['label' => 'Kategori aset', 'state' => $inventory === null ? 'Belum tersedia' : ($inventory['total'] === 0 ? 'Tidak ada populasi' : number_format($classificationPercent, 1, ',', '.').'% berkategori'),
                'detail' => $inventory === null ? 'Kelengkapan kategori belum dapat dihitung.' : number_format($classified, 0, ',', '.').' dari '.number_format($inventory['total'], 0, ',', '.').' aset memiliki kategori; '.number_format($inventory['unknown'], 0, ',', '.').' belum dikategorikan. Acuan Excel engineer dengan kecocokan ID tepat. Ini bukan skor kepercayaan atau validasi Asset Wellness.',
                'source' => 'inventory-summary · counts / classification'],
            ['label' => 'Kesegaran sumber', 'state' => 'Belum dapat dipastikan',
                'detail' => 'Waktu baca halaman dan tanggal scan bukan waktu sinkronisasi terakhir. Respons HTTP berhasil tidak membuktikan data sumber masih baru.',
                'source' => 'Metadata sinkronisasi sumber belum tersedia di ringkasan ini'],
            ['label' => 'WAPPR & gangguan', 'state' => $backlog === null ? 'Belum tersedia' : 'Backlog, bukan gangguan',
                'detail' => 'WAPPR dipisahkan sebagai antrean approval. Jumlah WO tidak sama dengan jumlah kejadian gangguan tervalidasi.',
                'source' => 'maintenance-events · status WAPPR · Registry'],
            ['label' => 'Pengukuran & rekomendasi', 'state' => $pdm === null || $recommendations === null ? 'Sebagian belum tersedia' : 'Draft lokal',
                'detail' => 'Kelengkapan pengisian tidak membuktikan akurasi pengukuran. Rekomendasi belum berarti persetujuan, pelaksanaan, atau WO sumber dibuat.',
                'source' => 'Store development NADI'],
            ['label' => 'Kondisi realtime & Asset Wellness', 'state' => 'Belum dinilai',
                'detail' => 'Ringkasan ini tidak mengukur kondisi realtime, skor Asset Wellness, reliability, ataupun jumlah gangguan tervalidasi. Tidak ada nilai pengganti atau asumsi nol.',
                'source' => 'Tidak ada sumber tervalidasi untuk metrik ini'],
        ];

        return ['observed_at' => now()->toIso8601String(), 'inventory' => $inventory, 'metrics' => $metrics, 'quality' => $quality];
    }

    public function reportRows(array $snapshot): array
    {
        $rows = [];
        foreach ($snapshot['metrics'] as $metric) {
            $rows[] = [$metric['key'], $metric['value'], $metric['unit'], $metric['state'], $metric['source'], $metric['scope'], $metric['definition'], $snapshot['observed_at']];
        }
        foreach (['equipment', 'component', 'part', 'system', 'unknown', 'pending_projection'] as $key) {
            $value = $snapshot['inventory'][$key] ?? null;
            $rows[] = ['inventory_'.$key, $value, 'aset', $value === null ? 'UNAVAILABLE' : 'AVAILABLE', 'Reliability Mart · inventory-summary', 'BSR / IP · hierarki CS01', 'Kategori mengikuti acuan dokumen, bukan validasi kondisi. pending_projection adalah backlog proyeksi.', $snapshot['observed_at']];
        }
        $rows[] = ['inventory_coverage', $snapshot['inventory'] === null ? null : ($snapshot['inventory']['complete'] ? 'COMPLETE_AS_OF_MANUAL_SCAN' : 'PARTIAL'), '', $snapshot['inventory'] === null ? 'UNAVAILABLE' : 'AVAILABLE', 'Reliability Mart · inventory-summary', 'BSR / IP · hierarki CS01', 'Lengkap saat scan tidak menjamin kesegaran saat ini.', $snapshot['observed_at']];
        $rows[] = ['last_completed_scan', $snapshot['inventory']['last_completed_at'] ?? null, 'ISO-8601', isset($snapshot['inventory']['last_completed_at']) ? 'AVAILABLE' : 'UNAVAILABLE', 'Reliability Mart · inventory-summary', 'BSR / IP · hierarki CS01', 'Waktu scan, bukan sinkronisasi terakhir. observed_at adalah waktu baca laporan.', $snapshot['observed_at']];
        foreach ($snapshot['quality'] as $quality) {
            $rows[] = [$quality['label'], $quality['state'], '', 'CONTEXT', $quality['source'], '', $quality['detail'], $snapshot['observed_at']];
        }

        return $rows;
    }

    private function metric(string $key, string $label, ?int $value, string $unit, string $source, string $scope, string $definition, string $route): array
    {
        return compact('key', 'label', 'value', 'unit', 'source', 'scope', 'definition', 'route') + ['state' => $value === null ? 'UNAVAILABLE' : 'AVAILABLE'];
    }

    private function read(callable $read): mixed
    {
        try {
            return $read();
        } catch (Throwable) {
            return null;
        }
    }
}
