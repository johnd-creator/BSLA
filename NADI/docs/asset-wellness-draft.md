# Asset Wellness: draft awal berbasis bukti

Implemented locally on 9 November 2026. Entry point: **Data & Laporan → Asset
Wellness**, or **Master Asset → detail → Tinjau draft Wellness**. The authenticated
GET page `/asset-wellness` accepts an exact BSR/IP asset and evidence year.

## What this draft does

The four proposed components are PdM **45%**, operating condition **25%**, locally
reviewed failure **20%**, and maintenance **10%**. These weights are illustrative
conversation inputs, not approved engineering rules. `AssetWellness::COMPONENTS`
is the single draft definition. No numerical normalization, condition threshold,
health category or production scoring engine is enabled. Every component score,
aggregate score and official score remains **null / Belum cukup data**.

This is a usable evidence-review page, not a random/synthetic score display:

- **PdM:** exact-asset, measurement-year records, latest measurement with original
  date precision, review basis current/stale/unknown, and links to measurement and
  analysis. Measurement counts never become required-point coverage. Inspect at
  most 500 newest measurements, with an explicit partial warning and full count.
  Display at most eight source rows. No cross-template/unit/point averaging.
- **Operations:** reuse verified manual-log exposure, separate known coverage and
  RUN hours, and disclose the full-calendar-year denominator. UNKNOWN, gaps and
  overlaps do not count as known coverage. Log verification does not prove healthy
  process parameters. No new historian access or polling; STOP/STANDBY is not a
  bad condition score. A genuine verified zero RUN stays zero; missing stays null.
- **Failure:** reuse the current Reliability evidence classification and version
  checks. Count only current local failure reviews with precise onset in the
  chosen year. Duplicate, stale, uncertain and missing-onset cases do not inflate
  that count. Observation coverage and interval conflicts remain separate. The
  existing 2,000-observation limit produces an explicit partial warning. Links
  retain the exact member asset; one event is not multiplied by its WO links.
- **Maintenance:** retained-Mart unique WO context in the actual-start year, plus
  unknown-year counts. WAPPR/CLOSE, volume, labor and elapsed actual duration are
  not scored. Outage remains unavailable/null. Failure is not penalized again
  through raw WO count. Source collection freshness remains unknown.

Coverage, latest observation/review time and confidence have separate labels in
every component. Confidence is currently **not assessed**, not a percentage or
probability of health. No default 100, filled missing input, rescaled partial
weights, guessed threshold or false healthy state is produced.

## Independent attention and criticality

An active engineer priority marked **Segera** gets a prominent separate warning
above the result, even when the selected evidence year differs. It cannot be
hidden by a composite average. Closed/voided priorities are not active warnings.
No active priority is explicitly **not** proof of safety.

Urgency, asset criticality and current condition are distinct. Existing priority
is read from the Action Board; governed criticality remains **Belum dipetakan**. An engineer may separately
record a proposed criticality label and consequence basis for the exact asset/year;
that proposal does not become a governed mapping. Automated critical-condition
threshold detection is not enabled. Reliability Supervisor approval applies to
its exact KPI snapshot and never silently approves Wellness weights or results.

## Data, permissions and traceability

The evidence report remains read-only. A local append-only
`asset_wellness_policies` table now stores draft method revisions in the existing
SQLite owner. There is no source replica, collector, new operational database,
new account, approval route, automatic Asset enrollment or source mutation.
Reads use local SQLite records and bounded GET-only Reliability Mart DTOs. All active authenticated roles can read through current-account middleware.
The exact asset/year filters are server validated; output is escaped and uses
`Cache-Control: no-store, private`. Native GET navigation works without JavaScript.

The page exposes source record/version links, the Reliability evidence hash and
method version `asset-wellness-draft-v2`. It is not an immutable cross-source
snapshot: Reliability reads its own consistent local snapshot; PdM and priority
summaries are subsequent live reads. Links and the Reliability download read the
latest evidence. No Wellness approval or reproducibility claim is implied.

## Decisions for the engineer conversation

1. Required assets, points, methods, units and operating modes.
2. Per-context condition bounds and normalization, accepted data age, required
   coverage and evidence-quality/confidence rules.
