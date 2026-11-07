"""Field mappers: raw OSLC payload -> contract-shaped domain models.

Translation table source of truth:
reliability-data-contracts/mappings/maximo-to-contracts.md (verified site BSR).
Ported from the reliability-cockpit adapter (which this collector replaces).
"""

from __future__ import annotations

from src.adapters.maximo.actual_dates import evidence as actual_date_evidence

from typing import Any, Mapping

from src.adapters.maximo.oslc_client import (
    oslc_pop_bool,
    oslc_pop_integer,
    oslc_pop_number,
    oslc_pop_text,
    oslc_timestamp,
)
from src.domain.models import (
    Equipment,
    Item,
    Labor,
    MaximoEquipmentSource,
    Person,
    ServiceRequest,
    WorkOrder,
)

# These fields are present in the verified ``mxapiasset`` knowledge record.
# Collection references, hrefs, and personal identifiers are intentionally
# excluded: this collector only stores scalar business data that is useful to
# the BSR equipment view.
_ASSET_EXTRA_TEXT = (
    "assettype_description", "plant_description", "mainstr", "mainstr_description",
    "hierarchypath", "eq5", "eq9", "eq8", "eq10", "eq11_description", "eq23", "newsite",
)
_ASSET_EXTRA_NUMBERS = (
    "ytdcost", "moddowntimehist", "totunchargedcost", "unchargedcost", "invcost",
    "budgetcost", "expectedlife",
)
_ASSET_EXTRA_BOOLEANS = (
    "moved", "pluscismte", "pluscisinhousecal", "tloampartition", "removefromactivesp",
    "mainthierchy", "returnedtovendor", "changepmstatus", "pluscsolution",
    "removefromactiveroutes", "rolltoallchildren", "islinear", "plusgexregistered",
    "pluscpmextdate", "plusciscontam", "disabled", "plusgleaking", "autowogen",
    "plusgistemp", "plusgispassvalve",
)
_WORK_ORDER_EXTRA_TEXT = ("seksi", "bu")
_WORK_ORDER_EXTRA_NUMBERS = ("jumlahhidup", "jumlahmati", "luasareatanam")


def _asset_extra(member: Mapping[str, Any]) -> dict[str, Any]:
    extra: dict[str, Any] = {}
    for name in _ASSET_EXTRA_TEXT:
        value = oslc_pop_text(member, name)
        if value is not None:
            extra[name] = value
    for name in _ASSET_EXTRA_NUMBERS:
        value = oslc_pop_number(member, name)
        if value is not None:
            extra[name] = value
    for name in _ASSET_EXTRA_BOOLEANS:
        value = oslc_pop_bool(member, name)
        if value is not None:
            extra[name] = value
    return extra


def _work_order_extra(member: Mapping[str, Any]) -> dict[str, Any]:
    extra: dict[str, Any] = {}
    for name in _WORK_ORDER_EXTRA_TEXT:
        value = oslc_pop_text(member, name)
        if value is not None:
            extra[name] = value
    for name in _WORK_ORDER_EXTRA_NUMBERS:
        value = oslc_pop_number(member, name)
        if value is not None:
            extra[name] = value
    return extra


