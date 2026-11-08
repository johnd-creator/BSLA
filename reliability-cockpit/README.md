# Reliability Cockpit — backend data NADI dan UI lama

Komponen ini tetap menyediakan **FastAPI/SQLAlchemy** dan query Reliability Mart
untuk [NADI Laravel](../NADI/README.md), workspace produk aktif. UI Next.js 15/
React 19 yang lama tetap disimpan dan berjalan terpisah; bukan target default
pengembangan fitur NADI baru. Ini bagian monorepo BSLA, bukan consumer starter
atau repository independen.

## Dua jalur data yang berbeda

| Jalur | Store / konfigurasi | Makna |
|---|---|---|
| Legacy collector ingestion | `DATABASE_URL` → existing `cockpit-db` | Worker menarik API Maximo Collector dan menyimpan normalized legacy records/KPI |
| Canonical Mart query | `RELIABILITY_MART_DATABASE_URL` → existing Maximo Collector DB | Public `/v1/reliability/*`, read-only, tidak menyalin Mart ke Cockpit DB |

Mart DSN memakai identity read-only existing, bukan permintaan database baru.
Tidak ada fallback ke DSN legacy jika Mart tidak tersedia. Laravel memakai
`RELIABILITY_MART_API_BASE`; Next.js lama memakai proxy `/api/cockpit/*` ke
`COCKPIT_API_BASE`. Production Maximo/PI/PLC tidak diakses langsung oleh consumer.

Inventory Asset dan governed Registry adalah populasi berbeda. Route inventory
melayani exact-Asset history di luar Registry; route governed tetap membatasi
membership. Master-data counts tidak membuktikan coverage atau freshness.
PI/CEMS API base yang dikonfigurasi tidak berarti proyeksi NADI sudah diimplementasi.

## Modul penting

- `src/api/reliability.py`: kontrak read-only canonical.
- `src/repositories/mart_reader.py`: query Mart dengan scope/DTO terkontrol.
- `src/repositories/asset_inventory.py`, `inventory_work_orders.py`,
  `annual_work_orders.py`, `maintenance_activity.py`: populasi, annual dan evidence.
- `src/adapters/collector_client.py`, `src/services/sync.py`: legacy collector path.
- `src/services/work_order_timing.py`: elapsed execution CLOSE dengan clocks valid.
- `src/services/kpi.py`: pure formula helpers dan readiness gate service legacy.
- `web/`: aplikasi Next.js yang dipertahankan, bukan Laravel.

## KPI belum siap dari WO saja

WO/failure code bukan event failure. Actual elapsed WO bukan MTTR, `actlabhrs`
bukan elapsed repair, dan `downtime` Maximo boolean bukan jam. Kalender bukan
operating exposure. Service WO-only mengembalikan null + **NOT_READY** untuk MTBF,
MTTR dan availability; API juga memask snapshot numerik lama tanpa menghapusnya.
Formula helper yang tersedia tidak membuktikan inputnya valid. PM compliance
mempertahankan definisi legacy-nya dan tidak membuktikan kelengkapan master PM.
Lihat [kontrak KPI](docs/kpi.md) dan [roadmap](../plans/MTBF-MTTR.md).

## Kerja lokal dan pemeriksaan

Baca [AGENTS](AGENTS.md) dan root lebih dahulu. Kerjakan langsung checkout aktif:
edit → test sesuai dampak → periksa respons/preview. Jangan membuat sidecar DB,
menyalin `.env`, menjalankan `cockpit init-db/sync/kpi` atau worker tambahan sebagai
setup rutin. Reuse environment dan deployment existing.

```bash
.venv/bin/python -m unittest discover -s tests
git diff --check
```

Untuk perubahan web lama yang memang diminta, baca scripts `web/package.json`
dan uji/build hanya bagian itu. Untuk fitur Laravel, gunakan pemeriksaan `../NADI/`.
Unit tests harus menggunakan fixture/temporary stores tanpa produksi. Jangan
menjalankan test yang memerlukan DB sebelum memastikan targetnya hermetic.

API managed default port 8000, web lama 3000. Instalasi existing dapat memakai image/config privat terpin; operasi
mengikuti [runbook platform](../deploy/compose/README.md) dan exact-service helper.
Tidak ada rebuild/restart/push/deploy hanya karena dokumen atau consumer berubah.

## Referensi aktif

- [Mart query API](docs/reliability-mart-query-api.md)
- [WO harian/evidence](src/repositories/maintenance_activity.py)
- [Investigasi pemeliharaan](docs/nadi-maintenance-investigation-semantics.md)
- [Performa investigasi](docs/maintenance-investigation-performance.md)
- [Mapping Asset–AF](docs/asset-af-mapping-admin.md)
- [Source resolution](docs/source-resolution.md) dan [adapter](docs/adapter.md)

Dokumen release/UI lama tetap bukti bertanggal, bukan instruksi untuk menghidupkan
ulang arsitektur lama. Jangan menebak identitas, mengubah Registry atau mengekspos
vendor payload di luar DTO allowlist. Secrets tidak masuk source/log/docs.
