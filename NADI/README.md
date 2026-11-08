# NADI Laravel — workspace aktif

NADI dikembangkan langsung di `NADI/` dengan **Laravel 13, Blade, dan Vite**.
Preview development: <http://127.0.0.1:8010/login>. Backend FastAPI/Reliability
Mart dan collector tetap digunakan; UI Next.js lama di port 3000 dipertahankan.
Laravel belum menjadi cutover atau deployment produksi.

Konteks diselaraskan dengan kode checkout pada 7 November 2026. Bukti pengujian
fitur tersimpan di dokumen masing-masing; angka test dan hitungan data pada laporan
lama adalah snapshot historis, bukan jaminan kondisi runtime hari ini.

## Cara kerja solo developer

**Edit → uji sesuai dampak → lihat hasil.** Kerjakan satu perubahan berguna
langsung di checkout aktif, tanpa worktree tambahan, handoff atau proses berlapis
rutin. Cek `git status` lebih dahulu dan jangan menimpa pekerjaan yang sudah ada.
Baca [AGENTS.md](AGENTS.md) dan aturan root sebelum mengubah data atau layanan.

```bash
cd NADI
# Hanya bila preview ini belum berjalan; jangan membuat listener kedua.
php artisan serve --host=127.0.0.1 --port=8010 --tries=1
# Setelah perubahan CSS/JS:
npm run build
```

`composer dev` juga menjalankan preview di 8010 tanpa collector/queue tambahan.
Perubahan Blade/PHP terlihat setelah refresh. CSP memakai aset lokal hasil build;
jangan mengasumsikan Vite dev server sudah didukung. Dokumen saja tidak memerlukan
restart, migration, collection atau build aplikasi.

## Fitur yang ada di checkout

| Area | Kemampuan dan batas |
|---|---|
| Beranda | Ringkasan bersumber, perlu perhatian, aktivitas terbaru, kandidat review, kualitas data |
| Master Asset | Inventaris BSR/IP/CS01, kategori/scope, detail, timeline dan relasi Registry; mapping BSR tetap proposal |
| Work Orders | Riwayat/detail, kandidat history gangguan, filter dan pagination, kelompok aktivitas per tahun per aset |
| PdM | Logbook rutin/request, template pengukuran, tanggal saja atau timestamp, analisis/rekomendasi tertaut, history dan tren per titik |
| Log Gangguan Aset | Observasi engineer, satu event dengan aset penyebab/terdampak/unknown, koreksi/revisi dan pembatalan |
| Action Board | Prioritas yang dinilai engineer, kandidat belum dinilai, rekomendasi lokal dan WAPPR terpisah |
| Kualitas data / laporan | Cakupan dan ketidaklengkapan eksplisit, CSV snapshot ringkasan tanpa isi temuan atau identitas pengguna |
| Operasi | Pemilihan Asset Registry dan tautan konteks; belum ada historian, live value, layout HMI atau kontrol |
| Administrasi | Kelola akun/role lokal, aktivasi/nonaktif, penggantian password development |

Ilustrasi Asset adalah gambar generik berlabel, bukan foto/spesifikasi aktual.
Tidak ada automatic diagnosis, reliability score, approval bisnis, pengiriman
notifikasi eksternal, Maximo write-back, atau perhitungan MTBF/MTTR resmi.

## Akun dan hak akses

Login menerima username atau email. Repository tidak menyertakan akun atau
password siap pakai. Bootstrap pada checkout development yang benar menghasilkan
credential privat; jangan publikasikan atau menyalin file credential ke Git.
Credential awal bukan sumber password terkini setelah password diganti.

- **ADMIN:** kelola akun lokal. Tidak mewarisi hak tulis engineering.
- **ENGINEER:** buat dan koreksi hanya catatan engineering miliknya sendiri.
- **SUPERVISOR / MANAGER:** baca workspace; bukan hak approval, risk acceptance,
  budget decision atau administrasi akun.
- Semua izin diperiksa oleh server Gate, bukan sekadar tombol tersembunyi.
  Auth-version menolak sesi lama/nonaktif, termasuk setelah reaktivasi. Perubahan
  akun melindungi admin aktif terakhir dan melarang perubahan role/status sendiri.
- Versi optimistis, kunci idempotensi, constraint unik dan revisi mempertahankan
  jejak perubahan serta mencegah submit ganda dan overwrite formulir lama.

Akun `development_only` memerlukan local environment, client IP dan Host loopback.
Preview HTTP lokal tidak ditujukan untuk dibagikan. HTTPS/session/security review
harus dilakukan sebelum akses bersama. Akun ini tidak diimpor dari aplikasi lama.
SSO, MFA dan pemulihan password melalui email belum tersedia.

