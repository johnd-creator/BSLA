# NADI-WO-INTEGRATED-LOCAL-RELEASE-01

Status: source preparation and isolated qualification; no activation authority.

The release contains qualified PR128 (`cbd4a800`) through PR129 (`3479b406`) and
preserves the qualified active hierarchy/access source (`469f21fe`). Direct PR129
selection would regress the active hierarchy capability decoder and navigation.
The active source patch is integrated once; both dependency heads remain unchanged.
No GitHub merge or forced branch update is part of this release.

## Controller admission

The accepted six-file local controller remains the authority. Its historical
hierarchy admission and all prior source, authentication, history, rollback,
listener and dependency guards remain intact. A separately reviewed seventh
module admits one exact candidate/private-recovery tuple. Changed protected leaves
are finite and owner-pinned; all other source leaves, application persistence,
locked dependency versions and bootstrap behavior must match the active baseline.
The one changed Mart reader is SELECT-only; it does not authorize schema changes.
Read-only fixture probes must show equal ledgers, schema and retained human records.

Preparation produces immutable code, metadata, source/admission hashes and the exact
wrapper change. Explicit owner GO is required to install. Installation holds both
existing lifecycle locks and changes only controller metadata/code, never services.
Known caught failures compensate both metadata files; power loss between their
individual atomic replacements requires the documented known-byte owner repair.
No claim of two-file crash atomicity or deletion of unknown metadata is made.

## Read access and authentication

Preserve AUTHOR and the existing Engineering write allowlist. Proposed registered
BSR/IP dashboard/Asset/Maintenance READ and renewal of the existing single-root
hierarchy READ are separate, closed grant records requiring one explicit owner
batch decision and fresh private issuer authentication through factual_reads.
Hierarchy READ never applies to the registered population grant. No portfolio,
FMEA/health/PI, administration, source-write or Engineering-write capability is added.

The second read packet resolves its expected ledger head solely from the committed
first approved receipt. Any intervening/wrong event stops the batch. The helper
only prepares the packet; it never authenticates or issues a grant. The controller
requires both exact events active before selecting the candidate. Private proof
must identify the legitimate engineer with original AUTHOR/write scope; ADMIN
cannot substitute. Expired/revoked reads remain denied by the application, while
restoring baseline transport must remain possible without inventing read authority.

## Recovery and operation

The owner-private release manifest must pin every service/image/controller change,
the original ten-WO/twenty-date packet, the exact detail campaign, fields/tables,
source request ceilings, operating window, expected changes and stop conditions.
Normal source scope/cadence/cursors are preserved. Routine workers have one owner;
no temporary source collector is started. Historical detail repair remains Legacy
only with at most ten exact WOs per atomic transaction, durable pre-commit field
journals, source/Registry guards and no automatic cohort replanning.

Fresh consistent private backups and independent restores precede live actions.
The restored environment must exercise date/detail recovery, idempotence, resumed
metadata replay, field rollback, newer-evidence refusals and every unrelated data
fingerprint. Service rollback uses the currently active baseline, including its
private source seal. Never restore a whole backup over an active owning database
or erase valid new data as a routine rollback.

All canonical CI and independent review apply to the final candidate. The existing
single HTTPS frontend and paired Engineering service switch only through the
approved controller. Actual image/source checks, permitted/denied reads and real
Engineer Beranda→Asset→Maintenance→WO UAT remain distinct from synthetic tests.
Screenshots, source data, exact cohorts and operational aggregates stay private.
Global source coverage remains PARTIAL/PAGE_LIMIT; changedate is not freshness.
WO Group and backlog semantics remain unapproved; operational MTBF/MTTR stays off.

Final ACTIVE status requires all approved services and actual UAT to pass. Until
then report NADI_WO_INTEGRATED_RELEASE_BLOCKED with the exact remaining approval,
authentication, source or recovery gates, without substituting CI for live evidence.
