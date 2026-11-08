# AGENTS.md — BSLA workspace

Read this file, then the owning component's `AGENTS.md` and relevant source docs.
This is one Git repository. **NADI Laravel in `NADI/` is the active product
workspace.** `reliability-cockpit/` remains the FastAPI/Mart backend and retained
Next.js application; choosing Laravel does not authorize a production cutover.

## 1. Solo developer workflow

- Work directly in the active checkout. Check `git status` and the current branch
  before edits; preserve all unrelated staged, unstaged and untracked work.
- Make a small useful change, run checks proportional to its impact, then inspect
  the result in the existing preview: **edit → test → inspect**.
- No routine extra worktrees, subagents, handoff gates, parallel implementation
  teams or mandatory branch/fetch/review ceremonies. Use extra structure only
  when explicitly needed or requested, not as the default way to resume work.
- Reuse current environments and dependencies. Read package scripts before testing.
  Documentation-only changes need fact/link checks and `git diff --check`, not
  application restarts, source collection or migrations.
- Report what changed, checks actually run, and unresolved limits. A source check
  or DOM test is not a browser visual pass; a focused suite is not a full pass.
- Do not commit, push, merge, deploy, rewrite history, discard changes or switch
  deployment modes without a request that authorizes it. Never reset or clean
  the working tree as a shortcut. Delete obsolete plans only recoverably after
  moving useful requirements into the current roadmap; retain evidence/runbooks.

## 2. Existing data and runtime are the default

Continue using the existing databases, volumes, APIs and collector identities.
Do not create a new operational database to implement a feature or fix an empty
page. Reliability Mart is a set of tables **inside the Maximo Collector DB**.

- No DB container/DSN/volume/project-name replacement or architecture migration
  without an explicit request. Correct a mistaken DSN only after verifying its
  documented existing owner. Do not create a store as a side effect.
- Never use `docker compose down -v`, remove volumes, drop/truncate tables, reset
  cursors, or redownload production history to compensate for a wrong connection.
- Compatible schema additions belong in the existing owning store. Back up and
  verify before a requested data/migration operation. Tests may use temporary,
  hermetic stores, never operational data or source systems.
- Preserve `.env` files, secrets, private workbooks, models, local logs and backups.
  Never copy an example over an existing `.env`, print full DSNs, or expose
  unfiltered `docker inspect` / interpolated Compose environment output.
- Laravel's existing ignored `NADI/database/development.sqlite` owns local accounts,
  inspection/recommendation drafts, PdM, manual disruptions, asset priorities and
  workspace audit records. It is not a source replica or production replacement.
- NK has no DB. It consumes the existing PI Collector API or manual/CSV input.

## 3. Components and data paths

| Directory | Responsibility | Persistence |
|---|---|---|
| `NADI/` | Laravel 13 / Blade / Vite active UI | Existing development SQLite only |
| `reliability-cockpit/` | FastAPI query backend and retained Next.js UI | Cockpit legacy store; read-only Mart connection to Maximo DB |
| `maximo-collector/` | Maximo acquisition, API and local Mart projection | Existing Maximo Collector Postgres |
| `pi-collector/` | PI snapshots/time series/API | Existing PI TimescaleDB |
| `cems-collector/` | Modbus reads, normalization, aggregation/API | Existing CEMS Postgres |
| `maximo-knowledge/`, `pi-knowledge/` | Verified source catalogs and mappings | Knowledge files, no app DB |
| `reliability-data-contracts/` | JSON Schema Draft 2020-12 / semantics | Contract files |
| `NK/` | Documentation for separately maintained Streamlit consumer; code is not bundled here | Model/scaler/session history in its own checkout, no DB |

```text
Maximo → maximo-worker → Maximo DB → maximo-api → legacy cockpit-worker → Cockpit DB
                              │
                       local mart-projector
                              │
                   Mart tables IN Maximo DB
                              │
                 cockpit-api /v1/reliability/*
                         ┌────┴────┐
                    NADI Laravel   retained Next.js UI
                    local SQLite   legacy /api/cockpit/* proxy
PI → pi-worker → PI DB → pi-api → PI dashboard / NK
PLC → cems-worker → CEMS DB → cems-aggregator / cems-api → CEMS dashboard
```

Laravel uses `RELIABILITY_MART_API_BASE` via GET-only bounded DTOs. It must not
read source SQL, copy source records into SQLite, register Assets, or collect.
A narrowly scoped legacy description fallback reads the existing loopback Maximo
Collector API after exact WO+Asset matching; it must not expose raw payloads.

