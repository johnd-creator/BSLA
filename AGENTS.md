# AGENTS.md — BSLA (workspace root)

Read this file before changing any subproject, then read that subproject's
`AGENTS.md` and relevant `CONTEXT.md`. This is one Git repository with **eight existing
components plus the NADI Laravel development workspace**. Each component has its own dependencies and tests; the root
Compose files provide a shared deployment, not a shared build or test suite.

## 1. Existing data and deployment are the default

**Continue development using the existing databases, volumes, collectors, and
APIs. Do not create a new application database to implement a feature.**

- Reuse the owning component's current store. Reliability Mart is a set of
  tables inside the Maximo Collector database, not a fifth database.
- NK has no database. Its PI input comes from the existing PI Collector API.
- Do not add a DB container, redirect a DSN to a new store, change database or
  volume identities, switch Compose project names, or switch deployment modes
  as a routine setup/fix. Those
  changes require an explicit user request for an architecture or data migration.
  Correcting a mistaken DSN to the documented existing owner is allowed after
  verifying the target; it must not create or replace a database.
- Do not use `docker compose down -v`, remove volumes, drop/truncate tables,
  recreate stores, or reset cursors to solve missing data.
- Schema additions belong in the existing owning store with compatible
  migrations. Temporary hermetic test databases are allowed; they must not
  replace operational stores or contact production sources.
- Preserve existing `.env` files and unrelated working-tree edits. Never
  overwrite an existing `.env` by copying an example over it.

A request to resume development or fix an empty page does not authorize
rebuilding the persistence architecture or deleting history.

## 2. Components and responsibilities

| Directory | Stack / responsibility | Persistent data owner |
|---|---|---|
| `maximo-knowledge/` | Python discovery, sanitized catalogs and verified Maximo mappings | Knowledge files; no app DB |
| `pi-knowledge/` | Python discovery, PI registry and verified WebIds | Knowledge files; no app DB |
| `reliability-data-contracts/` | JSON Schema Draft 2020-12 and semantic mappings | Contract files; no app DB |
| `maximo-collector/` | Python / FastAPI / SQLAlchemy; Maximo read-only sync and Mart projection | Existing Maximo Collector Postgres |
| `pi-collector/` | Python / FastAPI / SQLAlchemy; PI snapshots and time series | Existing PI Collector TimescaleDB |
| `cems-collector/` | Python / FastAPI; Modbus reads, normalization, aggregation | Existing CEMS Collector Postgres |
| `reliability-cockpit/` | NADI: FastAPI backend + Next.js 15 / React 19 / TypeScript | Existing Cockpit Postgres for legacy sync/KPIs; reads Mart in Maximo DB |
| `NK/` | Streamlit / pandas / scikit-learn / joblib; coal calorific value prediction | No DB; local model/scaler/mapping files and session history |
| `NADI/` | Laravel 13 / Blade / Vite development workspace | Existing ignored local SQLite for development accounts and inspection drafts only; source Asset/WO reads use existing APIs |

Collector dashboards also live under each collector's `web/`. The knowledge
repositories are not daemon applications. `manifest.json` is a generated file
inventory, not a build manifest. Only the workspace root is a Git repository.

### NADI Laravel development

Physical root is `/home/john-d/Music/BSLA`; the old root path is a compatibility
symlink for existing Docker mounts, units, venvs and worktrees. Keep Compose project,
volumes and operational store identities unchanged. Laravel is an additional
local development UI, not an automatic cutover of the existing NADI deployment.
Read `NADI/AGENTS.md` and `NADI/README.md` before changing it. Work as one developer
in the active checkout: small changes, focused tests and an immediately usable
preview. Do not add routine worktrees, handoff gates or subagents.

## 3. Data flow and ownership

```text
maximo-knowledge + pi-knowledge → reliability-data-contracts
          │ verified source identifiers and semantic mappings
          ▼
Maximo → maximo-worker → Maximo Collector DB → maximo-api
                              │                     │
                              │                     └→ cockpit-worker → Cockpit DB
                              │                                           │
                       mart-projector                           legacy sync/KPI API
                              │                                           │
                 Reliability Mart tables                                  │
                 IN THE SAME MAXIMO DB                                    │
                              │                                           │
                 cockpit-api /v1/reliability/* ────────────────────────────┤
                                                                          ▼
                                                                  NADI Next.js UI
PI → pi-worker → PI Collector DB → pi-api → PI dashboard / NK input
PLC → cems-worker → CEMS DB → cems-aggregator → cems-api → CEMS dashboard
Manual input / CSV ───────────────────────────────────────→ NK prediction
```

