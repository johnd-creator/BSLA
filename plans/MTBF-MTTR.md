# Roadmap MTBF / MTTR berbasis evidence

Status 7 November 2026: **fondasi evidence tersedia sebagian; KPI belum siap**.
Rencana ini melanjutkan NADI Laravel dan backend/Mart existing. Tidak membuat
collector/store baru dan tidak mengaktifkan perhitungan hanya dari WO.

## 1. Yang tersedia dan yang belum

| Area | Sudah ada | Gap sebelum KPI |
|---|---|---|
| Asset | Identitas inventaris/Registry, scope dan relasi yang eksplisit | Populasi KPI, mapping lintas sumber dan perubahan batas aset harus disepakati |
| WO/Mart | Failure code dipertahankan; petunjuk problem/faildate/parent/origin/task/follow-up terbatas | Satu WO bukan satu failure; completeness dan makna belum governed |
| Waktu | Actual start/finish zoned untuk CLOSE; evidence unknown/invalid berbeda | Elapsed execution bukan repair/restoration; clocks histori bisa kosong |
| Log gangguan | Event ID lokal, multi-asset, tanggal/presisi, recovery opsional, revisi/cancellation | Observasi engineer belum workflow validasi failure untuk KPI |
| PdM/Action Board | Temuan, rekomendasi, tren per konteks, penilaian manual | Bukan diagnosis, failure classifier atau skor reliability otomatis |
| Historian | Knowledge/registry PI dan store/API existing | Belum ada exposure interval NADI yang tervalidasi/terintegrasi |
| KPI legacy | WO-only MTBF/MTTR/availability null + NOT_READY; snapshot lama dimask di read API | Jangan menghidupkan ulang proksi angka lama |

Evidence teknis: [typed source evidence](../maximo-collector/src/adapters/maximo/reliability_fields.py),
[semantik Maximo](../maximo-knowledge/docs/mx-015a-maintenance-failure-semantics.md),
[log manual](../NADI/docs/asset-disruption-log.md),
[kontrak API](../reliability-cockpit/docs/reliability-mart-query-api.md).

## 2. Definisi sebelum implementasi

### Failure occurrence yang divalidasi engineer

- [ ] Sepakati apa itu loss of required function/failure, batas Asset/system,
  planned outage, trip tanpa kerusakan, degraded operation dan kejadian unknown.
- [ ] Tentukan status observasi → review → validated/rejected/void beserta siapa
  yang boleh memvalidasi, bukti, alasan dan revisi. Role ENGINEER saat ini dapat
  mencatat; itu belum berarti setiap log otomatis validated.
- [ ] Tetapkan event identity yang stabil dan relasi many-to-many ke WO/evidence.
  Beberapa WO bisa satu kejadian, satu WO bisa terkait beberapa kejadian, dan
  kejadian tanpa WO harus tetap mungkin. Pertahankan tautan uncertain/unresolved.
- [ ] Deduplication adalah keputusan dengan provenance, bukan fuzzy match atau
  kesamaan tanggal/kode. Task, parent, follow-up dan cancel punya aturan eksplisit.
- [ ] Pisahkan aset penyebab, terdampak dan unknown; satu event dihitung sekali
  global dan menurut membership yang disepakati. Jangan menjumlahkan semua hitungan
  aset untuk total plant atau menyalin satu durasi ke tiap aset sebagai downtime.

**Gerbang:** contoh engineer dengan duplicate, multi-WO/multi-asset, missing-date
serta rejected/void event dapat direview dan direkonsiliasi tanpa kehilangan audit.

### Operating exposure untuk MTBF

- [ ] Sepakati failure population, periode, zona dan boundary operasi yang sama.
  MTBF = jumlah jam operating exposure tervalidasi / jumlah failure eligible.
- [ ] Tentukan RUN/STOP/STANDBY/UNKNOWN dan aturan duty/standby, planned stops,
  initial/last state, gap, quality buruk dan waktu di luar cakupan pengamatan.
