"""Exact-cohort WO date recovery; no schedule, cursor, source or schema writes.

Functions accept existing owning services. Planning is read-only. Acquisition
is explicit GET-only, resumable and capped at ten identities. apply_cohort and
rollback_cohort are operational writes: their use requires separate owner
approval of the immutable plan plus fresh private backup/restore evidence.
They never create a database or table. Tests use disposable SQLite only.
"""
from __future__ import annotations

import copy
import dataclasses
import hashlib
import json
import re
from datetime import datetime, timezone

from sqlalchemy import text

from src.adapters.maximo.actual_dates import evidence, merge_evidence, version
from src.adapters.maximo.canonical_mappers import maintenance_event_from_payload
from src.canonical_identity import canonical_id
from src.domain.models import WorkOrder
from src.repositories import models, mart_models
from src.repositories.store import CollectorStore
from src.services.local_mart_projector import _work_order_payload
from src.services.mart import MartWriter

SELECT = ("wonum", "assetnum", "siteid", "orgid", "status", "worktype", "actstart", "actfinish",
          "reportdate", "schedstart", "schedfinish", "changedate")
MAX_COHORT = 10


def seal(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=_json).encode()).hexdigest()


def _json(value):
    if isinstance(value, datetime):
        return version(value).astimezone(timezone.utc).isoformat()
    raise TypeError("unsupported recovery evidence")


def _snapshot(row):
    return {c.name: copy.deepcopy(getattr(row, c.name)) for c in row.__table__.columns}


def _validate_plan(plan):
    if plan.get("format") != "wo-actual-dates/1" or not 1 <= len(plan.get("cohort", [])) <= MAX_COHORT:
        raise ValueError("exact bounded cohort required")
    seen = set()
    for item in plan["cohort"]:
        wonum, asset = item["wonum"], item["assetnum"]
        if (not re.fullmatch(r"BSR[A-Za-z0-9/_-]{1,155}", wonum)
                or not re.fullmatch(r"[A-Za-z0-9/_-]{1,160}", asset)
                or wonum in seen or version(item.get("changedate")) is None
                or item.get("canonical_id") != canonical_id("maintenance_event", "MXWODETAIL", wonum, "BSR", "IP")):
            raise ValueError("invalid cohort identity or source version")
        seen.add(wonum)
    return plan


def plan_cohort(db, wonums):
    """Freeze registered WO identities and equal legacy/Mart source versions."""
    if not 1 <= len(wonums) <= MAX_COHORT or len(set(wonums)) != len(wonums):
        raise ValueError("one to ten unique exact WOs required")
    cohort = []
    with db.session() as session:
        for wonum in wonums:
            cid = canonical_id("maintenance_event", "MXWODETAIL", wonum, "BSR", "IP")
            local = session.get(models.WorkOrderOrm, wonum)
            mart = session.get(mart_models.MaintenanceEventMartOrm, cid)
            if local is None or mart is None:
                raise ValueError("legacy/Mart identity unresolved")
            asset = canonical_id("asset", "MXASSET", local.equipment_id, "BSR", "IP")
            if (mart.equipment_id != asset or session.get(mart_models.ReliabilityAssetRegistryMartOrm, asset) is None
                    or mart.site_code != "BSR" or mart.organization_code != "IP"
                    or version(local.source_changed_at) is None
                    or version(local.source_changed_at) != version(mart.source_changed_at)):
                raise ValueError("registered scope or source version conflict")
            needed = [key for key, field in (("actstart", "actual_start"), ("actfinish", "actual_finish"))
                      if getattr(mart, field) is None]
            if not needed:
                raise ValueError("cohort contains no missing clocks")
            cohort.append({"wonum": wonum, "assetnum": local.equipment_id, "canonical_id": cid,
                           "changedate": version(local.source_changed_at).isoformat(), "needed": needed})
    return _validate_plan({"format": "wo-actual-dates/1", "cohort": cohort})


def _observation(item, raw):
    if any(raw.get(k) != v for k, v in (("wonum", item["wonum"]), ("assetnum", item["assetnum"]),
                                      ("siteid", "BSR"), ("orgid", "IP"))):
        raise ValueError("source identity/scope mismatch")
    if version(raw.get("changedate")) != version(item["changedate"]):
        raise ValueError("source version changed; refresh through normal acquisition then replan")
    if any(value is not None and not isinstance(value, (str, int, float, bool)) for value in raw.values()):
        raise ValueError("source scalar evidence required")
    return {key: raw[key] for key in SELECT if key in raw}


def fetch_cohort(client, plan, *, completed=None, checkpoint=None):
    """No DB access. Checkpoint each validated response for bounded resume.

    Resume data is revalidated against this plan. Exceptions stop the run;
    retry is an explicit later invocation using the already saved responses.
    The existing OslcClient owns auth, request caps, rate and one re-login.
    """
    _validate_plan(plan)
    result = dict(completed or {})
    expected = {item["wonum"]: item for item in plan["cohort"]}
    if set(result) - set(expected):
        raise ValueError("resume evidence outside cohort")
    for wonum, raw in result.items():
        _observation(expected[wonum], raw)
    with client.bounded_requests(20):
        for item in plan["cohort"]:
            if item["wonum"] in result:
                continue
            # Full date/identity/version context only; no broad history traversal.
            rows = list(client.iterate("mxwodetail", where='siteid="BSR" and wonum="' + item["wonum"] + '"',
                        required_scope='siteid="BSR"', select=list(SELECT), page_size=2,
                        max_pages=1, identity_field="wonum"))
            if len(rows) != 1:
                raise ValueError("exact WO response cardinality mismatch")
            result[item["wonum"]] = _observation(item, rows[0])
            if checkpoint:
                checkpoint(copy.deepcopy(result))
    return result


