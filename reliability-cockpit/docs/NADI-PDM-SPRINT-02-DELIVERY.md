# NADI PdM Sprint 2 — delivery and release readiness

Task: **NADI-PDM-SPRINT-02** · 1 November 2026. This document is the integrated
engineer/PO handoff. Exact reviewed source and hosted results are the Draft PR's
immutable head and final acceptance comment; they are not inferred from main.

## Source and scope

Verified main: `f1fc4e8b395691a17fe6d986bf14c772d37c1f2c`. PR114 remains
OPEN/DRAFT/unmerged at `aa065af9cef01d8ee3358bcca8fc628ba311ca3a`.
Branch `codex/nadi-pdm-sprint-02` is stacked on that exact head, with PR base
`codex/nadi-pdm-simplification-sprint-01`. Neither PR114 nor PR107 is merged or
modified by this task. No framework, database, authentication, DTO, schema,
source-acquisition or policy migration is included.

Implementation/test completion, hosted CI, independent review, merge, runtime
visibility, engineer method sign-off and PO acceptance are separate decisions.
The last two remain **PENDING**. Sprint2 is **not activated**.

## One engineer journey

1. Open **PdM Center → Register Inspeksi**. Default ten inspections per page;
   choose five or one when useful. Search observation/record, choose exact
   authorized asset/method/status, and optionally the original inspection-time
   range. Count = authorized filtered inspections, not measurements/source groups.
2. **Input Pengukuran** keeps the accepted continuous editor: work origin and
   authorized asset → original measurements or provisional workbook capture →
   observations/manual analysis → reported SR/existing follow-up → save draft.
   A workbook label is never a canonical asset mapping.
3. Open the record and follow **Riwayat pengukuran aset / metode ini**. The link
   carries exact asset/method/origin record, opens history in the mounted screen,
   and supports Back/Forward. Native history offers exact point/quantity and
   measurement-time filters. Page size1/10/25 is independent of Register1/5/10.
4. Read original values/types/units/time/provenance and stored procedure/instrument/
   orientation/operation context. Return to the exact source inspection, or open
   an event's record and return to the same history page/filter context.
5. **Ajukan inspeksi**. An independent reviewer begins review and returns with
   rationale if needed; author revises/updates/resubmits; reviewer makes a new
   explicit decision. Review approves the record only.
6. A normal inspection ends after review with **zero automatic Cases**. An
   approved native record can deliberately open the existing Case workflow with
   a frozen exact reviewed revision. Provisional capture retains the denial
   explanation. Recommendations and reported SR/existing WO remain distinct;
   nothing writes to Maximo.

## S2-01 — exact bounded page contract

The owning API already accepts limit1–100 and offset0–10000. Its inspection
service filters authorized canonical assets and author/approved visibility before
counting, orders by stable inspection ID, and streams database rows in batches100.
Native measurement order remains inspection ID then measurement index, not time.
No new query fan-out, export, eager source-history request or frontend bulk fetch
is introduced. Existing full-population scan cost for text/time counts remains;
this is not a new indexed-search/performance claim.

The workspace opts into **default10, options1/5/10**; other consumers of
`useQaRecords` retain the old inspection default1 and non-inspection default25.
Every returned row is rendered. Full totals, ceil page count, actual per-page
count, exact offset and has_more are verified before rendering. Offset beyond
10000 is not requested; the UI asks the engineer to narrow filters.

**Unchanged transport budgets:** QA request1MiB, response2MiB, timeout15s. Inspection
LIST alone now checks actual FastAPI/jsonable_encoder + JSONResponse UTF-8 bytes:
per-item incremental guard (stops before retaining an oversized multi-record page),
then complete response envelope including nulls, booleans and original timestamps.
No adaptive partial pages, record truncation, DTO fields or storage/input limits.
Server cursors close on early rejection. Above2MiB gives a small typed413
`PDM_PAGE_BODY_LIMIT`, with no count/record content; the public size selector
remains available even while new-entry editing. Same-session draft cache survives
recovery; identity/role/scope revocation still clears private state.

