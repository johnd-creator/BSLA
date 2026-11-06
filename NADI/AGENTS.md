# NADI Laravel

Read the workspace root AGENTS.md first. This is the new Laravel development
application; the existing FastAPI/Next.js application and collectors stay intact.

- Work as a single developer in this active checkout: small changes, focused
  checks, directly usable preview. No routine extra worktrees or subagents.
- Accounts and local inspection drafts use ignored `database/development.sqlite`, explicitly authorized
  for isolated development. Never copy old accounts or run migrations against
  operational databases. Tests use SQLite `:memory:`.
- Assets use GET only through the existing Reliability Mart query API.
  Never import/write source assets, contact production, or run collectors.
- ADMIN, ENGINEER, SUPERVISOR, MANAGER are independent roles. ADMIN manages these local
  accounts; it implies no engineering permission or source access.
- Keep credentials, .env, SQLite, sessions and logs ignored. No commit, push,
  merge, deploy or replacing the existing port 3000 preview without a request.
- Checks: `composer test`, `vendor/bin/pint --test`, `npm run build`.
- Preview: `php artisan serve --host=127.0.0.1 --port=8010`; see README.md.
