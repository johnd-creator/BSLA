# AGENTS.md — NADI Laravel

Read `../AGENTS.md` first. This is the active NADI product workspace, using
Laravel 13, Blade and Vite. FastAPI/Mart remains the data backend; the retained
Next.js preview and source collectors are not replaced by ordinary Laravel work.

## Solo developer loop

1. Check the current working tree, relevant routes/services/tests and feature doc.
2. Edit directly in this checkout. Keep changes small and preserve other work.
3. Test the affected behavior, including authorization, missing data and repeated
   submission where relevant. Build assets after CSS/JS edits and inspect the
   existing loopback preview. No routine extra worktree, subagent, handoff gate,
   parallel team or broad refactor is needed.
4. Run the broader checks warranted by the change, then report results and limits.
   For docs only: references, facts, `git diff --check`; no restart/migration.

Preview: `php artisan serve --host=127.0.0.1 --port=8010 --tries=1`, only if the
existing listener is not already serving NADI. Use built local assets (`npm run
build`), not a separate Vite server under the current strict CSP.

## Persistence and external boundaries

- Reuse ignored `database/development.sqlite`: accounts, inspection/recommendation
  drafts, PdM activities, manual disruption events/members/revisions, asset
  priorities/revisions, and workspace activities. This is development data, not
  disposable fixture data and not a replacement for any operational DB.
- Compatible migrations require checking the actual local target and a verified
  SQLite backup before application. Do not migrate/reset production, import old
  accounts, regenerate an existing app key or roll back populated history casually.
- Tests use SQLite `:memory:` + mocked HTTP. Browser fixtures use a separate
  temporary store/port; never seed synthetic users, incidents or priorities into
  the user's preview. Keep `.env`, SQLite, credentials, logs and backups ignored.
- Assets/WO are GET-only via the existing Reliability Mart API. Inventory and
  Registry differ; respect each feature's membership requirements. No source
  SQL, source-data replication, Asset auto-registration, production connection,
  new collector or collection trigger. The description-only fallback is limited
  to the existing loopback Collector with exact WO+Asset matching.
- Preserve DTO allowlists, 1 MiB body cap, timeouts and redirect rejection. Empty,
  unavailable, unverified and partial are different states; do not fabricate zero.

## Roles, revisions and semantics

- ADMIN manages only local accounts; it does not inherit ENGINEER write rights.
  ENGINEER can create and edit only its own engineering records. SUPERVISOR and
  MANAGER are read-only here, not business approval or risk-acceptance roles.
- Enforce server Gates on both forms and writes. Preserve account auth-version
  revocation, last-active-admin/self-change guards, optimistic version checks,
  idempotency keys, transaction boundaries and immutable-by-route revision history.
- PdM request, measurement, analysis and recommendation are distinct facts. Preserve
  exact Asset/template/unit/context grouping and date precision. Date-only values
  stay literal dates; sparse samples are not realtime/continuous monitoring.
- Disruption logs record manual observations and cause/affected/unknown roles.
  Event durations are not verified downtime; missing recovery does not mean still
  stopped. Cancellation retains history. One event may affect multiple assets;
  summing per-asset counts double-counts plant events.
- Action Board distinguishes engineer judgments from unassessed candidates.
  WAPPR remains backlog. Repeat-WO/failure-code clues are not validated failures.
  No automatic score, diagnosis, approval, external message or Maximo write-back.
- CLOSE actual elapsed execution is not MTTR; labor is not elapsed repair time;
  source boolean downtime is not hours. MTBF requires governed failures and
  operating exposure. Keep NOT_READY until the gates in `../plans/MTBF-MTTR.md`
  are met. Operations is a context/navigation foundation, not live HMI/historian.

## Checks and documentation

```bash
composer test
vendor/bin/pint --test
composer validate --no-check-publish
composer check-platform-reqs
npm run test:ui
npm run build
git diff --check
```

Read `README.md`, `../plans/NADI-LARAVEL.md`, and the relevant `docs/` feature
contract. Update current docs rather than appending competing completion counts.
Mark browser QA, runtime activation and production readiness separately. Do not
commit/push/merge/deploy or replace port 3000 without a covering request.
