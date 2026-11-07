# MX-015A Maintenance Failure Semantics Discovery

## Executive Result

The verified MXWODETAIL source exposes direct Work Order fields relevant to failure investigation:

- failurecode — string, present in all three bounded exact-Work-Order reads;
- problemcode — string, present in two of three bounded reads;
- plncausecode — string in the live schema, not present in selected bounded members;
- faildate — string in the live schema, present in two of three bounded reads;
- failureinformation and failureinformation_description — schema fields;
- reportdate, actstart, and actfinish — date-like Work Order fields;
- worktype, woclass, status, task, parent, and follow-up indicators.

This proves technical source availability, not failure identity. No field was proven to mean one governed failure occurrence, and no failure hierarchy was proven. The Failure Code object is technically identified through live metadata, but every bounded business collection attempt returned HTTP 400.

Therefore:

- Repeat Activity remains factual maintenance-event repetition.
- Repeat Failure remains NOT READY.

No failure KPI, repeat window, deduplication rule, or failure classification was implemented.

## Existing Maintenance Boundary

The current NADI maintenance boundary is the Maximo Work Order source copied into the local collector and represented as factual Maintenance Activity. The product does not equate repeated events with repeated failures.

Existing evidence establishes:

- collector Work Orders preserve a source failure_code value when present;
- the current local Mart maintenance population does not provide governed failure-code semantics sufficient for Repeat Failure;
- the Maintenance Activity date fallback is an activity/source-change basis, not a failure, repair, execution, or completion timestamp;
- Work Order statuses and Work Types remain raw source values;
- parent/task/follow-up indicators are technically present but are not governed exclusion rules.

The discovery scope is SITE=BSR, ORG=IP. Three local collector candidates with non-empty failure codes and registered Assets were selected without persisting Work Order descriptions or person fields. Their source Work Types and statuses were retained only as bounded semantic shapes: RTF, CD, PM and APPR, INPRG, WDONE.

## Work Order Failure Fields

The live JSON Schema /oslc/jsonschemas/MXWODETAIL returned HTTP 200 with title WORKORDER. The following fields are technical evidence from the schema and, where stated, bounded exact-Work-Order members.

| Field | Type | Bounded observation | Conservative interpretation | Evidence class |
|---|---|---|---|---|
| failurecode | string | Present in 3/3 members | Direct Work Order failure-classification candidate | SOURCE_SEMANTICS_REQUIRE_VERIFICATION |
| problemcode | string | Present in 2/3 members | Problem-code candidate; master relationship unknown | SOURCE_SEMANTICS_REQUIRE_VERIFICATION |
| plncausecode | string | Schema only | Cause-code candidate; not observed in bounded members | SOURCE_SEMANTICS_REQUIRE_VERIFICATION |
| faildate | string | Present in 2/3 members | Failure-date candidate; event meaning unknown | SOURCE_SEMANTICS_REQUIRE_VERIFICATION |
| failureinformation | string | Schema only | Failure-information candidate | UNKNOWN |
| failureinformation_description | string | Schema only | Failure-information display candidate | UNKNOWN |
| reportdate | string | Present in 3/3 members | Work Order report-date field; not proven failure time | SOURCE_SEMANTICS_REQUIRE_VERIFICATION |
| actstart | string | Present in 2/3 members | Work execution date candidate; not proven failure time | SOURCE_SEMANTICS_REQUIRE_VERIFICATION |
| actfinish | string | Present in 2/3 members | Work completion date candidate; not proven failure time | SOURCE_SEMANTICS_REQUIRE_VERIFICATION |
| assetnum | string | Present in 3/3 members | Direct Asset reference | VERIFIED |
| wonum | string | Present in 3/3 members | Work Order source identity | VERIFIED |
| workorderid | integer | Present in 3/3 members | Internal Work Order identity candidate | VERIFIED; uniqueness rule untested |
| siteid | string | Returned in bounded members | Site scope | VERIFIED |
| orgid | string | Returned in bounded members | Organization scope | VERIFIED |
| worktype | string | Present in 3/3 members | Raw Work Type | VERIFIED; failure meaning unknown |
| woclass | string | Present in 3/3 members | Raw Work Order class | VERIFIED; failure meaning unknown |
| status | string | Present in 3/3 members | Raw lifecycle/status value | VERIFIED; failure meaning unknown |
| istask | boolean | Present in 3/3 members | Task indicator | VERIFIED |
| pctaskid | string | Present where returned | Unverified source business attribute; not a resolved parent WO | Technical presence VERIFIED; parent-number equivalence and sequence rule UNKNOWN (semantic audit 2026-11-05, no new live reads) |
| haschildren | boolean | Present in 3/3 members | Child indicator | VERIFIED |
| hasfollowupwork | boolean | Present in 3/3 members | Follow-up indicator | VERIFIED |
| origrecordclass | string | Present in 2/3 members | Origin classification candidate | VERIFIED; duplicate/follow-up rule unknown |
| origrecordid | string | Present in 2/3 members | Origin record reference candidate | VERIFIED; target semantics unknown |
| plusgfailmech | integer | Schema only | Failure-mechanism candidate from technical name | SOURCE_SEMANTICS_REQUIRE_VERIFICATION |
| plusgfailmechrem | string | Schema only | Failure-mechanism/remedy-looking candidate | SOURCE_SEMANTICS_REQUIRE_VERIFICATION |
| plusgfailfix | boolean | Present in 3/3 members | Failure-fix-looking indicator | SOURCE_SEMANTICS_REQUIRE_VERIFICATION |
| plusgproblemstmt | string | Schema only | Problem-statement candidate | SOURCE_SEMANTICS_REQUIRE_VERIFICATION |
| plusgfailsubdiv | string | Schema only | Failure-subdivision candidate | SOURCE_SEMANTICS_REQUIRE_VERIFICATION |
| plusgfailsubdivrem | string | Schema only | Failure-subdivision/remedy-looking candidate | SOURCE_SEMANTICS_REQUIRE_VERIFICATION |
| plusghardfailmode | string | Schema only | Hard-failure-mode candidate | SOURCE_SEMANTICS_REQUIRE_VERIFICATION |

