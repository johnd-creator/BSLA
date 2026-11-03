# NADI-AUD-04A — Maximo Collector CI qualification

Status: CI infrastructure candidate; separate DRAFT PR. No merge or operational
acceptance. Baseline main: `919428a906c5ef0c7fd02fe0d64e33b537c39570`.
PR #91 was independently verified OPEN/DRAFT/unmerged at
`f16ff508f07efd56535553f49e6f0007273a44e0` on 16 October 2026.

## Initial gap and bounded scope

The existing [Engineering candidate workflow](../../.github/workflows/nadi-engineering-candidate.yml)
selects Cockpit/contracts/development-tool paths and selected backend suites.
Collector-only changes do not invoke that workflow. This implements the Maximo
slice of Astra F-06 / AUD-04, without editing the independent audit or PR #91.
It does not fix collector application logic or qualify operational deployment.

The new [workflow](../../.github/workflows/nadi-maximo-collector.yml) discovers
the entire `maximo-collector/tests/test*.py` suite, including generic sync,
asset baseline/registry, WO recency/recovery, OSLC authentication/read-only/scope
guards, local Mart projection and other test modules. Once selected from PR #91,
discovery also includes AUD-01 cursor recovery. Its changes are not copied into
this CI-only branch.

## Trigger and runtime contract

Pull requests and pushes to main match:

- `maximo-collector/**` (source, tests, dependencies and component documentation).
- `reliability-data-contracts/**` (shared input contracts).
- `.github/scripts/maximo_ci/**` and the dedicated workflow itself.
- `docs/ci/**` (qualification instructions and evidence).

Unrelated README/design-only changes and PI/CEMS-only changes are excluded.
Examples are tested against the actual YAML path lists. There is no claim that
this workflow covers the excluded components.

Two fresh GitHub-hosted Ubuntu lanes install the collector from its selected
checkout using pip, independently of any developer virtual environment:
Python **3.11** is the `pyproject.toml` minimum; **3.12** matches its Dockerfile.
Each lane has a 15-minute timeout, with separate five-minute metadata/gate jobs.
The original offline lanes launch no service or database. The additive PostgreSQL
recovery lanes below use a separate ephemeral synthetic service; no operational
stack or migration is launched.
Dependencies retain the project's existing bounded version ranges; PyYAML
6.0.3 is pinned for infrastructure tests. Dependency locking remains separate
work; Python patch versions and `ubuntu-latest` can advance. Exact Python
versions are recorded and installed-package versions remain visible in pip logs.

## Read-only source selection and trust boundary

[qualify.py](../../.github/scripts/maximo_ci/qualify.py) accepts an explicit PR
number and full lowercase 40-character SHA. Before checkout it verifies the
current GitHub PR metadata: exact number, OPEN/unmerged, both repositories equal
`johnd-creator/reliability-knowledge-starter`, base `main`, and current head equal
the requested SHA. Missing/unreadable PR metadata, stale heads, forks, wrong
repositories, abbreviated SHAs, branch names and unsupported events/refs fail.
Normal PR events select the **PR head**, not the synthetic merge commit. Main
pushes select their immutable event SHA.

Tools are checked out at `github.workflow_sha`, separately from the selected
source. The source checkout verifies HEAD, origin and clean tracked files before
and after tests. Checkout credentials are not persisted. The metadata API uses
the ephemeral GitHub token only in dedicated select/final-gate runners; the
collector job never receives that token as an environment variable. All jobs
have `contents: read`; only metadata jobs additionally have
`pull-requests: read`. There are no repository/plant secrets, environments,
`pull_request_target`, write/deployment permissions or self-hosted runners.

The final gate runs after both matrix lanes, explicitly refuses failed/skipped/
cancelled prerequisites, and re-fetches current PR HEAD in a fresh runner without
executing candidate code. A head that moved during testing fails qualification.
Later head changes invalidate the evidence; senior review must compare the
current PR head again before any separately authorized merge.

## Offline runner and failure reporting

