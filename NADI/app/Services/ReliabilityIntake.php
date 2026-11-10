<?php

namespace App\Services;

use App\Models\AssetDisruption;
use App\Models\ReliabilityReview;
use Illuminate\Support\Facades\Gate;
use Illuminate\Support\Facades\Validator;
use Illuminate\Validation\Rule;
use Illuminate\Validation\ValidationException;

/** Bounded preflight only. No import, classification, review or attestation writes. */
class ReliabilityIntake
{
    public const COLUMNS = ['event_id', 'event_version', 'review_revision', 'asset_ref', 'required_function', 'evidence', 'failure_at', 'restored_at', 'repair_state', 'active_intervals_text', 'timing_evidence', 'reason'];

    public const LIMIT = 50;

    public function preview(string $csv, string $asset, ReliabilityPeriod $period): array
    {
        if (strlen($csv) > 65536 || ! mb_check_encoding($csv, 'UTF-8')) {
            throw ValidationException::withMessages(['csv_text' => 'Gunakan CSV UTF-8 maksimal 64 KiB.']);
        }
        $stream = fopen('php://temp', 'r+');
        fwrite($stream, preg_replace('/^\xEF\xBB\xBF/', '', $csv));
        rewind($stream);
        try {
            if (fgetcsv($stream, null, ',', '"', '') !== self::COLUMNS) {
                throw ValidationException::withMessages(['csv_text' => 'Header dan urutan kolom harus sama dengan template. Gunakan pemisah koma.']);
            }
            $rows = [];
            while (($cells = fgetcsv($stream, null, ',', '"', '')) !== false) {
                if ($cells === [null]) {
                    continue;
                }
                if (count($rows) >= self::LIMIT) {
                    throw ValidationException::withMessages(['csv_text' => 'Maksimal 50 baris per pratinjau. Tidak ada baris yang diimpor.']);
                }
                if (count($cells) !== count(self::COLUMNS)) {
                    throw ValidationException::withMessages(['csv_text' => 'Jumlah kolom pada baris data '.(count($rows) + 1).' tidak sesuai. Kutip teks yang berisi koma atau baris baru.']);
                }
                $rows[] = $this->inspect(array_combine(self::COLUMNS, array_map(fn ($v) => trim($v ?? ''), $cells)), $asset, $period);
            }
            if (! $rows) {
                throw ValidationException::withMessages(['csv_text' => 'CSV belum memiliki baris data. Tidak ada catatan yang dibuat.']);
            }
        } finally {
            fclose($stream);
        }
        $counts = array_count_values(array_map(fn ($r) => (string) ((int) $r['values']['event_id']).'|'.$r['values']['asset_ref'], $rows));
        foreach ($rows as &$row) {
            if ($counts[(string) ((int) $row['values']['event_id']).'|'.$row['values']['asset_ref']] > 1) {
                $row['errors'][] = 'Kejadian/aset berulang dalam CSV. Rekonsiliasi menjadi satu baris; tidak digabung otomatis.';
            }
        }
        unset($row);

        return $rows;
    }

    public function inspect(array $values, string $asset, ReliabilityPeriod $period): array
    {
        $validator = Validator::make($values, [
            'event_id' => ['required', 'integer', 'min:1'], 'event_version' => ['required', 'integer', 'min:1'],
            'review_revision' => ['required', 'integer', 'min:0'], 'asset_ref' => ['required', 'string', 'max:240', Rule::in([$asset])],
            'required_function' => ['nullable', 'string', 'max:2000'], 'evidence' => ['nullable', 'string', 'max:4000'],
            'failure_at' => ['nullable', 'string', 'max:40'], 'restored_at' => ['nullable', 'string', 'max:40'],
            'repair_state' => ['required', Rule::in(array_keys(ReliabilityReview::REPAIR_STATES))],
            'active_intervals_text' => ['nullable', 'string', 'max:2500'], 'timing_evidence' => ['nullable', 'string', 'max:4000'],
            'reason' => ['nullable', 'string', 'max:2000'],
        ]);
        $row = ['values' => $values, 'errors' => $validator->errors()->all(), 'warnings' => [], 'event' => null];
        if ($row['errors']) {
            return $row;
        }
        $row['values'] = array_replace(array_fill_keys(self::COLUMNS, ''), $validator->validated());
        $event = AssetDisruption::forAsset($asset)->whereKey($values['event_id'])->first();
        if (! $event || ! Gate::allows('update-asset-disruption', $event) || $event->status !== 'recorded') {
            $row['errors'][] = 'Gunakan kejadian aktif milik Anda yang mencantumkan aset ini. Tidak ada identitas yang dibuat atau dipetakan otomatis.';

            return $row;
        }
        $row['event'] = $event;
        $revision = (int) (ReliabilityReview::where('asset_disruption_id', $event->id)->where('asset_ref', $asset)->max('revision') ?? 0);
        if ($event->version !== (int) $values['event_version'] || $revision !== (int) $values['review_revision']) {
            $row['errors'][] = 'Versi catatan/review berubah. Periksa bukti terbaru, lalu perbarui event_version dan review_revision.';
        }
        try {
            $timing = app(ReliabilityTiming::class);
            $failure = $timing->instant($values['failure_at'] ?? null, 'failure_at');
            $restored = $timing->instant($values['restored_at'] ?? null, 'restored_at');
            if ($restored && (! $failure || $restored->lt($failure))) {
                $row['errors'][] = 'Kembali siap memerlukan onset tepat dan tidak boleh mendahuluinya.';
            }
            $intervals = $timing->intervals($values['active_intervals_text'] ?? null, $failure, $restored);
            if (($values['repair_state'] === 'completed' && ! $intervals) || (in_array($values['repair_state'], ['unknown', 'not_applicable'], true) && $intervals) || ($values['repair_state'] === 'ongoing' && $restored)) {
                $row['errors'][] = 'Status perbaikan tidak sesuai interval atau waktu kembali siap.';
            }
            if (! $failure) {
                $row['warnings'][] = 'Onset belum diketahui. Tanggal observasi tidak diubah menjadi timestamp atau bukti onset.';
            } elseif (! $period->containsDate($failure->setTimezone(ReliabilityEvidence::ZONE)->toDateString())) {
                $row['warnings'][] = 'Onset di luar periode dipilih. Jangan menggeser waktu agar masuk periode.';
            }
            if (! $restored) {
                $row['warnings'][] = 'Kembali siap belum diketahui; bukan berarti masih berhenti atau nol durasi.';
            }
            if (($failure || $restored || $intervals || $values['repair_state'] !== 'unknown') && mb_strlen(trim($values['timing_evidence'] ?? '')) < 5) {
                $row['warnings'][] = 'Referensi bukti waktu/status perlu dilengkapi sebelum menyimpan review.';
            }
        } catch (ValidationException $error) {
            foreach ($error->errors() as $field => $messages) {
                foreach ($messages as $message) {
                    $row['errors'][] = $field.': '.$message;
                }
            }
        }
        foreach (['required_function' => 'Fungsi yang diperlukan', 'evidence' => 'Referensi bukti klasifikasi', 'reason' => 'Alasan review'] as $key => $label) {
            if (mb_strlen(trim($values[$key] ?? '')) < 5) {
                $row['warnings'][] = $label.' perlu diperiksa/dilengkapi. CSV tidak mengesahkan kehilangan fungsi.';
            }
        }

        return $row;
    }
}
