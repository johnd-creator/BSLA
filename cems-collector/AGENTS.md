# AGENTS.md — CEMS Collector

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

Read `../AGENTS.md` first. Reuse `cems-db` / database `cems_collector` / volume
`cems-db` in root Compose project `reliability-cockpit-platform`.
Managed DB port is private 5432; host 5435 belongs to the legacy standalone
container. Do not restart that container, add another DB, overwrite `.env`,
or run a local collector alongside `cems-worker`. The managed web default is
3003 and API is 8003. `cems-aggregator` owns aggregation separately from polling.

Cockpit has a configurable CEMS API base, but its CEMS projection is pending.
Do not claim that NADI already ingests emissions merely because this API works.
Preserve all normalization and operator overrides below. Source diagnostics
must not be run as an implicit effect of consumer/UI development.

## Mission

Collect CEMS (Continuous Emissions Monitoring System) readings from the
Beijer Box2Base Modbus TCP gateway (stack 1, PLTU Suralaya) into a local
contract-shaped store: raw + normalized + final values, 5-minute
aggregates, and a FastAPI read-only API for consumers — without ever
writing to the PLC.

Provenance: ported from the DAZ production collector
(`docker/sensor-collector/modbus_collector.py` + the Laravel
normalization/aggregation pipeline), restructured to follow the
maximo-collector architecture and workspace safety conventions.

## Source of Truth

1. `registry/cems-parameters.yaml` is the parameter registry — the
   collector never hardcodes register numbers. Load it into the local
   store with `cemscollector load-registry`.
2. Registry entries are `status: documented` (from the DAZ production
   config). Run `cemscollector diagnose` against the live PLC and flip
   entries to `verified` once readings are confirmed plausible.
3. Field naming follows the workspace contract conventions (vendor-neutral
   snake_case core; Modbus details quarantined under `sources.cems`).

## Mandatory Safety Rules

1. **READ ONLY against the PLC.** Only Modbus read function codes are
   exposed: FC03 `read_holding_registers` and FC04 `read_input_registers`
   (`src/adapters/modbus/client.py`, `READ_ONLY_FUNCTIONS`). Anything
   containing write/mask tokens raises `ModbusGuardError` — including
   accidental attribute pass-through to the underlying pymodbus client.
   Modbus has no authentication handshake, so unlike the maximo-collector
   there is **no write-shaped exception at all**.
2. **Register-count cap:** at most `CEMS_MAX_REGISTERS_PER_READ` (default
   and protocol maximum 125) registers per transaction.
3. **Rate limiting:** minimum pause `CEMS_MIN_REQUEST_GAP_SECONDS`
   (default 0.05 s) between any two Modbus transactions; poll interval
   floor 1 s. Both validated in `CemsConfig.validate_runtime_safety()` —
   environment values cannot weaken the floors.
4. **Single-stack scope:** `CEMS_STACK_ID` (default `1`) scopes every
   query, upsert, and API view.
5. **Never commit credentials.** The local Postgres DSN lives in `.env`
   (gitignored). No secrets exist in the Modbus path.
6. **Never brute-force registers.** The diagnostic prober only tries the
   16 documented combinations of register type × addressing × word/byte
   order for parameters whose current read is implausible (SO2/CO), with
   plausibility bounds and rate-limited logging. Anything else must be
   recorded as `status: unknown` in the registry, not guessed.
7. The collector writes only to its **own existing** Postgres store
   (`cems-db:5432` managed; host :5435 is legacy standalone only).
8. **Outbound push to the KLHK/CEMS server is intentionally absent.**
   The legacy outbound reporting job was not ported —
   this collector is read-only end to end. If reporting is ever needed it
   belongs in a separate, explicitly authorized component.

## Architecture

```text
registry/cems-parameters.yaml (15 current parameters, stack CB001)
      │ (cemscollector load-registry)
      ▼
cemscollector collect ──▶ ModbusClient (FC03/FC04 only, rate-limited,
      │                    register cap, SO2/CO self-healing prober)
      ▼
Normalizer (gas conversion → threshold clamp → state overrides →
            O2-reference correction / adjust / constant)
      │
      ▼
Postgres (contract-shaped: stack, parameter, reading_realtime,
          reading_5min, sync_cursor, collect_run)  managed cems-db:5432
      │
      ├──▶ cemscollector aggregate (5-minute windows, idempotent upserts)
      ▼
FastAPI read-only views (:8003) ──▶ Next.js dashboard (managed host :3003)
```

## Commands

