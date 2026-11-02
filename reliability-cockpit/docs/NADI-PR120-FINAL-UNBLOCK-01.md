# NADI-PR120-FINAL-UNBLOCK-01 — revised integrated package

## Scope and acceptance — 2 November 2026

This extends PR120 baseline `49ff4d1088a96673f85070bcaa1f293b5810f8f4`.
The final source HEAD necessarily advances; its immutable review and exact-head CI
are recorded in the PR handoff. PR120 remains stacked on PR119, without retargeting
to evade its production selector. PR121 baseline qualification tooling is
`345a4a3f4a7a72d309c0f2ee2a6eea20bdecabc9`.

Implementation and synthetic qualification are separate from owner approval,
installation, grant issuance, activation and real Engineer/PO UAT. The requested
`PR120_ENGINEER_FACTUAL_ACCESS_AND_LOCAL_UAT_READY` may be reported only after all
those gates PASS. PR119 remains active while grant/policy approval is outstanding.
No automatic merge, migration, source acquisition, retained backfill or PdM Log Book.

## A — Independent Factual READ entitlement

Capabilities are `FACTUAL_DASHBOARD_READ`, `FACTUAL_ASSET_READ` and
`FACTUAL_MAINTENANCE_READ`. They bind an immutable local authenticated subject to
an exact canonical BSR/IP Registry allowlist or explicit `REGISTERED_BSR_IP` scope.
The latter permits every current registered BSR/IP asset, without asset enumeration
or a wildcard canonical identity. They never enter `session.asset_ids`,
Engineering Principal roles/scope, SQL grants or source credentials. No public
privileged endpoint is added. Existing ADMIN portfolio behavior and legacy granted
asset reads retain their original authorization path; a bad new ledger does not
remove those rights or grant a fallback portfolio capability.

The application-owned policy is canonical NDJSON at the stable private controller
state path `state/factual-read-120/grants.ndjson`. It is outside source releases,
database backups and worktrees. Each ISSUE/REVOKE records version, prior hash,
grant ID, beneficiary, assets/capabilities, UTC not-before/absolute expiry,
authenticated approving/issuing actor, owner approval reference and operator
reference. At most 24 hours per issue, 20 simultaneously exact-allowlisted assets
per subject or the separately approved registered-population scope, 200 issues/400
events; bounded encoding reserves revocation capacity. The optional closed enum
`scope_kind` is hash-bound; registered scope requires an empty `assets` list and
cannot be substituted during revoke or controller activation approval.
Unknown fields, duplicate/noncanonical keys, invalid dates, wildcard/foreign scope,
non-READ capabilities, corrupt chains and reissued IDs are rejected.

Administration reuses the private CLI pattern in `src/qa/factual_reads.py` and the
existing `LocalIdentityProvider`. Apply requires a fresh authenticated approved
portfolio issuer with current ADMIN, not an arbitrary ADMIN username. This local
CLI pins the official loopback application directory host/port/database/role and
checks actual database/current user; a restored copy is not an identity authority.
It verifies target AUTHOR identity and exact Registry membership, or the existing
owning Registry service for an explicitly approved registered-population issue. The actor's
Engineering asset grants are not expanded or reused as Factual delegation scope.

An exact owner-private approval file and its SHA256 bind operation, grant ID,
subject, exact assets/capabilities, absolute validity, issuer, approval/operator
references and expected ledger head. Real issuance needs separate explicit owner
approval. Plan does not authenticate, connect to a DB, query Registry or create a
ledger. Apply uses the existing masked TTY password entry and explicit application
admin DSN; no password/reset/session proof is accepted on argv or through the web.
The existing account CLI, demo profile and password policy remain unchanged.

Updates use one stable flock, CAS, canonical validation, same-directory atomic
replacement and file/directory fsync. A stale/repeated approval fails closed without
extending validity. An error after replacement reports
`APPLY_STATE_REQUIRES_RECONCILIATION` / grant may be live, never a false DENIED/no-change
claim. `--status-only` reads back the current head/state without replay; it is not
durability reconciliation. Stop activation until read-back and storage durability
are reconciled, then obtain any new operation approval against the actual head.