`cockpit-api` uses `RELIABILITY_MART_DATABASE_URL` for the existing Maximo DB,
with the configured SELECT-only identity. No fallback to legacy
`DATABASE_URL`; a missing Mart connection returns unavailable/503.
`cockpit-worker` consumes collector APIs into its separate legacy store.

Master Asset inventory and governed Registry are different populations. Inventory
supports exact non-Registry Asset/WO history; Registry-only operations retain
membership gates. Technical counts or a populated `asset_master` do not prove
Registry availability. Never auto-enroll all technical assets or fuzzy-match IDs. Only one VERIFIED
PRIMARY_EQUIPMENT target resolves to MAPPED; proposed, retired, unmapped and
ambiguous records remain unusable. Controlled governance commands require the
explicit existing-owner admin DSN, never a fallback from the SELECT-only API.
Read `reliability-cockpit/docs/mart-runtime.md` before deliberate DDL or role changes.

`mart-projector` projects retained local Equipment/WO only, without Maximo calls,
using `RELIABILITY_CONTRACTS_ROOT=/contracts` and its read-only mount. Preserve
FMEA, RCFA, health, overhaul, Registry, AF mappings and projection state. The
projector does not populate every domain. PI/CEMS projections and the NADI
historian/Operations integration remain pending; configured URLs are not proof.

## 4. Deployment identity and safe operations

Resolve the active checkout path locally. Preserve any existing compatibility
symlinks while Docker mounts, systemd units, venvs or worktree pointers use them.

- Managed project: `reliability-cockpit-platform`; network:
  `reliability-cockpit-platform_platform`.
- Files: `compose.yaml` + `compose.dev.yaml`; existing `.env.platform`.
- Private DB port 5432, no published managed DB ports. Volume names retain the
  project prefix, for example `reliability-cockpit-platform_maximo-db`.

| Service | Database / owner | Volume | Default app ports |
|---|---|---|---|
| `maximo-db` | `maximo_collector` | `maximo-db` | API 8002 / dashboard 3001 |
| `pi-db` | `pi_collector` | `pi-db` | API 8001 / dashboard 3002 |
| `cems-db` | `cems_collector` | `cems-db` | API 8003 / dashboard 3003 |
| `cockpit-db` | `cockpit` | `cockpit-db` | API 8000 / retained Next.js 3000 |
| Laravel preview | existing development SQLite | no Compose DB volume | loopback 8010 |
| NK | no DB | none | separate Streamlit 8501 |

Existing installations may select privately pinned Collector/Mart/Cockpit images.
The public clone does not include the private lock or archived images. Read `deploy/compose/README.md` and `runtime-durability.md` there before
an operation. Use `runtime_release.py verify` and the exact-service
`runtime_service.py` workflow when a restart/recreate is actually needed.
Stopped rollback containers retain Compose labels: no mass `compose up`,
`--remove-orphans`, rebuild from the dirty checkout, or generic service recreation.
Never start a saved worker alongside its active replacement.

Old per-project Postgres containers/ports 5434, 5433, 5435 are not the managed
stores. `compose.external.yaml` is a separate alternative project/volume, not an
overlay or routine recovery route. Do not switch to it to fix NADI.

Before service/data work:

1. Inspect relevant Compose definitions, running containers/processes, systemd
   and cron. One collector worker per source/registry; no duplicate local daemon.
2. Verify non-secret API/DB owner, project, network, volume and image identity.
3. Check completed runs, partial/errors, cursors and collection timestamps.
   HTTP 200, source record dates and `mart_updated_at` do not prove source freshness.
4. For empty pages, check Mart connection, scope, inventory/Registry population,
   projection state and DTO compatibility before considering source acquisition.
5. Reuse a reviewed local migration with backups if data exists in another old
   volume. Preserve newer rows/cursors, conflict keys and sequences. Never reset.
6. Restart only affected services if authorized and needed. Successful one-shot
   registry/init jobs are not failed daemons.

## 5. Current collection and reliability semantics

- Maximo WO acquisition uses an inclusive rolling **four calendar years** of
  verified `reportdate` in `Asia/Jakarta`. It is not changedate/actual/WO-number
  age. Unknown, invalid, naive or future age fails closed. Older retained rows
  remain readable and projectable; this is acquisition policy, not deletion.
- New/changed active WOs get needed detail. CLOSE gets current-cycle actuals when
  first observed/transitioned; same terminal status stays frozen. CAN/CANCEL is
  summary-only. No terminal recovery/backfill just to fill missing evidence.
- Bounded newest-first traversal and active-status queue share source locks,
  request/rate/page budgets. Incomplete/error runs must not advance successful
  cursors. Do not turn local skips into a verified source-total claim.
