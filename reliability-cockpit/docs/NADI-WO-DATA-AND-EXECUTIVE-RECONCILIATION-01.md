# Integrated WO evidence and Executive reconciliation

Requirement: NADI-WO-DATA-AND-EXECUTIVE-RECONCILIATION-01. Dependency: Draft PR128
at cbd4a8006c1d2584dcacf9be9827e6fdd8c73dcf, based on main6bff0a5c. One integrated
candidate covers acquisition, Legacy/Mart detail, Factual DTO and both Executive
surfaces. Source implementation, independent qualification, deployment and PO UAT
are separate. No merge, source GET, service replacement or live Mart write is
implied by this document. Private counts, SQL, source samples and manifests stay
in ignored owner evidence.

## Field lineage matrix

| Evidence | Verified source field | Existing Legacy | Candidate Mart/API/UI | Qualification / limits |
|---|---|---|---|---|
| WO identity/site/org/Asset | wonum, siteid, orgid, assetnum | ID/Asset; old Legacy lacks per-row site/org columns | existing scoped references and source identity | Never derive site/org/group from prefix; Registry join remains mandatory |
| Location | location | location_id | bounded detail field | Direct source reference, no inferred hierarchy |
| Description | description | description | bounded plain text, prominent WO heading context | 4000 characters; classification description never substitutes |
| Status / description | status, status_description | retained | original code + bounded description | No execution, open/backlog or date inference |
| Raw type / class | worktype, woclass | retained | existing classification + direct class | Canonical enum/mapping policy unchanged |
| Priority | wopriority, wopriority_description | retained | bounded scalar/code description | Original technical code, no inferred risk score |
| Source parent | parent | not selected previously | newly selected, independently retained | Verified field/relationship presence; not reconstructed from pctaskid |
| Task / child | pctaskid, istask, haschildren | parent_wo stores pctaskid; flags retained | separate raw task reference/flags | PCTASKID does not become proof of PARENT or physical hierarchy |
| WO Group | wogroup | not selected previously | future raw scalar, semantics explicitly unverified | Field presence is known; BSR group/ownership meaning is not approved |
| Failure | failurecode | retained | existing direct code, recoverable if absent | No cause/remedy/failure-event interpretation or descriptor expansion |
| Report/status/schedule/target dates | reportdate, statusdate, schedstart, schedfinish, targcompdate | retained | separate bounded clocks + evidence | Zoned clocks retain source text when observed; naive clocks stay uncertain |
| Actual clocks | actstart, actfinish | PR128 versioned proof | existing actual fields + seven completeness states | PR128 guards/offsets/status-aware nulls remain; distinct approved pilot only |
| Last source modification | changedate | retained | separate record activity | Never replaces execution/report dates or source collection freshness |
| Collection / Mart update | Collector observation, Mart metadata | new allowlisted observation proof / existing Mart timestamp | separately labeled optional timestamps | Not a claim that a full polling traversal completed |
| Estimate/labor/downtime | estdur, actlabhrs, downtime | retained | estimate distinct from actual duration; existing labor/downtime | Explicit hours; zero stays zero; no MTBF/MTTR eligibility |
| Long description | description_longdescription exists in verified object metadata | not acquired by this package | withheld | Additional source-owner/size/content authorization needed |
| Job plan / responsibility / descriptors | no accepted mapping for this package | unresolved | withheld | Do not guess jpnum, ownership-group meaning, failure descriptors or work instructions |
| Person/cost/raw payload | existing private Legacy may contain them | private owner store | excluded | No reporter/supervisor/cost/raw JSON exposure or NADI cross-store join |

Knowledge anchors: maximo-knowledge/discovery/objects/mxwodetail.json,
reliability-data-contracts/mappings/maximo-to-contracts.md. Schema/field presence
is independent from business semantics and current source-value availability.
A representative exact registered BSR/IP sampling manifest is prepared privately;
no fresh source requests are authorized or executed by development. Absent retained
status/type representatives remain a stated coverage limitation.

## Retention and recovery

`wo_detail` is a strict additive allowlist in existing sources.maximo JSON. It
records exact identity, source version, optional collection time and bounded
non-personal fields. Per-field states distinguish observed value, retained Legacy
value, observed empty, unverified absence and invalid/ambiguous source input.
Existing non-null technical evidence survives an omitted/invalid source replay;
retained observations keep their field observation version. Equal-version
conflicting observed detail fails closed. A Legacy null never proves a source null.
Actual-date retention and rollback remain owned by unchanged PR128 mechanisms.