def equipment_from_payload(member: Mapping[str, Any]) -> Equipment:
    assetnum = oslc_pop_text(member, "assetnum")
    if not assetnum:
        raise ValueError("Maximo asset row has no assetnum")
    src = MaximoEquipmentSource(
        assetnum=assetnum,
        assetid=oslc_pop_integer(member, "assetid"),
        location=oslc_pop_text(member, "location"),
        siteid=oslc_pop_text(member, "siteid"),
        orgid=oslc_pop_text(member, "orgid"),
        status=oslc_pop_text(member, "status"),
        assettype=oslc_pop_text(member, "assettype"),
        plant=oslc_pop_text(member, "plant"),
        eq11=oslc_pop_text(member, "eq11"),
        parent=oslc_pop_text(member, "parent"),
        ancestor=oslc_pop_text(member, "ancestor"),
        children=oslc_pop_bool(member, "children"),
        isrunning=oslc_pop_bool(member, "isrunning"),
        installdate=oslc_timestamp(member.get("installdate")),
        changedate=oslc_timestamp(member.get("changedate")),
        totdowntime=oslc_pop_number(member, "totdowntime"),
        extra=_asset_extra(member),
    )
    return Equipment(
        id=assetnum,
        name=oslc_pop_text(member, "description"),
        description=oslc_pop_text(member, "description"),
        location_id=oslc_pop_text(member, "location"),
        equipment_class=oslc_pop_text(member, "assettype"),
        unit=oslc_pop_text(member, "eq11") or oslc_pop_text(member, "plant"),
        status=oslc_pop_text(member, "status") or oslc_pop_text(member, "status_description"),
        status_description=oslc_pop_text(member, "status_description"),
        is_running=oslc_pop_bool(member, "isrunning"),
        priority=oslc_pop_integer(member, "priority"),
        parent_id=oslc_pop_text(member, "parent"),
        ancestor_id=oslc_pop_text(member, "ancestor"),
        has_children=oslc_pop_bool(member, "children"),
        failure_code=oslc_pop_text(member, "failurecode"),
        is_safety_critical=oslc_pop_bool(member, "issafety"),
        is_calibration=oslc_pop_bool(member, "iscalibration"),
        installed_at=oslc_timestamp(member.get("installdate")),
        status_changed_at=oslc_timestamp(member.get("statusdate")),
        source_changed_at=oslc_timestamp(member.get("changedate")),
        purchase_price=oslc_pop_number(member, "purchaseprice"),
        replacement_cost=oslc_pop_number(member, "replacecost"),
        total_cost=oslc_pop_number(member, "totalcost"),
        downtime_total_hours=oslc_pop_number(member, "totdowntime"),
        manufacturer=oslc_pop_text(member, "manufacturer"),
        vendor=oslc_pop_text(member, "vendor"),
        maximo_source=src,
    )


def work_order_from_payload(member: Mapping[str, Any]) -> WorkOrder:
    return WorkOrder(
        id=oslc_pop_text(member, "wonum") or "",
        equipment_id=oslc_pop_text(member, "assetnum"),
        location_id=oslc_pop_text(member, "location"),
        status=oslc_pop_text(member, "status"),
        status_description=oslc_pop_text(member, "status_description"),
        work_type=oslc_pop_text(member, "worktype"),
        work_class=oslc_pop_text(member, "woclass"),
        description=oslc_pop_text(member, "description"),
        reported_at=oslc_timestamp(member.get("reportdate")),
        source_changed_at=oslc_timestamp(member.get("changedate")),
        status_changed_at=oslc_timestamp(member.get("statusdate")),
        scheduled_start=oslc_timestamp(member.get("schedstart")),
        scheduled_finish=oslc_timestamp(member.get("schedfinish")),
        target_completion=oslc_timestamp(member.get("targcompdate")),
        estimated_duration_hours=oslc_pop_number(member, "estdur"),
        downtime_hours=oslc_pop_number(member, "downtime"),
        priority=oslc_pop_text(member, "wopriority"),
        priority_description=oslc_pop_text(member, "wopriority_description"),
        reported_by=oslc_pop_text(member, "reportedby"),
        supervisor=oslc_pop_text(member, "supervisor"),
        lead=oslc_pop_text(member, "lead"),
        failure_code=oslc_pop_text(member, "failurecode"),
        is_task=oslc_pop_bool(member, "istask"),
        # PCTASKID has no verified equivalence to a parent WO number.
        parent_wo=None,
        has_children=oslc_pop_bool(member, "haschildren"),
        estimated_labor_cost=oslc_pop_number(member, "estlabcost"),
        estimated_material_cost=oslc_pop_number(member, "estmatcost"),
        actual_labor_cost=oslc_pop_number(member, "actlabcost"),
        actual_material_cost=oslc_pop_number(member, "actmatcost"),
        actual_labor_hours=oslc_pop_number(member, "actlabhrs"),
        sources={"maximo": {
            "wonum": member.get("wonum"),
            "workorderid": member.get("workorderid"),
            "siteid": oslc_pop_text(member, "siteid"),
            "orgid": oslc_pop_text(member, "orgid"),
            "observed_fields": sorted(str(k) for k in member if k in {
                "assetnum", "location", "status", "status_description", "worktype", "woclass", "description",
                "reportdate", "changedate", "statusdate", "schedstart", "schedfinish", "targcompdate", "estdur",
                "downtime", "wopriority", "wopriority_description", "reportedby", "supervisor", "lead", "failurecode",
                "istask", "haschildren", "estlabcost", "estmatcost", "actlabcost", "actmatcost", "actlabhrs"}),
            "extra": _work_order_extra(member),
            "actual_dates": actual_date_evidence(member),
            "hierarchy": {
                "schema_version": 1,
                "parent_wo_state": "UNKNOWN",
                "source_fields": {name: oslc_pop_text(member, name)
                                  for name in ("pctaskid", "parent", "wogroup") if name in member},
            },
        }},
    )


