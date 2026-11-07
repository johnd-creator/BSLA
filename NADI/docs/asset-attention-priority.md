# Asset Attention Priority MVP

Available in the active Laravel development preview at
`http://127.0.0.1:8010/action-board`. No cutover of the existing port 3000 application.

## Workflow

1. Read **Prioritas yang sudah dinilai** and **Kandidat yang belum dinilai**.
2. An ENGINEER selects a candidate or chooses an inventory asset with
   **Nilai prioritas aset**. Canonical identity must be verified through the existing
   inventory / Registry GET API before creating a judgment.
3. Record urgency (**Segera**, **Terencana**, **Pantau**), observed condition, impact,
   reasoning / next step, observation or evidence reference, PIC, and at least one
   target / review date. Unknown conditions and impacts must be described honestly.
   There is no computed risk score, failure diagnosis, work approval or risk acceptance.
4. Optionally link a manual disruption, inspection / PdM recommendation, or exact
   canonical WO. Local records must concern this asset; WO identity and asset scope
   are checked through the read-only API. A manual observation can be the basis
   without pretending that an instrument, WO or historian confirmed it.
5. Only the engineer who created the judgment can update it, requiring a reason and
   current version. Close, void, or reopen the same record. No deletion route exists.
   ADMIN does not inherit ENGINEER permissions. All authenticated roles can read.

One database-unique judgment per asset prevents duplicate priorities, including
repeat submissions, independent engineers, and completed / voided judgments. An
idempotency UUID prevents duplicate form submissions; optimistic version checking
prevents stale forms from overwriting later work. Every revision preserves all
judgment fields and linked reference IDs. Linked sources open their current version,
not a frozen source copy, and the UI calls this out. Manual logs retain their own history.

## Candidate scope

- Manual logs: distinct recorded disruption IDs per exact member asset, including
  cause, affected and unknown roles. Voided logs excluded. All recorded dates,
  including unknown dates, are eligible. Missing restoration is not an ongoing trip.
- PdM: nonempty recommendations, status open / in progress, with exact asset link.
  Completed recommendations excluded. Unlinked recommendations are disclosed
  separately, not assigned to an inferred asset.
- These two local sources are aggregated and deduplicated by asset in SQL, then
  paginated by 10. Any asset already assessed is excluded, even when its judgment
  is closed / voided; review the existing judgment instead of making another.
- Repeat WO: GET `/v1/reliability/maintenance-investigation` with fixed minimum 2,
  windows 30 / 90 / 180 days, count-descending order and pages of 10. Only governed
  Registry BSR/IP, latest retained unique WO identities, CLOSE, verified non-task,
  verified actual start, no timestamp fallback. This does not cover all inventory.
- Repeat-WO pages are matched to local judgments in one bounded query. Assessed
  assets on that API page are hidden and the number disclosed. Total is the remote
  total *before* that exclusion. Local and remote source lists may reference the
  same unassessed asset; they are not summed into a misleading cross-source total.
- WO drilldown uses the existing CLOSE history with the Jakarta-local date window.
  Its general timestamp / task semantics are broader than candidate eligibility;
  the link explicitly asks the reader to inspect actual-clock / non-task evidence.

Empty, partial, unavailable and unverified states remain distinct. Empty lists never
mean healthy, zero risk, or no incidents. Unknown clocks/task/status and excluded
record duplicates are disclosed without summing overlapping coverage groups.
An unavailable evidence state or mismatched API scope is rejected rather than
rendered as a valid zero. Response bytes are capped at 1 MiB by the existing client,
with connection / request timeouts and redirects disabled. No source SQL, collector
write, new source collection, historian, MTBF or MTTR is introduced.

## Verification boundary

Public tests use fictional assets, measurements, in-memory SQLite and mocked HTTP.
They establish software behavior, not source freshness, verified engineering
judgments or deployment acceptance. Private runtime evidence is not shipped.
Run the aggregate checks in the workspace README against the selected commit.
