# Beranda: attention, activity and source quality

The existing four global metrics remain unchanged. Homepage panels read the same
local development store and existing Reliability Mart GET API; they never write
source Assets/WO, trigger collection, infer failure or assign a health score.

## Four panels

- **Perlu perhatian:** at most six active engineer assessments ordered by stated
  urgency and earliest of target/review, plus four open/in-progress recommendation
  deadlines due within seven days (including overdue). Both dates remain visible;
  a future review never hides an overdue target. An unassessed recommendation
  deadline is not an inferred urgency or risk rating.
- **Aktivitas terbaru:** 12 recorded events per page. Existing disruption and
  priority revisions retain actor/version/snapshot and link to the exact revision.
  PdM/inspection creation and future updates are audited transactionally in
  `workspace_activities`. Recommendation/status/target changes retain before/after
  values. PdM edits record action/version, not historical measurement snapshots.
  Old drafts contribute only known creation metadata, with no assertion about
  original content, original asset, or later changes. `updated_at` is never used
  to fabricate a change event or actor. Dates here are save times in UTC, distinct
  from measurement precision and incident time.
- **Kandidat untuk ditinjau:** five unassessed local assets from existing signals,
  plus up to five unassessed assets from the first bounded ten-row Registry WO
  candidate response. Every existing assessment (including closed/voided) excludes
  the asset from the unassessed preview. The 90-day source contract retains CLOSE,
  verified non-task/actual-start semantics. Partial evidence and the limited
  Registry population are explicit. Repeated WO is not repeated failure. Sources
  can overlap and their counts must not be added.
- **Kualitas data:** compact availability/coverage/freshness context with a link
  to the full quality page. Missing data stays unavailable, never safe or zero.

## Filters and bounds

Scope and freshness-evidence filters affect work panels, not global metrics or
quality context. `local` means local notes (possibly non-Registry assets);
`registry` means the WO Registry source. A recorded local timestamp does not prove
asset health or current source freshness. No fresh-source state is invented.
Type/time filters apply only to the activity list and use save time. Conflicting
scope/evidence filters have an explicit empty state. Forms use native GET links,
validated allowlists, stable sorting and preserved pagination queries.

Each activity SQL branch is filtered before a bounded prefix read, then merged
and paginated. Feed sorting has indexed clocks, bounded hydration and no per-row
HTTP reads. The preview stops at 100 pages; narrower filters and source logs are
available. Default homepage makes three bounded GET calls (the original two
aggregate sources plus the existing candidate endpoint); local-only scope skips
that candidate call. There is no polling, collection or full-source history fetch.

## Audit migration and verification

Migration `2026_11_07_000005_create_workspace_activities` is additive in the existing
authorized development SQLite. Back up that store first. It adds the activity
table and feed-order indexes only; no history backfill or operational migration.
Creation replay and stale updates cannot duplicate events. Audit failure rolls
back the associated draft update. Existing independent role gates are unchanged;
Admin does not inherit engineering writes. Audit links are scoped to their subject.

Run `composer test`, `vendor/bin/pint --test`, `npm run test:ui`, `npm run build`,
`composer validate --no-check-publish`, `composer check-platform-reqs`, and
`git diff --check`. Feature coverage includes sorting, bounded SQL/pagination,
legacy provenance, actor/XSS handling, exact revision links, source outages,
partial candidates, filters, atomic audit writes, replays, stale edits and roles.
The public regression suite uses synthetic fixtures and mocked HTTP only. It does
not establish the current state of any running installation.
