# Supervisor approval of reliability method and results

The user designated Supervisor as the approver. This is a scoped extension to
NADI permissions, not general WO, budget, risk or production-release approval.

## Workflow and boundaries

1. The ENGINEER records/reviews real observations and operating evidence, reconciles
   the exact asset/function population, and records an explicit local method.
2. The ENGINEER inspects the gated pilot, numerator/denominator trace and exclusions,
   then saves an immutable snapshot. Saving a method or snapshot is not approval.
3. A SUPERVISOR opens that snapshot and inspects the same evidence. The form states
   the exact asset, onset calendar year in Asia/Jakarta, method/engine versions and
   independent metric populations. Nothing is selected or attested automatically.
4. The SUPERVISOR selects MTBF, MTTR or both, provides evidence and a reason, and
   explicitly attests the method and the selected results. Only ready numeric
   pilot metrics can be approved. The method is approved together with the selected
   result, within this scope; it is not a reusable blanket method approval.
5. Current approved values appear as `OFFICIAL_APPROVED`. The pure pilot stays a
   separate reproducible calculation. Unselected metrics remain unavailable.

MTTR can be approved without runtime, historian or WO availability. MTBF still
requires its own complete, closed annual exposure/census gates. MTTR uses the
chosen active-repair or restoration definition and complete onset-year episodes.
Approval applies to no other asset, hierarchy, plant aggregate or year.
Availability remains unavailable; this workflow does not invent its calculation.
No user data is automatically approved by feature activation.

Only accounts with SUPERVISOR may post approval or revocation. ENGINEER prepares
its own records/snapshots but cannot approve unless also explicitly assigned the
Supervisor role. ADMIN-only and MANAGER are read-only for these decisions. A
Supervisor does not acquire engineering edit rights. Existing active-account and
auth-version middleware still applies. This implements role separation; it does
not invent a separate-person/four-eyes rule the user has not specified.

## Immutable decision and current status

`reliability_approvals` is append-only through the application. Each decision has:

- exact asset/year and monotonically increasing scope revision;
- immutable snapshot ID, original snapshot evidence hash, method ID/revision,
  engine version, local calculation basis hash and calculation hash;
- actor ID and SUPERVISOR role at decision time, timestamp, request UUID;
- selected metrics, explicit method/result attestations, evidence and reason;
- original approved metric values including numerator, denominator and event IDs.

Statuses distinguish `AWAITING_SUPERVISOR`, `APPROVED`, `STALE`, `REVOKED` and
`OTHER_SNAPSHOT`. A local event/review, operating log, method or engine change
that changes the calculation hash immediately makes the current approval stale.
All official values are then withheld, even if one number happens to be unchanged.
Engineer reconciles the evidence and saves a fresh snapshot before reapproval.
Unrelated source outages/context changes do not manufacture a local data change.

A new decision supersedes the previous scope decision. Metrics omitted from that
new approval do not silently retain the previous approval. Revocation works even
for stale evidence, removes current official values and retains all historical
values/reasons. There is no approval edit/delete route. Older snapshots without a
current calculation cannot be promoted; they remain readable as historical data.

## Atomic checks, replay and exports

The POST uses the existing owning SQLite IMMEDIATE write transaction. It checks
the expected decision revision, reads the complete current local evidence under
that lock, matches the snapshot calculation hash, and persists the decision. It
performs no source HTTP while holding the lock. Concurrent local writers cannot
change a method/event/log between the comparison and decision insert. A unique
asset/year/revision constraint and scoped request UUID protect against lost
updates and duplicate submission. A stale form receives a visible validation
message; it cannot overwrite a newer decision.

Calculation engine v2 is independent of approval. `calculation.official` always
states that a separate Supervisor decision is required; effective status/values
are `report.approval` and `report.metrics`. `readiness.official_kpi` is the static
approval requirement, not the current decision. The evidence hash fingerprints
the captured evidence before these derived approval fields are applied, so a
decision itself does not invalidate the evidence. Original saved snapshot JSON
never changes. A snapshot page checks current approval separately and labels it.

The separate `approval.json` packet includes current status at the check time,
immutable original report and the snapshot's complete decision history. The
status also identifies the latest decision for the scope if a different snapshot
superseded this one. Exports are private/no-store, do not publish externally and
are available to authenticated read roles.

## Activation and verification

Migration `2026_11_09_000001_create_reliability_approvals.php` defines one additive
table in the existing owning local SQLite store. Publication does not apply it.
Verify the target and consistent private backup before separately authorized
activation; rehearse the migration and verify that all existing rows remain intact.
Do not drop populated audit history or restore an old whole-store backup without
reconciling legitimate newer records. Operational manifests stay private.

Verified after implementation:

- 982 PHP tests, including per-role denial, independent MTTR approval, both ready
  metrics, explicit attestations, zero/missing arithmetic, immutable exports,
  idempotency, stale forms, evidence/method/log invalidation, revocation,
  supersession, exact asset/year scope, old engine/schema and source-outage checks.
- 67 frontend tests; Pint, Composer validation/platform checks, Vite build and
  whitespace checks pass.
- 10 Supervisor browser scenario groups on a separate synthetic SQLite at port
  8044. These exercise actual forms, stale form errors, selective/both-metric
  approval, revocation, correction/reconciliation/new snapshot, non-Supervisor
  server denial, no-JavaScript revocation and 320/390/768/1440 px layouts.
  No page errors; 90 source calls, all GET against the fake host. Mobile form and
  desktop approved/audit screenshots were visually inspected. Artifacts are in
  the private temporary QA directory.
- Earlier pilot/calculation/browser checks are documented in
  [reliability-calculation.md](reliability-calculation.md).

No collector restart, source write, production deployment, commit or push was
performed. Real KPI availability still depends on genuine evidence, chosen
method rules and a Supervisor's explicit decision.
