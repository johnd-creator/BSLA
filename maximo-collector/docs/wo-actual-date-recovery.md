# WO actual date lineage and bounded recovery

Requirement: **NADI-MAXIMO-WO-ACTUAL-DATE-RECOVERY-01**, including the PO's
status-aware completeness addendum. Baseline main: `6bff0a5c5b67b2e5137b50c1d4d0063416f65686`.
This candidate is not operational activation, historical-population recovery or
KPI eligibility. Private operational evidence is kept outside Git.

## Field lineage audit

| Boundary | Baseline behavior | Candidate behavior |
|---|---|---|
| Verified MXWODETAIL contract | `actstart`/`actfinish` are TIMESTAMP candidates; canonical select already requests them | Same verified scalar fields; exact BSR/IP identity and original offsets |
| Routine `WORK_ORDER_SELECT` | Neither actual field selected | Both selected; schedules, limits, cursors and F01–F24 guards unchanged |
| Legacy mapper/store | Actual fields discarded; unrestricted replacement upsert | Allowlisted `sources.maximo.actual_dates` evidence; locked source-version checks |
| Local `_work_order_payload` | Both actual fields unconditionally NULL | Only exact identity/version-bound retained dates replay |
| Canonical mapper | Actual date support; naive/invalid input could fail a whole row | Zoned dates retain their instant and original text; unknown zones/invalid values remain evidence and canonical NULL |
| MartWriter | Blind update could erase dates or apply stale observations | Older/unknown versions cannot replace newer rows; NULL cannot retract dates; equal-version conflicting dates fail atomically |
| Mart/API | Existing `actual_start`/`actual_finish` columns and MaintenanceView fields | Existing fields reused, no schema or API migration |

`changedate`, scheduled/reported dates, status, downtime and labor never supply
actual dates or repair duration. Zero evidence stays zero. Status and raw Work
Type remain source values; this package introduces no classification or KPI rule.

## Retention decision

Use the existing JSON column rather than add legacy normalized columns. The
versioned allowlist stores only WO/Asset/site/org identity and each actual clock's
state, original scalar, normalized ISO timestamp and source observation version.
No raw response, person data or credential is added. Clock states distinguish
VALID, MISSING (returned null/empty), UNAVAILABLE (not returned), INVALID and NAIVE.
An omitted field cannot establish why it was omitted or that source storage is null.
Valid strings retain fractional precision and original offset; naive values never
receive an invented timezone. Date-only values are invalid actual timestamps.

A missing/invalid newer observation cannot retract an existing valid date. That
retained field keeps its original observation version. Newer explicit valid dates
may correct a date; conflicting dates at the same source version fail. Older
observations are no-ops. No source-null correction rule is authorized here. Local rows without source clock
proof stay UNAVAILABLE; reconstructed NULLs never become observed source nulls.
Invalid originals excluded by the retention size/type cap remain INVALID evidence.
Field-level observation versions govern valid corrections even when a newer row
previously carried a missing clock.

## Evidence-derived completeness and status matrix

`wo_actual_date_completeness.classify_dates` and `status_date_matrix` are read-only
reporting functions. `report_cohort` joins exact staged source, legacy and Mart
evidence without making source requests. States are:

- `ACTUAL_DATES_AVAILABLE`: both Mart dates available.
- `START_ONLY` / `FINISH_ONLY`: one Mart date available; independent missing-reason flags remain visible.
- `SOURCE_CONFIRMED_EMPTY`: both returned source clocks explicitly empty at the exact current source version.
- `SOURCE_NOT_YET_VERIFIED`: missing evidence has not been verified.
- `COLLECTOR_PROJECTION_GAP`: a missing Mart clock has verified source/retained evidence.
- `SOURCE_TIMESTAMP_INVALID`: source evidence has an invalid or ambiguous timezone/value.

Classification priority is invalid → verified gap → date availability → confirmed
empty → unverified. Matrices independently count both/start-only/finish-only/both
missing, confirmed-null, unverified, pipeline loss, timestamp issues and identity/
version mismatches. Missing-reason counts may overlap and must not be summed as
exclusive populations. Source-confirmed-null counts require an actual returned null;
returned empty strings are confirmed empty but do not count as source nulls. A missing field is not a confirmed source null. Old empty
observations cannot establish current emptiness after a source version change.

