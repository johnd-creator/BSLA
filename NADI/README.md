# NADI Laravel — BSLA

Laravel development workspace, built directly in `NADI/` by a single developer.
The original FastAPI/Next.js NADI remains available on its existing port 3000.
Existing collector services, operational databases, volumes, source credentials,
and legacy account data are preserved. Collector/Mart source work is coordinated
in a separate session; its runtime activation remains pending. This application is a local development preview, not a cutover.

## Run locally

```bash
cd /home/john-d/Music/BSLA/NADI
php artisan serve --host=127.0.0.1 --port=8010 --tries=1
```

Open <http://127.0.0.1:8010/login>. Port 8010 is separate from existing services.
Four development usernames are available: **admin, engineer, supervisor, manager**.
Read their memorable development passphrase only from
`storage/app/private/development-users.txt` (mode 0600). The original bootstrap
administrator is preserved; its original file is `development-login.txt`.
No credential is embedded in source, documentation, or console output.
The preview is loopback HTTP; use reviewed HTTPS/session settings before any
shared or production deployment. The session cookie is encrypted, HttpOnly,
SameSite=strict, and named separately from the old application's cookie.

Frontend assets are already built. After editing CSS or JS, run:

```bash
npm run build
```

Blade/PHP changes are visible after refreshing the preview. `composer dev` starts
the same server on 8010. No additional workers, queues or collectors are started.
The strict Content Security Policy is configured for built local assets; use
`npm run build` during this initial workflow rather than a separate Vite server.

## Fresh development checkout

Reuse PHP 8.3+ and Composer with the extensions required by `composer.lock`;
this installation was verified with PHP 8.5.12, Composer 2.10.3 and Node 25.6.1.
Laravel framework: **13.40.0**, latest stable release verified on 2026-11-05.
Official skeleton: laravel/laravel v13.11.0 (skeleton and framework versions differ).
Exact PHP and Node dependencies are recorded in both lockfiles.

```bash
composer install
# Only if .env is absent; never overwrite an existing .env.
php -r "file_exists('.env') || copy('.env.example', '.env');"
php artisan key:generate
npm ci --ignore-scripts
npm run build
# Explicit isolated development store only; do not point this at operational DBs.
php -r "file_exists('database/development.sqlite') || touch('database/development.sqlite');"
php artisan migrate
php artisan nadi:admin --email=your-development-email@example.test
```

Bootstrap works only in local mode with `database/development.sqlite` and an empty
account table. It generates a random secret into the private local file; it does
not create a default public password or modify any existing application account.
SQLite, private files, .env, sessions, vendor and node_modules are ignored.
The SQLite store is authorized **only for isolated account/inspection draft development**; it is
not a replacement or migration of Cockpit or collector persistence.

## Features and access

- Login/logout using Laravel server sessions, CSRF protection, generic failure
  messages and login rate limiting. Passwords use Argon2id in local development.
- Responsive sidebar, blank Beranda, and read-only Asset list/detail. Asset is a
  dropdown containing **Master Asset** and **Action Board**.
- Action Board reproduces the four attention categories and two table structures
  in konsep1.png as clearly labelled drafts. No scores, risk ranking, trends or
  critical findings are invented. A separate bounded GET read displays actual
  WAPPR maintenance records from the existing Mart.
- `Inspeksi & rekomendasi` is a simple single-form local draft based on konsep2.png:
  request reference → inspection findings → recommendation. It is separate from
  PdM log book, with no external user provisioning, sending or approval workflow.
- ADMIN: list/create/edit accounts, change assigned roles, deactivate/reactivate,
  and optionally replace a password. All administration routes enforce a server
  Gate. No account deletion or public registration.
- **Engineer**: reads workspace/Asset/Action Board and creates/edits only their own
  local inspection/recommendation drafts. Recommendations require an inspection
  finding, method and date. Asset references are verified by GET before saving;
  no Asset payload is copied into SQLite.