- [ ] Gunakan mapping Asset↔AF/tag yang diverifikasi engineer. Korelasikan event
  dan status historian pada clock yang selaras, toleransi waktu serta provenance.
  Historian memberi evidence, bukan otomatis penyebab atau validator failure.
- [ ] Hitung durasi interval yang diketahui dan covered duration/coverage; jangan
  menganggap jam kalender, panjang periode, source Asset status atau ketiadaan WO
  sebagai jam operasi. Unknown gaps tidak boleh diisi status sehat/running.
- [ ] Simpan basis interval, sumber, quality flags, timestamp, unit, rule version
  dan alasan eksklusi. Hindari overlap/double-count pada batas periode/pergantian aset.

**Gerbang:** exposure pilot dapat direkonsiliasi dengan bukti operasi/historian,
coverage diperlihatkan, dan semua interval unknown dikeluarkan/dinyatakan sesuai
kebijakan. Integrasi historian saat ini masih pekerjaan masa depan. Jangan retry
PI authentication atau memulai backfill tanpa permintaan yang mencakupnya.

### Repair / restoration untuk MTTR

- [ ] Pilih definisi: mean active repair time atau mean time to restoration.
  Keduanya bukan sinonim; jika dibutuhkan keduanya, gunakan nama/field terpisah.
- [ ] Definisikan awal/akhir: failure onset, acknowledgment, repair start,
  repair complete, test/return-to-service, termasuk waiting/logistics/admin delay.
  Catat inclusion/exclusion secara eksplisit, tanpa mengasumsikan dari WO status.
- [ ] Kaitkan interval ke failure tervalidasi dan aset yang tepat; satu event
  multi-asset dapat punya waktu restoration berbeda. Tidak gunakan event-level
  recovery manual sebagai duration tiap aset tanpa evidence.
- [ ] Tentukan completed eligible repair/restoration episodes sebagai denominator
  yang sesuai numerator; tampilkan ongoing/right-censored dan incomplete events
  secara terpisah. Jangan menghitung open event sebagai nol durasi atau membuangnya
  tanpa mengungkap bias populasi.
- [ ] Tolak timestamp naive/terbalik/invalid; date-only tetap date-only dan tidak
  diberi midnight. Durasi nol yang terbukti dibedakan dari missing. Intervals
  lintas periode, recurrence/reopen, overlaps dan multiple crews perlu aturan.

**Gerbang:** MTTR pilot dapat dijelaskan dari interval berpasangan dengan evidence.
`actfinish - actstart` tetap **elapsed execution WO**, `actlabhrs` adalah effort,
`reportdate/statusdate` bukan failure/restoration, dan `downtime` Maximo adalah
boolean. Jangan gunakan salah satunya diam-diam sebagai repair duration.

## 3. Kualitas data dan kontrak hasil

- [ ] Hasil membawa value nullable, unit, status readiness, definisi/rule version,
  asset population, period/timezone, numerator, denominator, coverage dan blockers.
- [ ] Bedakan: missing, unavailable, invalid, conflicting, unverified, partial,
  out-of-scope, excluded dan validated. Jangan gabungkan menjadi angka confidence
  atau nol tunggal. Source sync/projection freshness berbeda dari waktu kejadian.
- [ ] Nol failure hanya sah di cakupan pengamatan yang terbukti. Tampilkan zero
  observed failures + exposure; jangan MTBF=0 atau infinity tanpa kebijakan
  statistik eksplisit. Missing data bukan zero failures.
- [ ] Threshold coverage/minimum evidence ditetapkan engineer, tidak ditebak di UI.
  Simpan gap/exclusion counts; cegah agregasi populasi/period/rule yang berbeda.
- [ ] Read API tidak membocorkan vendor evidence/personal data internal. Tambahkan
  DTO allowlist/version dan regression fixture bila kontrak perlu diperluas.
- [ ] Snapshot perhitungan bisa ditelusuri/reproduksi dan revisi tidak menghapus
  hasil lama. Tentukan invalidation setelah event correction dan source update.

