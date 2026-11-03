"""FastAPI app: read-only contract-shaped views + sync triggers.

Consumers (the reliability cockpit) pull from these endpoints; they never
touch Maximo. Field names follow reliability-data-contracts; vendor values
stay quarantined under ``sources``.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query
from src.adapters.maximo.mappers import (
    equipment_from_payload,
    item_from_payload,
    labor_from_payload,
    person_from_payload,
    service_request_from_payload,
    work_order_from_payload,
)
from src.adapters.maximo.oslc_client import ASSET_DETAIL_FIELDS
from src.config import MaximoConfig
from src.repositories import models as orm
from src.repositories.database import Database, get_database
from src.repositories.store import CollectorStore
from src.services.sync import ObjectSyncConfig, SyncService
from src.api.data_explorer import router as data_explorer_router

WORK_ORDER_SELECT = (
    "wonum", "workorderid", "assetnum", "location", "status", "status_description",
    "worktype", "woclass", "description", "reportdate", "changedate", "statusdate",
    "schedstart", "schedfinish", "actstart", "actfinish", "targcompdate", "estdur", "downtime", "wopriority",
    "wopriority_description", "reportedby", "supervisor", "lead", "failurecode", "istask",
    "pctaskid", "haschildren", "estlabcost", "estmatcost", "actlabcost", "actmatcost",
    "actlabhrs", "siteid", "orgid", "seksi", "bu", "jumlahhidup", "jumlahmati", "luasareatanam",
)
PERSON_SELECT = ("personid", "displayname", "firstname", "status", "statusdate", "locationorg")
ASSET_SELECT = ASSET_DETAIL_FIELDS

# object_structure -> (entity_name, mapper, watermark_field, order_by, changed_column)
OBJECTS: dict[str, dict[str, Any]] = {
    # MXAPIASSET is the preferred verified asset structure. MXASSET remains
    # available for explicit backwards-compatible runs, but is not part of
    # the default list so the same equipment is not synced twice.
    "mxapiasset": dict(
        entity="equipment", mapper=equipment_from_payload,
        watermark="changedate", order_by="-changedate", changed_column="source_changed_at",
        orm=orm.EquipmentOrm, scope='siteid="BSR"', compare_column="source_changed_at",
        required_field="eq11", select=ASSET_SELECT,
    ),
    "mxasset": dict(
        entity="equipment", mapper=equipment_from_payload,
        watermark="changedate", order_by="-changedate", changed_column="source_changed_at",
        orm=orm.EquipmentOrm, scope='siteid="BSR"', compare_column="source_changed_at",
        required_field="eq11",
    ),
    "mxwodetail": dict(
        entity="work_order", mapper=work_order_from_payload,
        watermark="changedate", order_by="-changedate", changed_column="source_changed_at",
        orm=orm.WorkOrderOrm, scope='siteid="BSR"', compare_column="source_changed_at",
        prefix_field="wonum", select=WORK_ORDER_SELECT, batch_size=100, page_size=25,
        prefix_query=True,
        watermark_query=False, max_pages=20, recent_work_orders=True,
        cursor_requires_zero_errors=True,
    ),
    "mxapisr": dict(
        entity="service_request", mapper=service_request_from_payload,
        watermark="changedate", order_by="-changedate", changed_column="source_changed_at",
        orm=orm.ServiceRequestOrm, scope='siteid="BSR"', compare_column="source_changed_at",
    ),
    "mxperson": dict(
        entity="person", mapper=person_from_payload,
        watermark="statusdate", order_by="-statusdate", changed_column="status_changed_at",
        orm=orm.PersonOrm, scope='locationorg="IP"', compare_column="status_changed_at", batch_size=100,
        select=PERSON_SELECT,
    ),
    "mxitem": dict(
        entity="item", mapper=item_from_payload,
        watermark="statusdate", order_by="-statusdate", changed_column="status_changed_at",
        orm=orm.ItemOrm, scope='site="BSR"', compare_column="status_changed_at", batch_size=100,
    ),
    "mxapilabor": dict(
        entity="labor", mapper=labor_from_payload,
        watermark=None, order_by=None, changed_column=None,
        orm=orm.LaborOrm, scope='worksite="BSR"', compare_column=None, batch_size=100,
    ),
}
# alias: friendly names
ALIASES = {
    "equipment": "mxapiasset", "workorder": "mxwodetail", "work-orders": "mxwodetail",
    "servicerequest": "mxapisr", "person": "mxperson", "item": "mxitem", "labor": "mxapilabor",
}


def resolve_object(name: str) -> str:
    key = name.lower()
    if key in OBJECTS:
        return key
    if key in ALIASES:
        return ALIASES[key]
    raise KeyError(name)


def sync_config_for(object_structure: str) -> ObjectSyncConfig:
    canonical = resolve_object(object_structure)
    spec = OBJECTS[canonical]
    runtime_config = MaximoConfig.from_environment()
    return ObjectSyncConfig(
        object_structure=canonical,
        entity_name=spec["entity"],
        mapper=spec["mapper"],
        watermark_field=spec["watermark"],
        order_by=spec["order_by"],
        scope_clause=spec["scope"],
        compare_column=spec["compare_column"],
        prefix_field=spec.get("prefix_field"),
        allowed_prefixes=runtime_config.wo_prefixes if spec.get("prefix_field") else (),
        required_values=(
            (spec["required_field"], runtime_config.equipment_unit),
        ) if spec.get("required_field") else (),
        batch_size=spec.get("batch_size", 1),
        select=spec.get("select", ()),
        page_size=spec.get("page_size"),
        max_pages=spec.get("max_pages", 1000),
        prefix_query=spec.get("prefix_query", True),
        watermark_query=spec.get("watermark_query", True),
        recent_work_orders=spec.get("recent_work_orders", False),
        cursor_requires_zero_errors=spec.get("cursor_requires_zero_errors", True),
    )


def _store(db: Database = Depends(get_database)) -> CollectorStore:
    return CollectorStore(db)


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _parse_optional_datetime(value: str | None, name: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"{name} must be ISO-8601") from exc


def _serialize(row: Any) -> dict:
    out: dict[str, Any] = {}
    for column in row.__table__.columns:
        value = getattr(row, column.name)
        # The ORM keeps the database column name ``class_label`` to avoid a
        # Python keyword; the public contract calls this field ``class``.
        key = "class" if column.name == "class_label" else column.name
        out[key] = _iso(value) if isinstance(value, datetime) else value
    return out


def create_app() -> FastAPI:
    app = FastAPI(title="Maximo Collector API", version="0.1.0")
    app.include_router(data_explorer_router)
    runtime_config = MaximoConfig.from_environment()
    wo_prefixes = runtime_config.wo_prefixes
    equipment_unit = runtime_config.equipment_unit

    @app.get("/health", tags=["system"])
    def health() -> dict:
        return {"status": "ok"}

    def _list_endpoint(
        orm_cls,
        changed_column: str | None,
        *,
        filter_columns: dict[str, str],
        search_columns: tuple[str, ...],
        fixed_filters: dict[str, str] | None = None,
        prefix_column: str | None = None,
        prefixes: tuple[str, ...] = (),
    ):
        def endpoint(
            q: str | None = Query(None, description="Case-insensitive search"),
            status: str | None = Query(None),
            work_type: str | None = Query(None),
            equipment_id: str | None = Query(None),
            location_id: str | None = Query(None),
            unit: str | None = Query(None),
            equipment_class: str | None = Query(None),
            manufacturer: str | None = Query(None),
            vendor: str | None = Query(None),
            priority: str | None = Query(None),
            item_type: str | None = Query(None),
            issue_unit: str | None = Query(None),
            order_unit: str | None = Query(None),
            location_org: str | None = Query(None),
            work_site: str | None = Query(None),
            person_id: str | None = Query(None),
            changed_since: str | None = Query(None, description="ISO-8601; only rows changed after this"),
            changed_until: str | None = Query(None, description="ISO-8601; only rows changed up to this"),
            offset: int = Query(0, ge=0),
            limit: int = Query(1000, ge=1, le=10000),
            store: CollectorStore = Depends(_store),
        ) -> list[dict]:
            since = _parse_optional_datetime(changed_since, "changed_since")
            until = _parse_optional_datetime(changed_until, "changed_until")
            requested = {
                "status": status, "work_type": work_type, "equipment_id": equipment_id,
                "location_id": location_id, "unit": unit, "equipment_class": equipment_class,
                "manufacturer": manufacturer, "vendor": vendor, "priority": priority,
                "item_type": item_type, "issue_unit": issue_unit, "order_unit": order_unit,
                "location_org": location_org, "work_site": work_site, "person_id": person_id,
            }
            exact_filters = {
                filter_columns[key]: value for key, value in requested.items()
                if value and key in filter_columns
            }
            # Fixed source scope always wins over a client-provided filter.
            exact_filters.update(fixed_filters or {})
            rows = store.list_rows(
                orm_cls,
                changed_column=changed_column,
                changed_since=since,
                changed_until=until,
                offset=offset,
                limit=limit,
                exact_filters=exact_filters,
                search=q,
                search_columns=search_columns,
                prefix_column=prefix_column,
                prefixes=prefixes,
            )
            return [_serialize(r) for r in rows]
        return endpoint

    app.get("/equipment", tags=["equipment"])(_list_endpoint(
        orm.EquipmentOrm, "source_changed_at",
        filter_columns={"status": "status", "unit": "unit", "equipment_class": "equipment_class", "location_id": "location_id", "manufacturer": "manufacturer", "vendor": "vendor"},
        search_columns=("id", "name", "description", "location_id", "unit", "equipment_class", "status", "manufacturer", "vendor"),
        fixed_filters={"unit": equipment_unit},
    ))

    @app.get("/equipment/{asset_id}/status-history", tags=["equipment"])
    def equipment_status_history(
        asset_id: str,
        limit: int = Query(100, ge=1, le=1000),
        store: CollectorStore = Depends(_store),
    ) -> list[dict]:
        return [_serialize(r) for r in store.list_equipment_status_history(asset_id, limit)]
    app.get("/work-orders", tags=["work-orders"])(_list_endpoint(
        orm.WorkOrderOrm, "source_changed_at",
        filter_columns={"status": "status", "work_type": "work_type", "equipment_id": "equipment_id", "location_id": "location_id", "priority": "priority"},
        search_columns=("id", "equipment_id", "location_id", "status", "work_type", "description", "reported_by", "supervisor", "lead"),
        prefix_column="id", prefixes=wo_prefixes,
    ))
    app.get("/service-requests", tags=["service-requests"])(_list_endpoint(
        orm.ServiceRequestOrm, "source_changed_at",
        filter_columns={"status": "status", "work_type": "work_type", "equipment_id": "equipment_id", "location_id": "location_id", "priority": "internal_priority"},
        search_columns=("id", "equipment_id", "location_id", "status", "work_type", "description", "reported_by", "reported_by_name"),
    ))
    app.get("/persons", tags=["persons"])(_list_endpoint(
        orm.PersonOrm, "status_changed_at",
        filter_columns={"status": "status", "location_org": "location_org"},
        search_columns=("id", "display_name", "first_name", "status", "location_org"),
    ))
    app.get("/items", tags=["items"])(_list_endpoint(
        orm.ItemOrm, "status_changed_at",
        filter_columns={"status": "status", "item_type": "item_type", "issue_unit": "issue_unit", "order_unit": "order_unit"},
        search_columns=("id", "description", "status", "item_type", "issue_unit", "order_unit", "item_set_id"),
    ))
    app.get("/labor", tags=["labor"])(_list_endpoint(
        orm.LaborOrm, None,
        filter_columns={"status": "status", "work_site": "work_site", "person_id": "person_id"},
        search_columns=("id", "person_id", "status", "status_description", "work_site"),
    ))

    @app.get("/sync/status", tags=["sync"])
    def sync_status(store: CollectorStore = Depends(_store)) -> dict:
        return {
            obj: {
                "watermark": _iso(store.get_cursor(obj)),
                "rows": store.count(
                    spec["orm"],
                    exact_filters={"unit": equipment_unit}
                    if spec["entity"] == "equipment" else {},
                    prefix_column="id" if spec["entity"] == "work_order" else None,
                    prefixes=wo_prefixes if spec["entity"] == "work_order" else (),
                ),
            }
            for obj, spec in OBJECTS.items()
        }

    @app.get("/collect-runs", tags=["sync"])
    def collect_runs(
        limit: int = Query(20, ge=1, le=100),
        store: CollectorStore = Depends(_store),
    ) -> list[dict]:
        return [_serialize(r) for r in store.list_runs(limit)]

    @app.get("/stats", tags=["system"])
    def stats(store: CollectorStore = Depends(_store)) -> dict:
        last_run = store.latest_run()
        return {
            "site": "BSR",
            "org": "IP",
            "read_only": True,
            "resources": {
                spec["entity"]: store.count(
                    spec["orm"],
                    exact_filters={"unit": equipment_unit}
                    if spec["entity"] == "equipment" else {},
                    prefix_column="id" if spec["entity"] == "work_order" else None,
                    prefixes=wo_prefixes if spec["entity"] == "work_order" else (),
                )
                for key, spec in OBJECTS.items()
                if key != "mxasset"
            },
            "last_run": _serialize(last_run) if last_run else None,
        }

    @app.post("/sync/{name}", tags=["sync"])
    def trigger_sync(name: str, store: CollectorStore = Depends(_store)) -> dict:
        """Trigger one object's sync (login + GET-only)."""
        from src.adapters.maximo.auth import MaximoAuth
        from src.adapters.maximo.oslc_client import OslcClient

        try:
            object_structure = resolve_object(name)
        except KeyError:
            raise HTTPException(status_code=404, detail=f"unknown object: {name}")
        config = MaximoConfig.from_environment()
        client = OslcClient(config, MaximoAuth(config))
        service = SyncService(client, store, site_id=config.site_id)
        stats = service.sync(sync_config_for(object_structure))
        return {
            "object_structure": stats.object_structure,
            "mode": stats.mode,
            "rows_seen": stats.rows_seen,
            "upserted": stats.upserted,
            "skipped": stats.skipped,
            "errors": stats.errors,
            "watermark": _iso(stats.watermark),
            "complete": stats.complete,
            "pagination_error": stats.pagination_error,
            "duplicate_ids": stats.duplicate_ids,
            "recency": stats.recency,
        }

    return app
