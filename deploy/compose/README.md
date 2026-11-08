# BSLA managed platform — backend NADI Laravel

Deployment existing menggunakan project **`reliability-cockpit-platform`**,
`compose.yaml` + `compose.dev.yaml`, `.env.platform`, network dan volumes yang
sama. **NADI Laravel di `../../NADI/` adalah preview lokal terpisah pada loopback
8010**, bukan service Compose atau pengganti otomatis Next.js lama di 3000.

Collector tetap pemilik data sumber. `cockpit-api` menyajikan Mart yang ada di
Maximo Collector DB dengan identity read-only existing. Legacy Cockpit worker
mengonsumsi collector API ke Cockpit DB sendiri. Tidak ada DB Mart kelima,
source credentials di consumer, atau source write dari NADI.

## Operasi instalasi existing

Baca [AGENTS root](../../AGENTS.md) sebelum operasi. Reuse semua database,
volume, konfigurasi dan account. Jangan overwrite `.env.platform`, mengubah
project name, menggunakan `down -v`, menghapus history atau reset cursors.
Dokumen/UI Laravel tidak memerlukan restart collector.

Instalasi existing dapat memakai image pins dan release privat. Root Compose
publik tetap definisi instalasi buildable, bukan salinan pin lokal. Clone baru
tidak memiliki lock, arsip atau snapshot release. Sebelum operasi instalasi
berpin, pilih input privat melalui `BSLA_RUNTIME_LOCK`, `BSLA_RUNTIME_RELEASE_DIR`
dan `BSLA_RUNTIME_COMPOSE_FILES` sesuai runbook. Setelah input itu diverifikasi:

```bash
python3 deploy/compose/runtime_release.py verify
```

Hanya bila restart/recreate memang diminta/diperlukan, ikuti
[runtime durability dan rollback](runtime-durability.md), satu exact service
sekali operasi. Helper `runtime_service.py` menerima `maximo-api`, `maximo-worker`,
`mart-projector`, `cockpit-api`, `cockpit-worker` dan memeriksa image/config serta
single-worker identity. Jangan jalankan semua contoh operasi secara beruntun.

Stopped rollback containers dapat memiliki label Compose. Karena itu **jangan
mass `compose up`, `--remove-orphans`, atau generic service restart/recreate**
pada instalasi ini; hal tersebut dapat memilih backup atau image yang salah.
Jangan menjalankan backup worker bersamaan dengan worker aktif. Path/source/image
snapshot lokal dipertahankan untuk recovery, bukan target cleanup plans.

## Tanggung jawab layanan

| Service | Tanggung jawab |
|---|---|
| `maximo-worker` | Scheduled bounded acquisition; pertahankan command/interval/override yang disetujui pada instalasi existing, source locks dan guards |
| `maximo-api` | API store Maximo existing; local trigger bukan read-only lookup |
| `mart-projector` | Local incremental Equipment/WO projection; contract mount read-only; tanpa Maximo calls |
| `cockpit-api` | Mart read API untuk Laravel dan UI lama; no legacy DSN fallback |
| `cockpit-worker` | Maximo Collector API → legacy Cockpit records/KPI readiness; PI/CEMS projection pending |
| `pi-registry` / `pi-api` | One-shot verified/ok registry loader dan stored-data API |
| `pi-auth-check` / `pi-worker` | Opt-in `pi-collection`; verifikasi satu acquisition owner dan izin source sebelum mengubah state |
| `cems-worker` / `cems-aggregator` / `cems-api` | FC03/FC04 polling, completed-window aggregation dan API, dengan operator overrides existing |

| Store | Owner/database | Volume | Default app ports |
|---|---|---|---|
| Maximo + Mart | `maximo_collector` | `maximo-db` | API 8002 / dashboard 3001 |
| PI TimescaleDB | `pi_collector` | `pi-db` | API 8001 / dashboard 3002 |
| CEMS | `cems_collector` | `cems-db` | API 8003 / dashboard 3003 |
| Cockpit legacy | `cockpit` | `cockpit-db` | API 8000 / Next.js 3000 |

Managed DB ports 5432 berada di network privat, tidak dipublish. Physical volume
prefix tetap `reliability-cockpit-platform_`. Host ports 5434/5433/5435 pada
standalone lama bukan bukti koneksi managed. Laravel development SQLite tidak
termasuk tabel ini dan tidak mengganti store operasional.

## Kesegaran, scope dan data

Periksa completed run/cursor, partial/error, ingestion/source timestamps dan
projection state secara terpisah. API 200, process alive, source `changedate`
atau `mart_updated_at` bukan bukti source catch-up lengkap. Registry membership,
Asset inventory dan technical Equipment count berbeda populasi.

Mart projector tidak mengisi semua FMEA/RCFA/health/overhaul; pertahankan data
controlled loads yang sudah ada. Four-year acquisition WO tidak menghapus history
lama. Same terminal status tetap frozen; tidak memulai backfill untuk mengisi
field baru. MTBF/MTTR/availability WO-only tetap null/NOT_READY.

Managed PI menggunakan `.env.platform` sebagai otoritas konfigurasi dan
`PI_CONFIG_MODE=managed` untuk melewati dotenv lokal/home. Source settings hanya
masuk ke `pi-worker`, bukan API/migrate/Cockpit. Jangan menyalin secret ke consumer
atau membuat konfigurasi paralel. Periksa owner/lease yang berjalan sebelum
collection, migration atau retry authentication; contoh command bukan izin.
Lihat [runbook PI](../../pi-collector/docs/runtime-migrations.md).

Mart schema/governance menggunakan existing Maximo owner. `mart-ready` adalah
gate non-destructive; `mart-migrate`/`mart-reader` opt-in dan status-only secara
default. DDL/role apply memerlukan backup dan target yang benar, bukan bootstrap
API. Writer/admin DSN terpisah dari SELECT-only API tanpa fallback. Lihat
[runbook Mart](../../reliability-cockpit/docs/mart-runtime.md).

## Mode alternatif dan checkout baru

`compose.external.yaml` adalah deployment terpisah bernama
`reliability-cockpit-external`, dengan Cockpit volume sendiri dan collector API
external. Bukan overlay managed dan bukan solusi empty-page. Jangan berpindah
mode untuk development biasa atau menganggap menyalakannya memigrasi data.

Untuk instalasi baru yang secara eksplisit diminta: tentukan mode, target existing
atau fresh stores, secrets, image availability, source access, ownership/single
worker, backup/migration plan dan ports lebih dahulu. File contoh tidak boleh
menimpa env existing. Release privat perlu image/arsipnya sendiri, tidak bisa
direproduksi hanya dari clone publik. Jangan mengganti pin existing dengan broad
build dari checkout dirty atau mengklaim source build sama dengan runtime arsip.

## Cara kerja dan verifikasi

Solo developer: edit kecil → test sesuai dampak → inspeksi hasil. Tidak perlu
membuat worktree, stack paralel atau handoff berlapis. Untuk dokumentasi cukup
fact/link checks dan `git diff --check`; operasi runtime tidak dilakukan.

Perubahan controller runtime memakai fixture/tests di `tests/` dan `release_tests/`;
rehearsal terisolasi dibedakan dari live activation. Ikuti
[durability evidence](runtime-durability.md) untuk command, parity, backup dan
rollback. Jangan menganggap file lock atau laporan historis sebagai bukti semua
service sehat saat ini; verify sesuai kebutuhan tanpa mengubah runtime.
