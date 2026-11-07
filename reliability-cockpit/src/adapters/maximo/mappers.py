"""Field mappers: raw OSLC payload -> vendor-neutral domain models.

Translation table source of truth:
reliability-data-contracts/mappings/maximo-to-contracts.md (verified site BSR).
"""

from __future__ import annotations

from typing import Any, Mapping

from src.adapters.maximo.oslc_client import (
    oslc_pop_bool,
    oslc_pop_number,
    oslc_pop_text,
    oslc_timestamp,
)
from src.domain.equipment import Equipment, MaximoEquipmentSource
from src.domain.item import Item
from src.domain.labor import Labor
from src.domain.person import Person
from src.domain.service_request import ServiceRequest
from src.domain.work_order import WorkOrder


def equipment_from_payload(member: Mapping[str, Any]) -> Equipment:
    src = MaximoEquipmentSource(
        assetnum=oslc_pop_text(member, "assetnum"),
        assetid=oslc_pop_number(member, "assetid"),
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
    )
    return Equipment(
        id=oslc_pop_text(member, "assetnum") or "",
        name=oslc_pop_text(member, "description"),
        description=oslc_pop_text(member, "description"),
        location_id=oslc_pop_text(member, "location"),
        equipment_class=oslc_pop_text(member, "assettype"),
        unit=oslc_pop_text(member, "eq11") or oslc_pop_text(member, "plant"),
        status=oslc_pop_text(member, "status") or oslc_pop_text(member, "status_description"),
        status_description=oslc_pop_text(member, "status_description"),
        is_running=oslc_pop_bool(member, "isrunning"),
        priority=oslc_pop_number(member, "priority"),
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
        parent_wo=None,  # PCTASKID is not a verified parent WO number.
        has_children=oslc_pop_bool(member, "haschildren"),
        estimated_labor_cost=oslc_pop_number(member, "estlabcost"),
        estimated_material_cost=oslc_pop_number(member, "estmatcost"),
        actual_labor_cost=oslc_pop_number(member, "actlabcost"),
        actual_material_cost=oslc_pop_number(member, "actmatcost"),
        actual_labor_hours=oslc_pop_number(member, "actlabhrs"),
        sources={"maximo": {
            "wonum": member.get("wonum"), "workorderid": member.get("workorderid"),
            "hierarchy": {"schema_version": 1, "parent_wo_state": "UNKNOWN",
                          "source_fields": {name: oslc_pop_text(member, name)
                                            for name in ("pctaskid", "parent", "wogroup") if name in member}},
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