Original status is the grouping key. WAPPR/WMATL remain in all coverage totals and
receive a neutral note that dates may not yet be recorded; this establishes no
execution state. Genuine dates remain available for these statuses. COMP/CLOSE
with missing dates receive a completeness-review flag, never fabricated dates or
a complete-evidence designation. Advanced-status flags prioritize review only.

## Bounded operator mechanism and authorization

The service module `src.services.wo_actual_date_recovery` exposes separate stages:

1. `plan_cohort(db, wonums)`: read-only, 1–10 unique exact WOs, existing registered
   parent, equal zoned legacy/Mart source versions. Seal with `seal(plan)`.
2. `fetch_cohort(client, plan, completed=..., checkpoint=...)`: existing owning
   OslcClient, GET-only exact predicates, verified fields, one page per WO, budget
   20 business requests (including detail/auth retry requests), existing 1s floor
   and 1MiB cap. It requests only identity/date/status/version context. No broad
   traversal, automatic retry loop, cursor update or write occurs. A checkpoint
   callback privately persists each validated result. WO detail resource links carry
   the exact selected fields. A WO collection auth retry consumes the same request
   budget but does not count an expired response as a successfully visited page;
   the once-only retry and successful-page/loop caps remain enforced. Resume revalidates completed
   identities and skips their source requests. HTTP/auth failures stop the run.
3. Rehearse against a fresh full private PostgreSQL backup and independent isolated
   restore. Compare every restored table fingerprint, exact cohort identity/version,
   resumed normal-worker replay, rollback and unrelated records. Memory-only SQLite
   and six guarded file rehearsals remain additional synthetic checks.
4. **Separate explicit approval required:** `apply_cohort` must receive the exact
   reviewed plan digest and owning database identity. A digest is a pin, not an
   authorization credential. Before invocation, verify source/service ownership,
   fresh affected-row + database backups, independent restore, required reviews/
   exact-head CI and container/data preservation. PostgreSQL requires a durable
   private rollback-receipt callback before commit; callback failure rolls back.
5. Apply one small co-located legacy/Mart transaction through CollectorStore and
   the validating MartWriter. Lock Registry assets first, then WOs, in deterministic sorted order, recheck exact
   identities, current Registry membership and both source versions. A changed
   source version requires normal acquisition and a new plan, not clock rebasing.
   Only legacy clock JSON and Mart clock/evidence fields may change. All source,
   projection and collection cursors remain unchanged. A staged subset supports
   bounded resumption; replay is idempotent.
6. Privately checkpoint the versioned `wo-actual-dates-journal/2` receipt with
   owner-only permissions, fsync and durable host acknowledgment before commit.
   It contains the pinned plan, diagnostic before/after rows, exact changed leaves,
   created-container markers and date/provenance read guards. JSON absence differs
   from explicit null. Its digest detects damaged evidence; it is not authorization.
   Full-row seals are diagnostic and never the sole rollback CAS criterion.
7. `rollback_cohort` is separately governed mutation. Under the same deterministic
   locks, validate every cohort member before changing any row. Compare all actual
   values, raw date strings and complete date proof against the saved after guard.
   Restore only changed leaves; remove newly created containers only if empty.
   Preserve independent status, failure code, source changedate and JSON siblings.
   Advance `mart_updated_at` monotonically for a real rollback; never restore its
   old value. Unknown or regressed versions and identity/Registry changes conflict.
8. An advanced overall source version is safe only if legacy and Mart versions
   agree and unchanged, valid, identity-bound per-field proofs remain authoritative
   for both actual clocks. A NULL replay can retain these proofs; a newer valid
   observation, even with the same date, changes provenance and conflicts. Missing
   proof never permits guessing. A conflict rolls back the entire cohort.
9. A returned `ROLLED_BACK` journal includes verified rollback guards and source
   versions; duplicate invocation verifies them and performs no writes. An old
   APPLIED receipt cannot claim an already completed rollback. PREPARED journals
   reconcile lost apply acknowledgments only against the committed after evidence;
   if apply never committed, retry the approved apply. ROLLBACK_PREPARED journals
   distinguish wholly committed versus wholly uncommitted rollback; a mixed cohort
   conflicts. Callback failure aborts the transaction. PostgreSQL requires a durable
   checkpoint on rollback too. Never deserialize untrusted pickle data.

