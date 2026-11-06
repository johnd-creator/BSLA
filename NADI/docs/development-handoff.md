# NADI development handoff — 2026-11-05

## Open and try

Preview: **http://127.0.0.1:8010/login** on the johnd-creator laptop.
Laravel 13.40.0 / PHP 8.5.12. Source: `/home/john-d/Music/BSLA/NADI`.
The four usernames are **admin, engineer, supervisor, manager**; each has its
matching role. Their memorable initial phrase is only in the ignored private
`storage/app/private/development-users.txt` file (0600). Do not publish that file.
All four accounts require local mode plus loopback Host/IP. The original bootstrap
administrator was preserved. Admin can replace passwords through User management.

- Asset expands into **Master Asset** and **Action Board**. Master Asset reads
  actual governed Mart assets. An Asset detail links to its scoped WO list.
- Master Asset → **Mapping BSR** shows document candidates and engineering
  inference separately from source facts. Source identities/parents never change.
- **Action Board** follows the four cards/two table structures seen in konsep1.png.
  Risk ranking, scores, trends and critical findings are visibly unconnected drafts.
  Its separate WAPPR backlog is actual local Mart data, not a failure count.
- **Rekomendasi inspeksi** follows the table/form direction seen in konsep2.png.
  Engineer saves one local request, adds findings, then a recommendation in the
  same form. No approval engine, external account, notification or sending exists.
  Engineer edits only their own drafts; Supervisor/Manager read; Admin administers
  accounts without implicitly inheriting Engineer write rights.
- **Work Orders** reads actual local records. Detail uses a retained description
  from Mart or an exact WO+Asset match against the local Collector. Actual clocks
  and duration remain unavailable when the evidence is absent/invalid. START takes
  precedence; a FINISH reason cannot override a missing START. Matching NAIVE,
  INVALID and UNAVAILABLE provenance remains visible per clock. Only CLOSE
  plus two valid zoned clocks yields elapsed work hours; never status-date fallback.
- Beranda intentionally remains blank. Login, sidebar, tables, forms, private
  desktop/mobile previews, error screens and favicon have been polished.

No synthetic record is seeded into the user experience. The one browser-created
inspection was explicitly DATA UJI and only that exact row was removed afterwards.
There were zero retained local inspection drafts at the final check.

## Mapping coverage

Owner attachment asset(1).xlsx / HIRARKI REVISI: **12,048 nonempty rows**.
Local Registry snapshot: **845 assets**; **837 explicit BSR/IP/CS01** included.
Excluded: CS02 (1), CS03 (1), unknown unit (6). No unit is inferred from a KKS/name.
Matches: **798 exact unique candidates, 11 ambiguous, 28 unmatched**. These are
proposals, not approval of a new identity or parent. Engineering labels: 616
inferences with recorded keyword basis; 221 unresolved. Normal Registry stays intact.
Source and mapping evidence: `../../maximo-knowledge/docs/bsr-hierarchy-draft.md`.

## Validation

- Laravel: **43 tests, 409 assertions**; Pint, Composer manifest/lock/platform,
  frontend build and diff whitespace checks passed.
- Browser: **32 concept/auth checks + 16 mapping/WO checks + 7 final polish checks**.
  Four real development logins, server denials, exact local data, pagination,
  inspection→recommendation, CSRF and desktop/mobile overflow were exercised.
- At Collector/Mart handoff: **143 Collector tests**, **123 Cockpit tests**,
  **6 mapping safety tests**, **5 contract tests**, and **all 24 Draft 2020-12 schemas** passed.
  Tests use mocks/SQLite; the old Cockpit smoke fixture was corrected to stop
  looking up a default operational DSN. No operational database was used for tests.
- Existing 20 containers retained their IDs/start times; both existing NADI units
  remained active. User's compose.dev.yaml and 23496711.xls matched original hashes.

Browser evidence and screenshots are private local files, not public web assets.
Final preview copies: `storage/app/private/previews/`. Original JSON evidence:
`/tmp/nadi-concepts-qa`, `/tmp/nadi-data-qa`, `/tmp/nadi-final-preview`.

## Source-session boundary

John requested two parallel areas. This session owns **Laravel/UI only** after
handoff. Collector/Mart source work belongs to the parent-created separate session.
The internal duplicate review child was interrupted before any tool/write, and
confirmed zero commands, edits, tests, migrations, processes or source requests.

The source code changes for description/clock evidence/strict interval are tested
but were not deployed by this session. Existing PR #130 recovery remains separate;
no historical 10-WO/20-clock recovery, cursor reset, source recollection, merge,
commit, push or operational activation was performed here. Root checkout and
running source images differ in existing feature coverage; do not rebuild this
checkout over running services without preserving the qualified source baseline.

Laravel relies on existing compatible GET endpoints:

- `:8000/v1/reliability/assets` and `assets/{canonical_id}`.
- `:8000/v1/reliability/maintenance-events` with exact `work_order_id`, optional
  `asset_ref`/`status`, bounded offset/limit. Detail also checks canonical event ID.
- `source_detail.work_order_number` and `asset_number` identify the local Collector
  description read (`:8002/work-orders?q=...&equipment_id=...&limit=25`); both IDs
  must match exactly. No raw source/person/cost payload is exposed.
- `description` and `actual_timing_state` are compatible optional additions.
  Laravel works with the running older DTO without the new individual detail route.
- WAPPR uses the same maintenance list with fixed status and 10-row pages.

Preserve these shapes or coordinate changes with Laravel. Historical missing
clocks, 39 unresolved/ambiguous document matches, and 6 unknown-unit assets are
explicit evidence gaps, never substituted with invented values. Weighted scoring,
historian correlation and validated incident Pareto remain future work.


## Operasi follow-up — 2026-11-05

Menu `/operations` now provides a read-only process canvas foundation and real
Registry equipment selection (25/page, unit filter), with exact verified detail.
Links retain the same canonical Asset context across Master Asset, maintenance
WO and Engineer-only local inspection creation. All four existing roles can read
Operasi. Asset detail also links back to Operasi for that exact equipment.

Wonderware/Foxboro layout awaits actual verified screen references. Historian
values, source quality/age, tag mapping and cache remain unconnected/inactive.
There is no diagram of assumed process relationships, live status, control, alarm,
polling, adapter/source request, new persistence or migration. Future reliability
colors are neutral **Belum dinilai**, with expandable explanation of the future
validated score/Pareto evidence and the distinction between WO and incidents.

The older Laravel preview had ended before this follow-up. Confirmed port 8010
free and existing managed services; reopened only Laravel on 127.0.0.1:8010.
Source/collector/runtime configuration is untouched by this follow-up.

Final verification: **50 tests / 481 assertions**, Pint, build, diff whitespace
checks pass. **13 additional real browser checks** cover all four roles, correct
context links, unit/pagination, desktop/mobile layout and absence of background
polling/JS errors. JSON evidence `/tmp/nadi-operations-qa/results.json` is local.
No screenshot was uploaded or externally shared.
