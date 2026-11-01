# NADI-PDM-SPRINT-04-DELIVERY

1 November2026. S4-00 audited before coding. IMPLEMENTATION_IN_PROGRESS.
Base: PR116 exact `3778584a7d4f97b98aae44cea37838a34b61f5d0`, open/Draft and
stacked on PR115→114. Parent backend/frontend run41293638999 PASS. Main verified
`f1fc4e8b395691a17fe6d986bf14c772d37c1f2c`. Isolated branch
`codex/nadi-pdm-sprint-04`; no parent branch or live source is changed.

## S4-00 — prerequisites and architecture

Authority: [Sprint3 delivery](NADI-PDM-SPRINT-03-DELIVERY.md),
[Sprint4 prerequisite handoff](NADI-SPRINT4-PREREQUISITE-HANDOFF.md),
[KPI contract plan](NADI-RELIABILITY-KPI-CONTRACT-PLAN.md),
[source/application ADR007](adr/007-source-read-only-application-boundary.md).
Read root/scoped instructions, context, PRD, design/roadmap/status and source
ownership before implementation. Graph Tier2 generation2026-11-01T10:06:18Z,
coverage checks plus direct source reads; graph completeness is not claimed.

| Existing capability / meaning | Candidate treatment / remaining owner decision |
| --- | --- |
| Legacy KpiService in Cockpit store | Preserve exact source/formula/API; legacy counts every truthy failure_code within reported_at inclusive calendar days, NOT specifically CM. Null downtime contributes0 and operating proxy=max(calendar-hours−downtime,0). No method approval inferred |
| Mart maintenance_event | Exact registered identity, conservative event_type/raw status and activity clocks; source activity is not a functional failure or repair episode |
| PI latest selected signal | Original value/quality/clocks, not operating-hour exposure or a qualified historian interval |
| Failure definition/identity | MISSING; reliability engineer + maintenance owner sign functional failure, IDs, evidence and duplicate/child handling |
| Exposure/observation coverage | MISSING; operations + historian owner + reliability sign operating-hour source, quality, gaps, scope and window |
| Active repair versus outage | AVAILABLE_UNAPPROVED raw activity times; maintenance + reliability sign repair/restoration/wait/planned/censor/reopen rules |
| Version/window/exclusion policy | MISSING; reliability owner + contract reviewer sign effective version, half-open window, timezone/precision and attribution |
| Authenticated source access | Reuse existing exactasset GET/gateway; no grant or authentication changes |
| Live Reliability Performance input | No qualified canonical failure/exposure/repair endpoint exists. UI remains NOT_ELIGIBLE; source activity drilldown stays distinct |

No prerequisite prevents a technically correct *offline synthetic foundation*.
None authorizes operational evaluation. Candidate models/engine/tests live under
`contracts/sprint4`, unreachable from app routes/services. Existing active shared
contracts, stores, migrations, source acquisition and collectors remain unchanged.
Proposed contracts are not a second operational store or approved semantic policy.

Synthetic policy explicitly supports exact scope/version, aware precise clocks,
complete nonoverlapping exposure coverage, explicit functional identities, explicit
revision chains/replay/duplicate links, active/wait/planned repair intervals. Reject
unsupported overlaps, censor/reopen/cross-window episodes without clipping, now(),
source-changedate fallbacks or inferred owner approval. Operational status always
NOT_ELIGIBLE, even when a synthetic reference calculation qualifies.
