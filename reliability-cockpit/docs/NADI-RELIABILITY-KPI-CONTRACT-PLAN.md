# Reliability Performance — contract-first KPI plan

**Rencana, tidak ada kalkulasi baru atau source request.** Tetap FastAPI + Next.js; owning store/collector/kontrak existing. [Catalog KPI existing](nadi-kpi-evidence-catalog.md) mengendalikan apa yang boleh ditampilkan. [KPI legacy](kpi.md) memiliki proxy failure-code CM/downtime dengan batasnya; tidak dihapus, diubah maknanya atau dipromosikan sebagai KPI reliability tervalidasi oleh dokumen ini.

## Satu definisi sebelum satu angka

| Kontrak kandidat | Field/aturan minimum yang perlu disepakati, bukan schema yang telah diimplementasikan | Owner keputusan |
| --- | --- | --- |
| Failure event | Stable event ID; canonical_asset_id BSR/IP/Registry; functional failure definition/version; occurred_at beserta timezone/precision; evidence refs dan revisi; qualifying type/status; verification state; duplicate/supersedes link | Reliability engineer + maintenance owner |
| Operating exposure | Asset, [period_start,period_end), timezone, operating intervals/hours, unit `h`, evidence source/version, missing/unknown intervals, shutdown/standby rules, effective asset membership | Operations + historian owner + reliability |
| Repair episode | Failure-event ID; repair started/restored timestamps; **active repair duration** dan **total outage** dibedakan; waits/planned downtime, reopen/overlap handling, exclusions/reason | Maintenance + reliability |
| KPI result | Metric definition/version, scope/asset set, window/as_of, numerator/denominator/unit, included/excluded event IDs, exposure coverage, maturity/status/reason, evidence/version lineage | Reliability owner + contract reviewer |

Jangan menyatakan fields ini tersedia dari Maximo tanpa mapping terverifikasi. Failure-code master yang forbidden tetap forbidden; status PM/CM, WO closed, `source_changed_at`, histori upload, case count atau tanggal input bukan failure/repair clock. Maintenance-event aktivitas saat ini menggunakan COALESCE(actual_start,source_changed_at): sesuai untuk aktivitas, **tidak** sesuai untuk exposure atau durasi repair. Existing failure/downtime DTO dan schema perlu gap analysis sebelum revisi versioned; tidak ada migrasi atau duplikasi data di tugas ini.

## Formula kandidat dan denominator

- MTBF (`h`) = jumlah operating exposure berizin dalam window / jumlah qualifying **distinct functional failure events** pada scope/window yang sama. Bukan selisih rata-rata tanggal WO; bukan calendar hours otomatis.
- MTTR (`h`) = jumlah **active repair hours** untuk episode qualifying yang complete / jumlah episode complete yang memenuhi definisi yang sama. Jika hanya total downtime yang tersedia, tampilkan sebagai downtime metric dengan definisinya; jangan diam-diam menyebutnya active repair MTTR. Formula legacy downtime/failures tetap berlabel legacy/proxy.
- Window setengah terbuka [start,end), ISO8601 + offset, disimpan terstandar dengan original time claim terpelihara. Attribution failure di boundary, repair lintas window, event open/censored, asset commissioning/decommissioning dan scope-change harus diputuskan sebelum exposure dianggap lengkap.
- Parent/child WO dapat menggambarkan satu failure, dan satu WO dapat mencakup lebih dari satu episode. Dedup berdasarkan event identity yang disahkan, bukan nomor WO semata atau fuzzy text. Overlap outage/repair ditangani tanpa double count menurut policy yang disetujui; interval tak diketahui tidak diisi nol.
- Aggregate fleet MTBF adalah total exposure / total qualifying failures pada populasi tetap, **bukan** rata-rata MTBF asset. Fleet MTTR memakai durasi dan count episode yang sama definisinya. Jangan mencampur population/window/definition versions.
- Jika failure count=0 dengan evidence dan coverage lengkap, value=null dengan alasan NO_FAILURES_OBSERVED; bukan0 atau infinity. Exposure tidak lengkap/missing, event identity ambigu, zero denominator atau clocks tidak sah menghasilkan value=null dengan reason berbeda. Jangan menentukan ambang coverage numerik tanpa owner approval.

## Readiness dan UI

Pertahankan classes VERIFIED/DERIVED_SAFE/BUSINESS_SEMANTICS_REQUIRED/DATA_NOT_AVAILABLE/DEFERRED. Label VERIFIED pada source fact tidak mengesahkan causal KPI. Sebelum definition/coverage gate PASS, Beranda/Laporan hanya menunjukkan fakta existing dan alasan “KPI belum dapat dihitung”; tidak ada dummy card angka, severity atau equipment-health traffic light.

