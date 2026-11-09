# Logbook PdM dan tindak lanjut lokal

Implementasi 7 November 2026, checkout Laravel NADI.

- `/pdm` adalah satu daftar inspeksi rutin, request, pengukuran template dan catatan inspeksi lama. SQL memaginasi 20 identitas sebelum membaca detail. Analisis yang tertaut ke aktivitas tidak dihitung sebagai inspeksi kedua.
- Engineer dapat mencatat request terlebih dahulu melalui form sederhana: peminta, keluhan, referensi dan aset bila sudah diketahui. Hasil/temuan dapat dilengkapi kemudian dalam catatan yang sama. Request tanpa hasil tidak otomatis membuat rekomendasi.
- Pengukuran template memilih jenis rutin/request. Request memerlukan peminta dan keluhan. Nilai, satuan, snapshot template, tanggal/zona, konfirmasi manual, dan pemeriksaan aset Mart yang sudah ada tetap berlaku.
- Dari detail pengukuran, **Catat analisis / buat rekomendasi** membuka form dengan aset, metode, tanggal dan identitas request dari aktivitas tersebut. Satu analisis per aktivitas. Rekomendasi opsional, tetapi bila diisi memerlukan hasil, metode, tanggal dan aset yang diverifikasi dengan GET inventaris/Registry. Aktivitas lama tanpa jenis harus diklasifikasikan oleh penyusun lebih dahulu, bukan ditebak.
- `/action-board` menampilkan rekomendasi lokal dengan status manual Terbuka, Sedang ditindaklanjuti, atau Selesai dan target opsional. Hanya engineer penyusun yang dapat mengubahnya. WAPPR sumber tetap terpisah. Tidak ada pembuatan WO, approval, notifikasi eksternal, penilaian risiko atau diagnosis otomatis.
- Permintaan dan analisis memiliki kunci kirim ulang; constraint unik mencegah duplikasi analisis aktivitas. Versi optimistis mencegah formulir lama menimpa perubahan. Hubungan aset/aktivitas tidak dapat dialihkan setelah rekomendasi. Waktu pengukuran tidak dapat dialihkan setelah menjadi dasar analisis; pengukuran berbeda memakai aktivitas baru. Perubahan nilai atau konteks tetap draft dan menandai analisis untuk ditinjau kembali. Isi analisis dan status tindak lanjut tidak dihapus atau diubah otomatis.
- Endpoint `/inspections` dipertahankan sebagai tampilan ringkasan draft/rekomendasi kompatibel; catatan lama dan URL detail tidak dihapus. Data request lama yang tidak memiliki peminta tetap berlabel belum dicatat.

## Data dan migrasi

`2026_11_07_000001_link_pdm_inspections.php` menambah kolom hanya pada dua tabel draft lokal. Tidak memindah, menghapus, atau menggandakan histori. Jenis pengukuran lama nullable karena asal rutin/request tidak tercatat. Catatan inspection_drafts lama memang berasal dari alur permintaan; peminta tidak direka. Relasi unik nullable menghubungkan analisis dengan aktivitas PdM, dan request_key nullable menjaga kompatibilitas data lama.

Jalankan hanya di `database/development.sqlite` yang sudah ada setelah memeriksa konfigurasi dan backup. Jangan migrasikan database operasional. Semua fixture pengujian berada di SQLite memory dengan HTTP mock.

## Verifikasi

`PdmWorkflowTest` mencakup daftar tunggal/filter/pagination, request wajib peminta/keluhan, hasil tanpa rekomendasi, aset/method/tanggal dari pengukuran, kirim ulang, rekomendasi tanpa aset ditolak, outage mempertahankan input, status/owner/versi, hubungan immutable, data lama tetap unknown, dan GET-only. Suite PdM lama tetap menguji seluruh katalog form, satuan, zero-vs-missing, sumber snapshot dan batas akses.

## Ketelitian waktu pengukuran (7 November 2026)

- Form numerik baru memilih **Tanggal saja** secara default. `measured_on`
  menyimpan tanggal kalender literal `YYYY-MM-DD`, `time_precision=date`,
  sedangkan `measured_at` dan `timezone` benar-benar `NULL`. Tidak ada jam 00:00
  atau zona waktu asumsi. Tanggal masa depan dan tanggal tidak valid ditolak.
- Pilihan **Tanggal dan jam** menyimpan timestamp UTC beserta zona sumber dan
  tanggal kalender lokal. Detik dipertahankan; kiriman lama sampai menit tetap
  diterima. Ini dukungan format waktu, bukan koneksi sensor atau sampling 24 jam.
- Detail, edit, logbook, history dan timeline menyebut ketelitian waktu. Tanggal
  saja tidak dikonversi zona. Pengukuran berkala tidak diasumsikan harian, tidak
  diinterpolasi dan tidak dianggap realtime. Tidak ada perubahan ambang/diagnosis.
