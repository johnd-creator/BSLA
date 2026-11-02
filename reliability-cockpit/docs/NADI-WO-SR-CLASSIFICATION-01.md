# NADI-MAXIMO-WO-SR-CLASSIFICATION-01

Date: 2 November 2026 (Asia/Jakarta). Base: Draft PR118 exact
`0a10fe10bf2c9cd2158b5c47ed691f8b9404a7a0`. Technical qualification and owner
acceptance are independent. This document contains no operational record samples.
Private aggregate receipts remain outside Git and CI artifacts.

## Baseline and authority

GitHub metadata and local merge-base checks agree on the complete open draft chain:

| PR | Exact head | Base |
| --- | --- | --- |
| 114 | aa065af9cef01d8ee3358bcca8fc628ba311ca3a | main |
| 115 | 3a01e842b5bfca08a5d508b8988dc6deb32c2961 | PR114 branch |
| 116 | 3778584a7d4f97b98aae44cea37838a34b61f5d0 | PR115 branch |
| 117 | 988af8d4875758b300e7b563c0a205f143ee184c | PR116 branch |
| 118 | 0a10fe10bf2c9cd2158b5c47ed691f8b9404a7a0 | PR117 branch |

Each adjacent head is an ancestor of the next. One isolated worktree/branch is
stacked on PR118. Existing control checkout changes and untracked workbook are
preserved. No service activation, account/session/grant change, migration,
recollection or source request was performed. The integrated Sprint5 candidate
remains the active localhost selection; this branch is not activated there.

## Source-to-UI lineage and UNKNOWN root cause

1. Verified `MXWODETAIL` mapping: `wonum`, `assetnum`, `status`, `worktype` map
   to legacy `work_order.id`, `equipment_id`, `status`, `work_type`.
   The legacy store is normalized evidence, not a complete raw source archive.
   Site/org are not legacy WO columns. Projector imposes validated BSR/IP scope.
2. `CollectorMartProjector._work_order_payload` reconstructs approved scalar
   fields from local rows, excluding personal fields and source JSON. Legacy
   actual start/finish are not retained, so this path deliberately emits nulls.
3. `maintenance_event_from_payload` retains worktype under
   `sources.maximo.worktype`, status in both canonical status/source scalars,
   and scoped canonical/work-order/asset identities. Its conservative enum is
   CM, PM, INSPECTION, CALIBRATION, REPAIR, EMERGENCY. Other source codes keep
   null `event_type`. This is intentional contract behavior, not lost acquisition.
4. `MartWriter` persists local `maintenance_event` in the existing Maximo DB.
   Retained audit used BEGIN READ ONLY, bounded aggregate SELECTs, statement
   timeout and no row exports. It compared current BSR/IP Mart and matching
   legacy WO, and separately counted Registry membership.
5. `MartQueryRepository.list_maintenance` preserves Registry + BSR/IP scope,
   exact work-order/status/canonical-event-type filters, bounded SQL pagination
   and stable ordering. Existing SQL `_raw_work_type` fallback already serves
   repeat-work/investigation aggregates: raw → canonical → UNKNOWN. It was
   never applied to the MaintenanceView DTO or Asset Maintenance display.
6. FastAPI `_maintenance` formerly exposed canonical `event_type` but omitted
   retained raw worktype. AssetMaintenanceEvidence labeled this as source type
   and rendered null as UNKNOWN. That read/presentation mismatch is corrected.
7. Next `/api/cockpit/*` proxy, access policy and existing route dependencies are
   byte-identical. No new source interface or authorization scope is introduced.

Observed retained distributions: most legacy WO have type; a substantial Mart
subset has nonblank raw type and null canonical type. Both genuinely empty
retained types and original unknown codes remain distinct. Examined matching WO
statuses have no missing Mart status or mismatch; no status fallback/translation
is justified. This is a retained-data conclusion, not proof of current Maximo
configuration or freshness. Canonical identity and scoped work-order refs have
no duplicates in the examined Mart population. Local legacy id-only keys cannot
prove historical cross-site source uniqueness. No data repair is attempted.
Source changed timestamps, projector success time and source sync completion are
separate; recent projection does not establish complete/fresh source acquisition.

## Workbook reference and mapping decisions

Read-only verification: owner workbook `person group.xlsx`, sheet FLOW, only
TABEL/NAMA FLOW/PROCESS/VERSION. Workbook SHA256:
`721cc324f7a4acb47d6124fd018127b5d21dee44c030a6dadc330548f98e249f`.
The extracted table below contains no person/group/role/relationship columns.
The complete bounded WO/SR scan also found WOFLOW, the WO parent reference.
Workbook versions describe the reference only, not record assignment or active
configuration. No workflow step proves a source record's current status.

