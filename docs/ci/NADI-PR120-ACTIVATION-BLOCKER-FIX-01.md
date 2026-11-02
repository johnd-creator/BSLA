# NADI-PR120-ACTIVATION-BLOCKER-FIX-01

## Scope and status — 2 November 2026

PR120 remains pinned to `49ff4d1088a96673f85070bcaa1f293b5810f8f4`, stacked
on PR119 `119ba2f1472facedd71433d65b74f3b7d64a6434`. This support change
targets main independently. It does not alter PR120, activate services, authorize
grants, change branch protection, or replace the production CI gate. PR119 remains
the local frontend, Engineering API and Factual API runtime.

A is **BLOCKED_PENDING_FACTUAL_READ_AUTHORIZATION_AND_IMPLEMENTATION**. B adds
development evidence only; GitHub execution and recognition by the mandatory
activation policy are separate gates. C remains blocked. No fresh activation
backup/restore or cutover is claimed.

## A — Engineer authorization audit

The Cockpit proxy calls `factualGateway`, verifies the server-side local session,
then evaluates `factualAccess`. `FACTUAL_SCOPE_GRANT_REQUIRED` originates in
`web/lib/factual-gateway.ts`. The immutable-subject policy in `web/lib/factual-policy.ts`
permits portfolio reads only for the previously approved principal with its current
ADMIN role. AUTHOR alone does not grant Asset Register or `decision-overview`
portfolio access. Exact asset paths and asset-filtered maintenance requests instead
depend on `session.asset_ids`.

The legitimate engineer AUTHOR proof passed the unchanged official controller.
Its existing asset scope is synthetic. Account `asset_ids` also controls Engineering
AUTHOR write scope: adding a real asset there would not be a read-only solution.
The owner selected one source asset for the proposal; an exact retained Registry
lookup resolves it uniquely within BSR/IP. Operational principal, asset identity,
retained counts, receipts and session paths remain private.

The approved private administration boundary is `src/qa/users.py`, backed by
`LocalIdentityProvider`, not a public administration endpoint. Its fresh ADMIN and
actor-scope checks remain applicable. The demo profile freezes its four-account
role/scope contract. Neither mechanism implements a separate Factual-only read
entitlement. Direct SQL edits, demo-profile changes, ADMIN substitution and assigning
the portfolio capability are not approved workarounds.

The private proposal binds a new Factual READ entitlement to the immutable engineer
subject, exact canonical Registry/site/org allowlist, expiry, approver, version and
audit/revocation record. It requires a separately reviewed administration mechanism
and explicit owner approval before any grant. Account roles, Engineering asset
scope and source/SQL privileges remain unchanged.

Minimum read surface: scoped Asset Register entries, exact Asset identity and its
Maintenance/WO evidence. Filtering, counts and pagination must apply scope before
response construction. A small allowlist can use bounded existing exact asset
lookups; a new Factual API endpoint is not inherently required. The existing asset
page tolerates optional context denial. Portfolio-bearing context, integration-status
and decision-overview remain denied. A scoped Beranda summary requires its own safe
scoped read model; the page shell alone does not prove authorized summary access.
FMEA, health, overhaul and PI routes are not implicitly included in the WO permission.

After approved implementation, verify permitted reads return 200 and unrelated
asset/site/org, portfolio, admin and write requests return 403. Recheck entitlement
version/revocation after upstream responses. These real-resource 200 tests are
**not run**, since no grant has been changed.

## B — Separate stacked development qualification

The existing `nadi-maximo-collector.yml`, selector, guarded runners and infrastructure
tests are byte-identical to main `f1fc4e8b395691a17fe6d986bf14c772d37c1f2c`.
The production selector still requires an open same-repository PR targeting main.
Its failed PR120 main-only selection remains a failure.

The new `nadi-maximo-stacked-development.yml` uses a closed reviewed profile pinning
PR120 and PR119 to full SHAs. The tooling PR must itself target main under the
unchanged selector. Fresh metadata verifies same repository, open/unmerged state,
current heads and exact parent ref/SHA. Source checkout and ancestry are checked
before and after tests. Changes to six pinned existing qualification files fail
closed. There are no arbitrary dispatch refs.

Hosted ephemeral Python 3.11/3.12 jobs run unchanged guarded runners for the complete
Collector suite (projection and WO lineage included), shared source contracts and
all six private-file recovery rehearsals. Zero skips/errors/failures/blocked I/O
are required. Existing and new negative CI tests also run. Candidate jobs have no
metadata token, plant secrets, deployment environment, persisted Git credentials or
write permissions. Read-only metadata tokens occur only in selection and final
recheck jobs. Uploaded receipts contain synthetic qualification metadata only.
The guards prevent accidental external I/O, not hostile code in a privileged
environment; no such environment is provided here.

The distinct `Maximo stacked development evidence gate` requires successful
selection and every matrix job, then rechecks current candidate/dependency/tooling
metadata and profile digest on a fresh runner without candidate execution. It never
asserts that the production `Maximo qualification gate` passed for PR120.

Local preliminary evidence on exact PR120 SHA: Collector 206/206, contracts 14/14,
rehearsals 6/6, zero skips/errors/failures/blocked I/O; nine new infrastructure
negative tests PASS. Local Python 3.14 is not the supported matrix. Independent
source review found no actionable blocker; immutable support-head binding and the
actual GitHub 3.11/3.12 run are recorded at delivery. No actionlint PASS is claimed.

A passing development run does not automatically satisfy the mandatory activation
gate. If approved controller/policy cannot recognize equivalent evidence,
qualification remains **BLOCKED_PENDING_POLICY_RECOGNITION**. No failed check is
renamed, branch protection changed, or production policy relaxed.

## C — Conditional activation remains stopped

The existing conditional service plan and rollback to PR119 bound any future
cutover. Require the approved read entitlement, recognized exact-head qualification,
independent review, fresh legitimate session, controller/service ownership, fresh
private backup and independent isolated restore, DB identity/ledger/aggregates and
all-container preservation checks. Only then change the approved Factual image/
revision and paired NADI services through approved mechanisms. Verify exact running
SHAs, contracts and real authorized WO UAT; rollback on mandatory validation failure.
This support PR performs no service/data/grant change. Historical PR119 recovery
evidence is not a fresh PR120 activation PASS.