def service_request_from_payload(member: Mapping[str, Any]) -> ServiceRequest:
    return ServiceRequest(
        id=oslc_pop_text(member, "ticketid") or "",
        description=oslc_pop_text(member, "description"),
        status=oslc_pop_text(member, "status"),
        status_description=oslc_pop_text(member, "status_description"),
        work_type=oslc_pop_text(member, "worktype"),
        equipment_id=oslc_pop_text(member, "assetnum"),
        location_id=oslc_pop_text(member, "location"),
        reported_by=oslc_pop_text(member, "reportedby"),
        reported_by_name=oslc_pop_text(member, "reportedbyname"),
        reported_at=oslc_timestamp(member.get("reportdate")),
        source_changed_at=oslc_timestamp(member.get("changedate")),
        affected_at=oslc_timestamp(member.get("affecteddate")),
        actual_start=oslc_timestamp(member.get("actualstart")),
        actual_finish=oslc_timestamp(member.get("actualfinish")),
        target_start=oslc_timestamp(member.get("targetstart")),
        target_finish=oslc_timestamp(member.get("targetfinish")),
        internal_priority=oslc_pop_text(member, "internalpriority"),
        reported_priority=oslc_pop_text(member, "reportedpriority"),
        actual_labor_hours=oslc_pop_number(member, "actlabhrs"),
        actual_labor_cost=oslc_pop_number(member, "actlabcost"),
        risk_area_environment=oslc_pop_text(member, "cxarlingkungan"),
        risk_area_process=oslc_pop_text(member, "cxarproses"),
        risk_area_human=oslc_pop_text(member, "cxarmanusia"),
        risk_area_reputation=oslc_pop_text(member, "cxarreputasi"),
        class_label=oslc_pop_text(member, "class"),
        status_changed_at=oslc_timestamp(member.get("statusdate")),
        sources={"maximo": {"ticketid": member.get("ticketid"), "ticketuid": member.get("ticketuid")}},
    )


def person_from_payload(member: Mapping[str, Any]) -> Person:
    return Person(
        id=oslc_pop_text(member, "personid") or "",
        display_name=oslc_pop_text(member, "displayname"),
        first_name=oslc_pop_text(member, "firstname"),
        status=oslc_pop_text(member, "status"),
        status_changed_at=oslc_timestamp(member.get("statusdate")),
        location_org=oslc_pop_text(member, "locationorg"),
    )


def item_from_payload(member: Mapping[str, Any]) -> Item:
    return Item(
        id=oslc_pop_text(member, "itemnum") or "",
        description=oslc_pop_text(member, "description"),
        status=oslc_pop_text(member, "status"),
        item_type=oslc_pop_text(member, "itemtype"),
        lot_type=oslc_pop_text(member, "lottype"),
        issue_unit=oslc_pop_text(member, "issueunit"),
        order_unit=oslc_pop_text(member, "orderunit"),
        is_rotating=oslc_pop_bool(member, "rotating"),
        is_kit=oslc_pop_bool(member, "iskit"),
        is_crew=oslc_pop_bool(member, "iscrew"),
        inspection_required=oslc_pop_bool(member, "inspectionrequired"),
        meter_name=oslc_pop_text(member, "metername"),
        item_set_id=oslc_pop_text(member, "itemsetid"),
        status_changed_at=oslc_timestamp(member.get("statusdate")),
    )


def labor_from_payload(member: Mapping[str, Any]) -> Labor:
    return Labor(
        id=oslc_pop_text(member, "laborcode") or "",
        person_id=oslc_pop_text(member, "personid"),
        status=oslc_pop_text(member, "status"),
        status_description=oslc_pop_text(member, "status_description"),
        work_site=oslc_pop_text(member, "worksite"),
        is_assigned=oslc_pop_bool(member, "assigned"),
        availability_factor=oslc_pop_number(member, "availfactor"),
        reported_hours=oslc_pop_number(member, "reportedhrs"),
        year_to_date_other_hours=oslc_pop_number(member, "ytdothrs"),
        year_to_date_refused_hours=oslc_pop_number(member, "ytdhrsrefused"),
    )
