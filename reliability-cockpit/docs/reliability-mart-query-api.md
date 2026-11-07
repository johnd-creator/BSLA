# NADI Reliability Mart Query API v1

MX-010R adds a read-only, vendor-neutral query surface to the existing
Reliability Cockpit FastAPI application. MX-012R keeps the six canonical Mart
tables and adds the current `reliability_asset_registry` projection; it does
not call Maximo, start a collector, or copy Mart data into the legacy Cockpit
store.

## Architecture and database boundary

```text
Maximo → CanonicalCollector → MartWriter → Reliability Mart PostgreSQL
                                      ↓
                         MartQueryRepository (SELECT only)
                                      ↓
                         ReliabilityQueryService
                                      ↓
                         /v1/reliability (FastAPI)
```

The legacy Cockpit database remains configured by `DATABASE_URL`. The Mart
reader uses the separate `RELIABILITY_MART_DATABASE_URL`; it intentionally has
no fallback to the legacy DSN. Deployment should use a database role with
read-only grants. PostgreSQL transactions are marked `READ ONLY` and receive a
bounded statement timeout. The application query facade exposes no
`insert`/`update`/`delete`/`commit` API.

If the Mart DSN is absent or unavailable, Mart routes return HTTP 503 while the
legacy Cockpit routes can continue to serve their existing data.

## Public route catalog

All routes are GET-only and use canonical reliability concepts:

| Route | Purpose |
| --- | --- |
| `GET /v1/reliability/assets` | Bounded asset list with status, unit, and type filters |
| `GET /v1/reliability/registry` | Aggregate current Registry snapshot metadata |
| `GET /v1/reliability/decision-overview?window_days=30` | Bounded Executive Overview aggregates; `window_days` is 7, 30, or 90 |
| `GET /v1/reliability/asset-health/overview` | Factual Asset Health population, raw status, relationship, and record-recency aggregates |
| `GET /v1/reliability/fmea/overview` | Factual FMEA population, raw status/revision, relationship, Failure Code, and record-recency aggregates |
| `GET /v1/reliability/rcfa/overview` | Global factual RCFA population, raw status/category/revision, and record-recency aggregates; relationships remain unresolved |
| `GET /v1/reliability/overhauls/overview` | Factual Overhaul population, Work Order Mart resolution, Asset-path resolution, dates, progress availability, and raw status |
| `GET /v1/reliability/assets/{canonical_id}` | Asset detail |
| `GET /v1/reliability/assets/{canonical_id}/context` | Bounded asset context: maintenance, FMEA, health, and overhaul |
| `GET /v1/reliability/assets/{canonical_id}/fmea` | Paginated FMEA assessments for an asset |
| `GET /v1/reliability/assets/{canonical_id}/health-assessments` | Paginated health assessments for an asset |
| `GET /v1/reliability/assets/{canonical_id}/health/latest` | Latest health assessment using the documented timestamp fallback |
| `GET /v1/reliability/assets/{canonical_id}/timeline` | Bounded reliability timeline |
| `GET /v1/reliability/assets/{canonical_id}/pi-mapping` | Governed Maximo Asset to PI AF mapping state and safe AF reference metadata |
| `GET /v1/reliability/maintenance-events` | Maintenance event list and filters |
| `GET /v1/reliability/fmea` | Registry-scoped FMEA list with FMEA number, Asset number, source status, and source Failure Code filters |
| `GET /v1/reliability/asset-health` | Registry-scoped Asset Health list with Asset number, description, status, and pagination filters |
| `GET /v1/reliability/rcfa` | Global RCFA list with number, status, category, pagination, and no Asset/Work Order filters |
| `GET /v1/reliability/overhauls` | Overhaul list with Overhaul Number, source Work Order number, lifecycle status, bounded filters, and relationship states |
| `GET /v1/reliability/data-trust` | Aggregate population, domain maturity, relationship readiness, and semantic readiness evidence; no trust score |
| `GET /v1/reliability/integrity` | Aggregate logical-reference health counts |

List responses contain `items` and `meta` (`total`, `offset`, `limit`, and
`has_more`). Defaults are 50 records and the maximum is 200. Sort values are
allowlisted per resource; arbitrary SQL column names are never accepted.

The Data Trust route is aggregate-only and keeps the business Asset Registry,
technical `asset_master` context, local Collector projection, and controlled
Mart populations distinct. Latest domain dates are source-record evidence, not
sync freshness; `sync_freshness` remains `NOT_AVAILABLE` without a permitted
Collector operational-metadata dependency.

## Scope and provenance safety

The reader applies `site_code = BSR` and `organization_code = IP` in every
query. Public site and organization parameters, where present, are literal
validated values and cannot be used to request another site. This is defense
in depth after the Collector and Mart writer scope guards.

Normal `/assets` and global Maintenance views join the current Registry
relation. Technical `asset_master` rows outside that relation remain Mart
context and are not normal NADI Assets. Maintenance date filters and sorting
use `COALESCE(actual_start, source_changed_at)` because local Collector history
may not retain actual start timestamps.

Normal product DTOs expose canonical fields, scope, contract version, and
selected source timestamps. They do not expose `sources.maximo`, full
provenance, relationship JSON, raw OSLC responses, credentials, or database
state.

## Relationships and context

The following are safe canonical joins:

```text
fmea_assessment.asset_ref
asset_health_assessment.asset_ref
maintenance_event.equipment_id
overhaul_event.asset_ref (when populated)
        ↓
asset_master.canonical_id
```

Overhaul-to-maintenance joins use:

