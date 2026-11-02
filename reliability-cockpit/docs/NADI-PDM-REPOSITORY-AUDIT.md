# Repository and runtime audit — 31 October 2026

## Evidence boundary

Tier2 task-directed audit. Graph project reliability-knowledge-starter points to the older root branch feature/pi-governed-source-adapter; recorded generation2026-08-24. Searches for PdM/Engineering components did not locate modern symbols. This is insufficient graph coverage, not evidence those features do not exist. Main/worktree source and exact runtime sources were read directly; no graph completeness or production acceptance is claimed. Scope: workspace page routes/navigation, PdM entry/history/review components, relevant domain/contract/runbooks/tests, official roadmap and PR105–112. This is not an exhaustive security/API audit.

Remote origin verified: https://github.com/johnd-creator/reliability-knowledge-starter. Main fetched at f1fc4e8b395691a17fe6d986bf14c772d37c1f2c. All merged commits below were checked as ancestors of that main. PR107 is OPEN, mergeCommit=null: the task wording “merged PR105–112” is corrected, not silently accepted.

| PR | Exact state / merge | Title |
| --- | --- | --- |
| [#105](https://github.com/johnd-creator/reliability-knowledge-starter/pull/105) | MERGED / `8bb1bcb2c485feeb792235c64b5aef6bbce5e3cc` | feat(nadi): integrate recovery, Design System V2 and experience rework |
| [#106](https://github.com/johnd-creator/reliability-knowledge-starter/pull/106) | MERGED / `35f3c101129241745e1795edd78a34c3617dccd7` | fix(nadi): validate stored evidence and prepare recovery rehearsals |
| [#107](https://github.com/johnd-creator/reliability-knowledge-starter/pull/107) | OPEN / `NONE` | fix(mart): harden F03 recovery restore and identity checks |
| [#108](https://github.com/johnd-creator/reliability-knowledge-starter/pull/108) | MERGED / `44bc1def5ba18802838bc5d40e04165685197696` | feat(nadi): preserve Engineering workflows and add provisional PdM input |
| [#109](https://github.com/johnd-creator/reliability-knowledge-starter/pull/109) | MERGED / `891dfee8a6606cbab64553a829863518f89e2cac` | feat(pdm): record work origin, manual analysis and reported SR references |
| [#110](https://github.com/johnd-creator/reliability-knowledge-starter/pull/110) | MERGED / `e84eaec0e38e57cf0f057abaeda04e34739b01f8` | fix(pdm): clarify access, render Indonesian dates, and stage history imports |
| [#111](https://github.com/johnd-creator/reliability-knowledge-starter/pull/111) | MERGED / `85e6bb61eb5cb724e436846b9bdeee31709dffd4` | feat(pdm): preserve complete provisional Excel source history |
| [#112](https://github.com/johnd-creator/reliability-knowledge-starter/pull/112) | MERGED / `f1fc4e8b395691a17fe6d986bf14c772d37c1f2c` | Publish exact PdM history bridge and bounded demo import support |

## Development runtime: privately verified, not published or changed

Read-only local checks compared the active paired source metadata, actual frontend/API service working directories and localhost health with main. The active source differs from main. Exact local process identities, source identities, paths and owning-store observations are retained only in the Product Owner's private local audit, excluded from this PR. Anonymous health is not authenticated UAT or a complete backend imported-code attestation.

Local inspection confirms that source-history availability and inspection-register availability must be evaluated separately. No local aggregate counts or database metadata are published here. Public historical source-plan coverage is documented in nadi-pdm-complete-history-01.md; it is not a fresh runtime visibility certificate.

The active source has additional source-reading/interpretation and account-policy behavior beyond this main baseline. Existing controller compatibility and those capabilities must be preserved by a separately reviewed release/parity task. This documentation PR does not integrate them or select a source. No source requests, DDL, grants, import, restart, authentication or controller change occurred. Controller identity/compatibility is not requalified by this product audit.

## Route inventory: main source, not runtime smoke certification

All28 page entry files below are retained. Route-group directories are layout boundaries, not URL segments. API proxy paths /api/cockpit/* and /api/engineering-qa/* retain their existing authority/bounded transport; /api/development health/status remain operator diagnostics, not product menu items. Proposed placement is in the navigation document; QA/lab routes retain their own feature gates.

| Existing route | Main source |
| --- | --- |
| `/login` | `reliability-cockpit/web/app/(authentication)/login/page.tsx` |
| `/action-board` | `reliability-cockpit/web/app/(workspace)/action-board/page.tsx` |
| `/asset-health` | `reliability-cockpit/web/app/(workspace)/asset-health/page.tsx` |
| `/assets/[...canonicalId]` | `reliability-cockpit/web/app/(workspace)/assets/[...canonicalId]/page.tsx` |
| `/assets` | `reliability-cockpit/web/app/(workspace)/assets/page.tsx` |
| `/data-quality` | `reliability-cockpit/web/app/(workspace)/data-quality/page.tsx` |
| `/engineering/[caseId]` | `reliability-cockpit/web/app/(workspace)/engineering/[caseId]/page.tsx` |
| `/engineering/advisories` | `reliability-cockpit/web/app/(workspace)/engineering/advisories/page.tsx` |
| `/engineering/cases` | `reliability-cockpit/web/app/(workspace)/engineering/cases/page.tsx` |
| `/engineering/inbox` | `reliability-cockpit/web/app/(workspace)/engineering/inbox/page.tsx` |
| `/engineering/lab` | `reliability-cockpit/web/app/(workspace)/engineering/lab/page.tsx` |
| `/engineering/local` | `reliability-cockpit/web/app/(workspace)/engineering/local/page.tsx` |
| `/engineering` | `reliability-cockpit/web/app/(workspace)/engineering/page.tsx` |
| `/engineering/qa` | `reliability-cockpit/web/app/(workspace)/engineering/qa/page.tsx` |
| `/engineering/workflow` | `reliability-cockpit/web/app/(workspace)/engineering/workflow/page.tsx` |
| `/equipment/[id]` | `reliability-cockpit/web/app/(workspace)/equipment/[id]/page.tsx` |
| `/fmea` | `reliability-cockpit/web/app/(workspace)/fmea/page.tsx` |
| `/maintenance/investigation` | `reliability-cockpit/web/app/(workspace)/maintenance/investigation/page.tsx` |
| `/maintenance` | `reliability-cockpit/web/app/(workspace)/maintenance/page.tsx` |
| `/overhauls` | `reliability-cockpit/web/app/(workspace)/overhauls/page.tsx` |
| `/` | `reliability-cockpit/web/app/(workspace)/page.tsx` |
| `/panduan/istilah` | `reliability-cockpit/web/app/(workspace)/panduan/istilah/page.tsx` |
| `/pdm` | `reliability-cockpit/web/app/(workspace)/pdm/page.tsx` |
| `/rcfa` | `reliability-cockpit/web/app/(workspace)/rcfa/page.tsx` |
| `/recommendations` | `reliability-cockpit/web/app/(workspace)/recommendations/page.tsx` |
| `/reports` | `reliability-cockpit/web/app/(workspace)/reports/page.tsx` |
| `/system-integration` | `reliability-cockpit/web/app/(workspace)/system-integration/page.tsx` |
| `/work-orders` | `reliability-cockpit/web/app/(workspace)/work-orders/page.tsx` |

## Forms and transitions inspected

| Surface | Existing content / transition | UX risk and preservation rule |
| --- | --- | --- |
| PdmMeasurementForm | Work origin/asset/method, native typed grid or capture editor; instrument/context, observations/hypotheses, manual notes/SR, metadata | Long form and repeated caveats; group without deleting fields or relaxing validation |
| PdmCaptureEditor / PdmWorkbookTemplate | Candidate profile and literal row/clock/context claims | Template/catalog is not operational qualification or a mass-upload capability |
| PdmCenter | Register/filter, input/history/detail state; record query; one item per page | “35 inspections” does not count source archive; preserve server filters/limits and dirty guard |
| PdmHistory / PdmSourceHistory | Native events/scatter versus source groups/proofs/aliases | History naming conflates sources; split labels and counters, keep authorization and byte paging |
| InspectionDetail / PdmInspectionWorkflow | Read/edit/submit/review/revise, exact Case handoff, old revision reader | Multiple back/close actions and generic Engineering link; maintain partial-failure state and review independence |
| CaseForm / CaseWorkspace | Structured investigation, evidence, independent review, immutable history | Move entry context, not lifecycle or access; Case remains optional for ordinary inspection |
| Recommendation / Advisory / Inbox | Record review, local follow-up, publication/ACK | Separate local record approval, recommendation, work authorization and actual source WO status |

Repeated boundary/help content appears in QaProductBoundary, PdmCenter fact row/filter help, form acquisition guidance, InspectionDetail, workflow review prose and history panels. Simplify placement only; blocked-action reasons and QA/estimate disclosures remain visible. The current provisional source-history pane has no canonical chart; absence of a chart is intentional, not a request to invent measurements.

## Exact historical capability and gate references

Read source-of-truth documents: nadi-pdm-center-input-01, input-first-contract-01, work-origin-01, manual-follow-up-01, history-staging-01, complete-history-01, complete-demo-activation-proposal, eng-validation-01, native-recommendations, KPI evidence catalog and asset-af-mapping-admin. Their earlier local-only/OPEN/UNEXECUTED labels are dated checkpoints. PR merge facts and current runtime observations above override only status claims, not semantic or permission boundaries.

The runtime-only source interpretation package retains one explicit nonpersisted numerical estimate with original raw blank and provenance. Main lacks that overlay. It must not be silently lost, expanded, relabelled as a measured value or consumed by KPI/Case while simplifying navigation. Runtime demo-account management is likewise not a new permission model for Sprint1.

See feature preservation matrix F01–F24 for exact capabilities, source and existing regression anchors. No backend/form implementation is included in this task. CI for the documentation PR is regression evidence for its exact source, not confirmation that the future UX proposal is implemented.
