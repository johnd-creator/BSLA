# Repeat-WO candidate query

The investigation path ranks narrow latest-WO identity rows before status, task,
date or Registry filtering. A PostgreSQL materialized CTE decodes scalar source
evidence once. Chronology, aggregates, coverage, total and bounded page share one
read-only statement. An outer join retains metadata for empty and past-end pages.
SQLite tests exercise equivalent semantics. Existing scope, sort/tie breakers,
partial-coverage DTOs and no-failure-inference boundaries are unchanged.

`test_maintenance_investigation_performance` covers query count, bounded hydration,
empty pages and evidence parity. No operational counts, query timing, image IDs
or local deployment snapshots are included. Run the backend suite and PostgreSQL
CI before deployment. A source test pass is not a runtime-performance guarantee.
