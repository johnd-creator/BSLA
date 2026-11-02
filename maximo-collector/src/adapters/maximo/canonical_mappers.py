"""Explicit Maximo -> NADI Reliability Contract v1 mappers.

Only allowlisted scalar fields are emitted. Raw OSLC payloads, hrefs, person
fields, and collection references never cross this boundary.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping

from src.adapters.maximo.oslc_client import oslc_pop_integer, oslc_pop_number, oslc_pop_text, oslc_timestamp
from src.canonical_identity import canonical_id, scoped_reference


CONTRACT_VERSION = "1.0"
_EVENT_TYPES = {"CM", "PM", "INSPECTION", "CALIBRATION", "REPAIR", "EMERGENCY"}


def _text(member: Mapping[str, Any], key: str) -> str | None:
    return oslc_pop_text(member, key)


def _required(member: Mapping[str, Any], key: str) -> str:
    value = _text(member, key)
    if not value:
        raise ValueError(f"Maximo canonical mapping requires {key}")
    return value


def _scope(member: Mapping[str, Any]) -> tuple[str, str]:
    return _required(member, "siteid"), _required(member, "orgid")


def _timestamp(member: Mapping[str, Any], key: str) -> str | None:
    raw = member.get(key)
    if raw is None or raw == "":
        return None
    parsed = oslc_timestamp(raw)
    if parsed is None:
        raise ValueError(f"invalid Maximo timestamp field {key}")
    return parsed.isoformat()


def _retained_clock(member: Mapping[str, Any], key: str) -> str | None:
    parsed = _timestamp(member, key)
    value = member.get(key)
    return value if parsed is not None and isinstance(value, str) else parsed


def _provenance(
    source_object: str,
    source_record_id: str,
    site: str,
    organization: str,
    *,
    application: str | None,
    source_number: str | None = None,
    source_created_at: str | None = None,
    source_updated_at: str | None = None,
) -> dict[str, Any]:
    return {
        "source_system": "MAXIMO",
        "source_application": application,
        "source_object": source_object,
        "source_record_id": source_record_id,
        "source_number": source_number,
        "source_site": site,
        "source_organization": organization,
        "source_created_at": source_created_at,
        "source_updated_at": source_updated_at,
        "ingested_at": None,
    }


def _evidence(status: str, *, path: list[str] | None = None, notes: str | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {"status": status}
    if path:
        result["path"] = path
    if notes:
        result["notes"] = notes
    return result


def asset_master_from_payload(member: Mapping[str, Any]) -> dict[str, Any]:
    assetnum = _required(member, "assetnum")
    site, organization = _scope(member)
    changed = _timestamp(member, "changedate")
    return {
        "canonical_id": canonical_id("asset", "MXASSET", assetnum, site, organization),
        "contract_version": CONTRACT_VERSION,
        "source_asset_number": assetnum,
        "description": _text(member, "description"),
        "status": _text(member, "status"),
        "location_ref": scoped_reference("location", "MXASSET", _text(member, "location"), site, organization),
        "site_code": site,
        "organization_code": organization,
        "asset_type": _text(member, "assettype"),
        "plant": _text(member, "plant"),
        "unit": _text(member, "eq11"),
        "source_updated_at": changed,
        "provenance": _provenance("MXASSET", assetnum, site, organization, application=None, source_updated_at=changed),
        "relationship_evidence": {
            "location_ref": _evidence("DIRECT_VERIFIED"),
        },
        "sources": {"maximo": {
            "object_structure": "MXASSET", "assetnum": assetnum,
            "assetid": oslc_pop_integer(member, "assetid"), "description": _text(member, "description"),
            "location": _text(member, "location"), "siteid": site, "orgid": organization,
            "status": _text(member, "status"), "assettype": _text(member, "assettype"),
            "plant": _text(member, "plant"), "eq11": _text(member, "eq11"),
            "parent": _text(member, "parent"), "changedate": changed,
        }},
    }


def maintenance_event_from_payload(member: Mapping[str, Any]) -> dict[str, Any]:
    wonum = _required(member, "wonum")
    assetnum = _required(member, "assetnum")
    site, organization = _scope(member)
    changed = _timestamp(member, "changedate")
    work_type = _text(member, "worktype")
    asset_ref = scoped_reference("asset", "MXASSET", assetnum, site, organization)
    return {
        "id": canonical_id("maintenance_event", "MXWODETAIL", wonum, site, organization),
        "canonical_id": canonical_id("maintenance_event", "MXWODETAIL", wonum, site, organization),
        "contract_version": CONTRACT_VERSION,
        "equipment_id": asset_ref,
        "work_order_id": scoped_reference("workorder", "MXWODETAIL", wonum, site, organization),
        "status": _text(member, "status"),
        # The existing schema has a conservative enum. Preserve every source
        # value in work_type/source quarantine and only populate the legacy
        # enum field when it is contract-valid.
        "event_type": work_type if work_type in _EVENT_TYPES else None,
        "work_type": work_type,
        "actual_start": _timestamp(member, "actstart"),
        "actual_finish": _timestamp(member, "actfinish"),
        "reported_at": _timestamp(member, "reportdate"),
        "scheduled_start": _timestamp(member, "schedstart"),
        "scheduled_finish": _timestamp(member, "schedfinish"),
        "source_changed_at": changed,
        "downtime_hours": oslc_pop_number(member, "downtime"),
        "labor_hours": oslc_pop_number(member, "actlabhrs"),
        "failure_code": _text(member, "failurecode"),
        "site_code": site,
        "organization_code": organization,
        "provenance": _provenance("MXWODETAIL", wonum, site, organization, application=None, source_number=wonum, source_updated_at=changed),
        "relationship_evidence": {"equipment_id": _evidence("DIRECT_VERIFIED")},
        "sources": {"maximo": {
            "origin": "MXWODETAIL", "wonum": wonum, "assetnum": assetnum,
            "worktype": work_type, "status": _text(member, "status"),
            "actstart": _timestamp(member, "actstart"), "actfinish": _timestamp(member, "actfinish"),
            "changedate": changed, "downtime": oslc_pop_number(member, "downtime"),
            "reportdate": _retained_clock(member, "reportdate"),
            "schedstart": _retained_clock(member, "schedstart"),
            "schedfinish": _retained_clock(member, "schedfinish"),
        }},
    }


def fmea_assessment_from_payload(member: Mapping[str, Any]) -> dict[str, Any]:
    record_id = _required(member, "fmeaid")
    site, organization = _scope(member)
    updated = _timestamp(member, "lastmodifieddate")
    assetnum = _text(member, "assetnum")
    return {
        "canonical_id": canonical_id("fmea", "IPFMEA", record_id, site, organization),
        "contract_version": CONTRACT_VERSION,
        "source_record_id": record_id,
        "source_number": _text(member, "fmeanum"),
        "revision": _text(member, "revision"),
        "lifecycle_status": _text(member, "status"),
        "description": _text(member, "description"),
        "asset_ref": scoped_reference("asset", "MXASSET", assetnum, site, organization),
        "failure_code_ref": scoped_reference("failure_code", "MXFAILURECODE", _text(member, "failurecode"), site, organization),
        "site_code": site,
        "organization_code": organization,
        "source_updated_at": updated,
        "status_changed_at": _timestamp(member, "statusdate"),
        "provenance": _provenance("IPFMEA", record_id, site, organization, application="RELIABILITY", source_number=_text(member, "fmeanum"), source_updated_at=updated),
        "relationship_evidence": {"asset_ref": _evidence("DIRECT_VERIFIED")},
        "sources": {"maximo": {
            "object_structure": "IPFMEA", "fmeaid": record_id, "fmeanum": _text(member, "fmeanum"),
            "revision": _text(member, "revision"), "status": _text(member, "status"),
            "description": _text(member, "description"), "assetnum": assetnum,
            "siteid": site, "orgid": organization, "failurecode": _text(member, "failurecode"),
            "lastmodifieddate": updated, "statusdate": _timestamp(member, "statusdate"),
        }},
    }


def rcfa_analysis_from_payload(member: Mapping[str, Any]) -> dict[str, Any]:
    record_id = _required(member, "rcfaid")
    site, organization = _scope(member)
    created = _timestamp(member, "createddate")
    requested = _timestamp(member, "req_date")
    return {
        "canonical_id": canonical_id("rcfa", "IPRCFA", record_id, site, organization),
        "contract_version": CONTRACT_VERSION,
        "source_record_id": record_id,
        "source_number": _text(member, "norcfa"),
        "revision": _text(member, "revisi"),
        "lifecycle_status": _text(member, "status"),
        "category": _text(member, "kategori"),
        "asset_ref": None,
        "location_ref": None,
        "workorder_ref": None,
        "failure_event_ref": None,
        "site_code": site,
        "organization_code": organization,
        "source_created_at": created,
        "requested_at": requested,
        "provenance": _provenance("IPRCFA", record_id, site, organization, application="RELIABILITY", source_number=_text(member, "norcfa"), source_created_at=created),
        "relationship_evidence": {
            "asset_ref": _evidence("UNRESOLVED"),
            "location_ref": _evidence("UNRESOLVED"),
            "workorder_ref": _evidence("UNRESOLVED"),
            "failure_event_ref": _evidence("UNRESOLVED"),
        },
        "sources": {"maximo": {
            "object_structure": "IPRCFA", "norcfa": _text(member, "norcfa"), "rcfaid": record_id,
            "revisi": _text(member, "revisi"), "status": _text(member, "status"),
            "kategori": _text(member, "kategori"), "siteid": site, "orgid": organization,
            "createddate": created, "req_date": requested,
        }},
    }


def asset_health_assessment_from_payload(member: Mapping[str, Any]) -> dict[str, Any]:
    record_id = _required(member, "bhmid")
    site, organization = _scope(member)
    created = _timestamp(member, "createddate")
    updated = _timestamp(member, "lastmodifieddate")
    return {
        "canonical_id": canonical_id("bhm", "IPBHM", record_id, site, organization),
        "contract_version": CONTRACT_VERSION,
        "source_record_id": record_id,
        "revision": _text(member, "revision"),
        "lifecycle_status": _text(member, "status"),
        "description": _text(member, "description"),
        "function_description": _text(member, "fungsi"),
        "asset_ref": scoped_reference("asset", "MXASSET", _text(member, "assetnum"), site, organization),
        "site_code": site,
        "organization_code": organization,
        "source_created_at": created,
        "source_updated_at": updated,
        "status_changed_at": _timestamp(member, "statusdate"),
        "provenance": _provenance("IPBHM", record_id, site, organization, application="RELIABILITY", source_updated_at=updated, source_created_at=created),
        "relationship_evidence": {"asset_ref": _evidence("DIRECT_VERIFIED")},
        "sources": {"maximo": {
            "object_structure": "IPBHM", "bhmid": record_id, "eid": _text(member, "eid"),
            "revision": _text(member, "revision"), "status": _text(member, "status"),
            "description": _text(member, "description"), "fungsi": _text(member, "fungsi"),
            "assetnum": _text(member, "assetnum"), "siteid": site, "orgid": organization,
            "createddate": created, "lastmodifieddate": updated, "statusdate": _timestamp(member, "statusdate"),
        }},
    }


def overhaul_event_from_payload(
    member: Mapping[str, Any],
    workorder_index: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    record_id = _required(member, "domid")
    site, organization = _scope(member)
    wonum = _text(member, "wonum")
    workorder_ref = scoped_reference("workorder", "MXWODETAIL", wonum, site, organization)
    workorder = workorder_index.get(wonum) if workorder_index and wonum else None
    asset_ref = workorder.get("equipment_id") if workorder else None
    evidence = {
        "workorder_ref": _evidence("DIRECT_VERIFIED"),
        "asset_ref": _evidence(
            "DERIVED_VERIFIED_PATH",
            path=["IP_DOM_OH.wonum", "MXWODETAIL.wonum", "MXWODETAIL.assetnum", "asset_master"],
            notes="Resolved through an already fetched Work Order; no Maximo lookup is performed.",
        ),
    }
    unresolved: dict[str, Any] = {}
    inspection = _text(member, "inspeksinum")
    performance = _text(member, "perfomance_test")
    if inspection is not None:
        unresolved["inspection_number"] = inspection
    if performance is not None:
        unresolved["performance_test"] = performance
    created = _timestamp(member, "createdate")
    updated = _timestamp(member, "changedate")
    result: dict[str, Any] = {
        "canonical_id": canonical_id("oh", "IP_DOM_OH", record_id, site, organization),
        "contract_version": CONTRACT_VERSION,
        "source_record_id": record_id,
        "source_number": _text(member, "domohnum"),
        "lifecycle_status": _text(member, "status"),
        "workorder_ref": workorder_ref,
        "asset_ref": asset_ref,
        "site_code": site,
        "organization_code": organization,
        "planned_start_at": _timestamp(member, "tgl_mulai"),
        "planned_finish_at": _timestamp(member, "tgl_selesai"),
        "actual_start_at": _timestamp(member, "tgl_actual_mulai"),
        "actual_finish_at": _timestamp(member, "tgl_actual_selesai"),
        "progress": oslc_pop_number(member, "progress"),
        "source_created_at": created,
        "source_updated_at": updated,
        "provenance": _provenance("IP_DOM_OH", record_id, site, organization, application="DOMINION", source_number=_text(member, "domohnum"), source_created_at=created, source_updated_at=updated),
        "relationship_evidence": evidence,
        "sources": {"maximo": {
            "object_structure": "IP_DOM_OH", "domid": record_id, "domohnum": _text(member, "domohnum"),
            "wonum": wonum, "inspeksinum": inspection, "status": _text(member, "status"),
            "siteid": site, "orgid": organization, "tgl_mulai": _timestamp(member, "tgl_mulai"),
            "tgl_selesai": _timestamp(member, "tgl_selesai"), "tgl_actual_mulai": _timestamp(member, "tgl_actual_mulai"),
            "tgl_actual_selesai": _timestamp(member, "tgl_actual_selesai"), "changedate": updated,
            "createdate": created, "progress": _text(member, "progress"), "perfomance_test": performance,
        }},
    }
    if unresolved:
        result["unresolved_source_attributes"] = unresolved
    return result
