# Manual operating evidence and independent KPI readiness

The [pilot calculation and trace extension](reliability-calculation.md) now adds executable MTBF/MTTR arithmetic, immutable calculation evidence, charts and drilldown. Selected ready metrics now have a separate [Supervisor approval workflow](reliability-supervisor-approval.md); saving an engineer method alone never approves a KPI.

Implemented locally in the existing NADI Laravel checkout. Entry point:
**Reliability → exact asset/year → Log operasi & cakupan / Aturan KPI & versi**.
The repair review now has a date/time interval editor; the annual report includes
reviewed-failure monthly counts and an observation-type Pareto table.

## Operating logs

Each exact asset can have manual RUN, STOP, STANDBY and UNKNOWN intervals with
source, evidence, author, time and reason. Only the original ENGINEER can correct,
review or void its log. ADMIN does not inherit engineering write permission.
Other authenticated roles can read the complete append-only revision history.

- A new log starts unreviewed/UNKNOWN in the form. Verified evidence requires an
  explicit fresh attestation. Software does not validate a real operating state.
- Both endpoints must be exact zoned instants, end strictly after start, not in
  the future. Date-only and unknown-offset `-00:00` values are rejected. Open
  intervals are not estimated to now. The current repair parser retains its
  separate ability to represent genuinely proven zero-duration work intervals.
- Correcting or voiding a log creates another immutable revision. Optimistic
  version checks reject stale forms and UUID request keys prevent duplicate saves.
  Transactions preserve the log/revision pair on failure.
- New asset identities are checked using the existing bounded GET-only Mart.
  Source failure preserves form input. Existing local logs remain correctable
  during an outage; there are no source writes, new collectors or asset enrollment.

The coverage service sweeps half-open intervals clipped to the full calendar year
in Asia/Jakarta. Adjacent endpoints do not overlap. Every overlap is a conflict,
even two agreeing RUN records; neither is silently preferred or counted twice.
Draft/voided revisions do not contribute. RUN, STOP, STANDBY, UNKNOWN, uncovered
GAP and OVERLAP are separate durations. Known coverage is RUN+STOP+STANDBY without
conflicts. Observed operating seconds are RUN only, never calendar hours. A fully
UNKNOWN/uncovered/conflicted record set does not establish zero runtime.

**The current denominator is the full calendar year, not year-to-date.** In an
open year, the unobserved future is explicitly included under uncovered/future
and annual MTBF readiness stays insufficient. Nothing is extrapolated. All known
coverage and operating values are withheld if more than 5,000 retained logs for
that asset would be materialized. This is an explicit conservative limit.

## Versioned local methods and failure scope

A method is append-only per exact asset and calendar year; only its original
ENGINEER can create later revisions. It records required function, failure
criteria/exclusions, exposure basis, recurrence policy, active-repair versus
restoration MTTR, minimum operating coverage, incomplete-episode policy, evidence,
reason, actor, version and explicit unresolved choices.

Saving an engineer method does not approve it. New versions mark
`organization_approval=SEPARATE_SUPERVISOR_DECISION`; historical versions retain
their original metadata. The current approval is a separate snapshot decision,
see [Supervisor workflow](reliability-supervisor-approval.md).
A locally reviewed method is not an approved organizational standard. In particular:

- Failure-observation completeness is an explicit evidence-backed engineer
  attestation, separate from the percentage of known operating states.
- The engineer must separately attest that the reviewed failures match the
  method's function/population. No text similarity or role implies this decision.
- Attestation is tied to a SHA-256 fingerprint of the asset's current observation
  and review versions, plus the check time. A newly recorded/corrected event or
  review requires fresh reconciliation. Unknown and out-of-year records are kept
  in this conservative fingerprint because their correction may change the cohort.
- The current implementation supports full onset-year cohorts and withholding
  incomplete populations. Selecting a lower minimum coverage never permits
  scaling partial RUN time to a whole-year failure denominator.

Method and operating evidence are included in JSON and immutable snapshots.
Changes produce a new evidence hash; old snapshots are never recalculated. The
report also exports the event version and rule reviewed, plus duplicate target
versions, so stale decisions have replayable evidence. Older snapshots without
these additive sections remain readable.

