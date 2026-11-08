# CEMS Collector

## Konteks aktif dan operasi existing

CEMS tetap komponen independen; [NADI Laravel](../NADI/README.md) adalah UI produk
aktif tetapi proyeksi CEMS ke NADI belum dibuat. Jangan klaim emisi sudah menjadi
input reliability/MTBF/MTTR. Reuse managed `cems-db` / `cems_collector` / volume
`cems-db`; API 8003 dan dashboard 3003. Port standalone lama 5435 bukan store ini.

Ikuti [AGENTS](AGENTS.md) dan root: edit langsung checkout aktif → uji sesuai
perubahan → lihat hasil, tanpa worktree/handoff atau poller paralel. Source
collector/diagnose bukan langkah default pengembangan consumer. Contoh bootstrap
berikut hanya untuk instalasi standalone baru yang memang diminta.

Pipeline legacy tetap tersedia, tetapi registry saat ini menonaktifkan legacy
normalization dan mempertahankan verified adjustments/operator overrides.
NO/NO2/CO2/Flow tetap raw sesuai override; jangan mengaktifkan koreksi otomatis.
Status knowledge dan switch `collect` berbeda. Detail bukti/override ada di AGENTS.

Read-only CEMS Modbus TCP collector for stack 1 (PLTU Suralaya, Beijer
Box2Base gateway). The checked-in registry contains 15 emission parameters
(SO2, NOx, O2, PM, Hg, CO2, …). The collector uses Modbus FC03/FC04 only,
normalizes readings through registry-driven adjustments, aggregates 5-minute
windows, and serves a FastAPI read API. Ported
from the DAZ project and restructured to follow the maximo-collector
architecture; the outbound KLHK/CEMS push was deliberately not ported.

See `AGENTS.md` for safety rules and architecture.

## Setup standalone baru (bukan instalasi managed existing)

```bash
python3 -m venv .venv && .venv/bin/pip install -e .
[ -e .env ] || cp .env.example .env # preserve current PLC/DB settings
docker compose up -d postgres # Postgres on :5435
cemscollector init-db
cemscollector load-registry   # stack + current parameter registry from YAML
cemscollector collect         # continuous polling (or --once for one cycle)
cemscollector aggregate       # 5-minute window aggregation (or --start/--end)
cemscollector diagnose        # read-only probe of every parameter
cemscollector serve           # http://127.0.0.1:8003 (+ /docs)
.venv/bin/python -m unittest discover -s tests   # hermetic suite, no source network
```

The parameter registry lives in `registry/cems-parameters.yaml`. Entries
are `status: documented` (DAZ production values, register map 3100–3150);
after verifying readings against the live PLC via `diagnose`, flip them to
`verified`. The registry is the only place register numbers exist — the
collector never hardcodes them.

The dashboard is a separate Next.js process:

```bash
cd web && npm install
CEMS_COLLECTOR_API_BASE=http://127.0.0.1:8003 npm run dev
# Standalone dev default may be 3000; managed dashboard is 3003.
```

## API

Read-only views (vendor-neutral snake_case; Modbus details quarantined
under `sources.cems`):

- `GET /latest` — newest reading per parameter
- `GET /readings?parameter=…&status=…&since=…&until=…` — raw time-series
- `GET /readings/5min?parameter=…&since=…` — aggregates
- `GET /parameters`, `GET /stacks` — registry
- `GET /sync`-equivalents: `GET /stats`, `GET /collect-runs`, `GET /health`
- `POST /collect/once`, `POST /aggregate` — trigger local runs

All list endpoints support `offset` and `limit`. The dashboard buttons
only trigger local collection; requests to the PLC remain read-only.

## Data model

| table | contents |
|---|---|
| `stack` | monitored stacks (port of DAZ `cerobongs`) |
| `parameter` | registry rows; modbus config in `sources.cems` JSONB |
| `reading_realtime` | append-only raw/normalized/final values per poll |
| `reading_5min` | avg/min/max/count per 5-minute window (unique upsert) |
| `sync_cursor` | aggregation watermark |
| `collect_run` | per-run observability (collect + aggregate) |