- **Supervisor / Manager**: read workspace, Asset, backlog, and local drafts. No
  account administration, draft editing, work approval, budget decision or risk
  acceptance is granted. Role names do not imply enterprise/collector privileges.
- **Admin** does not inherit Engineer draft-writing rights. All enforcement uses
  server Gates; hiding UI controls is supplementary. Existing Laravel development
  AUTHOR/REVIEWER grants are migrated to ENGINEER/SUPERVISOR with session revocation;
  no account in the old FastAPI application is changed.
- Every user change increments an authentication version. Disabled/stale sessions
  are rejected, including after reactivation. Optimistic version checking rejects
  stale forms. An administrator cannot change their own role/status; at least one
  active administrator is retained. Concurrent updates serialize through SQLite
  IMMEDIATE transactions or row locks on databases supporting them.

These are separate development identities, not imported or shared old accounts.
Admin password changes are direct replacements for development; email recovery,
SSO, MFA, audit-event browsing and custom role creation are not included.

## Asset source

The approved source for Asset is the existing **Reliability Mart query API**,
accessed via Cockpit, not the technical Equipment endpoint or production Maximo:

```dotenv
RELIABILITY_MART_API_BASE=http://127.0.0.1:8000
```

Only these existing GET routes are used:

- `/v1/reliability/assets`: Registry membership, scope BSR/IP, pages of 25.
- `/v1/reliability/assets/{canonical_id}`: canonical detail.
- `/v1/reliability/maintenance-events`: scoped Work Order list/detail, pages of 25;
  detail uses exact work_order_id and canonical event identity.
- `/v1/reliability/maintenance-events?status=WAPPR`: separate backlog, pages of 10.
  The verified API returned 18 records on 2026-11-05. Record counts are not distinct
  incident counts and do not feed a score.

Filters: unit, raw source status, asset type. API sorting accepts only the existing
allowlist. Responses are bounded to 1 MiB, use connection/request timeouts, reject
redirects, and expose only approved DTO fields. No source records are stored in
SQLite. No fallback to direct SQL, collector writes, or production is provided.

The existing API returned a total of **845 governed assets** at verification.
That count is a point-in-time observation, not a sync freshness guarantee.
Source record timestamps are displayed without claiming freshness. Empty lists,
missing details (404), and unverified/unavailable responses are distinct; a
connection problem shows **Belum terhubung**, never fabricated sample assets.

Contract reference: `../reliability-cockpit/docs/reliability-mart-query-api.md`.
Role references were inspected in the active existing NADI checkout:
`src/domain/engineering.py`, `docs/nadi-admin-authorization-matrix.md`, and
`docs/local-authentication-v1.md`. No legacy application account or role data was changed.

## Development checks

```bash
composer test
vendor/bin/pint --test
composer validate --no-check-publish
composer check-platform-reqs
npm run build
git diff --check
```

Tests use SQLite `:memory:` and mocked HTTP; they must not contact source systems.
Latest verification on 2026-11-05: **50 tests / 481 assertions**, plus **32 concept/auth browser
checks**, **16 mapping/WO browser checks**, and **7 final polish browser checks** for all four actual development usernames, denied administration/edit
rights, Asset dropdown, real WAPPR pagination, and the single-form draft flow.
Only the browser-created synthetic draft was removed after testing; no user draft
was deleted. Final screenshot copies are private in `storage/app/private/previews/`; JSON
evidence remains in `/tmp/nadi-concepts-qa`, `/tmp/nadi-data-qa`, and
`/tmp/nadi-final-preview`. See [development handoff](docs/development-handoff.md). Earlier
foundation evidence remains at `/tmp/nadi-laravel-qa` (temporary artifacts).

Official sources:
- https://github.com/laravel/framework/releases/tag/v13.40.0
- https://github.com/laravel/laravel/releases/tag/v13.11.0
- https://laravel.com/framework/docs/13.x/authentication
- https://laravel.com/framework/docs/13.x/authorization

