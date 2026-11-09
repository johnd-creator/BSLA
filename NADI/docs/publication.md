# Public-source integration

This release is integrated selectively from current main. It does not import the
older feature branch's unrelated PI/NK history or change Compose/runtime setup.
Main's existing reviewed classification, source-detail, cursor safety and
integration-status endpoints are retained alongside the additional NADI reads.

The original active checkout and its private catalogs remain unchanged. This
public package contains application code, synthetic tests and generic generated
illustrations, not source Excel files, derived operational inventories, private
mapping review notes, measured values, runtime evidence or local credentials.

The Laravel catalog and mapping locations are configurable private files. Missing
private inputs are visible as unavailable, never replaced by sample source data.
Tests cover form semantics using deliberately fictional fixtures. Offline checks
establish software behavior only; they do not establish real-world asset identity,
source freshness, engineering acceptance, deployment or approval of calculations.

Collector migrations in this package are additive definitions for the existing
owner store. Publication does not apply them, initiate collection, run a backfill,
or restart any service. Review the existing owner's migration and access process
before separately authorized operational use.

## Local verification before publication

- Laravel: 791 tests, 11,994 assertions with synthetic catalog fixtures.
- Collector: 371 offline tests, no failures, skips or external I/O.
- Cockpit: 1,336 discovered tests passed, with 318 PostgreSQL/optional integration
  cases skipped locally. The collector-only canonical contract passed separately.
- Knowledge: 58 tests; shared contracts: 14 tests.
- Laravel UI: 24 tests, Pint, Composer validation/platform and Vite build.
- Existing Next.js frontend: all configured non-browser checks, lint, TypeScript
  and production build passed. Historical preservation assertions remain active,
  with an explicit hash manifest for this integration.

GitHub CI provides the separate PostgreSQL/browser acceptance. Local results do
not claim those skipped/browser checks or engineering UAT.

## Remaining source integration, 8 November 2026

The additional source package contains explicit multi-WO links, local Reliability
reviews/snapshots, the simulation-only page-demand historian, and the optional
shared CEMS RAM service/UI. Legacy CEMS persistence is now opt-in through the
`cems-legacy-storage` profile. This is a source/configuration change only; no
service, existing environment file, database or source acquisition was changed
by publication. Main's private catalog handling, synthetic fixtures, collector
fixes, Mart governance and existing frontend are retained.

Final focused integration checks: 916 Laravel tests / 13,383 assertions, 61 UI
tests, 385 Maximo tests, 106 CEMS tests, 16 historian tests, 18 runtime controller
tests and all 36 current schemas passed. Pint, Composer validation/platform,
Vite build and whitespace checks passed. CEMS browser QA separately covered
focused-filter polling, 15-second expiry, blocked-request recovery and narrow
layouts. The two Python RAM-source suites also have exact-commit GitHub CI.

Workbooks, source-derived catalogs/mappings/review reports, private image locks,
source snapshots, backups and database files remain outside this public package.
Old branch-only PI/NK changes are not merged over current main.

## Governed workflow source integration, 9 November 2026

The release adds engineer-owned PdM inspection plans and effectiveness reviews,
versioned Asset Wellness draft settings, operating evidence and deterministic
Reliability calculations with separate Supervisor decisions, exact-scope MTTR
replay guards, and plain-decimal Hg display. Private catalog/mapping configuration,
synthetic fixtures, missing-input notices and freshness controls from main remain.

Selected source/tests/docs only were integrated from the active development
checkout. No source workbook, derived catalog, operational asset/WO readout,
database, account, private image lock or unrelated historical PI/NK/backend change
is included. Existing source evidence and deployment files are not replaced.
Additive migration definitions do not activate themselves or approve real KPIs.

Integration review also reproduced and fixed the operating-log request-key race
between identity verification and the write transaction. Replays now recheck exact
owner and scope inside the owning SQLite transaction, without duplicate history.

The final public-source regression uses in-memory SQLite and mocked HTTP. Browser
acceptance of the new feature forms was completed separately with isolated fixtures;
the integrated publication is not a production activation or an engineering signoff.

Final integration checks: **1,056 Laravel tests / 14,856 assertions**, **72 frontend
tests**, and **18 offline runtime-boundary tests** passed. Pint, Composer validation
and platform requirements, Vite build, whitespace and changed-document links passed.
The added replay regression failed before the fix and passed afterward.

A scoped publication audit found no credential/private-source patterns or binary
data in the selected changes. Ten catalog/mapping/ignore/fixture boundary files
match the main baseline exactly. These checks reduce publication risk; they do not
replace operational security review, engineering acceptance or deployment QA.
