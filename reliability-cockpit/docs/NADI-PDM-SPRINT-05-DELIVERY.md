# NADI-PDM-SPRINT-05 — Integrated Stabilization & UAT Readiness

1 November2026. One isolated candidate, stacked above Draft PR117 exact
`988af8d4875758b300e7b563c0a205f143ee184c`. Source branch
`codex/nadi-pdm-sprint-05`; main verified
`f1fc4e8b395691a17fe6d986bf14c772d37c1f2c`. No parent worktree changed.
Final immutable HEAD, Draft PR URL, terminal backend/frontend CI and independent
review receipts are bound in the final Sprint5 PR qualification receipt; the report
cannot embed its own Git object ID. Technical PASS requires every listed gate.

## S5-00 baseline and dependency audit

Read root/scoped rules, product context/PRD/design, official roadmap/status/log,
Sprint1–4 reports/known issues, Sprint4 prerequisite/contract plan and Sprint5
handoff. Parent graph Tier2 generation2026-11-01T10:06:18Z; exact source fallback
for new/changed/excluded/partial files. New worktree is not claimed graph-indexed.
Current Git/CI/runtime evidence is independent of historical document headings.
The new owner task authorizes stabilization while human policy sign-off remains
pending; the prior handoff's scheduling proposal does not block synthetic tests.

| Dependency | Exact head at audit | State / readiness |
| --- | --- | --- |
| Sprint1 PR114 |aa065af9cef01d8ee3358bcca8fc628ba311ca3a |OPEN/DRAFT, parent main; source-qualified, no new acceptance inferred |
| Sprint2 PR115 |3a01e842b5bfca08a5d508b8988dc6deb32c2961 |OPEN/DRAFT, direct stack on114; actual local front/back pair |
| Sprint3 PR116 |3778584a7d4f97b98aae44cea37838a34b61f5d0 |OPEN/DRAFT on115; read-only evidence, PO/source decisions pending |
| Sprint4 PR117 |988af8d4875758b300e7b563c0a205f143ee184c |OPEN/DRAFT on116; backend/frontend run41299381050 PASS, independent bounded review PASS |
| Sprint5 current candidate |Final receipt on its one stacked Draft PR |Automated qualification only; HUMAN_UAT_PENDING, no activation |

Git merge-base checks prove114→115→116→117 ancestry. Parent heads/bases and main
are rechecked at delivery; no merge, reset, force-push, rebase or deletion. Existing
unmerged branches/worktrees remain; new tests never contact retained business data.
Official read-only controller status before/after verifies actual localhost
Sprint2 front/back3a01e842, stale=false. No authenticated handoff is needed for
isolated tests; no login, password reset, credential/cookie/proof extraction.

## S5-01 integrated workflow and confirmed fixes

The new actual-component harness traverses Asset Register→exact Asset Detail→
Maximo register/source detail→PdM Register1/5/10→editor→inspection detail→contextual
history→sample inspection→PI evidence→exact original history/record context, then
existing Case/Recommendation services and Laporan→Reliability readiness→source.
All network is intercepted at `sprint5.synthetic.invalid`, GET only. It does not
mock a successful business save and count it as persistence qualification.
Existing real HTTP/disposable PG/browser suites independently cover save, dirty
draft recovery, concurrency/lostACK, author/reviewer, frozen revisions and Case.

Two confirmed P2 defects fixed in one existing helper `web/lib/asset-evidence.ts`:

1. Corrupt Maximo rendered fields previously passed identity/page checks and could
   crash StatusBadge/React. Validate every displayed string/null, finite numeric
   hour/null and structural source datetime before accepting the whole page.
   Preserve0/null/raw status and naive source-clock text; no invented zone, enum,
   threshold, failure definition, normalization or silent partial page.
2. An inspection opened from history lost its history mode/origin/point/quantity/
   page after an Asset evidence detour. Add only the seven existing contextual
   keys to the same-origin closed allowlist. Exact return context is tested;
   arbitrary returnTo/secret keys remain excluded. No new route or permission.

A single exact helper SHA exception is enforced by `check:sprint5`; all runtime
backend/component/page/API/auth/store/collector/contract/controller bytes remain
identical to parent988. Test-only localization entry now includes existing Reports
so the same intercepted browser can cross prior sprint boundaries.

## S5-02 regression and the disclosed React skip

