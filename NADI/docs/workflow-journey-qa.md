# Workflow regression coverage

`WorkflowJourneyTest` drives real Laravel routes, validation, SQLite persistence
and Blade rendering with synthetic assets and mocked HTTP. It covers inspection
creation, manual disruption, Action Board assessment, feed attention, recommendation
status, closing and reopening the same judgment, and revision history. Independent
role gates, replay protection and optimistic version conflicts remain enforced.

`PdmTrendTest` covers exact identity/context/unit separation, date-only precision,
missing and zero values, extreme numeric values, bounded history, unavailable
context, escaping, reader roles and guest/disabled sessions. Synthetic measurements
are not source workbook extracts or engineering evidence.

Run `composer test`, `npm run test:ui`, `vendor/bin/pint --test` and `npm run build`.
Browser verification must use a temporary test store with fake HTTP. Never insert
QA records into an existing development or operational store. Screenshots and
operational evidence are private and not included in this public source release.
