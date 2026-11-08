# PI Collector

## Existing workspace, bukan bootstrap ulang

Komponen ini tetap independen dari [NADI Laravel](../NADI/README.md), UI aktif
BSLA. Reuse managed `pi-db` / `pi_collector` / volume `pi-db`; API 8001,
dashboard 3002. Jangan memakai Cockpit DB atau menjalankan database/worker baru.
[AGENTS](AGENTS.md) dan [runbook root](../deploy/compose/README.md) mengalahkan
contoh standalone di bawah untuk instalasi existing.

Jangan retry authentication atau mengubah collection tanpa permintaan yang
mencakup tindakan tersebut. Periksa ownership worker yang sudah berjalan.
Stored data tetap dapat dibaca dengan age/quality jujur; NK memakai API tanpa DB
sendiri. Proyeksi PI/historian NADI belum aktif. Roadmap
[MTBF/MTTR](../plans/MTBF-MTTR.md) membutuhkan mapping/state/exposure tervalidasi,
bukan jam kalender atau technical registry saja.

Cara kerja solo developer: edit langsung checkout aktif → test yang terdampak →
periksa hasil. Tidak perlu worktree/handoff/collector paralel. Perintah setup,
collection, scheduler dan backfill di bawah adalah referensi opt-in untuk
instalasi/operasi yang diminta, bukan checklist development rutin.

Time-series data collector for PI Web API (AVEVA/OSIsoft). Pulls verified
attributes into a local TimescaleDB store and serves them via REST API to
multiple consumers: trending dashboards, ML feature pipelines, and the
reliability cockpit.

## Design Principles

1. **Read-only against PI** — GET/HEAD/OPTIONS only, enforced in code.
2. **Knowledge-driven** — the technical registry of attributes to collect comes
   from `pi-knowledge`, never hardcoded. It is not a governed Asset mapping.
3. **Time-series optimized** — TimescaleDB hypertable for efficient range
   queries and aggregation at scale.
4. **Multi-consumer** — clean REST API, no vendor payloads escape the layer.

## Architecture

```text
DCS / control systems
        │
        ▼ existing acquisition / OPC / PI Interface pipeline
Central PI Data Archive + AF
        │
        ▼ PI Web API / AF (Basic auth, runtime-only credentials)
PiClient (GET/HEAD/OPTIONS, same-origin only)
        │
        ├── technical collection mode ──▶ local pi_snapshot/pi_timeseries
        │                                  (trending and ML consumers)
        │
        └── governed source boundary ◀── VERIFIED Asset ↔ AF target supplied
                                         by future NADI orchestration
```

The broad `pi-knowledge/mappings/bsr1-parameters.yaml` inventory contains 541
technical attributes, including 433 stream-ok entries. It is a technical
collection registry, not a list of governed reliability signals:

```text
TECHNICAL_PI_ATTRIBUTE != GOVERNED_ASSET_SIGNAL
```

PI Vision is a visualization surface, not the ingestion API. The governed boundary
does not crawl the AF hierarchy or infer Asset identity from names, tags, or
similarity. Existing raw registry identifiers are pre-existing technical debt;
this work adds no new production WebIds or tags.

## Setup

### Prerequisites

| Tool | Version |
|---|---|
| Python | ≥ 3.11 |
| Docker | any (for TimescaleDB) |

### Managed versus standalone configuration

Managed Power Plant Data Platform uses **`.env.platform`** with Compose
substitution as its configuration authority. Only `pi-worker` receives the
explicit PI source URL/auth/timeout/rate/cap/TLS settings. `pi-api` receives
non-secret post-cycle pause metadata only; `pi-migrate` and Cockpit receive no
PI source configuration. Managed PI roles use `PI_CONFIG_MODE=managed` and do
not read `pi-collector/.env` or `~/.pi-collector.env`.

Standalone development continues to allow those local dotenv files. The
installation examples below are standalone; do not create a second dotenv
file or database for a managed deployment, and do not copy example files over
existing operational secrets.

### Install

```bash
cd pi-collector
python3 -m venv .venv
.venv/bin/pip install -e .          # installs the `picollector` CLI
cp .env.example .env                # fill PI credentials + DATABASE_URL
```

`PI_WEB_API_BASE_URL` is required for live source operations and must be
provided as a runtime value. `PI_VERIFY_TLS` defaults to `1`. The currently
instance-verified authentication mode is Basic auth via `PI_USERNAME` and
`PI_PASSWORD`; credentials are never logged, persisted, or returned by the
collector. Bearer configuration remains compatibility-only and is not claimed
as verified for the current instance.

### Start TimescaleDB

```bash
docker-compose up -d postgres       # TimescaleDB on port 5433
```