Ten large records may not fit: choose five/one explicitly. A single persisted
record above2MiB already exceeds the existing proxy; this PR does **not** claim
all domain-maximum captures fit. That case requires separately reviewed summary
DTO/security work, not a raised guard. Measurement-history retains its existing
contract/default25; selectable10/1 provides explicit recovery from its unchanged
proxy byte guard. Do not silently reduce a page or prefetch subsequent pages.

## S2-02 — three populations and their authority

| Population | Time/filter identity | Count/page proof | Preserved boundary |
| --- | --- | --- | --- |
| Inspection Register | canonical asset/method/status/text; inspected_at interval | AUTHORIZED_POPULATION / INSPECTED_AT; fixed bounded offsets | author/approved visibility or reviewer scope |
| Native measurement events | exact asset/method/status/text + point/quantity; measured_at interval | AUTHORIZED_POPULATION / MEASURED_AT; fixed bounded offsets | native current revision only; original types/time/units |
| Provisional Excel source groups | existing workbook/sheet/kind/classification/clock filters | AUTHORIZED_PROVISIONAL_SOURCE; own counts/keysets/byte-bounded fields | separate source scope; immutable cells, aliases, profile/hash proof |

Native filters disappear while reading Excel; source filters retain their own
meaning. Source history loads only when deliberately selected, and stays mounted
while toggling types to preserve its current filters. A provisional detail link
opens the source area with origin-record return but does **not** invent a source
key, physical mapping or canonical point from a label. Deep-link context includes
native event limit/offset and exact point/quantity; unrelated query/hash survives
ordinary Register navigation. Existing source keyset/detail behavior is unchanged.

## S2-03 — honest graph eligibility

**REAL_MULTI_INSPECTION_TREND: NOT_ELIGIBLE.** The validation packet/catalog contain
no approved comparable physical series policy. Stored matching strings, record
APPROVED, the nine Tribology samples or Codex fixtures are not such approval.
No retained or provisional data is joined into a cross-inspection trend.

The original raw one-inspection/revision scatter remains: no interpolation,
smoothing, daily filling, threshold, health grade or canonical RAW promotion.
The new wrapper also rejects mixed asset identity and incomplete/date-only/
time-only/naive clocks. Zero is numeric; null/boolean/text never become zero.
Unknown clocks remain visible in the raw table. Plot scope explicitly says
"this page"; event paging can split an inspection and does not imply completeness.

A compact eligibility explanation exposes recorded/unknown/different metadata and
pending policy separately. Acquisition/bandwidth/mounting evidence is UNKNOWN;
recorded references do not verify physical comparability. The filterable raw table
is useful while this decision is pending.

`web/fixtures/PdmTrendDemonstrator.tsx` is a clearly **SYNTHETIC ONLY** visual sample
with seven irregular invented times/values and an accessible table. It is imported
only by the network-intercepted test entry, never an app page or retained QA/API.
The28 application page entries remain byte-identical. Its plot is not an activated
product capability or engineer approval.

Unlocking a real trend requires authorized G01/G02 and per-method scope/version,
exact physical point/quantity/unit, procedure/instrument/acquisition/operating
context, genuine timestamp precision/zone and explicit comparability decisions
V06/T05/MC05/TH06, with X01 cadence and X02 custody. No generic metadata bag,
source adapter, historian binding or invented policy is added here.

## S2-04 — compact M02 decision session

[The existing engineer packet](nadi-pdm-engineer-review-packet.md) now starts with
representative V/H/A evidence and one decision session. It retains all20 distinct
P1 rows (G01/G02,V01–V05,T01–T04,MC01–MC04,TH01–TH05) and six distinct P2 rows
(V06,T05,MC05,TH06,X01,X02), each with evidence owner, scope, method/version,
decision, date and unresolved question. All26 remain PENDING_ENGINEER_VALIDATION;
Q01–Q10 remain PENDING. The authoritative detailed validation matrix is linked,
not duplicated. Inspection review ≠ method validation ≠ health ≠ maintenance.

