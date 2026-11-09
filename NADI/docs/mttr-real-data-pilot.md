# Pilot MTTR tanpa historian: kesiapan data dan uji alur

Pemeriksaan 9 November 2026 pada checkout dan runtime lokal existing. Ini hasil
persiapan pilot, bukan pengesahan KPI atau validasi kejadian operasional.

## Status pilot operasional

Pilot angka nyata masih menunggu evidence operator/engineer yang memadai.
Ringkasan WO dan tanggal actual pelaksanaan tidak membuktikan failure onset atau
return-to-service. Tidak dibuat observasi, metode, snapshot atau approval nyata
untuk menggantikan evidence yang belum tersedia. Identitas aset, angka sumber,
dan hasil pemeriksaan store lokal tidak disertakan dalam paket publik ini.
Historian bukan prasyarat MTTR, tetapi bukti batas waktu dan cakupan tetap wajib.

## Paket evidence minimum untuk memulai

Pilih satu aset dan satu tahun onset WIB. Untuk setiap kejadian nyata, siapkan:

1. Identitas catatan asal yang bisa ditelusuri: nomor/halaman log operator, laporan
   gangguan, atau bukti lapangan. WO boleh menjadi konteks pendukung.
2. Fungsi yang harus dipenuhi, bukti kehilangan fungsi, serta aset penyebab dan
   terdampak yang dibedakan. Jangan otomatis menyebut setiap trip sebagai failure.
3. Failure onset dan kembali siap setelah pengujian, lengkap dengan tanggal, jam,
   zona/offset, dan referensi bukti bagi masing-masing batas. Tanggal saja tetap
   tanggal saja; jangan mengisi midnight atau menyalin actual WO.
4. Jika memilih **active repair**, interval kerja aktif beserta jeda yang dikeluarkan.
   Jika memilih **restoration**, rentang onset sampai kembali siap termasuk waiting.
   Repair aktif yang belum diketahui tidak menghalangi restoration yang terbukti.
5. Daftar episode belum selesai, waktu belum pasti, duplicate, kejadian non-failure,
   dan recurrence yang belum direkonsiliasi. Jangan menyembunyikannya agar KPI lolos.
6. Evidence cakupan/populasi fungsi dan alasan pemilihan metode. Beberapa contoh
   lengkap hanya mendukung sample deskriptif sampai coverage yang diminta gerbang
   metode telah diperiksa; beberapa contoh bukan otomatis census lengkap.

Engineer memasukkan dan mereview observasi per member aset, memeriksa readiness
serta pembilang/penyebut, lalu menyimpan snapshot immutable. Supervisor memilih
**MTTR** pada snapshot yang masih sesuai bukti, memeriksa metode/hasil, dan melakukan
attestation sendiri. MTBF tetap null tanpa operating exposure yang lengkap dan
gerbang tahun tertutup yang sesuai. Perubahan evidence memerlukan rekonsiliasi,
metode/snapshot baru dan pengesahan ulang, tanpa menimpa keputusan historis.

Rincian UI dan batas metode ada di [evidence/review](reliability-evidence.md),
[mesin pilot](reliability-calculation.md) dan
[pengesahan Supervisor](reliability-supervisor-approval.md).

## Gap alur yang diperbaiki

Replay UUID snapshot sebelumnya memeriksa actor saja: scope aset/tahun berbeda
bisa diarahkan ke snapshot lama seolah permintaan itu tersimpan. Replay UUID review
memeriksa actor/event saja: member aset berbeda pada kejadian yang sama juga bisa
diarahkan ke review lama. Keduanya kini menolak scope berbeda dengan HTTP 409.
Snapshot memvalidasi scope sebelum replay dan sebelum membaca sumber. Replay
permintaan sama tetap idempotent; tidak membuat histori duplikat.

Perubahan terbatas pada controller review/snapshot, tanpa rumus baru, migrasi,
penyalinan sumber, perubahan permission role atau perubahan database operasional.

## Verifikasi increment ini

`tests/Feature/MttrPilotWorkflowTest.php` menggunakan SQLite `:memory:` dan HTTP
palsu. Seluruh observasi, review, metode, snapshot dan keputusan dibuat melalui
route pengguna, bukan menanam review langsung untuk melewati validasi controller.

- Dua episode restoration sintetis 4 dan 2 jam menghasilkan 21.600 detik / 2
  episode = 3 jam. Active repair tidak diketahui, WO context unavailable, log
  operasi kosong dan MTBF null. Angka ini hanya oracle test, bukan data pengguna.
- ENGINEER tidak dapat approve. SUPERVISOR dapat memilih MTTR saja; replay tidak
  menggandakan keputusan. Ekspor menyimpan report asli.
- Koreksi episode menjadi 6 jam membuat approval stale dan nilai resmi null.
  Rekonsiliasi metode, snapshot baru dan pengesahan ulang menghasilkan 4 jam;
  snapshot/keputusan awal tetap mempertahankan 3 jam.
- Replay snapshot lintas asset/tahun dan review lintas member ditolak. Kedua
  regresi terbukti gagal sebelum perbaikan dan lulus sesudahnya.
- **87 test / 821 assertions** lulus pada suite pilot, evidence, operating
  reliability dan snapshot consistency. Pint terfokus lulus. Ini uji HTTP route
  dan render server, bukan browser visual QA baru. QA browser terdahulu tercatat
  pada dokumen Supervisor dan calculation.

Tidak ada synthetic record di preview, pengesahan nyata, restart collector,
pembacaan PI, deployment, commit atau push dalam increment ini.
