"""Manual bounded exact-ID enrichment; never relabel a WO."""
from datetime import datetime, timezone
import re
import time
from src.adapters.maximo.mappers import equipment_from_payload
from src.adapters.maximo.oslc_client import ASSET_DETAIL_FIELDS, OslcPaginationLimitError
from src.repositories.asset_references import AssetReferenceStore, RUN_OBJECT
from src.services.sync import SyncStats


def collect_asset_references(client, store, *, checks=None, limit=10, scheduled=False,
                             max_seconds=45, monotonic=time.monotonic):
    if not 1 <= limit <= 50 or not 1 <= max_seconds <= 180:
        raise ValueError("asset checks require 1..50 requests and 1..180 seconds")
    checks = checks or AssetReferenceStore(store._db)
    now = datetime.now(timezone.utc)
    result = {"checked": 0, "inserted": 0, "updated": 0, "not_found_in_scope": 0,
              "errors": 0, "requests": 0, "stop_reason": "BOUNDED_QUEUE_CHECKED",
              "full_source_baseline_complete": False}
    with store.work_order_recovery_lock() as acquired:
        if not acquired:
            return {**result, "stop_reason": "SOURCE_BUSY"}
        if scheduled and not checks.due(now):
            return {**result, "stop_reason": "NOT_DUE"}
        # The run marker is local schedule/audit state, never a source watermark.
        stats = SyncStats(RUN_OBJECT, mode="targeted", started_at=now)
        start = monotonic()
        before = client.request_telemetry["business_requests"]
        with client.bounded_requests(limit):
            for identity in checks.candidates(now, limit):
                if monotonic() - start >= max_seconds:
                    result["stop_reason"] = "TIME_BUDGET"; break
                if client.request_telemetry["business_requests"] - before >= limit:
                    result["stop_reason"] = "REQUEST_BUDGET"; break
                outcome = "SOURCE_ERROR"
                try:
                    # Percent, quotes and backslashes could alter OSLC predicates.
                    if not re.fullmatch(r"[A-Za-z0-9_./ -]{1,60}", identity):
                        outcome = "UNSUPPORTED_ID"
                        raise ValueError("unsupported exact asset identity")
                    rows = list(client.iterate("mxapiasset",
                        where=f'siteid="BSR" and eq11="CS01" and assetnum="{identity}"',
                        required_scope='siteid="BSR"', select=list(ASSET_DETAIL_FIELDS),
                        page_size=2, max_pages=1, identity_field="assetnum",
                        strict_members=True, allow_resource_links=False))
                    if not rows:
                        outcome = "NOT_FOUND_IN_SCOPE"
                        result["not_found_in_scope"] += 1
                    else:
                        if len(rows) != 1:
                            outcome = "AMBIGUOUS"; raise ValueError("non-unique source asset")
                        raw = rows[0]
                        if raw.get("assetnum") != identity:
                            outcome = "IDENTITY_MISMATCH"; raise ValueError("source identity mismatch")
                        if (raw.get("siteid"), raw.get("orgid"), raw.get("eq11")) != ("BSR", "IP", "CS01"):
                            outcome = "SCOPE_MISMATCH"; raise ValueError("source scope mismatch")
                        outcome = "MAPPING_ERROR"
                        equipment = equipment_from_payload(raw)
                        saved = store.upsert_equipment(equipment)
                        store.record_equipment_status(equipment)
                        if saved in ("inserted", "updated"):
                            result[saved] += 1
                        outcome = "FOUND_EXACT"
                    result["checked"] += 1
                    checks.mark(identity, outcome, datetime.now(timezone.utc))
                except Exception as error:
                    if isinstance(error, OslcPaginationLimitError): outcome = "AMBIGUOUS"
                    result["errors"] += 1
                    result["stop_reason"] = outcome
                    result["error_class"] = type(error).__name__
                    checks.mark(identity, outcome, datetime.now(timezone.utc))
                    break  # auth, permission, transport and unexpected shape never storm/retry
        result["requests"] = client.request_telemetry["business_requests"] - before
        stats.rows_seen = result["checked"]
        stats.upserted = result["inserted"] + result["updated"]
        stats.skipped = result["not_found_in_scope"]
        stats.errors = result["errors"]
        stats.mode = "targeted_partial" if stats.errors or result["stop_reason"] != "BOUNDED_QUEUE_CHECKED" else "targeted"
        stats.finished_at = datetime.now(timezone.utc)
        store.record_run(stats)
    return result
