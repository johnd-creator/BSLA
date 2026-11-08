# AGENTS.md — Maximo Collector

## Solo developer workflow

Follow root `../AGENTS.md`. Work directly in the active checkout: inspect existing
changes → edit a small scoped change → run relevant checks → inspect the result.
Preserve unrelated work. No routine extra worktree, subagent, mandatory branch,
handoff or layered approval process. Documentation-only work needs factual/link
checks and `git diff --check`, not source calls or restarts. Report checks actually
run and limitations. Do not commit/push/deploy or change runtime/data ownership
without a covering request. The active product UI is `../NADI/` (Laravel); this
component keeps its existing responsibility and safety boundary.

## Existing deployment and database ownership

Read the root `../AGENTS.md` first. The existing managed deployment is
`reliability-cockpit-platform`, using root `compose.yaml` + `compose.dev.yaml`.
Reuse `maximo-db` / database `maximo_collector` / volume `maximo-db`.
No new DB, parallel Compose project, or duplicate Maximo worker is needed.
The old per-project Postgres container on host port 5434 is not this store;
do not start it or copy an example over the existing `.env` by default.

The **Reliability Mart lives in this same database**. Keep legacy tables and
canonical tables together. `mart-projector` runs
`mxcollector mart-project --incremental` over local Equipment/Work Order rows,
with `RELIABILITY_CONTRACTS_ROOT=/contracts` and a read-only contract mount.
It does not call Maximo or load every canonical domain. Preserve existing
FMEA/RCFA/health/overhaul data and the governed `reliability_asset_registry`.
The FastAPI canonical read API uses this Mart for Laravel and the retained
Next.js UI; legacy Cockpit sync uses our API. Existing installations may use privately pinned runtime images; read `../deploy/compose/runtime-durability.md` before operations. Do not
rebuild the dirty checkout or use generic Compose recreation on retained backups.

Before source collection, check for Docker, local, systemd and cron workers.
Use one source worker; preserve scope, rate/page guards and cursors. A partial
run must not advance its successful watermark. API availability is not proof
of a complete, fresh source sync. See `docs/reliability-mart-v1.md` and
`docs/mx-012r-unified-collector-mart-pipeline.md` for projection semantics.

## Mission

Collect verified Maximo OSLC objects (site BSR, org IP) into a local
contract-shaped store and serve them to consumers (the reliability cockpit)
without ever mutating production Maximo.

## Source of Truth

1. Object structures must exist in `maximo-knowledge` with `status: verified`.
2. Verified objects (release 1): `mxapiasset` (preferred equipment source),
   `mxwodetail`, `mxapisr`, `mxperson`, `mxitem`, `mxapilabor`. `mxasset`
   remains available for explicit backwards-compatible runs.
3. Field translation source of truth:
   `reliability-data-contracts/mappings/maximo-to-contracts.md`.
4. If knowledge is missing, add a discovery task in `maximo-knowledge` — never
   guess identifiers in this repo.

## Mandatory Safety Rules

1. **READ ONLY against business data.** Every request to `/oslc/*` is
   GET/HEAD/OPTIONS only; anything else raises `OslcError`
   (`src/adapters/maximo/oslc_client.py`, `READ_ONLY_METHODS`).
2. **The single exception is authentication**: one POST to
   `/j_security_check` per session (programmatic login), prescribed by
   `maximo-knowledge/docs/authentication.md` for downstream apps. Login is
   authentication, not data mutation. It lives in `src/adapters/maximo/auth.py`
   only — the OSLC client guard stays untouched.
3. Never create/update/delete Maximo business data, no POST/PUT/PATCH/DELETE
   to `/oslc/os/*` or any business resource.
4. BSR/IP scope is applied on every query: `siteid="BSR"` for site-scoped
   objects, `worksite="BSR"` for labor, `site="BSR"` for items, and the
   verified org-level `locationorg="IP"` scope for persons. Equipment is
   additionally restricted to Maximo `eq11="CS01"` (configurable only through
   the validated `MAXIMO_EQUIPMENT_UNIT` setting).
5. Rate limit 1 req/s and 1 MiB response cap on every request (including
   login).
6. Credentials and session cookies live in memory only — never logged, never
   persisted. `.env` is gitignored.
7. On login failure: raise a clear error. No retry loops (anti brute-force).
8. On session expiry mid-sync: re-login ONCE and retry the page.
9. The collector writes only to its **own** Postgres store.

## Architecture

```text
maximo-knowledge (verified object maps)
      │
      ▼
mxcollector sync ──▶ OslcClient (GET-only, rate-limited)
      │                 ▲
      │        MaximoAuth (POST /j_security_check once, cookie in memory,
      │                 re-login once on expiry)
      ▼
Postgres (contract-shaped: equipment, work_order, service_request,
          person, item, labor, sync_cursor, collect_run, Reliability Mart)
          managed maximo-db:5432; host :5434 is legacy standalone only
      │
      ▼
FastAPI read-only views (contract field names, vendor under sources.maximo)
                                          :8002
      │
      ▼
reliability-cockpit (legacy sync pulls API; canonical API reads this DB's Mart;
                     never touches production Maximo)
```

