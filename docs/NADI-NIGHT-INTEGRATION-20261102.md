# NADI source integration — 2 November 2026

Source implementation through PR122 is MERGED. Local deployment remains original
PR119; PR120 activation is BLOCKED. Full hierarchy population, hierarchy-role
semantics and Product Owner/live acceptance remain PARTIAL/PENDING. These states
must not be collapsed into one PASS.

## Source and CI evidence

Dependency-ordered ordinary merges were owner-authorized. No provider APPROVE
review was submitted, branch/protection policy changed, force push used, or branch
deleted. Independent security review covered PR114, the entire remaining sprint
stack including intermediate variants, and the hierarchy source. Final hierarchy
directive-order repair was separately verified at its exact head.

| PR | Qualified head | Main merge | Backend/frontend CI |
|---|---|---|---|
| [#114](https://github.com/johnd-creator/reliability-knowledge-starter/pull/114) | `aa065af9cef01d8ee3358bcca8fc628ba311ca3a` | `f498d5bdd2d70f04126b1f826e24548a673a76e9` | [PASS](https://github.com/johnd-creator/reliability-knowledge-starter/actions/runs/41254254441) |
| [#115](https://github.com/johnd-creator/reliability-knowledge-starter/pull/115) | `05a7b9502a0ba638a706fb0853793a9a58232c39` | `6d8a3ac9ee3622d1e9761874d0604f339d320d0f` | [PASS](https://github.com/johnd-creator/reliability-knowledge-starter/actions/runs/41465642258) |
| [#116](https://github.com/johnd-creator/reliability-knowledge-starter/pull/116) | `f847f14e22f84e5c8a555398993fddcd6c16dc9d` | `e914c3b9022842b39a24ebd293e5ccdf24c92f95` | [PASS](https://github.com/johnd-creator/reliability-knowledge-starter/actions/runs/41470916568) |
| [#117](https://github.com/johnd-creator/reliability-knowledge-starter/pull/117) | `6dc89217bad4ea3e17490eb8cb36bc637d5099a1` | `e1d915c4b292ea56f9432a1fdda7de8f86a148ed` | [PASS](https://github.com/johnd-creator/reliability-knowledge-starter/actions/runs/41472750879) |
| [#118](https://github.com/johnd-creator/reliability-knowledge-starter/pull/118) | `fe28bd6c7ea7df0855756ed24589b1fe5beba1f4` | `1b25dce89b3cfcd3d5e2fb544aec5a2e37408f19` | [PASS](https://github.com/johnd-creator/reliability-knowledge-starter/actions/runs/41474648791) |
| [#119](https://github.com/johnd-creator/reliability-knowledge-starter/pull/119) | `f7b43fcbbc2947962676f9e6f2014dc681a9d52d` | `2e7be05432af003c6da5afbd8f9fcebeca62900e` | [PASS](https://github.com/johnd-creator/reliability-knowledge-starter/actions/runs/41474789772) |
| [#120](https://github.com/johnd-creator/reliability-knowledge-starter/pull/120) | `a08ab633e7c5ed9bc8729887d9b898beec31de78` | `09842dde53ee1907aa3157f824d322ec153f7295` | [PASS](https://github.com/johnd-creator/reliability-knowledge-starter/actions/runs/41480874167) |
| [#122](https://github.com/johnd-creator/reliability-knowledge-starter/pull/122) | `6d9efc2f3e364a14f6faea1520c083dcf65b9197` | `00aaeda1d3b89141fd20c870277addc03c29a231` | [PASS](https://github.com/johnd-creator/reliability-knowledge-starter/actions/runs/41480347826) |

Every resulting merge tree was compared to its qualified candidate. PR120's final
source tree equals reviewed04548631; later history integrations do not change it.
After its actual parents merged, the unchanged main-policy Maximo workflow ran on
the final PR120 head: [canonical qualification41480873314](https://github.com/johnd-creator/reliability-knowledge-starter/actions/runs/41480873314).
Exact checkout, Python3.11/3.12 Collector/source-contract/lineage suites and final
fresh PR-head recheck all PASS. Production/main selectors and tools are unchanged;
no stacked equivalence is used for this final gate. PR121's task-pinned development
profile is held Draft because its original candidate/parent assumptions are now
obsolete; it is not merged as a generic qualification policy.

Fresh CI exposed a synthetic two-tab identity race in PR118/119. The already
reviewed per-tab fixture from PR120 was backported with all assertions retained
and a deliberate reviewer-refresh check. New exact-head CI passed. PR122's first
build failed because a type-only import preceded the client directive. Restoring
the directive order and its exact hash pin preserves emitted API JavaScript; full
local build and new exact-head CI passed. Failed runs remain historical evidence.

## Initial source hierarchy verification

The [retained hierarchy candidate](../reliability-cockpit/docs/NADI-ASSET-HIERARCHY-01.md)
is useful source implementation, not a full source-population refresh. The owner
also required verification against Maximo rather than an Excel import.

A bounded authorized live probe used the existing credential-owning Maximo worker
and its existing client/authentication mechanism. Business access was GET-only on
`/oslc/os/mxapiasset` relative to the configured base, with BSR/IP and the current
validated `eq11=CS01` scope. The prescribed authentication-only `/j_security_check`
handshake kept cookies in memory. A verified idle window avoided the routine WO
worker. Per-query page and total-request budgets, a stricter request floor and
deadline, and the existing 1 MiB cap remained enforced. No new credentials,
permissions, acquisition worker, source write or local store write was introduced.

The owner-selected registered Asset and direct-child filter returned HTTP200.
Observed parent/ancestor/unit/child-flag values match retained evidence. Raw rows,
identities, cardinalities and screenshots remain private. No source rows were
imported and asset acquisition runs were unchanged. This proves the bounded read
path and relationship match in the pilot; it does not prove full Maximo coverage,
cross-unit completeness, new Registry membership or a current full ingestion.

`mainthierchy` was observed as a boolean and `hierarchypath` as a string; their
names do not establish system/equipment/component roles or a canonical path.
Roles remain UNKNOWN. The new [sanitized knowledge receipt](../maximo-knowledge/discovery/nadi-hierarchy-read-verification-20261102.json)
contains field types and method/scope evidence without raw examples. Excel, ID
prefixes and missing retained edges are not semantic substitutes.

### Subsequent scoped source reconciliation and normal ingestion — 3 November WIB

The owner-authorized follow-up went beyond the pilot. All existing registered CS01
roots whose retained child flag was true but had no retained direct children were
queried through the same credential-owning worker. Exact parent-IN predicates,
BSR/IP/CS01 guards and bounded server pagination were verified. Capped parent
groups were split into smaller groups and read again until the selected gap-root
set was reconciled without remaining capped groups or unread roots. This is the
named approved subset, not full Maximo, other units or global hierarchy coverage.

Previously unretained child IDs were fetched with the full existing allowlisted
asset projection. The packet remained in memory between the source client and
normal writer. Fresh private pg_dump and independent network-none PostgreSQL
restore passed. That exact packet then passed the existing SyncService/mapper/
CollectorStore and MartWriter path on the isolated restored store before it was
admitted to the existing owner database. Only new technical Equipment/AssetMaster
rows and their normal initial status observations were appended. The acquisition
run is explicitly PARTIAL and cursor-free; no global source or projection cursor
was advanced by this operation. No Registry membership or hierarchy role was
created. The source children flags were retained without assigning semantic roles.

Private before/after fingerprints prove preservation of old Equipment/AssetMaster,
old status history, Registry, mappings, selections, schema ledger and asset cursors.
The original WO worker and projector continued their own schedules; no service was
restarted. The temporary restore was removed and all existing containers rechecked.
Raw identities, counts, retained evidence and recovery bytes remain private. No
Excel import, destructive recollect, source permission expansion, schema change,
WO backfill or canonical classification correction occurred. Full-population and
role acceptance remain PARTIAL/UNKNOWN beyond this bounded subset.

## Runtime, recovery and acceptance

Official read-only status reports frontend and Engineering at
`119ba2f1472facedd71433d65b74f3b7d64a6434`, stale:false. Factual image remains
`sha256:2b4d766c49666bd236ec45325c9a498c1dc86ffe3857bdf95455a42f34fcf766`
with the same119ba2f revision. All35 service roles and all34 unrelated exact
container identities/images/start/state/restart/ports remain preserved. No service
transition, controller installation, account/grant write, migration, retained-WO
backfill or destructive source recollection was performed. The scoped normal
asset append above is a separate authorized data operation. The existing WO worker continues
its own bounded schedule; source update timestamps alone are not sync freshness.

The unchanged official controller stops PR120 at
`FRONTEND_BACKEND_CONTRACT_DIFFERENCE: reliability-cockpit/src`. Earlier approval
pins a different source/image and cannot authorize a new controller/source
admission or combined hierarchy deployment. The approved registered READ intent
remains separate from actual issuer-authenticated issuance; no grant was issued
by this work. Engineer technical-hierarchy scope is also not silently added.

Before any future cutover, prepare a separately reviewed exact controller/service
plan, obtain the required service-owner approval and refresh all mandatory gates:
issuer/Engineer session, source/ownership/versions, DB/ledger/aggregates, backup,
independent isolated restore, preservation and rollback. Fresh activation backup/restore and
live PR120/122 UAT were not run after this STOP. The later asset-ingestion
backup/isolated restore qualifies only that append and is not reused as a cutover gate. Original PR119 source/image and
sealed recovery evidence remain retained; this is not a fresh activation-ready
claim. M02/Q01–Q10, operational KPI eligibility and PO decisions are unchanged.
Logbook PdM remains HOLD.


### Unit-filter limit after gap-set reconciliation

Private set comparison confirms that every remaining registered gap belongs to
the source-queried and exhausted initial gap set: no unread root or capped group
remains for that subset. The `eq11=CS01` predicate filters each returned child row,
not merely the selected parent's membership. A legitimate child with a different
or absent unit value can therefore be excluded by this approved query. Whether
unit data, relationship semantics or source visibility explains the remaining
discrepancy is UNKNOWN; no cross-unit request or permission expansion was performed.
This is a source discrepancy requiring owner verification, not proof of leaf
status or complete hierarchy. Evidence identities and cardinalities remain private.


## NADI-HIERARCHY-CHILD-UNIT-READ-20261103 — scoped read exception

The owner explicitly authorized a finite read-only investigation of the previously
unresolved registered parent allowlist in BSR/IP, omitting only the child-row unit
predicate. This was a one-task exception, not a change to the default Collector
equipment scope, credential, grant, configuration or ingestion policy.

All selected parents were covered by exhausted traversals; capped groups were
refined or resumed, with no unfinished parent or paging continuation. The same
parent population returned direct children without the child unit predicate and
none with the CS01 predicate restored. This reproduces the query-filter effect;
it does not establish a child's stored unit as null, blank or another unit.
In the returned child records, eq11 was absent. Explicit null, empty string,
other nonblank unit and unavailable field are distinct states. A same-object,
same-credential projection control exposed CS01 on selected parents while eq11
remained absent on already observed child samples with a smaller field selection.
The actual stored unit and reason for omission remain UNKNOWN. Do not coalesce
the parent's unit into the child's source fact or broaden grants to guess it.

Paging used the existing GET-only client, source-origin checks, response/rate caps,
finite parent predicates, request/time budgets and WO-owner idle windows. A safe
numeric next-page counter could resume the same query/field selection; no raw
session URL, cookie, token or auth header was retained. Duplicate observations
were reconciled by exact source identity, with no conflicting relationship/unit
observations. This is scoped API traversal, not a transactional global snapshot.

No investigated child was ingested by this read. The earlier separately approved
technical-row append remains a different operation; Registry, Equipment/AssetMaster,
status history, mappings, ledger, asset cursors/runs and existing containers are
preserved. Live services remain PR119 and candidate activation remains stopped at
the controller source/recovery compatibility gate. PR121 remains Draft/superseded;
Logbook PdM remains HOLD. Counts, identities and evidence remain private.

Two local diagnostics initially exited with code1: an isolated synthetic test
context omitted the urlparse import, and a comm-only docker top format omitted
the PID column required by Docker. Both were corrected and their checks passed.
Those diagnostics sent no Maximo requests and performed no database operations;
all actual investigation business GETs succeeded. These are not source failures.

The owner describes an unnamed level above system, then system -> subsystem ->
asset -> equipment. This is domain input, not verified Maximo role metadata.
Preserve the source parent-child structure without imposing a two-level taxonomy,
mapping workbook S/E/C labels, or treating Registry members as physical roots.
A registered node can start an authorized view and still have source ancestors.
Depth and semantic role are independent; role mapping and global coverage remain
UNKNOWN/PARTIAL. Excel remains a reference and was not imported.

Next safe work is a separately reviewed eligibility/scope plan for any future
ingestion of children with unavailable source units. The read exception does not
authorize that ingestion, new membership, role assignment or service activation.
