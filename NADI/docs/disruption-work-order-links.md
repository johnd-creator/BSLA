# Hubungan Log Gangguan ↔ WO

Source implementation prepared on 8 November 2026. Publication does not activate
migrations or change a running preview. This is engineer correlation, not a failure-validation process or KPI input.

## Workflow

1. Save a manual observation in **Asset → Log Gangguan Aset**. A WO, known cause,
   occurrence time or recovery time is still not required.
2. Open the event and choose **Pilih / koreksi hubungan WO**. The picker shows only
   WOs for the exact primary asset after inventory/Registry identity verification.
3. Select one WO, add an optional note and save. Repeat for additional WOs, up to
   20 active links per event. A source WO can be referenced by several observations;
   this is not automatic incident deduplication or a failure count.
4. Correct a link with a reason, or choose **Hubungan dilepas**. Removed links
   remain stored and in revision snapshots. Re-adding uses a fresh source identity
   check and resets the relationship to uncertain.

The list is bounded to 25 rows per page. Exact-number search accepts a readable
source number, including slashes such as `BSR26/19873`, and encodes it using the
existing canonical-ID convention. No fuzzy matching, parent/child propagation,
WO creation, collector trigger, or source mutation occurs. Main-asset-only linking
is intentional for this first pilot; an affected asset's WO cannot be substituted.
Navigation away from the picker does not save an unfinished form.

## Two separate facts

- **Identity:** the exact WO ID, Mart record ID and primary asset matched through
  the existing read-only API at `identity_checked_at`. This is a historical check,
  not proof of current source freshness. Descriptions and source payloads are not
  replicated into Laravel storage.
- **Relationship:** `uncertain` (Belum dipastikan) is always the initial state.
  `related` (Terkait menurut engineer) is an explicit engineer correction with
  its basis/reason. Neither state validates failure, causality or a repair interval.
  `removed` releases the current relationship without erasing its history.

The old `work_order_ref` text on the observation remains separately labelled
**Referensi WO manual (belum dicocokkan)**. It is never automatically promoted,
matched, replaced or used to create a structured link. Old revision snapshots
without structured-link data remain readable and explicitly say none was recorded.

Links do not change observation type, asset role, dates, recovery, impact or status.
WAPPR remains backlog; CLOSE is not a failure or MTTR. A cancelled observation can
retain its links, is labelled cancelled on the WO detail and remains excluded from
active disruption indicators. No MTBF/MTTR/availability formula or readiness gate
changes. Event totals still count events, not linked WOs.

## Integrity and permissions

Only the original ENGINEER can use the picker or change its links. ADMIN does not
inherit engineering write permission; other authenticated current accounts can
read relationships on the event and exact WO detail. Nested writes reject a link
belonging to another event.

Adding a link rechecks exact Asset + WO identity, scope and unambiguous Mart record.
Missing, mismatched, duplicate or unavailable API results fail closed. Existing
local links remain readable during an outage; failed additions retain form input.
Source status/cause/failure clues are never interpreted as relationship approval.

Every link addition/correction increments the observation's existing optimistic
version and atomically saves a complete revision snapshot, actor and reason.
Both ordinary observation forms and relationship forms reject stale versions.
Repeated attachment of an already active WO returns the existing relationship
without adding another row or revision. A unique event/WO constraint remains the
storage backstop. Audit failure rolls back the relationship and version together.
There is no link-delete route; removed identities remain stored.

## Storage and publication boundary

The additive migration defines `asset_disruption_work_orders` in the existing
local Laravel store. No migration runs as part of publication. Back up and verify
the existing SQLite owner before separately authorized activation. Test stores
are hermetic; operational observations, identities and pilot results remain local.

## Verification

Run `php artisan test --filter=DisruptionWorkOrderTest` and the full Laravel
suite. Tests use mocked Mart responses and in-memory SQLite. They cover identity,
member/Registry scope, ownership, concurrent edits, duplicate requests and audit
history. A passing test does not validate any real-world event-to-WO link.