```text
overhaul_event.workorder_ref = maintenance_event.work_order_id
```

They never join to `maintenance_event.canonical_id`, and the reader does not
assume `work_order_id` is unique. RCFA asset, location, and Work Order
relationships are unresolved in Contract v1, so RCFA is not attached to an
asset context or timeline. The context response reports
`rcfa_relationship_status: UNRESOLVED`.

Overhaul source Work Order identity is read from the approved
`sources.maximo.wonum` value when present. The API exposes separate factual
states for a source Work Order that is locally resolved, a source Work Order
whose local Mart row is absent, and a missing source Work Order. The Asset
link is never created by the query layer: an existing `asset_ref` is checked
against `asset_master` and the Registry, reflecting the verified
`IP_DOM_OH.wonum -> MXWODETAIL.wonum -> MXWODETAIL.assetnum` path.

Asset context uses a fixed small section limit (five by default, capped at ten)
and does not return full child history. Unresolved Overhaul rows remain
available through `/overhauls`, but cannot enter an asset timeline without a
populated asset reference.

## Timeline semantics

The timeline contains only `MAINTENANCE`, `FMEA`, `ASSET_HEALTH`, and resolved
`OVERHAUL` events. It is newest-first, bounded by the same 50/200 limits, and
uses these timestamp fallbacks:

* maintenance: `actual_start`, then `source_changed_at`;
* FMEA: `status_changed_at`, then `source_updated_at`;
* health: `status_changed_at`, then `source_updated_at`, then `source_created_at`;
* overhaul: `actual_start_at`, then `planned_start_at`, then `source_updated_at`.

No health score, MTBF, MTTR, or other analytics are calculated here.

## Governed Maximo Asset to PI AF mapping

PI Asset Framework is a verified downstream source boundary, but the bounded
PI discovery did not find a native Maximo Asset → AF identity key:
`NATIVE_MAXIMO_AF_MAPPING: NOT_FOUND_BOUNDED`. The NADI-owned
`asset_af_mapping` relation is therefore the explicit governance boundary. It
is stored in the existing Reliability Mart database and references the
canonical `asset_master.canonical_id`; it is not a second Asset master and is
never written back to Maximo or PI.

The registry has `PROPOSED`, `VERIFIED`, and `RETIRED` lifecycle states and
never treats a proposal as usable identity. Only one `VERIFIED`
`PRIMARY_EQUIPMENT` row resolves an Asset to `MAPPED`; zero resolves to
`UNMAPPED`, and more than one resolves to `AMBIGUOUS` without silently choosing
an AF Element. The public route is read-only. Registry commands are internal
administration boundaries only; this task adds no browser form, anonymous write
endpoint, production seed, PI request, or fuzzy/name-based fallback.

The generic `asset-source-link` contract remains unchanged. Its source-link
vocabulary does not carry the AF server/database, mapping role, lifecycle, and
evidence fields required by this governed relation, so the registry remains a
Mart-internal cross-source relation until a future contract task establishes a
vendor-neutral extension.

## Controlled mapping administration

The internal workflow is documented in
[`asset-af-mapping-admin.md`](./asset-af-mapping-admin.md). It is deliberately
separate from this public read-only API:

```text
controlled CSV
     ↓
  DRY RUN
     ↓
 validation
     ↓
 PROPOSED
     ↓
human verification
     ↓
 VERIFIED
     ↓
usable mapping
```

`cockpit mapping import --file <csv> --dry-run` parses and validates a bounded
candidate batch without database writes. The same command without `--dry-run`
persists the complete batch atomically as `PROPOSED`; it never accepts a
status column and never creates a `VERIFIED` row. Verification and retirement
are separate internal commands requiring an explicit human actor and evidence
or reason. No command performs a PI request or a fuzzy/name/tag match.

The public `GET /v1/reliability/assets/{canonical_id}/pi-mapping` route remains
the only mapping HTTP route. It exposes safe evidence method and verification
timestamp fields, while verification notes, evidence references, and actor
identities remain administrative fields.

## Legacy coexistence and handoff

Existing `/equipment`, `/work-orders`, `/kpis/...`, `/sync/status`, and
`/health` routes remain unchanged and continue to use the legacy Cockpit store.
The new query layer is a separate read path. It contains no Maximo client or
collector control endpoint and does not perform a production load.

MX-011R can use these APIs after a controlled initial Mart load. That task may
configure deployment credentials and operational readiness; it must not require
an API redesign or knowledge of Maximo object-structure names.

## Laravel read-only integration

The additive inventory APIs distinguish collected hierarchy membership from
governed Registry membership. Exact asset inventory reads and their WO histories
do not register assets, acquire source records or write to source stores. Annual
WO comparison uses explicit asset/population scope, unique WO identity and actual
start-year buckets; unknown dates remain separate. Counts are records, not
validated incidents, reliability scores or operating availability.

Maintenance DTOs retain reviewed classification and allowlisted source detail.
The added description is a scalar only. Final duration is recomputed exclusively
for CLOSE with two valid explicit-zone actual timestamps; unknown, naive, reversed
or incomplete clocks produce no duration. A legitimate equal timestamp pair is
zero. Non-CLOSE has no final actual pair or final elapsed duration. Stored labor,
downtime, report/schedule/status dates and old duration values are not substitutes.

Overview responses add daily evidence, time-zone and counting-basis fields.
Legacy DTO payloads may omit these additive fields; omission remains unknown.
Record-change counts are not physical maintenance work. Existing integration,
classification, scoped-read and source-detail routes remain available. No runtime
activation or source-data publication is implied.