| TABEL | NAMA FLOW | PROCESS | VERSION | Reference | Decision |
| --- | --- | --- | --- | --- | --- |
| SR | SRFLOW | PARENT | 33 | FLOW!B4:E4 | VERIFIED reference; CANDIDATE record mapping |
| SR | SR-C | SR TIPE CD,CM DAN FLM | 6 | FLOW!B5:E5 | VERIFIED reference; CANDIDATE record mapping |
| WORKORDER | WOFLOW | PARENT | 38 | FLOW!B10:E10 | VERIFIED reference; CANDIDATE record mapping |
| WORKORDER | WOCD-C | WO TIPE CD | 11 | FLOW!B11:E11 | VERIFIED reference; CANDIDATE record mapping |
| WORKORDER | WOCM-C | WO TIPE CM | 34 | FLOW!B22:E22 | VERIFIED reference; CANDIDATE record mapping |
| WORKORDER | WOEM | WO TIPE EM (QUICK REPORTING) | 10 | FLOW!B33:E33 | VERIFIED reference; CANDIDATE record mapping |
| WORKORDER | WOINV-U | WO Inventory UBH | 2 | FLOW!B39:E39 | VERIFIED reference; CANDIDATE record mapping |
| WORKORDER | WOOH-IN | WO OVERHAUL BUKAN UBH | 6 | FLOW!B48:E48 | VERIFIED reference; CANDIDATE record mapping |
| WORKORDER | WOPDM | WO TIPE PDM | 10 | FLOW!B61:E61 | VERIFIED reference; CANDIDATE record mapping |
| WORKORDER | WOPM-C3 | WO TIPE PM | 10 | FLOW!B69:E69 | VERIFIED reference; CANDIDATE record mapping |
| WORKORDER | WOPMI-C | WO TIPE OH UBH | 17 | FLOW!B77:E77 | VERIFIED reference; CANDIDATE record mapping |

| Subject | Decision | Reason / next action |
| --- | --- | --- |
| Raw WO CM/PM and canonical CM/PM equality | VERIFIED | Retained values + existing enum; no semantic expansion |
| CD/PDM/EM/OH raw codes | VERIFIED raw; UNRESOLVED canonical mapping | Workbook workflow labels are CANDIDATE associations only; EM is not automatically EMERGENCY |
| RTF/S/PRO/ECO | UNRESOLVED | Not covered by supplied WO workflow reference; retain exact code |
| WOINV-U | CANDIDATE | Inventory workflow text supplies no raw type code |
| WOOH-IN / WOPMI-C | CANDIDATE | Both mention overhaul contexts; cannot assign records by OH alone |
| SR CD/CM/FLM and class SR | VERIFIED retained | Separate fields; one workflow may serve multiple types |
| SRFLOW parent / SR-C | VERIFIED workbook; CANDIDATE per-record | No retained assignment/version evidence |
| Record description expansion / workflow/version | NOT_AVAILABLE | No reviewed per-record interpretation; API leaves null |
| Empty retained type/status | NOT_AVAILABLE | Cannot distinguish original absence vs unretained source field universally |

## Backward-compatible WO read contract

Only MaintenanceView gains optional `classification`. Existing `event_type` and
`status` values/filter meanings remain unchanged. No canonical schema or enum changes.
The object exposes allowlisted raw worktype, canonical category, state, origin,
confidence, nullable description/workflow fields, workflow availability and status
availability. It never serializes source JSON, internal provenance, person fields
or timestamps absent from the prior public contract.

`UNMAPPED` means retained raw type exists but canonical category does not.
`MISSING_RETAINED_TYPE` means the retained source scalar is empty; it does not
assert original production absence. `CANONICAL_ONLY` means only canonical category
is available. `CANONICAL_SUPPORTED` means a category exists. Confidence VERIFIED
only confirms exact raw/canonical equality; no workflow, functional failure or
engineering approval is implied. Other mappings remain UNRESOLVED.
Old responses without the object render NOT_EXPOSED. Null/blank status stays
unchanged in the API and displays missing retained status in UI. Frontend rejects
malformed or contradictory metadata. Canonical filter label now states its actual
meaning; raw display does not change filter behavior.

## SR audit and proposed contract (not implemented)

Verified legacy table: `service_request.id`, work_type, class_label, status,
status_description, equipment_id/location_id, source_changed_at/status_changed_at
and other normalized fields. Its retained `sources.maximo` contains only ticketid
and ticketuid in the examined population. The source mapping uses MXAPISR;
workflow/version and related WO are not captured. Observed class SR is not a work
type. All examined rows have type/class/status; their CD/CM/FLM values agree with
SR-C's description without proving assignment.

