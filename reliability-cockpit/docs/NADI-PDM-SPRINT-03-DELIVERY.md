# NADI-PDM-SPRINT-03-DELIVERY

Development candidate, 1 November 2026. Status: IMPLEMENTATION_IN_PROGRESS.
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

Pending implementation, executable qualification, exact-head CI and independent
technical review. This checkpoint makes no technical-PASS claim.