## S2-05 — reproducible qualification

Tests use generated records only, intercepted .invalid browser origins, TestClient
trusted-session dependency and a separately named disposable PostgreSQL test
store. No retained localhost records, accounts or sessions are mutated.

- RED→GREEN: original code returned a multi-MiB200 for an extreme requested page;
  new guard returns typed413. Both SQLite/PG test classes walk23 records at1/5/10,
  exact full-envelope boundary and+1 byte, Unicode, null/boolean, incremental stop,
  foreign-asset denial, other-author draft exclusion, approved visibility, token
  revocation before serialization, and large provisional capture exclusion from
  native history. Individual readable raw values and partial clocks round-trip.
- Actual UI→trusted API→disposable PG: native origin/analysis/reported SR create,
  committed503/lost-ACK retry with same intent and one record, readback/edit/CAS,
  immutable earlier revisions,390px reopen, explicit clear to legacy contract;
  author submit → independent begin/return → author revise/update/resubmit →
  fresh reviewer APPROVED → zero automatic Cases → deliberate optional Case
  with exact frozen reviewed revision. Original zero/mm/s/+07:00 time survives.
- Existing native/provisional/work-origin/follow-up/review/source-proof/estimate
  regressions are retained. Source/history tests cover403/401/503/loading/empty,
  denied session, partial clocks, deep links, unsaved guards, role/scope clearing,
  provisional Case denial and no source/canonical promotion. Hosted backend also
  runs disposable source-history proof/alias and restore suites.
- Matched actual React screenshots use identical23-inspection synthetic fixtures
  before(AA) and after(candidate):390/768/1440/1920, light/dark. Candidate matrix
  includes seven accepted screens plus fixture-only demonstrator; automated axe
  covers WCAG2A/AA/2.1A/AA within these tested states. Keyboard/drawer/disclosure,
  draft recovery and no-overflow checks remain. Automated checks do not substitute
  for human engineer/PO UAT. See [visual evidence](evidence/nadi-pdm-sprint-02/README.md).

## F01–F24 — exact preservation matrix

| ID | Final preservation evidence / change |
| --- | --- |
| F01 | Native≤100 typed rows; original zero/unit/time; real UI/API/PG lifecycle + pdm-input regressions |
| F02 | Native/capture exclusivity and literal clocks/units; capture suites + large provisional budget test |
| F03 | Work-origin union/conditional department exact; real form/create/edit/history/clear + origin contracts |
| F04 | Manual analysis/follow-up remains narrative; real edit/readback/clear immutable history |
| F05 | Reported-unverified SR exact original; real form/clear tests; no SR lookup/write |
| F06 | Explicit Sprint2 exception:1/5/10 fixed read pages and typed2MiB guard; auth/filter/order/offset/count unchanged |
| F07 | Same-inspection/revision rawPlot bytes unchanged; stricter time/asset wrapper +14 history contracts; no real trend |
| F08 | Source service/UI bytes unchanged; separate lazy source scope/keyset/byte pages and source tests |
| F09 | Source repository/migration007/profile/aliases unchanged; no workbook replay/import or reclassification |
| F10 | Existing review commands untouched; actual author↔reviewer return/revise/resubmit UI/API/PG |
| F11 | Optional deliberate approved native Case, frozen exact revision; existing stale-revision/partial-link retries |
| F12 | Provisional Case/plot exclusion unchanged; capture denial suites and explicit UI reason |
| F13 | Existing Case paths/forms/investigation/review/audit remain; only optional shared detail history callback added |
| F14 | Recommendation service/UI/WO semantics unchanged; existing recommendation workflow CI |
| F15 | Advisory/Inbox/ACK service/UI unchanged; existing advisory CI |
| F16 | Command hook/repository bytes unchanged; lost-ACK same receipt, CAS, immutable audit tests |
| F17 | Draft provider bytes unchanged; actual focus/checking/scope clearing + new dirty-entry413 recovery regression |
| F18 | Auth/RBAC/CSRF/Origin/session files unchanged; real trusted dependency + negative scope/revocation suites |
| F19 | Attachments metadata/custody unchanged; inspection detail retains provenance/custody disclosure |
| F20 | All28 app page bytes unchanged; Registry/six asset detail paths preserved |
| F21 | FMEA/maintenance/health/overhaul/RCFA utility paths and semantics untouched |
| F22 | Existing overview/reports/integration unchanged;403/401/503 regressions retained |
| F23 | Six pinned parity files preserved, source interpretation service unchanged; display-only low-confidence estimate/proof keyboard regression |
| F24 | Exact demo account/session/controller parity pins unchanged; no credential reset/login/grant/session mutation in this Sprint |

