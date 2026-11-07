# Maximo → Reliability Contracts Mapping

Field-by-field translation from verified Maximo object structures (site BSR) to
vendor-neutral contracts. Source of truth: `maximo-knowledge/discovery/objects/`.

Every contract keeps a `sources.maximo` block with the raw Maximo field names so
the adapter can map back. Core contract fields are vendor-neutral (snake_case).

Status legend: ✅ verified on this instance · ⛔ forbidden (BMXAA0024E) · ⊘ derived/computed

---

## Equipment ← `MXASSET` (69 fields verified)

| Contract field | Maximo field | Type | Notes |
|---|---|---|---|
| `id` | `assetnum` | string | natural key |
| `name` | `description` | string | asset description used as name |
| `description` | `description` | string | |
| `location_id` | `location` | string | |
| `equipment_class` | `assettype` | string | e.g. PRODUCTION |
| `unit` | `eq11` / `plant` | string | eq11=unit code, plant=plant |
| `status` | `status` | string | e.g. OPERATING, DECOMMISSIONED |
| `status_description` | `status_description` | string | |
| `is_running` | `isrunning` | boolean | |
| `priority` | `priority` | integer | |
| `parent_id` | `parent` | string | hierarchy |
| `ancestor_id` | `ancestor` | string | hierarchy |
| `has_children` | `children` | boolean | |
| `failure_code` | `failurecode` | string | |
| `is_safety_critical` | `issafety` | boolean | |
| `is_calibration` | `iscalibration` | boolean | |
| `installed_at` | `installdate` | datetime | |
| `status_changed_at` | `statusdate` | datetime | |
| `source_changed_at` | `changedate` | datetime | **delta-sync watermark** |
| `purchase_price` | `purchaseprice` | number | |
| `replacement_cost` | `replacecost` | number | |
| `total_cost` | `totalcost` | number | |
| `downtime_total_hours` | `totdowntime` | number | |
| `manufacturer` | `manufacturer` | string | (mxapiasset only) |
| `vendor` | `vendor` | string | (mxapiasset only) |

---

## WorkOrder ← `MXWODETAIL` (166 fields verified)

| Contract field | Maximo field | Type | Notes |
|---|---|---|---|
| `id` | `wonum` | string | natural key |
| `equipment_id` | `assetnum` | string | |
| `location_id` | `location` | string | |
| `status` | `status` | string | required |
| `status_description` | `status_description` | string | |
| `work_type` | `worktype` | string | CM/PM/etc |
| `work_class` | `woclass` | string | |
| `description` | `description` | string | |
| `reported_at` | `reportdate` | datetime | |
| `source_changed_at` | `changedate` | datetime | **delta watermark** |
| `status_changed_at` | `statusdate` | datetime | |
| `scheduled_start` | `schedstart` | datetime | |
| `scheduled_finish` | `schedfinish` | datetime | |
| `target_completion` | `targcompdate` | datetime | |
| `estimated_duration_hours` | `estdur` | number | |
| `downtime_hours` | — | number/null | NOT DERIVED from MXWODETAIL.downtime: the source field is a boolean indicator, not hours. Current Maximo adapter emits null. |
| `priority` | `wopriority` | string | |
| `priority_description` | `wopriority_description` | string | |
| `reported_by` | `reportedby` | string | personid |
| `supervisor` | `supervisor` | string | |
| `lead` | `lead` | string | |
| `failure_code` | `failurecode` | string/null | Verified direct classification field; preserved through local Maintenance Mart. Not a governed failure occurrence or denominator. |
| `sources.maximo.reliability_evidence` | `failurecode`, `problemcode`, `faildate`, `parent`, `origrecordclass`, `origrecordid`, `woclass`, `istask`, `haschildren`, `hasfollowupwork`, `downtime` | object | Typed, scoped, per-field source-version evidence only. Missing/invalid/naive clocks remain explicit. Parent/origin are not resolved or deduplicated; downtime is an indicator, not hours. |
| `is_task` | `istask` | boolean | |
| `parent_wo` | — | string/null | Unknown in current adapters; pctaskid/wogroup are not verified parent WO numbers. Null is not proof of no parent. |
| `sources.maximo.hierarchy.source_fields` | `pctaskid`, `parent`, `wogroup` when actually returned | object | Allowlisted observations only, state UNKNOWN; no inferred hierarchy/sequence. Old stored values use `legacy_parent_wo` with unknown provenance. |
| `has_children` | `haschildren` | boolean | |
| `estimated_labor_cost` | `estlabcost` | number | |
| `estimated_material_cost` | `estmatcost` | number | |
| `actual_labor_cost` | `actlabcost` | number | |
| `actual_material_cost` | `actmatcost` | number | |
| `actual_labor_hours` | `actlabhrs` | number | |

