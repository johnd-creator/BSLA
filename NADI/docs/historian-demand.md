# Historian sesuai halaman: pondasi simulasi

## Status dan batas

Kode pondasi tersedia pada 8 November 2026. **Historian/DCS nyata belum terhubung.**
Menu Operasi → Historian membuka demonstrasi dengan label SIMULASI yang tetap
terlihat. Jika endpoint tidak dikonfigurasi, halaman menyatakan belum aktif dan
browser tidak membuat subscription. Tidak ada tag/koneksi/alarm, status running,
KKS, mapping Asset↔AF atau operating exposure yang ditebak.

Paket `historian/` terpisah dari PI Collector, CEMS dan Reliability Mart. Tidak
mengimpor klien PI, worker, konfigurasi sumber, registry atau repository DB.
Autentikasi PI yang sebelumnya ditunda tetap tidak dicoba. SQLite existing,
Timescale/Postgres, Compose, worker dan identitas deployment tidak diubah.
Gateway demo tidak dijalankan otomatis oleh halaman atau Laravel.

## Aliran data

1. Browser membuka salah satu **page ID allowlisted**. Laravel memeriksa login,
   current-account dan CSRF; browser tidak dapat memilih URL atau tag sumber.
2. Laravel meminta lease ke gateway internal. Gateway mengembalikan cache RAM
   segera, tanpa menunggu atau memicu pembacaan sumber dari request HTTP. Cache
   dingin mengembalikan `value/source_at/age_seconds = null`, `no_data`.
3. Satu sampler menggabungkan tag seluruh halaman aktif. Viewer pada halaman
   yang sama, atau halaman yang berbagi tag, tidak membuat polling sumber ganda.
   Default 4 detik; hanya 3, 4 atau 5 detik yang dapat dipilih pada launcher.
4. Heartbeat mempertahankan lease selama halaman terlihat. `visibilitychange`
   dan `pagehide` melepas lease, membatalkan request dan menghapus tampilan nilai.
   Lease default 20 detik membersihkan tab yang crash atau kehilangan koneksi.
   Tag tanpa referensi berhenti setelah grace default 10 detik. Tab aktif lain
   tetap mempertahankan tag yang dibutuhkannya.
5. History hanya diminta saat tombol ditekan, untuk tag dalam lease halaman itu.
   UI meminta 15 menit/maksimal 120 titik. Kontrak membatasi satu tag, jendela
   maksimal satu jam, 1–1.000 titik, dan satu request per lease per 5 detik.
   Hasil tidak ditambahkan ke database atau cache history server.

Target sampling bukan jaminan end-to-end 3–5 detik, apalagi subdetik. I/O dibatasi
kontrak deadline 2 detik dan tidak berjalan paralel dengan history; saat busy,
cycle dilewatkan, bukan ditumpuk. Tidak ada adapter produksi untuk membuktikan
latensi/cadence nyata. Bridge Laravel memakai timeout 3 detik, tanpa redirect,
dan body cap 1 MiB. Browser menampilkan umur dan menyembunyikan nilai kedaluwarsa.

## Memori dan kualitas

- Maksimal 128 tag katalog, 32 page ID, 32 tag per halaman, 256 lease total,
  8 lease per pemilik sesi. Cache latest dan jadwal dibatasi katalog.
- Subscription bersifat idempotent untuk pasangan pemilik/client/page. Pemilik
  adalah HMAC account+session, bukan account ID atau session ID yang dikirim mentah.
  Lease acak tidak dapat digunakan melalui sesi Laravel berbeda.
- Restart gateway menghapus semua lease, latest dan konteks. Tidak ada sample
  file, DB, Redis, localStorage/sessionStorage, service worker atau payload log.
- DTO memisahkan `source_at`, `received_at`, `source_quality`, kualitas efektif,
  freshness dan age. Waktu sumber tidak diganti dengan waktu retrieval.
- Sampel nonfinite, timestamp tidak valid/masa depan, missing dan source error
  menghasilkan null; nilai nol yang benar tetap nol. Pada umur ≥3×interval
  halaman, nilai lama disembunyikan dan quality menjadi stale.
- `current/partial/no_data/degraded` menjelaskan kualitas feed, bukan kesehatan
  atau status operasi equipment. Kehadiran sinyal bukan bukti running.
- History mengembalikan `coverage=not_asserted`, termasuk history simulasi.
  Tidak ada klaim cakupan kontinu atau backfill otomatis.

## Konteks umum per menit, opt-in

`context_tags` kosong secara default: tanpa viewer tidak ada pembacaan sumber.
Jika operator secara eksplisit memilih tag konteks, tag itu dibaca/publikasikan
setiap 60 detik, termasuk saat tidak ada page viewer. Snapshot konteks dibekukan
sampai publikasi menit berikutnya; sample halaman yang lebih cepat tidak mengubah
publikasi tersebut. Umur ≥75 detik menyembunyikan nilai konteks yang lama.