The scope guard now also checks untracked protected files. Only three exact-byte
Sprint2 read files are admitted (`human_records.py`,new`pdm_read_budget.py`,
`useQaRecords.ts`), alongside the six existing F23/F24 pins. Auth, repositories,
DTOs, contracts, migrations, collectors and development controller remain protected.
The localization guard pins the same reviewed hook; no broad allowlist removal.

## Runtime and later activation readiness

Read-only official controller status reports active frontend/backend **AA**, both
`aa065af9cef01d8ee3358bcca8fc628ba311ca3a`, stale=false. Installed controller
source remains `1ec93d6f3507321617903d169451d77fdcc1216e` with its accepted private
history/source-reading amendments. Only existing generated next-env.d.ts differs
in active source. Sprint2 does not switch/restart that source or any collector.

Official current-fixture and independent recovery read-only probes are equal for
existing records/schema/ledger; migration007 remains APPLIED. Owner-private account
file/controller/config/store identity fingerprints are retained privately. Existing
historical backup is private, present and digest-matched, but **expired for a new
transition** (>1hour); historical acceptance is not a fresh restore qualification.
No dump/raw records/session proof is committed or attached publicly.

Candidate fixture compatibility inputs (migrations/repositories/auth/identity/
bootstrap/dependency/source fixture) remain unchanged from AA; paired front/back
must both select the same final Sprint2 commit. Static source parity is distinct
from fresh source/session/owner/store/recovery gates. Installed controller is not
amended and a transition is not attempted. Actual new preflight, sealed recovery
receipt qualification and fresh≤1hour backup remain **NOT RUN for Sprint2**.
The official previous engineer session-proof has expired; no cookies were read,
proof fabricated, password reset or broader admin grants used.

**One owner action later:** explicitly authorize this reviewed final Sprint2 head
for one local paired evaluation and complete legitimate engineer login/official
private session-proof handoff when prompted. Then Codex must rerun source/controller/
accounts+session/store+ledger/service-owner gates, qualify independent recovery and
fresh private backup through the existing controller, and transition only if all
mandatory gates PASS. No future merge or production deployment is implied.
Current live AA and all retained records/grants/sessions/unrelated services remain.

## Proposed issue mapping and acceptance

| Proposed issue (not created remotely) | Delivered scope | Remaining human/release gate |
| --- | --- | --- |
| S2-01 | Bounded Register1/5/10 + exact byte/auth tests | PO daily workflow evaluation |
| S2-02 | Native exact context/filter/return; distinct Excel scope | authorized human history usability UAT |
| S2-03 | Eligibility/raw table + synthetic demonstrator only | explicit comparability policy before any real trend |
| S2-04 | Existing compact26-decision packet | actual engineer owner/scope/version/date answers |
| S2-05 | Disposable real UI/API/PG independent workflow | engineer/PO acceptance separately; no retained mutating UAT |
| S2-RELEASE | One stacked Draft PR, exact-head CI + independent review | later explicit paired-cutover authorization and fresh gates |

Phase0–5/M0–M8 history and official current/partial status remain intact. No M02
completion, equipment health, reliability KPI or Phase advancement is claimed.
