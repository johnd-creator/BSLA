# AGENTS.md — Reliability Data Contracts

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

Maintain vendor-neutral semantic contracts for reliability applications.

## Rules

1. Do not copy vendor-specific payloads directly into core contracts.
2. Preserve source-system identifiers under `sources`.
3. Prefer stable organization-owned IDs where available.
4. Document units explicitly.
5. Use ISO-8601 timestamps.
6. Mark nullable/unknown fields intentionally.
7. Backward-compatible changes are preferred.
8. Breaking schema changes require a version bump.

## Reliability and public contracts

Keep technical source evidence separate from governed business definitions.
Failure code/WO is not a failure occurrence; CLOSE elapsed execution/labor is not
repair/restoration; MXWODETAIL downtime is boolean, not hours. Date-only values
must not acquire fabricated timezones/midnight. MTBF/MTTR need the validated
event, exposure and repair boundaries in `../plans/MTBF-MTTR.md`.

Optional evidence additions must preserve old consumers, identity/scope/version
and missing-versus-null semantics. Do not expose raw `sources.*` merely because
a schema accepts it: public Mart DTO allowlists are deliberately narrower.
Validate every current schema with Draft 2020-12 and affected serializer/consumer
fixtures; a schema-ready status is not implemented/verified product readiness.
