# Power Plant Data Platform

## NADI — start here

**NADI — Reliability Data Platform**, supporting PLTU Banten 1 Suralaya within the
Power Plant Data Platform. Read [NADI-CONTEXT.md](NADI-CONTEXT.md) for concise
onboarding, [PRD](PRD.md) for requirements, [Design System](DESIGN-SYSTEM.md) and
[UI specification](docs/design/NADI-UI-SPEC.md) for proposed design.

[Official product roadmap](plans/NADI-ROADMAP.md) ·
[Repository Status](plans/REPOSITORY-STATUS.md) · [DEV-LOG](DEV-LOG.md) ·
[Agent safety and onboarding](AGENTS.md).

Primary development frontend: **https://localhost:3000**. FIX-03 verified main
0cb26882c870185a54282df3af4a136f31702b67 with PR62/63 MERGED. The last recorded runtime
source is 0bfea1273f97ce96a08ef147b44f804aecb428d1; documentation reconciliation
does not switch the running frontend.
See [verified audit and startup authority](docs/NADI-DOC-FOUNDATION-01.md).
No global login enforcement is introduced by the documentation foundation.

Monorepo untuk fondasi data pembangkit yang dipakai bersama oleh aplikasi
engineering dan analitik. Nama repository tetap `reliability-knowledge-starter`;
visi produknya telah berkembang menjadi **Power Plant Data Platform**.

**Mulai di [peta platform dan roadmap](plans/README.md).** Dalam beberapa menit,
dokumen itu menjelaskan posisi produk, pekerjaan berikutnya, dan utang branch.

```text
POWER PLANT DATA PLATFORM
├── Shared Data Foundation
│   ├── Maximo Knowledge + Maximo Collector
│   ├── PI Knowledge + PI Collector
│   ├── CEMS Collector
│   └── Reliability Data Contracts / Governance
├── NADI — main quest: Reliability / Engineering Intelligence
└── NK — child roadmap: Coal Calorific Value Prediction
```

Collector memiliki akuisisi sumber, pengaturan cadence, kualitas sumber, dan
penyimpanan lokal. Aplikasi memakai kemampuan collector atau kontrak yang
dikelola; aplikasi tidak melakukan discovery produksi sendiri.

## Historical position — audit 7 Oktober 2026

Snapshot berikut dipertahankan sebagai histori; status aktif ada di tautan di atas.

Audit **7 Oktober 2026**, baseline `main`:
[`ef07a26`](https://github.com/johnd-creator/reliability-knowledge-starter/commit/ef07a263b122d30e7dbec451e6094f9016b603c3)
(24 Agustus 2026).

- **NADI Phase 0 — Factual Foundation: COMPLETE**, dalam batas release faktual
  `v0.1.0-rc.1`. Ini bukan sertifikasi bahwa seluruh platform production-ready.
- **NADI Phase 1 — Evidence Expansion: CURRENT / PARTIAL.** Discovery sumber
  dan administrasi governed Asset ↔ AF sudah merged. Pilot mapping dan bukti PI
  di NADI masih belum diterima.
- **Next technical PR: NADI-PI-001 — Governed PI Source Adapter.** Review dan
  rekonsiliasi kandidat `d23f848` ke baseline terbaru; jangan merge seluruh
  branch campuran NK/deployment hanya untuk mengambil adapter.
- **NK sengaja menjadi aplikasi kedua.** Implementasi manual dan integrasi PI
  ada di feature branch `feature/pi-governed-source-adapter`, belum di `main`.
  PI integration masih partial: seluruh 13 feature mapping belum disetujui.
- Utang runtime Mart, branch lama, dan perbedaan Git/runtime dijelaskan di
  [Repository Status](plans/REPOSITORY-STATUS.md). Audit ini tidak menjalankan
  source collector atau memeriksa ulang data produksi.

## Komponen

| Path | Peran |
|---|---|
| `maximo-knowledge/` | Pengetahuan sumber Maximo dan discovery read-only |
| `pi-knowledge/` | Registry, topology dan bukti sumber PI |
| `maximo-collector/` | Sinkronisasi Maximo, local store, canonical Mart |
| `pi-collector/` | Snapshot / time-series PI dan API untuk banyak consumer |
| `cems-collector/` | Read-only Modbus, normalisasi dan agregasi CEMS |
| `reliability-data-contracts/` | Kontrak vendor-neutral, identity dan provenance |
| `reliability-cockpit/` | Implementasi NADI: FastAPI + Next.js |
| `NK/` | Streamlit / ML; tersedia di feature branch, sengaja belum disalin ke main |

Tidak ada root build/test tunggal; setiap komponen memiliki environment sendiri.
Root Compose adalah deployment orchestration. Reuse database dan volume yang
sudah ada. Reliability Mart berada di database Maximo Collector; **NK tidak
memerlukan database baru** dan membaca PI Collector API.

## Sumber kebenaran

1. [Vision](plans/PLATFORM-VISION.md): tanggung jawab dan batas data.
2. [NADI Product Roadmap](plans/NADI-ROADMAP.md): Phase 0–5 dan next task.
3. [Engineering Roadmap](plans/reliability-cockpit-platform/05-roadmap-implementasi.md):
   M0–M8, dependency dan status yang direkonsiliasi.
4. [NK Child Roadmap](plans/NK-ROADMAP.md): manual, mapping, fetch, validation, pilot.
5. [Repository Status](plans/REPOSITORY-STATUS.md): SHA, PR, branch debt dan governance.
6. [AGENTS.md](AGENTS.md): instruksi agen; baca juga aturan scoped setiap komponen.

Dokumen discovery/domain tetap menjadi bukti semantik. Dokumen proposal lama dan
`summary.md` tetap tersedia sebagai histori, bukan daftar pekerjaan aktif.

## Cara bekerja

Gunakan branch per task → PR ke `main` → review dan pemeriksaan yang relevan.
Default branch belum protected pada audit; rekomendasi ringan ada di Repository
Status. Jangan auto-merge atau menghapus branch berdasarkan dokumen audit ini.

Produksi tetap read-only. Jangan commit `.env`, credential, cookie, payload
produksi mentah, atau data personal. Jangan membuat database/worker duplikat untuk
mengatasi halaman kosong. Periksa konfigurasi, ownership, cursor dan freshness
terlebih dahulu; lihat [deployment runbook](deploy/compose/README.md), termasuk
batas runtime pada baseline `main`.

## Local Laravel development workspace

[NADI Laravel](NADI/README.md) is a separate loopback-only development UI.
Its private catalogs, operational data and accounts are not distributed with the
source. Publication does not replace the existing Next.js runtime or deploy it.