Names are retained as source clues only. They do not establish a Maximo UI label, domain, hierarchy, or business rule.

## Failure Code Object

GET /oslc/apimeta/MXAPIFAILURECODE returned HTTP 200. The metadata identifies object structure MXAPIFAILURECODE, title Maximo API's Failure Codes, and queryCapability=All.

GET /oslc/jsonschemas/MXAPIFAILURECODE returned HTTP 200 with schema title FAILURECODE. Required schema fields are:

| Field | Type | Role | Evidence |
|---|---|---|---|
| failurecodeid | integer | identity candidate | Live schema |
| failurecode | string | code candidate | Live schema |
| description | string | description candidate | Live schema |
| description_longdescription | string | long-description candidate | Live schema |
| orgid | string | organization scope | Live schema |

No siteid, parent, child, hierarchy, category, type, problem, cause, or remedy field was exposed by the live schema.

The following bounded business requests all returned HTTP 400:

1. Prior BSR-scoped siteid/href request, retained from previous evidence.
2. Metadata-informed orgid=IP, pageSize=1, minimal field selection.
3. Metadata-informed queryCapability=All, pageSize=1, minimal field selection without a scope filter.

No Failure Code business member was returned. The object is therefore technically identified but not instance-verified as a readable master data collection.

## Failure Hierarchy

No verified hierarchy exists in the evidence collected for this task.

The live Failure Code schema has no parent/child/hierarchy fields. The Work Order schema has problemcode and plncausecode candidates, but no verified relationship connects either field to MXAPIFAILURECODE, and no remedy field was identified.

No exact Problem → Cause → Remedy graph is drawn. The hierarchy result is UNKNOWN for the instance because the business Failure Code collection could not be read. The absence of hierarchy fields in the schema is evidence against promoting a textbook hierarchy, not proof that a report or UI projection cannot expose one.

## Work Order → Failure Relationship

The bounded Work Order members returned direct namespaced fields such as spi:failurecode and spi:problemcode. No failure collection reference or same-origin Failure Code detail link was returned by the selected response.

The strongest verified technical path is:

- MXWODETAIL.failurecode
- MXWODETAIL.problemcode
- MXWODETAIL.plncausecode as a schema candidate
- MXWODETAIL.faildate

This is a direct-field observation, not a verified relationship to the MXAPIFAILURECODE master. The Work Order can carry a failure-classification value, but the value's identity, hierarchy, scope, and business meaning remain unresolved.

Evidence class: PARTIAL for the Work Order-to-failure boundary.

No detail/relationship GET was performed because no relationship link was returned and bounded child discovery was not justified.

## FMEA / FMEAITEM Comparison

These three concepts remain explicitly separate.

| Concept | Source object | Field | Type | Relationship | Evidence class |
|---|---|---|---|---|---|
| Work Order failure classification | MXWODETAIL | failurecode | string | Direct Work Order field; master relationship unknown | SOURCE_SEMANTICS_REQUIRE_VERIFICATION |
| FMEA header failure code | IPFMEA | failurecode | factual source field | IPFMEA-to-Asset verified; WO relationship unknown | VERIFIED field; semantics unverified |
| FMEA item failure-mode candidate | IPFMEAITEM | failuremode | string | Item-to-FMEA verified; WO relationship unknown | SOURCE_SEMANTICS_REQUIRE_VERIFICATION |

No evidence permits any of these equalities:

- MXWODETAIL.failurecode = IPFMEA.failurecode
- MXWODETAIL.failurecode = IPFMEAITEM.failuremode
- IPFMEA.failurecode = IPFMEAITEM.failuremode

## Failure Occurrence Identity

The source exposes candidate components for an occurrence:

- Asset identity: MXWODETAIL.assetnum;
- Work Order identity: wonum, workorderid;
- classification candidates: failurecode, problemcode, and possibly plncausecode;
- event/date candidates: faildate, reportdate, actstart, and actfinish;
- sequence/context candidates: istask, pctaskid, haschildren, hasfollowupwork, origrecordclass, and origrecordid.