The earlier hosted backend skip was dependency ordering: the test decorator is
evaluated when imported, before npm installation. Node22/npm ci now precede the
main backend suite. A separate mandatory named-test runner requires exactly1 test,
zero skips and no failures/errors/unexpected successes; otherwise it fails CI.
The test actually projects synthetic API evidence into real ConditionEvidence/
DataTrust React render and checks unknown/null not fabricated0. Local execution
PASS, executed1/skipped0. Final hosted receipt must confirm it, not count a skip.
No existing skip/assertion/coverage requirement was removed or weakened.
The inherited Sprint3/4 CI uploads are also narrowed to non-image JSON receipts;
all image generation/browser assertions remain intact. Independent review caught
this privacy boundary and a new-harness request-ordering race; both are repaired
with non-image artifact paths and an explicit intercepted-request callback signal.

Existing backend/frontend suites, disposable PG migration/recovery/bridge tests,
auth/RBAC/CSRF/session/revocation/CAS/Case/recommendation/Advisory/audit, Maximo
canonical replay and unchanged active/shared contracts remain in exact-head CI.
Unconfigured PostgreSQL tests skip explicitly locally; hosted CI uses named
throwaway databases. No retained schema or account is used for mutation tests.

## S5-03 measured performance and stability

New synthetic tests seed2501 inspections in SQLite memory,500 outside author
scope;2001 authorized inspections/10005 measurement events. Register1/5/10 and
history return fixed pages with one application SELECT per read, stable IDs and
original typed values. The JSON reader still scans filtered documents with
`yield_per=100` to count/search; it is NOT a SQL-LIMIT/indexed-search optimization.
Reported query count concerns that repository call, not an entire HTTP request.
No per-row application-query fanout or full-population browser fetch is introduced.

Maximo fixture10025 source events/10000 selected:20 pages×25rows,40SELECTs
(one COUNT + one LIMIT per page),500 distinct returned identities, source-read-only.
Python tracemalloc peak, durations and serialized page bytes are measured in
`/tmp/nadi-sprint05/performance.json` and the non-image CI receipt. Gross60s test
budget is not an operational SLA; Python allocation peak is not full-process RSS.
Browser fixture1013 inspections/10025 maintenance rows verifies at most one bounded
Register request per1/5/10 choice and no new request for source-detail disclosure.
PI contract already caps selected latest signals at5; excess/duplicate/ambiguous/
foreign/unapproved responses reject. No unbounded PI registry query is benchmarked.


Measured local checkpoint (synthetic SQLite/Python tracemalloc,1 November2026;
setup excluded; results vary by environment):

| Read | Seconds | Python allocation peak bytes | SELECTs | Serialized page bytes |
| --- | --- | --- | --- | --- |
| register_1 | 0.4775 | 316683 | 1 | 2155 |
| register_5 | 0.5306 | 319120 | 1 | 10199 |
| register_10 | 0.5291 | 373757 | 1 | 20255 |
| history | 0.5870 | 390504 | 1 | 18357 |
| maintenance | 0.1231 | 441467 | 40 | not measured |

Local configured backend:852 tests run,632 executed PASS and220 explicit optional
environment skips;48 dedicated population/foundation/legacy tests PASS, mandatory
React1 executed/skipped0. All configured frontend contract/lint/type/build gates
PASS; retained EngineeringWorkspace missing-useEffect-dependency warning is
unchanged. Final exact-head hosted CI results, not these local optional skips,
govern technical delivery.

Real PostgreSQL execution plans, production population/latency and operational
memory capacity are NOT_QUALIFIED. A separate authorized read-only plan audit of
actual indexes/populations, exact scope/DSN and query limits is required; this
sprint does not run EXPLAIN or acquisition against retained/source systems.

## S5-04 security/accessibility evidence

Corrupt/empty/403/503 Maximo, invalid/unapproved/ambiguous/empty PI and original
zero/null/false/source quality retain truthful states with no raw private errors.
Late A success,403 and503 after choosing denied asset B cannot replace B's scope
or reintroduce A's identity. Runtime auth/grants/API policy is unchanged. Existing
expiry/forced logout/role/scope revocation/independent review suites remain required.
390/768/1440 light/dark, actual theme controls, keyboard source focus/return,
no document overflow and full WCAG2A/AA/2.1A/AA scans run on tested states. Existing
broader UI matrices remain; no human assistive-technology certification is claimed.

## F01–F24 combined preservation baseline

The historical feature descriptions below retain their Sprint4 evidence. Sprint5
repeats their existing suite groups on exact final HEAD, enforces all protected
bytes and adds integrated navigation/negative/population tests. Source-only
preservation does not establish live UAT acceptance.

