# NADI-AUD-02B-B3 — Bounded Dependency Recovery & Replay

## 1. Executive summary

Disabled synthetic candidate only. B3 recovers an old deferred Work Order by exact
local primary key after its Equipment dependency is repaired, without a timestamp
overlap, source acquisition, cursor change, or full source rescan. It reuses B1
immutable manifests, MartWriter's caller-owned transaction, and B2 versioned debt
and controlled resolution. Astra **F-03 remains OPEN**.

No operational/Persistent-QA database, service, browser endpoint, source system,
collector, session, frontend, or freshness policy was accessed or changed.
Migrations were applied only in independently verified disposable PostgreSQL.
This document is development evidence, not rollout approval or operational acceptance.

## 2. Exact baseline and dependency graph

| Layer | Exact commit | State at preflight |
| --- | --- | --- |
| main | `4914a73fc7b640b6dd0667d0450fdb12aa04c452` | Verified remote |
| B1, PR #95 | `ce6a29a29fb55a5c72612bc981e32b220768b27e` | OPEN / DRAFT |
| B2, PR #96 | `86d760c7f3cf8638ef2099f4e545ec315f82916e` | OPEN / DRAFT |
| B3 | `codex/nadi-aud02b-b3-bounded-replay` | New isolated branch from exact B2 |

