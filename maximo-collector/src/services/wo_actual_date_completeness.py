"""Status-neutral, evidence-derived WO date completeness (no acquisition).

Status only adds an explanation/review priority. It never supplies clocks or
changes the evidence classification. Matrices retain every original status.
"""
from __future__ import annotations

from collections import Counter

from src.adapters.maximo.actual_dates import clock, evidence, version
from src.canonical_identity import canonical_id

STATES = ("ACTUAL_DATES_AVAILABLE", "START_ONLY", "FINISH_ONLY", "SOURCE_CONFIRMED_EMPTY",
          "SOURCE_NOT_YET_VERIFIED", "COLLECTOR_PROJECTION_GAP", "SOURCE_TIMESTAMP_INVALID")


def _verified_fields(proof, identity, changed):
    if not isinstance(proof, dict) or proof.get("schema_version") != 1 or proof.get("identity") != identity or changed is None:
        return {}
    result = {}
    for key in ("actstart", "actfinish"):
        item = proof.get("fields", {}).get(key, {})
        state = item.get("state")
        checked = clock(item.get("original"), present=state != "UNAVAILABLE")
        observed = version(item.get("source_changed_at"))
        valid_state = state == checked["state"] or (state == "INVALID" and item.get("original") is None)
        if (valid_state and item.get("normalized") == checked["normalized"]
                and observed is not None and (observed == changed or state == "VALID" and observed < changed)):
            result[key] = {**checked, "state": state}
    return result


def classify_dates(record, *, source=None, legacy_sources=None):
    """Classify a Mart row using exact identity/version-bound observations.

    Invalid -> verified pipeline gap -> date presence -> confirmed empty ->
    unverified. Availability and missing-reason flags remain independent, so
    START_ONLY does not conceal why the finish field is missing.
    """
    vendor = (record.get("sources") or {}).get("maximo", {})
    provenance = record.get("provenance") or {}
    wonum = provenance.get("source_record_id") or vendor.get("wonum")
    asset_ref = record.get("equipment_id")
    changed = version(record.get("source_changed_at"))
    identity = {"wonum": wonum, "assetnum": vendor.get("assetnum"), "siteid": "BSR", "orgid": "IP"}
    scoped = (isinstance(wonum, str) and isinstance(identity["assetnum"], str)
              and record.get("site_code") == "BSR" and record.get("organization_code") == "IP"
              and record.get("canonical_id") == canonical_id("maintenance_event", "MXWODETAIL", wonum, "BSR", "IP")
              and asset_ref == canonical_id("asset", "MXASSET", identity["assetnum"], "BSR", "IP"))
    retained = _verified_fields(vendor.get("actual_dates"), identity, changed) if scoped else {}
    legacy = _verified_fields((legacy_sources or {}).get("maximo", {}).get("actual_dates"), identity, changed) if scoped else {}
    observed = {}
    mismatch = False
    if source is not None:
        mismatch = not scoped or any(source.get(k) != v for k, v in identity.items()) or version(source.get("changedate")) != changed
        if not mismatch:
            observed = _verified_fields(evidence(source), identity, changed)
    proof = {**retained, **legacy, **observed}
    available = {key: record.get(field) is not None for key, field in (("actstart", "actual_start"), ("actfinish", "actual_finish"))}
    missing = [key for key in available if not available[key]]
    invalid = [key for key, item in proof.items() if item["state"] in ("INVALID", "NAIVE")]
    gap = [key for key in missing if any(fields.get(key, {}).get("state") == "VALID" for fields in (retained, legacy, observed))]
    confirmed = [key for key in missing if proof.get(key, {}).get("state") == "MISSING"]
    unverified = [key for key in missing if key not in gap and key not in confirmed and key not in invalid]
    start, finish = available["actstart"], available["actfinish"]
    if invalid:
        state = "SOURCE_TIMESTAMP_INVALID"
    elif gap:
        state = "COLLECTOR_PROJECTION_GAP"
    elif start and finish:
        state = "ACTUAL_DATES_AVAILABLE"
    elif start:
        state = "START_ONLY"
    elif finish:
        state = "FINISH_ONLY"
    elif len(confirmed) == 2:
        state = "SOURCE_CONFIRMED_EMPTY"
    else:
        state = "SOURCE_NOT_YET_VERIFIED"
    status = record.get("status")
    advanced = status in ("COMP", "CLOSE") and bool(missing)
    note = None
    if status in ("WAPPR", "WMATL"):
        note = "Actual dates may not yet be recorded; execution state is not established by this status."
    elif advanced:
        note = "Data-completeness review: actual dates are missing; status does not establish date evidence."
    return {"status": status, "state": state, "actual_start_available": start, "actual_finish_available": finish,
            "source_confirmed_null_fields": confirmed, "unverified_missing_fields": unverified,
            "collector_projection_gap_fields": gap, "invalid_timestamp_fields": invalid,
            "source_identity_or_version_mismatch": mismatch, "advanced_status_missing_dates": advanced, "status_note": note}


def status_date_matrix(classifications):
    groups = {}
    for result in classifications:
        row = groups.setdefault(result["status"], Counter())
        start, finish = result["actual_start_available"], result["actual_finish_available"]
        row["total"] += 1
        row["both_available"] += int(start and finish)
        row["start_only"] += int(start and not finish)
        row["finish_only"] += int(finish and not start)
        row["both_missing"] += int(not start and not finish)
        row["source_confirmed_null"] += bool(result["source_confirmed_null_fields"])
        row["unverified_missing"] += bool(result["unverified_missing_fields"])
        row["collector_projection_loss"] += bool(result["collector_projection_gap_fields"])
        row["invalid_or_ambiguous"] += bool(result["invalid_timestamp_fields"])
        row["identity_or_version_mismatch"] += result["source_identity_or_version_mismatch"]
        row["advanced_status_missing_dates"] += result["advanced_status_missing_dates"]
        row[result["state"]] += 1
    return [{"status": status, **dict(row)} for status, row in sorted(groups.items(), key=lambda item: (item[0] is not None, str(item[0])))]
