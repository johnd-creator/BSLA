# NADI-PDM-SPRINT-03-DELIVERY

Development candidate, 1 November 2026. Status: IMPLEMENTED_AND_LOCALLY_QUALIFIED; final publication gates below.
PO UI/UX acceptance, engineer policy decisions and activation remain pending.

## S3-00 — immutable baseline and capability audit

Base: `3a01e842b5bfca08a5d508b8988dc6deb32c2961`, PR115, stacked on open
Draft PR114 `aa065af9cef01d8ee3358bcca8fc628ba311ca3a`. At audit, main was
`f1fc4e8b395691a17fe6d986bf14c772d37c1f2c`; neither dependency was merged.
PR115 exact-head backend/frontend CI run41282072282 passed. Sprint3 uses a
separate managed worktree and branch `codex/nadi-pdm-sprint-03`.

The Sprint2 delivery's pre-activation checkpoint is historical. The later
[owner-authorized local activation receipt](https://github.com/johnd-creator/reliability-knowledge-starter/pull/115#issuecomment-6555450276)
records Sprint2 serving3a at https://localhost:3000. This task neither selects
Sprint3 there nor resets accounts. Retained operational data is not a test fixture.

| Capability | Existing authority / implementation | Sprint3 disposition |
| --- | --- | --- |
| Exact registered Asset | Registry in existing Maximo-owned Mart; SELECT-only API | Reuse; never infer identity from names |
| Maintenance | Existing maintenance-events API; exactasset/status/type/WO/date filters, max200; canonical PK upsert | Reuse bounded25-row UI; no new endpoint/store |
| WO identity | Maximo MXWODETAIL/site/org/WO canonical identity; same-ID INSERT/UPDATE | Prove idempotent status updates; flag distinct IDs sharing WO, do not discard |
| Maintenance clocks | actual_start/finish and source_changed_at exposed | Label separately; collection/projection timestamps NOT_EXPOSED |
| Source dates/filter | COALESCE(actual_start,source_changed_at) date filter/sort | Disclose fallback; never call it failure time |
| Approved PI latest | Existing condition-evidence contract; max5 approved signals; typed values/4 quality flags/lineage | Reuse exactasset allowed endpoint; expose original clocks/source detail |
| PI history | No governed NADI history contract | NOT_QUALIFIED; no history request/acquisition/resampling |
| Real PI pilot | Coal Feeder A / Coal Flow A only; Phase1 acceptance records one verified mapping/approvedsignal | No implied approval of any other asset; no hardcoded real measurement |
| Crosswalk | Existing canonical governance and condition DTO PI refs | Read-only evidence inventory; missing/conflict explicit |
| Full mapping candidates | pi-mapping route excluded by existing frontend gateway; method/date absent from condition DTO | BLOCKED_BY_CURRENT_CONTRACT; offline decision register, no permission expansion |
| Condition verification | Signal approval provenance differs from mapping approval | Never substitute selection approval for mapping evidence |
| Data Trust/context | Existing portfolio aggregate capability restrictions | Preserve403; no aggregate leakage through asset grants |
| DCS Historian | No independently approved NADI integration established | DISCOVERY_ONLY |
| Reliability KPI | Raw WO times/types available; failure/exposure/repair semantics unapproved/missing | Contract-first NOT_ELIGIBLE; no MTBF/MTTR calculation |
| F01–F24 | Sprint1/2 existing product/services | Preserve; contextual evidence links only |

Evidence: [query API](reliability-mart-query-api.md),
[source/application ownership ADR007](adr/007-source-read-only-application-boundary.md),
[platform ownership](../../plans/PLATFORM-VISION.md),
[authoritative pilot acceptance](../../plans/NADI-PHASE-1-ACCEPTANCE.md),
[Sprint2 delivery](NADI-PDM-SPRINT-02-DELIVERY.md),
[product blueprint](NADI-PDM-PRODUCT-BLUEPRINT.md).
The old zero-mapping runtime report is historical, not current pilot authority.

Graph Tier2 audit used the new worktree generation2026-11-01T08:54:57Z. Coverage
checks were followed by direct reads for excluded app pages/docs/scripts and
partial TSX ranges. Graph metadata is not Git/runtime acceptance evidence.

Canonical upserts establish one row per canonical source identity. They do not
establish a new latest-source-timestamp-wins policy. Same-WO conflicts are detected
only within the returned page and cannot certify population-wide uniqueness.

## Scope boundaries

No source-system requests, collector/polling changes, Maximo writes, account/grant/
session changes, mapping persistence/approval, retained migrations, new database,
or service restart. PR107/F-03 remains separately owned. Five navigation entries,
all existing detail tabs and contextual Engineering services remain available.
Synthetic tests/gallery are isolated and visibly labelled; no fixture enters a
retained store. Sprint4 implementation is not authorized by this handoff.

## Qualification and final evidence

S3-00 checkpoint was recorded before coding. See integrated delivery below for
implementation/qualification and the final PR receipt for immutable publication gates.

## Integrated delivery — S3-01–S3-06

Single [Draft PR116](https://github.com/johnd-creator/reliability-knowledge-starter/pull/116),
base branch `codex/nadi-pdm-sprint-02`; no dependency merged/rebased/force-pushed.
Original code and screenshot candidate:
`0e31fd2b0a2b5e0b6f7d103474710ca7bc9775ee`.
The final publication HEAD (including this report), hosted run IDs and independent
review carry-forward are recorded in the **immutable final qualification receipt
on PR116**, using `git rev-parse HEAD` and GitHub's exact head SHA. This avoids
claiming a document can embed its own Git object ID. Only that receipt can mark
`SPRINT3_TECHNICAL_PASS_PO_REVIEW_PENDING`; until all gates pass, status is pending.

| Requirement | Implemented / automated evidence | Remaining boundary |
| --- | --- | --- |
| S3-01 | Existing exactasset maintenance endpoint;25-row filter/page proof; canonical source detail; source/site/org/contract refs; separate actual/source-change clocks; page-local sameWO conflicts; encoded filter/inspection return | Public DTO has canonical WO reference, not a separate raw wonum/worktype/provenance export. event_type is the conservative existing work-type enum; other raw types may be null. Sync/projection freshness NOT_EXPOSED. No arbitrary latest-source-order policy added |
| S3-02 | Existing approved selected latest PI values with strict original types, quality4flags, source/collection/projection/UI clocks, complete permitted lineage and signal-approval detail; stale/bad/unknown remain visible | Histori NOT_QUALIFIED, no acquisition/resampling/trends. UI clock is observation only. Pilot approval does not extend scope |
| S3-03 | Read-only exactasset crosswalk disclosure from allowed condition DTO; offline bounded decision schema/tool, actual repository checkpoint register and synthetic ambiguity/forbidden fixtures | Full candidate enumeration and mapping-verification method/date unavailable under existing gateway. No new mapping or permission; DCS DISCOVERY_ONLY |
| S3-04 | Existing Asset Register/detail tabs and PdM inspection links; filter/page/source context through URL/history; same-origin allowlisted return; keyboard focus restored; readable responsive source disclosures | Existing operational PdM/application binding limitations remain explicit; no new dashboard/frontend. PO consolidated review pending |
| S3-05 | All17 prerequisite entries mandatory; additive offline schema/example/evaluator, unknown/blocked evidence and distinct overlap/reopen/duplicate/status policies; extra metric fields rejected | Always NOT_ELIGIBLE; no KPI calculation. [Sprint4 handoff](NADI-SPRINT4-PREREQUISITE-HANDOFF.md); no automatic Sprint4 start |
| S3-06 | SQL/select-only bounds,10k fixture/query regression, canonical replay, negative scope/type/lineage/paging, actual-component browser matrix, immutable preservation fences, full existing exact-head CI wiring | Hosted final-head evidence recorded on PR; human visual, engineer method and activation remain independent |

No new endpoint, collector, store, schema migration or source request. The existing
Next.js + FastAPI architecture remains. Raw Maximo worktype values outside the
contract enum stay quarantined; no empty event_type is assumed PM/CM. Corrective
work, source failure codes, WO status or recorded downtime never become an
engineer-approved functional failure or repair duration.

### Engineer navigation

1. Open **Aset**, apply its existing bounded filters/page search, select exact
   registered asset. Back restores filter/page/search context.
2. **Ringkasan → Bukti Kondisi** shows latest selected PI evidence only. Open a
   signal's source disclosure for exact AF/attribute/approval lineage. Crosswalk
   disclosure distinguishes verified server status from missing decision detail.
3. **Pemeliharaan** opens existing Mart maintenance records. Apply exact WO ref,
   source status, conservative event/worktype and explicit ISO-8601+zone bounds.
   Date filter/sort remains actual_start with source_changed_at fallback.
4. Open an exact canonical source record; prior filter/page stays in URL. Closing
   detail restores keyboard focus to that row; browser Back restores prior context.
   An off-page/removed selected ID is explicit, never replaced by a different WO.
5. From an authorized PdM inspection choose **Evidence aset · Maximo / PI**.
   Return restores the same record and prior PdM filter/page context. The actual
   endpoint still checks permission; a link grants no extra authority. A provisional
   workbook label never creates an Asset mapping or condition measurement.

Source facts stay separate from human inspection analysis/review/Case/recommendation.
No Case, SR or WO is created by opening evidence. Existing Engineering services
remain contextual and accessible; source systems remain read-only.

### Qualification and independent review

Local checks on the code candidate and final reviewed repairs:

- Existing hosted-backend acceptance command: **804 tests PASS**, **220 skipped**
  locally because their optional disposable PostgreSQL/external test environments
  were absent. No operational DSN was supplied. Hosted backend provisions its own
  isolated PostgreSQL and runs its complete configured suite; its exact-head
  outcome is mandatory and recorded in the final PR receipt.
- Reliability contracts: **18 PASS**. NADI source-evidence qualification4 PASS
  uses10025 synthetic SQLite rows. Real collector-owned canonical status replay1
  PASS uses in-memory SQLite and no collection entry point. Replay identity is
  assured, not universal monotonic timestamp ordering.
- All18 frontend regression/lint gates PASS, TypeScript PASS and Next build PASS.
  Existing build warning in EngineeringWorkspace's effect dependency is retained;
  no new lint error. API client emitted JS is byte-identical to parent3a after
  removing comments/types: only existing PI DTO type declarations were added.
- Actual React/browser: **6 scenario groups PASS**, **12 supplied screenshots**,
  **7 automated WCAG2A/AA/2.1A/AA states with0 violations**. Tested390/768/1440,
  light/dark, keyboard source detail/return, exact links/filters/browser Back,
  malformed/foreign PI/Maximo, missing/ambiguous/unknown mapping, verified-no-signal,
  empty/error403/503. Every request intercepted at `.invalid`; GET-only, no PI
  mapping/history/source/collector requests. [Gallery and receipt](evidence/nadi-pdm-sprint-03/README.md).
- Independent reviewer inspected immutable code0e31fd2 and directly read stale/
  excluded/new graph paths: **no remaining actionable code/security/data-contract
  blocker**. Review repairs covered exact return key/context, strict full PI lineage
  and attribute label validation, fractional digital codes, page proof, access error
  variants/focus, qualified AF-target collisions and malformed approval evidence.
  This is bounded independent technical review, not a claimed exhaustive security scan.

The auxiliary Maximo workflow refused the stacked base with
`UNSUPPORTED_PR_BASE`. Its main-only guard remains unchanged. Proposed offline
readiness contracts and the synthetic cross-component replay qualification now
live in NADI's own qualification package, where they belong: these do not change
any active shared contract or collector behavior. Final diff changes neither
collector paths nor `reliability-data-contracts`. The exact-head NADI backend runs
both unchanged shared-contract regressions and the proposed offline contracts,
plus replay against the unchanged Maximo source. Final-head NADI backend/frontend
qualification is authoritative for this NADI-only bundle.
No main-only guard, branch protection or ancestry was weakened to manufacture PASS.

### Query/performance findings

Synthetic SQLite holds10000 records for AssetA and25 for AssetB. Forty25-row
pages are SELECT-only, stable/disjoint, correctly scoped and bounded; terminal
page, type/status/WO filters and COALESCE date behavior tested. Entire new4-test
suite took under1s locally; the broad15s synthetic guard is a gross regression
budget, **not** an approved operational SLA or claim about source databases.
Browser fixture retains2000 rows on the intercepted server but renders25 at once;
no full-population client fetch or off-page conflict fanout. Existing gateway200-row
hard query limit,2MiB response cap, timeout, registry and final-session checks stay
unchanged. Existing API can count a large population; real Mart query plans/index
capacity require separately authorized operational performance evidence.

Crosswalk tool accepts at most10000 offline relationship rows and preserves all.
Repeated canonical relationships and a fully qualified AF target reused across
relationships are flagged UNRESOLVED for owner review. This is a conservative
review condition, **not** a new universal inverse one-to-one mapping policy.
Candidate rows never become VERIFIED and FORBIDDEN stays excluded. Missing AF/
source scope or aware dated evidence cannot qualify a conclusion. No persistence.

### Exact F01–F24 preservation matrix

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
| F20 | All28 routes retained; only two exact pinned Asset presentation pages change; all six tabs retained |
| F21 | FMEA/maintenance/health/overhaul/RCFA utility routes retained; exactasset maintenance improved only |
| F22 | Beranda/Laporan/DataTrust unchanged; portfolio403 boundaries preserved; no aggregate bypass |
| F23 | Source interpretation/estimates/proofs and six existing parity pins unchanged |
| F24 | Accounts/sessions/auth/controller/deploy bytes unchanged; no reset/login/grant/session write in Sprint3 |

`asset-evidence-preservation.mjs` compares operational backend/migrations/deploy/
collectors/source/auth/navigation against exact parent3a and compares emitted API
client JS. Existing simplification scope guard retains all F23/F24 and Sprint2
pins and admits only additive exact-byte proposed NADI offline contracts plus two exact reviewed
Asset pages. New synthetic test tooling is not an operational collector change.

### Runtime preservation and future gates

Official read-only `local-status` before/after reports the same frontend/backend:
`3a01e842b5bfca08a5d508b8988dc6deb32c2961`, stale=false, controller
`1ec93d6f3507321617903d169451d77fdcc1216e`. Controller manifest/amendment,
retained database identity and Engineering data readiness are equal. No session
proof, password or credential was retrieved or used; no actual account/grant/data
mutation, source call, service restart, parallel permanent frontend or production
operation was performed. Active Sprint2 is still https://localhost:3000. Existing
AA rollback checkpoint remains owned by the prior official activation procedure.

Source/account/store preservation is supported by unchanged operational bytes,
read-only controller identity/readiness and isolated tests; this task does not claim
a new operational DB backup/restore, production query plan or authenticated live
Sprint3 UAT. Existing autonomous collector cycles may naturally continue; no new
acquisition owner/schedule/contract is introduced.

Before future activation: explicit owner authorization for the final exactSHA,
dependency/CI/review revalidation, official authenticated session proof, account/
session preservation, service ownership, fresh backup/ledger/recovery and rollback
receipts, then the separately governed paired transition and authenticated live
UAT. None of those pending actions is implied by technical PASS. Human decisions:
full crosswalk/source-owner approvals, governed historian contract/DCS discovery,
KPI failure/exposure/repair policies, M02 comparability and consolidated PO visual
review remain pending. No automatic merge, activation, Sprint4 or production claim.
