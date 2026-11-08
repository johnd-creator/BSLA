# AGENTS.md — Maximo Knowledge

## Solo developer workflow

Follow root `../AGENTS.md`. Work directly in the active checkout: inspect existing
changes → edit a small scoped change → run relevant checks → inspect the result.
Preserve unrelated work. No routine extra worktree, subagent, mandatory branch,
handoff or layered approval process. Documentation-only work needs factual/link
checks and `git diff --check`, not source calls or restarts. Report checks actually
run and limitations. Do not commit/push/deploy or change runtime/data ownership
without a covering request. The active product UI is `../NADI/` (Laravel); this
component keeps its existing responsibility and safety boundary.

## Mission

Discover, verify, document, and maintain the Maximo API knowledge available to this organization without changing production data.

## Mandatory Safety Rules

1. READ ONLY for Maximo business data.
2. The sole POST exception is one controlled authentication handshake to the exact configured base URL plus `/j_security_check`, using a dedicated read-only account, runtime environment credentials, and an in-memory cookie jar.
3. Never execute POST, PUT, PATCH, DELETE, or MERGE against OSLC or other business resources, and never issue any state-changing request against production.
4. Never brute-force paths, IDs, object names, or credentials.
5. Prefer OpenAPI/OAS metadata and documented resources before probing.
6. Respect server-side rate limits and add delays when enumerating large collections.
7. Never store credentials, passwords, tokens, cookies, API keys, session identifiers, or Authorization headers.
8. Sanitize all saved response examples.
9. Do not commit personal data unless explicitly approved and required.
10. Do not infer business meaning without evidence.
11. If access behavior is uncertain, stop and record the endpoint as `unknown`.
12. Never change remote Git history.
13. Never push directly to `main` unless explicitly instructed.

## Discovery Procedure

For every resource:

1. Identify the documented endpoint.
2. Record HTTP method.
3. Record required/optional parameters.
4. Test the smallest safe read request.
5. Record status and access result.
6. Record response structure only.
7. Map relevant fields to business meaning.
8. Record pagination/filter/sort capabilities.
9. Store sanitized sample.
10. Update `verified_at`.

## Required Metadata Per Endpoint

- system
- resource
- endpoint
- method
- status
- access
- description
- parameters
- important_fields
- relationships
- use_cases
- notes
- verified_at

## Git Working Rules

Before editing, inspect `git status` and the current branch. Continue in the
active checkout; no automatic fetch/branch/worktree is required for local work.
Preserve existing edits and keep evidence changes focused. Source discovery is
opt-in and bounded even though it is read-only; documentation/UI work does not
authorize new source requests.

Use small commits:

```text
docs(maximo): document workorder endpoint
feat(discovery): add asset object structure
docs(mapping): map failure fields
```

Before reporting the result:

```bash
git diff --check
git status
```

Do not merge, rebase, reset, force-push, or delete branches unless explicitly instructed.

## Current NADI evidence boundary

Laravel consumes the existing Collector/Mart/API, never discovery directly.
Use `docs/mx-015a-maintenance-failure-semantics.md` and the Collector source-evidence
report for the newest technical findings. A field or schema name does not prove
failure identity, parent/child taxonomy, operating exposure or repair duration.
MXWODETAIL downtime is boolean. Failure Code business HTTP 400 is not proof of
a permission denial; preserve actual observed status. BSR workbook mappings stay
proposals unless separately validated/authorized, never auto-applied hierarchy.
