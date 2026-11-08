# AGENTS.md — Reliability Cockpit

## Solo developer workflow

Follow root `../AGENTS.md`. Work directly in the active checkout: inspect existing
changes → edit a small scoped change → run relevant checks → inspect the result.
Preserve unrelated work. No routine extra worktree, subagent, mandatory branch,
handoff or layered approval process. Documentation-only work needs factual/link
checks and `git diff --check`, not source calls or restarts. Report checks actually
run and limitations. Do not commit/push/deploy or change runtime/data ownership
without a covering request. The active product UI is `../NADI/` (Laravel); this
component keeps its existing responsibility and safety boundary.

## Existing NADI stack and data ownership

Read root `../AGENTS.md` first. Active NADI UI is Laravel in `../NADI/`.
This component keeps Python FastAPI / SQLAlchemy and the retained Next.js 15 /
React 19 / TypeScript UI; new product work does not automatically belong in web/.
The current deployment is root Compose project `reliability-cockpit-platform`;
web default 3000, API 8000 with `compose.dev.yaml`.

**Do not create a new NADI database or a separate Reliability Mart database.**
Reuse the existing stores with these distinct paths:

| Path | Configuration / owner | Purpose |
|---|---|---|
| Legacy sync/KPIs | `DATABASE_URL` → `cockpit-db` / `cockpit` | `cockpit-worker` consumes Maximo Collector API; legacy equipment/work orders/KPIs |
| Canonical NADI | `RELIABILITY_MART_DATABASE_URL` → `maximo-db` / `maximo_collector` | `/v1/reliability/*` reads the existing Mart; no legacy-store fallback |

The Mart DSN is a separate connection setting, **not a request for another
database**. Public Mart query transactions stay read-only; governed mapping
administration has its own documented internal workflow and existing Mart
tables. Do not add public write endpoints or auto-verify mappings.

Governed Asset routes require `reliability_asset_registry` membership. The
separate inventory routes serve scoped non-Registry Asset and exact-Asset WO
history without enrollment. Technical Equipment / `asset_master` counts alone
do not prove either route's coverage or freshness.
Investigate DSN, scope, Registry, canonical tables and projection state before
starting collection. `mart-projector` refreshes local Equipment/Work Order
projections in the Maximo DB; `cockpit run` does not populate that Mart.
Do not fuzzy-match identities, fabricate unresolved RCFA links or invent health
scores. Preserve the semantics in `docs/reliability-mart-query-api.md` and the
domain-specific `docs/nadi-*-semantics.md` files.

The retained Next.js browser uses `/api/cockpit/*`, proxied to `COCKPIT_API_BASE`.
Laravel uses `RELIABILITY_MART_API_BASE` directly server-side for bounded GET DTOs.
Cockpit's PI/CEMS API bases are configurable but their projections are pending.
Never put production Maximo/PI credentials in Cockpit; source collection belongs
to the collectors. Do not switch to `compose.external.yaml`, use old localhost
DB defaults, or run another worker as a routine fix for empty pages.

## Current reliability gates

WO-only MTBF/MTTR/availability remain null with NOT_READY and concrete blockers;
old persisted numeric snapshots are also masked at the read boundary. Do not
restore WO/failure-code counts as event counts, calendar hours as exposure,
boolean downtime as hours, labor effort or CLOSE elapsed execution as MTTR.
Pure formula helpers are not evidence that inputs are valid. Follow
`../plans/MTBF-MTTR.md` and `docs/kpi.md`; preserve existing PM behavior separately.

Repeat-WO investigation is a review candidate population (governed scope, current
eligibility and explicit unknown/exclusions), not validated repeat failure.
Public query transactions remain read-only and vendor evidence must not leak.
Read `../deploy/compose/runtime-durability.md` before authorized runtime operations;
current app images are pinned and generic Compose recreation can select backups.

## Mission

Build reliability applications by consuming verified organizational knowledge rather than rediscovering production systems.

## Source of Truth

Before introducing a Maximo field, PI tag, endpoint, WebId, or parameter:

1. Search the relevant knowledge repository.
2. Prefer entries with `status: verified`.
3. If knowledge is missing, create a discovery task in the appropriate source-knowledge repository.
4. Do not guess production identifiers.

## Architecture Rule

Application domain models must prefer `reliability-data-contracts`.

Vendor-specific fields belong in source adapters.

## Safety

Production source systems remain read-only unless a separate explicit authorization exists.
