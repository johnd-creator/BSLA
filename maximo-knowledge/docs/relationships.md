# Relationship Map

Verified relationships between Maximo object structures, evidenced from live
OSLC field observations (site BSR). Relationships are recorded machine-readably
in each `discovery/objects/*.json` under the `relationships` array.

## Evidence levels

| Tag | Meaning |
|---|---|
| `verified field` | The linking field appeared on a verified OSLC sample record |
| `verified collectionref` | A `_collectionref` URL reference was observed on a verified record |
| `foreign key` | Field name matches a known primary-key pattern; business-confirmed |

> Per `AGENTS.md`: do not mark a relationship as verified until confirmed from
> metadata, schema, or successful authorized queries. All relationships below
> are evidence-based from verified field observations. Referential integrity
> (actual value resolution) is not yet join-tested.

## Entity model

```text
Location (MXAPILOCATION ⛔ forbidden)
└── Asset (MXASSET)
    ├── parent / ancestor / children      (asset hierarchy)
    ├── AssetSpec, AssetMeter, AssetUserCust, AssetMntSkd, AssetOpsKd  (collectionrefs)
    ├── Work Order (MXWODETAIL)
    │   ├── assetnum → Asset
    │   ├── WPLabor, WPMaterial, InvReserve   (collectionrefs)
    │   ├── parent / haschildren              (WO task hierarchy)
    │   └── failurecode → FailureCode (MXFAILURECODE ⛔ forbidden)
    ├── Service Request (MXAPISR)
    │   ├── assetnum → Asset
    │   └── WorkLog, TicketSpec, ClassStructure, Site  (collectionrefs)
    └── Item (MXITEM)
        ├── ItemSpec, ItemCondition, ItemOrgInfo, Conversion  (collectionrefs)
        └── metername → Meter (MXAPIMETER ⛔ forbidden)

Person (MXPERSON)
└── Labor (MXAPILABOR)
    └── personid → Person
```

## Per-object relationships

### MXASSET (asset) — 9 relationships
`parent`, `ancestor`, `children` (asset hierarchy); `assetspec_collectionref`,
`assetmeter_collectionref`, `assetusercust_collectionref`,
`assetmntskd_collectionref`, `assetopskd_collectionref` (verified
collectionrefs); `failurecode` → failure code (MXFAILURECODE forbidden).

### MXWODETAIL (work order) — 7 relationships
`assetnum` → asset (foreign key); `location` → location (MXAPILOCATION
forbidden); `wplabor_collectionref`, `wpmaterial_collectionref`,
`invreserve_collectionref` (verified collectionrefs); `parent`,
`haschildren` (WO task hierarchy).

### MXAPISR (service request) — 6 relationships
`assetnum` → asset (foreign key); `location` → location (MXAPILOCATION
forbidden); `worklog_collectionref`, `ticketspec_collectionref`,
`classstructure_collectionref`, `site_collectionref` (verified collectionrefs).

### MXITEM (item) — 5 relationships
`itemspec_collectionref`, `itemcondition_collectionref`,
`itemorginfo_collectionref`, `conversion_collectionref` (verified
collectionrefs); `metername` → meter (MXAPIMETER forbidden).

### MXAPIASSET (api asset) — 4 relationships
`parent`, `ancestor`, `children` (asset hierarchy); `failurecode` → failure
code (MXFAILURECODE forbidden).

### MXPERSON (person) — 1 relationship
`locationorg` → location/org.

### MXAPILABOR (labor) — 1 relationship
`personid` → person (foreign key to MXPERSON).

## Forbidden-object links

Six relationship targets are currently blocked by object-level READ
permissions (`BMXAA0024E`). The linking fields are verified on the parent
objects; only the target master is inaccessible:

| Target | Underlying object | Referenced from |
|---|---|---|
| FailureCode | FAILURECODE | mxasset.failurecode, mxwodetail.failurecode |
| Location | LOCHIERARCHY | mxwodetail.location, mxapisr.location |
| Meter | METER | mxitem.metername, mxasset.assetmeter_collectionref |
| PM | PM | (no verified inbound link yet) |
| JobPlan | JOBPLAN | (no verified inbound link yet) |

Granting READ sigoption (scoped to BSR) on these underlying objects will make
them discoverable and join-testable on the next run.

## 2026-11-02 hierarchy read verification

A bounded authenticated BSR/IP/CS01 pilot verified the existing MXAPIASSET
parent-child filter and retained relationship match. See the [sanitized field/type
receipt](../discovery/nadi-hierarchy-read-verification-20261102.json) and the
[platform checkpoint](../../docs/NADI-NIGHT-INTEGRATION-20261102.md). No raw plant
example is published. `mainthierchy` boolean and `hierarchypath` string do not
establish canonical role/path semantics; system/equipment/component stays UNKNOWN.
No full-population coverage, permission expansion or local ingestion is claimed.


### Scoped source-ingestion follow-up — 2026-11-03 WIB

The approved registered CS01 gap-root subset was paged against Maximo, with capped
groups refined until that subset was exhausted. New technical child rows passed
fresh private backup/independent isolated restore and exact-packet normal-writer
rehearsal before append to the existing Maximo-owned Collector/Mart. Old master,
Registry, mapping, ledger and asset-cursor fingerprints remain unchanged; the run
is PARTIAL and does not advance global cursors. No Registry import, role inference,
WO backfill, source write or service change. Full population/role acceptance stays
PARTIAL/UNKNOWN and local PR120 activation stays BLOCKED. Evidence and cardinalities
remain private; see the [integrated source report](../../docs/NADI-NIGHT-INTEGRATION-20261102.md) for the bounded method.


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

## NADI-HIERARCHY-CHILD-CANONICAL-INGEST-20261103 — closed approved ingestion

A later explicit owner approval admitted the sealed child/parent allowlist into the
existing Maximo-owned canonical Mart after fresh consistent backup, independent
restore and full-batch rollback/insert/replay rehearsal. The prior read-only unit
exception alone did not authorize writes. Existing canonical source fields and
MartWriter were reused, with a same-connection outer transaction and INSERT-only
AssetMaster fence. Legacy Equipment/status history were not appended; this avoids
expanding the scheduled WO/projector input population. Routine acquisition scope,
Registry, grants, credentials, schema and asset cursors remain unchanged.

Exact source IDs and direct parent references are preserved. Missing child eq11
stays unavailable/UNKNOWN, without parent/plant/CS01 fallback. Protected old facts,
Registry/mappings/ledger and WO classifications pass preservation checks. The
reviewed hierarchy reader traversed the isolated restored data with UNKNOWN roles
and unregistered child flags; unregistered roots were denied. The configured live
SELECT-only reader also verified all approved stored identities and parents.

These checks establish stored-data/source-reader compatibility; live hierarchy UI
and Engineer UAT remain pending while the PR119 runtime/controller gate is retained.
Global hierarchy coverage remains PARTIAL, semantic roles UNKNOWN, and Registry
members do not imply physical roots. Excel was not imported; Logbook PdM HOLD.
See the [closed-batch method and recovery limits](../../docs/NADI-NIGHT-INTEGRATION-20261102.md#nadi-hierarchy-child-canonical-ingest-20261103--closed-approved-ingestion).
Raw identities, cardinalities and recovery evidence remain private.
