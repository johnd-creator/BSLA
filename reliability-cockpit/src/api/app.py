"""FastAPI application exposing normalized reliability data.

Endpoints mirror reliability-data-contracts field names; no raw Maximo/PI
payloads escape this layer. Read-only views over the cockpit store.
"""

from __future__ import annotations

import logging

from fastapi import Depends, FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from src.repositories import get_database
from src.repositories.database import Database
from src.repositories.store import CockpitStore
from src.api.reliability import router as reliability_router
from src.services.kpi import WORK_ORDER_KPI_BLOCKERS

LOG = logging.getLogger(__name__)


class EquipmentView(BaseModel):
    id: str
    name: str | None = None
    location_id: str | None = None
    equipment_class: str | None = None
    unit: str | None = None
    status: str | None = None
    status_description: str | None = None
    is_running: bool | None = None
    parent_id: str | None = None
    ancestor_id: str | None = None
    downtime_total_hours: float | None = None


class WorkOrderView(BaseModel):
    id: str
    equipment_id: str | None = None
    status: str | None = None
    work_type: str | None = None
    description: str | None = None
    reported_at: str | None = None
    downtime_hours: float | None = None
    failure_code: str | None = None


class WorkOrderPage(BaseModel):
    """Bounded work-order page; the browser never receives the whole table."""

    items: list[WorkOrderView]
    total: int
    offset: int
    limit: int
    has_more: bool


class ReliabilityKpiView(BaseModel):
    readiness: str | None = None
    blockers: list[str] = Field(default_factory=list)
    id: str
    equipment_id: str | None = None
    metric: str | None = None
    value: float | None = None
    unit: str | None = None
    period_start: str | None = None
    period_end: str | None = None


class SyncStatusView(BaseModel):
    object_structure: str
    last_changedate: str | None = None
    last_synced_at: str | None = None
    rows_seen: int | None = None


def _store(db: Database = Depends(get_database)) -> CockpitStore:
    return CockpitStore(db)


def create_app() -> FastAPI:
    app = FastAPI(title="Reliability Cockpit API", version="0.1.0")

    @app.get("/health", tags=["system"])
    def health() -> dict:
        return {"status": "ok"}

    @app.get("/equipment", response_model=list[EquipmentView], tags=["equipment"])
    def list_equipment(
        equipment_class: str | None = None,
        limit: int = Query(100, ge=1, le=1000),
        store: CockpitStore = Depends(_store),
    ) -> list[EquipmentView]:
        items = store.list_equipment(limit=limit)
        if equipment_class:
            items = [i for i in items if i.equipment_class == equipment_class]
        return [
            EquipmentView(
                id=i.id,
                name=i.name,
                location_id=i.location_id,
                equipment_class=i.equipment_class,
                unit=i.unit,
                status=i.status,
                status_description=i.status_description,
                is_running=i.is_running,
                parent_id=i.parent_id,
                ancestor_id=i.ancestor_id,
                downtime_total_hours=i.downtime_total_hours,
            )
            for i in items
        ]

    @app.get("/equipment/{equipment_id}", response_model=EquipmentView, tags=["equipment"])
    def get_equipment(equipment_id: str, store: CockpitStore = Depends(_store)) -> EquipmentView:
        i = store.get_equipment(equipment_id)
        if i is None:
            raise HTTPException(status_code=404, detail="equipment not found")
        return EquipmentView(
            id=i.id,
            name=i.name,
            location_id=i.location_id,
            equipment_class=i.equipment_class,
            unit=i.unit,
            status=i.status,
            status_description=i.status_description,
            is_running=i.is_running,
            parent_id=i.parent_id,
            ancestor_id=i.ancestor_id,
            downtime_total_hours=i.downtime_total_hours,
        )

    @app.get("/work-orders", response_model=WorkOrderPage, tags=["work-orders"])
    def list_work_orders(
        equipment_id: str | None = None,
        offset: int = Query(0, ge=0),
        limit: int = Query(50, ge=1, le=200),
        store: CockpitStore = Depends(_store),
        status: str | None = None,
    ) -> WorkOrderPage:
        count_kwargs = {"equipment_id": equipment_id}
        list_kwargs = {"equipment_id": equipment_id, "offset": offset, "limit": limit}
        if status:
            count_kwargs["status"] = status
            list_kwargs["status"] = status
        total = store.count_work_orders(**count_kwargs)
        items = store.list_work_orders(**list_kwargs)
        views = [
            WorkOrderView(
                id=i.id,
                equipment_id=i.equipment_id,
                status=i.status,
                work_type=i.work_type,
                description=i.description,
                reported_at=i.reported_at.isoformat() if i.reported_at else None,
                downtime_hours=i.downtime_hours,
                failure_code=i.failure_code,
            )
            for i in items
        ]
        return WorkOrderPage(
            items=views,
            total=total,
            offset=offset,
            limit=limit,
            has_more=offset + len(views) < total,
        )

    @app.get("/work-orders/statuses", response_model=list[str], tags=["work-orders"])
    def list_work_order_statuses(store: CockpitStore = Depends(_store)) -> list[str]:
        return store.list_work_order_statuses()

    @app.get("/kpis/{equipment_id}/{metric}", response_model=ReliabilityKpiView, tags=["kpis"])
    def get_kpi(equipment_id: str, metric: str, store: CockpitStore = Depends(_store)) -> ReliabilityKpiView:
        kpi = store.get_latest_kpi(equipment_id, metric)
        if kpi is None:
            raise HTTPException(status_code=404, detail="kpi not computed yet; run sync+kpi stage")
        # Existing persisted snapshots also came from the unsupported WO-only basis.
        blockers = WORK_ORDER_KPI_BLOCKERS.get((kpi.metric or metric).upper(), ())
        return ReliabilityKpiView(
            id=kpi.id,
            equipment_id=kpi.equipment_id,
            metric=kpi.metric,
            value=None if blockers else kpi.value,
            readiness="NOT_READY" if blockers else None,
            blockers=list(blockers),
            unit=kpi.unit,
            period_start=kpi.period_start.isoformat() if kpi.period_start else None,
            period_end=kpi.period_end.isoformat() if kpi.period_end else None,
        )

    @app.get("/sync/status", response_model=SyncStatusView, tags=["sync"])
    def sync_status(object_structure: str, store: CockpitStore = Depends(_store)) -> SyncStatusView:
        from src.repositories.models import SyncCursorOrm

        with store._db.session() as session:
            row = session.get(SyncCursorOrm, object_structure)
            if row is None:
                raise HTTPException(status_code=404, detail="sync cursor not found")
            return SyncStatusView(
                object_structure=row.object_structure,
                last_changedate=row.last_changedate.isoformat() if row.last_changedate else None,
                last_synced_at=row.last_synced_at.isoformat() if row.last_synced_at else None,
                rows_seen=row.rows_seen,
            )

    # FastAPI's installed version inserts an internal ``_IncludedRouter``
    # sentinel when ``include_router`` is called.  The legacy test/helpers
    # iterate ``app.routes`` and expect concrete routes, so extend the app
    # router with the already-prefixed, read-only routes directly.
    app.router.routes.extend(reliability_router.routes)
    return app
