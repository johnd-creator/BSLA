# NADI Laravel development workspace

This is a separate local Laravel UI using the existing read-only Reliability Mart
and Collector APIs. It does not replace the existing Next.js application, start
collectors, deploy services, or change operational databases.

## Local setup

Requires PHP 8.3+, Composer, Node, and extensions required by composer.lock.
Run `composer install` and `npm ci --ignore-scripts`. Copy `.env.example` to
`.env` only when `.env` does not exist, then generate a local application key.
Set `RELIABILITY_MART_API_BASE` to the authorized existing API.

The isolated SQLite development database is for local accounts and draft records
only. Create `database/development.sqlite` if absent and run `php artisan migrate`
only after confirming this isolated database is selected. Never migrate against
an operational store. Bootstrap an administrator with `php artisan nadi:admin`
and a development email address. Credentials are generated privately, not shipped
in this repository. Existing accounts and drafts must not be overwritten.

Build assets with `npm run build`, then preview with
`php artisan serve --host=127.0.0.1 --port=8010 --tries=1`.
Do not replace another application or expose the development preview publicly.

## Features and boundaries

- Local server-session authentication and independent ADMIN, ENGINEER,
  SUPERVISOR and MANAGER roles. ADMIN does not inherit engineering permissions.
- Read-only Asset inventory, exact-identity details, timeline, work-order history,
  yearly comparisons, data overview, and an operations context screen.
- Engineer-owned inspection/recommendation and PdM drafts, optimistic updates,
  duplicate-submission protection, and date-only or explicit-timezone readings.
- Source states, missing evidence, unavailable APIs and unknown units remain
  explicit. Work-order records are not validated incidents or health scores.
- Generic asset-family illustrations are display aids, not actual plant photos,
  equipment specifications, verified models or condition assessments.

## Private catalogs and mapping

Source workbooks, asset identities, extracted templates, mappings, measurements,
operational evidence, credentials and databases are not included in this release.
Provision a reviewed catalog in `storage/app/private/pdm-form-catalog.json` or
set `NADI_PDM_CATALOG` to its private absolute path. An optional exact-identity
mapping file uses `storage/app/private/asset-mapping.json`, or `NADI_ASSET_MAPPING`.
Unset these environment variables to use their default private locations.

Existing installations can point those settings at their existing private files;
there is no need to copy, rewrite, regenerate or import operational data. Preserve
existing catalog IDs and fingerprints so local draft history remains consistent.
A missing catalog displays an explicit unavailable state without fabricated data.
The synthetic file in `tests/Fixtures` exists solely for hermetic tests and must
not be used as an operational catalog or evidence of verified asset bindings.

## Checks

```sh
composer test
vendor/bin/pint --test
composer validate --no-check-publish
composer check-platform-reqs
npm run test:ui
npm run build
git diff --check
```

Tests use SQLite in memory, synthetic catalog fixtures and mocked HTTP. They do
not need source workbooks, production credentials or operational databases.
See [publication and integration notes](docs/publication.md).
