# Maximo Knowledge

## Peran dalam NADI Laravel

Ini komponen knowledge dalam monorepo BSLA, bukan aplikasi atau collector baru.
[NADI Laravel](../NADI/README.md) adalah UI aktif; data mengalir melalui Maximo
Collector → Mart → FastAPI → Laravel. Kerja solo developer langsung checkout
aktif: edit bukti/mapping → uji lokal → periksa hasil, tanpa discovery produksi
sebagai efek samping perubahan UI. Baca [AGENTS](AGENTS.md).

Bukti [failure semantics](docs/mx-015a-maintenance-failure-semantics.md) dan
[typed collector evidence](../maximo-collector/src/adapters/maximo/reliability_fields.py)
menjadi acuan roadmap [MTBF/MTTR](../plans/MTBF-MTTR.md): field teknis tidak
membuktikan event/repair/exposure. `downtime` WO adalah boolean, dan HTTP 400
Failure Code master tidak boleh disimpulkan sebagai permission denial.
Mapping dan review hierarki lokal tetap privat dan non-destructive, bukan
perubahan source hierarchy atau bagian otomatis dari clone publik.

Living knowledge base for Maximo API capabilities available to the organization.

> **Building an app on top of this data?** Read [`CONTEXT.md`](./CONTEXT.md)
> first — it is the entry point for humans and AI tools (Codex/GLM).

This repository is not an application. It is a source-intelligence layer that
records:

- API discovery results
- object structures
- fields
- relationships
- supported filters
- pagination behavior
- access limitations
- business meaning
- verified use cases
- unit-specific mappings

The first executable component is the read-only discovery CLI in
`scripts/discover.py`. It parses local OAS fixtures and, only with explicit
`--execute`, fetches an OAS document or minimal endpoint samples. Form/login
mode performs one controlled authentication POST to the exact
`/j_security_check` path, then uses GET/HEAD/OPTIONS for business resources.
It never performs business-data mutation requests.

## Suggested Discovery Seed

If available in the authorized Maximo environment, start from the OpenAPI page:

```text
/maximo/oas3/api.html
```

Do not assume every documented endpoint is authorized for the current account.

## Discovery CLI

```bash
# Parse without network access
python scripts/discover.py --oas-file openapi.json --scope reliability-core

# Enumerate OSLC object structures (read-only business GETs, requires --execute).
# Maximo exposes its real surface via /oslc/os, not the OAS paths object.
python scripts/discover.py --enumerate-oslc --execute --scope reliability-core
python scripts/discover.py --enumerate-oslc --execute --resource asset --resource workorder

# One BSR-scoped collection record plus at most one same-origin detail GET.
# Pagination and child collection references are never followed.
python scripts/discover.py --enumerate-oslc --verify-detail --execute \
  --resource IPFMEA --resource IPRCFA

# MX-006C adds resource-specific identity ranking and bounded query shaping.
# Scope/relationship fields are recorded as roles, not promoted to identity.

# Fetch from an authorized read-only environment
python scripts/discover.py --fetch-oas --execute --scope reliability-core
python scripts/discover.py --fetch-oas --execute --resource workorder

# Manual form login, then browser-session GET discovery
python scripts/session_discover.py run --scope reliability-core --verify-samples
```

Credential values belong only in local `.env`; `.env.example` contains
placeholders. Automated discovery may use an approved bearer token or the
controlled form/login mode documented in `docs/authentication.md`. Only the
authentication handshake may POST, and only to `/j_security_check`; all
business discovery remains read-only. The session CLI opens a browser and
waits for the operator to log in manually when that workflow is preferred. It
keeps the authenticated browser context only in memory and writes discovery
results to a timestamped staging run.

## Folder Guide

- `CONTEXT.md` — **entry point** for AI tools and new contributors
- `docs/` — human-readable knowledge (incl. `etl-playbook.md` for building fetchers)
- `docs/extended-application-inventory.md` — metadata inventory for Reliability, DIAMOND, DOMINION, and Efficiency Management
- `docs/mx-006r-live-verification.md` — bounded live-verification gate and matrix
- `discovery/` — machine-readable catalogs (`object-structures.json`, `objects/`, `capabilities.json`, `endpoints.json`)
- `schemas/` — JSON Schema definitions (`object.schema.json`, `endpoint.schema.json`)
- `samples/` — sanitized response examples
- `scripts/` — safe discovery helpers
- `mappings/` — organization/unit-specific semantic mappings

## Status Vocabulary

- `unknown` — not tested
- `documented` — present in docs/OpenAPI but not verified
- `verified` — tested successfully with authorized read-only access
- `forbidden` — endpoint exists but current account cannot access it
- `deprecated` — known but should no longer be used