No command defaults to acquisition, schema creation or live recovery. The library
is deliberately invoked by a reviewed owner-private runner, not an unauthenticated
web endpoint. Existing broad `mxcollector backfill` is **not** this bounded repair.
No runtime replacement is approved by this source patch.

## Qualification and operational evidence

The hermetic suite covers future selection/retention, all clock states, fractional
precision/offsets, null/zero, source/identity/version conflicts, stale and equal-version
replay, atomic partial failure, checkpoint failure, independent restore, exact CAS
rollback, every completeness state and neutral status rules. CI's original memory-only
offline guard remains intact. File-backed private rehearsal is separate from that
suite. Canonical Maximo CI must test the immutable PR head on Python 3.11 and 3.12;
independent review and a passing gate are required before any later release.

Runtime audit, authorized bounded source samples, real-cohort restore/replay,
status matrices, coverage counts and service seals belong in owner-private evidence.
A bounded source pilot or isolated recovery cannot establish population-wide source
absence, source completeness, operational recovery or production acceptance.

## Minimum later runtime change and scalable population plan

If separately approved, build one exact-head Collector image and inspect the actual
console imports as well as `/app/src`. Replace only Maximo API, scheduled Maximo
worker and Mart projector using their existing Compose ownership/overrides. All
three import this shared Collector package. Preserve the exact commands, env,
ports, project, volumes, cursor floors and schedules. No NADI frontend/Engineering/
Factual API replacement is needed to expose the already existing date columns.
Pin all three old images/configurations and affected-row recovery receipts. Prove
all unrelated container roles/states unchanged; do not use broad `compose up` or
`down`, migrations, collection bootstrap or data backfill as a release shortcut.

After a separately approved pilot write, prioritize COMP/CLOSE missing-date cohorts
for review while retaining all other statuses in coverage. Each next cohort needs
an exact manifest and finite budget; use current missing evidence and current source
versions, record explicit source-null vs unavailable/invalid cases, apply only
approved batches, stop on auth/scope/version/backup/ownership failure and resume
from sealed private checkpoints. A successful pilot authorizes no larger population.

## Next NADI presentation task

Existing MaintenanceView already exposes `actual_start`, `actual_finish`, status,
canonical identity, scoped source dates and optional source detail. UI must consume actual dates explicitly,
keep planned/reported/changed dates distinct and show timezone/source uncertainty.
The status notes and completeness report are ready as Collector-side functions;
exposing them through a new optional Factual read DTO is a separately reviewed API
follow-up. No broad grant, frontend redesign or KPI eligibility is part of this PR.

## Worker-safe rollback correction — NADI-WO-ACTUAL-DATE-ROLLBACK-FIX-01

The prior full-row CAS blocked a legitimate worker replay: independent failure-code
and source metadata updates changed the seal despite unchanged actual dates. The
correction audits the complete recovery write set:

| Side | Restorable fields | Independent fields preserved |
|---|---|---|
| Collector | `sources.maximo.actual_dates` schema, exact identity and individual field-proof leaves | All row metadata and other JSON paths |
| Mart | `actual_start`, `actual_finish`, `sources.maximo.actstart`, `actfinish`, individual `actual_dates` proof leaves | Status, failure_code, source_changed_at, report/schedule metadata, provenance and other JSON |
| Transaction metadata | No stale value restoration | `mart_updated_at` advances for actual rollback |

CI adds a separate PostgreSQL matrix on Python 3.11/3.12, using a pinned PostgreSQL
image, dedicated disposable database and non-superuser synthetic owner. The final
Maximo gate now requires this matrix as well as the original offline matrix and
six guarded file rehearsals. Production/main selection, exact-head recheck,
read-only workflow permissions and source network restrictions remain intact.

The owner-private full restore reproduced the earlier whole-row refusal and the
independent replay changes. The corrected rollback, reapply, idempotence and newer
start/finish conflict checks passed on that isolated restore. This records tested
candidate behavior, not operational activation. Exact-head CI/review receipts and
all service/image/cohort details belong in the separate private readiness package.

Read-only polling investigation remains separate: PAGE_LIMIT intentionally ends a
bounded traversal without advancing its watermark. Repeated newest-first runs can
replay the same capped window without reaching the old cursor. A recent worker run
or recovered cohort does not prove full source coverage. Preserve request/page caps,
cursor, recovery floor, schedule and scope; any reconciliation needs its own reviewed
operational proposal. No broad recollection is authorized by this correction.
