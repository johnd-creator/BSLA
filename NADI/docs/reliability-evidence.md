# Reliability evidence and local engineer review

Source implementation prepared on 8 November 2026; runtime activation is separate.
This completes the usable local evidence workflow supported by the retained data;
it does **not** claim complete operational reliability data or approved KPI values.

## Where to use it

- **Data & Laporan → Reliability**, or **Master Asset → detail → Reliability**.
- Select an exact BSR/IP asset and calendar year. Source inventory and Registry
  membership remain different; the existing Mart selects the appropriate scope.
- **Log Gangguan → event detail → Buka review reliability** reviews an individual
  asset's function, evidence and time boundaries. The original engineer may review
  each member asset; other users can read. ADMIN has no engineering write bypass.
- Download **evidence JSON**, or save a local immutable review snapshot. Snapshots
  retain their original report and hash and warn when the current evidence differs.

No source mutation, collector call, discovery, backfill, fuzzy asset mapping,
auto-registration, PI login, worker restart or production deployment is involved.

## What is recorded, and what is not inferred

One observation may concern several assets and WOs. A `ReliabilityReview` is an
append-only review of **one event and one exact member asset**. It records:

- `uncertain`, `failure` (loss of required function according to engineer),
  `not_failure` for this asset, or `duplicate` of a checked earlier event;
- required function and how it was lost, supporting evidence, reason, actor,
  UTC review time, event version and rule version `local-evidence-v1`;
- optional precise failure onset and return-to-service after required testing;
- active repair intervals, evidence explaining boundaries/excluded waits, and
  explicit `unknown`, `ongoing`, `completed` or `not_applicable` repair state;
- the original observation/membership/WO-link snapshot that the engineer reviewed.

This is a **local engineering review**, not a new organizational approval role.
The owner must actively attest to checking evidence. Planned stop, duty/standby,
trip, causal/affected roles, a failure code, CM, WAPPR, CLOSE, labor hours and WO
actual elapsed duration do not classify loss of function or generate repair times.
Event-level recovery is not copied onto each member asset. Missing recovery does
not mean the asset remains stopped. Source boolean downtime is not hours.

Duplicate linking requires the same asset, an earlier active event and its current
failure review. The target's event and review versions are retained. Chains and
cycles are rejected. A target correction or superseded target rule invalidates the duplicate decision.
Different events sharing a WO are not automatically merged or counted as one.

## Time and calculation boundaries

Inputs use exact ISO-8601 seconds with an explicit offset or Z. Naive, date-only,
invalid-calendar, future, reversed and unsupported-offset instants are rejected.
The RFC 3339 unknown offset `-00:00` is rejected rather than normalized into
verified UTC; Z and `+00:00` remain valid when supported by the source.
Unknown times can remain empty; date-only observations retain their literal date.
There is no invented midnight. Each active interval must have both endpoints,
remain within known failure/restoration bounds and not overlap another interval
of that episode. Parallel crews are not summed. Up to 20 intervals are accepted.
Zero duration is retained only when both provided endpoints genuinely match.

The report has two **descriptive reviewed-local-sample means**, kept separate:

1. Active repair: sum of completed active work interval seconds / number of
   completed eligible repair episodes, expressed in hours. Waiting/logistics are
   excluded by leaving gaps between intervals. Ongoing episodes are not averaged.
2. Restoration: sum of complete failure-onset-to-return-to-service seconds /
   number of complete eligible restoration episodes, expressed in hours.

A precise failure onset is required for either sample to establish the annual
cohort. Known repair intervals without that onset can still be retained for
review, but are not quietly assigned to a cohort mean. A missing numerator is
null, not zero. Status and numerator/denominator accompany every sample.

The annual window is `[January 1, next January 1)` in Asia/Jakarta. A complete
cross-year episode belongs in full to its **onset year**, not again to its finish
year and not clipped to calendar hours. Review queues can fall back to observation
instant or literal date with an explicit basis, but this does not invent exposure.
All retained years are checked for overlapping episodes on the same asset; the
involved events are flagged and excluded from both descriptive means. Prior-year
intervals can therefore block a current-year sample. Zero-duration intervals do
not occupy time. Unknown, stale, rejected, duplicate, voided, incomplete and
ongoing records remain visible as separate quality categories. Complete-case
means can be biased toward shorter repairs; the page explicitly warns about this.

**MTBF and MTTR remain null / NOT_READY without a current Supervisor decision**
for the selected ready metrics; a descriptive sample alone never qualifies.
Availability remains null. Organizational definitions, eligible population, completeness,
coverage and recurrence/reopen policy are not approved by software. Exposure is
not supplied by the WO period, calendar length, asset status, six-hour volatile
cache or absence of events. Verified historian **or verified manual operating
logs** can supply future exposure once mapping, quality and coverage rules are
agreed. Historian is not the only missing decision or evidence source.

## Evidence report and reproducibility

`GET /reliability/evidence.json?asset_ref=...&year=2026` returns the bounded
`nadi.reliability-evidence.v1` report with:

