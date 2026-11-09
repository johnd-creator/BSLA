# Log Gangguan Aset (manual engineer)

Local development feature, added 2026-11-07. Menu **Asset → Log Gangguan Aset**
(`/disruptions`), with a create action and latest history on each asset detail.
It does not create a Maximo WO, consume DCS signals, write collector data, or
publish a diagnosis. Source assets are still GET-only through the existing Mart.

## Recording

Engineer chooses a verified inventory or Registry asset, event type, optional observation,
asset role (cause / affected / unknown), and impact (including unknown). The log
requires neither WO nor causal diagnosis. Date, clock time, known cause, impact
explanation, recovery, WO reference and evidence reference are optional. Evidence
is text/location/URL reference, not a file upload. The original free-text WO field
remains unverified; structured WO links are managed separately from the saved
event detail, as described in [WO relationships](disruption-work-order-links.md).

A date without a clock time remains a literal date, with no invented midnight or
zone. Both clock times use the explicitly selected zone and are stored in UTC.
Dates without times use the current Asia/Jakarta (WIB) calendar date as their
latest permitted day; they still store no timezone or invented instant. Zoned
timestamps are checked as instants, so a valid WITA/WIT date ahead of UTC or WIB
is not rejected by a second calendar cutoff. Future timestamps, invalid dates, times without
a date/zone, and recovery before the event are rejected. Empty recovery does not
mean the asset is still stopped. Duration is calculated only when both complete
instants exist, and is labelled recorded event duration, not verified downtime.

Additional affected assets and at most one recorded causal asset can be attached
to the same event. Each membership is unique and verified against the existing
asset read API; parent/child effects are never inferred. An impacted asset has a
history entry but is not counted as the causal asset. Impact and duration belong
to the event, not separate per-asset measurements. For now engineers enter extra
assets using exact Canonical IDs from Master Asset, maximum 20 affected additions.

## Indicators, not an official score

The asset page and logbook show recorded-event count by occurrence year, causal /
affected / uncertain role counts, and completeness denominators for known date,
clock time, recovery and calculable duration. All active records are counted,
independently from the paginated/filtered table. Unknown dates are shown separately
and never placed in the creation year. Years are based on the recorded local date,
not the UTC conversion or the date the engineer entered the log.

A single event ID counts once globally and once per linked asset; per-asset counts
must not be added to produce a plant total. Request UUID prevents repeated form
submission from creating a second event. Separate independently submitted records
are not automatically deduplicated: engineers must check history and cancel a
confirmed duplicate with a reason. Durations can overlap and are not an availability
calculation. No records is unknown coverage, not proof of a healthy asset. There
is no fabricated score, MTBF, validated failure rate, or production health change.
An official score still requires an agreed engineering method and validation.

## Access and audit

All authenticated, current local accounts can read. Only ENGINEER can create,
and only its original engineer can correct a record. ADMIN does not inherit
engineering permissions. Server Gates apply to GET forms and POST/PUT writes.
Every initial record and correction atomically saves an immutable-by-route
snapshot, actor, timestamp, version, and correction reason. Optimistic version
checking rejects stale edits. Cancellation is a status change with a reason,
retained in history and excluded from active indicators. No delete route exists.
This is application-level traceability, not a tamper-proof compliance audit store.

Corrections and cancellation remain available during a Mart outage when their
asset identities are retained in the current local record. Adding a new affected
or causal asset still requires a successful exact identity check. A member removed
from the current record must be checked again before re-adding it; historical
snapshots are not an offline identity cache. Role, version, audit and input checks
remain unchanged. Saving a local correction does not claim fresh source evidence.

## Storage and verification

The additive migration `2026_11_07_000003_create_asset_disruptions.php` creates three
tables in the existing ignored Laravel development SQLite: events, memberships,
and revision snapshots. No operational stores, accounts, source payloads or existing
records are migrated/replaced. A private local backup precedes preview activation.
This extends the local draft workspace to manual incident observations only.

`AssetDisruptionTest` uses in-memory SQLite and mocked HTTP, including authorization,
precision, annual counts, idempotency, rollback, stale edits, cancellation, escaping,
Mart outages, pagination and impacted-asset history. Browser QA runs against a
separate temporary SQLite fixture and synthetic users/assets on loopback 8021;
no test incident is saved in the user's development logbook.

Checks: `composer test`, `vendor/bin/pint --test`, `npm run test:ui`,
`npm run build`, `git diff --check`. The normal preview remains on port 8010.

Latest regression verification (8 November 2026, including structured WO links):
875 PHP tests / 21,683 assertions, 54 frontend tests, Pint, Composer validation and
platform requirements, Vite build and diff whitespace checks pass. The original
logbook browser coverage includes creation, edit/audit, stale updates, cancellation,
role denials, annual filters and interrupted navigation. The new link workflow
passed 12 additional isolated browser scenario groups at 320/390/768/1440;
see the linked feature contract for its scope and real-data limits.