### NADI has two distinct read paths

1. **Legacy collector ingestion:** `cockpit-worker` consumes Maximo Collector
   API resources, writes normalized records to Cockpit's `DATABASE_URL`, and
   computes legacy KPIs. It does not rediscover or authenticate to Maximo.
2. **Canonical Reliability Mart:** `cockpit-api` reads
   `RELIABILITY_MART_DATABASE_URL`, pointing to the existing Maximo Collector
   database. Public `/v1/reliability/*` queries are read-only and do not copy
   Mart records into Cockpit's legacy store. No fallback to the legacy DSN is
   allowed when the Mart DSN is missing; Mart routes can return HTTP 503.

The Mart includes `asset_master`, `maintenance_event`, `fmea_assessment`,
`rcfa_analysis`, `asset_health_assessment`, `overhaul_event`, and governance /
projection relations such as `reliability_asset_registry`, `asset_af_mapping`,
and `mart_projection_state`. Normal NADI Asset lists use governed Registry
membership; technical `equipment` or `asset_master` counts alone do not prove
those lists are populated. Do not register every technical asset automatically.

`mart-projector` incrementally projects **local** Equipment and Work Order
records. It never calls production Maximo. It requires the read-only contract
mount and `RELIABILITY_CONTRACTS_ROOT=/contracts`. It does not populate all
FMEA/RCFA/health/overhaul records from production; preserve their existing
controlled loads and handle missing domains through their documented pipeline.

PI/CEMS Collector API bases are configurable in Cockpit, but their Cockpit
projections remain pending. Configured URLs do not prove ingestion exists.
The direct Cockpit PI adapter remains a placeholder. Do not add production
PI/Maximo credentials to Cockpit or NK.

The browser uses `/api/cockpit/*`; Next.js proxies to `COCKPIT_API_BASE`.
Diagnose both the proxy and the corresponding backend data path.

## 4. Deployment identity and database map

Last deployment handoff: **2026-10-07**. Confirm actual runtime before making
changes; these names describe the existing managed deployment, not a reason to
create missing resources in a different project.

- Compose project: `reliability-cockpit-platform` (`name` in `compose.yaml`).
- Files: `compose.yaml` + `compose.dev.yaml`; configuration: `.env.platform`.
- Network: `reliability-cockpit-platform_platform`.
- DBs use container port 5432 on the private network, with **no published host
  DB ports**. `localhost:5432` is not evidence of the managed Cockpit DB.

| DB service | Database / user | Compose volume | Used by |
|---|---|---|---|
| `maximo-db` | `maximo_collector` | `maximo-db` | Maximo worker/API, Mart projector, NADI Mart reader |
| `pi-db` | `pi_collector` | `pi-db` | PI registry loader, worker/API; NK consumes API only |
| `cems-db` | `cems_collector` | `cems-db` | CEMS worker, aggregator, API |
| `cockpit-db` | `cockpit` | `cockpit-db` | Cockpit legacy worker/API/KPIs |

Physical volumes are prefixed `reliability-cockpit-platform_`, e.g.
`reliability-cockpit-platform_maximo-db`. Changing `-p`, `COMPOSE_PROJECT_NAME`,
or the Compose `name` can select different, empty volumes.

| Application | Web port default | API port with `compose.dev.yaml` |
|---|---|---|
| NADI / Cockpit | 3000 | 8000 |
| Maximo Collector | 3001 | 8002 |
| PI Collector | 3002 | 8001 |
| CEMS Collector | 3003 | 8003 |
| NK (separate Streamlit process) | 8501 | Uses PI API; no separate backend DB |

Ports can be overridden; confirm listeners and resolved non-secret settings.
Legacy per-project DB containers (`maximo-collector-postgres`,
`pi-collector-postgres`, `cems-collector-postgres`, `cockpit-postgres`) and their
volumes may still exist. They were stopped after local-data migration. Their
old host ports 5434/5433/5435 and local Cockpit port configuration are not the
managed databases. Do not restart them or use their `.env` DSNs by default.

`compose.external.yaml` is an alternative deployment named
`reliability-cockpit-external`; it creates a separate Cockpit volume. It is not
an overlay for the running managed deployment. Do not switch to it to fix NADI.
Read `deploy/compose/README.md` before deployment changes.

## 5. Mandatory checks before running services or repairing data

1. Read `git status`, the relevant scoped instructions, and current Compose
   service definitions. Confirm the project name and existing containers/volumes.