## Workspace rename

Repository: <https://github.com/johnd-creator/BSLA>.
Physical root: `/home/john-d/Music/BSLA`.
The old `/home/john-d/Music/reliability-knowledge-starter` is retained as a symlink
for existing Docker bind mounts, systemd services, virtual environments and Git
worktree pointers. Do not remove that compatibility path as routine cleanup.
The Compose project is still **reliability-cockpit-platform**, with the same
volumes. No global path rewrite, collector restart, commit, push, merge or deploy
was performed for this setup. Services keep using their established paths.

## Catatan roadmap — Pareto frekuensi gangguan

Tahap awal yang direncanakan adalah Pareto **jumlah WO yang diklasifikasikan sebagai
WO gangguan per aset**, dengan filter periode/tanggal acuan, site/organisasi, unit,
aset, status WO, dan klasifikasi gangguan yang terverifikasi. Tentukan aturan WO
batal, WO duplikat, relasi task/parent, serta WO tanpa aset sebelum menghitung.
Tampilkan aturan hitung, cakupan dan kelengkapan data bersama hasilnya. Jangan
menganggap semua WO sebagai WO gangguan atau mengarang klasifikasi sumber.

**Jumlah WO bukan jumlah kejadian gangguan nyata.** Satu kejadian dapat memiliki
beberapa WO; sebagian kejadian juga dapat belum memiliki WO. Setelah definisi
awal disepakati, korelasikan kandidat dengan historian/status operasi pada waktu
yang selaras, lalu minta validasi manusia untuk hubungan WO–kejadian dan konteks
operasinya. Catatan ini belum mengimplementasikan collector, pipeline, integrasi
historian, penghitungan Pareto, maupun scoring.


## Four local development accounts

Login accepts username or email. The four requested accounts are marked
`development_only`: login and every authenticated request require local environment,
loopback client IP, and a loopback Host. The preview currently binds 127.0.0.1:8010.
Their shared memorable phrase is not a production password and is never printed or
tracked. Replace passwords via Admin → User management → Kelola. The credential
file records initial values only. Existing account uniqueness and password policy
are retained. For a fresh isolated development checkout, the private one-time
command is `php artisan nadi:dev-users --memorable`; it refuses to overwrite users.

## WAPPR development rule

Retain the source record/status. WAPPR is presented separately as waiting for
approval/backlog, not automatically a failure, validated incident or score input.
Future counts require agreed work type, evidence, date basis, deduplication and
status rules. Historian/status correlation and human validation remain separate
work. Weighted reliability scoring is deferred. No collector filter was changed.

See [concept notes](docs/concepts.md) for the pixel-verified scope and data boundaries.


## BSR Asset mapping

Master Asset → Mapping BSR displays a non-destructive draft from the owner-supplied
`asset(1).xlsx`, sheet HIRARKI REVISI (12,048 populated rows). The local canonical
Registry snapshot contains 845 assets. Only 837 with explicit site BSR, organization
IP, unit CS01 enter the mapping: 798 unique exact matches, 11 ambiguous, 28 without
an exact match. Excluded: 1 CS02, 1 CS03, and 6 unknown-unit assets.

KKS OLD/NEW, parent proposals and alias remain document candidates. New identities
and parents are not applied. Engineering groups are labelled inference (616
classified, 221 unresolved), not source facts. No fuzzy matching or unit/child
guessing occurs. Existing Registry membership and source records remain intact.
The generated overlay is in `../maximo-knowledge/mappings/bsr-hierarchy-draft.json`;
the repeatable local-only preparation script and six hermetic safety tests live
in maximo-knowledge. The source workbook is unchanged.

## Work Order detail

Open Master Asset → Work Orders, an Asset's linked WO list, or a WAPPR reference
in Action Board. Description first uses the Mart DTO when available. For the
currently running older API, NADI can read only the description from the existing
loopback Maximo Collector (`MAXIMO_COLLECTOR_API_BASE`, default 127.0.0.1:8002),
after exact WO-number **and Asset-number** matching. Raw Collector payloads, people
and prices are not exposed or copied. Only GET is used; this never triggers sync.

