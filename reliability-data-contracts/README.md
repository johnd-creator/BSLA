# Reliability Data Contracts

## Konteks aktif NADI Laravel

Kontrak ini dipakai collector/Mart, backend FastAPI dan consumer NADI Laravel.
UI aktif ada di [NADI](../NADI/README.md); Next.js lama bukan target produk baru.
Kerja langsung di checkout aktif mengikuti [AGENTS root](../AGENTS.md): edit,
uji schema/consumer yang terdampak, periksa hasil. Schema tersedia tidak berarti
workflow, sumber atau metrik sudah terimplementasi/tervalidasi.

Untuk MTBF/MTTR, gunakan [roadmap evidence](../plans/MTBF-MTTR.md). Failure code
bukan failure occurrence; actual WO elapsed/labor bukan repair duration;
`downtime` MXWODETAIL yang terverifikasi adalah boolean, bukan jam. WO-only KPI
legacy tetap null/NOT_READY. Vendor evidence internal tidak otomatis boleh
keluar dalam DTO NADI.

Vendor-neutral semantic contracts used by reliability applications.

The purpose is to prevent application code from becoming tightly coupled to
Maximo or PI. Application domain models consume these contracts; vendor-specific
field names live only in the `sources.maximo` / `sources.pi` blocks.

## Source of truth

Field mappings are verified against `maximo-knowledge` (site BSR, org IP) and
`pi-knowledge` (site BSR, unit BSR1). See
[`mappings/maximo-to-contracts.md`](./mappings/maximo-to-contracts.md) and
[`mappings/pi-to-contracts.md`](./mappings/pi-to-contracts.md) for the
field-by-field translation tables.

## Schemas

### Maximo source contracts (site BSR)

Verification refers to documented source/field evidence, not complete collection
or validated failure semantics. Use the current knowledge catalogs for coverage.
Historical field counts are not a runtime completeness contract.
| Schema | Maximo source | Status |
|---|---|---|
| [`equipment.schema.json`](./schemas/equipment.schema.json) | MXAPIASSET preferred; MXASSET historical | ✅ verified |
| [`work-order.schema.json`](./schemas/work-order.schema.json) | MXWODETAIL | ✅ verified |
| [`service-request.schema.json`](./schemas/service-request.schema.json) | MXAPISR | ✅ verified |
| [`person.schema.json`](./schemas/person.schema.json) | MXPERSON | ✅ verified |
| [`item.schema.json`](./schemas/item.schema.json) | MXITEM | ✅ verified |
| [`labor.schema.json`](./schemas/labor.schema.json) | MXAPILABOR | ✅ verified |

### Vendor-neutral source
| Schema | Source | Status |
|---|---|---|
| [`condition-parameter.schema.json`](./schemas/condition-parameter.schema.json) | pi-knowledge registry YAML via pi-collector | ✅ verified (v2, breaking rename 2026-08) |
| [`condition-reading.schema.json`](./schemas/condition-reading.schema.json) | PI Web API streams via pi-collector | ✅ verified (snapshot + timeseries) |
| [`emission-reading.schema.json`](./schemas/emission-reading.schema.json) | CEMS collector | documented; live registry verification required |
| [`collector-run.schema.json`](./schemas/collector-run.schema.json) | collector runtime audit | implemented contract |

### Cockpit decisions and computed presentation
| Schema | Purpose | Status |
|---|---|---|
| [`asset-source-link.schema.json`](./schemas/asset-source-link.schema.json) | verified cross-source asset identity | contract ready; no unverified links seeded |
| [`condition-finding.schema.json`](./schemas/condition-finding.schema.json) | explainable finding | contract ready |
| [`recommendation.schema.json`](./schemas/recommendation.schema.json) | proposed action and workflow state | contract ready |
| [`asset-health-snapshot.schema.json`](./schemas/asset-health-snapshot.schema.json) | versioned calculated score/presentation | contract ready; formulas pending approval |

### Computed reliability concepts (derived, not a direct source field)
| Schema | Derived from |
|---|---|
| [`failure.schema.json`](./schemas/failure.schema.json) | Classification evidence only; governed occurrence/deduplication pending; latest master collection HTTP 400 is not an access-denial verdict |
| [`downtime.schema.json`](./schemas/downtime.schema.json) | Requires verified elapsed downtime intervals; WO boolean downtime and unverified legacy totals are not eligible hours |
| [`location.schema.json`](./schemas/location.schema.json) | location_id on Equipment/WO/SR (MXAPILOCATION ⛔ forbidden) |
| [`maintenance-event.schema.json`](./schemas/maintenance-event.schema.json) | WO maintenance evidence; actstart/actfinish describe execution and actlabhrs effort, not a validated failure or MTTR |
| [`reliability-kpi.schema.json`](./schemas/reliability-kpi.schema.json) | Formula/transport contract; WO-only MTBF/MTTR/availability NOT_READY, PM compliance retains its separate basis |