2. Inspect running Docker workers, local processes, systemd units, and cron for
   the affected source. **One collector worker per source/registry**: do not run
   local `.venv` collection alongside Compose, systemd, or another worker.
3. Confirm API bases and DB host/database/owner without printing passwords,
   tokens, cookies, full DSNs, or interpolated Compose environment output.
4. Check API responses, worker logs, last completed runs, cursors and recent
   collection timestamps. HTTP 200 proves availability, not fresh source data.
   Source-record dates and `mart_updated_at` are not source sync freshness.
5. For empty NADI pages, check the Mart DSN, canonical table population,
   Registry membership, scope filters, and `mart_projection_state` before
   touching legacy sync or production collection.
6. If old local data is in another existing volume, use a backed-up, reviewed
   local migration into the intended store. Preserve newer rows and cursors,
   use stable conflict keys, and reset sequences after importing explicit IDs.
   Do not redownload production history to compensate for a wrong DSN.
7. Restart only the affected services after a necessary change. Init/registry
   services exiting successfully are normal one-shot jobs, not broken daemons.

Safe initial runtime inventory from the root:

```bash
docker compose --env-file .env.platform -f compose.yaml -f compose.dev.yaml ps -a
docker compose --env-file .env.platform -f compose.yaml -f compose.dev.yaml config --services
docker volume ls --filter name=reliability-cockpit-platform
```

Do not run unfiltered `docker inspect` or interpolated `compose config` in chat
outputs: they can expose secrets. Per-project README/bootstrap commands are
for isolated installations; they do not override this existing deployment.

## 6. Current operational handoff (recheck when relevant)

- **PI authentication is deferred at the user's request.** Last source check
  returned HTTP 401. Do not retry credentials, enable `pi-collection`, or start
  `pi-auth-check` / `pi-worker` until the user says credentials are ready and
  asks to resume. This is a session handoff, not a permanent PI limitation.
- PI API/dashboard may serve stored snapshots and history while collection is
  paused. `pi-registry` is a local registry loader, not a collection daemon.
  `pi-auth-check` and `pi-worker` are opt-in under the `pi-collection` profile.
- Managed PI workers read source config from `pi-collector/.env`; Compose
  overrides their `DATABASE_URL` to `pi-db`. Managed DB and Maximo/CEMS worker
  settings use `.env.platform`. Do not copy source secrets into consumer apps.
- Local history was merged into the managed Maximo/PI stores; NADI Mart routes
  were populated and the local projector completed. Do not assume today's
  exact row counts or timestamps from that handoff; verify them when needed.
- Maximo worker was active, but some source runs reported partial completion
  and mapping skips. A running process or successful login does not prove full
  sync. Preserve page/rate guards and never advance cursors for incomplete runs.

## 7. NK input rules — no new database

NK supports **manual sliders/CSV** and **PI Collector API** input. PI mode reads
stored `GET /attributes` and `GET /snapshots?limit=5000`; it must not connect
directly to PI production, read SQL with a new DSN, or trigger collection.
`PI_COLLECTOR_API_BASE` defaults to `http://127.0.0.1:8001` for host-local NK.
Containerized clients must use the appropriate service/network address.

`NK/pi_feature_mapping.json` governs all 13 model inputs. Candidate tags are
not verified model mappings. Confirm feature meaning, source/training units,
registry identity and evidence before marking a mapping usable. Validate
finite numbers, quality flags, source age and timestamp skew on every refresh.
Missing/stale/invalid inputs block automatic predictions; do not substitute
zeros, dummy values, or manual inputs silently. Preserve training feature order
and the model/scaler pair. Technical integration is not model validation.

**PS means pemakaian sendiri**, confirmed by the user. The exact tag and unit
(W or MW) remain unconfirmed; do not treat PS as a percentage or infer a sum of
auxiliary tags. SFC derivation and APH inlet/outlet equivalence also remain
unconfirmed. Prediction history is session-local (bounded, JSON export), not
persistent storage. Read `NK/AGENTS.md` and `NK/PI_MAPPING.md` before changes.

## 8. Production safety and semantic contracts

- Production business data stays **READ ONLY**. Maximo OSLC and PI requests
  allow GET/HEAD/OPTIONS only. The sole Maximo POST exception is the controlled
  `/j_security_check` authentication handshake documented in the scoped rules;
  never relax the business-data guard. No authentication brute force.
- Preserve Maximo BSR/IP scope and validated CS01 equipment scope. Field names
  differ by object (`siteid`, `worksite`, `site`, `locationorg`); follow the
  verified mapping rather than adding `siteid` blindly to every resource.
