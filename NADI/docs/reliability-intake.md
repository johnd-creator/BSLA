# Intake bukti pilot per aset/periode

Intake tersedia dari **Reliability → Buka intake bukti terpandu** pada
`/reliability/intake`. Ini panduan input data asli, bukan verifikasi, impor massal,
perhitungan baru atau approval otomatis.

## Alur engineer

1. Pilih Canonical ID exact BSR/IP dan tahun, 3/6/12 bulan, atau rentang tanggal.
   Rolling period dibekukan ke tanggal exact pada navigasi berikutnya.
2. Periksa catatan asal. Jika belum tercatat, buka form Log Gangguan existing dan
   simpan observasi asli. Bedakan penyebab/terdampak/unknown; tanggal saja tetap
   literal. Identitas baru tetap harus lolos pemeriksaan inventori/Mart existing.
3. Buka review terpandu existing per event/member aset. Isikan fungsi, bukti
   kehilangan fungsi, onset/kembali siap setelah pengujian, repair aktif/jeda,
   referensi tiap batas dan alasan. Unknown tetap kosong, bukan nol atau midnight.
4. Kembali ke intake untuk rekonsiliasi episode unik/duplicate/recurrence/reopen,
   stale review, konflik dan populasi. Ikuti link metode, log operasi dan laporan
   exact-period existing. Snapshot dan keputusan Supervisor tetap langkah terpisah.

Daftar menggunakan status dari ReliabilityEvidence existing, maksimal 2.000
observasi dan 20 per halaman. Tanpa tanggal ditampilkan lebih dahulu, diikuti
periode pilihan dan periode lain. Truncation/outage diberi label. Ini bukan
kelengkapan populasi dan tidak menyamakan tanggal observasi dengan onset.

## Pratinjau CSV opsional

Khusus ENGINEER dan kejadian aktif miliknya yang sudah mencantumkan aset exact.
Tidak membuat aset, observasi, review, snapshot, kebijakan atau approval.
Template berisi header saja, tanpa data operasional buatan:

`event_id,event_version,review_revision,asset_ref,required_function,evidence,failure_at,restored_at,repair_state,active_intervals_text,timing_evidence,reason`

- Tempel CSV UTF-8 berpemisah koma, maksimal 64 KiB / 50 baris. Urutan header wajib
  sama; sel berisi koma/baris baru dikutip menurut CSV. BOM UTF-8 diterima.
- Gunakan ID, versi event dan revisi review pada daftar. Revisi 0 berarti belum
  ada review. Versi/revisi diperiksa ulang saat membuka draft, dan guard existing
  tetap memeriksa ulang saat menyimpan review.
- Timestamp harus ISO-8601 detik dengan offset/Z. Date-only, naive, -00:00,
  kalender invalid, future, reversed, interval overlap dan boundary invalid
  ditolak memakai ReliabilityTiming existing. Interval memakai `awal | akhir`,
  satu interval per baris, maksimum 20; kru paralel tidak dijumlahkan.
- Duplikat event/aset dalam CSV ditandai pada semua kemunculan. Tidak ada merge,
  penghapusan atau klasifikasi duplicate otomatis. CSV bukan deduplikasi semantik
  seluruh populasi; kejadian berbeda tetap direkonsiliasi engineer.
- Batas kosong, referensi kurang lengkap dan onset di luar periode diberi peringatan,
  tidak diubah atau digeser. Validasi format tidak memverifikasi kebenaran bukti.
- Tombol **Buka draft untuk diperiksa** membawa satu baris ke form review existing
  lewat redirect GET dan flash sesi sementara. Tidak menyimpan business record.
  Classification selalu dimulai `uncertain`, duplicate target kosong, attestation
  tidak dicentang, request key baru. Blank tidak mewarisi waktu/keputusan lama.
- Kesalahan saat simpan kembali ke GET review yang valid dengan isian dipertahankan,
  bukan ke URL POST-only. Aset/periode exact tetap dibawa ke link dan redirect.
  Draft bukan autosave; reload/menutup halaman dapat membuang isian belum tersimpan.

ADMIN, MANAGER dan SUPERVISOR dapat membaca panduan tetapi tidak melakukan staging
CSV/draft. Server Gate tetap membatasi review milik engineer. Tidak ada migrasi,
source write, pengambilan sejarah, perubahan perhitungan KPI atau publikasi data sumber.

## Publication verification

See [public-source integration](publication.md) for the checks run against this
publication branch. Historical feature QA is not a fresh browser pass or an
engineering signoff. No source records, private catalogs, runtime data, database
activation, merge or deployment are included in publication.