Final elapsed execution hours are computed only for source status CLOSE and two
valid explicit-zone actual timestamps. Missing, invalid, naive or reversed clocks
produce no duration. No status/report/schedule date, stored estimate, labor or
downtime is substituted; valid identical clocks give a real zero. This is not a
reliability score, failure duration or incident count.

Compatible Collector/Mart source fixes are present and tested locally: scoped
clock evidence retention (reusing the prior PR #130 helper), description projection,
a read-only detail DTO, and strict elapsed duration. No new operational DB/column
migration, worker restart, candidate activation or historical recovery was run.
Existing historical actual timestamps that are absent remain visibly unavailable.
The sampled real CLOSE WO has a local description but no actual pair.

Final component validation: Collector 142 tests, Cockpit 121 tests (hermetic SQLite
smoke fixture), mapping 6 tests, all 24 JSON schemas, Laravel 41/378 assertions,
Pint, Composer validation/platform, and frontend build. Private browser evidence:
`/tmp/nadi-concepts-qa` and `/tmp/nadi-data-qa`.

## Operasi — fondasi layar proses

Open `/operations` after login. All four development roles can read it. The menu
uses the existing Registry GET API for bounded equipment selection (25 per page)
and unit filtering. An exact canonical Asset detail supplies the context; links
open Master Asset and equipment-scoped WO. Engineer can open a local inspection
draft with that same Asset reference. No new role or privilege is introduced.

The process canvas intentionally has no equipment arrangement, pipes, live value,
alarm state or controls. Wonderware/Foxboro screen references must be provided and
verified before their layout and value positions can be reproduced. Historian
adapter/tag mapping and cache are **not connected/active**. Source units, timestamps,
quality, data age and stale indicators must be verified when integrating them.
A Registry status is a source Asset record status, never inferred realtime health.

This read-only foundation joins navigation context for operations, maintenance and
engineering; it is not an HMI replacement or a claim that historian/engineering
analysis is integrated. There is no polling, adapter/source connection, database
migration, source record copying or control command in this module.

Reliability attention stays neutral **Belum dinilai**. Future equipment colors
must link to a validated score/Pareto basis, period and source evidence. No score,
loss, incident count or healthy/alarm color is invented. WAPPR remains separate
backlog; a WO count does not establish a validated incident count.

Operasi verification: 7 focused feature tests within the full **50 tests / 481
assertions**, plus **13 real browser checks** across all four roles, actual bounded
Registry equipment selection, shared context links, unit/pagination, no polling,
and desktop/mobile overflow. Pint, frontend build and whitespace checks passed.
No source-service restart, collector edit, migration or adapter installation was
needed. Local browser JSON evidence: `/tmp/nadi-operations-qa/results.json`.

## Tampilan ringkas Laravel

UI pada 6 November 2026 disederhanakan menjadi panel/form netral, satu header
halaman, navigasi ringkas, dan tabel lebih padat. Login tidak lagi memakai hero
dua kolom. Semua batas data, role, dan draft tetap berlaku.

Lihat [audit kepadatan UI](docs/ui-density-audit.md) untuk ukuran sebelum/sesudah
dan hasil verifikasi, termasuk batasan uji visual browser. Jalankan
`npm run test:ui` untuk regresi logika navigasi, bersama pemeriksaan di atas.


Polesan lanjutan mempertahankan kepadatan tersebut dengan sidebar navy, aksen teal,
ikon seragam, dan hover/focus halus. Akun dan tombol Keluar dipindahkan ke header
kanan atas yang tetap terlihat saat scroll. Verifikasi akhir: 55 test Laravel /
513 assertion dan 8 test frontend, Pint, Composer validate/platform, serta build
lulus. QA visual browser masih terbatas karena browser terhubung tidak tersedia.