These bootstrap commands describe a fresh isolated installation. They are not
the default for the current managed workspace. Reuse root Compose and existing
stores; create env files only if absent and avoid duplicate polling. Tests can
use the existing venv without starting a DB or contacting the PLC.

```bash
python3 -m venv .venv && .venv/bin/pip install -e .
[ -e .env ] || cp .env.example .env        # fresh setup only; preserve existing settings
docker compose up -d postgres             # Postgres on :5435
cemscollector init-db
cemscollector load-registry               # stacks + current parameter registry from YAML
cemscollector collect                     # continuous polling (Ctrl-C stops)
cemscollector collect --once              # single cycle
cemscollector aggregate                   # aggregate last completed window
cemscollector aggregate --start T --end T # backfill (ISO-8601)
cemscollector diagnose                    # read-only probe of every parameter
cemscollector serve                       # FastAPI on 127.0.0.1:8003
.venv/bin/python -m unittest discover -s tests   # current hermetic test suite
```

Dashboard (separate process):

```bash
cd web && npm install
CEMS_COLLECTOR_API_BASE=http://127.0.0.1:8003 npm run dev
```

## Normalization pipeline (port of DAZ LegacyNormalizationService)

Per reading: gas conversion `30.01/(0.08206·298.15)` (except O2, PM,
Laju_alir) → threshold clamp (value/threshold ≥ 2 → maintenance value) →
state overrides (negative → maintenance; stack under maintenance →
maintenance; raw O2 > 18 → maintenance on all parameters) → rounding
(Hg 5 decimals, others 3; half away from zero) → CO operational validity
(raw or normalized ≤ 0 → failed) → adjustment (O2-reference correction
`(21−ref)/(21−O2_measured)`, then factor + constant).

Maintenance values: Hg → 0.0001, everything else → 1.0.

**Normalization and operator overrides:** the configured registry is authoritative
for normalization enablement, spans, reference correction and raw passthrough.
Preserve each approved setting and the raw/final distinction. NO, NO2, CO2 and
Flow have explicit raw-passthrough behavior; do not re-enable correction or
"repair" raw values without an authorized engineering change. Validate intended
semantics against code/tests and reviewed local evidence, not comparisons copied
into public docs. Production endpoints, observed values and calibration reports
are private and are not reproduced here.

**Documented divergences from DAZ:**
- The Laravel formula-string engine (shunting-yard evaluation of
  `normalize`/`formula` fields) is replaced by explicit numeric registry
  fields (`o2_reference` / `adjust` / `constant`) — same pipeline
  semantics for everything seeded in production, no formula interpreter
  in the collector.
- The DAZ Laravel gas conversion stays implemented (pipeline stage above)
  but is disabled in the shipped registry because production does not
  apply it.
- SO2 probe plausibility lower bound is 1.0 (aligned with the probe
  trigger `value ≤ 1.0`); DAZ used 0.0 which let probes immediately
  re-accept the same implausible reading.
- Aggregation covers every parameter present in readings; the hardcoded
  KLHK seven-code list was dropped along with the push job.

## Gotchas

- **YAML 1.1 booleans:** bare `NO` / `YES` / `ON` / `OFF` parse as
  booleans. Parameter codes must be quoted in the registry; the loader
  rejects non-string codes with a hint.
- **`status` vs `collect`:** registry `status` is the workspace knowledge
  vocabulary (documented/verified/…); the operational switch is
  `collect: true|false`. `active_parameters()` filters on
  `collect_enabled`, never on the knowledge status.
- Float32 arrives as two registers; word order selects which register is
  the high word, byte order selects payload endianness. Diagnostics learn
  working combinations in memory only.
- pymodbus 3.x API (`pymodbus.client.ModbusTcpClient`), not the 2.x
  `client.sync` path used by the original DAZ script. The unit-id kwarg
  name differs across versions (`device_id`/`slave`) — resolved from the
  delegate signature at runtime.
- Learned probe overrides are process-local; to make one durable, edit the
  registry YAML and flip the parameter to `verified`.
- Standalone legacy Postgres uses host port **5435**. Managed Compose uses
  private `cems-db:5432` without a published DB port; API port is **8003**.

## Git Rules

```text
feat(modbus): read-only client guard
feat(collect): polling cycle with diagnostics
feat(api): contract-shaped views
```

Do not merge, reset, force-push, or rewrite history unless explicitly
authorized.

## Product scope

CEMS remains independent of the active NADI Laravel UI. No CEMS-to-NADI
projection or reliability failure/MTBF/MTTR interpretation is implied by a working
API. Preserve the exact normalization/operator overrides above; this documentation
refresh does not authorize diagnostic polling, deployment or formula changes.