- exact asset identity, period/basis, rule, observed-at, source freshness UNKNOWN;
- nullable official metrics, sample numerators/denominators and overlap exclusions;
- local quality categories, observation/operating coverage unknown and blockers;
- retained-Mart annual WO counts/distributions, unknown dates and duplicates;
- PdM counts by local measurement date, date precision, linked analysis and a
  version fingerprint that changes after measurement/analysis corrections;
- observation snapshots, member roles, event/review versions, reviewer ID/time,
  classified function/evidence, per-asset time boundaries and structured WO links
  with exact WO asset owner and whether it matches the selected report asset;
- a SHA-256 evidence hash (excluding only the read timestamp).

For multi-asset events, the report separates WO links belonging to the selected
asset, another event member, and removed relationships. A historical snapshot
without recorded WO ownership says unknown; the UI does not assign the primary
asset’s WO to an affected asset or rewrite old snapshots.

WO date basis is **actual start in WIB**; failure cohort is reviewed onset;
PdM uses recorded measurement date. These populations are not added or silently
joined. WO aggregate zero means zero retained Mart records in that scope, not
zero operational failures. Source outage yields unavailable/null WO context while
local evidence remains readable. HTTP success is not source freshness.

At most 2,000 local observations for an asset are materialized, with no silent
truncation: the report flags PARTIAL and withholds sample values at the limit.
PdM fingerprints stream in bounded batches. API reads retain the existing DTO
allowlists and budgets. JSON is downloadable with no-store/private headers and
no raw vendor payloads or credentials. It is not uploaded or shared externally.

Snapshots are append-only by route, stored in the existing SQLite, not a new
operational database. Later corrections do not rewrite them. Their complete
report provides the values, intervals, exclusions and definitions needed to
reproduce the sample arithmetic. A different current hash warns that evidence,
period context or source availability changed; it does not prove which source
is newer or grant a new approval. Unknown source freshness remains unknown.

Local evidence is read through one SQLite snapshot. Source HTTP finishes before
that transaction starts. Standalone report reads use a deferred transaction, not
the existing IMMEDIATE write policy; the owning store, journal settings and write
configuration are unchanged. A two-connection WAL fixture verifies that an event
and its review stay on the same version while a concurrent correction commits.
The following report sees the newer version. Interrupted reads roll back cleanly.
This is local consistency, not an atomic snapshot across SQLite and the Mart.

## Integrity and permissions

- Review POST uses the existing event-owner ENGINEER gate. All active authenticated
  roles can read. Non-member assets and cross-event idempotency keys fail closed.
- Request UUID prevents repeated saves. Event-version and prior-review-revision
  checks reject stale forms. The owning event update is serialized inside the
  transaction; the unique event/asset/revision constraint is the race backstop.
- Reviews never overwrite earlier reviews, mutate source events or change log
  classification. Observation or WO-link corrections advance the existing event
  version and make associated reviews stale until explicitly checked again.
- Voiding an observation prevents new review and excludes it from sample means;
  history remains readable. A save failure rolls back the review atomically.
- Only ENGINEER can save an evidence snapshot. Read-only roles have no write UI
  and receive server-side 403 on attempted writes. There are no delete/update
  routes for snapshots or review history.

## Storage and verification

The additive migration defines `reliability_reviews` and `reliability_snapshots`
in the existing local Laravel store. Publication does not apply migrations.
Back up and verify the actual owner store before separately authorized activation.
Operational records and real-data pilot evidence remain private.

Run the complete Laravel suite, Pint, frontend tests and the Vite build. Focused
`ReliabilityEvidenceTest` and `ReliabilitySnapshotConsistencyTest` exercise mocked
HTTP and in-memory SQLite, including stale review/snapshot and transaction guards.
These software checks do not establish engineering acceptance or official KPIs.

## Remaining engineer/data work

1. Enter actual observations and reconcile their event identity/multi-asset roles.
2. Review loss of required function and justified duplicate/non-failure exclusions.
3. Supply real per-asset active repair and restoration boundaries with evidence.
4. Approve organizational definitions, population, annual cohort, coverage minimum,
   planned stops/standby, recurrence/reopen and incomplete-episode policies.
5. Provide validated operating exposure with known gaps, quality and provenance,
   from authorized historian mapping or engineer-validated manual operating logs.
6. Only then qualify official KPI calculation, reconciliation, production access,
   persistence/backup and rollout. No completeness percentage is invented now.

## Governed calculations and selected-metric approval

[Operating evidence and readiness](reliability-operating-readiness.md) add versioned
methods, manual exposure intervals, explicit gaps/overlaps and separate MTBF/MTTR
gates. [Pilot calculations](reliability-calculation.md) retain deterministic
numerators, denominators, exclusions and immutable evidence hashes.
[Supervisor decisions](reliability-supervisor-approval.md) may approve selected
ready metrics for one exact asset/year snapshot; changed evidence, method or engine
makes the current approval stale without rewriting historical decisions.
Availability remains unavailable. The [MTTR pilot workflow](mttr-real-data-pilot.md)
requires actual onset/restoration evidence; WO elapsed time is not a substitute.

Publication includes additive migration definitions only. It does not apply them
or approve any operational method or KPI.
