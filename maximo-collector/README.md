# Maximo Collector

Read-only Maximo OSLC collector for site BSR. Auto-login (programmatic
`j_security_check`), GET-only data requests, delta sync via `changedate` /
`statusdate` watermarks, contract-shaped local Postgres store, and a FastAPI
read-only API for consumers such as the reliability cockpit. The verified
`mxapiasset` structure is the preferred equipment source; its additional
scalar fields are retained under `sources.maximo.extra`.

See `AGENTS.md` for safety rules and architecture.

## Quick start

```bash
python3 -m venv .venv && .venv/bin/pip install -e .
cp .env.example .env          # fill MAXIMO_USERNAME / MAXIMO_PASSWORD
docker compose up -d postgres # Postgres on :5434
mxcollector init-db
mxcollector sync              # WO/SR and operational master data
mxcollector sync mxapiasset   # explicit asset baseline/status refresh
mxcollector backfill          # cursor-independent, idempotent BSR WO traversal
mxcollector diagnose master-data # GET-only probe for Persons, Items, Labor
mxcollector serve             # http://127.0.0.1:8002 (+ /docs)
```

The master-data sync uses verified scopes: Persons `locationorg="IP"`, Labor
`worksite="BSR"`, and Items `site="BSR"`. Person, Item, and Labor rows are
written in batches to the local Postgres store. If the diagnostic reports
`mxitem: zero_rows`, do not broaden the query by guesswork; verify the Item
object’s live site/item-set scope in `maximo-knowledge` first.

`mxcollector backfill` never advances the incremental `mxwodetail` cursor. It
uses the verified `siteid="BSR"` scope, follows Maximo’s server-provided
`oslc:nextPage`, and returns a non-zero partial result when its configurable
page cap is reached. A rerun is safe because work orders are upserted by
`wonum`; do not treat a page-cap result as complete. The legacy `like`
wildcard predicate is not used because this Maximo instance returns
`BMXAA8744E` for it (and for the unsupported incremental date comparator on
`mxwodetail`).

The dashboard is a separate Next.js process:

```bash
cd web && npm install
MAXIMO_COLLECTOR_API_BASE=http://127.0.0.1:8002 npm run dev
# open http://127.0.0.1:3000
```

## API

Read-only views whose field names follow `reliability-data-contracts`:

- `GET /equipment?changed_since=…`
- `GET /equipment/{asset_id}/status-history`
- `GET /work-orders?changed_since=…`
- `GET /service-requests?changed_since=…`
- `GET /persons?status=…&location_org=…&q=…`
- `GET /items?status=…&item_type=…&issue_unit=…&order_unit=…&q=…`
- `GET /labor`
- `GET /labor?status=…&work_site=…&person_id=…&q=…`
- `GET /sync/status`, `GET /health`
- `GET /stats`, `GET /collect-runs`
- `POST /sync/{object}` — trigger one object's sync

All list endpoints support `q`, `offset`, `limit`, and optional
`changed_since` / `changed_until` where the resource has a source watermark.

Vendor identifiers are quarantined under `sources.maximo`.
The dashboard's sync button only triggers the local collector; business data
requests to Maximo remain GET-only.

## Typed reliability evidence

Allowlisted work-order reliability observations retain identity, field state and
observation version. Missing, invalid and unknown clocks remain explicit; parent
and origin identifiers do not imply resolved relationships. `downtime` is a
boolean indicator, never a repair-duration value. Failure classification is not
a governed failure occurrence or a valid MTBF denominator. The local projector
revalidates retained evidence and does not contact production.

Offline coverage is in `tests/test_reliability_evidence.py` and the projector
regressions under `deploy/compose/release_tests`. Operational evidence, source
samples and local repairs are not shipped or performed by this release.