- Logbook/history dikelompokkan menurut tanggal kalender sumber; record berjam
  ditampilkan lebih dahulu pada tanggal yang sama, lalu record tanggal saja.
  Urutan kelompok ini bukan bukti urutan kejadian intrahari. Timeline memakai
  tanggal WIB untuk record berjam dan tanggal apa adanya untuk record tanggal
  saja, dengan ketidakpastian intrahari dinyatakan. Record tanpa tanggal yang
  valid tetap berada di akhir cuplikan.
- Analisis tertaut memakai tanggal kalender sumber, bukan tanggal UTC. Setelah
  analisis tertaut, tanggal, jam, zona dan jenis ketelitian tidak dapat dialihkan.
  Edit nilai/deskripsi tetap draft dan memerlukan review analisis kembali.
- Migrasi `2026_11_07_000002_support_pdm_date_precision.php` mempertahankan waktu
  lengkap dan relasi lama, menambahkan ketelitian/tanggal, serta melonggarkan
  nullability timestamp/zona. Tanggal lokal record lama diturunkan dari timestamp
  dan zona yang sudah tersimpan. Rollback ditolak bila ada record tanpa waktu
  lengkap agar tidak menghapus data atau mengarang waktu. Database development
  harus dibackup melalui SQLite backup sebelum migrasi, bukan diganti.
- Pengujian memakai SQLite memory dan database QA sementara; angka Excel tidak
  diimpor ke database pengguna. `PdmDatePrecisionTest` dan `PdmDateMigrationTest`
  mencakup literal date/NULL, detik, peralihan tanggal UTC, compatibility, validasi,
  urutan campuran, timeline, analisis terkunci, outage, anti-duplikat dan migrasi.

## Koreksi pengukuran dan tinjauan analisis (8 November 2026)

- Koreksi PdM menyimpan nilai/konteks sebelum dan sesudah dalam audit yang sama
  dengan perubahan draft. Kegagalan audit membatalkan koreksi; versi formulir lama
  tetap ditolak. Audit lama tanpa rincian tidak direkonstruksi.
- Analisis baru mencatat versi dan fingerprint nilai/konteks yang ditinjau dalam
  audit existing, tanpa kolom atau migrasi baru. Perubahan bukti menampilkan
  **Analisis perlu ditinjau** di logbook, detail, daftar inspeksi dan Action Board.
  Penyimpanan ulang tanpa perubahan bukti tidak membuat analisis stale.
- Analisis lama tanpa basis tercatat berstatus belum terverifikasi, bukan otomatis
  dianggap sesuai. Engineer dapat menyimpan progres tanpa menghapus penanda;
  penanda baru bersih setelah mencentang tinjauan eksplisit atas pengukuran terkini.
  Form analisis membawa versi pengukuran dan pemeriksaan di dalam transaksi
  menolak tab lama. Temuan/rekomendasi tetap keputusan engineer, bukan diagnosis
  atau pengesahan otomatis.
- Batas tanggal saja untuk pengukuran dan inspeksi mandiri memakai hari kalender
  Asia/Jakarta (WIB), bukan UTC. Ini hanya batas validasi; tanggal tetap literal
  tanpa jam/zona yang direka. Inspeksi tertaut memakai tanggal sumber yang sudah
  tervalidasi, termasuk WIT yang lebih dulu berganti hari.

Regresi tambahan memakai SQLite memory dan HTTP mock: koreksi 10 menjadi 1,
riwayat nilai, basis unknown, status tanpa review, review eksplisit, tab lama,
kirim ulang, penyimpanan tanpa perubahan, rollback audit, dan pergantian hari WIB/WIT.

## Edit lokal saat Mart tidak tersedia

- Koreksi draft pengukuran memakai identitas aset/template yang sudah tersimpan
  dan tidak boleh menggantinya. Perubahan nilai tetap dicatat di audit dan membuat
  analisis perlu ditinjau sesuai aturan di atas, tanpa bergantung pada koneksi Mart.
- Inspeksi mandiri dengan aset yang tidak berubah dapat menyimpan hasil,
  rekomendasi dan status lokal. Analisis yang tertaut memakai identitas dari
  pengukuran itu sendiri. Ini bukan pemeriksaan ulang kesegaran atau kondisi aset.
- Draft tanpa aset yang menambahkan identitas, penggantian aset yang masih
  diperbolehkan, dan catatan baru yang tidak tertaut tetap memerlukan verifikasi
  Mart. Catatan lain tidak dijadikan cache untuk melewati pemeriksaan itu.
- Role/owner, versi formulir, validasi bukti dan transaksi audit tetap berlaku.
  Regresi outage menguji penyimpanan lokal tanpa request sumber, penolakan
  identitas baru, isian yang dipertahankan, dan tinjauan analisis sesudah koreksi.

## Bukti efektivitas tindak lanjut (9 November 2026)

