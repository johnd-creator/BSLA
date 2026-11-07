"""Bounded newest-first WO acquisition; no speculative date predicates."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from src.adapters.maximo.oslc_client import (
    OslcError, OslcPaginationError, OslcPaginationLimitError,
    OslcRequestBudgetExceeded, oslc_timestamp,
)
from src.services.sync import SyncStats
from src.services.workorder_age import eligibility, window
from src.services.workorder_policy import SUMMARY_FIELDS, acquire_work_order

LOG = logging.getLogger(__name__)


def sync_recent_work_orders(client, store, config, *, recovery_floor=None):
    """Advance only after ordered exhaustion or a fully validated cursor boundary.

    Missing routine cursors require explicit recovery; a recovery floor is a
    traversal boundary, never a cursor seed. Partial rows replay on restart.
    Entire pages are validated before writes/early stop, including out-of-prefix
    timestamps. No fallback to unordered traversal when ordering is rejected.
    """
    if (config.entity_name != "work_order" or config.object_structure != "mxwodetail"
            or config.order_by != "-changedate" or config.watermark_field != "changedate"
            or not config.allowed_prefixes or config.scope_clause != 'siteid="BSR"'
            or not config.cursor_requires_zero_errors):
        raise ValueError("WO recency requires verified ordering, BSR scope and strict cursor safety")
    cursor = store.get_cursor(config.object_structure)
    stats = SyncStats(config.object_structure, mode="incremental" if cursor else "full")
    age_bounds = window(stats.started_at)
    evidence = stats.recency
    evidence.update(age_cutoff=age_bounds[0].isoformat(), age_years=4, age_timezone="Asia/Jakarta",
                    age_field="reportdate", age_excluded=0, age_unknown=0,
                    age_source_filter="NOT_VERIFIED_LOCAL_GUARD_ONLY")
    evidence.update(cursor_before=_iso(cursor), cursor_after=_iso(cursor),
                    source_rows_read=0, prefix_accepted=0, prefix_skipped=0,
                    newest_source_change=None, oldest_source_change=None,
                    pages=0, validated_pages=0, requests=0, stop_reason=None)
    evidence.update(recovery_floor=_iso(recovery_floor), page_cap=config.max_pages,
                    request_budget=config.request_limit, page_size=config.page_size)
    if cursor is None and recovery_floor is None:
        return _operational_stop(store, stats, "BOOTSTRAP_REQUIRED")
    cutoff = recovery_floor if recovery_floor is not None else cursor
    page_limit = config.max_pages
    request_limit = config.request_limit
    if config.work_order_lifecycle and recovery_floor is None:
        page_limit = store.work_order_catchup_pages(cursor, config.max_pages, config.catchup_page_ceiling)
        request_limit = max(config.request_limit, min(400, page_limit * 2))
    evidence.update(page_cap=page_limit, request_budget=request_limit, detail_fetched=0,
                    terminal_detail_skipped=0, source_scope_verified=0, source_scope_unknown=0,
                    source_scope_excluded=0, source_total=None, source_total_state="NOT_VERIFIED",
                    resume_strategy="IDEMPOTENT_REPLAY_BOUNDED_ADAPTIVE_BUDGET",
                    coverage_state="BOUNDED_ORDERED_TRAVERSAL_NOT_TOTAL_RECONCILIATION")
    before_requests = client.request_telemetry["business_requests"]
    newest = oldest = previous = candidate = None
    identities = set()
    page_signatures = set()
    prior_page_identities = set()
    reason = "SOURCE_EXHAUSTED"
    where = config.scope_clause
    if config.prefix_query:
        values = ','.join(f'"{p}%"' for p in config.allowed_prefixes)
        where += f' and wonum in [{values}]'
    try:
        with client.bounded_requests(request_limit):
            for page in client.iterate_pages(
                config.object_structure, where=where, required_scope=config.scope_clause,
                select=list(SUMMARY_FIELDS) if config.work_order_lifecycle else list(dict.fromkeys((*config.select, "reportdate"))), order_by="-changedate",
                page_size=config.page_size, max_pages=page_limit,
                identity_field="wonum", strict_members=True,
            ):
                evidence["pages"] += 1
                stats.rows_seen += len(page)
                evidence["prefix_accepted"] += sum(
                    str(raw.get("wonum") or "").strip().upper().startswith(config.allowed_prefixes)
                    for raw in page
                )
                evidence["prefix_skipped"] = stats.rows_seen - evidence["prefix_accepted"]
                changes = []
                # Validate the whole page, rather than trusting its first old row.
                for raw in page:
                    change = oslc_timestamp(raw.get("changedate"))
                    if change is None or change.tzinfo is None:
                        raise OslcError("missing or invalid change timestamp")
                    changes.append(change)
                    newest = change if newest is None else max(newest, change)
                    oldest = change if oldest is None else min(oldest, change)
                    if previous is not None and change > previous:
                        reason = "ORDER_VIOLATION"
                        raise OslcError("source did not honor descending changedate")
                    previous = change
                    if (str(raw.get("siteid") or "").upper() != "BSR"
                            or str(raw.get("orgid") or "").upper() != "IP"):
                        if not raw.get("siteid") or not raw.get("orgid"):
                            evidence["source_scope_unknown"] += 1
                        else:
                            evidence["source_scope_excluded"] += 1
                        reason = "SCOPE_ERROR"
                        raise OslcError("source row violates BSR/IP scope")
                page_identities = {str(raw.get("wonum") or "").strip() for raw in page}
                if page_identities & prior_page_identities:
                    reason = "UNSTABLE_PAGINATION"
                    raise OslcError("WO identity repeated across pages; coverage cannot be reconciled")
                prior_page_identities.update(page_identities)
                signature = tuple((str(raw.get("wonum") or ""), change.isoformat()) for raw,change in zip(page,changes))
                if signature and signature in page_signatures:
                    reason = "REPEATED_PAGE"
                    raise OslcError("repeated WO page content")
                page_signatures.add(signature)
                evidence["validated_pages"] += 1
                evidence["source_scope_verified"] += len(page)
                boundary = False
                for raw, change in zip(page, changes):
                    prefix_match = str(raw.get("wonum") or "").strip().upper().startswith(config.allowed_prefixes)
                    if change < cutoff:
                        boundary = True
                        stats.skipped += 1
                        continue
                    if not prefix_match:
                        stats.skipped += 1
                        continue
                    age = eligibility(raw, age_bounds)
                    if age != "AGE_ELIGIBLE":
                        stats.skipped += 1
                        evidence["age_excluded" if age == "AGE_EXCLUDED" else "age_unknown"] += 1
                        if age == "AGE_EXCLUDED":
                            candidate = change if candidate is None else max(candidate, change)
                        continue
                    try:
                        entity = config.mapper(raw)
                        identity = str(getattr(entity, "id", "") or "").strip()
                        if not identity.upper().startswith(config.allowed_prefixes):
                            raise ValueError("invalid mapped WO identity")
                        if identity in identities:
                            stats.duplicate_ids += 1
                            stats.skipped += 1
                            continue
                        identities.add(identity)
                        if config.work_order_lifecycle:
                            outcome, policy = acquire_work_order(client, store, config, raw)
                            if policy == "AGE_EXCLUDED": evidence["age_excluded"] += 1
                            if policy == "AGE_UNKNOWN": evidence["age_unknown"] += 1
                            if not policy.startswith("AGE_") and str(raw.get("status") or "").upper() not in {"CLOSE", "CAN", "CANCEL"}:
                                store.mark_work_order_status_checked(identity)
                            if policy == "DETAIL": evidence["detail_fetched"] += 1
                            if policy == "TERMINAL_FROZEN": evidence["terminal_detail_skipped"] += 1
                            if outcome == "unchanged":
                                stats.unchanged += 1; stats.skipped += 1
                            else:
                                stats.upserted += 1
                                if outcome in ("inserted", "updated"):
                                    setattr(stats, outcome, getattr(stats, outcome) + 1)
                        elif store.is_unchanged(config.entity_name, identity, config.compare_column, change):
                            stats.unchanged += 1
                            stats.skipped += 1
                        else:
                            outcome = store.upsert_for(config.entity_name, entity)
                            stats.upserted += 1
                            if outcome in ("inserted", "updated", "unchanged"):
                                setattr(stats, outcome, getattr(stats, outcome) + 1)
                        candidate = change if candidate is None else max(candidate, change)
                    except Exception:
                        reason = "MAPPING_OR_STORE_ERROR"
                        raise
                if boundary:
                    reason = "RECOVERY_FLOOR_REACHED" if recovery_floor is not None else (
                        "CURSOR_REACHED" if candidate and candidate > cursor else "NO_NEW_ROWS"
                    )
                    break
    except Exception as error:
        stats.complete = False
        stats.mode = "partial"
        stats.errors += 1
        stats.pagination_error = type(error).__name__
        if reason == "MAPPING_OR_STORE_ERROR":
            pass  # Nested detail errors must never become a head-pagination fallback.
        elif isinstance(error, OslcPaginationLimitError):
            reason = "PAGE_LIMIT"
        elif isinstance(error, OslcPaginationError):
            reason = "PAGINATION_ERROR"
        elif isinstance(error, OslcRequestBudgetExceeded):
            reason = "REQUEST_BUDGET"
        elif reason == "SOURCE_EXHAUSTED":
            reason = "SOURCE_ERROR"
        LOG.warning("WO recency partial reason=%s error_class=%s", reason, type(error).__name__)
    head_rows_seen = stats.rows_seen
    # Unstable offset pages cannot establish coverage, but exact active-WO reads
    # remain useful. Continue only for local traversal guards, never after an
    # authentication, permission, source, scope, mapping or storage failure.
    poll_permitted = stats.complete or reason in {
        "PAGE_LIMIT", "UNSTABLE_PAGINATION", "REPEATED_PAGE",
    }
    if config.work_order_lifecycle and recovery_floor is None and poll_permitted:
        from src.services.workorder_status_poll import poll_active_work_orders
        remaining = request_limit - (client.request_telemetry["business_requests"] - before_requests)
        if remaining >= 2:
            try:
                with client.bounded_requests(remaining):
                    poll = poll_active_work_orders(client, store, config, identities)
                evidence["active_status_poll"] = poll
                evidence["age_excluded"] += poll.get("age_excluded", 0)
                evidence["age_unknown"] += poll.get("age_unknown", 0)
                evidence["detail_fetched"] += poll["detail_fetched"]
                stats.rows_seen += poll["checked"]
                stats.upserted += poll["inserted"] + poll["updated"]
                stats.inserted += poll["inserted"]; stats.updated += poll["updated"]
                stats.unchanged += poll["unchanged"]; stats.skipped += poll["unchanged"]
                if poll["errors"]:
                    raise OslcError("bounded active status reconciliation failed")
            except Exception as error:
                if stats.complete:
                    reason = "ACTIVE_STATUS_CHECK_FAILED"
                stats.complete = False
                stats.mode = "partial"
                stats.errors += 1
                stats.pagination_error = stats.pagination_error or type(error).__name__
                evidence["active_status_poll_error_class"] = type(error).__name__
        else:
            evidence["active_status_poll"] = {"checked": 0, "stop_reason": "SHARED_REQUEST_BUDGET",
                                            "entire_active_population_verified": False}
    if config.work_order_lifecycle and recovery_floor is None and reason == "PAGE_LIMIT":
        next_limit = min(config.catchup_page_ceiling, page_limit * 2)
        if next_limit > page_limit:
            store.save_work_order_catchup_pages(cursor, next_limit)
        evidence["next_page_cap"] = next_limit
        evidence["catchup_ceiling_reached"] = next_limit == page_limit
    if evidence["age_unknown"]:
        stats.complete = False
        stats.mode = "partial"
        if reason in {"SOURCE_EXHAUSTED", "CURSOR_REACHED", "NO_NEW_ROWS", "RECOVERY_FLOOR_REACHED"}:
            reason = "AGE_UNKNOWN"
    if recovery_floor is not None:
        evidence["recovery_floor_reached"] = stats.complete and oldest is not None and oldest <= recovery_floor
        if stats.complete and (not evidence["recovery_floor_reached"] or candidate is None):
            return _finish_unreconciled(client, store, stats, evidence, before_requests, newest, oldest)
        # Changes after this run started must remain eligible on the next cycle.
        if candidate is not None:
            candidate = min(candidate, stats.started_at)
    if candidate is not None:
        candidate = min(candidate, stats.started_at)
    # No changes to a pre-existing watermark on any incomplete traversal.
    after = max(cursor, candidate) if cursor and candidate else candidate or cursor
    if stats.complete and after is not None:
        try:
            store.set_cursor(config.object_structure, after, stats.rows_seen)
        except Exception as error:
            stats.complete = False
            stats.mode = "partial"
            stats.errors += 1
            stats.pagination_error = type(error).__name__
            reason = "CURSOR_STORE_ERROR"
            after = cursor
    else:
        after = cursor
    stats.watermark = after
    stats.finished_at = datetime.now(timezone.utc)
    evidence.update(pages=evidence["pages"],
                    source_rows_read=head_rows_seen, cursor_after=_iso(after),
                    newest_source_change=_iso(newest), oldest_source_change=_iso(oldest),
                    requests=client.request_telemetry["business_requests"] - before_requests,
                    stop_reason=reason, complete=stats.complete)
    store.record_run(stats)
    LOG.info("WO recency %s", json.dumps(evidence, sort_keys=True))
    return stats


def _iso(value):
    return value.isoformat() if value is not None else None


def _operational_stop(store, stats, reason):
    stats.complete = False
    stats.mode = "partial"
    stats.finished_at = datetime.now(timezone.utc)
    stats.recency.update(stop_reason=reason, complete=False)
    store.record_run(stats)
    LOG.warning("WO recency %s", json.dumps(stats.recency, sort_keys=True))
    return stats


def _finish_unreconciled(client, store, stats, evidence, before_requests, newest, oldest):
    evidence.update(newest_source_change=_iso(newest), oldest_source_change=_iso(oldest),
                    pages=evidence["pages"],
                    requests=client.request_telemetry["business_requests"] - before_requests,
                    source_rows_read=stats.rows_seen)
    return _operational_stop(store, stats, "RECOVERY_FLOOR_NOT_REACHED")


def bootstrap_recent_work_orders(client, store, config):
    """Explicit recovery, serialized and anchored before any source/local upsert.

    The durable floor lives in existing collect_run evidence, not sync_cursor.
    A retry reuses it even if partial progress raised the local WO maximum.
    """
    if not config.prefix_query or not 1 <= (config.page_size or 25) <= 25:
        raise ValueError("bootstrap requires verified prefix query and page size 1..25")
    if not 1 <= config.max_pages <= 1000 or not 1 <= config.request_limit <= 2000:
        raise ValueError("bootstrap requires explicit finite page/request ceilings")
    with store.work_order_recovery_lock() as acquired:
        if not acquired:
            return _operational_stop(store, SyncStats(config.object_structure), "BOOTSTRAP_BUSY")
        cursor = store.get_cursor(config.object_structure)
        if cursor is not None:
            stats = SyncStats(config.object_structure, watermark=cursor)
            stats.recency.update(cursor_before=_iso(cursor), cursor_after=_iso(cursor), requests=0, pages=0)
            return _operational_stop(store, stats, "BOOTSTRAP_NOT_REQUIRED")
        floor = store.prepare_work_order_recovery_floor()
        if floor is None or floor.tzinfo is None or floor > datetime.now(timezone.utc):
            stats = SyncStats(config.object_structure)
            stats.recency.update(cursor_before=None, cursor_after=None, requests=0, pages=0,
                                 recovery_floor=_iso(floor))
            return _operational_stop(store, stats, "BOOTSTRAP_BLOCKED")
        return sync_recent_work_orders(client, store, config, recovery_floor=floor)
