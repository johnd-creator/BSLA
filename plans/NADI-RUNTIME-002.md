# NADI-RUNTIME-002 — Existing Mart Governance Schema and Runtime Reconciliation

> Historical design/status reference retained for traceability. Current product
> work follows [NADI Laravel](NADI-LARAVEL.md) and [MTBF/MTTR](MTBF-MTTR.md).
> Phase/checkpoint statements below do not establish current runtime readiness
> or authorize implementation, collection, migrations or deployment.

Status: **CURRENT / CANDIDATE — runtime scope PASS, ready for senior review**.

PR #15 merged as `c052d7d`; fresh branch `codex/nadi-runtime-002`. Existing
Mart canonical governance 002/003 applied with private backup and all 17 factual
populations/fingerprints preserved; empty mapping table and SELECT-only reader
are operational. Only NADI API replaced. [Acceptance evidence and exact tests](../reliability-cockpit/docs/nadi-runtime-002.md).
**READY — NADI-IDN-002**; no real mapping/pilot performed, Phase 1 CURRENT/PARTIAL.

The paragraphs below preserve the initial task rationale, not post-task schema state.
Evidence: [NADI-PI-RUNTIME-001](../pi-collector/docs/nadi-pi-runtime-001.md),
7 October 2026, merged baseline `3e981a3`.

The accepted factual NADI runtime uses the existing `maximo-db` /
`maximo_collector` Reliability Mart via `RELIABILITY_MART_DATABASE_URL` supplied
by the feature checkout's Compose file. Its ignored Maximo override pins reviewed
WO collector/worker/projector image `2eacce47`; it does not supply the Mart DSN.
Mart Registry has 845 assets, but `public.asset_af_mapping` is absent. Merged
models/migration files are therefore not proof of deployed governance schema.

Scope:

1. Inventory exact accepted NADI API, Maximo WO worker/projector, DSNs, images,
   schema/migration ownership, local overrides and any actual read-only DB role.
2. Back up existing Maximo DB privately before any deliberate governance DDL.
   Review/apply only missing approved local Mart migrations with provenance and
   compatibility; preserve WO/Registry/Mart populations and all cursors. Do not
   execute init commands that accidentally migrate into legacy Cockpit DB.
3. Reconcile managed source-controlled projection/init ordering and driver/DSN
   settings with accepted WO recovery overrides, without importing the unrelated
   mixed feature/NK commit or blindly cherry-picking historical `7149455`.
4. Define external-mode Mart connection explicitly (never a new Mart database),
   preserve its no-source-worker property, and verify read-only query behavior.
5. Deploy only necessary local services after review; verify factual route/data
   acceptance and controlled mapping dry-run/import/verify/retire semantics on
   the actual existing Mart. Use synthetic fixtures only in isolated test DBs.

Exit: owning Mart and schema proven, governance table/migrations accepted,
SELECT-only reader and separate controlled local mapping commands verified,
Maximo WO recovery invariant intact, reproducible runtime wiring/rollback,
relevant mapping/Mart/runtime tests pass and review PR remains unmerged.
Then NADI-IDN-002 may establish a bounded human-verified pilot. No live AF crawl,
PI history download, guessed mappings, Reliability scoring, CEMS/NK changes,
source writes, database reset or replacement operational store are included.