- Action Board dan detail rekomendasi menautkan halaman **Bukti efektivitas**.
  Status pelaksanaan lama (Terbuka / Sedang ditindaklanjuti / Selesai) tetap
  terpisah. Selesai tidak otomatis efektif; tanpa review tampil **Efektivitas
  belum dinilai**. Tidak ada perubahan status, WO, approval atau risiko otomatis.
- Engineer penyusun mencatat tindakan yang benar-benar dilakukan, tanggal
  selesai literal, dua referensi pengukuran dan titik numerik, alasan/kriteria,
  serta keputusan **Belum dapat dinilai**, **Efektif menurut engineer**, atau
  **Perlu tindakan lagi**. Pengakuan tinjauan eksplisit wajib. Role lain hanya
  membaca. Keputusan efektif bukan bukti sebab-akibat atau pengesahan pekerjaan.
- Pemilih menampilkan 50 pengukuran terbaru pada aset persis, ditambah bukti yang
  sedang dipilih. Input ID lanjutan dapat memilih catatan lebih lama tanpa
  menganggap daftar terbaru sebagai seluruh histori. Pilihan eksplisit kosong
  mengosongkan bukti, bukan diam-diam memakai review sebelumnya.
- Keputusan efektif/perlu tindakan lagi membutuhkan dua aktivitas berbeda,
  asset_ref sama dengan rekomendasi, template/snapshot/metode/titik/satuan identik,
  serta alat, mode, kondisi operasi dan titik/lokasi yang lengkap dan sama.
  Fingerprint tidak dipercaya sendirian; snapshot penuh diperiksa. Angka harus
  finite dan terukur; nol tetap nol, kosong tidak diisi, tidak ada konversi unit.
  Template review-only, titik bukan numerik dan data tak sebanding tidak lolos.
- Tanggal pengukuran sebelum harus lebih awal dan sesudah lebih akhir dari
  tanggal tindakan. Karena waktu tindakan hanya tanggal, bukti pada hari yang
  sama belum membuktikan urutan intrahari dan tidak dipaksakan. Waktu/zona tidak
  direka. Analisis PdM tertaut yang unknown/stale harus ditinjau ulang dahulu
  melalui alur analisis existing sebelum membuat kesimpulan efektivitas.
- Bila bukti belum lengkap/sebanding, engineer masih dapat mencatat tindakan
  dan alasan dengan keputusan Belum dapat dinilai. Halaman mempertahankan
  blocker bukti secara eksplisit, tanpa angka, diagnosis atau kesimpulan buatan.
- Setiap penyimpanan adalah revisi append-only pada `action_effectiveness_reviews`:
  keputusan, actor, tindakan, tanggal, rekomendasi dan snapshot pengukuran saat
  dinilai tetap tersedia. Form lama ditolak berdasarkan versi rekomendasi,
  versi kedua pengukuran dan ID review terakhir. Token request menjaga replay
  tidak menggandakan hasil atau berpindah ke rekomendasi lain.
- Koreksi nilai/konteks/template/rekomendasi setelah review menampilkan **Bukti
  berubah · tinjau ulang**, tanpa menulis ulang snapshot atau keputusan lama.
  Versi bertambah tanpa perubahan isi tidak otomatis membuat review stale.
  Perubahan progres/target saja juga tidak mengubah bukti efektivitas.

Migrasi kompatibel `2026_11_09_000003_create_action_effectiveness_reviews.php`
menambah satu tabel di SQLite development existing, tanpa backfill atau
kesimpulan untuk record lama. Aktivasi runtime memerlukan verifikasi target dan
backup SQLite terlebih dahulu; pengujian tidak mengaktifkan migrasi pengguna.

Verifikasi: `ActionEffectivenessTest` mencakup bukti kosong/nol/nonfinite,
ketelitian tanggal dan urutan, identitas/konteks/snapshot/unit, analisis stale,
role/owner/guest/session nonaktif, konflik versi, replay lintas rekomendasi,
append-only history, XSS, dan label Action Board. Regresi bersama PdmWorkflow,
AssetPriority, DraftFeatures dan WorkflowJourney lulus 62 tes / 837 asersi.
Semua fixture menggunakan SQLite memory serta HTTP mock. QA browser dengan
Playwright lokal lulus 9 kelompok pemeriksaan di SQLite sementara terpisah:
pemilihan bukti/zero, tampilan 1440/390/320px tanpa page overflow, simpan dan
replay tanpa duplikat, revisi append-only, tab stale, Batal, Back/Forward, label
Action Board, serta snapshot historis. Tidak ada page error. Screenshot desktop
dan mobile diperiksa; semua 60 request browser hanya menuju origin QA loopback.
Fixture bukan bukti lapangan dan tidak masuk ke database pengguna. Bukti QA lokal
tersimpan di `/tmp/nadi-action-evidence-20261109/` (check.cjs, results.json dan
screenshot). Aktivasi migration development dan readiness produksi tetap terpisah.