Availability menjadi metrik terpisah dengan definisi required/operating/downtime
exposure dan overlap yang disepakati. Jangan langsung memakai MTBF/(MTBF+MTTR)
atau WO downtime bila asumsi statistik/operasionalnya belum terpenuhi.

## 4. Urutan pekerjaan yang disarankan

1. **Event review lokal:** perluas log manual yang sudah ada dengan validasi dan
   relasi WO yang governed setelah keputusan definisi disepakati. Tetap dalam
   owning store dengan additive migration/backup, tanpa perubahan sumber.
2. **Pilot evidence:** pilih scope Asset/periode kecil yang disepakati engineer;
   rekonsiliasi event dan repair boundaries, daftar unknown/duplicate dengan jelas.
3. **Exposure historian:** setelah akses/mapping diotorisasi, bangun pembacaan
   terbatas dari jalur PI existing, kualitas dan interval; tidak membuat collector
   paralel atau menebak tag. Jadwal/budget/caching ditentukan sebelum collection.
4. **Read model/versioned calculation:** implementasikan schema/DTO dan pure
   calculation dengan null/readiness gates; jangan mengganti data sumber.
5. **UI pilot NADI:** tampilkan basis hitung, evidence drilldown, coverage dan
   blockers. Engineer merekonsiliasi contoh sebelum angka disebut KPI tervalidasi.
6. **Rollout terbatas:** uji kompatibilitas, performance, RBAC, audit, backup/restore
   dan rollback; activation/deployment hanya berdasarkan permintaan terpisah.

Tidak ada tanggal atau janji production readiness sebelum definisi dan data cukup.
Pareto jumlah WO terklasifikasi dapat menjadi alat review awal dengan label yang
benar; Pareto kejadian/loss dan weighted scoring tetap pekerjaan berbeda.

## 5. Guard collection yang tidak boleh dilanggar

- Empat tahun kalender dari `reportdate`, Asia/Jakarta, adalah batas acquisition,
  bukan retention atau definisi periode failure. Older stored history tetap ada.
- Same terminal status CLOSE/CAN/CANCEL tetap frozen; CAN/CANCEL summary-only.
  Field evidence baru tidak mengizinkan mass refetch terminal/historical clocks.
- Request/page/rate/body caps, BSR/IP/CS01 scope, source locks, cursor rules dan
  single worker dipertahankan. Partial run bukan complete source scan.
- Tidak menambah source field/object/query/credential dari namanya saja. Tidak
  menyamakan schema technical presence dengan business semantics atau HTTP 400
  dengan permission denied.
- Tidak menghapus/menimpa database, snapshots, raw history, Registry atau mapping.

## 6. Pengujian minimum

Fixture sintetis: satu event banyak WO/aset; dua event satu WO; duplicate/cancel/
reopen; causal/affected/unknown; zero versus missing; ongoing/censored repair;
unknown coverage; overlap/batas periode; timestamp offset/naive/date-only; historian
bad quality/gap; stale edits/permissions/idempotency; event correction dan hasil
versi lama; fail-closed read API untuk legacy numeric KPI. Unit/contract tests
hermetic, tidak memakai produksi. Browser UI bukan bukti semantic validation.

## Governed source implementation, 9 November 2026

The NADI [operating/readiness workflow](../NADI/docs/reliability-operating-readiness.md),
[pilot calculator](../NADI/docs/reliability-calculation.md) and
[Supervisor decisions](../NADI/docs/reliability-supervisor-approval.md) are implemented.
Engineer methods, exact-asset evidence, immutable snapshots and selected-metric
attestations remain separate. MTTR does not require historian exposure; MTBF still
requires its complete eligible operating denominator. No WO-based shortcut is added.

The [MTTR pilot](../NADI/docs/mttr-real-data-pilot.md) verifies the end-to-end workflow
with fictional fixtures. Real operator/engineer failure and restoration evidence
is still required before calculating or approving operational results. No migration,
data import or real approval is performed by publication.
