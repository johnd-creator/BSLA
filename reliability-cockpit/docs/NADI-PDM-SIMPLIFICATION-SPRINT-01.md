# NADI-PDM-SIMPLIFICATION-SPRINT-01

31 October 2026 · isolated frontend implementation · requirements S1-01–S1-05.

The Product Owner authorized the PR113 blueprint direction and this implementation.
This candidate simplifies the existing product; visual/UAT acceptance is still pending.
Main baseline: `f1fc4e8b395691a17fe6d986bf14c772d37c1f2c`. Blueprint/base:
[PR113](https://github.com/johnd-creator/reliability-knowledge-starter/pull/113),
`2437fdb3b12f8ab63d56236dbb532caa7e39b671`, verified OPEN/DRAFT before publication.
Implementation branch: `codex/nadi-pdm-simplification-sprint-01`, stacked on PR113.
PR107 remains separate and OPEN. Final immutable implementation SHA and exact-head
backend/frontend CI are recorded in the delivery PR/checks and handoff.

## What engineers see

| Requirement | Implemented behavior | Principal source (`web/`) |
| --- | --- | --- |
| S1-01 | Exactly Beranda, Aset, PdM Center, Tindak Lanjut, Laporan. Existing technical/asset/Engineering routes remain in labeled utilities; Action Board offers contextual Case, Recommendation, Advisory, Inbox and audit links. | lib/navigation.ts; components/AppNavigation.tsx; RecommendationWorkspace.tsx |
| S1-02 | Compact authorized population/current-page counts; unchanged limit1 inspection paging. Original measurements and provisional Excel source groups have separate selectors/counts. Complete observations and mandatory pending/unknown warnings remain available. | components/PdmCenter.tsx; PdmHistory.tsx; PdmSourceHistory.tsx |
| S1-03 | One continuous editor: A Pekerjaan & Aset, B Pengukuran, C Observasi & Analisis, D Referensi & Bukti. Detail prioritizes context, readings, human analysis and authorized action; full provenance/SR/evidence remain accessible. Invalid fields expand their disclosure and receive focus. | components/PdmMeasurementForm.tsx; InspectionDetail.tsx; PdmFollowUpEditor.tsx; PdmFollowUpDetail.tsx |
| S1-04 | Ordinary inspections can end after independent review. Eligible native APPROVED records offer an optional Case. Reviewer deliberately selects a decision; rationale and existing server permissions still govern submission. | components/PdmInspectionWorkflow.tsx |
| S1-05 | Actual React components tested with synthetic intercepted responses and disposable UI→API→PostgreSQL fixtures. Responsive, keyboard, draft, review, source-history and existing security suites retained. | scripts/pdm-simplification-browser.mjs; pdm-input-browser.mjs; pdm-auth-browser-check.py |

No new backend requirement was needed. The 28 application page files are byte-identical
to the blueprint base. DTOs, handlers, auth/session policy, hooks owning commands/drafts,
source budgets and source collectors are unchanged. The Sprint scope guard runs in CI.
Tier2 graph checks on this checkout reported partial JSX and excluded test/docs/
asset subtrees; direct source/diff/route-file verification supplies those claims,
not graph completeness.
No new permanent frontend or operational database was created.

## Acceptance evidence and limits

- All 16 `check:*` script groups, TypeScript, ESLint and production build run locally;
  one pre-existing EngineeringWorkspace hook-dependency warning remains outside scope.
- [Visual evidence](evidence/nadi-pdm-simplification-sprint-01/README.md): matched
  baseline/candidate, seven actual-component screens × four widths × two themes.
  Candidate axe WCAG A/AA scans have zero violations. Overflow and interactive checks
  also run; axe does not certify complete accessibility or engineer usability.
- Ordinary native create/readback, failed-save/same-intent retry, zero/null, origin,
  manual analysis/SR, edit/clear, submit, return→revise→resubmit, independent review,
  audit and exact-revision Case evidence are covered by component/API tests.
- Case creation/link503/retry retains one Case and the same evidence request intent.
  No automatic Recommendation or Maximo command occurs. Provisional Case denial,
  history RAW unknowns, denied/loading/error states and byte/keyset limits retain
  existing regressions. Physical workbook preservation is covered by unchanged
  hermetic backend fixtures; this sprint does not reimport live workbooks.
- 13 actual-component draft/session scenarios pass: focus refresh, pending/lost ACK,
  transient503, bounded paging, multiline capture, changed subject/role/asset scope,
  and revoked401/403. Four actual UI→trusted API→PostgreSQL scenarios pass for
  origin/analysis/reported SR, readback/retry/revisions and explicit clear.
- Existing localization399, integration67, experience107 and source-history15 browser
  checks pass. Existing date42, login/logout56 and reports browser suites also
  pass locally. Final exact-head backend/frontend CI is a delivery gate, separately
  bound to the implementation SHA in the PR; local results alone do not satisfy it.

The standalone login presentation and global auth enforcement are unchanged. Tests
use synthetic identities and labels, not an operational login or live plant evidence.
No thresholds, diagnoses, measurement defaults, canonical mappings or KPIs are added.

## F01–F24 validation matrix

Original obligations and source anchors remain in
[the blueprint preservation matrix](NADI-PDM-FEATURE-PRESERVATION.md).
Here `PASS` means source preservation plus the named regression scope, not live UAT.
Backend suites below run in exact-head CI with disposable fixtures. Component paths
are relative to `web/components/`; Python tests to `tests/`.

| ID | Original behavior → new entry | Affected / preserved source | Regression evidence | Result / limit |
| --- | --- | --- | --- | --- |
| F01 | Typed native multi-point, zero/null, ≤100 → B Pengukuran | PdmMeasurementForm; lib/pdm-input unchanged | pdm-input-browser; test_pdm_input | PASS; no field/limit/default change |
| F02 | Provisional workbook transcription/exclusivity → editor source mode | PdmCaptureEditor and DTO unchanged | check:pdm-input; auth browser; test_pdm_input_capture | PASS; no canonical promotion |
| F03 | Origin union/department/unknown → A and detail | PdmWorkOriginDetail unchanged; form composition | UI/API origin regression; test_pdm_work_origin | PASS; literal text retained |
| F04 | Human analysis/optional follow-up → C and detail | PdmFollowUpEditor/Detail | UI/API save/edit/clear; test_pdm_manual_follow_up | PASS; narrative remains human |
| F05 | Exact reported-unverified SR, max10 → D and detail disclosure | PdmFollowUpEditor/Detail | follow-up checks/UI/API; test_pdm_manual_follow_up | PASS; no lookup/write or WO equivalence |
| F06 | Authorized filters/bounded pages → Register | PdmCenter | new limit1/count/query/Back tests; auth paging; test_pdm_input | PASS; population differs from page |
| F07 | Native raw history/single-revision scatter → Pengukuran Asli | PdmHistory | pdm-input-browser; test_pdm_input | PASS; no joined/interpolated trend |
| F08 | Raw source groups/filters/keyset/byte pages → Sumber Excel | PdmSourceHistory heading/composition only | source-history browser15; test_pdm_source_history | PASS; authorization/paging unchanged |
| F09 | Immutable physical source/profile/alias/batch/receipt proofs → Excel archive | owning backend unchanged | test_pdm_complete_plan; test_pdm_complete_postgres | PASS in fixture scope; no live reimport or new count attestation |
| F10 | Independent review/contributor exclusion/revise → Detail actions | PdmInspectionWorkflow | return/revise/resubmit/component audit; test_inspection_workflow | PASS; server remains authority |
| F11 | APPROVED native→exact frozen Case; partial link retry → optional Case | PdmInspectionWorkflow | Case503/retry/same-intent browser; test_engineering_integrity | PASS; one Case, exact revision |
| F12 | Capture excluded from Case/plot → visible ineligible reason | existing capture gates unchanged | capture checks; test_pdm_input_capture | PASS; review does not qualify source |
| F13 | Case create/investigation/evidence/review/history → Tindak Lanjut/utilities/deep URL | CaseWorkspace/Form/FrozenCaseEvidence unchanged | localization/experience; engineering suites | PASS; exact Case links retained |
| F14 | Recommendation draft/review/reopen/frozen existing WO → Tindak Lanjut | RecommendationWorkspace contextual links only | check:engineering-fixes; recommendation workflow tests | PASS; no entity/lifecycle merge |
| F15 | Advisory review/publication, authorized Inbox/ACK → contextual navigation | AdvisoryWorkspace unchanged | localization; test_advisory; test_advisory_http | PASS; existing authorization applies |
| F16 | CAS/lost ACK/immutable actor/revisions → all existing workflows | usePdmCommand unchanged | auth/input/UI/API browser; manual/engineering integrity suites | PASS; no optimistic persistence claim |
| F17 | Same-session draft, scope clearing/unsaved guard → continuous editor/navigation | PdmDraftContext unchanged; PdmCenter location handling | auth13; dirty Back/cancel; section hash Back/Forward | PASS; no persistence expansion |
| F18 | Session identity/CSRF/Origin/RBAC/asset visibility → same entries | trusted backend/middleware/proxy unchanged | auth13; local/global auth/bounded HTTP; backend access suites | PASS; no grants/account changes |
| F19 | Metadata separate from attachment custody → D/detail disclosure | InspectionDetail composition; attachments service unchanged | UI field validation; test_attachments | PASS; no upload activation |
| F20 | Registry/six asset detail views/exact identity → Aset | asset page files unchanged | 28-page byte guard; localization; Mart/backend suites | PASS; no fuzzy identity |
| F21 | Maintenance/WO/FMEA/RCFA/overhaul → asset utilities | navigation only; underlying pages unchanged | UX route inventory; integration/reports checks | PASS; unresolved RCFA remains explicit |
| F22 | Overview/reports/integration/Data Trust → Beranda/Laporan/utilities | factual views unchanged | integration67/localization399/experience107; factual policy/report suites | PASS; unknown never becomes healthy/current |
| F23 | Runtime interpretation/nonpersisted estimate → preserved active preview | runtime-only files read-only; not backported | private source fingerprint comparison | RELEASE GATE PENDING; no runtime acceptance from main tests |
| F24 | Runtime demo-account policy/controller → preserved active preview | runtime-only files/services read-only | private source/process comparison | RELEASE GATE PENDING; no account/session reads or writes |

## Independent review and runtime parity

An independent reviewer inspected the complete implementation and acceptance delta.
Confirmed corrections: preserve query/hash and location reference after completion;
remove competing Input actions in editor/detail; exact-route `aria-current`; retain
dirty editor state during hash-only section Back/Forward; demote filter submission
so Input Pengukuran remains the primary register action. Review choice/rationale
also reset defensively by record/revision/status. An initial stale-radio concern
was withdrawn after tracing the owning reload/remount behavior; it is not presented
as a proven original defect. Final bounded review found no unresolved integrity,
authorization, payload or lifecycle blocker. PO usability remains a separate gate.

Read-only inventory confirms the active preview has F23 source interpretation and
nonpersisted estimate components/services plus F24 demo-account policy that are not
part of this base. Relevant source fingerprints and frontend/API service process
identities/restart counts were unchanged during this task. Private host/process/
source metadata stays local and is not published. No active account/session or
application DB was inspected or changed by this sprint.

Before any later activation, a separate task must reconcile those runtime-only
capabilities with this candidate, preserve raw-source/provenance and estimate
separation, prove demo-account/controller/schema/session compatibility, perform
reviewed rollback/readback qualification, and obtain explicit activation approval.
Source PASS is not a safe-deployment certificate. Existing private overrides,
original dirty files and `23496711.xls` remain untouched. Temporary test PostgreSQL
is disposable and does not replace an operational store.

## Delivery state

IMPLEMENTED/TESTED: this isolated candidate and synthetic/disposable scope.
MERGED: NO. VISIBLE on localhost: NO (active preview unchanged).
PO VISUAL/ENGINEER ACCEPTANCE: PENDING. F23/F24 release compatibility: PENDING.
Phase0–5 history and Phase1 engineering gates remain unchanged.

Next: **Senior Review → PO UX Acceptance → Separate Runtime Compatibility & Activation Task.**

### CI qualification correction

The first run on c452945 passed backend acceptance but the frontend date browser
asserted visibility of the now-collapsed record provenance. The regression now
explicitly opens that disclosure and retains all original exact date/ISO/timezone
assertions. Both America/Los_Angeles and Pacific/Kiritimati synthetic contexts pass
(42 checks); no formatter, timestamp or runtime source changed. Final CI is bound
to the subsequent delivery head in the PR, not the first backend-only success.
