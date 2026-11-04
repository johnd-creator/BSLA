# NADI-AUD-02B-B2 — Durable deferred obligation candidate

## 1. Executive summary

**Disabled, isolated B2 implementation; Astra F-03 remains OPEN.**
A version-aware obligation ledger now accompanies B1 dispositions in the same
PostgreSQL transaction. Debt survives recapture, deletion/omission of local source
rows, restart and source-date changes. Resolution requires an explicit controlled
transition and a matching committed receipt; dependency repair alone is insufficient.
No B3 scanner/replay, operational migration, source request or runtime action exists.

Precommit synthetic qualification: **228 offline tests and 85 real PostgreSQL tests
PASS**, no skips/failures/errors/blocked external I/O. This preliminary local run used
Python 3.14.3/PostgreSQL 18.6; supported-Python exact-head CI is separately authoritative.

## 2. Baseline and dependency chain

- Main: `4914a73fc7b640b6dd0667d0450fdb12aa04c452`.
- B1: [PR95](https://github.com/johnd-creator/reliability-knowledge-starter/pull/95),
  `ce6a29a29fb55a5c72612bc981e32b220768b27e`, OPEN/DRAFT and unmodified.
- B1 [exact-head CI 38857614073](https://github.com/johnd-creator/reliability-knowledge-starter/actions/runs/38857614073): PASS.
- Discovery: independent DRAFT [PR94](https://github.com/johnd-creator/reliability-knowledge-starter/pull/94),
  `71d2f3802b325e1cf36563db556364444305ec7f`.
- B2 branch: `codex/nadi-aud02b-b2-deferred-ledger`, isolated worktree from exact B1.

**Stacked candidate dependent on PR95. Do not merge B2 ahead of B1.** The DRAFT PR
must target main for the existing exact-head qualifier; this does not make B1 merged.
Review the cumulative main→B2 diff separately from incremental B1→B2:

```text
git diff 4914a73fc7b640b6dd0667d0450fdb12aa04c452..HEAD
git diff ce6a29a29fb55a5c72612bc981e32b220768b27e..HEAD
```

Graph project generation was stale for B1/B2 candidate files; coverage was checked
and the pinned worktree source was read directly. No runtime/DB discovery substituted
for missing graph coverage. Existing untracked workbook and dirty generated files in
other worktrees are preserved; no checkout was switched.

## 3. Incremental changed-file inventory

| Incremental B1→B2 file | Responsibility |
|---|---|
| [deferred_models.py](../src/repositories/deferred_models.py) | Separate candidate SQL metadata, not operational Base |
| [deferred_store.py](../src/repositories/deferred_store.py) | Identity, classification, ledger, bounded state machine and coverage proof |
| [005 candidate SQL](../migrations/005_deferred_obligation_candidate.sql) | Follow-on tables/indexes/constraints and audit guards |
| [projection_store.py](../src/repositories/projection_store.py) | Three extension hooks; base B1 behavior unchanged |
| [offline B2 tests](../tests/test_deferred_store.py) | 11 new pure-policy/default-disabled regressions |
| [PostgreSQL B2 tests](../tests_postgres/test_deferred_postgres.py) | 47 new transactional/state-machine/schema regressions |
| [PG fixture runner](../../.github/scripts/maximo_ci/run_projection_pg.py) | Display wording only; established isolation/guards unchanged |
| [CI workflow](../../.github/workflows/nadi-maximo-collector.yml) | Display labels B1+B2 only; qualification route/gates unchanged |
| This report | B2 evidence and B3 handoff |

Nine incremental files; cumulative main→B2 also includes the eleven B1 files (17
unique cumulative files). B1 migrations/models/tests/report/MartWriter remain unchanged
relative to B1. No CLI, Compose, public contract, Cockpit, PI/CEMS, engineering decision,
roadmap/policy or operational environment file is changed.

## 4. Obligation identity model

`family_identity` hashes protocol version, projection domain, MAXIMO object, exact
local source PK, target scope/prefix policy, policy epoch and mapper/contract epoch.
It deliberately excludes source timestamps and fingerprints. The scope key identifies
the **intended** BSR/IP projection context; UNKNOWN proof is stored explicitly on the
version, not invented into a source scope or a second unrelated family.

`mart_deferred_family` has one stable source/domain/scope/policy identity and a current
version pointer. `mart_deferred_version` retains fingerprint, version/predecessor,
capture run/manifest/ordinal, scope proof, safely derived canonical ID, classification,
reason, first occurrence, last projection attempt, attempt count, revision, last event,
resolution reference and writer owner/fence. First family occurrence is the retained
first version; per-version occurrence/attempt times never replace that history.

No source payload, person identity, credential, raw source JSON or exception text is
copied into long-lived debt tables. Evidence references point to immutable B1 inputs.
The fixed candidate epoch is `deferred-v1-BSR-IP-WO-BSR`; B1 mapper epoch is preserved.
Mapper or policy changes require a reviewed epoch/compatibility decision.

## 5. Dependency and failure classification

| Input outcome | Internal classification / behavior |
|---|---|
| Approved existing WO-prefix exclusion | EXPECTED_EXCLUSION receipt, no new debt |
| Missing local Equipment / normalized identity | DEFERRED_DEPENDENCY / scoped local-Equipment key |
| Unproven BSR/IP | DEFERRED_SCOPE_PROOF; site/org/canonical target remain unknown when unsupported |
| Missing required Asset identifier | DEFERRED_MAPPING; safe correction prerequisite, no fabricated target |
| Other invalid mapper input, including invalid timestamp | FAILED_MAPPING + BLOCKED_NEEDS_REVIEW, immutable FAILED item receipt |
| A newer version has a valid target while prior debt exists | RESOLUTION_PENDING; explicit reconciliation still required |
| Writer validation, scope, persistence or DB failure | Propagates; transaction rolls back, item remains UNPROCESSED, never ordinary deferral |

WO BSR/IP proof inherits the already-approved scoped local Collector ownership/prefix
contract; a prefix is not independent evidence of an arbitrary external database's
organization. Operational owner/scope verification is still a rollout gate.
Missing **target Asset** remains an accepted soft reference, distinct from missing
local Equipment. No hard FK or new target-Asset defer rule is introduced.

Dependencies are normalized, immutable references with `(kind, scoped_key, obligation)`
lookup indexing. The current policy emits one reviewed dependency per version. The
schema supports multiple references without additional active debt; synthetic tests
exercise this shape. General audited dependency extension requires a future reviewed
interface, not arbitrary caller-supplied keys.

## 6. Schema and migration compatibility

Order: existing schemas → B1 candidate **004** → B2 candidate **005**.
Only new follow-on 005 is added; no deployed/B1 migration bytes/checksums are edited.
005 fails if 004 is absent and refuses reapplication. It is never auto-applied.
Candidate metadata remains separate from operational `Base`/`create_all`.

005 adds family, version, dependency, event and receipt-occurrence tables. Uniqueness
covers scoped source identity, family/version, one active version (partial unique
index), event key, event revision and manifest-item occurrence. FKs bind inputs and
audit references. Deferred constraints permit atomic supersession/event creation
without independent commits. Ordinary UPDATE/DELETE of audit/reference records and
DELETE/TRUNCATE of debt are rejected; this is not a defense against an unrestricted
DBA disabling guards or dropping objects.

Preflight checks exact columns/types/nullability/PKs, required constraints/indexes,
reviewed function hashes and trigger attachments/flags. A normalized catalog digest
pins **actual constraint and index definitions**, including active-state predicates;
missing objects and altered predicates fail closed. B1 preflight remains mandatory.
Actual operational grants, migration ledger/checksum packaging and role privileges
were not queried or changed.

## 7. Atomicity and fencing evidence

B1 item processing calls the B2 receipt hook after staging the item disposition but
before scan continuation/commit. The same Session/connection/transaction owns target
write (if any), sidecar, disposition, debt/version, dependency, audit event, occurrence
link and continuation. No hidden ledger commit or second DSN exists.

Executed tests inject a before-commit exception and real driver-connection loss:
no debt/event/receipt/continuation survives. A lost acknowledgment after commit
preserves all evidence; restart resumes without duplicating a debt/event. Resolution
transition failure similarly rolls back its audit/state change. These are transaction
boundary tests, not machine/power-failure qualification.

Every repository mutation uses the B1 domain lock and checks owner, fence, latest run
and DB-clock expiry. Version SQL guards also reject expired/stale ownership and
invalid revision/state edges; deferred audit guards require the matching transition.
CAS plus domain serialization permits one of two concurrent resolution requests to
commit; the stale request fails. The tests use the private fixture owner, not a
production least-privilege application-role deployment.

## 8. Version and supersession model

Identical repeated delivery of one committed manifest item is a no-op. A distinct
captured occurrence of the same failure links to the same version and records one
bounded attempt/event. Fingerprint changes create a new version with predecessor
lineage. An active old version transitions to SUPERSEDED_BY_NEW_VERSION and points
to its successor in the same transaction; the successor remains active/incomplete.

A previously RESOLVED version remains immutable/RESOLVED when a newer version is
observed; the successor and SOURCE_VERSION_CHANGED event retain the lineage. The
newer target receipt does not silently resolve this successor. If a deterministic
identical fingerprint unexpectedly changes from resolved to failed, processing refuses
pending an epoch/policy review rather than inventing a source-version change.

B1 receipts and historical PARTIAL runs are never rewritten. Source deletion,
backdated changes, NULL dates and timestamp ties do not erase debt.

## 9. Resolution audit design

The repository's synthetic controlled transition capability is **off by default**.
It is not an HTTP API, new RBAC model or operational authority. An enabled test caller
must supply the current fenced ticket, current obligation version, expected revision,
allowlisted action, bounded event UUID and exact evidence run/ordinal.

Supported edges include OPEN→ELIGIBLE_FOR_RETRY→RESOLVED and OPEN→BLOCKED_NEEDS_REVIEW;
source observation may supersede an active version. BLOCKED cannot be casually
unblocked through this API. Every transition stores sanitized reason, input evidence,
revision, time and writer attribution. Duplicate keys require identical intent;
collision, stale revision, wrong record/version/run and missing capability fail closed.

Resolution rechecks a current sealed compatible manifest, exact source/fingerprint,
committed terminal receipt and actual target digest. Existing approved exclusion
proof is re-evaluated against the same exact identity; an unrelated excluded WO cannot
resolve debt. Under today's immutable prefix predicate, an already in-scope WO cannot
become out-of-prefix without changing identity; no new exclusion/adjudication policy
is invented. Executed positive resolutions use actual supported target receipts.

Repaired dependencies/new targets alone leave OPEN debt. After explicit audited
resolution, a later/current clean generation can complete; old DEFERRED receipts and
PARTIAL run outcomes remain immutable. Unlinked pre-B2/B1 debt stays UNKNOWN/incomplete,
not auto-imported or forgiven. Bounded completion proof revalidation rejects target
drift even when a later manifest is empty.

## 10. Resource and retention limits

| Candidate bound | Default / supported hard range |
|---|---|
| Source obligation identities per transaction | Exactly 1 |
| Transition events per transaction | 2; configurable 1–2 (supersession needs 2) |
| Captured attempts per version | 5; configurable 1–20 |
| Audit transitions per version | 16; configurable 4–64 |
| Versions per source identity | 16; configurable 1–128 |
| Dependencies supplied per new version | 4; configurable 1–8 |
| Resolved proofs checked per completion | 1,000; configurable 1–10,000 |
| Policy expiry | Optional aware timestamp; expired policy refuses mutation/completion |
| Resolved/unresolved metadata retention | Retain indefinitely; no purge API |

Attempts count captured projection occurrences while debt is active, including valid
receipts awaiting reconciliation; last attempt and audit transitions remain distinct.
At the attempt cap debt becomes BLOCKED; further attempts remain unprocessed. Version,
transition or coverage caps refuse/roll back without deleting pending work or faking an
event. Limits require integer values. A one-event batch cannot partially supersede a
version; both events roll back/refuse. No automatic budget increase exists.

Retention policy is **CANDIDATE**, not operationally approved. Expiry never expires
data; it blocks mutation/completion, including empty generations. Statement/lock/time
limits inherited from B1 remain enabled. Total installation capacity, retention/
archival approval, workload cost and long-term proof compaction need data-owner review.
There is no future replay full-table scan hidden in this implementation.

## 11. Test matrix and actual local results

| Suite | Existing before B1 | Existing B1 additions | New B2 | Total |
|---|---:|---:|---:|---:|
| Offline Collector | 202 | 15 | 11 | 228 PASS |
| Private disposable PostgreSQL | — | 38 | 47 | 85 PASS |
| CI infrastructure | 21 | 2 | 0 | 23 PASS |

All 20 requested scenario groups are covered: single missing-Equipment debt; duplicate
failure; restart/scoped dependency; cross-generation omission; fingerprint supersession;
unknown scope; approved exclusion; mapper vs writer error; before-commit exception/
disconnect; after-commit lost reply; stale lease/fence; concurrent resolution; supported
receipt proof; idempotency; poison caps; retention expiry; NULL/ties; backdated change;
complete-coverage withholding; and unchanged AUD-01/specialized-WO/asset baseline suites.
Additional negatives cover missing/changed indexes/constraints, migration order,
immutable receipts/audit, disabled capabilities, revision/identity collisions, history/
version/batch budgets, source deletion, nested-data avoidance and legacy restrictions.

All PG cases assert unchanged synthetic source `sync_cursor`. B1 test files remain
byte-identical. Only the established independently identified Unix-only disposable
cluster runner was used: no operational/persistent-QA DB, TCP listener, inherited
credentials, source access, Docker or existing service inspection. Clusters stop after
tests; private logs/data are retained under runner-owned `/tmp/nadi-b1-pg-*` directories.

Review corrections included exact catalog-definition checks, explicit attempt/batch
semantics, empty-generation policy-expiry refusal and same-fingerprint inconsistency
refusal. Local development iterations passed their then-current suites; no failed
application/operational attempt was hidden or retried. Precommit metadata identifies
the B1 checkout plus uncommitted B2 source; it is not exact-head B2 CI evidence.

## 12. Exact-head CI evidence

The established qualifier selects an open same-repository PR against main, verifies
its exact HEAD/clean source, runs the entire offline suite and separate disposable
PG suite on **Python 3.11 and 3.12**, and rechecks the current HEAD in a fresh final job.
No CI safety predicate, secret boundary, fixture identity check or operational access
restriction was weakened. B2 changes runner/workflow display labels only.

Exact tested source SHA, workflow SHA, Python/PG versions, test counts and fresh-head
gate are recorded in the DRAFT PR checks and final delivery evidence. A green B1 run
is dependency evidence, never substituted for B2 exact-head qualification. No unrun
or skipped PG test can be counted as PASS.

## 13. Legacy-writer constraints

**RESTRICTED.** A feature flag/exclusive-writer assertion does not fence existing
projector/bootstrap/controlled loaders that bypass the domain protocol. B1 target
revision/drift checks remain enabled, but do not make concurrent legacy writers safe.
Before operational use, require shared compatible fencing or explicitly approved
exclusion of incompatible same-target writers and a compatible reader/rollback plan.
No writer was stopped, inspected, modified or restarted in this task.

## 14. Known limitations

- No B3 due scanner, targeted recovery capture, retry/backoff, watcher, CLI or scheduler.
- No automatic migration, debt import, source deletion resolution or data cleanup.
- No public status/contract or Phase1 policy change; F-03 remains OPEN.
- Pre-B2 debt without links still blocks completion and needs separately reviewed reconciliation.
- Active healthy receipts awaiting manual reconciliation still consume bounded history;
  exhaustion requires review, never silent forgiveness or operational limit increases.
- Global storage sizing/archival/compaction, least-privilege grants, owner/co-location and
  rollout compatibility remain unqualified operational gates.
- Synthetic transition opt-in/fenced ownership is not application-level organizational
  authentication/RBAC. Any operational transition surface requires separate review.
- Current policy creates one dependency per version; broader multi-dependency changes
  require an audited interface and matching limits in B3.

## 15. B3 handoff contract — designed, not implemented

| Future interface | Required contract |
|---|---|
| Due selection | Domain/scope/policy-bound, indexed keyset `(due_at,id)`, finite limit and fairness cursor; no unbounded scan |
| Dependency readiness | Exact typed scoped keys; return READY/NOT_READY/UNKNOWN from local authorized evidence; no source GET |
| Attempt lease | Current domain owner/fence plus obligation revision; serialize/reject stale claims |
| Targeted recovery input | Short consistent snapshot by exact source identity, minimal allowlist, bounded seal/fingerprint; no full Collector rescan or source-date overlap |
| Version reconciliation | Compare captured fingerprint/epoch and current version; create audited lineage, never overwrite newer target data |
| Bounded retry | Existing item/target/ledger/receipt transaction; reject ambiguity and preserve unprocessed/deferred evidence |
| Backoff/poison | Approved finite attempts/due times, explicit review/unblock policy; no tight retry loop or silent budget extension |
| Resolution | Valid current target/exclusion receipt, exact revision/event identity and immutable audited transition |
| Fairness/resources | Bounded batches, dependency indexes, per-domain fairness and proof/retention capacity gates |

B2 supplies identities, versions, dependency indexing, revisioned transitions and
atomic hooks only. B3 must implement and qualify these interfaces under its own task;
this handoff authorizes no operational replay, worker or source acquisition.

## 16. Operational blockers and Senior Review recommendation

**GO for Senior Review of disabled B2; NO-GO for operational rollout.** Review B1→B2
incremental changes independently, retain PR95 as the stacked dependency, and wait for
separate B3 authorization. Do not merge this DRAFT ahead of B1 or auto-merge any PR.

Operational migration/checksums/grants, verified backups/disposable restore, actual
owner/co-location, legacy writer exclusion/shared fencing, B3–B5 qualification,
compatible read status/rollback and data-owner policy/load acceptance remain required.
Rollback must retain debt, audit and immutable B1 evidence; returning to an incompatible
legacy writer cannot certify coverage. No actual runtime rollback is needed or run.

PR90/93/94/95 and frozen PR75–81 remain unmodified. All databases/sessions, collectors,
Mart services, original PNG/workbook, other worktrees, localhost3000, Phase1 governance
and 26 pending engineering decisions are preserved. No operational DDL, DB inspection,
source login/GET, replay, deployment, merge or engineering/PdM activation is performed.