| ID | Preserved feature and evidence |
| --- | --- |
| F01 | Native typed measurements/original values and units; unchanged services/contracts + input suites |
| F02 | Native/provisional exclusivity/raw capture preserved; capture/workbook suites |
| F03 | Work-origin conditional department preserved; no PR107/Maximo recovery/acquisition change |
| F04 | Human analysis/follow-up narrative preserved; no source-fact interpretation conversion |
| F05 | Reported-unverified SR references preserved; no source request/write |
| F06 | Sprint2 Register1/5/10/2MiB hook unchanged; existing browser/backend suites |
| F07 | Same-inspection sample wrapper/plot unchanged; cross-inspection trend NOT_ELIGIBLE/M02 pending |
| F08 | Lazy provisional source/keyset/byte history unchanged; source-history tests retained |
| F09 | Migration007, source profiles/aliases and originals untouched; no replay/import |
| F10 | Author/reviewer workflow commands and independent review preserved; existing HTTP/PG/browser tests |
| F11 | Deliberate approved-native Case/frozen revision unchanged; no automatic Case |
| F12 | Provisional Case/plot exclusion unchanged; no RAW promotion or guessed mapping |
| F13 | Cases/investigation/review/audit accessible contextually; source/services/paths preserved |
| F14 | Recommendation/reported existingWO service unchanged; no Maximo create/update |
| F15 | Advisory/Inbox/ACK unchanged and available; existing regression gates |
| F16 | Intent receipts/CAS/audit/command hooks unchanged; HTTP integrity regression |
| F17 | Draft recovery and synchronous session/scope clearing unchanged; browser regressions |
| F18 | RBAC/CSRF/Origin/session/gateway/policy/middleware byte-identical to3a;403 is access, not outage |
| F19 | Attachment metadata/custody unchanged; detail source link grants no upload/download authority |
| F20 | All28 page entries and six Asset tabs byte-identical to parent377; no new route/frontend |
| F21 | FMEA/maintenance/health/overhaul/RCFA utility routes retained; exactasset maintenance improved only |
| F22 | Existing Beranda/DataTrust/report definitions/readers preserved; contextual Laporan readiness added, no KPI publication/portfolio bypass |
| F23 | Source interpretation/estimates/proofs and six existing parity pins unchanged |
| F24 | Accounts/sessions/auth/controller/deploy bytes unchanged; no reset/login/grant/session write in Sprint4 |

New owning-suite crosscheck: F01–09 PdmInput/PdmCapture/workbook/source/history/
Sprint2/Register suites and simplification browser; F10–17 InspectionWorkflow,
EngineeringIntegrity, RecommendationWorkflow, Advisory, HTTP/draft/auth browser;
F18–19 identity/auth/session/access/attachments/CSRF/gateway suites; F20–22 exact
route/navigation/component fence plus existing experience/reports/integration and
new integrated browser; F23–24 source interpretation/demo-account disposable tests
and exact protected source pins. No Collector/Maximo recovery ownership change.

## S5-05 private consolidated UX package

[Private package and per-screen purposes/limits](NADI-SPRINT5-PRIVATE-REVIEW-PACKAGE.md)
and generated owner-private gallery `/tmp/nadi-sprint05/browser/index.html`.
Public repository: no new screenshot bytes committed or uploaded. Each actual
image has exact candidate version, path, purpose, viewport/theme and SYNTHETIC
classification in results/index/hash manifest. Existing screenshots are historical.
Non-blocking visual preferences wait for consolidated PO review; automated scans
and synthetic images never record PO acceptance or factual plant evidence.

## S5-06/07 handoff, unresolved decisions and recommendations

[Consolidated engineer/PO UAT and future activation gates](NADI-SPRINT5-UAT-CHECKLIST.md).
All Sprint4 functional-failure identity, source mapping, exposure/quality/coverage,
repair/restoration/wait/planned, duplicate/supersession/reopen/overlap/censor/window/
timezone/version decisions remain PENDING with the same accountable role owners
in [Sprint4 decision register](NADI-PDM-SPRINT-04-DELIVERY.md). M02 comparability
and approved historian history remain pending. No new KPI source-contract adoption,
real eligible dataset, mapping, failure/health inference or numerical publication.

Merge recommendation: technically review this stacked candidate only after exact
CI/review PASS; dependencies must be reconciled in order under separate owner
merge authorization. Keep Draft while human decisions/acceptance remain pending.
Activation recommendation: NO activation in Sprint5. Future explicit owner
exact-SHA authorization, legitimate login/official private proof, source/controller/
service ownership, ledger, fresh backup, independent restore, recovery/compatibility
and rollback receipts are mandatory; any failed gate preserves Sprint2.
QA/production authorization remains absent. Technical PASS is neither merge nor
activation permission. No following sprint is started.

Final target only after gates: SPRINT5_TECHNICAL_PASS_HUMAN_UAT_PENDING.
Operational KPI NOT_ELIGIBLE; PO and engineer acceptance PENDING. Exact final
receipts, test counts/skips, measured results, remaining findings and actual
unchanged serving pair are recorded on the single Draft PR before this status.