## Catalog examples

- [`catalog/equipment.example.yaml`](./catalog/equipment.example.yaml)
- [`catalog/work-order.example.yaml`](./catalog/work-order.example.yaml)
- [`catalog/condition-parameter.example.yaml`](./catalog/condition-parameter.example.yaml)

## Core concepts

Equipment · Location · WorkOrder · MaintenanceEvent · Failure ·
ConditionParameter · Alarm · Downtime · ReliabilityKPI

## NADI Reliability Canonical Contract v1

The explicit Reliability Mart boundary is documented in
[`docs/nadi-reliability-canonical-contract-v1.md`](./docs/nadi-reliability-canonical-contract-v1.md).
It defines `asset_master`, `maintenance_event`, `fmea_assessment`,
`rcfa_analysis`, `asset_health_assessment`, and `overhaul_event`. The machine-
readable Maximo mappings, relationship graph, and deferred registry are:

- [`mappings/maximo-nadi-reliability.json`](./mappings/maximo-nadi-reliability.json)
- [`catalog/nadi-reliability-relationship-graph.json`](./catalog/nadi-reliability-relationship-graph.json)
- [`catalog/nadi-reliability-deferred.json`](./catalog/nadi-reliability-deferred.json)

The v1 schemas are [`asset-master.schema.json`](./schemas/asset-master.schema.json),
[`fmea-assessment.schema.json`](./schemas/fmea-assessment.schema.json),
[`rcfa-analysis.schema.json`](./schemas/rcfa-analysis.schema.json),
[`asset-health-assessment.schema.json`](./schemas/asset-health-assessment.schema.json),
[`maintenance-event.schema.json`](./schemas/maintenance-event.schema.json), and
[`overhaul-event.schema.json`](./schemas/overhaul-event.schema.json).

These v1 contracts preserve Maximo identifiers under `sources.maximo` and
provenance. Scope fields (`siteid`, `orgid`) and relationship fields
(`assetnum`, `wonum`) are not record identities. The existing runtime schemas
remain readable and are not replaced by the canonical design document.

## Rules (see AGENTS.md)

1. Do not copy vendor-specific payloads into core contract fields.
2. Preserve source-system identifiers under `sources`.
3. Prefer stable organization-owned IDs where available.
4. Document units explicitly. Use ISO-8601 timestamps.
5. Mark nullable/unknown fields intentionally.
6. Breaking schema changes require a version bump.

### Governed condition evidence foundation (NADI-ING-PI-001A candidate)

`condition-evidence.schema.json`, `condition-signal-selection.schema.json` and
`condition-projection-plan.schema.json` are additive contracts for selected,
governed latest evidence. Synthetic examples live in `examples/condition-evidence/`.
They preserve numeric/text/digital/boolean/null and explicit quality/timestamps;
source identifiers stay under `sources.pi`. They do not replace the legacy
technical `condition-reading` contract, imply production mappings, or define
health/reliability scores. See [foundation acceptance](../reliability-cockpit/docs/nadi-ing-pi-001a.md).

### Engineering Case candidate contract (Phase 2)

[engineering-case.schema.json](schemas/engineering-case.schema.json) is generated
from the typed EngineeringCase v1.0 model. It describes attributed human
investigation, independent review, revisions and bounded canonical evidence
references. Hypotheses and human priority are not source facts or risk scores.
Condition snapshots reuse the canonical condition-evidence shape with PI identity
under sources.pi. Fixtures are synthetic; no production case migration or write
endpoint is activated. See [Engineering ADR](../reliability-cockpit/docs/adr/006-engineering-workspace.md).


## Phase 2 Bundle B candidate contracts

The existing generic recommendation contract is preserved. These candidate schemas are generated from the strict application domain models and exercised only with synthetic/isolated persistence:

| Schema | Purpose | Readiness |
|---|---|---|
| [`manual-inspection.schema.json`](schemas/manual-inspection.schema.json) | Human measurement envelope; original values/units/timestamps and separate interpretation | Candidate; engineer field approval pending |
| [`engineering-recommendation.schema.json`](schemas/engineering-recommendation.schema.json) | Independently reviewed NADI proposal, local follow-up, exact case/evidence/existing-WO references | Candidate; never a Maximo WO or maintenance authorization |
| [`existing-work-order-reference.schema.json`](schemas/existing-work-order-reference.schema.json) | Bounded informational canonical WO identity/status/provenance | SELECT-only local reference; no source command |

Structural/nonblank constraints are in JSON Schema. Cross-field chronology, lifecycle authorization, identity resolution and review independence remain authoritative server-domain/service validation. See the [Bundle B acceptance report](../reliability-cockpit/docs/nadi-phase2-bundle-b.md). No production application activation or source write is authorized.
