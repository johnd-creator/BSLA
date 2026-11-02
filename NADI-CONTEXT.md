# NADI — project context

Current source/runtime checkpoint: [2 November integration](docs/NADI-NIGHT-INTEGRATION-20261102.md). Earlier dated sections retain historical scope.

Updated: 2026-10-10 · NADI-DOC-FOUNDATION-01. Start here after [AGENTS.md](AGENTS.md).

**NADI — Reliability Data Platform** supports reliability engineering and asset
maintenance decisions at **PLTU Banten 1 Suralaya**. It is the reliability product
within the Power Plant Data Platform. Its vision is to bring factual data and
governed engineering evidence into one Reliability Engineering platform.

## Architecture and ownership

The Shared Data Foundation comprises Maximo Knowledge/Collector, PI
Knowledge/Collector, CEMS Collector and Reliability Data Contracts. Collectors
own guarded source acquisition and their existing stores. Reliability Mart is
inside the existing Maximo Collector database; the NADI FastAPI backend reads it
with SELECT-only authority. The Next.js frontend uses the Cockpit API proxy.
Legacy Cockpit ingestion is a separate path into the existing Cockpit store.

Engineering Cases, inspections, reviews, audit and recommendations belong to
NADI's application store, never to the Mart or source systems. Operational writer
provisioning remains gated; current persisted development workflows use the
existing isolated test fixture. NK is a separate consumer with no application DB.
See [platform ownership](plans/PLATFORM-VISION.md),
[ADR006](reliability-cockpit/docs/adr/006-engineering-workspace.md) and
[ADR007](reliability-cockpit/docs/adr/007-source-read-only-application-boundary.md).

## Development environment

Primary frontend: **https://localhost:3000**. One address serves factual screens
and development-only Engineering. Explicit, controlled branch previews may use
that same address; do not create permanent parallel NADI frontends.

Bundle A verified merged main `963e7a8bf0b2a7cf62b1ee8a5661c95d62df7108`,
including PR62/63/64. The development baseline was synchronized through the existing
launcher, then the integrated `codex/nadi-ux-bundle-a` candidate was explicitly
selected on the same HTTPS address. Source selection uses detached HEAD; the banner
accurately reports that state and the full serving SHA. Runtime evidence and rollback
are recorded in the [Bundle A review](reliability-cockpit/docs/nadi-ux-bundle-a.md).
The [audit and development runbook links](docs/NADI-DOC-FOUNDATION-01.md)
record the verified source, secure login boundary and startup authority.
Read the banner's full SHA, dirty state, backend availability and fixture identity
before reviewing changes. A documentation branch is not automatically visible there.

Bundle A is now MERGED via PR65 in verified main `160737b3bfaeac94f4e8093b8566ca0e5d3585c9`. Bundle B is MERGED via PR66 in main `cc90fc73bea6ae399383d8538035c6454dc7e65a`, provisionally development accepted by the PO; final visual review is 12 October 2026. [Bundle B evidence](reliability-cockpit/docs/nadi-ux-bundle-b.md) distinguishes implementation from operational readiness and PO approval.

## Modules and current scope

| Module | Verified scope / target |
|---|---|
| Executive Overview | Factual dashboard and Bundle A visual candidate implemented; PO acceptance pending |
| Asset Health | Factual register/detail and assessment records retained; six-section Bundle B detail implemented |
| PdM Center | Bundle B authenticated QA event/detail/history UI implemented; operational method/trend approval pending |
| Engineering Workspace | Merged case/review/audit foundation; persisted isolated QA visible; operational activation partial |
| Recommendations | Bundle B NADI-owned QA register/detail/history implemented; operational activation pending |
| Action Board | Bundle B authorized QA review/follow-up board implemented; operational acceptance pending |
| Reports | Product module planned; no claim of a complete reporting product |
| System Integration | Data Trust/technical navigation consolidated in Bundle A; PI/CEMS product projections remain planned |
| Administration | Private bounded account administration exists; product administration UI planned |