For the managed platform, use the existing `pi-db` / `pi_collector` database
and volume. Do not repoint PI tables into the Cockpit store or create another DB.
The standalone setup above is for a separate fresh development installation.

### First run

```bash
.venv/bin/picollector init-db              # create tables + hypertable
.venv/bin/picollector load-registry        # load 433 stream-ok attributes from the 541-attribute registry
.venv/bin/picollector collect-snapshots    # fetch current values
.venv/bin/picollector backfill --start "*-7d" --end "*" --interval 1h  # 7-day history
```

### Upgrade an existing store

`init-db` does not alter existing columns. Use deliberate `picollector migrate`
(read-only status) and `picollector migrate --apply` only after backup, schema
preflight and acquisition quiescence. The runner tracks ordered SQL checksums
in the existing PI store; it never calls PI or creates a database. Managed
Compose exposes opt-in `pi-maintenance` and `pi-collection` profiles; the worker
uses `picollector worker` for a single DB lease and snapshot-only scheduling.
See [operator runbook](docs/runtime-migrations.md) and
[actual runtime evidence](docs/nadi-pi-runtime-001.md) for accepted image pins,
overrides and limitations. Do not start a second cron/systemd/manual collector.

### Download ALL historical data (recorded)

```bash
# Full raw history — only runs during off-hours (22:00-06:00 + weekend)
.venv/bin/picollector backfill-recorded --start "2024-01-01T00:00:00Z" --end "*"

# Single attribute (resumes where it stopped — upserts are idempotent)
.venv/bin/picollector backfill-recorded --start "2024-01-01T00:00:00Z" --attribute BSR-BSR1-turbine-...

# Emergency override of the off-hours gate (use with caution!)
.venv/bin/picollector backfill-recorded --start "*-30d" --end "*" --force
```

### Continuous collection (serial cycle plus 300s pause)

```bash
# Snapshot mode: serial acquisition, then 300s pause after completion
.venv/bin/picollector run --mode snapshot --pause-seconds 300

# Recorded-delta mode: fetch new raw points since the last cursor
.venv/bin/picollector run --mode recorded-delta --interval-seconds 300
```

`PI_SNAPSHOT_INTERVAL_SECONDS` remains a compatible environment name for
**post-cycle pause**; omitted CLI pause uses it (default 300). The explicit
`--pause-seconds` and old `--interval-seconds` flags accept identical values.
Measured acquisition 508.142s + configured pause 300s gives approximately
808.142s start-to-start (~13.5 minutes), with no parallel polling or lower
request spacing. CLI overrides should match API pause configuration when
running a standalone custom schedule.

`GET /schedule` estimates the **next cycle start** from the latest cycle's
completion + pause. It preserves `interval_seconds` as a compatibility alias
and adds `pause_seconds`, `last_cycle_duration_seconds`, estimated
`effective_start_to_start_seconds`, and `latest_collection_activity_at`.
Countdown is suspended during inferred active writes; an expired estimate
means waiting for activity, not guaranteed data arrival. Cron/manual runs and
worker ownership cannot be certified from stored writes alone.

Freshness concepts remain separate: acquisition duration; post-cycle pause;
estimated start-to-start cadence; latest completed cycle (`last_run_at`, which
can include failures); latest **successful** collection (verify run outcomes,
rows/errors/aborted); and each reading's **source_timestamp**. Recent collection
can store an old source value—the accepted canary returned an epoch timestamp.
Do not declare a signal fresh or Good solely because acquisition ran recently.

### Serve

```bash
.venv/bin/picollector serve                # API on http://127.0.0.1:8001
```

Swagger docs: `http://127.0.0.1:8001/docs`

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Health check |
| `/attributes` | GET | List registered attributes (`?equipment=&parameter=`) |
| `/snapshots` | GET | Latest values (`?equipment=&limit=`) |
| `/snapshots/{id}` | GET | Latest value of one attribute |
| `/timeseries/{id}` | GET | History (`?start=&end=&limit=`) |
| `/heatmap/{id}` | GET | Daily data coverage (GitHub-style) |
| `/collect/snapshots` | POST | Trigger snapshot collection |
| `/collect/backfill` | POST | Trigger backfill (`?start=&end=&interval=`) |
| `/stats` | GET | Collection statistics |
| `/schedule` | GET | Observed activity and estimated next cycle start; no source-freshness certificate |

The API serves locally collected data. It is not a live PI proxy and does not
accept arbitrary WebIds or URLs. The existing collection trigger routes only
start the configured local collector modes; they do not create governed
Asset↔AF mappings.

## Governed source boundary

`src/domain/governed.py` defines `GovernedAfTarget`. The
`GovernedSourceBoundary` accepts only an explicit target with:

