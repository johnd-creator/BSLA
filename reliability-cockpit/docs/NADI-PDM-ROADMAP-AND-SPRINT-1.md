# Roadmap reconciliation and proposed Linear mapping

31 Oktober 2026 · Usulan, belum menjadi issue Linear yang dibuat. Judul/ID di bawah adalah **planning keys lokal**, bukan ID Linear nyata. Tidak ada Linear workspace/issue yang diverifikasi atau diubah oleh tugas ini. Owner adalah fungsi tanggung jawab, bukan penunjukan orang tanpa persetujuan.

## Phase 0–5 tetap utuh

[Official roadmap](../../plans/NADI-ROADMAP.md) menyimpan seluruh sejarah. Urutan eksekusi ini tidak mengganti Phase atau mengklaim completion baru.

| Phase existing | Kontribusi prioritas baru | Status yang tidak boleh dinaikkan otomatis |
| --- | --- | --- |
| 0 Factual Foundation | Preserve Registry, source evidence, read-only factual views | Accepted scope existing, bukan semua source/domain lengkap |
| 1 Evidence Expansion | Data Integration + offline crosswalk/coverage review | CURRENT/PARTIAL, freshness/governance/F03 gates tetap |
| 2 Collaborative Engineering | PdM workflow clarity, inspection/review/Case | Foundation merged, operational acceptance/field validation tetap partial |
| 3 Diagnostic & PdM Intelligence | Human analysis dahulu; discovery comparability dan KPI contracts | Tidak ada diagnosis, threshold atau automatic estimates baru |
| 4 Recommendation Action Loop | Contextual Recommendation/WO/SR traceability existing | Local foundation bukan operational work authorization/distribution |
| 5 Organizational Learning | Retain audit, revisions/outcome provenance sebagai prasyarat | Planned, bukan sprint analytics baru |

## Urutan yang diusulkan

**Sekarang**: PO menyetujui blueprint → **Sprint1**: lima pintu dan tiga layar lebih jelas → **berikutnya**: engineer validation + offline mapping discovery → **kemudian**: approved KPI contracts dan qualification → activation/UAT tersendiri. Excel existing dibuat mudah ditemukan lebih dulu; jangan import ulang atau memperluas canonical evidence untuk mengisi layar. History/Q01–Q10/M01–M07/UX tracks tetap referensi; tidak menghapus task F03, data quality atau audit yang belum selesai.

| Planning key / proposed Linear title | Existing roadmap mapping | Dependency / owner | Acceptance / gate |
| --- | --- | --- | --- |
| RESET-S1-01 — Lima entry dan route parity | UX-03, Phase2 ENG-UX-01 | PO blueprint; frontend | Semua route audit dapat ditemukan dengan label baru, deep links tetap; tidak mengganti auth |
| RESET-S1-02 — Register dan dua jenis history | UX-06, M03/M04 (presentation only) | S1-01; frontend | Counts inspeksi/source dipisah, arsip existing reachable; byte/page budgets sama |
| RESET-S1-03 — Editor dan detail kontekstual | M01/M02 input presentation; ENG-UX-01/02 | S1-01; frontend + engineer reviewer | Semua field existing available; primary/state dan cancel/readback jelas; tidak mengubah DTO/metode |
| RESET-S1-04 — Contextual Case/Recommendation/review | M05/M06, ENG-UX-02, ADV-03, Phase4 | S1-03; frontend | Exact native evidence/independence, capture refusal, SR≠WO dan all legacy entry retained |
| RESET-S1-05 — Preservation and PO walkthrough | UX-09, M07 preparation | S1-01–04; QA + PO | Matrix PASS, states/responsive/accessibility; PO acceptance dicatat tanpa mengaktifkan operasional |
| RESET-NEXT-01 — Engineer decision packet | M01/M02, Q01–Q10 | Engineering authority/custodian | G01/G02 + method P1 signed scope/version; P2 tetap separate |
| RESET-NEXT-02 — Offline crosswalk inventory | Phase1, M03/M04 | Source owners + contracts | Sanitized verified/missing/forbidden inventory; tanpa production call |
| RESET-NEXT-03 — Reliability KPI contracts | Phase1/3, KPI evidence catalog | NEXT-02 + reliability/operations | Failure/exposure/repair definitions + fixtures; tidak ada invented metric |
| RESET-GATE-01 — Runtime parity/release preflight | UX-01, runtime recovery track | Operator/reviewer, sebelum deployment apa pun | Reviewed main+runtime capabilities reconciled; account policy/overlay/controller compatibility tidak hilang |

