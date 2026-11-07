"""HTTP client for the maximo-collector API (the cockpit's data source).

The cockpit is a pure dashboard: it never talks to Maximo. It pulls
contract-shaped views from the collector and rebuilds its own domain models.
Field names match reliability-data-contracts on both sides, so conversion is
mechanical (parse ISO datetimes, rebuild the quarantined sources block).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Mapping

import requests

from src.domain.equipment import Equipment, MaximoEquipmentSource
from src.domain.item import Item
from src.domain.labor import Labor
from src.domain.person import Person
from src.domain.service_request import ServiceRequest
from src.domain.work_order import WorkOrder


class CollectorClientError(RuntimeError):
    """Collector API unreachable or returned an unexpected payload."""


@dataclass(frozen=True)
class PullResult:
    """Normalized collector rows plus explicit traversal completion metadata."""

    items: list
    complete: bool
    pages: int
    rows_seen: int
    duplicate_ids: int = 0
    invalid_ids: int = 0
    overlap_ids: int = 0
    stop_reason: str | None = None
    conversion_errors: int = 0

    def __iter__(self):
        return iter(self.items)

    def __len__(self) -> int:
        return len(self.items)


def _dt(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _build(model_cls: type, view: Mapping[str, Any], *, datetime_fields: tuple[str, ...]):
    kwargs: dict[str, Any] = {}
    for f in getattr(model_cls, "__dataclass_fields__", {}).values():
        if f.name not in view:
            continue
        value = view[f.name]
        if f.name in datetime_fields:
            value = _dt(value)
        kwargs[f.name] = value
    return model_cls(**kwargs)


def equipment_from_view(view: Mapping[str, Any]) -> Equipment:
    # Map collector assetnum → cockpit id
    view = dict(view)
    if "id" not in view and "assetnum" in view:
        view["id"] = view.pop("assetnum")
    equipment = _build(
        Equipment,
        {k: v for k, v in view.items() if k != "sources"},
        datetime_fields=(
            "installed_at", "status_changed_at", "source_changed_at",
        ),
    )
    sources = view.get("sources") or {}
    maximo = sources.get("maximo")
    if isinstance(maximo, Mapping):
        maximo = dict(maximo)
        for key in ("installdate", "changedate"):
            if key in maximo:
                maximo[key] = _dt(maximo[key])
        known = set(MaximoEquipmentSource.__dataclass_fields__)
        unknown = {k: v for k, v in maximo.items() if k not in known}
        if unknown:
            merged = dict(maximo.get("extra") or {})
            merged.update(unknown)
            maximo["extra"] = merged
        equipment.maximo_source = MaximoEquipmentSource(
            **{k: v for k, v in maximo.items() if k in known}
        )
    return equipment


def work_order_from_view(view: Mapping[str, Any]) -> WorkOrder:
    # Map collector worktype → cockpit work_type
    view = dict(view)
    if "id" not in view and "wonum" in view:
        view["id"] = view.pop("wonum")
    if "work_type" not in view and "worktype" in view:
        view["work_type"] = view.pop("worktype")
    if view.get("parent_wo") is not None:
        # Older Collector versions used an unverified PCTASKID mapping. Keep
        # the legacy observation quarantined, never as a resolved relationship.
        sources = dict(view["sources"]) if isinstance(view.get("sources"), Mapping) else {}
        maximo = dict(sources["maximo"]) if isinstance(sources.get("maximo"), Mapping) else {}
        hierarchy = dict(maximo["hierarchy"]) if isinstance(maximo.get("hierarchy"), Mapping) else {}
        hierarchy.update(schema_version=1, parent_wo_state="UNKNOWN", legacy_parent_wo=view["parent_wo"])
        maximo["hierarchy"] = hierarchy
        sources["maximo"] = maximo
        view["sources"] = sources
    view["parent_wo"] = None
    return _build(
        WorkOrder,
        dict(view),
        datetime_fields=(
            "reported_at", "source_changed_at", "status_changed_at",
            "scheduled_start", "scheduled_finish", "target_completion",
        ),
    )


def service_request_from_view(view: Mapping[str, Any]) -> ServiceRequest:
    return _build(
        ServiceRequest,
        dict(view),
        datetime_fields=(
            "reported_at", "source_changed_at", "affected_at",
            "actual_start", "actual_finish", "target_start", "target_finish",
            "status_changed_at",
        ),
    )


def person_from_view(view: Mapping[str, Any]) -> Person:
    return _build(Person, dict(view), datetime_fields=("status_changed_at",))


def item_from_view(view: Mapping[str, Any]) -> Item:
    return _build(Item, dict(view), datetime_fields=("status_changed_at",))


def labor_from_view(view: Mapping[str, Any]) -> Labor:
    return _build(Labor, dict(view), datetime_fields=())


# resource -> (endpoint, view->domain builder, watermark column)
RESOURCES: dict[str, tuple[str, Callable[[Mapping], Any], bool]] = {
    "equipment": ("/equipment", equipment_from_view, True),
    "workorder": ("/work-orders", work_order_from_view, True),
    "servicerequest": ("/service-requests", service_request_from_view, True),
    "person": ("/persons", person_from_view, True),
    "item": ("/items", item_from_view, True),
    "labor": ("/labor", labor_from_view, False),  # no watermark by design
}


class CollectorClient:
    """Read-only HTTP client for the maximo-collector API."""

    def __init__(self, base_url: str = "http://127.0.0.1:8002", timeout_seconds: int = 60):
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout_seconds

    def pull(
        self,
        resource: str,
        *,
        changed_since: datetime | None = None,
        limit: int = 1000,
        max_pages: int = 1000,
    ) -> PullResult:
        """Pull pages as normalized models and report whether traversal completed."""
        if resource not in RESOURCES:
            raise CollectorClientError(f"unknown resource: {resource}")
        if limit < 1 or max_pages < 1:
            raise CollectorClientError("collector pagination limits must be positive")
        endpoint, builder, has_watermark = RESOURCES[resource]
        params: dict[str, Any] = {"limit": limit, "offset": 0}
        if has_watermark and changed_since is not None:
            params["changed_since"] = changed_since.isoformat()
        items: list[Any] = []
        seen_ids: set[str] = set()
        seen_page_fingerprints: set[str] = set()
        previous_page_ids: set[str] = set()
        pages = 0
        rows_seen = 0
        duplicate_ids = 0
        invalid_ids = 0
        overlap_ids = 0
        conversion_errors = 0
        while True:
            request_fingerprint = _pagination_fingerprint(endpoint, params)
            if request_fingerprint in seen_page_fingerprints:
                return PullResult(
                    items, False, pages, rows_seen, duplicate_ids, invalid_ids,
                    overlap_ids, "repeated_request_page", conversion_errors,
                )
            if pages >= max_pages:
                return PullResult(
                    items, False, pages, rows_seen, duplicate_ids, invalid_ids,
                    overlap_ids, "max_pages", conversion_errors,
                )
            seen_page_fingerprints.add(request_fingerprint)
            try:
                resp = requests.get(self._base_url + endpoint, params=params, timeout=self._timeout)
                resp.raise_for_status()
                payload = resp.json()
            except requests.RequestException as error:
                raise CollectorClientError(
                    f"collector API {endpoint} failed (is mxcollector serve running on "
                    f"{self._base_url}?): {error}"
                ) from error
            except ValueError as error:
                raise CollectorClientError(f"collector API {endpoint} returned non-JSON: {error}") from error
            if not isinstance(payload, list):
                raise CollectorClientError(f"collector API {endpoint} returned {type(payload).__name__}, expected list")
            pages += 1
            rows_seen += len(payload)
            page_ids: set[str] = set()
            for view in payload:
                try:
                    item = builder(view)
                except Exception:  # noqa: BLE001 — one bad row must not abort a pull
                    conversion_errors += 1
                    continue
                item_id = str(getattr(item, "id", "") or "").strip()
                if resource == "workorder" and not item_id.upper().startswith("BSR"):
                    invalid_ids += 1
                    continue
                if item_id:
                    page_ids.add(item_id)
                    if item_id in seen_ids:
                        duplicate_ids += 1
                        continue
                    seen_ids.add(item_id)
                items.append(item)
            overlap_ids += len(page_ids & previous_page_ids)
            page_fingerprint = _content_fingerprint(page_ids)
            if page_fingerprint in seen_page_fingerprints:
                return PullResult(
                    items, False, pages, rows_seen, duplicate_ids, invalid_ids,
                    overlap_ids, "repeated_content_page", conversion_errors,
                )
            seen_page_fingerprints.add(page_fingerprint)
            previous_page_ids = page_ids
            if len(payload) < limit:
                break
            params["offset"] += limit
        return PullResult(
            items, True, pages, rows_seen, duplicate_ids, invalid_ids, overlap_ids,
            None, conversion_errors,
        )

    def health(self) -> bool:
        try:
            resp = requests.get(self._base_url + "/health", timeout=self._timeout)
            return resp.status_code == 200
        except requests.RequestException:
            return False


def _pagination_fingerprint(endpoint: str, params: Mapping[str, Any]) -> str:
    safe = "&".join(f"{key}={params[key]}" for key in sorted(params))
    return hashlib.sha256(f"{endpoint}?{safe}".encode("utf-8")).hexdigest()[:16]


def _content_fingerprint(ids: set[str]) -> str:
    safe = "\0".join(sorted(ids))
    return hashlib.sha256(safe.encode("utf-8")).hexdigest()[:16]
