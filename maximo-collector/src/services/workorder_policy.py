"""Versioned WO lifecycle acquisition. Source business data is always read-only."""
from __future__ import annotations
from dataclasses import replace
from src.services.workorder_age import eligibility, window
import re
from src.adapters.maximo.actual_dates import version
from src.adapters.maximo.oslc_client import OslcError

TERMINAL = frozenset({"CLOSE", "CAN", "CANCEL"})
SUMMARY_FIELDS = ("wonum", "workorderid", "siteid", "orgid", "assetnum", "status", "status_description", "reportdate", "changedate", "statusdate")

def normalized_status(value):
    return str(value or "").strip().upper()

def acquire_work_order(client, store, config, summary):
    bounds = window()
    age = eligibility(summary, bounds)
    if age != "AGE_ELIGIBLE":
        return "unchanged", age
    identity = str(summary.get("wonum") or "").strip()
    status = normalized_status(summary.get("status"))
    if not identity or not status or not re.fullmatch(r"[A-Za-z0-9_./ -]+", identity):
        raise OslcError("invalid WO identity or status")
    prior = store.work_order_snapshot(identity)
    change = version(summary.get("changedate"))
    if change is None:
        raise OslcError("missing source version")
    old_change = version(prior.get("source_changed_at")) if prior else None
    old_status = normalized_status(prior.get("status")) if prior else None
    if old_change and change < old_change:
        return "unchanged", "OLDER_OBSERVATION"
    needs_status_confirmation = prior is not None and old_change == change and old_status != status
    same_version = old_change == change and old_status == status
    frozen = prior is not None and old_status in TERMINAL and old_status == status
    if frozen:
        return "unchanged", "TERMINAL_FROZEN"
    cancelled = status in {"CAN", "CANCEL"}
    need_detail = not cancelled and (prior is None or not same_version)
    raw = dict(summary)
    mode = "STATUS_ONLY"
    if need_detail or needs_status_confirmation:
        fields = ([f for f in config.select if status == "CLOSE" or f not in ("actstart", "actfinish")]
                  if need_detail else list(SUMMARY_FIELDS))
        # Exact-WO equality and these fields are documented in owning knowledge.
        # No date predicate or guessed resource href is used.
        rows = list(client.iterate("mxwodetail", where=f'siteid="BSR" and wonum="{identity}"',
            required_scope='siteid="BSR"', select=fields, page_size=1, max_pages=2,
            identity_field="wonum", strict_members=True))
        if len(rows) != 1:
            raise OslcError("exact WO detail did not return one row")
        raw = dict(rows[0])
        age = eligibility(raw, bounds)
        if age != "AGE_ELIGIBLE":
            return "unchanged", age
        if raw.get("reportdate") != summary.get("reportdate"):
            raise OslcError("WO report date changed during detail confirmation")
        if any(str(raw.get(k) or "").strip() != str(summary.get(k) or "").strip()
               for k in ("wonum", "siteid", "orgid", "assetnum")):
            raise OslcError("WO detail identity or scope differs from summary")
        confirmed_statusdate = version(raw.get("statusdate"))
        summary_statusdate = version(summary.get("statusdate"))
        if needs_status_confirmation and (confirmed_statusdate is None or summary_statusdate is None):
            raise OslcError("same-version status confirmation requires zoned status timestamps")
        if (version(raw.get("changedate")) != change or normalized_status(raw.get("status")) != status
                or version(raw.get("statusdate")) != version(summary.get("statusdate"))):
            raise OslcError("WO changed while confirming source observation; retry next cycle")
        mode = "DETAIL" if need_detail else "STATUS_ONLY"
    # A server may ignore oslc.select. Never store unsolicited open-state clocks.
    if status != "CLOSE" or mode == "STATUS_ONLY":
        raw.pop("actstart", None); raw.pop("actfinish", None)
    entity = config.mapper(raw)
    source = dict(entity.sources or {})
    maximo = dict(source.get("maximo") or {})
    maximo["collection"] = {"schema_version": 1, "mode": mode, "status": status,
        "source_changed_at": change.isoformat(), "terminal_detail_frozen": frozen,
        "same_version_status_confirmed": needs_status_confirmation,
        "confirmed_status_changed_at": version(raw.get("statusdate")).isoformat() if needs_status_confirmation else None,
        "prior_status": old_status if needs_status_confirmation else None,
        "actual_collection": "CLOSE_DETAIL" if status == "CLOSE" and mode == "DETAIL" else "NOT_REQUESTED"}
    source["maximo"] = maximo
    outcome = store.upsert_for("work_order", replace(entity, sources=source))
    return outcome, "DETAIL" if need_detail else ("TERMINAL_FROZEN" if frozen else "UNCHANGED_SUMMARY")