## Independent readiness, without manufactured KPI

`readiness.mtbf`, `.mttr`, `.active_repair` and `.restoration` expose independent
blockers. `LOCAL_EVIDENCE_READY` means local evidence sufficiency only. Official
MTBF and MTTR remain null / NOT_READY until a Supervisor approves a current
snapshot for those metrics. Availability remains unavailable.
The existing descriptive means retain their numerator, denominator and exclusions.

MTBF requires matching exact asset/function/year, failure census reconciliation,
closed annual window, a failure census rechecked after that window ended, positive eligible exposure, no gap/UNKNOWN/OVERLAP and an
eligible operating state immediately before each reviewed onset. Zero eligible
failures does not become zero or infinity. Recurrence is unestablished when a new
onset precedes verified restoration of the previous episode; reopen is not
silently treated as a fresh failure.

MTTR does **not** depend on operating logs, historian integration, WO availability
or calendar runtime. Active repair and restoration have their own numerators,
denominators and completeness checks. A known full restoration episode can be
ready locally while active repair is unknown, and vice versa. Their completed
sample means retain full cross-year episodes in the onset year, not clipped to
exposure windows. Incomplete, stale, conflicting and uncertain evidence is not zero.

## Repair editor and trends

The repair editor offers separate start/end date-time controls, explicit offsets,
and add/remove actions for up to 20 intervals. Gaps represent excluded waiting
and logistics, not work duration. Existing instants retain their explicit offset;
changing it changes the stated source time, not an inferred timezone. Empty rows
are not zero-duration work. Invalid original text retains the plain-text control,
and the existing textarea remains the no-JavaScript fallback. Server validation,
attestation and version protections remain authoritative.

Monthly counts and Pareto use only current locally reviewed failures with precise
onsets on this exact asset/year. Unreviewed/stale/non-failure/duplicate/voided
records and WO counts are not added. The Pareto groups **observation types**, not
validated root causes. Missing onset and partial evidence are explicitly labelled.
These are local reviewed record counts, not a complete organizational failure
census; overlap/recurrence concerns remain visible in readiness and quality.
Never sum multi-asset record counts into unique plant incidents.

## Storage and publication boundary

The additive migration defines operating logs, immutable log revisions and
versioned reliability policies in the existing owning local SQLite store.
Publication does not apply it. Before any separately authorized activation,
verify the target, make and verify a consistent backup, rehearse the addition,
and preserve all existing rows. Test fixtures use in-memory SQLite only.
Operational identities, runtime records and local preservation manifests are
not part of this public package.

## Verification

- New hermetic feature tests cover log create/review/correct/void, audit, idempotency,
  stale forms, cross-asset keys, permission denials, invalid/future/unknown-offset
  times, adjacent/cross-year/leap-year intervals, agreeing/conflicting overlaps,
  source outage, atomic rollback, explicit limits and UNKNOWN-only evidence.
- Method/readiness tests cover independent MTTR without logs/historian/WO source,
  separate active/restoration completeness, unresolved recurrence, zero failure,
  complete state coverage without failure census, version scope and fingerprint
  invalidation. Snapshots, downloads and escaping are verified.
- Browser QA passed **10 scenario groups** on new temporary SQLite and mocked
  HTTP only, including complete log/repair/method flows, audit/stale tabs, overlap,
  source outage, immutable snapshot, ADMIN/SUPERVISOR/MANAGER denial, no-JS fallback,
  Cancel/Back and 320/390/768/1440 px layouts. There were no page errors; all 47
  recorded source requests were GET to the fake host. Desktop operating and mobile
  repair screenshots were visually inspected. This is fixture QA, not validation
  of actual operating evidence. Artifacts are retained in
  the private temporary QA directory.
- Final full checks: **962 PHP tests**, **66 frontend tests**, Pint, Composer
  validation/platform checks, Vite build and whitespace checks passed. Three
  additional final browser checks verified coverage labels, expandable blockers
  and 320/390/1440 px layouts.