Hasil KPI future harus bisa ditelusuri ke event/exposure asli beserta exclusions. Nilai provisional Excel, sumber assessment, overlay estimate runtime, review APPROVED atau Recommendation tidak memberi failure count/operating hours. Unknown relationship tetap tidak terhubung.

## Urutan kerja dan gate implementasi

1. Inventory offline DTO/schema legacy dan Mart serta evidence catalog; gap matrix setiap candidate field → verified source, missing, forbidden atau semantics required.
2. Owner menandatangani functional failure, repair-vs-outage, scope/window, denominator, censored-event dan exclusion rules. Catat versi dan effective date.
3. Buat proposal kontrak JSON Schema/semantic mapping di reliability-data-contracts, fixtures synthetic dan exposure/event lineage. Contract review sebelum service/API.
4. Implementasi kelak hanya pada owning store existing melalui compatible migration bila benar diperlukan. Factual query tetap read-only, source credentials tidak masuk Cockpit. UI membaca versioned result; tidak menghitung dari page WO yang dimuat browser.
5. Qualify offline against hand-reconciled reference set yang disahkan; engineer UAT dan per-action deployment approval terpisah. Legacy API tidak diganti diam-diam.

| Planned fixture | Expected invariant |
| --- | --- |
| Duplicate/child WO for one failure | Count event sekali; receipt/evidence masih lengkap |
| Zero failures, complete exposure | null + NO_FAILURES_OBSERVED |
| Missing exposure or failure-code authority | null + explicit unavailable/semantics reason, bukan0 |
| Repair open / interval crosses end | Censor/exclude sesuai signed rule; tidak memakai as_of sebagai restoration palsu |
| Planned outage / waiting material | Pisahkan active repair dari downtime |
| Overlap episodes and asset replacement | Tidak double count exposure; identity effective period jelas |
| Clock unknown/date-only/DST/window boundary | Ketelitian tidak dipromosikan; deterministik sesuai signed rule |
| Late correction / superseded event | Recompute versioned result tanpa menghapus audit |
| Different units/scopes/filter pages | Reject mixing, convert hanya dengan kontrak approved, pagination tidak mengubah KPI |

## Read-only Maximo ↔ PI / local DCS discovery and crosswalk plan

Tahap0 adalah **offline**: baca inventory/mapping/Registry dan dokumentasi existing dalam maximo-knowledge, pi-knowledge dan reliability-data-contracts. Pastikan apakah “local DCS Historian” adalah endpoint/interface terpisah, replika, atau sistem lain; jangan menganggap PI Vision adalah API historian dan jangan menganggap jalur Cockpit PI placeholder sudah merupakan integrasi. Catat interface/vendor/version, owner, permitted operations, source identity, time basis, quality dan unit tanpa menyalin credentials.

Tahap1 hanya jika nanti diotorisasi: owner menetapkan verified endpoint/object/tag/WebId/asset scope, account read-only, allowlist GET/HEAD/OPTIONS, quota/page/byte/time bounds, retry/circuit breaker, scheduled window dan stop conditions. Local DCS tidak otomatis boleh SQL direct atau protocol write. Discovery dieksekusi di owning knowledge/collector, tidak dari browser/Cockpit; tidak ada permintaan produksi pada task reset ini. Hormati sole controlled Maximo login exception yang sudah ada; tidak memperluas business methods.

Crosswalk kandidat harus memuat canonical Asset identity + site/org, source alias, exact AF/database/element/attribute atau documented historian tag identifier, relation role (equipment/measurement point), effective interval, point/axis, original quantity/unit, acquisition type/operating context, timestamp/quality semantics, evidence method/ref, verifier dan verification date/version. Identitas relation dan measurement comparability adalah dua persetujuan berbeda. Shared train/parent-child/one-to-many atau ambiguous mapping tetap explicit unresolved; jangan memilih “paling mirip”.

Reuse [Asset↔AF governance](asset-af-mapping-admin.md): internal reviewed operator flow, bukan public mutation API. Import current mapping hanya menerima allowlisted CENTRAL_PI alias dan schema existing; **jangan** menyelipkan DCS alias ke field AF. DCS extension perlu contract/version/owner review terlebih dahulu dan tetap di owning store existing. Candidate→independent verification→approved bounded import→read-only consumer adalah gate terpisah; belum ada automatic mapping atau canonical trend join.

Output discovery yang direncanakan: sanitized inventory, exact-source crosswalk candidates, unresolved list, signed unit/time/quality/comparability evidence, contract diff proposal dan bounded execution request. Semua tetap proposal sampai disetujui; tidak ada asset auto-registration, data migration, collector restart atau backfill tersirat.
