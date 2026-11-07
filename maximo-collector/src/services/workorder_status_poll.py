"""Bounded active-only status reconciliation independent of changedate ordering."""
from src.adapters.maximo.oslc_client import OslcError, OslcRequestBudgetExceeded
from src.services.workorder_policy import SUMMARY_FIELDS, acquire_work_order
import re

def poll_active_work_orders(client, store, config, excluded, max_checks=25):
    result = {"checked": 0, "updated": 0, "inserted": 0, "unchanged": 0, "detail_fetched": 0,
              "age_excluded": 0, "age_unknown": 0, "errors": 0, "stop_reason": "BOUNDED_ACTIVE_QUEUE_CHECKED", "entire_active_population_verified": False}
    candidates = store.active_work_order_candidates(config.allowed_prefixes, excluded, max_checks)
    for identity in candidates:
        telemetry = client.request_telemetry
        if telemetry.get("budget") is not None and telemetry["budget"] - telemetry["business_requests"] < 2:
            result["stop_reason"] = "SHARED_REQUEST_BUDGET"; break
        try:
            if not re.fullmatch(r"[A-Za-z0-9_./ -]+", identity):
                raise OslcError("unsupported exact-WO query identity")
            rows = list(client.iterate("mxwodetail", where=f'siteid="BSR" and wonum="{identity}"',
                required_scope='siteid="BSR"', select=list(SUMMARY_FIELDS), page_size=1, max_pages=2,
                identity_field="wonum", strict_members=True))
            if (len(rows) != 1 or rows[0].get("wonum") != identity
                    or rows[0].get("siteid") != "BSR" or rows[0].get("orgid") != "IP"):
                raise OslcError("active WO summary identity/scope unavailable")
            outcome, policy = acquire_work_order(client, store, config, rows[0])
            result["checked"] += 1
            if outcome in ("updated", "inserted", "unchanged"):
                result[outcome] += 1
            if policy == "DETAIL": result["detail_fetched"] += 1
            if policy == "AGE_EXCLUDED": result["age_excluded"] += 1
            if policy == "AGE_UNKNOWN": result["age_unknown"] += 1
            if not policy.startswith("AGE_"):
                store.mark_work_order_status_checked(identity)
        except OslcRequestBudgetExceeded:
            result["stop_reason"] = "SHARED_REQUEST_BUDGET"; break
        except Exception as error:
            result["errors"] += 1
            result["error_class"] = type(error).__name__
            result["stop_reason"] = "STATUS_CHECK_FAILED"
            store.mark_work_order_status_checked(identity, "FAILED")
            break  # no retry storm, especially on auth/permission errors
    return result
