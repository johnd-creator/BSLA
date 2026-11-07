<?php

namespace App\Services;

class WorkOrderEvidence
{
    private const TYPES = [
        'CM' => 'Korektif', 'PM' => 'Preventif', 'INSPECTION' => 'Inspeksi',
        'CALIBRATION' => 'Kalibrasi', 'REPAIR' => 'Perbaikan', 'EMERGENCY' => 'Darurat',
    ];

    public static function fromRecord(array $record): array
    {
        $raw = $record['classification_raw_work_type'] ?? null;
        $canonical = $record['event_type'] ?? null;
        $state = $record['classification_state'] ?? null;
        $category = $record['classification_canonical_category'] ?? null;
        // Unknown source codes and inconsistent mappings must not acquire invented meanings.
        $supported = isset(self::TYPES[$canonical ?? ''])
            && in_array($state, [null, 'CANONICAL_SUPPORTED', 'CANONICAL_ONLY'], true)
            && ($category === null || $category === $canonical)
            && ($raw === null || $raw === $canonical);
        $code = trim($record['failure_code'] ?? '');
        if ($code !== '') {
            $review = 'candidate';
            $label = 'Kandidat review';
            $reason = 'Ada failure code pada DTO Mart. Makna kode dan hubungan ke kejadian masih perlu validasi.';
        } elseif ($supported && in_array($canonical, ['CM', 'REPAIR', 'EMERGENCY'], true)) {
            $review = 'candidate';
            $label = 'Kandidat review';
            $reason = 'Tipe pekerjaan kanonis '.$canonical.' menjadi petunjuk review saja, bukan bukti gangguan.';
        } elseif ($supported) {
            $review = 'maintenance';
            $label = 'Pemeliharaan terklasifikasi';
            $reason = 'Tipe pekerjaan tersedia. Tidak membuktikan terjadi atau tidak terjadinya gangguan.';
        } else {
            $review = 'unknown';
            $label = 'Unknown · belum terklasifikasi';
            $reason = 'Makna tipe pekerjaan atau bukti kejadian belum tersedia. Tidak dianggap sehat atau gagal.';
        }

        return [
            'work_type' => $raw ?: ($canonical ?: 'Unknown'),
            'work_label' => $supported ? self::TYPES[$canonical] : 'Makna belum terverifikasi',
            'review' => $review, 'label' => $label, 'reason' => $reason,
            'date' => ($record['actual_start'] ?? null) ?: ($record['source_changed_at'] ?? null),
            'date_basis' => ! empty($record['actual_start']) ? 'Actual start WO' : (! empty($record['source_changed_at']) ? 'Perubahan record · bukan waktu kejadian' : 'Tanggal belum tersedia'),
        ];
    }
}