- `mapping_status=VERIFIED`
- `mapping_role=PRIMARY_EQUIPMENT`
- `pi_source_id=CENTRAL_PI`

`PROPOSED`, `RETIRED`, `UNMAPPED`, and `AMBIGUOUS` targets are rejected. The
boundary reads one AF Element, at most 100 direct Attributes, Attribute
metadata, a linked current value, or a bounded recorded window of at most 20
samples. It does not read or write the Reliability Mart and does not discover
Asset↔AF relationships.

See [boundary and upgrade details](docs/governed-source-boundary.md) and
[offline implementation evidence](docs/nadi-pi-001-implementation.md).
Existing stores need migration `004_signal_quality_fields.sql` before this code
is started; `init-db` does not alter existing columns. No migration was applied
by NADI-PI-001 or FIX-01. The PI migration order is:

```text
001_init.sql
002_collect_runs.sql
003_backfill_progress.sql
004_signal_quality_fields.sql
```

If an experimental `002_signal_quality_fields.sql` was applied outside main,
final `004` remains safe: guarded `ADD COLUMN IF NOT EXISTS` additions keep
existing columns/data and add any missing quality fields. This does not imply
that the production migration has been executed.

The normalized local signal retains `source_value`, the source timestamp, numeric/text/digital
value classification, engineering unit, and the PI `Good`, `Questionable`,
`Substituted`, and `Annotated` flags. A digital state remains non-numeric;
quality is source evidence and is not interpreted as an alarm, failure, or
diagnosis.

## Safety guardrails (bulk downloads)

`backfill-recorded` is the heaviest operation — it downloads every raw point.
To protect the PI server from being overwhelmed or blocking the account, the
following layers are enforced in code (all configurable via `.env`):

| Layer | Default | Env var |
|---|---|---|
| Rate limit (per request) | 1 req/s | `PI_RATE_LIMIT_SECONDS` |
| Response size cap | 1 MiB | `PI_MAX_RESPONSE_BYTES` |
| **Off-hours gate** — aborts if run outside 22:00–06:00 or weekends | 22–06 + Sat/Sun | `PI_OFF_HOURS_START/END`, `PI_OFF_HOURS_WEEKEND` |
| **Circuit breaker** — hard stop after N requests per session | 5000 | `PI_MAX_REQUESTS_PER_SESSION` |
| **Consecutive error abort** — stop if PI fails 10 times in a row | 10 | `PI_MAX_CONSECUTIVE_ERRORS` |
| **Time-window chunking** — split ranges into 7-day windows | 7 days | `PI_BACKFILL_CHUNK_DAYS` |
| **Inter-attribute pause** — 2s cooldown between attributes | 2.0s | `PI_PAUSE_BETWEEN_ATTRIBUTES` |

Resumability: all inserts are idempotent upserts (by attribute_id + timestamp).
If a run aborts (circuit breaker, errors), re-running the same command resumes
from where it stopped — no duplicates, no lost data.

## Scheduling (night + weekend)

Ready-made units in `deploy/`:

```bash
# systemd (recommended for servers)
sudo cp deploy/pi-collector-backfill.{service,timer} /etc/systemd/system/
sudo systemctl enable --now pi-collector-backfill.timer   # nightly 22:15 + weekend
sudo systemctl enable --now pi-collector-snapshot.service  # continuous 5-min snapshots

# cron alternative — see deploy/crontab.example
crontab -e   # paste the lines, adjust paths
```

The timer/cron only **trigger** the run; the in-app off-hours gate remains the
final authority (a stray daytime cron entry still aborts safely).

## Tests

```bash
.venv/bin/python -m unittest discover -s tests
```

## Project structure

```
src/
├── cli.py                      # picollector CLI (7 commands)
├── config.py                   # PiApiConfig, DbConfig, CollectSafetyConfig
├── adapters/pi/client.py       # PiClient (GET-only, rate-limit, pagination)
├── domain/models.py            # normalized PI readings and registrations
├── domain/governed.py          # validated NADI Asset↔AF target boundary
├── repositories/
│   ├── database.py             # SQLAlchemy engine + TimescaleDB hypertable
│   ├── models.py               # ORM models
│   └── store.py                # CollectorStore (upsert/query/heatmap)
├── services/
│   ├── registry.py             # parse pi-knowledge YAML → registrations
│   ├── collector.py            # technical collection engine + safety gates
│   └── governed_source.py      # AF-linked reads for validated targets
└── api/app.py                  # FastAPI consumer endpoints
web/                            # Next.js UI (attribute list, heatmap, collect buttons)
deploy/                         # systemd timer/service + cron examples
tests/                          # hermetic tests, including temporary SQLite storage
```