[run_offline.py](../../.github/scripts/maximo_ci/run_offline.py) is a CI-owned
adaptation of PR #91's `maximo-collector/tests/run_offline.py`; PR #91 is unchanged.
Before source imports/discovery it removes source/database/credential variables,
suppresses private dotenv loading and installs Python audit/driver guards.
Connections, DNS resolution, datagram sends and subprocess execution are denied;
SQLAlchemy/psycopg external connections and file SQLite are denied. Only fresh
in-memory SQLite fixtures are allowed. Denial records contain categories only,
not addresses, DSNs or secrets. Caught I/O attempts still fail the suite.

This is defense against accidental I/O, **not a security sandbox for hostile
Python/native code**. Source and dependency review remains required. GitHub
runner network access is needed for actions/package bootstrap and metadata, but
no plant credentials, operational DSNs, private dotenv files or plant network
access are provisioned. This task does not certify malicious-code containment.

Discovery must be nonempty, all discovered cases must execute, and failures,
errors, skips, expected failures or blocked I/O fail qualification. There is no
hardcoded expected test count. Logs list each executed test; JSON and the GitHub
job summary record Python, immutable source/workflow SHAs, exact command, run URL,
discovered/executed counts, failures/errors/skips/expected failures, blocked-I/O
count/categories and PASS/FAIL. A green lane is insufficient without the final
qualification gate. If setup fails before tests, that job fails and no test PASS
is claimed. No failure is masked with `continue-on-error` or shell fallthrough.

## Commands and validation evidence

CI executes:

```bash
python -m pip install ./source/maximo-collector PyYAML==6.0.3
python -m unittest discover -s ci-tools/.github/scripts/maximo_ci/tests -v
python ci-tools/.github/scripts/maximo_ci/run_offline.py \
  --root source/maximo-collector --sha "$TESTED_SHA" \
  --report "$RUNNER_TEMP/maximo-offline-$PYTHON_VERSION.json"
```

Local qualification on 16 October 2026 used the existing component Python
3.14.3 only as preliminary evidence, not supported-runtime CI qualification:

| Check | Observed result |
|---|---|
| Infrastructure regression | 21 tests PASS, including synthetic negative subcases |
| Main collector discovery | 181 discovered/executed; 0 failures/errors/skips/blocked I/O |
| PR #91 runner compatibility, local only | 202 discovered/executed at `f16ff508f07efd56535553f49e6f0007273a44e0`; 0 failures/errors/skips/blocked I/O |
| YAML/workflow syntax | PyYAML parse and actionlint 1.7.7 PASS |
| Scope | No collector production source, existing workflow, runtime, database or independent audit edits |

The 21-case difference is PR #91's added recovery tests. It is not a minimum
count. Tests exercise valid/stale/missing/wrong PR metadata, wrong repositories,
unsupported refs, head movement, dirty/wrong checkout, trigger examples,
read-only job separation, intentional failure/import error, silent skip/expected
failure/empty discovery, blocked network/database/subprocess attempts, allowed
in-memory fixtures and dotenv/environment suppression. No live socket/database
connection is needed for the negative tests; a deterministic audit-event case
also covers connect denial where the host already forbids creating sockets.

Initial local failures are retained in `/tmp/nadi-aud04a-*.log`: system Python
did not have collector dependencies, so subsequent local runs used the existing
component environment. An overbroad experimental socket-creation guard flagged
a library capability probe even though all 181 tests passed; it was corrected
to deny connection/DNS/send operations. Both full suites and negative regressions
were rerun successfully. CI installs dependencies independently.

