# Reproducible pilot calculation, trace and failure charts

This extends [manual operating evidence and readiness](reliability-operating-readiness.md).
The earlier implementation supplied policy versions, readiness and descriptive
sample means, but did not calculate MTBF or provide a calculation audit page.
This increment closes that arithmetic/trace/visualization gap. It does **not**
invent organizational authority or make local pilot numbers official KPI.

## Practical workflow

1. Record real observations and review loss of function per exact asset. Reconcile
   duplicates, onset, restoration, active-work intervals and incomplete episodes.
2. Supply real operating evidence for MTBF, and reconcile gaps, unknown states and
   overlaps. MTTR does not require historian, operating logs or WO availability.
3. Record the local method for the asset/year, including the chosen MTTR definition,
   function/population, failure census evidence, coverage, recurrence and exclusions.
4. Open Reliability. **Hasil hitung pilot & status resmi** shows a number only when
   local method/data gates are satisfied. Missing gates remain explicit and null.
5. Use **Telusuri pembilang & penyebut** to reconcile event/review versions, reviewer,
   times, active intervals, numerator contributions, exclusions and the exact
   operating segments matched to each onset. Event and exposure tables paginate
   independently, 20 rows per page. Their filters never alter the calculation.
6. Save a snapshot from the report. Download the complete evidence JSON for a
   review packet containing the method, source record revisions, arithmetic,
   engine version, basis hash and result hash. This action does not submit or
   publish anything externally and does not approve the result.

When an observation or review changes, the previous local scope attestation
becomes stale. Reconcile it explicitly and create a new method revision before
using a newly calculated pilot. Historical snapshots retain their original
engine/results/trace. Older snapshots without this trace explain that limitation
and are not silently populated from the current database.

## Deterministic calculation contract

`ReliabilityCalculator` is a read-only calculation over one captured report. It
performs no HTTP, database writes or source collection. Result fields include:

- `engine_version = nadi-reliability-calculation-v2`, asset, annual WIB period,
  policy identity/revision and method schema version;
- separate `pilot.mtbf`, `.mttr`, `.active_repair`, `.restoration` values, formulas,
  units, raw numerator seconds, denominator episodes, exact event IDs and blockers;
- `event_trace`, including event/review/rule versions, reviewer/time, eligibility,
  exclusions, per-episode durations, source evidence, active intervals and WO context;
- `exposure_trace`, including clipped half-open segments, states, eligible seconds,
  exclusions, log IDs and source record versions in `operating_records`;
- `basis_hash` over the method, local evidence, period and readiness, plus a
  `calculation_hash` over the complete result. The read timestamp and unavailable
  external WO/PdM context do not change the local arithmetic basis.

The engine recomputes durations from endpoints and checks stored arithmetic and
exposure sequencing. It does not merely display a cached WO-derived number.

MTBF numerator is eligible RUN, or RUN+STANDBY only when explicitly selected,
with the same exact asset/function/year as the failure denominator. A full annual
window must be complete, closed and reconciled; the failure census must have been
checked after that year ended. Gap/UNKNOWN/overlap, unknown definitions, unresolved
recurrence and onset outside eligible exposure withhold the value. No scaling to
calendar hours, no zero/infinite MTBF for zero failures, and no WO count as failure.

MTTR uses the selected active-repair or restoration definition. Its two component
metrics use their own completed episode populations and numerators. Active work
excludes gaps between work intervals; restoration spans onset to return to service.
Complete cross-year episodes belong fully to their onset year. Proven zero duration
is zero; no numerator is null. Partial trace totals are labelled as partial and
never promoted to a KPI. Descriptive complete-case sample means remain available
separately when pilot population gates are not satisfied.

## Pilot versus official

`PILOT_CALCULATED` means local evidence and the recorded method support the
arithmetic. The pure calculator never authorizes itself: `calculation.official`
remains null with `SUPERVISOR_APPROVAL_REQUIRED`. Effective official status is a
separate, versioned decision in `report.approval` and `report.metrics`.

The user has now designated **SUPERVISOR** as approver. Engineer prepares evidence,
method versions and snapshots. Supervisor explicitly approves the method and one
or both ready metrics for the exact asset/year/snapshot. Unselected metrics remain
null. Evidence, method or engine changes make approval stale; revocation and
supersession retain the original audit. MTTR approval does not require MTBF data.
See [Supervisor approval workflow](reliability-supervisor-approval.md) for the
scope, permissions, hash contract, migration and tests. No real data was approved
by this implementation.

## Useful trends without mixed populations

The report offers server-rendered SVG charts and accessible evidence tables for:

- counts of current reviewed failures;
- total completed active-repair hours;
- total completed restoration hours.

A basis selector and onset-month selector filter only the display, including
historical snapshots. The report, arithmetic, saved content and hashes remain
unchanged. Monthly episode links open the exact filtered calculation trace. Both
controls and charts work without JavaScript.

Failure records need a current review, precise onset and exact selected asset/year.
Conflicting intervals and unresolved recurrence are excluded; known missing onset
and exclusion counts are shown. Duration charts use their own complete-episode
populations and disclose omitted incomplete/not-applicable episodes. Their totals
are not calendar downtime, availability or monthly MTTR estimates. Complete cases
can be biased. Zero-height/count months mean no eligible retained records, not
proof that no operational failures occurred.

Pareto groups observation types, **not assumed root causes**. Sorting is stable;
share/cumulative percentages use the selected measure. A proven all-zero duration
population does not divide by zero: percentages are explicitly undefined. Never
sum per-asset counts into unique plant incidents.

## Checks and activation

- Added fixture arithmetic: 8,754 observed RUN hours and two eligible failures
  yield MTBF pilot 4,377 hours; 3 active-work hours / 2 episodes yield 1.5 hours;
  6 restoration hours / 2 episodes yield 3 hours. These are synthetic tests, not
  the user's operating data.
- Tests cover missing policy versus descriptive sample, MTTR without logs/source,
  explicit zero, inconsistent stored arithmetic, bad exposure sequence, separate
  trend populations, recurrence/conflict exclusions, filter/hash invariance,
  immutable historical engine results, old-snapshot compatibility and read-only
  roles. Invalid filters fail before source reads.
- Browser QA passed 10 scenario groups: pilot math, filters/drilldown, Back/Forward,
  trace empty state, saved engine/trace, repair correction and stale attestation,
  explicit re-reconciliation, source outage, all read-only roles, no-JS flows and
  320/390/768/1440 px layouts. There were no page errors; all 81 recorded source
  requests used GET against the fake host. Desktop trace and mobile chart
  screenshots were visually inspected. Artifacts: the private temporary QA directory.
- Pilot increment regression: 971 PHP tests, 67 frontend tests, Pint, Composer validation/
  platform checks, Vite build and whitespace checks passed. Tests use hermetic
  SQLite/mock HTTP; browser writes use a temporary SQLite and port 8042 only.
- The pilot/chart increment needed no migration (the later Supervisor audit adds
  one compatible table): calculations/trace are stored inside existing immutable
  evidence snapshots. No actual log, rule, failure or organizational approval was
  fabricated in the user's development SQLite. No collector restart, production
  deployment, commit or push was performed.
