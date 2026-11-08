# Roadmap NADI Laravel

Baseline checkout: 7 November 2026. Status "ada" berarti implementasi ditemukan
pada checkout, bukan jaminan semua fitur lulus QA hari ini atau siap produksi.
Acuan operasional: [README NADI](../NADI/README.md) dan runbook platform.

## Arah dan cara kerja

Satu developer mengerjakan langsung checkout aktif: **edit → uji sesuai dampak →
lihat hasil di preview**. Ambil perubahan kecil yang berguna, pertahankan data dan
perubahan pengguna. Tidak ada phase/handoff, worktree atau tim paralel wajib.
Persetujuan hanya diperlukan untuk keputusan/tindakan yang memang mengubah
scope, data, akses, integrasi atau deployment. Checklist di sini bukan izin eksekusi.

## Fondasi yang sudah ada

- Laravel 13/Blade/Vite, preview 8010, login lokal dan empat role dengan server Gate.
- Inventaris dan Registry dibedakan; Asset/detail/mapping, history WO, kelompok
  aktivitas tahunan, detail dan bukti waktu diekspos melalui GET API yang ada.
- PdM rutin/request/template, precision tanggal/jam, analisis/rekomendasi tertaut,
  history, tren per titik dan timeline lokal.
- Log gangguan manual dengan satu event/multi-asset, role sebab/terdampak/unknown,
  revisi, idempotensi, stale-edit protection dan cancellation tanpa menghapus histori.
- Action Board dengan prioritas engineer, kandidat lokal/repeat-WO, rekomendasi
  dan WAPPR terpisah; tidak ada skor/approval otomatis.
- Beranda, feed aktivitas, kualitas data, CSV ringkasan dan UI ringkas responsif.
- Existing local SQLite diperluas kompatibel untuk data development; source
  Asset/WO tetap tidak direplikasi atau ditulis oleh Laravel.

## Pekerjaan yang masih berguna

### 1. Stabilitas alur engineer dan kualitas tampilan

- [ ] Ulangi QA browser alur penuh yang terdampak perubahan terakhir: request →
  measurement → analisis/rekomendasi → prioritas; log gangguan → koreksi/cancel →
  timeline; role read-only/Admin; stale form, submit ulang, Back/Close dan mobile.
- [ ] Jaga label basis tanggal, scope, partial/outage dan sumber link konsisten
  pada kartu, detail, CSV dan drilldown. Jangan menyamakan unknown dengan zero.
- [ ] Selesaikan gap usability yang ditemukan dari pemakaian nyata, tanpa
  memigrasikan framework, menambah approval berlapis atau menulis ulang fitur stabil.

Selesai jika perjalanan relevan teruji, hasil visual/interaksi jelas, dan batas
QA yang tidak bisa dijalankan dinyatakan. Lihat [QA perjalanan](../NADI/docs/workflow-journey-qa.md).

### 2. Reliability bertahap, dengan evidence

- [ ] Ikuti [roadmap MTBF/MTTR](MTBF-MTTR.md): validasi kejadian manual dan korelasi
  WO lebih dahulu, lalu exposure/repair boundary dan read model versi-tertentu.
- [ ] Bila Pareto WO dibuat, sepakati tipe/status/period/deduplikasi dan beri label
  "WO terklasifikasi", bukan kejadian, downtime, loss atau reliability score.
- [ ] Pertahankan prioritas engineer sebagai keputusan manual; kandidat review
  bukan diagnosis dan bukan pengganti validasi event.

### 3. Operations dan historian, belum terhubung

- [ ] Peroleh serta verifikasi referensi layout proses bila layar Operations
  dilanjutkan; jangan mengarang equipment, pipa, live value atau alarm.
- [ ] Gunakan mapping Asset↔AF yang terverifikasi dan akses historian yang diminta
  pengguna. Bedakan technical tag registry dari governed signal.
- [ ] Rancang read-only cache/quality/age/coverage dan exposure bersama roadmap
  reliability. Tidak ada polling baru/PI auth retry sebagai efek samping UI.
- [ ] Integrasi CEMS tetap terpisah dan opsional; API tersedia tidak berarti
  proyeksi ke NADI sudah ada.

### 4. Data lokal dan gerbang deployment

- [ ] Untuk migrasi berikutnya, verifikasi target SQLite existing, backup yang bisa
  direstore, preservasi akun/histori, upgrade compatible dan failure recovery.
- [ ] Sebelum shared/production rollout: sepakati target deployment, authentication,
  HTTPS/session, least privilege, ownership persistence, backup/restore/RPO-RTO,
  retention, monitoring dan rollback. Ini keputusan baru, bukan tugas bootstrap rutin.
- [ ] Sebelum backend rollout: gunakan image/config parity dan exact-service
  runtime tools; pertahankan single collector dan semua store/volume/cursor.
- [ ] Uji schema/DTO lintas consumer, performa/pagination, outage dan keamanan pada
  fixture/staging yang sesuai. Tidak ada source production dalam test suite.

Jangan memberi label siap produksi sebelum gerbang yang relevan benar-benar
terverifikasi. Retention/purge, SSO/MFA dan penggantian storage tidak diaktifkan
hanya karena tercantum sebagai kebutuhan masa depan.

## Pemeriksaan sesuai dampak

- Dokumentasi: kesesuaian kode/fakta, tautan lokal, `git diff --check`.
- Laravel: test relevan lalu suite lebih luas bila perlu, Pint, Composer checks;
  frontend: `npm run test:ui`, `npm run build`, browser QA pada fixture terpisah.
- API/collector/contracts: suite komponen, schema set aktual, regresi scope/null/
  clock/permission/cursor sesuai perubahan; jangan restart collector untuk docs/UI.
- Laporkan test, render, browser, runtime activation dan readiness secara terpisah.

## Batas tetap

Tidak ada source write, automatic score, failure count dari WO mentah, risiko/
approval yang diturunkan dari nama role, source credential di consumer, penggantian
DB/volume, atau penghapusan history. Panduan rinci ada di [AGENTS](../AGENTS.md).

## Source additions, 8 November 2026

Disruption/WO links and versioned local Reliability review are implemented in
[NADI](../NADI/docs/reliability-evidence.md). Official KPIs and exposure remain
NOT_READY. The [historian demonstration](../NADI/docs/historian-demand.md) is
simulation-only. The [CEMS RAM bridge](../NADI/docs/cems-live.md) has separate
source-owner/cutover gates; publication alone activates neither source.
