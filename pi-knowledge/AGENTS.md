# AGENTS.md — PI Knowledge

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

Discover and maintain authorized PI Web API knowledge for operational and reliability use without altering PI production configuration or data.

## Mandatory Safety Rules

1. READ ONLY.
2. Never perform state-changing calls.
3. Never create/delete/update PI Points, AF Elements, Attributes, analyses, event frames, or configuration.
4. Never brute-force WebIds, tag names, or authentication.
5. Prefer system navigation endpoints and documented API relations.
6. Respect server rate limits.
7. Never commit credentials, cookies, NTLM/Kerberos artifacts, tokens, or session data.
8. Save sanitized samples only.
9. Record units of measure and data type whenever discovered.
10. Record business meaning separately from technical tag names.
11. Never push directly to `main` unless explicitly instructed.

## Preferred Discovery Order

1. PI Web API root / system information
2. Data Servers
3. PI Points
4. Asset Servers
5. AF Databases
6. Elements
7. Attributes
8. Streams
9. Recorded values
10. Interpolated values
11. Summaries

## Git Rules

Inspect the current branch/status and continue directly in the active checkout.
No automatic branch, fetch or worktree is needed. Keep the knowledge evidence
change small and test locally before considering explicitly requested discovery.

Keep commits focused:

```text
feat(pi): catalog data servers
feat(pi): map BFP temperature tags
docs(pi): document stream query behavior
```

Do not merge, reset, force-push, or rewrite history unless explicitly authorized.

## NADI historian/exposure boundary

The PI Collector already exists in `../pi-collector/`; do not create another.
Technical registry entries are not verified NADI Asset↔AF signal mappings.
Historian exposure integration for MTBF is future work, requiring explicit state,
quality, time alignment, coverage and operating-boundary definitions. Never infer
Asset identity from tag similarity or calendar hours from absent data.

Do not retry credentials, discover production or change collection/backfill
without a covering request and a check of current runtime ownership.
Stored evidence may be read with its age/verification limits kept explicit.