- Maximo/PI HTTP clients enforce rate limiting (default 1 request/second) and
  a 1 MiB response cap. CEMS permits FC03/FC04 reads only; preserve its own
  register caps, transaction gap and poll floors, and normalization overrides.
- PI bulk recorded history has off-hours gates, circuit breakers, bounded
  chunks and resumable upserts. Never bypass guards or reset tables to retry.
  Do not launch backfills as a side effect of opening NK or diagnosing a page.
- Never guess production paths, objects, tags, WebIds or register numbers.
  Add a bounded discovery task in the owning knowledge repository when needed;
  discovery execution is opt-in, not implicit in ordinary app development.
- Status vocabulary: `unknown` = untested; `documented` = described but not
  verified; `verified` = tested with authorized access; `forbidden` = current
  account denied; `deprecated` = should not be used. PI collection eligibility
  requires registry `verified` + stream `ok`. CEMS operational `collect` is a
  separate switch from registry verification status; preserve scoped rules.
- Core contracts use snake_case, explicit units and ISO-8601 timestamps.
  Vendor fields belong under `sources.maximo`, `sources.pi`, `sources.cems`.
  Public NADI DTOs follow their stricter approved exposure boundary; do not
  expose raw vendor payloads or internal provenance automatically.
- Preserve governed identities and unresolved relationships. Do not fuzzy-match
  Maximo Assets to PI AF elements or invent RCFA links/health scores.
- Secrets remain in ignored environment files/runtime memory. Never commit or
  log credentials, tokens, cookies, Authorization headers, private DSNs, or
  unsanitized source samples. Report authentication status without secret values.

## 9. Code discovery and validation

Prefer codebase-memory MCP graph tools for structural discovery. At session
start or after compaction confirm the nearest graph project and generation
with `list_projects` or `index_status`; use Tier 2 verification by default.
Use `search_graph`, `trace_path`, and `get_code_snippet`, then
`check_index_coverage` for every evidence path and scopes behind negative or
exhaustive claims. Use `query_graph` / `get_architecture` for broader structure.
Coverage is best-effort. Read stale, partial, skipped, excluded or unknown
source directly; do not infer completeness from an old graph. File reads/`rg`
are appropriate for config, documentation, literals, and coverage fallback.

Use each component's environment and tests; there is no root test command.
Most Python suites use hermetic `unittest` tests without production access;
Mart tests can use temporary SQLite. Do not create an operational database to
run them. Typical commands (reuse existing environments):

```bash
cd maximo-collector  # or pi-collector, cems-collector, reliability-cockpit, knowledge dirs
.venv/bin/python -m unittest discover -s tests
# NK, from NK/:
MPLCONFIGDIR=/tmp/nk-matplotlib .venv/bin/python -m unittest discover -s tests
# A relevant Next.js web/ directory: inspect package.json for its checks/build.
```

Schema validation belongs in `reliability-data-contracts`; reuse an environment
with `jsonschema`, and validate the actual schema set rather than a hardcoded
count. Use focused checks appropriate to the change. For docs-only changes,
verify references and `git diff --check`; runtime restarts are unnecessary.
Use scoped conventional commits; never reset, force-push, or discard unrelated
changes. Do not commit secrets or model/data artifacts incidentally.

## 10. Read next

| Task | Documentation |
|---|---|
| Deployment or worker diagnosis | `deploy/compose/README.md`, Compose files, relevant scoped `AGENTS.md` |
| Maximo source discovery | `maximo-knowledge/CONTEXT.md`, `maximo-knowledge/AGENTS.md` |
| PI source discovery | `pi-knowledge/CONTEXT.md`, `pi-knowledge/AGENTS.md` |
| Contracts and mappings | `reliability-data-contracts/README.md`, `reliability-data-contracts/AGENTS.md` |
| Maximo collection / Mart projection | `maximo-collector/AGENTS.md`, `docs/reliability-mart-v1.md`, `docs/mx-012r-unified-collector-mart-pipeline.md` under that project |
| NADI queries / governance | `reliability-cockpit/AGENTS.md`, `docs/reliability-mart-query-api.md`, `docs/asset-af-mapping-admin.md` under that project |
| CEMS reads / normalization | `cems-collector/AGENTS.md` (preserve documented operator overrides) |
| NK manual / automatic prediction | `NK/AGENTS.md`, `NK/README_WebApp.md`, `NK/PI_MAPPING.md` |
| Historical local setup | `USERGUIDE.md` and per-project READMEs; reconcile with current deployment first |
