# NADI-WO-DETAIL-ENHANCEMENT-01

2 November 2026. Development candidate stacked on Draft PR119 at
`119ba2f1472facedd71433d65b74f3b7d64a6434`. Implementation and synthetic
qualification are separate from activation and owner acceptance. Operational
identifiers, aggregates, backups and screenshots belong in owner-private evidence,
never this repository or CI artifacts.

## Requirement coverage and presentation

A01: WO clocks use explicit `Asia/Jakarta`, for example
`2026-10-23T07:51:51Z` → `23 Okt 2026, 14.51 WIB`. Original ISO text, offset
and fractional precision remain selectable in the technical disclosure. Naive
clocks and RFC3339 unknown offset `-00:00` retain their original calendar and
an explicit unverified-zone label. Invalid values are never converted to facts.
`Terakhir Diubah di Maximo` is a source record change, not work execution time.

A02/A03: exact retained `sources.maximo.wonum` is the prominent WO number;
canonical/scoped identifiers are not split or guessed. Six detail groups cover
identity/status, classification, chronology, duration/downtime/labor, Asset
relationship and expandable source/technical information. Original status remains
visibly exact and neutral. Technical identifiers, contract version, classification
state/origin/confidence, status availability and clocks remain available.
Keyboard selection/return, bounded paging and browser history are preserved.

A04: missing retained fields display BELUM TERSEDIA; unresolved canonical types
display BELUM DIPETAKAN; unverified description/workflow displays BELUM
DIVERIFIKASI; absent optional response fields display TIDAK DIEKSPOS. No rule
establishes TIDAK BERLAKU for a WO field, so it is not asserted. Numeric zero is
preserved. CLOSE, raw types and source downtime do not establish restoration,
functional failure or active repair time. MTBF/MTTR remain NOT_ELIGIBLE.

## B01/B02: verified field lineage and compatible correction

| Field | Legacy Collector | Baseline projector/mapper/Mart | Candidate behavior |
|---|---|---|---|
| actstart / actfinish | No normalized WO columns; current legacy mapper does not retain them in source JSON | Projector explicitly emits null; canonical mapper supports direct source dates; Mart/API have nullable actual fields | Keep missing. No use of changedate, reportdate, schedule, SR or overhaul dates as WO actual dates |
| reportdate | `reported_at` | Projector sends it; mapper emits top-level `reported_at`; Mart writer has no such column and baseline source JSON drops it | Preserve reviewed scalar under existing `sources.maximo.reportdate`; optional API `source_detail.reported_at` reads only that retained scalar |
| schedstart / schedfinish | `scheduled_start` / `scheduled_finish` | Same loss between canonical output and persisted Mart source JSON | Preserve reviewed scalars in existing vendor JSON; expose optional source detail clocks |
| changedate | `source_changed_at` | Projector, Mart and existing public field already retain it | Presentation change only; original public value is unchanged |
| failurecode | `failure_code` | Baseline local projector and canonical maintenance mapper omit it; Mart/API already have nullable field | Future projector forwards existing normalized scalar; canonical mapper fills existing `failure_code` |
| worktype / status | Normalized legacy fields | Raw vendor worktype plus conservative canonical enum; original status retained | PR119 classification behavior, status, identity and filters preserved |
| downtime / actlabhrs | `downtime_hours` / `actual_labor_hours` | Already mapped and persisted | Preserve, including zero; never call downtime active repair MTTR |
| estdur | `estimated_duration_hours` | Not actual duration evidence | Do not populate actual `duration_hours` from estimate |

The read-only audit covered the registered BSR/IP WO population with fixed SQL,
read-only transaction and statement timeout, plus owning catalog/timezone metadata.
It found retained legacy report/schedule/failure values not present in the current
Mart, and no actual-start/finish evidence in the inspected WO path. Exact aggregate
results and scope are private. DB timezone UTC and timestamptz columns establish
stored instants, not the lost original source offset/precision. New JSON clocks
preserve the exact payload string when available; disposable naive clocks remain
naive. Existing changedate normalization is outside this correction.

The verified MXWODETAIL knowledge record and MX-015A supersede the older mapping
table's assertion that direct failurecode is absent. Its scalar remains source
context; no Failure Code master, hierarchy, cause/remedy or failure-event rule is
inferred. The mapping table is reconciled accordingly.