- Failure code, problem, faildate, parent/task/follow-up clues are evidence, not
  governed failure identity. `downtime` is a source boolean, not hours; labor
  effort and CLOSE actual elapsed time are not repair/restoration duration.
- Manual disruption records are engineer observations with corrections, not
  automatically validated failures. Cause/affected/unknown asset roles remain
  distinct. WAPPR is backlog, repeat WO is a review candidate, and no data is not
  proof of health. Do not sum per-asset event counts into plant incident totals.
- WO-only MTBF/MTTR/availability remain null with **NOT_READY** and blockers,
  including old stored KPI snapshots at the read boundary. Do not re-enable the
  formulas from raw WO counts or calendar hours. Follow `plans/MTBF-MTTR.md`.
- Verify the current PI acquisition owner before any source action. Do not
  retry authentication, change collection state or start history jobs without a
  covering request. Read stored data with honest age/quality; a snapshot worker
  does not authorize governed NADI identity mapping or exposure ingestion.

## 6. Production safety and source contracts

- Maximo/PI business data: GET/HEAD/OPTIONS only. Sole Maximo POST exception is
  the controlled `/j_security_check` login in scoped rules; never weaken the
  business-data guard or brute-force authentication.
- Preserve BSR/IP and verified CS01 scope. Field names differ by object:
  `siteid`, `worksite`, `site`, `locationorg`; use verified mappings.
- Maximo/PI rate limit defaults to 1 request/second and 1 MiB response cap.
  Preserve PI off-hours, circuit breakers, bounded chunks and resumable upserts.
  CEMS only FC03/FC04, with its register caps, poll floors and operator overrides;
  no outbound KLHK push. Consumer development must not trigger discovery/backfill.
- Do not guess endpoints, tags, WebIds, register numbers or cross-source links.
  Use the owning knowledge repository; discovery execution is separately opt-in.
- `unknown` = untested; `documented` = described, not verified; `verified` = tested
  with authorized access; `forbidden` = account denied; `deprecated` = do not use.
  HTTP 400 is not an access denial. PI eligibility is verified + stream ok;
  CEMS `collect` is distinct from registry status.
- Contracts: snake_case, explicit units, ISO-8601 timestamps, intentional nulls.
  Literal date-only observations must not acquire invented midnight/timezone.
  Vendor fields stay under `sources.*`; public DTO allowlists may be stricter.
- No credentials, cookies, tokens, Authorization headers, private DSNs or raw
  personal source samples in source control, logs, documentation or chat.

## 7. Independent NK input integrity

Read `NK/AGENTS.md` and `plans/NK-ROADMAP.md`. NK implementation and private
mapping inputs are not part of this public documentation-only directory. Use existing GET `/attributes` and
`/snapshots?limit=5000`, not direct PI/SQL or a new collector/store. Preserve all
13 training features and the model/scaler pair. Candidate tags are not mappings.
Check meaning, units, quality, finite values, age and time skew; missing/stale
inputs block auto prediction, never silently become zero/manual defaults.
PS means **pemakaian sendiri**; its tag and W/MW unit remain unconfirmed, not a
percentage or guessed auxiliary sum. SFC and APH inlet/outlet equivalence remain
unconfirmed. History is session-local and bounded, not persistent model validation.

## 8. Discovery, checks and documentation

Use codebase-memory graph tools when available for structural discovery; verify
index generation and path coverage, then read stale/partial/unknown paths
explicitly. File reads and `rg` are appropriate for docs/config and fallback.
Do not infer completeness from an old graph.

Use each component's existing environment; no root test suite:

```bash
# In NADI/; tests use memory SQLite + mocked HTTP.
composer test
vendor/bin/pint --test
npm run test:ui
npm run build
# In the affected Python component (reuse its venv):
.venv/bin/python -m unittest discover -s tests
# Documentation / all changes:
git diff --check
```

Validate the actual JSON Schema set for contract changes; do not hardcode a count.
Relevant checks include negative permissions, stale forms, missing/partial data,
repeat submissions and interrupted navigation. Do not seed test data in the user's
preview. Consult scoped test setup before any database integration test.

Current plans: `plans/README.md`, `plans/NADI-LARAVEL.md`, `plans/MTBF-MTTR.md`.
Feature detail/evidence stays in `NADI/docs/`; API contracts stay in
`reliability-cockpit/docs/`; source evidence in the owning knowledge/collector
component. Old release reports, `USERGUIDE.md`, worktrees and runtime backups are
historical references, not instructions to recreate old architecture.