3. Reconciled event identities, recurrence, impact, time window and WO relations.
4. Maintenance plan/due-date denominators and verified effectiveness evidence.
5. Critical-condition handling, asset criticality, revised weights, pilot
   validation and the eventual method/result approval workflow.

## Draft method settings

`GET /asset-wellness/policy?asset_ref=…&year=…` is readable by every active role.
`POST /asset-wellness/policy` is ENGINEER-only. Only the engineer who created the
first asset/year revision may revise it. ADMIN does not inherit write permission.
The request key makes repeat submissions idempotent; `previous_revision` rejects
stale tabs. Versions are append-only by route, with author, time, reason and
reference. No update/delete/approve route is provided.

- Criticality is a free proposed label plus an explicit consequence/reference
  basis. No severity matrix or risk weighting is invented.
- Each of the four components has nullable proposed maximum calendar-day age and
  a textual required-evidence checklist. Empty means undecided. Merely filling the
  settings does not assert evidence completeness, confidence or method approval.
  Operations/failure/maintenance ages remain proposals: their accepted timestamp
  basis and completeness must still be reviewed by the engineer.
- Up to ten PdM point proposals bind to an existing same-asset/year measurement.
  Point, units, numeric field definition, method, template fingerprint and full
  snapshot, mode, instrument, operating condition and asset-selection basis stay
  exact. Preview-only templates, missing units/context, conflicting/duplicate
  rules, non-finite bounds and foreign asset/year anchors are rejected. Each
  range needs at least one inclusive bound and a written reference. Without a
  measurement anchor, other method settings can still be saved, but no threshold
  is invented. The editor lists 100 newest measurements plus saved anchors.
- The read-only preview compares only the newest matching context in the selected
  year against the proposed bounds. It never substitutes an older valid reading
  for a missing latest one, converts units or mixes contexts. An anchor change,
  snapshot/unit mismatch, invalid/future timestamp, or ambiguous same-day order
  with date-only observations withholds the comparison. A repeated precise
  timestamp also cannot choose a latest value by ID. Date-only values stay dates.
- Age is calendar-day distance to the current date in Asia/Jakarta, explicitly
  shown even for a historical evidence year. Point age is separate from the
  component proposal, never silently inherited. Age, range comparison and local
  analysis version status are separate; an in-range value is not a healthy label.
  Data adequacy and instrument quality still require engineer review.
- Saved rules always have `DRAFT_NOT_APPROVED`. Posted approval/score fields are
  rejected. All component, aggregate and official scores remain null. Proposed
  criticality does not replace the independent urgent-priority warning.

The compatible migration is
`2026_11_09_000003_create_asset_wellness_policies.php`. It has not been applied to
operational/development data by this feature task. Until activated against the
verified existing SQLite owner with a verified backup, the editor shows a clear
storage blocker and the old evidence report continues working. Source outage
blocks creation for an unverified asset but does not block the owner's revisions
to an existing exact-asset proposal. No deployment or runtime restart is needed
for a code review.

## Verification and limits

Current focused checks (9 November 2026): **34 Wellness feature tests / 243
assertions**, four Wellness frontend checks, targeted Pint, Vite build and
`git diff --check` passed. Feature tests use SQLite in memory with mocked source
HTTP, including missing data, roles/ownership, duplicate submit, stale revision,
source outage, exact contexts, zero, missing latest values, ambiguous dates,
changed anchors, invalid bounds, and absent storage migration. These are focused
checks, not a full-regression claim.

Browser QA for the new settings uses a separate temporary SQLite database and
mocked HTTP on loopback port 8046. Its synthetic records are not operational data.
Nine scenario groups passed: guest/login, editor/save, repeat POST, immutable
revision/stale tab, Cancel and Back/Forward, read-only roles, no-JavaScript save,
missing-year inputs, and source isolation. Layouts at 320/390/768/1440 px had no
horizontal overflow or browser page errors. Mobile/desktop screenshots were
visually inspected. QA artifacts remain under the temporary feature QA folder;
the main preview and user records were not modified. Operational pilot identities and source counts remain private; empty local inputs
do not establish health or method validation.

This is a draft-configuration and evidence-review foundation, not a numerical
scoring release. Engineer validation, required-point denominator, normalization,
approval workflow and operational condition verification remain outside this
release. No source collection, data import, commit, push or deployment.