The [official roadmap](plans/NADI-ROADMAP.md) owns Phase 0–5 and the Product UI/UX
track. Factual Phase 0 is complete within its accepted boundary; Phase 1 remains
partial. Engineering foundations are merged, but merging and development tests do
not establish operational activation or engineer UAT. [Repository Status](plans/REPOSITORY-STATUS.md)
and [DEV-LOG](DEV-LOG.md) distinguish those milestones.

## Non-negotiable boundaries

- Maximo and PI source data remain READ-ONLY. NADI never creates, approves,
  updates or closes Maximo Work Orders; existing WO links are informational.
- Preserve stores, accepted evidence, audit/session history and `23496711.xls`.
  A documentation task never changes services, policies, credentials or data.
- No invented condition, score, threshold, risk classification or prediction.
  UNKNOWN, NOT ASSESSED and labeled DEMO have different meanings.
- Source quality, source/collection/projection time, human review and equipment
  condition are independent. Portable PdM is episodic; PD is not assumed DGA.
- Global login is a future requirement. Bundle C polishes the existing isolated QA sign-in presentation only;
  factual development access and existing HTTPS Engineering security remain intact.

## How work continues

Read [PRD](PRD.md), [Design System](DESIGN-SYSTEM.md),
[UI specification](docs/design/NADI-UI-SPEC.md), roadmap/status/log, then scoped
instructions and technical evidence. Use task branches, PRs, relevant tests and
exact-head CI. Verify runtime visibility separately. Record Product Owner decisions
with scope/evidence; proposals are not approvals. Append a development-log entry at
each material milestone. GitHub reviewed documents are the persistent knowledge
source; chat decisions become durable only when their provenance is recorded.

Bundle C login presentation and UX-09 preparation are recorded in the [readiness report](reliability-cockpit/docs/nadi-ux-bundle-c.md). Global enforcement and operational engineer acceptance remain separate.

## 21 October 2026 — complete PdM source-history candidate

NADI-PDM-HISTORY-COMPLETE-01 is implemented locally on PR110/main e84eaec0,
with isolated full-source qualification: 7 workbooks/200 sheets/173,147 populated
cells/25,278 navigable source groups. RAW/provisional content stays distinct from
canonical trends and human inspections. Migration 007 and full-history demo-target
activation/import are not applied. [Scope and evidence](reliability-cockpit/docs/nadi-pdm-complete-history-01.md).

## 2026-11-02 retained Maximo hierarchy candidate

[NADI-ASSET-HIERARCHY-01](reliability-cockpit/docs/NADI-ASSET-HIERARCHY-01.md) adds
SELECT-only, registered-root hierarchy context from retained Maximo edges. It does
not import Excel or expand Registry/Engineer grants. Coverage remains PARTIAL;
source role semantics remain UNKNOWN. Implementation/testing, merge, deployment
and Product Owner acceptance remain separate. Local activation is still stopped
at the official PR120 source-compatibility gate; Logbook PdM remains HOLD.

## NADI source integration 2026-11-02

PR114–120 and122 are MERGED with exact-head CI and independent review. The
[reconciled checkpoint](docs/NADI-NIGHT-INTEGRATION-20261102.md) distinguishes merged source, the authorized
bounded live Maximo hierarchy read, partial population/UNKNOWN roles and unchanged
PR119 runtime. Local activation is BLOCKED at the official controller source gate;
no grant or service transition occurred. Logbook PdM remains HOLD.


### Scoped source-ingestion follow-up — 2026-11-03 WIB

The approved registered CS01 gap-root subset was paged against Maximo, with capped
groups refined until that subset was exhausted. New technical child rows passed
fresh private backup/independent isolated restore and exact-packet normal-writer
rehearsal before append to the existing Maximo-owned Collector/Mart. Old master,
Registry, mapping, ledger and asset-cursor fingerprints remain unchanged; the run
is PARTIAL and does not advance global cursors. No Registry import, role inference,
WO backfill, source write or service change. Full population/role acceptance stays
PARTIAL/UNKNOWN and local PR120 activation stays BLOCKED. Evidence and cardinalities
remain private; see the [integrated source report](docs/NADI-NIGHT-INTEGRATION-20261102.md) for the bounded method.