The evidence does not establish which components define one failure occurrence. It does not prove that each Work Order is a failure, that each failurecode is a failure identity, or that faildate is the event time. No formula or time window is proposed.

FAILURE_OCCURRENCE_IDENTITY_READY: NO

## Failure Event Time

| Candidate | Technical evidence | Business suitability |
|---|---|---|
| faildate | Schema field; present in 2/3 bounded members | Strongest name-based candidate, but meaning is unverified |
| reportdate | Schema field; present in 3/3 members | Report/creation boundary is not proven failure time |
| actstart | Schema field; present in 2/3 members | Work execution boundary, not necessarily failure time |
| actfinish | Schema field; present in 2/3 members | Work completion boundary, not necessarily failure time |
| statusdate | Schema field and collector field | Status-change boundary, not necessarily failure time |

No date is promoted to the failure occurrence timestamp.

FAILURE_EVENT_TIME_READY: NO

## Work Type / WO Class Implications

The instance technically distinguishes Work Orders using worktype, woclass, status, istask, pctaskid, haschildren, hasfollowupwork, origrecordclass, and origrecordid.

The bounded local candidate set included raw Work Types RTF, CD, and PM, and raw statuses APPR, INPRG, and WDONE. These values demonstrate source categories only. No evidence establishes which Work Types or statuses represent a failure event. PM, inspection, planned, corrective-looking, repair-looking, or other categories must not be mapped to failure without owner validation.

## Duplicate / Follow-up / Cancellation Evidence

Technical fields exist to investigate sequence distortion:

- status can distinguish raw lifecycle values, including cancellation where the source supplies such a value;
- istask, pctaskid, and haschildren expose task/parent structure;
- hasfollowupwork exposes a follow-up indicator;
- origrecordclass and origrecordid expose origin candidates.

No field semantics or exclusion policy was proven for cancelled, duplicate, follow-up, planning, PM, inspection, child, or overhaul Work Orders. No rows were deleted or reclassified, and no deduplication rule was applied.

## Repeat Failure Readiness

Repeated Work Orders are not Repeat Failure. A product-ready definition would need a governed failure occurrence identity covering Asset identity, authoritative failure classification and hierarchy, failure-event timestamp, Work Type/status inclusion rules, repair/completion meaning, parent/child/follow-up/duplicate treatment, and business-owner acceptance of a repeat interval rule.

Current gates:

- WORKORDER_FAILURE_FIELDS_IDENTIFIED: YES
- FAILURE_CODE_OBJECT_IDENTIFIED: PARTIAL
- FAILURE_HIERARCHY_IDENTIFIED: NO
- WO_TO_FAILURE_RELATIONSHIP: PARTIAL
- PROBLEM_IDENTITY_IDENTIFIED: PARTIAL
- CAUSE_IDENTITY_IDENTIFIED: PARTIAL
- REMEDY_IDENTITY_IDENTIFIED: NO
- FAILURE_EVENT_TIME_READY: NO
- FAILURE_OCCURRENCE_IDENTITY_READY: NO
- REPEAT_FAILURE_IDENTITY_READY: NO
- REPEAT_FAILURE_PRODUCT_READY: NO

## Remaining Business Questions

- What does MXWODETAIL.failurecode represent: a failure event, classification, code-list value, or another source concept?
- Does the Failure Code master have a hierarchy exposed through another application, report, relationship, or object structure?
- Do problemcode and plncausecode refer to governed Problem and Cause identities, and where is Remedy represented?
- What does faildate mean operationally, and which date marks failure occurrence rather than reporting, execution, completion, or status change?
- Which Work Types and statuses qualify as actual failures?
- How are PM, inspection, planned, cancelled, duplicate, child, follow-up, overhaul, and administrative Work Orders treated?
- Is origrecordid a reliable source-event link, and what object does it target?
- Is the Failure Code master organization-scoped, site-scoped, or global?
- Can a single Work Order contain multiple failure occurrences?
- What business-owner acceptance criteria define Repeat Failure and its time window?

## Request Audit

All Maximo business access was read-only.

| Request class | Count | Result |
|---|---:|---|
| Authentication POST /j_security_check | 4 | Authentication only; cookies remained in memory |
| Metadata GET | 6 | MXWODETAIL and MXAPIFAILURECODE apimeta/schema plus capability/schema refinement |
| Business GET | 5 | Three exact-WO reads HTTP 200; two bounded Failure Code reads HTTP 400 |
| Detail/relationship GET | 0 | No link was returned or followed |
| HEAD | 0 | Not used |
| OPTIONS | 0 | Not used |
| Business writes | 0 | No POST/PUT/PATCH/DELETE/merge/status action |

The task remained within the 15 metadata GET and 15 business GET budgets. The local collector API and one read-only SQL query were used only to select three bounded candidates; they are not counted as Maximo business GETs. Browser UI inspection was not needed.
