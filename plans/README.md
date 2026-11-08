# Rencana aktif BSLA / NADI

Konteks aktif: **NADI Laravel** di `../NADI/`, backend query FastAPI dan collector/
Reliability Mart yang sudah berjalan. Bukan proyek membuat ulang platform dari nol.
Diperbarui berdasarkan checkout 7 November 2026.

1. [NADI Laravel](NADI-LARAVEL.md): kondisi yang sudah ada, pekerjaan lanjutan dan
   cara kerja solo developer.
2. [MTBF / MTTR](MTBF-MTTR.md): definisi kejadian, exposure, repair boundary,
   quality/readiness, dan urutan implementasi yang belum selesai.

## Yang tidak lagi menjadi rencana aktif

Paket `reliability-cockpit-platform/` bertanggal 20 Agustus 2026 dihapus dari
working tree karena rencana bootstrap Compose, port/DB lama, cutover collector,
workflow role/UI Next.js dan milestone-nya sudah tidak cocok dengan keadaan kini.
Tujuh dokumen sebelumnya: `README.md`, `01-audit-kondisi-saat-ini.md`,
`02-arsitektur-target-docker-compose.md`, `03-integrasi-data-dan-kontrak.md`,
`04-rencana-produk-ui.md`, `05-roadmap-implementasi.md`, dan
`06-operasional-keamanan-pengujian.md`. Versi lama tetap dapat dilihat/dipulihkan
melalui riwayat Git.

Persyaratan yang masih penting dipertahankan pada dua roadmap di atas dan runbook
aktif, bukan dibuang: ownership data, scope/read-only, null/quality, identitas
lintas sumber, keamanan, backup/restore, deployment dan verifikasi.

## Dokumen yang tetap dipakai

- [README root](../README.md) dan [AGENTS root](../AGENTS.md).
- [README NADI](../NADI/README.md) dan bukti fitur di `../NADI/docs/`.
- [Operasi runtime](../deploy/compose/README.md), termasuk image lock/rollback.
- [Kontrak Mart](../reliability-cockpit/docs/reliability-mart-query-api.md),
  [schema/semantik](../reliability-data-contracts/README.md).
- Bukti discovery/aktivasi di knowledge dan collector; bukan backlog baru.

PI/CEMS/NK tetap komponen independen. Dokumentasi, source, dependency, worktree
lama, runtime backup dan data privatnya tidak ikut dihapus. Membaca roadmap tidak
mengizinkan source discovery, backfill, migrasi, deployment atau perubahan izin.

## Referensi lama yang tetap berguna

- [Platform vision](PLATFORM-VISION.md) mempertahankan ownership dan batas data.
- [NK roadmap](NK-ROADMAP.md) mencatat consumer independen; source/model NK belum
  dibawa ke main oleh task dokumentasi ini.
- [Roadmap NADI lama](NADI-ROADMAP.md), [runtime design](NADI-RUNTIME-002.md),
  [acceptance Phase 1](NADI-PHASE-1-ACCEPTANCE.md), dan
  [repository status](REPOSITORY-STATUS.md) disimpan untuk desain/evidence historis.
  Status fase/checkpoint di sana bukan backlog aktif atau status runtime terkini.

Dua roadmap Laravel dan MTBF/MTTR di atas memandu pengembangan produk sekarang.
Dokumen lama tidak memberi izin memulai deployment, migrasi atau source collection.
