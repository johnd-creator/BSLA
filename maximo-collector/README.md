# Maximo Collector — sumber dan Reliability Mart NADI

Collector Python/FastAPI read-only untuk Maximo BSR/IP. Source store dan
Reliability Mart berada dalam **database Maximo Collector existing**. Backend
FastAPI membaca Mart dan [NADI Laravel](../NADI/README.md) membaca DTO-nya;
consumer tidak menerima source credentials atau memulai collection.

Baca [AGENTS](AGENTS.md) dan [runbook managed runtime](../deploy/compose/README.md).
Scope, source lock, rate minimum 1 request/detik dan body cap 1 MiB dipertahankan.
Business calls hanya GET/HEAD/OPTIONS; satu exception POST adalah controlled
`/j_security_check` authentication, bukan perubahan data Maximo.

## Deployment dan cara kerja

Existing Compose project `reliability-cockpit-platform` memakai `maximo-db` /
`maximo_collector` / volume `maximo-db`, API default 8002 dan dashboard 3001.
Port standalone lama 5434 bukan DB managed. Jangan menyalin `.env`, membuat DB,
menjalankan worker tambahan atau bootstrap ulang saat memperbaiki NADI.

Kerja solo developer langsung checkout aktif: edit → test sesuai dampak → lihat
hasil. Runtime existing dapat memakai image overlay privat; checkout yang berubah tidak otomatis
berarti runtime berubah. Ikuti exact-service tools, bukan broad rebuild/restart.
Dokumentasi tidak memerlukan restart atau source requests.

## Acquisition WO saat ini

- Bounded newest-first summary dan active-status queue memverifikasi BSR/IP;
  prefix WO tambahan bukan bukti scope. Active queue dibatasi 25 pemeriksaan
  terpilih per run dan berbagi lock/request budget yang sama.
- Empat tahun kalender dari verified `reportdate` dalam Asia/Jakarta, cutoff
  inklusif. Bukan `changedate`, actual clock atau WO number. Invalid/missing/naive/
  future dates tetap unknown. Older retained records tetap bisa dibaca/proyeksi;
  tidak ada purge atau penyembunyian history.
- Detail hanya untuk WO baru/berubah sesuai lifecycle. CLOSE mengambil actuals
  pada observation/transition yang memenuhi syarat. Retained same-terminal-status
  CLOSE/CAN/CANCEL tetap frozen meski fields kosong; CAN/CANCEL summary-only.
- Open actual clocks tidak diminta/dianggap current evidence; reopen tidak boleh
  memakai clocks cycle lama. Konflik same-version status perlu exact confirmation.
- Cursor sukses tidak maju untuk incomplete traversal, mapping/scope/order/
  transport failure. Page catch-up bertahap tetap bounded; API 200 bukan complete
  population/freshness. Tidak ada historical/terminal backfill otomatis.

Aturan publik ada dalam [lifecycle policy](src/services/workorder_policy.py),
[age window](src/services/workorder_age.py), [actual dates](src/adapters/maximo/actual_dates.py)
dan [recency guards](docs/maximo-wo-recency-001.md). Pertahankan command/interval
worker existing yang telah diotorisasi; jangan menggantinya dengan scheduler
lain atau menyamakan post-cycle pause dengan freshness.

## Mart dan evidence reliability

`mart-projector` menggunakan local Equipment/WO dan read-only contract mount,
tanpa panggilan Maximo. Mart bukan DB baru. Registry, FMEA, RCFA, health dan overhaul
existing dipertahankan; projector operasional tidak mengoleksi semua domain itu.

Failure code diproyeksikan ke `maintenance_event`; allowlisted reliability evidence
menjaga per-field version, identity/scope, null versus omission dan clock validity.
`downtime` sumber adalah boolean, **bukan jam**; labor dan actual WO elapsed juga
bukan repair/restoration. Evidence baru hanya terisi saat lifecycle detail normal
memerlukannya. Public DTO tidak otomatis dibuka ke seluruh vendor evidence.

[Regresi evidence](tests/test_reliability_evidence.py) memakai fixture sintetis.
Laporan sumber, aktivasi dan repair operasional tetap privat.
[Roadmap MTBF/MTTR](../plans/MTBF-MTTR.md) tetap membutuhkan validated failure
events, historian exposure dan repair boundary. KPI WO-only tetap NOT_READY.

## API dan dashboard

GET `/equipment`, `/work-orders`, `/service-requests`, `/persons`, `/items`,
`/labor`, `/sync/status`, `/health`, `/stats`, `/collect-runs` menyediakan view
lokal. Filter/pagination mengikuti kontrak resource; vendor identity ada di
`sources.maximo`. `/equipment/{asset_id}/status-history` adalah observation history,
bukan otomatis event operasi/failure.

POST lokal `/sync/{object}` adalah trigger collection, **bukan read-only lookup**.
Tombol dashboard juga dapat memulai source GETs; jangan klik/jalankan hanya untuk
menguji UI consumer. Object selection dan trigger perlu scope kerja yang sesuai.

`mxapiasset` adalah preferred equipment source, scoped CS01. Person memakai
`locationorg=IP`, Labor `worksite=BSR`, Item `site=BSR`; zero rows tidak mengizinkan
perluasan query atau tebakan item-set/object. Gunakan owning knowledge evidence.

## Recovery manual yang tetap terpisah

- `mxcollector collect-asset-references --report-only`: laporan coverage lokal.
  Exact-ID source recovery hanya bila memang diminta dengan budget/scope sesuai
  [implementasi bounded recovery](src/services/asset_references.py).
- `collect-asset-inventory-batch --workbook <engineer-reference.xlsx>` adalah
  source collection manual resumable; bukan bagian default UI/startup. Source
  exhaustion dan verification wajib sebelum complete publication.
- `refresh-asset-inventory --workbook <engineer-reference.xlsx> --local-only`
  melakukan refresh klasifikasi lokal, tetap bukan perintah untuk menjalankan
  tanpa kebutuhan. [Implementasi inventory](src/services/asset_inventory.py).
- Historical actual backfill tetap langkah terpisah; jangan mengulang recovery
  lama untuk mengisi evidence yang dibekukan policy terminal.

## Pemeriksaan lokal

```bash
.venv/bin/python -m unittest discover -s tests
git diff --check
```

Reuse venv existing dan fixture hermetic. Uji cursor/partial replay, terminal
freeze, four-year age, scope, summary-only evidence, actual precision dan null
semantics sesuai dampak. Tidak perlu produksi, DB baru atau bootstrap.
Fresh isolated installation memerlukan pemilihan deployment/owner yang eksplisit;
contoh standalone tidak boleh menggantikan store managed yang berisi data.