The OS custodian is trusted. A hash chain detects corruption but cannot detect
restoration of a valid older prefix. Never restore, replace or truncate entitlement
history from source/DB recovery. Revoke in place; preserve read/security audit.
Server release checks append private bounded security receipts in `reads.ndjson`
(subject/version/head, time and request hash; no cookie/proof/raw URL/WO body).
File and parent are fsynced; unavailable/full/unsafe audit closes new reads. A
receipt records an authorized release check, not proof the browser received data.
Account, grant, session and source revocation remain distinct operations.

## B/C — Scoped Beranda, Assets and WO evidence

The Beranda page separates page access from dataset authorization. The existing
approved portfolio principal still renders `ExecutiveOverview`. Other authenticated
users render `ScopedExecutiveOverview`: permitted counts and exact Asset links, or
an explicit restricted/unavailable state. The server-only scoped-overview read model
is composed from exact existing Asset and asset-filtered Maintenance endpoints
for an exact allowlist. A registered-population grant uses the dedicated bounded
`registered-maintenance-overview` read model: three aggregate/ranking SQL queries
over only Registry, Asset and WO, scoped before counts and serialization. The
retained totals cover all registered BSR/IP assets; the table is explicitly the
top ten by retained WO count. The complete Register retains native pagination.
No portfolio `decision-overview`, context or integration totals are fetched.

Counts describe authorized retained records, not complete operational history.
MTBF/MTTR, equipment health and cross-inspection trends remain NOT_ELIGIBLE; there
are no invented KPI values or synthetic production metrics. Navigation to Aset,
PdM, Tindak Lanjut and Laporan remains present under the original rules.

Register authorization precedes every exact lookup, filter, total, sort and page.
The registered scope uses the owning API's Registry+BSR/IP SQL joins before
filter/count/page, without a per-asset fan-out or client-side scope filtering.
Exact Asset/BSR/IP identity,
safe typed scalar fields and clock structure are validated before serialization;
foreign parent references are withheld. Zoned clocks sort by instant with stable
identity ties; naive/unknown clock semantics remain explicit. Scope/paging proof,
unique row identity, scalar source/classification fields and the 2 MiB response
bound remain enforced. Existing Maintenance/WO source detail DTOs are reused.

The grant does not include FMEA, health, timeline, PI, context, integration or any
portfolio route. Those requests remain denied. Exact WO evidence reads retain
original type/status/null/zero/clocks. Existing filter/deep-link/return navigation
is preserved. The server reloads the canonical ledger and verifies current session,
subject, permission head/version/expiry before releasing upstream data, including
after private audit. Atomic revoke/expiry during upstream work discards the body.

## D — Local CI recognition, preserving production policy

`deploy/development/stacked_activation_policy.py` is a separate read-only preflight;
it never installs, restarts, grants, executes candidate code or rewrites check status.
Ten immutable qualification code/policy hashes are pinned to the independently
reviewed PR121 baseline. A changed exact target profile is independently reviewed.
The verifier requires current same-repository open/unmerged PR120/119/121 heads,
the exact stack/base, main-target tooling PR, unchanged trusted runner/workflow
bytes, successful complete hosted Python3.11/3.12 jobs and fresh final metadata gate.

It verifies two bounded ZIP digests and all six receipts: Collector206 (including
projection and WO lineage), contracts14 and recovery6 on each Python version, exact
tested SHA, workflow merge identity, zero skips/errors/failures/expected failures/
blocked I/O and owned rehearsal cleanup. Backend/frontend exact-head CI must also
pass. Metadata is rechecked after download. Token reads use fixed GitHub GETs only;
artifact redirects discard the metadata token. No credentials enter services or
receipts. PR121 tooling remains nonprivileged on hosted disposable runners.

