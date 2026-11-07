"""Allowlisted WO reliability clues, not governed failures or repair intervals.

Technical presence was verified in MX-015A and bounded BSR reads. Retain each
field's observation version; an omitted field is not a source null. No person,
free-text failure narrative, href, or guessed failure hierarchy is retained.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from src.adapters.maximo.actual_dates import clock, version

TEXT_FIELDS = ("failurecode", "problemcode", "parent", "origrecordclass", "origrecordid", "woclass")
BOOL_FIELDS = ("istask", "haschildren", "hasfollowupwork", "downtime")
FIELDS = (*TEXT_FIELDS, *BOOL_FIELDS, "faildate")
# Only these additional fields are needed on the existing lifecycle detail GET.
DETAIL_FIELDS = ("problemcode", "faildate", "parent", "origrecordclass", "origrecordid", "hasfollowupwork")
IDENTITY_FIELDS = ("wonum", "assetnum", "siteid", "orgid")


def observation(name: str, value: Any, *, present: bool = True) -> dict[str, Any]:
    if not present:
        return {"state": "UNAVAILABLE", "value": None}
    if value is None or value == "":
        return {"state": "MISSING", "value": None}
    if name == "faildate":
        item = clock(value)
        # Keep bounded clock text for diagnosis; NAIVE is never assumed UTC.
        return {"state": item["state"], "value": item["normalized"], "original": item["original"] if isinstance(item["original"], str) else None}
    if name in BOOL_FIELDS:
        if isinstance(value, bool):
            return {"state": "OBSERVED", "value": value}
        if isinstance(value, (str, int)) and str(value).strip().lower() in {"true", "false", "1", "0"}:
            return {"state": "OBSERVED", "value": str(value).strip().lower() in {"true", "1"}}
    elif name in TEXT_FIELDS and isinstance(value, str) and len(value) <= 200:
        return {"state": "OBSERVED" if value.strip() else "MISSING", "value": value.strip() or None}
    return {"state": "INVALID", "value": None}


def evidence(member: Mapping[str, Any]) -> dict[str, Any]:
    stamp = clock(member.get("changedate"))["normalized"]
    return {
        "schema_version": 1,
        "semantics": "SOURCE_FIELDS_ONLY",
        "identity": {key: member.get(key) if isinstance(member.get(key), str) else None for key in IDENTITY_FIELDS},
        "fields": {key: {**observation(key, member.get(key), present=key in member), "source_changed_at": stamp} for key in FIELDS},
    }


def merge_evidence(previous: Any, incoming: dict[str, Any]) -> dict[str, Any]:
    """Preserve omitted observations, but honor explicit nulls and invalid data."""
    result = deepcopy(incoming)
    if not isinstance(previous, dict) or previous.get("identity") != incoming.get("identity"):
        return result
    previous_fields = previous.get("fields")
    if not isinstance(previous_fields, dict):
        return result
    for key in FIELDS:
        old = previous_fields.get(key)
        if isinstance(old, dict) and result["fields"][key]["state"] == "UNAVAILABLE":
            result["fields"][key] = deepcopy(old)
    return result


def projected_evidence(member: Mapping[str, Any]) -> dict[str, Any]:
    """Revalidate allowlist, scope, identity, types and per-field observation time."""
    if "collector_reliability_evidence" not in member:
        return evidence(member)
    result = evidence({key: value for key, value in member.items() if key not in FIELDS})
    proof = member.get("collector_reliability_evidence")
    if (not isinstance(proof, dict) or proof.get("schema_version") != 1
            or proof.get("identity") != result["identity"]
            or result["identity"]["siteid"] != "BSR" or result["identity"]["orgid"] != "IP"):
        return result
    current = version(member.get("changedate"))
    fields = proof.get("fields")
    if not isinstance(fields, dict):
        return result
    for key in FIELDS:
        item = fields.get(key)
        if not isinstance(item, dict):
            continue
        state = item.get("state")
        checked = observation(key, item.get("original") if key == "faildate" else item.get("value"), present=state != "UNAVAILABLE")
        # Invalid non-scalars were deliberately not retained.
        redacted_invalid = state == "INVALID" and item.get("value") is None and item.get("original") is None
        observed = version(item.get("source_changed_at"))
        if ((checked["state"] == state or redacted_invalid) and checked["value"] == item.get("value")
                and current is not None and observed is not None and observed <= current):
            result["fields"][key] = {**checked, "state": state, "source_changed_at": item["source_changed_at"]}
    return result
