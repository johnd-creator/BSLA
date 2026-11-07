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