GitHub-hosted qualification actually executed in
[run 38839782878](https://github.com/johnd-creator/reliability-knowledge-starter/actions/runs/38839782878)
for CI-only source `4d73565e81f2e3d845d489f4194bce73e3fcf48e`, with immutable
workflow revision `4091bf6d5045f1cc51b0fbebf4f4f66009bc4d38` (the workflow's PR
merge revision, distinct from the selected PR head). Python **3.11.17** and
**3.12.15** each executed 21 infrastructure tests and 181 collector tests;
failures/errors/skips/expected failures/blocked I/O were all zero. Both metadata
checks, both matrix lanes, tracked-source integrity checks and final gate PASS.
The source's collector subtree exactly equals baseline main; the runner also
proved locally compatible with PR #91's additional tests. Detailed commands,
Python and source/workflow identities are in each job's JSON summary/log.

[CI-only DRAFT PR #92](https://github.com/johnd-creator/reliability-knowledge-starter/pull/92)
remains separate from [PR #91](https://github.com/johnd-creator/reliability-knowledge-starter/pull/91).
This evidence commit adds the observed run to documentation; subsequent exact-head
results are available in PR #92's checks. A run on this branch qualifies its
selected SHA, **not PR #91**. PR #91 exact-head GitHub qualification is PENDING.

## Default-branch prerequisite and controlled integration

The new workflow is absent from verified main. `workflow_dispatch` therefore
requires the separately reviewed CI-only merge first. The selector additionally
refuses dispatch from any ref other than `refs/heads/main`. Do not modify PR #91
or manufacture another branch run to represent its missing exact-head gate.

After separate approval and integration, the authorized operator can use:

```bash
gh workflow run nadi-maximo-collector.yml --ref main \
  -f pr_number=91 \
  -f expected_sha=f16ff508f07efd56535553f49e6f0007273a44e0
```

Re-read PR #91 metadata before dispatch; a changed head needs renewed review.
Dispatch evidence belongs to the workflow run's immutable `tested_sha`, not
automatically to PR #91's Checks tab. Inspect both Python lanes, final gate and
summaries/run URL explicitly.

1. **A — Current scope:** senior review and qualify this separate DRAFT CI PR.
2. **B — Separate approval:** merge the CI-only PR into main.
3. **C — Subsequent authorized action:** exact-head PR #91 dispatch from main.
4. **D — Senior review:** inspect immutable results and unchanged PR #91 diff.
5. **E — Separate decision:** consider conditional PR #91 merge.
6. **F — Separate operational plan:** replay load/cursor compatibility/rollout.

This task executes A only. No merge, rollout, branch-protection/ruleset change
(AUD-08), cursor replay or runtime acceptance follows automatically. Two Python
lanes plus negative subprocess fixtures consume hosted CI minutes; path filters
limit cost. Concurrency queues rather than cancels existing qualification runs.
There is no cross-version cache dependency or operational service cost.

## Remaining AUD-04 gaps

- PI and CEMS collector-aware full-suite CI remain outside this Maximo slice.
- Engineering repository PostgreSQL tests require their own explicit
  `NADI_ENGINEERING_TEST_DSN` lane/selection; existing candidate CI does run other
  PostgreSQL suites using `NADI_APPLICATION_TEST_DSN`. This is not an absence of
  all database testing.
- Small real Next/API contract coverage and the broader affected-component
  matrix/check contract remain follow-up work alongside existing synthetic UI
  tests. Operational PostgreSQL behavior is not proven by in-memory SQLite.
- Dependency reproducibility and future required-check/ruleset adoption remain
  separate decisions; existing requirements and safety guards are preserved.

Official localhost:3000, all QA sessions/data/schema, collectors, Mart, Phase-1
policy, worktrees, backups, original PNGs and workbook are untouched. No
operational action, database access or source synchronization was performed.

## Additive WO rollback PostgreSQL gate — 3 November 2026

NADI-WO-ACTUAL-DATE-ROLLBACK-FIX-01 adds `postgres` lanes for Python 3.11/3.12.
They use the same selected exact source HEAD and immutable workflow tooling,
`postgres:16.4-alpine` pinned by digest, a fresh `maximo_collector` test database
and non-superuser `nadi_ci` owner. Synthetic passwords are disposable CI fixtures,
never Maximo/plant credentials. The guarded runner scrubs source environment,
disables dotenv, denies HTTP/subprocess and other database targets, and fails
on missing tests, skipped tests, expected failures or unexpected I/O. This is
accidental-I/O defense, not a hostile-code sandbox; use only disposable runners.

The final gate requires success of `select`, `collector` and `postgres`, followed
by the existing fresh PR-HEAD recheck. Main-target selection and production policy
are preserved. Offline memory-only guards and the exact six file rehearsals are
unchanged. The new PostgreSQL suite covers real row locks, atomic field rollback,
worker metadata replay, NULL and field-version protection, commit interruptions,
verified duplicate rollback and partial cohort conflicts. Real-cohort full-backup
restore is additionally recorded privately; CI contains synthetic evidence only.