def _database_guard(session, db, expected_database):
    dialect = db.engine.dialect.name
    if dialect == "sqlite":
        if expected_database != "disposable-sqlite":
            raise ValueError("disposable target acknowledgment required")
    elif dialect != "postgresql" or expected_database != "maximo_collector" or session.scalar(text("select current_database()")) != expected_database:
        raise ValueError("owning database identity mismatch")


def apply_cohort(db, plan, observations, *, expected_database, approved_plan_sha256, checkpoint=None):
    """One atomic co-located legacy/Mart transaction. Never advances cursors.

    The digest pins the reviewed cohort; it does not confer authorization.
    Operators must obtain explicit approval and verify private recovery gates.
    A subset of staged identities is supported for bounded retry/resume.
    """
    _validate_plan(plan)
    if seal(plan) != approved_plan_sha256 or not observations:
        raise ValueError("reviewed plan seal required")
    expected = {item["wonum"]: item for item in plan["cohort"]}
    if set(observations) - set(expected):
        raise ValueError("observations outside approved cohort")
    receipt = {"plan_sha256": seal(plan), "records": []}
    store, writer = CollectorStore(db), MartWriter(db)
    with db.session() as session:
        _database_guard(session, db, expected_database)
        if db.engine.dialect.name == "postgresql" and not callable(checkpoint):
            raise ValueError("durable private rollback checkpoint required before operational commit")
        for wonum in sorted(observations):
            item = expected[wonum]
            raw = _observation(item, observations[wonum])
            local = session.get(models.WorkOrderOrm, wonum, with_for_update=True)
            mart = session.get(mart_models.MaintenanceEventMartOrm, item["canonical_id"], with_for_update=True)
            if (local is None or mart is None or local.equipment_id != item["assetnum"]
                    or version(local.source_changed_at) != version(item["changedate"])
                    or version(mart.source_changed_at) != version(item["changedate"])):
                raise ValueError("local source version conflict; replan")
            asset = canonical_id("asset", "MXASSET", item["assetnum"], "BSR", "IP")
            if session.get(mart_models.ReliabilityAssetRegistryMartOrm, asset) is None:
                raise ValueError("registry scope no longer approved")
            before = {"legacy": _snapshot(local), "mart": _snapshot(mart)}
            sources = copy.deepcopy(local.sources or {})
            vendor = sources.setdefault("maximo", {})
            vendor["actual_dates"] = merge_evidence(vendor.get("actual_dates"), evidence(raw))
            domain_values = {f.name: (sources if f.name == "sources" else getattr(local, f.name))
                             for f in dataclasses.fields(WorkOrder)}
            # This is a proven DB version, not a naive source observation.
            # SQLite loses timezone metadata on legacy DateTime columns.
            domain_values["source_changed_at"] = version(local.source_changed_at)
            domain = WorkOrder(**domain_values)
            store.upsert_work_order_in_session(session, domain)
            payload = _work_order_payload(local)
            if payload is None:
                raise ValueError("unresolved parent asset")
            writer.recover_actual_dates(session, maintenance_event_from_payload(payload))
            session.flush()
            after = {"legacy": _snapshot(local), "mart": _snapshot(mart)}
            receipt["records"].append({"wonum": wonum, "canonical_id": item["canonical_id"],
                                       "before": before, "after_sha256": seal(after)})
        if checkpoint:
            checkpoint(copy.deepcopy(receipt))  # durable before commit; failure rolls back
        session.commit()
    return receipt


def rollback_cohort(db, receipt, *, expected_database):
    """CAS rollback: refuse to overwrite any later normal-worker observation.

    Receipt is private backup evidence, kept in memory or in an owner-only
    datetime-preserving archive. Never deserialize untrusted pickle data.
    """
    with db.session() as session:
        _database_guard(session, db, expected_database)
        rows = []
        for entry in sorted(receipt["records"], key=lambda e: e["wonum"]):
            local = session.get(models.WorkOrderOrm, entry["wonum"], with_for_update=True)
            mart = session.get(mart_models.MaintenanceEventMartOrm, entry["canonical_id"], with_for_update=True)
            if local is None or mart is None or seal({"legacy": _snapshot(local), "mart": _snapshot(mart)}) != entry["after_sha256"]:
                raise ValueError("rollback conflict; preserve newer evidence")
            rows.append((local, mart, entry["before"]))
        for local, mart, before in rows:
            local.sources = copy.deepcopy(before["legacy"]["sources"])
            for name in ("sources", "actual_start", "actual_finish", "mart_updated_at"):
                setattr(mart, name, copy.deepcopy(before["mart"][name]))
        session.commit()


def report_cohort(db, plan, *, source_observations=None):
    """Read-only status matrix; source samples/identifiers remain private."""
    from src.services.wo_actual_date_completeness import classify_dates, status_date_matrix
    _validate_plan(plan)
    observations = source_observations or {}
    expected = {item["wonum"] for item in plan["cohort"]}
    if set(observations) - expected:
        raise ValueError("report evidence outside cohort")
    classifications = []
    with db.session() as session:
        for item in plan["cohort"]:
            local = session.get(models.WorkOrderOrm, item["wonum"])
            mart = session.get(mart_models.MaintenanceEventMartOrm, item["canonical_id"])
            if local is None or mart is None:
                raise ValueError("report identity unresolved")
            classifications.append(classify_dates(_snapshot(mart), source=observations.get(item["wonum"]), legacy_sources=local.sources))
    return status_date_matrix(classifications)