Only optional `MaintenanceView.source_detail` is added publicly, with five
allowlisted scalar fields: work_order_number, asset_number, reported_at,
scheduled_start, scheduled_finish. All existing response fields and their values
are preserved. There is no source JSON/provenance/person serialization, legacy DB
join, new SQL, route, capability or grant. Existing consumers may omit or ignore
the optional object. Invalid scalar types, unsupported ISO syntax and malformed
offsets do not enter it. Existing scoped/denied-access behavior remains intact.

**No operational field has been recovered by changing source code alone.** The
projector/mapper correction is tested for future use only; no collector/projector
image is activated and no operational row is reprojected. Existing stores and
reader grants are unchanged. Recovery of current legacy report/schedule/failure
values requires separately approved bounded reprojection; that is not part of
this package's activation permission.

## B03: separately approvable actual-date retrieval plan (not executed)

1. Owner approves an exact private allowlist of at most ten registered BSR/IP WO
   numbers, intended fields, retrieval window and operator. Confirm MXWODETAIL
   knowledge and original timezone/precision evidence before execution.
2. Use the existing owning Collector read adapter and prescribed authentication;
   no credentials in NADI or a new service. Read only verified MXWODETAIL,
   scoped BSR/IP, exact wonum membership and fields wonum/assetnum/siteid/orgid,
   actstart/actfinish/reportdate/schedstart/schedfinish/changedate/failurecode.
   Confirm the verified exact query form before use; never guess a comparator.
3. Fixed maximum ten WO, 25 rows/page, at most twelve business requests including
   retries/detail requests, one request/second, 1 MiB cap, finite paging. Stop on
   scope/identity mismatch, auth failure, exceeded budget, ambiguous offset or
   unexpected payload. Existing auth permits one guarded session renewal only.
4. Save original allowlisted scalar bytes and response/timezone metadata privately;
   reconcile one-to-one source identity against the approved retained records.
   Missing/naive values stay missing/unverified. Produce a dry-run proposal only.
5. No retained writes, backfill, cursor/schedule changes or automatic replay.
   Any ingestion/reprojection needs a separate reviewed authorization and backup.

No Maximo request has been issued for this task. This document is a proposal,
not permission to run that retrieval.

## C: qualification and preservation

Synthetic tests cover projector→mapper→Mart writer idempotent replay, exact
source/status identity, failure scalar, retained clocks, zero/null, no fabricated
actual dates, original offset/precision and naive clocks. Actual API serializer
output passes the TypeScript validator and renders the real React component,
including invalid ISO variants and unknown offsets. Existing API endpoint/scope,
bounded Asset evidence, PdM, Engineering, auth/RBAC/CSRF and F01–F24 suites remain
mandatory. Browser fixtures stay network-isolated and synthetic, with actual
components at 390/768/1440 in light/dark modes and automated accessibility checks.

Historical F01–F24 assertions and PR119 pins remain verifiable at their immutable
baselines. `wo-detail-preservation.mjs` lists exact new hashes for the narrowly
authorized serializer, DTO, validator, WO components/formatter, future mapper/
projector correction, synthetic lineage test and reconciled mapping documentation.
All other source guards, mappings, shared schemas/enums, migrations, source workers,
controller, auth/session/grants, retained records, routes/navigation and KPI gates
remain protected. The collector runtime is not part of the allowed deployment.

## D/E: conditional local activation and owner review

Owner authorized one local development attempt after all mandatory gates PASS.
Use the existing Factual Compose service and official paired frontend/Engineering
controller only. Pin the candidate image/source and accurate container revision
label, preserve every other Compose setting/override/port, and qualify rollback
to PR119 for all three services. Fresh private backups and independently isolated
restores, session proof, source/dependency ancestry, exact-head backend/frontend CI,
independent technical/security review, DB identity/ledger and unrelated-service
preservation are required before any stop/replacement.

If eligible, update only the existing Factual API, verify compatible consumers,
then select the matching frontend/Engineering source. Verify all live versions,
data and service preservation, and perform authorized Asset→Maintenance UAT.
Failed mandatory validation invokes the approved rollback; no retained restore.
Missing legitimate session proof or Asset capability is reported as blocked;
do not substitute another role or broaden grants. Actual WO browser acceptance
requires a real authorized path and private screenshots. Synthetic acceptance is
not real WO UAT, and technical activation is not Product Owner acceptance.

No merge, QA/production deployment, schema migration, source acquisition, retained
backfill, grant expansion, polling change or Log Book PdM implementation.