Chain: main → PR95/B1 → PR96/B2 → B3. B2 exact-head qualification:
[run 38861970132](https://github.com/johnd-creator/reliability-knowledge-starter/actions/runs/38861970132).
B3 does not rewrite, rebase, merge, or modify either dependency branch. Its DRAFT
PR targets main because the existing immutable CI qualifier requires that base.
The PR head/check artifacts identify the delivered exact SHA; this report avoids
a circular claim that a file can embed its own final containing commit hash.

Graph metadata was insufficient for these unindexed candidate paths. Pinned
source, migrations, and tests were read directly; no completeness claim relies
on the older graph generation.

## 3. Incremental and cumulative inventory

Incremental B2 → B3:

- `src/repositories/projection_store.py`: default-preserving scope validation
  hook and pre-item hook. Default B1 accepts full scope only.
- `src/repositories/deferred_store.py`: B2 evidence proof uses the same strict
  scope hook. Default B2 still rejects targeted manifests.
- `src/repositories/replay_models.py`: separate metadata; never operational Base.
- `src/repositories/replay_store.py`: opt-in queue, schema checks, readiness,
  exact-ID capture, attempt reservation, audited stages and resolution.
- `src/services/projection_replay.py`: explicit bounded synchronous invocation;
  no startup registration, scheduler, daemon, CLI or environment DSN.
- `migrations/006_bounded_replay_candidate.sql`: additive candidate queue,
  append-only journal, index, stage/fence/audit guards. No edits to 004/005.
- `tests/test_projection_replay.py`: pure/offline safety and policy cases.
- `tests_postgres/test_replay_postgres.py`: new disposable recovery regressions.
- This report.

Cumulative main → B3 additionally contains unchanged B1 capture and MartWriter
transaction integration, B2 deferred ledger, 004/005 candidates, B1/B2 suites,
and the pinned read-only CI qualification infrastructure. Use the DRAFT PR's
cumulative diff and compare B2's exact SHA to the B3 head for the incremental
view. Collector acquisition, runtime wiring, API DTOs, deployment settings,
public routes, and existing test implementations are unchanged by B3.

## 4. Due selection and indexing

Explicit `register(ticket, obligation_id)` enrolls one current OPEN or
ELIGIBLE_FOR_RETRY version with exact family/domain/scope/epoch. There is no
startup scan/import of old B1 or B2 history. Initial BLOCKED debt is refused.
Duplicate identical enrollment is idempotent. Changed enrollment policy or an
externally repointed family requires explicit reconciliation; it is not reset.

`due()` returns at most 20 candidates ordered by `(due_at, family_id)`, with a
validated keyset continuation. The partial `replay_due` B-tree starts with domain,
scope, B2/replay epoch and pinned policy digest, followed by that ordering key;
it excludes DONE/BLOCKED queue rows. Its fixed phase predicate matches the query.
A stable statement-time cutoff supports indexed due ranges. Joins require current
B2 version and compatible mapper. RESOLVED versions are included solely to finish
an already existing claim after a resolution/DONE crash gap, never to replay it.

Claim transactions lock the B1 domain first, then the selected due row. A live
domain lease yields no claim. Scheduling delays move unready items behind older
due work; callers need not advance a cursor to get fairness. No source tables are
queried during due selection. Statement/lock timeouts bound database work as well
as result size. This is a synthetic index/ordering qualification, not production
cardinality or query-latency certification.

## 5. Exact local readiness contract

| Outcome | Meaning and behavior |
| --- | --- |
| READY | Exact current local input maps, or reviewed prefix exclusion applies |
| NOT_READY | Exact Equipment or required mapping input still missing; reschedule |
| UNKNOWN | BSR/IP not proven; reschedule without invented scope |
| UNKNOWN / SOURCE_ABSENT | Source row disappeared; block queue pending absence policy |
| BLOCKED | Invalid mapping, inconsistent dependency identity, or finite limit |

Only B2's typed LOCAL_EQUIPMENT, SCOPE_PROOF, MAPPING_INPUT and
RECEIPT_RECONCILIATION references are supported. References must match the original
immutable input's reviewed `describe()` result. Readiness re-reads the exact
local primary key and B1 allowlisted scalar fields. Equipment matching uses the
existing normalized reference with exact stored Equipment identity, not fuzzy
matching. Scope is not guessed; Registry and canonical Asset rows are not added.
A missing canonical Asset remains the existing soft reference, not a new failure.

A probe increments only B3 `probes`; it changes neither B2 attempts nor target
records. Unready probes do not manufacture receipt success. Persistent invalid
or unverified evidence is retained and cannot silently become READY.

## 6. Exact-identity recovery capture

One claim creates one new CAPTURING run under the domain fence. Its scope includes
`capture_mode=RECOVERY_BY_ID`, family ID, exact source ID, mapper/scope and replay
policy identities. The fingerprint retains B1's approved projection contract.
Targeted membership is explicitly different from full population coverage.

Capture uses one short REPEATABLE READ transaction for the exact-ID source query,
readiness, bounded scalar payload, input insert, ordered manifest digest, snapshot
ID and seal. B1 row/byte/time/scalar limits remain. Source NULL and backdated
timestamps are preserved, never advanced. Repairing Equipment changes the captured
boolean dependency proof/fingerprint even when the WO timestamp is unchanged.

Before any target write, the exact source and required exact Equipment row are
share-locked and fingerprint rechecked against the sealed input. Changes after
capture refuse replay and retain evidence for reviewed reconciliation. No old
fingerprint or matching receipt is synthesized. There is no absence/delete policy.

## 7. Execution and transaction boundaries

| Transaction | Durable result |
| --- | --- |
| Enrollment | Exact current debt + PENDING queue + immutable journal |
| Claim | New owner/fence + targeted run + CLAIMED queue + journal |
| Capture | Consistent input + sealed manifest + CAPTURED stage, or explicit probe/backoff |
| Reservation | One logical actual attempt + WRITING stage |
| Target | Canonical upsert + sidecar + immutable receipt + B2 version/occurrence/continuation + PROJECTED queue, all atomic |
| Eligible | B2 ELIGIBLE audited CAS transition using current committed input |
| Resolution | B2 RESOLVED audited CAS transition using committed target/receipt proof |
| Completion | Revalidated resolution + DONE journal, followed by separate lease release |

These are **separate transactions**, not one distributed atomic operation. Every
intermediate stage is visible and durable. A crash may leave work incomplete;
it cannot legitimately close debt without the correct receipt and audit chain.

A targeted run always remains PARTIAL and cannot update `last_complete_*`.
A later independently captured full B2 generation may become COMPLETE after all
its coverage and debt proofs pass. Original partial manifests are never rewritten.

## 8. Version/supersession and resolution proof

The B2 family is stable across fingerprint changes. A repaired dependency causes
B2's existing atomic SUPERSEDED(old) + OBSERVED(new) transition, predecessor and
successor pointers, and exact occurrence link in the target transaction. The old
receipt stays immutable. B3's queue follows the resulting current version in that
same transaction and journals its ID; it does not preapprove the new version.

`resolve_claim` uses deterministic UUIDv5 transition keys tied to the recovery
run and action. The standard B2 CAS and proof checks remain, extended to verify
that the targeted run belongs to this queue/family/current owner. A receipt alone
is not resolution: eligible and resolved events must be committed separately.
Before DONE, B3 again checks current resolved version and actual target digest.
SQL guards also reject illegal stage edges, counter jumps and unproven DONE.

## 9. Lease, fencing and concurrency

PID/process ownership is not relevant to this repository capability: B1's durable
domain owner, fence, latest-run and lease are the participating-writer authority.
Domain-first locking prevents concurrent duplicate claims even across connections.
Queue `run_id` is unique. SQL queue guards require matching live domain ownership;
append-only events and deferred audit triggers bind each revision to its history.

An expired claim can be resumed with a **new owner/fence on the same run** after
its due time. Unsealed pre-capture claims are resumable. If another run overtook
that claim, B3 refuses automatic recovery. Old tickets cannot write or resolve.
Live source fingerprint and target sidecar/digest checks protect newer data.

**Legacy writer compatibility remains RESTRICTED**. Neither explicit opt-in nor
these synthetic tests prove exclusion of existing unfenced operational writers.
Shared-writer exclusion/fencing and deployment privileges remain rollout gates.

## 10. Retry, backoff and poison budgets

Defaults: one item/invocation, 20 seconds, three logical write attempts, 16
readiness probes, 128 journal revisions, exponential 30-second base backoff capped
at 3600 seconds. Accepted ranges are finite and strictly integer-validated.
Capture, SQL statement, lock, lease and B2 history limits remain independently
active. A context-local deadline bounds phase admission, each transaction SQL
timeout and pre-commit checks across the entire invocation. Nested invocations
cannot extend it; concurrent invocations cannot change each other's deadline.
Expiry after a committed projection retains PROJECTED and does not fabricate
resolution; a later independently bounded call can reconcile that receipt. No catch/retry loop replays a failed application invocation automatically.

All policy values, including B2 limits/expiry, contribute to an immutable stored
policy digest. Different budgets cannot silently apply to an enrolled row. B3's
max attempts cannot exceed B2's cap. Before reservation it conservatively reserves
B2 observation/supersession/eligible/resolution capacity, refusing a same-version
write that would hit B2's poison boundary even if mapping succeeds.

Readiness probes and failed actual writes have persisted backoff. Probe, attempt,
version or history exhaustion blocks work or raises a visible bounded refusal;
debt/evidence remain. BLOCKED/DONE queue rows have no automatic reset/unblock.
Insufficient remaining stage-journal capacity fails before claim. No purge, cap
increase, record deletion or operational retention decision is included.

## 11. Failure recovery and idempotency

- Before target commit, connection loss rolls back canonical target, sidecar,
  receipt, B2 version and PROJECTED stage together. A separate sanitized failure
  stage records backoff; it cannot conceal a target commit.
- A lost reply after target commit leaves PROJECTED. Resume skips the target
  writer and reconciles the committed receipt before resolution.
- A crash after attempt reservation resumes the same logical reservation; it
  does not charge an ambiguous write twice. A confirmed failed transaction may
  reserve the next bounded attempt on the same sealed manifest.
- Crashes after ELIGIBLE or RESOLVED resume that exact run/version. Deterministic
  transition keys prevent duplicate audit events. A RESOLVED/DONE gap is finished
  without reprojecting or creating a second claim.
- Source/dependency change after sealing, overtaken runs, expired/stale tickets,
  actual target drift, incompatible schema/policy or unproven scope fail closed.
- Fault callbacks are caller-injected synthetic-test hooks, not runtime actions.
  There is no automatic source acquisition or operational recovery entrypoint.

## 12. Regression matrix and actual results

The established CI runners independently create and verify a private cluster's
on-disk system ID/data directory, database/role and Unix-only listener. TCP is
absent, inherited secrets/DSNs are stripped, and Python network/subprocess or
nonfixture database connections are denied during tests. Only their own cluster
is stopped; evidence is retained. The accidental-I/O guard is not a hostile-code
sandbox; hosted CI has no plant credentials.

Local qualification uses existing Python 3.14.3 / PostgreSQL 18.6; supported
Python 3.11/3.12 with hosted PG16 is separately required in exact-head CI.

| Suite | Composition | Final result gate |
| --- | --- | --- |
| Offline Collector | 202 pre-B1 + 15 B1 + 11 B2 + 12 B3 = 240 | Local PASS; zero skips/failures/errors/forbidden I/O |
| Disposable PostgreSQL | 38 B1 + 47 B2 + 48 B3 = 133 | Local PASS; zero failures/errors/skips/forbidden I/O; owned cluster stopped |
| CI infrastructure/security | 23 existing immutable qualifier/I-O guard tests | Local PASS; hosted Python 3.11/3.12 required |

There are **60 new B3 tests**: 12 offline and 48 disposable PostgreSQL.

B3 covers old WO recovery and unchanged timestamps; NULL/backdated input; exact
source and dependency queries; all four dependency kinds; unknown/invalid/deleted
input; soft Asset references; keyset fairness/index use; policy/backoff/probe and
attempt caps; competing claims; lease expiry and stale owners; before-commit
connection loss; after-commit reply loss; restart before capture/after reservation/
after eligible/after resolved; supersession; newer targets and digest drift;
004→005→006 ordering/reapplication; schema/index/trigger drift; disabled defaults;
full-versus-targeted coverage; queue/audit atomicity; unchanged source cursors.

Development failures retained in private `/tmp/nadi-b3-*` logs include the initial
catalog-signature derivation (not acceptance), cleanup of engines after fixture
setup failure, correction of the raw psycopg migration-exception assertion, and
an overly broad test selector counting the Equipment EXISTS subquery as a second
row-lock query. The fixes narrow fixture assertions/cleanup; they do not weaken
candidate evidence checks. The new 006 partial-index catalog is pinned explicitly. A distinct final review
also tightened the cross-transaction deadline and added tests for deadline reset,
non-extension, refusal before SQL and expiry after committed projection.
Final exact-head artifacts/PR results supersede intermediate dirty-worktree runs,
which were labelled against the B2 base and are not claimed as exact-head CI.

## 13. Exact-head CI evidence

The unchanged `nadi-maximo-collector.yml` workflow qualifies open same-repository
PRs targeting main. It selects the current immutable head, uses pinned immutable
CI tooling, then runs full offline + CI safety tests and full disposable PG on
Python 3.11 and 3.12. The final gate rechecks the PR head with a read-only token.
No candidate code receives GitHub credentials. No skipped/designed tests count.

Delivery must include the B3 DRAFT PR URL, actual SHA, workflow run URL and four
JSON artifacts with matching `tested_sha`, counts, zero forbidden I/O and owned
cluster cleanup. A workflow headline or B2's green run cannot establish B3 PASS.
The final PR body and task report supply those read-back values after checks.
[B3 DRAFT PR #97 checks](https://github.com/johnd-creator/reliability-knowledge-starter/pull/97/checks)
are the exact-head evidence entry point; read the selected SHA and artifact
`tested_sha` rather than assuming a previous green run qualifies a newer commit.

## 14. B4 status handoff (design only)

| Durable fact | Safe future interpretation |
| --- | --- |
| B1 latest run/status/start and journal timestamps | Latest attempt; never freshness or full coverage by itself |
| Domain `last_complete_run/at` + B2 proof | Last independently proven full coverage; not source sync time |
| B2 current OPEN/ELIGIBLE/BLOCKED versions | Outstanding governed debt, one current version per family |
| Queue PENDING plus due time/probe reason | Scheduled dependency check, not proof of readiness |
| CAPTURED/WRITING/FAILED/PROJECTED + manifest | Captured-ready/in-flight/retry/reconciliation evidence; unfinished |
| Queue BLOCKED + journal reason | Probe/poison/history/refusal requiring review; never zero debt |
| DONE + B2 resolved event + matching current target receipt | Successful exact-ID recovery only |
| Unenrolled debt, obsolete policy or externally repointed queue | Unscheduled/unreconciled; explicitly unknown/review-required |
| B1 history without B2 lineage / unfenced legacy history | UNKNOWN; never auto-imported or forgiven |
| Source acquisition run/cursor versus projection attempt/coverage | Separate source and projection freshness axes |

Ready-but-unreplayed counts need reviewed current evidence, not an invented
`PENDING=READY` mapping. B4 must distinguish missing enrollment/policy mismatch,
bounded query truncation, expired policy, target drift and live unfinished claims.
Vocabulary is an internal handoff for Astra AUD-11 review, not implementation or
approval of AUD-11. Public Integration Center DTOs/routes, Phase 1 thresholds,
review checkpoints and expiry are unchanged.

## 15. Remaining operational blockers

- Senior review of stacked B1/B2/B3 and integrated B4/B5 qualification; F-03 OPEN.
- Operational grants, protected migration role, schema upgrade/backup and
  source/target writer exclusion are unqualified. Fixture owner is privileged;
  these trigger tests are not proof against an administrative DB owner.
- No operational scheduler, budget/retention approval, rollout or replay permit.
- No automatic enrollment of existing historical debt, blocked-queue reopening,
  changed-policy reset, overtaken-claim reconciliation, source-absence policy or
  sealed-stale-input replacement. Those states retain evidence and need review.
- Production cardinality, long-term fairness/latency, alert and status UX remain
  unqualified; synthetic bounded results do not certify those behaviors at scale.
- Existing QA sessions/data were preserved by non-access, not read/compared.
  localhost:3000, all operational services, original assets/workbook and unrelated
  worktrees remain outside this task. No runtime acceptance is asserted.

## 16. Senior Review recommendation

Review the incremental B2→B3 patch alongside cumulative main→B3. Require the
current exact-head qualification and preserved dependency SHAs. Accept only the
disabled synthetic recovery foundation if those gates PASS. Keep rollout, F-03,
operational Mart replay and B4/B5 acceptance separate. Next authorized handoff is
Senior Review → NADI-AUD-02B-B4; no next task is started automatically.