---

## ServiceRequest ← `MXAPISR` (96 fields verified)

| Contract field | Maximo field | Notes |
|---|---|---|
| `id` | `ticketid` | natural key |
| `description` | `description` | |
| `status` | `status` | required |
| `work_type` | `worktype` | |
| `class` | `class` | |
| `equipment_id` | `assetnum` | |
| `location_id` | `location` | |
| `reported_by` | `reportedby` | |
| `reported_by_name` | `reportedbyname` | |
| `reported_at` | `reportdate` | |
| `source_changed_at` | `changedate` | **delta watermark** |
| `affected_at` | `affecteddate` | |
| `actual_start` / `actual_finish` | `actualstart` / `actualfinish` | |
| `target_start` / `target_finish` | `targetstart` / `targetfinish` | |
| `internal_priority` | `internalpriority` | |
| `reported_priority` | `reportedpriority` | |
| `actual_labor_hours` | `actlabhrs` | |
| `actual_labor_cost` | `actlabcost` | |
| `risk_area_environment` | `cxarlingkungan` | custom IP risk |
| `risk_area_process` | `cxarproses` | custom IP risk |
| `risk_area_human` | `cxarmanusia` | custom IP risk |
| `risk_area_reputation` | `cxarreputasi` | custom IP risk |

---

## Person ← `MXPERSON` (34 fields verified)

| Contract field | Maximo field | Notes |
|---|---|---|
| `id` | `personid` | natural key |
| `display_name` | `displayname` | |
| `first_name` | `firstname` | |
| `status` | `status` | |
| `status_changed_at` | `statusdate` | |
| `location_org` | `locationorg` | |

> `email_collectionref` and `phone_collectionref` are URL references only —
> do NOT persist raw personal values.

---

## Item ← `MXITEM` (40 fields verified)

| Contract field | Maximo field | Notes |
|---|---|---|
| `id` | `itemnum` | natural key |
| `description` | `description` | |
| `status` | `status` | |
| `item_type` | `itemtype` | |
| `lot_type` | `lottype` | |
| `issue_unit` | `issueunit` | |
| `order_unit` | `orderunit` | |
| `is_rotating` | `rotating` | |
| `is_kit` | `iskit` | |
| `is_crew` | `iscrew` | |
| `inspection_required` | `inspectionrequired` | |
| `meter_name` | `metername` | |
| `item_set_id` | `itemsetid` | |
| `status_changed_at` | `statusdate` | |

---

## Labor ← `MXAPILABOR` (14 fields verified)

| Contract field | Maximo field | Notes |
|---|---|---|
| `id` | `laborcode` | natural key |
| `person_id` | `personid` | → Person |
| `status` | `status` | |
| `work_site` | `worksite` | |
| `is_assigned` | `assigned` | |
| `availability_factor` | `availfactor` | |
| `reported_hours` | `reportedhrs` | |
| `year_to_date_other_hours` | `ytdothrs` | |
| `year_to_date_refused_hours` | `ytdhrsrefused` | |

---

## Forbidden objects (pending read-enabled credential)

These Maximo objects are currently inaccessible (BMXAA0024E) for the discovery
account. Contracts fall back to derived/alternative sources:

| Contract | Intended Maximo source | Current fallback |
|---|---|---|
| Failure | `MXFAILURECODE` ⛔ | derived from `MXWODETAIL.failurecode` |
| Downtime (master) | Downtime Report ⛔ | derived from `MXWODETAIL.downtime` / `MXASSET.totdowntime` |
| Location | `MXAPILOCATION` ⛔ | `location` field embedded on Equipment/WO/SR |
| PM schedule | `MXAPIPM` ⛔ | `worktype=PM` filter on WorkOrder |
| Meter | `MXAPIMETER` ⛔ | `metername` on Item; `assetmeter_collectionref` on Asset |
| JobPlan | `MXAPIJOBPLAN` ⛔ | — |

---

## Standard query constraints (all objects)

```
oslc.where=siteid="BSR"               # mandatory site scope
oslc.paging=true&pageno=N&oslc.pageSize=100   # pagination
oslc.select=<comma-separated>         # field selection
oslc.orderBy=-changedate              # sort by delta watermark
```

Rewrite resource href host `mx761app1.plnindonesiapower.co.id` →
`maximo.plnindonesiapower.co.id` (LB) so session cookies apply.
