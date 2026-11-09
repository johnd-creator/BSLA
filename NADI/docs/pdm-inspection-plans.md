# Jadwal dan cakupan inspeksi PdM

`/pdm/plans` menambahkan rencana inspeksi lokal di atas logbook PdM existing.
Ini bukan scheduler collector, notifikasi, diagnosis atau kepatuhan historis.

## Identitas dan cakupan

- Satu rencana menyimpan aset inventori tepat, snapshot template/fingerprint,
  metode sumber, satu titik, satuan, alat/laporan, mode, kondisi operasi dan dasar
  pemilihan aset/sampling. Aset baru diverifikasi melalui GET Mart; bukan Registry
  enrollment. Template review-only tidak bisa dipakai.
- Konteks menggunakan batas identitas yang sama dengan tren: kecocokan tepat,
  tanpa normalisasi ejaan atau penggabungan unit/template/OLD-NEW. Tidak menyalin
  deskripsi atau data master aset ke SQLite. Kombinasi identitas dan konteks yang
  sama tidak boleh memiliki dua rencana, termasuk antar-penyusun.
- Hanya pengukuran **rutin** cocok dengan nilai terisi yang menjadi bukti.
  Request/analisis, tanggal literal/instant masa depan, snapshot berbeda, satuan berbeda, nilai
  kosong atau angka tidak hingga tidak dihitung. Nol tetap nilai terukur.
- Koreksi pengukuran langsung dihitung kembali. Nilai yang dihapus menjadi kosong
  dapat membuat cakupan mundur ke bukti sebelumnya atau kembali belum diukur.
- Penelusuran maksimal 250 aktivitas cocok terbaru per rencana. Jika belum ada
  bukti valid dan masih ada catatan lebih lama, hasil **belum pasti**, bukan nol.
  Cakupan halaman memakai maksimal 20 rencana dan menyebut penyebut lokal ini;
  tidak menyatakan keseluruhan aset pabrik atau seluruh hasil pagination.

## Frekuensi dan tanggal

Frekuensi manual 1–365 hari, minggu, atau bulan kalender. Tanggal pertama disimpan
literal tanpa jam/zona. Berikutnya = tanggal sumber pengukuran cocok terakhir +
frekuensi, paling awal tanggal pertama. Tanpa bukti, tanggal pertama tetap jatuh
tempo; tidak dilompati otomatis. Bulan menggunakan akhir bulan bila hari asal
tidak tersedia, misalnya 31 Januari + 1 bulan menjadi 28/29 Februari.

Hari pembanding memakai Asia/Jakarta. Terlambat, jatuh tempo hari ini, terjadwal,
dan belum pasti dibedakan. Rencana dijeda tidak masuk cakupan aktif, tetapi tetap
tersimpan dengan riwayat. Cakupan segar memerlukan bukti yang interval aslinya
belum habis; memundurkan tanggal pertama tidak membuat bukti lama menjadi segar.
Tidak ada penghitung kepatuhan interval historis, interpolasi atau jam rekaan.

## Hak akses dan audit

Semua akun aktif dapat membaca. ENGINEER membuat dan memperbarui hanya rencana
milik sendiri; ADMIN tidak otomatis mewarisi hak engineering. Identitas titik dan
konteks tidak dapat diganti sesudah tersimpan. Untuk konteks baru, buat rencana
baru dan jeda yang lama bila perlu. Judul, frekuensi, tanggal, status dan catatan
bisa direvisi dengan alasan wajib, optimistic version dan snapshot audit atomik.
Request UUID menahan kirim ulang; constraint unik menahan duplikat identitas.
Tidak ada route hapus rencana/revisi. Update lokal tetap bisa saat Mart offline.
Pembuatan yang gagal mempertahankan isian dan tetap wajib verifikasi sumber.

## Data dan verifikasi

Migrasi additive `2026_11_09_000002_create_pdm_inspection_plans.php` menambah
`pdm_inspection_plans` dan `pdm_inspection_plan_revisions` pada store lokal existing.
Rollback ditolak bila ada rencana supaya histori tidak terhapus. Aktivasi runtime
memerlukan pemeriksaan target SQLite dan backup verified oleh workflow pemilik;
menulis migrasi dan tes memory tidak berarti migrasi database pengguna dijalankan.

`PdmInspectionPlanTest`: 16 tests / 170 assertions, memakai SQLite memory dan HTTP
mock. Cakupan: form/list/detail/edit, exact identity dan GET-only, role/owner,
idempotensi/duplikat, stale form, snapshot/audit rollback, outage, unit/context,
review-only, zero/missing, bulan akhir, batas hari WIB/WIT, paused/pagination,
bounded-search unknown, escaped text, larangan delete dan rollback populated. Scoped Pint lulus.
Angka ini adalah focused check, bukan bukti full-suite atau browser visual pass.


Regresi PdM gabungan setelah implementasi: 71 tests / 9.496 assertions lulus.
Browser QA memakai SQLite fixture terpisah di `/tmp`, bukan database development,
pada port loopback terpisah. Login, daftar/detail, edit jeda/aktif, Cancel/Back,
dan penolakan tab stale berhasil. Screenshot desktop dan mobile 390px diperiksa;
tidak ada document overflow atau error JavaScript. Create dipastikan melalui
feature tests dengan HTTP mock, bukan penyimpanan data riil lewat browser.