Collector `/service-requests` is an existing read interface, but returns personal
fields and does not implement NADI's scoped factual exposure boundary. NADI has
no suitable authorized SR read route in the inspected API scope. Do not proxy
that route to engineers. A future separately reviewed read model must establish
Registry/site/org scope from verified retained evidence, stable scoped SR identity,
allowlisted type/class/status, explicit availability, bounded paging, and tests for
denied scope/person redaction. A related WO reference needs explicit retained
relationship evidence; do not infer it from asset/type/workflow. No SR Mart,
workflow engine, new store, route or grants are added here.

## Qualification and preservation

New synthetic tests cover supported enum values, raw unmapped values, genuinely
empty retained values, legacy DTO compatibility, status preservation/blanks,
redaction, SR class/type/workflow separation and multiple types using one workflow.
Existing synthetic canonical replay proves stable identity after duplicate/status
updates. Existing 10k maintenance fixtures prove bounded stable pagination,
Registry scope, exact filters, duplicate/conflicting references and read-only SQL.
Frontend corrupt-response tests include contradictory classification metadata.

| ID | Preserved baseline feature / evidence |
| --- | --- |
| F01 | Native typed measurements/original values and units; unchanged services/contracts + input suites |
| F02 | Native/provisional exclusivity/raw capture preserved; capture/workbook suites |
| F03 | Work-origin conditional department preserved; no PR107/Maximo recovery/acquisition change |
| F04 | Human analysis/follow-up narrative preserved; no source-fact interpretation conversion |
| F05 | Reported-unverified SR references preserved; no source request/write |
| F06 | Sprint2 Register1/5/10/2MiB hook unchanged; existing browser/backend suites |
| F07 | Same-inspection sample wrapper/plot unchanged; cross-inspection trend NOT_ELIGIBLE/M02 pending |
| F08 | Lazy provisional source/keyset/byte history unchanged; source-history tests retained |
| F09 | Migration007, source profiles/aliases and originals untouched; no replay/import |
| F10 | Author/reviewer workflow commands and independent review preserved; existing HTTP/PG/browser tests |
| F11 | Deliberate approved-native Case/frozen revision unchanged; no automatic Case |
| F12 | Provisional Case/plot exclusion unchanged; no RAW promotion or guessed mapping |
| F13 | Cases/investigation/review/audit accessible contextually; source/services/paths preserved |
| F14 | Recommendation/reported existingWO service unchanged; no Maximo create/update |
| F15 | Advisory/Inbox/ACK unchanged and available; existing regression gates |
| F16 | Intent receipts/CAS/audit/command hooks unchanged; HTTP integrity regression |
| F17 | Draft recovery and synchronous session/scope clearing unchanged; browser regressions |
| F18 | RBAC/CSRF/Origin/session/gateway/policy/middleware byte-identical to3a;403 is access, not outage |
| F19 | Attachment metadata/custody unchanged; detail source link grants no upload/download authority |
| F20 | All28 page entries retained; only Asset Maintenance presentation changes; no new route/frontend |
| F21 | FMEA/maintenance/health/overhaul/RCFA utility routes retained; exactasset maintenance improved only |
| F22 | Existing Beranda/DataTrust/report definitions/readers preserved; contextual Laporan readiness added, no KPI publication/portfolio bypass |
| F23 | Source interpretation/estimates/proofs and six existing parity pins unchanged |
| F24 | Accounts/sessions/auth/controller/deploy bytes unchanged; no reset/login/grant/session write in Sprint4 |

Historical Sprint3/Sprint5 preservation assertions stay active with four explicitly
hash-pinned exceptions: MaintenanceView serializer, its TypeScript DTO, evidence
response validator, and AssetMaintenanceEvidence presentation. All other protected
source/auth/session/controller/schema/collector bytes must remain unchanged.
Exact-head GitHub backend/frontend jobs and independent review are required before
technical PASS; results and immutable HEAD are recorded in the Draft PR.

## Owner decisions and future work

Confirm readable type definitions and code-to-category mappings, including EM,
OH subtypes, RTF/S/PRO/ECO and Inventory. Confirm live workflow versions/assignment
only through separately authorized evidence; workbook alone is insufficient.
If canonical expansion is desired, review the shared contract and all consumers
before a compatible collector/Mart migration. No migration/reprojection is needed
for this read correction. Review SR scope/identity/exposure separately.
Operational MTBF/MTTR, functional failure classification and cross-inspection
trending remain NOT_ELIGIBLE. Technical tests do not confer owner acceptance.
