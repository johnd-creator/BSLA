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
