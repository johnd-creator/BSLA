# CEMS live read-only

Operasi → CEMS (`/operations/cems`) reads one shared RAM service through
`CEMS_LIVE_API_BASE`, blank/unavailable by default. No fallback to the historical
CEMS database API, source collection, operational writes, migrations or browser
persistence. Existing databases remain untouched. Cache retention is six hours;
the source service polls every five seconds and restart loses RAM contents.

Bounded GET-only reads use a 1 MiB body cap, 1 s connection / 3 s total timeout,
no redirects and allowlisted DTOs (32 parameters, 360 history points). Authenticated
page refresh is five seconds, visible-page only and non-overlapping. Failed refresh
hides old values; HTTP is no-store. Simulation is conspicuous. Missing values are
not zero. Quality, timestamp, last-good and age stay separate. History is a bounded
sample of the RAM window, not an archive or compliance/health assessment.

The page shows one stack scope and one card per unique parameter. Each card
combines the current value, quality/age, verified KKS link (or unmapped state),
and that same parameter's minute-feed evidence. The schematic no longer repeats
the parameter list, and the feed is not a second set of cards. Feed records are
joined by exact parameter_code, never list position; missing records remain
unavailable. The single shipped source is stack 1 / CB001. No new stack or
source reader is created by this presentation change.

The responsive stack/analyzer drawing is illustrative, not as-built.
`config/cems.php` initially has no parameter→KKS mappings. Verified mappings need
exact canonical_id, exact source_asset_number as kks, verified=true and provenance
in evidence. The linked identity must also match the read-only Mart inventory.
Unknown, unavailable or mismatched targets have no clickable asset link.
The known CEMS and chimney inventory candidates do not establish a parameter or
stack relationship, so they are deliberately not preconfigured.

Publication and an installation-specific live cutover are distinct.
Do not activate or stop any source reader without authorization.
See ../../cems-collector/docs/volatile-cems-pilot.md for cutover and rollback.
Tests use mocked HTTP and in-memory SQLite; browser QA must use an isolated fixture.

## Minute data-signal feed

`/v1/cems/signals` reads the same service's once-per-minute RAM summary. NADI
shows feed timestamp/age/status and received-good sample count per parameter.
This is communication/data evidence only, never operating-state, equipment health,
WO status or automatic MTBF/MTTR/downtime evidence. No separate source poll occurs. Numeric values use eight significant digits to
preserve small Hg readings. Snapshots older than 15 seconds or inconsistent
non-good numeric values fail closed at the UI read boundary.


## Freshness enforcement

A focused filter does not stop polling and its DOM identity is preserved. A
separate browser watchdog hides expired values at 15 seconds, including a stalled
request. Hidden/navigation states clear old readings. PHP verifies strict source
timestamps, rejects future or inconsistent observations, and cross-checks reported
age against observation/publication time. Good zero values remain valid.
