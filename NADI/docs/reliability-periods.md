# Flexible reliability and Wellness evidence periods

Implemented locally in the existing NADI Laravel workspace. Calendar-year,
rolling and custom reports now support exact-period method revisions, pilot
calculations and Supervisor decisions. This does not supply real engineering
observations, decide a method for an engineer, or approve any actual result.

## Period selection

Reliability, manual operating coverage and Asset Wellness accept a calendar year,
the last 3/6/12 calendar months, or an inclusive custom date range. A preset ends
**yesterday in Asia/Jakarta** unless an explicit historical end date is supplied.
For example, 3 months ending 8 November 2026 selects 9 August through 8 November.
Calendar-month arithmetic disables month-end overflow; it is not 90/180/365 days.
Custom ranges require valid dates from 1900, start no later than end, and an end
before today. Partial current-day reporting is not enabled. The existing year
option still represents the full year, including unknown future coverage in an
unfinished year, exactly as before.

API query: `period=3m|6m|12m|custom`, optional preset `end_date`, and required
`start_date`/`end_date` for custom ranges. Omitted `period` retains `year` behavior.
Rolling selections resolve once to fixed dates in links, pagination, download,
method forms and snapshot saving. These filters do not change retention policy or
start source acquisition/backfill.

## Evidence, arithmetic and boundaries

Selections become `[start 00:00 WIB, day-after-end 00:00 WIB)` for arithmetic.
Date-only observations remain literal dates, not measured midnight instants.
A failure enters the cohort through its exact reviewed onset. A completed repair
or restoration contributes the **whole episode**, including completion after the
report end. It is not assigned again simply because it finishes in a later,
non-overlapping period. Overlapping rolling reports are not additive.

Operating exposure alone is clipped. Verified RUN, and STANDBY only when the
engineer chooses that basis, contribute observed exposure. UNKNOWN, gaps,
overlaps and draft/voided records do not become runtime. Coverage uses the exact
selected interval denominator. No WO-count, labor, calendar-hour substitution or
extrapolation is used. An onset exactly at the window start still lacks preceding
verified exposure inside that window and remains unqualified for MTBF.

MTBF requires a closed period, complete non-conflicting operating coverage,
positive eligible exposure, compatible failure onsets and an explicitly reconciled
failure census checked through the interval end. A configured minimum below 100%
does not authorize filling missing time. MTTR does not need operating logs or
historian; it uses the chosen active-repair or restoration definition, complete
eligible episodes and the common method/failure-quality gates. Unknown, ongoing,
stale and conflicting evidence remain visible and may withhold results. No
failure records do not produce MTBF zero or infinity.

All retained events are checked for overlap/recurrence, including episodes before
the selected window. Existing 2,000-observation/5,000-operating-log limits and
partial safeguards remain. PdM uses measurement dates and exact context. Trends
use distinct YYYY-MM buckets across years; charts over 24 months defer to the
readable monthly table. Trace and queue filters never alter stored arithmetic.

## Method and Supervisor workflow

1. Select an exact asset and fixed period, record/reconcile actual evidence.
2. Open **Aturan KPI periode & versi**. The engineer records required function,
   failure definition, exposure basis, MTTR definition, recurrence/incomplete
   policies, coverage decisions and supporting evidence. Unknown choices remain
   unknown. Existing method ownership and stale-form checks apply.
3. Reconcile the failure census for that exact period. Saving a method does not
   automatically review events or approve KPI. A later event/review change makes
   the scope attestation stale.
4. When gates pass, inspect pilot MTBF/MTTR and numerator/denominator trace.
5. Save an immutable snapshot. A Supervisor can approve selected qualified metrics
   and the snapshot's method, or revoke that scope's latest decision. Changes to
   evidence, method or engine make its approval stale; old decisions and reports
   remain intact. A snapshot from the earlier recap-only stage must be replaced
   with a new snapshot after current method/evidence reconciliation.