## Commands

The bootstrap below describes a fresh isolated installation. For this existing
workspace, reuse the root Compose services and stores instead; do not run
these DB/worker bootstrap steps alongside the managed deployment. Create an
environment file only if absent. Read-only tests can use the existing venv.

```bash
python3 -m venv .venv && .venv/bin/pip install -e .
[ -e .env ] || cp .env.example .env      # fresh setup only; preserve existing credentials
docker compose up -d postgres           # Postgres on :5434
mxcollector init-db
mxcollector sync                        # WO/SR + operational master data
mxcollector sync mxapiasset             # preferred equipment object (or: equipment)
mxcollector serve                       # FastAPI on 127.0.0.1:8002
.venv/bin/python -m unittest discover -s tests
```

The optional `web/` Next.js app provides a local BSR dashboard. Its sync
buttons call the collector's local trigger endpoint; the collector still uses
POST only for the prescribed login handshake and GET/HEAD/OPTIONS for Maximo
business data.

## Current WO policy and evidence

- Preserve the inclusive rolling four-calendar-year `reportdate` window in
  Asia/Jakarta. Do not substitute changedate, actuals or WO numbers. Unknown,
  invalid, naive and future age fails closed. Older retained records are not
  deleted/hidden and remain eligible for local projection.
- New/changed active detail, first/transition CLOSE actuals, same-terminal-status
  freeze, CAN/CANCEL summary-only, and reopen clock-cycle isolation are deliberate.
  Do not refetch frozen history just to populate new evidence fields.
- Bounded newest-first traversal and active queue share source advisory lock,
  request budget, 1-second rate floor and 1 MiB response cap. The active queue
  cannot promote the traversal cursor. Partial/errors never become full coverage.
- Preserve the existing authorized worker command and schedule, including any
  private WO-only override. A post-cycle pause is not a freshness guarantee.
  Compare runtime identity/config before any authorized activation.
- Failure-code projection and per-field reliability evidence retain identity,
  scope, observation version, explicit-null/omission and date validity. Summary
  polls must not fabricate detail evidence. Public DTO exposure stays allowlisted.
- `downtime` MXWODETAIL is a boolean, not hours; labor effort and actual elapsed
  WO are not MTTR. Preserve null/NOT_READY gates and legacy KPI masking downstream.
  See `../plans/MTBF-MTTR.md`, the policy implementations under `src/services/`,
  and `tests/test_reliability_evidence.py`. Private operational reports stay local.

## Watermarks

Delta sync per object (mirrors the cockpit engine this project replaced):

| object | watermark |
|---|---|
| mxasset / mxwodetail / mxapisr | `changedate` |
| mxperson / mxitem | `statusdate` |
| mxapilabor | — (full sync each run; small table) |

Mapping failures must remain visible; skipping an individual row must not turn
an incomplete WO traversal into success or advance its successful cursor. Cursors
persist in `sync_cursor`; `collect_run` records bounded progress and failures.
The source-version watermarks above are not the WO reportdate age boundary.

Routine `mxwodetail` sync uses newest-first bounded acquisition: 25 rows/page,
20 pages, 40 business requests including detail reads/retries. It uses the
verified `wonum in ["BSR%"]` form, never LIKE or an unverified date comparator.
It validates whole-page descending order and BSR/IP scope, replays cursor ties,
and stops strictly below an existing cursor. Partial/error runs never advance
the WO cursor. Missing routine cursors return BOOTSTRAP_REQUIRED with zero source requests.
Use explicit `bootstrap-workorders-recent --max-pages N --request-budget N` for
operator-controlled recovery. Its initial floor comes from existing local WO
MAX but is frozen before upserts in the existing collect_run recovery-floor
marker; retain that marker on retry. Only reconciled traversal through all floor
ties can establish a runtime cursor. Partial runs never seed one from local MAX.
See `docs/maximo-wo-recency-001.md` for ceilings and deployment/paging review.

`mxcollector backfill` remains separate and cursor-independent; it does not
establish an operational cursor. Generic resources keep their existing mapping
error handling. A row that fails to map is logged and skipped — one bad row never aborts a
sync. Cursors persist in `sync_cursor`; collect runs are logged in
`collect_run` for observability.


## Gotchas

- OSLC records live under the `_member` key (fallbacks `member`,
  `oslc:member`, `rdfs:member`).
- Next-page link is nested under `oslc:responseInfo.oslc:nextPage`.
- Maximo scalars arrive as strings — use the `oslc_*` coercion helpers.
- Session expiry signature: 302 to `login.jsp`, 401/403, or an HTML body
  where JSON was expected.

## Git Rules

```text
feat(auth): add programmatic login
feat(sync): delta sync with changedate watermark
feat(api): contract-shaped views
```

Do not merge, reset, force-push, or rewrite history unless explicitly authorized.