Kontrak internal `POST /v1/historian/context` hanya membaca publikasi yang sudah
ada; tidak membuat subscription atau memicu I/O. `meaning=signal_data_only`.
Belum ada consumer konteks umum yang diaktifkan di halaman NADI lain. Launcher
`--demo-minute-context` hanya memilih tag sintetis `DEMO.TEMP`, bukan tag nyata.

## Adapter dan antarmuka internal

`historian/core.py`: `HistorianSource.snapshot(tags, deadline)` dan
`HistorianSource.history(tag, start, end, limit, deadline)` menerima identitas
allowlisted dan mengembalikan Reading(value, source_at, quality). Implementasi
saat ini hanya `SimulatedSource`. Coordinator menolak mode selain simulation.
Tidak ada discovery, retry kredensial, SQL, mutasi DCS atau fallback ke source.

Endpoint internal POST pada `/v1/historian/`:

| Endpoint | Input yang dibatasi | Hasil |
|---|---|---|
| subscribe | owner HMAC, client ID, page ID | Lease + latest halaman |
| heartbeat | owner, subscription | Perpanjang lease + latest |
| release | owner, subscription | Lepas referensi; TTL bila request hilang |
| history | owner, subscription, tag, start, end, limit | Titik bounded tanpa persistence |
| context | owner | Publikasi menit yang sudah ada, atau disabled |

POST hanya mengubah lease RAM internal; bukan HTTP POST ke PI/DCS. Tidak ada
endpoint source write. Server menolak Origin browser, Host bukan loopback,
body >4 KiB dan bukan JSON. Delapan handler maksimum, antrean socket terbatas,
timeout koneksi 3 detik. Tidak ada CORS/public listener. Konfigurasi Laravel
hanya menerima `http://127.0.0.1:<port>` tanpa credentials/path/query/fragment.

Gateway ini **bukan boundary multi-tenant produksi**: proses lokal tepercaya
masih bisa mengakses port loopback. Sebelum akses bersama/non-loopback, perlukan
service authentication, otorisasi page/tag per kelompok, transport terenkripsi,
request/rate budget sesuai sumber, observability tanpa secrets, dan verifikasi
kepemilikan sampler tunggal. Jangan expose listener melalui reverse proxy publik.
Launcher Linux mengambil abstract-socket ownership lock, sehingga dua instance
launcher di port berbeda tetap tidak membuat dua sampler. Jangan menjalankan
multi-worker atau replika tanpa koordinator bersama.

## Menjalankan demonstrasi secara eksplisit

Tidak ada perubahan `.env` atau service runtime historian dari implementasi ini.
Untuk sesi simulasi yang memang dikehendaki, dari `NADI/`:

```bash
python3 -m historian.server --simulation --port 8015 --sample-seconds 4
```

Secara terpisah konfigurasi proses Laravel development dengan
`HISTORIAN_DEMAND_API_BASE=http://127.0.0.1:8015`. Jangan arahkan ke PI/DCS, port
collector existing, atau `.env` operasional. Menutup proses gateway menghapus RAM.
Jangan mengaktifkan minute context kecuali memang menghendaki pembacaan demo saat
semua halaman ditutup. Demo tidak mengubah kondisi `Historian belum terhubung`
di konteks equipment.

## Gerbang berikutnya sebelum sumber nyata

1. Pastikan jenis/versi historian, transport read-only, autentikasi dan kemampuan
   timestamp/quality/history berdasarkan akses yang diizinkan; jangan menebak API.
2. Verifikasi katalog tag, satuan, timezone, page → tag dan Asset/KKS mapping dari
   evidence resmi. Technical PI registry tidak otomatis menjadi governed signal.
3. Implementasikan adapter bounded yang mematuhi deadline, response cap, source
   rate limit, single-owner dan fail closed. Tidak ada opsi source nyata sekarang.
4. Uji cold/warm cache, concurrent viewer, error/stale, shutdown dan budgeting
   dengan adapter yang sebenarnya. Aktifkan hanya setelah runtime/cutover diizinkan.
5. Running state/exposure memerlukan state rules, gap handling dan rekonsiliasi
   tersendiri sesuai `../../plans/MTBF-MTTR.md`; tidak disimpulkan dari sinyal.

## Verifikasi

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests/Historian -v
php artisan test --filter=HistorianDemandTest
node --test tests/Frontend/historian-demand.test.js
composer test
vendor/bin/pint --test
npm run test:ui
npm run build
```

Tests Python memakai clock/source fake, RAM dan temporary loopback; PHP memakai
SQLite `:memory:` dan mocked HTTP. Browser QA menggunakan store/akun/port fixture
terpisah serta gateway simulasi nyata, bukan fixture di preview pengguna.
Aktivasi runtime nyata dan validasi terhadap historian/DCS bukan bagian pengujian ini.