The separately governed `wo_detail_reprojection` library plans at most ten exact
registered identities with equal known Legacy/Mart source versions. Its distinct
`wo-details-plan/1` digest cannot be substituted for an actual-date plan. Apply
locks the same Registry→WO order, updates only detail/report/schedule JSON and a
missing direct failure code, and requires a durable pre-commit checkpoint on
PostgreSQL. It never inserts a WO, contacts Maximo, advances a cursor or restores a
whole stale row. Replays are idempotent. Scoped rollback compares owned after
values before any mutation, preserves independent metadata, advances Mart update
metadata and refuses changed owned facts/newer versions atomically. Returned
rollback journals support verified retries; ambiguous partial cohorts fail closed.
The private campaign is an immutable eligibility proposal, not an approved write.
A changed version requires stopping and review, not silent expansion/replanning.

## Executive definitions

All new aggregates remain SQL-only after BSR/IP and Registry predicates. Counts
use distinct work_order_id, with a disclosed canonical-event fallback for unresolved
keys. Duplicate canonical rows cannot multiply a known WO identity. Scope captions
include retained population, all retained work types/statuses, task inclusion,
period and unverified WO Group semantics. The existing status/task projection
policy is not changed.

- Reported: valid retained report-date evidence, never changedate fallback.
- Actual started / finished: corresponding actual clock and versioned source proof.
- Record modified: changedate only; data activity, never performed maintenance.
- Status distribution: retained snapshot, not a history of status transitions.
- Backlog: withheld until an approved open-status definition exists.
- Coverage: available dates / total unique retained WO; absent coverage is shown
  as unavailable instead of a complete-looking activity chart.
- Collection freshness: explicitly NOT_EXPOSED when the reader lacks collection
  evidence. API query time, Mart update and business changedate cannot supply it.

Legacy Executive response fields remain backward-compatible and use ACTSTART only
instead of COALESCE(ACTSTART, changedate). The new explicit series is additive;
legacy panels remain visible with a coverage warning. Engineer registered READ
receives only the registered WO module, never FMEA/health/portfolio authority.
Exact-allowlist READ retains bounded Asset/WO requests; unavailable aggregate or
latest-modification information is withheld rather than broadening a query/grant.

## Polling and operational boundaries

Read-only evidence confirms repeated PAGE_LIMIT at the existing25×20 cap, with
an old cursor and oldest selected change still above it. Existing cadence is
post-cycle sleep300seconds; running on that cadence does not prove complete source
coverage. A count of already-retained rows above the watermark is not unseen backlog.
Do not reset the cursor or increase source scope/page caps/schedule. A persisted
pagination offset is not safe proof of a stable source snapshot across changing
records/deletions. No verified snapshot/date predicate contract currently proves a
safe resumable traversal, so the operational reconciliation design remains gated
on source-owner evidence. Source sampling/polling repair belongs in the single
consolidated approval manifest with service and data actions, not an implicit sync.

## Qualification and delivery

Required: Collector offline and guarded PostgreSQL lanes; six existing file
rehearsals; projection/source/version/NULL/concurrent replay; new detail rollback;
SQL identity/scope/date-basis regressions; optional DTO/privacy/scoped READ; actual
React escaping/date/null/zero/legacy compatibility; hierarchy/PdM preservation;
canonical NADI/Maximo exact-head CI; independent full integrated review.
Historical preservation hashes remain enforced. New source changes require a
reviewed, exact-byte exception before those guards can qualify the candidate;
a hash mismatch is not PASS and must not be bypassed.

All live versions, backups/restores, exact campaign/sample/image seals, controller
compatibility and authorized browser screenshots are owner-private. Current login
state is expired; baseline browser visibility cannot establish candidate UAT.
Do not claim NADI_WO_INTEGRATION_LOCAL_ACTIVE_READY_FOR_PO_REVIEW until approved
services run this candidate and real Engineer Beranda→Aset→Maintenance→WO Detail
passes. Development completion may qualify NADI_WO_EVIDENCE_AND_EXECUTIVE_RECONCILED
only after all exact-head code/review gates pass. Operational recovery counts stay0
until separately approved writes genuinely occur.


### Review and browser compatibility correction

WO detail observations retain per-field versions, including verified empty values
through omitted or invalid replay. Historical repair preserves known null proof
instead of downgrading it to unverified absence. Executive date aggregates bind
typed source evidence to original/normalized timestamps, retained columns and
known nonfuture versions; malformed JSON never enters unchecked numeric/time
casts. PostgreSQL 16 validates source calendars before timestamp conversion.

The finite preservation manifest validates exact immutable blobs and current
bytes; a stable historical wrapper base retains both historical assertion loops.
It does not regenerate pins, adopt moving HEAD or authorize runtime actions.
All old maps and broader source, route, untracked and ancestry checks remain.

The mandatory browser journey also requires the original provenance disclosure
label, visible chronology heading and raw Legacy report/schedule ISO text. Those
remain compatible with the seven-section presentation and plain bounded text.
Browser assertions and CI qualification selectors are preserved. A code review
PASS and individual green jobs are not full final-head qualification.
