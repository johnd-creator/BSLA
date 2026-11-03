"""Allowlisted WO clock evidence. Unknown zones are evidence, never UTC guesses."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone

FIELDS = {"actstart": "actual_start", "actfinish": "actual_finish"}


def clock(value, *, present=True):
    original = value if isinstance(value, (str, int, float, bool)) and len(str(value)) <= 128 else None
    result = {"state": "UNAVAILABLE", "original": original, "normalized": None}
    if not present:
        return result
    if value is None or value == "":
        result["state"] = "MISSING"
        return result
    try:
        if not isinstance(original, str) or "T" not in original:
            raise ValueError("not a timestamp")
        parsed = datetime.fromisoformat(original.replace("Z", "+00:00"))
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            result["state"] = "NAIVE"
        else:
            result.update(state="VALID", normalized=parsed.isoformat())
    except (ValueError, TypeError, OverflowError):
        result["state"] = "INVALID"
    return result


def version(value):
    """Source observations require an explicit zone. DB datetimes use UTC."""
    if isinstance(value, datetime):
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value
    parsed = clock(value)
    return datetime.fromisoformat(parsed["normalized"]) if parsed["state"] == "VALID" else None


def evidence(member):
    changed = clock(member.get("changedate"))["normalized"]
    fields = {}
    for key in FIELDS:
        fields[key] = dict(clock(member.get(key), present=key in member), source_changed_at=changed)
    return {"schema_version": 1,
            "identity": {key: member.get(key) for key in ("wonum", "assetnum", "siteid", "orgid")},
            "fields": fields}


def retained_values(proof, wonum, assetnum, changed_at):
    """Re-validate scoped identity, clock text and field version before replay."""
    if not isinstance(proof, dict) or proof.get("schema_version") != 1:
        return {}
    if proof.get("identity") != {"wonum": wonum, "assetnum": assetnum, "siteid": "BSR", "orgid": "IP"}:
        return {}
    current = version(changed_at)
    result = {}
    for key in FIELDS:
        item = proof.get("fields", {}).get(key, {})
        checked = clock(item.get("original"))
        observed = version(item.get("source_changed_at"))
        if (current is not None and observed is not None and observed <= current
                and checked["state"] == item.get("state") == "VALID"
                and checked["normalized"] == item.get("normalized")):
            result[key] = item["original"]
    return result


def merge_evidence(previous, incoming):
    """Missing/invalid observations cannot retract previously valid clocks."""
    result = deepcopy(incoming)
    if not previous or previous.get("identity") != incoming.get("identity"):
        return result
    for key in FIELDS:
        old = previous.get("fields", {}).get(key, {})
        new = result.get("fields", {}).get(key, {})
        if old.get("state") != "VALID":
            continue
        if new.get("state") != "VALID":
            result["fields"][key] = deepcopy(old)
        elif (version(old.get("source_changed_at")) == version(new.get("source_changed_at"))
              and version(old.get("normalized")) != version(new.get("normalized"))):
            raise ValueError("WO actual date conflict at the same source version")
    return result


def projected_evidence(member):
    """Local synthetic NULLs cannot establish an observed source null."""
    if "collector_actual_dates" not in member:
        return evidence(member)
    result = evidence({key: value for key, value in member.items() if key not in FIELDS})
    proof = member.get("collector_actual_dates")
    if not isinstance(proof, dict) or proof.get("schema_version") != 1 or proof.get("identity") != result["identity"]:
        return result
    current = version(member.get("changedate"))
    for key in FIELDS:
        item = proof.get("fields", {}).get(key, {})
        state = item.get("state")
        checked = clock(item.get("original"), present=state != "UNAVAILABLE")
        # A capped/non-scalar invalid original is deliberately not retained.
        redacted_invalid = state == "INVALID" and item.get("original") is None
        observed = version(item.get("source_changed_at"))
        if ((checked["state"] == state or redacted_invalid)
                and checked["normalized"] == item.get("normalized")
                and current is not None and observed is not None and observed <= current):
            result["fields"][key] = {**checked, "state": state, "source_changed_at": item["source_changed_at"]}
    return result
