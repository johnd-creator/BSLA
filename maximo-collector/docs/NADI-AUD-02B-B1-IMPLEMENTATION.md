# NADI-AUD-02B-B1 — Stable capture and atomic receipt candidate

## 1. Baseline and changed files

**Candidate implementation only; F-03 remains OPEN. No operational acceptance.**
Main: `4914a73fc7b640b6dd0667d0450fdb12aa04c452` (merged PR91).
Branch: `codex/nadi-aud02b-b1-stable-capture`, created in an isolated worktree.
Pinned discovery: [PR94](https://github.com/johnd-creator/reliability-knowledge-starter/pull/94),
`71d2f3802b325e1cf36563db556364444305ec7f`, still independent DRAFT.
PR90/93/94 and frozen runtime investigations are not modified.

| File | Responsibility |
|---|---|
| [projection_models.py](../src/repositories/projection_models.py) | Separate candidate metadata; not registered with operational Base/create_all |
| [projection_store.py](../src/repositories/projection_store.py) | Disabled constructor, bounded local snapshot, seal, domain fencing, atomic item processing |
| [mart.py](../src/services/mart.py) | Existing owning-transaction API plus caller-owned session path |
| [004 candidate SQL](../migrations/004_projection_capture_candidate.sql) | New additive tables/immutability and progress guards; no automatic runner |
| [offline regressions](../tests/test_projection_store.py) | 15 source-free regressions |
| [PostgreSQL regressions](../tests_postgres/test_capture_postgres.py) | MVCC, transaction, interruption, identity, drift and fencing proofs |
| [fixture context](../tests_postgres/fixture_context.py) | In-memory URL supplied only by disposable-cluster runner |
| [PG runner](../../.github/scripts/maximo_ci/run_projection_pg.py) | Creates/verifies/stops its own private Unix-only PostgreSQL cluster |
| [qualification tests](../../.github/scripts/maximo_ci/tests/test_qualification.py) | Existing CI safety checks plus PG-gate/fixture-target negatives |
| [workflow](../../.github/workflows/nadi-maximo-collector.yml) | Separate PG lanes, same exact-head selection and final recheck |
| This report | Design, evidence and limitations |

The existing local projector, CLI, Compose, source store/cursors, deployed migrations,
public contracts, Cockpit readers and application routes are unchanged.

## 2. Architecture and transaction design

One explicitly supplied PostgreSQL engine owns local input, canonical target and
candidate tables. There is no second DSN or environment fallback. Split-database
atomicity is unsupported. Actual operational co-location/roles were not inspected.

1. Commit an identified CAPTURING attempt and a monotonically increasing domain fence.
2. In one REPEATABLE READ transaction, lock the domain, capture approved scalars by
   PK keyset, insert bounded input items, record the PostgreSQL snapshot and seal.
3. Process only sealed items by durable next ordinal. For each item, the same
   Session/transaction owns target upsert, target-version sidecar, immutable receipt
   and continuation. No target/receipt independent commits exist.
4. Only a fully acknowledged, reconciled generation with no historical unresolved
   sealed items may advance candidate last-complete coverage. No source timestamp
   watermark or existing `mart_projection_state` is advanced by this module.

Latest attempt and last-complete run/time are separate domain fields. COMPLETE means
coverage of **the captured snapshot and fixed scope**, not present-time source
freshness, accepted operational completeness or recovery of deleted historical data.
A process crash can leave an unfinished CAPTURING/SEALED/PARTIAL attempt; it is not
silently relabeled successful. Persistence/validation exceptions propagate with no
receipt for the uncommitted item. This is explicitly UNPROCESSED work, not exclusion.

## 3. Manifest and fingerprint semantics

Domain is `asset_master` or `maintenance_event`; fixed candidate scope is MAXIMO,
BSR/IP and the existing default BSR WO prefix. Other configured prefixes require a
reviewed scope/epoch variant; no private operational configuration is loaded.
Epoch `contract1.0-local-mapper-b1-v1` must change with capture/mapper semantics.

Each fingerprint is SHA256 over deterministic JSON of epoch, scope, domain, source
PK and the approved captured inputs. The ordered seal hashes ordinal/PK/fingerprint;
run and manifest have separate UUIDs. NULL timestamps remain NULL. Backdated/equal
source dates never filter membership or stand in for commit order. Changes committed
after the snapshot, including old-dated ones, belong to a later full generation.

Equipment capture selects individually allowlisted Maximo scalar fields plus the
existing local fallbacks, preserving explicit NULL precedence. WO capture excludes
person fields and raw JSON; local Equipment existence is captured in the same MVCC
snapshot and normalization matches the existing mapper. Registry membership is
unchanged. Missing target Asset remains a soft logical reference as in current
contracts; missing **local** Equipment is DEFERRED, never PROJECTED. Unknown BSR/IP
proof is DEFERRED; only the explicit existing WO-prefix predicate is exclusion.

Sealed item membership/input and acknowledged receipts are protected by SQL triggers.
No mutable OFFSET pagination or mutable-table MAX checkpoint is used. Items cannot
be deleted through ordinary DML. Administrative bypass is not an application threat
boundary; rollout requires controlled roles, migration checksum and schema review.

## 4. Atomicity evidence

Executed PostgreSQL tests cover: exception after target/receipt staging before
commit (all roll back); real driver-connection loss before commit (server rollback,
no target/receipt/continuation); commit followed by a lost-client-reply exception
(receipt and target survive, restart does not duplicate writes). These are explicit
fault boundaries, not a claim to have tested machine/power/storage failure.

Caller-owned `MartWriter.persist_in_session` validates the entire batch, flushes and
never commits. Its caller must roll back on error. Existing `persist_collection`
continues owning commit/rollback and error propagation. Canonical IDs, scope/schema
validation, deterministic upsert, created timestamps and unchanged counters remain.

## 5. Fencing and concurrency

Participating workers take a domain row lock and verify owner UUID, fence, latest-run
identity and database-clock lease expiry before writes and again before commit.
Capture holds that lock until seal. New ownership requires lease expiry or explicit
release. Restart receives a new token for the latest sealed manifest only; older
workers cannot acknowledge, overwrite targets or move coverage. A genuine PG lock
conflict fails closed under lock_timeout.

Per-target sidecars bind canonical ID, run, fence, source fingerprint and actual
persisted-row digest. Prewrite and completion-time target drift checks refuse known
unfenced changes. An unchanged input fingerprint alone does not certify a target.
These checks **do not fence legacy writers** that ignore the protocol.

## 6. Resource bounds

| Limit | Default | Hard accepted maximum |
|---|---:|---:|
| Capture rows | 10,000 | 100,000 |
| Captured ID/payload JSON bytes | 16 MiB | 64 MiB |
| Capture wall-clock budget | 15 seconds | 60 seconds |
| PK page | 100 | 500 |
| Scalar SQL result | 8,192 bytes | Fixed; oversized scalar aborts, never truncates |
| Lease | 60 seconds | 300 seconds |
| Process call items | 100 | 500 |
| Process wall-clock budget | 10 seconds | 60 seconds |

SQL scalar-size checks bound fetched values; per-row/page/time checks abort oversized
capture atomically, leaving the identified attempt incomplete. Byte budget measures
canonical serialized ID/input, not PostgreSQL/WAL/index overhead. DB statement and
idle-in-transaction timeouts accompany a 1-second lock timeout; these are statement
limits plus cooperative wall-clock checks, not an OS-level hard real-time deadline.
Transaction/MVCC/WAL cost on actual populations is UNKNOWN. Defaults are synthetic
qualification values, not approved operational sizing (historical WO population
already exceeds default capture cap). No partial snapshot is resumed as a new
snapshot under the same manifest identity.

## 7. Migration and compatibility

New Maximo/Mart-owned migration candidate 004 is additive and deliberately not
idempotent: reapplying refuses rather than hiding drift. Existing 001–003/checksums
remain byte-identical. Only disposable tests apply 004. No deployed migration ledger,
Cockpit migration allowlist, grant or startup behavior is changed. Candidate models
have their own metadata; existing `Database.create_all()` never installs them.

Schema preflight verifies candidate table columns/types/nullability/primary keys and
exact reviewed active guard bodies/trigger kinds. Missing or drifted capability
fails closed; there is no legacy-success fallback. This is not an exhaustive DBA
schema/grant attestation: rollout still requires owner-approved migration checksum,
full constraint/index/grant inventory and least-privilege validation.

## 8. Legacy writer risks — RESTRICTED

`exclusive_writer=True` is a deliberate API prerequisite, **not evidence** that
concurrent writers are safe. Existing projector/bootstrap/controlled-loader writers
do not acquire this fence. They can overwrite canonical rows before/after a candidate
transaction or assert old SUCCEEDED state. B1 therefore cannot be activated alongside
incompatible same-target writers. A reviewed shared writer protocol or explicit
operator-approved exclusion of such writers is required. Acquisition itself need
not be paused. No such operational action is performed here.

Readers remain unchanged and do not consume candidate coverage; old success is not
retroactively certified. Public status vocabulary/Phase1 thresholds are unchanged.

## 9. Regression matrix

| Discovery case | Executed candidate assertion |
|---|---|
| T03 | Concurrent commits insert keys before/after page boundary; old MVCC manifest remains exact; next generation sees inserts |
| T04 | Later source mutation/higher timestamp is absent from captured version; new generation has new fingerprint |
| T05 | Before-commit exception/connection loss rolls back target+receipt; after-commit lost reply preserves both |
| T06 | Restart resumes next ordinal with new fence, stable receipts/created timestamps, no duplicate target |
| T10/T11 | NULL and equal timestamps preserved across multiple PK pages |
| T14 | Row/byte/scalar/time capture overruns fail unsealed; bounded processing remains PARTIAL |
| T17 | Backdated mutation appears in next generation regardless of old timestamp |
| T18 | Live-lease conflict, genuine lock contention, expired/stale token, newer generation and revision drift refuse |
| T01/T12 | Missing local Equipment is DEFERRED; scan may advance with receipt but complete remains held; historical unresolved work cannot disappear behind a new generation |
| Compatibility | Existing 202 tests preserved; 15 new offline tests include disabled gate, isolated metadata, scope/schema validation, no hidden commit |

Additional PG negatives cover immutable seal/items/receipts, continuation without
receipt, unknown scope vs exclusion, schema/trigger drift, migration reapply,
unauthorized data-field retention and writer rejection. All PG cases assert unchanged
synthetic `sync_cursor` before/after. Source acquisition is never called.

## 10. Suite and CI evidence

Precommit local qualification (Python 3.14.3; preliminary, not supported-version
acceptance): **217 offline tests = 202 existing + 15 new**, PASS, no skips/failures/
errors/blocked I/O. Private PostgreSQL **18.6**, new Unix-only cluster per run; no TCP
listener, no inherited/private DSN, exact database/owner/data-directory and independent
on-disk system-identifier checks. Cluster stopped after tests; private data/logs
retained under `/tmp/nadi-b1-pg-*`. Precommit PG suite: **38/38 PASS** after review corrections. Final exact-head supported Python
3.11/3.12 results are recorded by the PR's qualification checks and delivery report.

Meaningful failed attempt retained: first PG execution had 27 passing cases and one
**test assertion error** (raw psycopg DuplicateTable was incorrectly expected to be
SQLAlchemy DBAPIError). Corrected to the actual raw-driver exception. Later runs
passed, including new review-driven connection-loss and drift regressions.
A distinct compatibility review found the initial refactor created a Session even
for dry-run/invalid input. Validation was restored ahead of session creation and two
regressions verify the original behavior without an available Database. No
operational retry, source request or data cleanup was used to obtain a PASS.

The original offline runner remains unchanged: all existing tests are still discovered
under its no-network/no-subprocess/no-external-DB guard. A separate hosted disposable
PG lane runs the real-PG suite on Python 3.11 and 3.12; its private socket is the only
allowed DB target. Fixture connection negatives reject operational DB names/ports,
other socket paths/owners and credential/service overrides. No PG tests are silently
skipped inside the offline suite. Final gate requires BOTH matrices and fresh current
PR-head recheck; selected source SHA and immutable workflow SHA remain distinct.

## 11. Remaining B2 dependencies

B1 deliberately has no cross-run obligation ledger, repair/replay, due scheduling,
backoff, poison-item escalation or resolution history. DEFERRED/FAILED/unprocessed
sealed input conservatively blocks subsequent complete coverage, even after source
repair/deletion; it cannot be silently forgiven by recapture. B2 must define durable
obligation identity/reason/dependency/version, audited resolution linking, approved
exclusion/target-readiness rules and retention. B3 must implement separately reviewed
bounded replay. No such functionality is implemented or implied here.

## 12. Rollout and rollback blockers

**NO-GO for operational deployment.** Separate authorization is required for actual
owner/co-location/schema/grants inventory, validated private backup/disposable restore,
reviewed additive migration packaging/checksums, shared-fencing or exclusion of legacy
writers, population/load sizing, B2/B3 completeness and B4 conservative reader wiring.
No operational migration or candidate invocation is authorized by this PR.

Rollback preserves manifests/receipts and any unresolved evidence. Do not drop tables,
delete debt, reset a cursor or revert to an incompatible unfenced writer and claim
coverage. A compatible rollback build or separately authorized projection-only pause
must be prepared before rollout; source acquisition/read-only APIs remain separate.
Current runtime needs no rollback because it has not been changed.

## 13. Senior review recommendation

Review B1 as a disabled foundation with executed synthetic transaction guarantees,
not F-03 closure or deployment approval. Proceed to AUD-02B-B2 only after Senior Review.
PR90/93/94 remain independent; all operational databases, QA records/sessions,
collectors, Mart services, Phase1 governance, original assets/workbook, other worktrees
and localhost3000 were not accessed or modified. No merge, source GET, scheduler,
replay, public status change or engineering/PdM activation is included.