Recognition requires a separately approved private LOCAL_DEVELOPMENT_ONLY policy
file/digest binding exact request/run IDs, current source/tooling/dependency SHAs,
policy+trust bundle digest, independent exact-head security-review digest, immutable
approver/reference and expiry. Ambiguous approval JSON is rejected. Recognition
returns no grant or deployment authority; other activation gates remain mandatory.
Without this specific approval it reports BLOCKED.

The original main-only workflow and selector remain byte-identical. Its original
PR120 failure is not renamed PASS. Historical run41437088412 was reverified against
exact49ff through the new verifier, including ZIP digests. After PR120 advances,
PR121's closed profile must pin the new head and run afresh; old evidence cannot
qualify changed source. No branch protection or production rule is weakened.

## E — Security/regression and F01–F24 preservation

New synthetic tests cover private approval/issuer authority, wrong directory,
scope/type/paging faults, corruption, expiry/revocation/race, uncertain commit,
audit, negative portfolio/domain/write access and unchanged Engineering scope.
Actual React components exercise Login→Beranda→Register→Asset→Maintenance→WO→PdM
on an intercepted synthetic origin; light/dark390/768/1440, automated accessibility
and private screenshots are separate from real UAT. No operational server/listener
or real login is used by these tests.

F01–F17, F19 and F23 retain their source/contract ownership and existing complete
candidate checks. F18 gains only the separately gated READ boundary; existing
session/CSRF/Origin/RBAC/Engineering writer and account bytes remain pinned.
F20/21 retain every existing page/tab and original domain permissions. F22 adds a
scope-limited home reader while preserving the admin dashboard. F24 adds an explicit
task-mode controller hook, with account/demo/local_fixture parity bytes unchanged.
Historical hash assertions remain active; exact authorized new exceptions are
listed separately and reviewed rather than dropping the guards.

## F — Conditional local activation and recovery

The source controller adds `--require-factual-read` only for local-preflight/select.
This task must use it. It verifies the exact private active issue approval, full
ledger chain, subject/scope/caps/expiry before stopping and again before pair start,
then passes only the stable policy path to the frontend. Generic PdM launches do
not require a temporary Factual grant. PR119 rollback leaves all entitlement and
revocation state intact. An expired grant must not disable ordinary PdM development.

Installed controller amendments and its manifest are preserved until an exact reviewed
installation plan is approved. Do not replace accepted PR111/source-reading changes
with an older generic controller. Installation, if approved, applies only the reviewed
task flag/helper delta and verifies all previous ownership/seal/recovery contracts.

Before cutover: explicit exact grant issuance and local-policy recognition approval,
exact-head CI and independent security review, fresh Engineer session, controller/
service/source ownership, fresh private backups, independent isolated restore,
DB/ledger/count/source seals and preservation of all35 service roles. None can be
borrowed from a historical PR119 acceptance. Failure stops the attempt.

The registered-population extension changes Factual API/repository source. The
previous49ff Factual image cannot serve its new contract and must not be reused
or relabeled. Build and seal a new Factual image at the final reviewed PR120 head,
with the same exact frontend/Engineering pair through the official controller;
report each service's actual source SHA separately. No extra permanent Factual API,
ports, database or Compose project. Roll back services/source to pinned PR119 on a
mandatory post-cutover failure; never restore retained stores or old grant state.

Real Engineer Beranda→Asset→Maintenance→WO UAT and private factual screenshots are
NOT RUN while owner approval remains outstanding. Synthetic screenshots are never
represented as real plant acceptance. Runtime/grant/backup/restore receipts and the
precise remaining owner decisions are recorded privately at handoff.

## Owner scope amendment — 2 November 2026

The owner explicitly approved Dashboard, Asset and Maintenance READ across the
registered population, superseding the initial one-asset proposal. This authorizes
the three READ capabilities for all Registry BSR/IP assets, at the previously
proposed maximum24-hour validity, without ADMIN or broader Engineering write
scope. Grant issuance, CI-policy/controller approval, fresh session, recovery,
service-level image plan and actual UAT remain separately evidenced gates.
Other sites/orgs, unregistered technical assets, general portfolio/domain routes
and all writes remain restricted. Existing ADMIN dashboard source is unchanged.
