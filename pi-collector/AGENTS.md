# AGENTS.md — PI Collector

## Solo developer workflow

Follow root `../AGENTS.md`. Work directly in the active checkout: inspect existing
changes → edit a small scoped change → run relevant checks → inspect the result.
Preserve unrelated work. No routine extra worktree, subagent, mandatory branch,
handoff or layered approval process. Documentation-only work needs factual/link
checks and `git diff --check`, not source calls or restarts. Report checks actually
run and limitations. Do not commit/push/deploy or change runtime/data ownership
without a covering request. The active product UI is `../NADI/` (Laravel); this
component keeps its existing responsibility and safety boundary.

## Mission

Collect verified PI Web API time-series data into a local store and serve it
to multiple consumers (trending dashboards, ML pipelines, reliability cockpit)
without ever mutating production PI.

## Source of Truth

Before introducing a PI tag, WebId, or attribute into technical collection:

1. The attribute **must** exist in `pi-knowledge` with `status: verified`.
2. The registry YAML (`../pi-knowledge/mappings/bsr1-parameters.yaml`) is the
   sole input for technical collection — never hardcode WebIds in collector
   code. A technical registry entry is not a governed NADI Asset signal.
3. If an attribute is missing, create a discovery task in `pi-knowledge` first.
4. Do not guess production identifiers.

Governed source operations accept only explicit `GovernedAfTarget` values from
a trusted mapping resolver. They use source-returned metadata after checking
AF server/database/element/attribute lineage, not guessed names or new technical
registry seeds. This does not approve attribute business semantics. See
[governed boundary](docs/governed-source-boundary.md). No public live-source
proxy route is provided; future orchestration must enforce unique Mart mapping
resolution and caller authorization before creating a target.

## Mandatory Safety Rules

1. **READ ONLY.** Never execute POST, PUT, PATCH, DELETE, MERGE, or any
   state-changing request against PI production.
2. Never create/delete/update PI Points, AF Elements, Attributes, analyses,
   event frames, or configuration.
3. Never brute-force WebIds, tag names, or authentication.
4. Respect server rate limits (hard minimum 1s/request).
5. Never store credentials, cookies, NTLM/Kerberos artifacts, tokens, or
   session data.
6. The collector writes only to its **own** Postgres/TimescaleDB store.

## Architecture

```text
pi-knowledge (registry YAML)
      │
      ▼
load-registry ──▶ pi_attribute_registry (Postgres)
                        │
collect-snapshots ──────┤  ◀── PiClient (GET-only, rate-limited)
backfill ───────────────┤
backfill-recorded ──────┤  (off-hours gate + circuit breaker + chunking)
run (daemon) ───────────┤
                        ▼
              pi_snapshot + pi_timeseries (TimescaleDB hypertable)
                        │
                        ▼
              FastAPI (read-only views for consumers)
```

## Commands

```bash
picollector init-db              # create missing tables; does not alter existing columns
picollector migrate              # local read-only migration status; no PI requests
picollector migrate --apply      # deliberate existing-store upgrade after backup/preflight
picollector worker --pause-seconds 300  # single leased snapshot owner
picollector load-registry        # load verified attributes from pi-knowledge YAML
picollector collect-snapshots    # fetch current values for all active attributes
picollector backfill --start "*-7d" --end "*" --interval 1h
picollector backfill-recorded --start "2024-01-01T00:00:00Z" --end "*"  # heavy, off-hours only
picollector run --mode snapshot --interval-seconds 300  # continuous daemon
picollector serve                # FastAPI on 127.0.0.1:8001
```

## Bulk Download Safety (non-negotiable)

`backfill-recorded` downloads every raw archived point and is the highest-risk
operation for the shared PI server. These guardrails are enforced IN CODE and
must not be weakened without explicit authorization:

1. **Off-hours gate** — `backfill-recorded` refuses to run outside
   22:00–06:00 local time (weekends allowed all day). `--force` overrides it;
   never use `--force` during business hours on production PI.
2. **Circuit breaker** — max 5000 API requests per session, then a clean abort.
3. **Consecutive-error abort** — 10 failures in a row aborts the run (PI may be
   down or rate-blocking us; hammering it further risks an account ban).
4. **Chunking** — long ranges are split into 7-day windows so each request is
   bounded and progress is committable.
5. **Pause between attributes** — 2s cooldown after each attribute.
6. **Rate limit + size cap** — every request is ≥1s apart, responses capped at
   1 MiB (enforced in `PiClient.request`).
7. **Idempotent resume** — upserts by (attribute_id, timestamp). After any
   abort, re-running the same command resumes; NEVER retry with a fresh table.

Scheduling (systemd units + cron in `deploy/`) triggers runs at night and on
weekends; the in-app off-hours gate stays active as the final authority.

## Gotchas

- PI pagination links (`Links.Next`) may be absolute URLs; `iter_recorded()`
  validates scheme/host/port against the configured PI origin before using the
  link. Foreign origins must be rejected so credentials cannot be forwarded.
- `recorded-delta` run mode tracks its cursor in `pi_collect_cursor` keyed
  `recorded-delta`; do not reuse that scope name for other purposes.
- The heatmap endpoint uses `date_trunc('day', ...)` — TimescaleDB accelerates
  this on the hypertable, plain Postgres will be slow on large datasets.

## Git Rules

Use small, focused commits:

```text
feat(collector): add snapshot collection
feat(api): add timeseries endpoint
fix(client): handle PI digital state values
```

Do not merge, reset, force-push, or rewrite history unless explicitly authorized.

## Existing-store/runtime ownership

Use the existing PI owner, never a new operational database. Follow
[operator runbook](docs/runtime-migrations.md): private full backup, actual schema
preflight, one acquisition owner, bounded local DDL, and stored-data API
acceptance before source canaries. `pi_schema_migration` is audit state in the
same store. Historical quality nulls remain null. Managed `worker` and `migrate`
share a session lease; legacy manual/backfill/API commands do not participate.
Disable competing schedulers first. Snapshot cadence is cycle duration plus
300s pause; no history job is automatically enabled. Read
[runtime evidence](docs/nadi-pi-runtime-001.md) for exact reviewed-image and
operator-tooling provenance. Governed target validation remains separate from
technical registry access; no legitimate verified target means defer the canary.


Managed deployment configuration belongs only to `.env.platform`: explicit
source environment goes to `pi-worker`, never API/migrate/Cockpit. Managed PI
roles use `PI_CONFIG_MODE=managed` to skip collector/home dotenv files.
Standalone local dotenv support remains. `PI_SNAPSHOT_INTERVAL_SECONDS` and
legacy CLI `--interval-seconds` mean pause after completion; `--pause-seconds`
is preferred. `/schedule` is an estimated next cycle start, not guaranteed data
arrival or source freshness. Keep completed/failed/successful collection and
individual source timestamp separate. Preserve accepted runtime evidence when
correcting labels/configuration; no production migration or source rerun needed.

## Exposure roadmap, not an active KPI feed

Follow `../plans/MTBF-MTTR.md`. A governed target plus stored time series is not
validated operating exposure: state rules, gaps/quality, boundaries, periods and
engineer reconciliation must be explicit. A snapshot worker's 300-second delay
is after the sequential cycle, not a five-minute freshness guarantee. Do not
add parallel requests/workers, infer missing running time or enable source auth
as a side effect of Laravel work. Check the existing acquisition owner and preserve all source guards.