Annual methods/approvals and each exact custom range are separate, even when a
custom range happens to cover a full calendar year. An approval does not apply to
another asset, a child asset or an overlapping range. Moving rolling dates creates
a new exact scope; no automatic method, census attestation or approval is copied.
Only the existing SUPERVISOR gate can approve. ADMIN alone, MANAGER and ENGINEER
cannot approve; Supervisor does not gain engineering edit rights.

## Retrospective reporting is not as-of knowledge

A historical filter uses **current reviews of historical events**. Later review,
correction or restoration can change a recap. It is not a reconstruction of facts
already known at the historical date and does not claim current asset condition.
A saved Reliability snapshot captures its own read time, exact period, original
report, method, evidence and engine basis. Later reads compare, not overwrite it.
Source freshness remains UNKNOWN unless independently established.

Wellness is still a read-only evidence view, not a cross-source immutable Wellness
snapshot. Active priorities are labelled current regardless of the historical
period. Its historical PdM age comparison is relative to the selected period's end
**using current revisions**; the annual compatibility view keeps age relative to
today. Neither means a later analysis was known at the earlier date.

## Wellness remains configurable draft, not an invented score

Each exact range can store its own proposed criticality basis, required evidence,
maximum ages, exact-point PdM thresholds, component weights and normalization text.
No annual proposals or illustrative weights are inherited into a range. Missing
weights stay null. Partial/non-100 totals are visibly incomplete proposals; four
weights totaling 100 still do not validate the method or produce a score.
Normalization text is a proposal, not executable or approved scoring logic.

PdM comparisons enforce exact template/point/unit/method/instrument/mode/context,
anchor fingerprints, date precision and ambiguous ordering. A changed anchor
withholds comparison; the latest missing/invalid reading is not replaced with an
older convenient one. Draft threshold comparisons are not health categories or
alarms. Component evidence completeness, confidence, normalization and Wellness
method/result approval still require domain decisions. Therefore actual Wellness
scores remain null rather than being inferred from WO counts, missing data,
Reliability approvals or an assumed 45/25/20/10 formula.

Mart currently supplies annual WO aggregates, not arbitrary-range counts. Range
WO counts remain unavailable, never prorated or turned into zero. Annual WO links
are labelled context. No collector expansion or backfill was started.

## Storage and migration

`2026_11_10_000001_add_exact_reliability_period_scopes.php` adds one nullable
`period_key` and one lookup index each to `reliability_policies`,
`reliability_approvals`, and `asset_wellness_policies` in the existing SQLite.
Null means the legacy annual scope. Ranges use a SHA-256 identity of exact
boundaries and timezone; immutable rule JSON also retains the full period.
No existing rows, annual hashes, indexes or constraints are rewritten.

The existing unique `(asset_ref, year, revision)` constraints remain. Revision
numbers are allocated across that asset/start-year transactionally, so a scope's
revision history may have gaps. Optimistic comparisons and ownership checks use
the latest revision of the exact scope, not another range's revision.

Snapshots reuse their original table. `year` is the start-year anchor for ranges;
report JSON boundaries/kind are authoritative for listing/idempotency and all
approval checks. Legacy quality keys `in_year`, `out_of_year`, `unknown_year` and
`cross_year_restoration` are explicitly documented as selected-period keys in
range report metadata. Annual report payloads retain their prior shape/hash.

Publication includes the additive migration definition only. Applying it to any existing store requires separate authorization, verified target identity, and a restorable backup. No runtime database is changed by this publication.

Missing migration fails closed for range method/approval writes while annual
compatibility and evidence reads continue. Down-migration refuses to remove period
identity if any range history exists. Use a forward-compatible fix after real
range records exist, not a whole-store restore that could lose newer work.

## Publication verification

See [public-source integration](publication.md) for the checks run against this
publication branch. Historical feature QA is not a fresh browser pass or an
engineering signoff. No source records, private catalogs, runtime data, database
activation, merge or deployment are included in publication.