## Data dan sumber

Existing ignored `database/development.sqlite` menyimpan akun, draft inspeksi/
rekomendasi, PdM, gangguan manual beserta anggota/revisi, prioritas aset/revisi,
dan aktivitas workspace. Data ini bukan fixture yang boleh dihapus sewaktu-waktu.
Migrasi bersifat kompatibel pada store yang sama dengan backup lebih dahulu;
tidak mengganti database operasional atau menyalin source payload.

```dotenv
RELIABILITY_MART_API_BASE=http://127.0.0.1:8000
```

Laravel memakai GET melalui [`ReliabilityMart`](app/Services/ReliabilityMart.php):

- `/v1/reliability/assets/inventory-summary`, `/assets/inventory` dan detailnya:
  inventaris terkoleksi BSR/IP/CS01, bukan janji semua Asset BSR sudah lengkap.
- `/v1/reliability/assets` dan detailnya: populasi Registry yang digovern.
  Inventory tidak otomatis memberikan membership atau akses operasi Registry.
- `/v1/reliability/maintenance-events`: WO Registry; `inventory-maintenance-events`
  untuk history exact-Asset inventaris non-Registry. Annual/detail endpoints
  mengikuti [kontrak API](../reliability-cockpit/docs/reliability-mart-query-api.md).
- `/v1/reliability/maintenance-investigation`: kandidat repeat-WO Registry dengan
  jendela 30/90/180 hari; tidak mencakup seluruh inventaris.
- WAPPR dibaca terpisah sebagai backlog, bukan failure count atau score input.

Ada fallback kompatibilitas description-only ke Maximo Collector loopback
(`MAXIMO_COLLECTOR_API_BASE`, default 127.0.0.1:8002), setelah exact WO **dan** Asset
cocok. Tidak ada raw payload, person/cost exposure, source SQL, koleksi baru atau
fallback ke produksi. Semua respons dibatasi 1 MiB dengan timeout dan tanpa redirect.

Kartu inventaris memakai kontrak agregat, bukan jumlah 25 baris yang terlihat,
jumlah Registry atau baris workbook. Kategori berasal dari exact source identity
yang cocok dengan referensi engineer; unknown/conflict tidak ditebak dari tree
depth/type. Unit/parent sumber dan membership tidak diubah. Timestamp record atau
HTTP 200 tidak membuktikan freshness. Empty, partial, unavailable dan unknown
selalu dibedakan; unavailable tidak ditampilkan sebagai nol.

## Arti WO, gangguan dan waktu

- History gangguan berbasis WO adalah **kandidat review/unknown**, bukan daftar
  failure tervalidasi. CM/REPAIR/EMERGENCY atau failure code hanyalah petunjuk.
- Basis tanggal history umum dapat memakai actual start, lalu perubahan record
  ketika kosong; labelnya menyatakan itu bukan waktu kejadian. Annual WO memakai
  actual start dalam WIB; tanggal kosong tetap unknown, status adalah status
  terakhir, bukan status akhir tahun. Jangan campur kedua basis tersebut.
- Durasi final WO hanya dihitung untuk CLOSE dengan dua actual timestamp valid,
  berzona dan tidak terbalik. Ini elapsed execution, **bukan MTTR/downtime**.
- Log gangguan manual punya event ID dan revisi, tetapi belum memiliki proses
  validasi failure untuk KPI. Satu event bisa terkait banyak Asset; hitungan per
  aset tidak boleh dijumlahkan menjadi total plant. Recovery kosong tidak berarti
  masih trip; event duration yang tercatat bukan verified downtime.
- PdM tanggal saja tetap tanggal literal tanpa midnight/zona buatan. Tren tidak
  menggabungkan asset, template, unit, point atau konteks yang berbeda; data jarang
  tidak dianggap realtime, tidak diinterpolasi dan tidak menjadi diagnosis.
- Prioritas engineer adalah penilaian manual dengan dasar yang terlihat, bukan
  skor otomatis. Kandidat belum dinilai tidak diberi status sehat/gagal.

Collector sekarang membatasi acquisition WO ke empat tahun kalender `reportdate`
(Asia/Jakarta), mempertahankan history lokal lama dan membekukan detail terminal
yang tidak berubah. Evidence tambahan hanya terisi pada detail normal yang memang
perlu, bukan backfill otomatis. Failure-code retention dan koreksi boolean downtime
diterapkan dalam [adapter evidence](../maximo-collector/src/adapters/maximo/reliability_fields.py)
dan diuji oleh fixture sintetis. Laporan aktivitas sumber tetap privat.
Ini tidak membuat failure event, operating exposure atau repair interval menjadi siap.
MTBF/MTTR/availability WO-only tetap **NOT_READY**, termasuk snapshot KPI lama di API.

