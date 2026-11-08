# BSLA — NADI Laravel dan platform data

Workspace aktif untuk **NADI Laravel**: aplikasi lokal engineering/reliability
berbasis Laravel 13, Blade, dan Vite. Pengembangan produk dilakukan di [`NADI/`](NADI/README.md),
bukan meneruskan UI Next.js lama. Preview lokal: <http://127.0.0.1:8010/login>.
Ini belum merupakan cutover atau rilis produksi.

Collector, Reliability Mart, API FastAPI, dan data lama tetap dipakai. NADI
Laravel membaca data Asset/WO melalui API yang sudah ada dan menyimpan akun,
PdM, inspeksi/rekomendasi, log gangguan, prioritas aset, serta audit lokal di
SQLite development yang sudah ada. Tidak ada penggantian database operasional.

## Mulai dari sini

- [Panduan NADI Laravel](NADI/README.md): fitur, akses, preview, dan pemeriksaan.
- [Aturan kerja workspace](AGENTS.md) dan [aturan NADI](NADI/AGENTS.md).
- [Rencana aktif](plans/README.md): pengembangan Laravel dan fondasi MTBF/MTTR.
- [Operasi platform](deploy/compose/README.md): deployment yang sudah berjalan.
- [Kontrak query Mart](reliability-cockpit/docs/reliability-mart-query-api.md).

## Cara kerja solo developer

1. Baca aturan yang relevan, cek `git status`, lalu kerjakan langsung di checkout
   aktif. Pertahankan perubahan pengguna yang sudah ada.
2. Ambil satu perubahan kecil yang berguna: **edit → uji sesuai dampak → lihat
   hasil** pada preview yang sama. Perubahan frontend dibangun dengan `npm run build`.
3. Periksa alur utama, kondisi gagal, dan hak akses bila terdampak. Untuk dokumen
   saja, periksa fakta, tautan, dan `git diff --check`; tidak perlu restart layanan.
4. Laporkan hasil, pemeriksaan yang benar-benar dijalankan, dan batas yang tersisa.
   Tidak perlu handoff, worktree, pembagian agen, atau proses berlapis rutin.
5. Jangan commit/push/deploy, mengganti preview lama, menjalankan collection,
   migrasi data, atau membuat store baru tanpa permintaan yang mencakup tindakan itu.

## Komponen dan batas tanggung jawab

| Direktori | Peran saat ini |
|---|---|
| `NADI/` | UI Laravel aktif: Asset, riwayat WO, PdM/tren, log gangguan, prioritas, overview/laporan |
| `reliability-cockpit/` | Backend FastAPI/Mart yang masih dipakai; UI Next.js lama tetap dipertahankan |
| `maximo-collector/` | Collector Maximo read-only, store sumber dan Reliability Mart lokal |
| `pi-collector/` | Store/API time series PI; integrasi historian NADI belum aktif |
| `cems-collector/` | Collector/API Modbus CEMS independen; proyeksi NADI belum aktif |
| `maximo-knowledge/`, `pi-knowledge/` | Bukti sumber, identitas, mapping dan discovery terkontrol |
| `reliability-data-contracts/` | Schema dan makna data antar-komponen |
| `NK/` | Dokumentasi consumer Streamlit independen; implementasi/model tidak disertakan pada main ini |

Satu Git repository berada di root ini. Tiap komponen punya dependensi dan
pengujian sendiri; tidak ada satu perintah test untuk seluruh workspace.
Direktori runtime/backup, dependency, worktree lama, dan data privat bukan target
pembersihan dokumentasi atau rencana aktif.

## Status reliability yang perlu dibaca benar

- WO adalah aktivitas pemeliharaan, bukan otomatis kejadian failure. WAPPR tetap
  backlog. Failure code dan tipe pekerjaan hanya petunjuk review.
- Log gangguan manual menyimpan observasi engineer beserta revisi, bukan sertifikasi
  failure. Jumlah per aset tidak boleh dijumlahkan menjadi jumlah kejadian plant.
- Durasi actual WO CLOSE bukan MTTR. `downtime` Maximo yang terverifikasi adalah
  boolean, bukan jam. Jam kalender bukan operating exposure.
- MTBF, MTTR, dan availability berbasis WO saja tetap **NOT_READY**; fondasi
  kejadian, exposure historian, repair boundary, dan coverage perlu disepakati.
  Lihat [roadmap MTBF/MTTR](plans/MTBF-MTTR.md).

## Identitas deployment

Root fisik mengikuti checkout lokal. Pertahankan symlink kompatibilitas yang
masih dipakai mount, unit, venv atau worktree existing.
Compose project tetap `reliability-cockpit-platform`; database/volume tidak diganti.
Preview Next.js lama memakai port 3000; Laravel memakai loopback 8010.
Baca [runtime durability](deploy/compose/runtime-durability.md) sebelum operasi
instalasi yang memakai release privat. Clone publik tidak membawa image lock atau arsipnya. Tidak boleh mass rebuild/recreate sebagai setup rutin.

Semua sumber produksi tetap read-only. Rahasia, `.env`, SQLite development,
backup, dan payload privat tidak masuk Git. Status historis atau HTTP 200 tidak
membuktikan kelengkapan dan kesegaran data hari ini.
