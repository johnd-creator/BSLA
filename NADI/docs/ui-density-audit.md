# Audit UI/UX ringkas — 6 November 2026

## Arah tampilan

Tampilan Blade disederhanakan mengikuti pola starter Laravel: latar abu-abu netral,
panel putih, garis batas jelas, tombol utama gelap, dan formulir standar. Ini bukan
instalasi starter kit baru atau salinan tema Maximo. Tidak menambah dependensi UI.

## Temuan dan perubahan

- Header halaman sebelumnya berulang di breadcrumb, eyebrow, dan judul besar.
  Sekarang satu judul di header; keterangan draft/domain tetap terlihat bila ada.
- Sidebar desktop 246 px menjadi 208 px. Kartu identitas workspace yang berulang
  dihapus. Work Orders tersedia langsung pada submenu Asset dengan penanda aktif.
- Padding konten desktop 35/38/50 px menjadi 16 px. Header dasar 73 px menjadi
  minimum 52 px, dengan tinggi alami bila teks perlu membungkus.
- Padding vertikal sel tabel 21 px menjadi 8 px. Font isi tabel justru naik dari
  12 px menjadi 13 px; kepadatan tidak dicapai dengan mengecilkan teks.
- Header panel 22/24 px menjadi 10/12 px. Jarak form 22 px menjadi 14 px, input
  dasar 43 px menjadi 36 px. Di layar kecil kontrol tetap minimum 40 px.
- Login dua kolom dengan hero pemasaran menjadi satu kartu form. Wordmark NADI
  dipertahankan tanpa aksen teal, ilustrasi, gradient, atau logo dekoratif lama.
- Action Board, inspeksi, mapping, detail WO, role, dan Operasi memakai skala
  spacing yang sama. Placeholder kanvas tidak lagi memaksakan tinggi 390 px.
- Mobile memakai menu disclosure native yang dapat dilipat; desktop tetap terbuka.
  Pergantian breakpoint membuka kembali menu desktop. Tanpa JS, navigasi tetap
  tersedia. Tabel lebar tetap dapat digeser horizontal dalam kontainernya.
- Focus keyboard, skip link, label, CSRF, status draft/read-only, peringatan WAPPR,
  dan kondisi data belum terhubung dipertahankan. Indikator sumber tidak lagi
  memakai titik hijau yang bisa disalahartikan sebagai bukti koneksi/freshness.
- Beranda tetap kosong sesuai ruang lingkup sebelumnya.

## Verifikasi

Lulus pada code akhir:

- `composer test`: 54 tests / 505 assertions, termasuk empat regresi struktur UI.
- `vendor/bin/pint --test`.
- `npm run test:ui`: empat unit test untuk state navigasi desktop/mobile,
  perubahan breakpoint berulang, dan halaman tanpa navigasi.
- `npm run build`.
- `composer validate --no-check-publish` dan `composer check-platform-reqs`.
- GET preview lokal `/login`: HTTP 200, satu h1, tidak ada hero lama.
  Kedua aset CSS/JS build baru yang direferensikan juga HTTP 200.
- Pemeriksaan whitespace pada file yang diubah.

**Belum diverifikasi secara visual/interaktif:** inventory browser yang tersedia
pada laptop kosong. Karena itu screenshot, pengukuran pixel, klik native Menu,
zoom, resize browser, serta Back/Forward interaktif belum dijalankan. Unit test
navigasi menguji logika JS, bukan menggantikan uji browser. Regression suite
Laravel tetap meliputi autentikasi, izin, filter, pagination, dan draft yang sudah
ada dengan HTTP mock dan SQLite in-memory.

## Batas perubahan

Hanya presentasi, test UI, script test, dan dokumentasi di NADI yang diubah.
Frontend build lokal diperbarui untuk preview yang sudah berjalan di port 8010.
Tidak ada perubahan route/controller/domain data, migrasi, akun, kredensial,
collector, database operasional, atau deployment Next.js pada port 3000.
Tidak ada commit, push, merge, atau deployment.

Preview: <http://127.0.0.1:8010/login>. Refresh halaman yang sedang terbuka untuk
memuat aset build baru. Original file UI disalin sebelum pengeditan ke direktori
backup lokal `/tmp/nadi-ui-compact-20261106/before`.


## Polesan visual lanjutan — 6 November 2026

Atas permintaan pengguna, skala compact dipertahankan dan gaya netral awal
dipoles menjadi sidebar navy, aksen teal, ikon SVG garis yang seragam, panel
beradius halus, serta bayangan tipis. Tidak ada hero atau kartu besar baru.
Sidebar tetap 208 px, konten desktop 16 px, dan sel tabel 8/12 px dengan teks
13 px. Status sumber/draft tetap eksplisit dan tidak ditafsirkan sebagai health.

Akun dan tombol **Keluar** sekarang berada di header kanan atas, di luar menu
mobile. Header tetap terlihat saat scroll. Label Keluar tidak disembunyikan pada
mobile; target sentuh minimum 40 px. Detail akun yang diringkas pada layar kecil
tetap tersedia untuk pembaca layar. POST dan CSRF logout tetap digunakan.

Hover/focus memakai transisi pendek 120–150 ms tanpa pergeseran layout. Preferensi
reduced motion mengurangi transisi/animasi. Warna teks utama, sekunder, navigasi,
menu aktif, tombol utama, dan link memenuhi rasio kontras teks minimum 4.5:1
dalam pengujian token warna; ini bukan audit aksesibilitas browser menyeluruh.

Verifikasi akhir: 55 test Laravel / 513 assertion; 8 test frontend; Pint; Vite
build; Composer validate/platform. Test baru mengunci lokasi logout, CSRF, ukuran
compact, kontras token, reduced motion, dan target logout mobile. Preview login
dan kedua aset build juga mengembalikan HTTP 200.

QA visual/interaktif masih belum dijalankan: inventory browser laptop kosong.
Tidak mengklaim screenshot, pengukuran pixel, atau klik/resize browser telah
lulus. Semua perubahan terbatas pada presentasi, test, dan dokumentasi; tidak
ada perubahan data/backend, dependensi aplikasi, atau layanan sumber.