## Pengembangan lanjutan

- [Roadmap NADI Laravel](../plans/NADI-LARAVEL.md): polish/QA, workflow engineer,
  ketahanan data lokal dan gerbang deployment.
- [Roadmap MTBF/MTTR](../plans/MTBF-MTTR.md): validasi kejadian, korelasi WO,
  operating exposure historian, batas repair/restoration dan kualitas data.
- Pareto WO terklasifikasi harus diberi label WO, bukan jumlah kejadian. Pareto
  kejadian membutuhkan event yang divalidasi; Pareto loss membutuhkan evidence
  dampak tersendiri. Tidak ada score atau rumus aktif hanya karena ada roadmap.

## Checkout development baru, bukan reset instalasi ini

Gunakan PHP 8.3+ dengan ekstensi dari `composer.lock`, Composer dan Node yang
kompatibel dengan lockfile Vite. Versi tepat mengikuti lockfile; jangan menyebut
versi lama sebagai "latest". Hindari `composer setup` pada instalasi yang sudah
berisi data karena script tersebut juga meregenerasi app key.

Hanya untuk checkout development baru yang belum punya `.env`/SQLite:

```bash
composer install
php -r "file_exists('.env') || copy('.env.example', '.env');"
# Hanya isi key jika APP_KEY belum ada; jangan rotasi key instalasi yang berjalan.
php artisan key:generate
npm ci --ignore-scripts
npm run build
php -r "file_exists('database/development.sqlite') || touch('database/development.sqlite');"
# Verifikasi target development.sqlite dahulu, bukan database operasional.
php artisan migrate
php artisan nadi:admin --email=your-development-email@example.test
```

Bootstrap menolak store/account yang tidak sesuai dan menulis secret acak hanya
ke file privat. `php artisan nadi:dev-users --memorable` tersedia untuk empat akun
lokal pada checkout development yang sesuai dan menolak menimpa user yang ada.
Jangan menjalankan bootstrap/migrasi sebagai langkah otomatis membaca README.

## Pemeriksaan

```bash
composer test
vendor/bin/pint --test
composer validate --no-check-publish
composer check-platform-reqs
npm run test:ui
npm run build
git diff --check
```

Test menggunakan SQLite `:memory:` dan HTTP mock. Browser QA harus menggunakan
fixture/store sementara tersendiri, bukan menambah data sintetis ke preview.
Periksa role, missing/partial data, stale edit, submit ulang, navigasi terputus dan
layout responsif bila terdampak. Laporkan terpisah test kode, render, browser QA,
aktivasi runtime dan kesiapan produksi. Tidak ada klaim seluruhnya lulus dari
sekadar perubahan dokumen ini.

## Katalog dan mapping privat

`NADI_PDM_CATALOG` memilih katalog yang ditinjau secara lokal. Defaultnya
`storage/app/private/pdm-form-catalog.json`. `NADI_ASSET_MAPPING` memilih mapping
lokal, default `storage/app/private/asset-mapping.json`. Kosongkan dengan menghapus
variabel bila ingin memakai default, bukan mengganti sumber dengan fixture tes.

Clone publik tidak membawa workbook, katalog turunan, identitas aset, pengukuran,
mapping operasional, akun atau database. Katalog yang tidak tersedia tetap tampil
unavailable. Instalasi existing dapat menunjuk file privat yang sudah ada; jangan
regenerasi ID/fingerprint atau menimpa snapshot draft. Fixture sintetis dalam
`tests/Fixtures` hanya untuk pengujian, bukan sumber operasional.

## Panduan fitur publik

- [PdM logbook](docs/pdm-logbook.md) dan [tren per titik](docs/pdm-trends.md).
- [Log gangguan](docs/asset-disruption-log.md) dan [Action Board](docs/asset-attention-priority.md).
- [Home feed](docs/home-feed.md), [UI ringkas](docs/compact-workspace-ui.md),
  [QA perjalanan](docs/workflow-journey-qa.md), dan [batas publikasi](docs/publication.md).
- [Kontrak query Mart](../reliability-cockpit/docs/reliability-mart-query-api.md)
  untuk inventory, history dan endpoint pendukung.

Dokumen lokal tambahan dan bukti operasional bukan bagian clone publik. Jangan
menambahkannya hanya untuk memperbaiki tautan; gunakan kontrak/kode publik di atas.

Repository: <https://github.com/johnd-creator/BSLA>. Root fisik dan symlink lama,
Compose project/volume, akun lama serta port layanan tetap dipertahankan.
Operasi backend mengikuti [runbook platform](../deploy/compose/README.md), bukan
restart/rebuild seluruh stack dari perubahan frontend.