Saat dipindah ke Linear nanti: cari duplikasi berdasarkan task ID/judul dan tautkan ke M/UX/Phase existing; simpan implementasi, CI, merge, visibility, engineer acceptance dan operational acceptance sebagai status/bukti berbeda. Tidak menandai issue lama Done hanya karena dokumen ini merged. Tidak ada issue-write/assignment/subscription pada task ini.

## Bounded Sprint 1 yang bisa disetujui

Usulan kapasitas: satu sprint singkat, estimasi 5–7 engineer-days total, dikonfirmasi tim; bukan tanggal/komitmen personel. S1-01 (1 hari), S1-02 (1–2), S1-03 (1–2), S1-04 (1), S1-05 (1). Backend/QA reviewer membantu mengawasi contract parity; tidak menulis endpoint baru.

- **S1-01** owner frontend: `web/lib/navigation.ts`, `AppNavigation.tsx` dan contextual links. Uji exact routes, active group, direct URL, keyboard/mobile drawer; no rename/delete.
- **S1-02** owner frontend: `PdmCenter.tsx`, `PdmHistory.tsx`, `PdmSourceHistory.tsx`. Label counts/type, explicit history entry dan empty/error messages. Tidak mengubah limit=1, server filters, keyset/byte bounds atau load seluruh workbook. PENDING/NOT_ASSESSED dan estimasi-runtime disclosures tetap.
- **S1-03** owner frontend: `PdmMeasurementForm`, `InspectionDetail`, origin/follow-up/capture components. Group/progressive disclosure; semua field/conditional validation tetap; tidak memecah ke wizard baru. Guard cancel/navigation/error-focus tetap.
- **S1-04** owner frontend: `PdmInspectionWorkflow`, contextual Case/Recommendation entry existing. Save/readback/submit tetap terpisah, independent reviewer exclusions dan exact revision handoff; tidak membuat action/entity otomatis atau Maximo lookup/write.
- **S1-05** owner QA/PO: jalankan suite relevant existing dan bounded UAT fixture; rekonsiliasi preservation matrix, screenshots desktop/mobile/light/dark dan deep links. Runtime release hanya setelah RESET-GATE-01 + separate authorization; sprint implementation tidak termasuk deployment.

### Exit dan stop rules

PO bisa menunjukkan alur tanpa Case wajib, menemukan arsip yang sudah ada, membedakan approval rekam dengan kondisi aset, serta melacak nilai/revisi/alasan. Semua fitur matrix memiliki entry dan regression evidence. Exact-head CI + review required. Jika perubahan menuntut DTO/role/grant/schema/page-budget/Case evidence/estimation changes, **keluarkan dari Sprint1** dan buat proposal terpisah; jangan menyelundupkan lewat label UX.

Tidak termasuk sprint: redesign dashboard, framework migration, user/account provisioning, migration007, history import, new Excel upload wizard, source discovery execution, DCS collector, KPI implementation, automatic diagnosis, alerting, operational rollout, attachment custody activation atau penghapusan modul. Runtime aktif berada di luar ancestry main; deployment dari main saja berisiko kehilangan fungsi existing. Gate tersebut harus dibereskan oleh task berizin terpisah sebelum source selection.
