"""SQLAlchemy ORM models — contract-shaped store.

Column names follow reliability-data-contracts (vendor-neutral snake_case);
raw Maximo values live in the JSONB ``sources`` column (quarantined).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.repositories.database import Base

_json = JSONB().with_variant(JSON(), "sqlite")


class EquipmentOrm(Base):
    __tablename__ = "equipment"

    id: Mapped[str] = mapped_column(String(60), primary_key=True)
    name: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    location_id: Mapped[str | None] = mapped_column(String(60))
    equipment_class: Mapped[str | None] = mapped_column(String(40))
    unit: Mapped[str | None] = mapped_column(String(40))
    status: Mapped[str | None] = mapped_column(String(30))
    status_description: Mapped[str | None] = mapped_column(Text)
    is_running: Mapped[bool | None] = mapped_column(Boolean)
    priority: Mapped[int | None] = mapped_column(Integer)
    parent_id: Mapped[str | None] = mapped_column(String(60))
    ancestor_id: Mapped[str | None] = mapped_column(String(60))
    has_children: Mapped[bool | None] = mapped_column(Boolean)
    failure_code: Mapped[str | None] = mapped_column(String(60))
    is_safety_critical: Mapped[bool | None] = mapped_column(Boolean)
    is_calibration: Mapped[bool | None] = mapped_column(Boolean)
    installed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    purchase_price: Mapped[float | None] = mapped_column(Float)
    replacement_cost: Mapped[float | None] = mapped_column(Float)
    total_cost: Mapped[float | None] = mapped_column(Float)
    downtime_total_hours: Mapped[float | None] = mapped_column(Float)
    manufacturer: Mapped[str | None] = mapped_column(Text)
    vendor: Mapped[str | None] = mapped_column(Text)
    sources: Mapped[dict | None] = mapped_column(_json)


class EquipmentStatusHistoryOrm(Base):
    """Append-only local history of asset status observations."""

    __tablename__ = "equipment_status_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    equipment_id: Mapped[str] = mapped_column(String(60), index=True)
    status: Mapped[str | None] = mapped_column(String(30))
    status_description: Mapped[str | None] = mapped_column(Text)
    is_running: Mapped[bool | None] = mapped_column(Boolean)
    status_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class WorkOrderOrm(Base):
    __tablename__ = "work_order"

    id: Mapped[str] = mapped_column(String(60), primary_key=True)
    equipment_id: Mapped[str | None] = mapped_column(String(60))
    location_id: Mapped[str | None] = mapped_column(String(60))
    status: Mapped[str | None] = mapped_column(String(30))
    status_description: Mapped[str | None] = mapped_column(Text)
    work_type: Mapped[str | None] = mapped_column(String(20))
    work_class: Mapped[str | None] = mapped_column(String(20))
    description: Mapped[str | None] = mapped_column(Text)
    reported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    scheduled_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    scheduled_finish: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    target_completion: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    estimated_duration_hours: Mapped[float | None] = mapped_column(Float)
    downtime_hours: Mapped[float | None] = mapped_column(Float)
    priority: Mapped[str | None] = mapped_column(String(20))
    priority_description: Mapped[str | None] = mapped_column(Text)
    reported_by: Mapped[str | None] = mapped_column(String(60))
    supervisor: Mapped[str | None] = mapped_column(String(60))
    lead: Mapped[str | None] = mapped_column(String(60))
    failure_code: Mapped[str | None] = mapped_column(String(60))
    is_task: Mapped[bool | None] = mapped_column(Boolean)
    parent_wo: Mapped[str | None] = mapped_column(String(60))
    has_children: Mapped[bool | None] = mapped_column(Boolean)
    estimated_labor_cost: Mapped[float | None] = mapped_column(Float)
    estimated_material_cost: Mapped[float | None] = mapped_column(Float)
    actual_labor_cost: Mapped[float | None] = mapped_column(Float)
    actual_material_cost: Mapped[float | None] = mapped_column(Float)
    actual_labor_hours: Mapped[float | None] = mapped_column(Float)
    sources: Mapped[dict | None] = mapped_column(_json)


class ServiceRequestOrm(Base):
    __tablename__ = "service_request"

    id: Mapped[str] = mapped_column(String(60), primary_key=True)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str | None] = mapped_column(String(30))
    status_description: Mapped[str | None] = mapped_column(Text)
    work_type: Mapped[str | None] = mapped_column(String(20))
    equipment_id: Mapped[str | None] = mapped_column(String(60))
    location_id: Mapped[str | None] = mapped_column(String(60))
    reported_by: Mapped[str | None] = mapped_column(String(60))
    reported_by_name: Mapped[str | None] = mapped_column(Text)
    reported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    affected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    actual_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    actual_finish: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    target_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    target_finish: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    internal_priority: Mapped[str | None] = mapped_column(String(20))
    reported_priority: Mapped[str | None] = mapped_column(String(20))
    actual_labor_hours: Mapped[float | None] = mapped_column(Float)
    actual_labor_cost: Mapped[float | None] = mapped_column(Float)
    risk_area_environment: Mapped[str | None] = mapped_column(Text)
    risk_area_process: Mapped[str | None] = mapped_column(Text)
    risk_area_human: Mapped[str | None] = mapped_column(Text)
    risk_area_reputation: Mapped[str | None] = mapped_column(Text)
    class_label: Mapped[str | None] = mapped_column(Text)
    status_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sources: Mapped[dict | None] = mapped_column(_json)


class PersonOrm(Base):
    __tablename__ = "person"

    id: Mapped[str] = mapped_column(String(60), primary_key=True)
    display_name: Mapped[str | None] = mapped_column(Text)
    first_name: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str | None] = mapped_column(String(30))
    status_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    location_org: Mapped[str | None] = mapped_column(String(20))


class ItemOrm(Base):
    __tablename__ = "item"

    id: Mapped[str] = mapped_column(String(60), primary_key=True)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str | None] = mapped_column(String(30))
    item_type: Mapped[str | None] = mapped_column(String(20))
    lot_type: Mapped[str | None] = mapped_column(String(20))
    issue_unit: Mapped[str | None] = mapped_column(String(20))
    order_unit: Mapped[str | None] = mapped_column(String(20))
    is_rotating: Mapped[bool | None] = mapped_column(Boolean)
    is_kit: Mapped[bool | None] = mapped_column(Boolean)
    is_crew: Mapped[bool | None] = mapped_column(Boolean)
    inspection_required: Mapped[bool | None] = mapped_column(Boolean)
    meter_name: Mapped[str | None] = mapped_column(String(60))
    item_set_id: Mapped[str | None] = mapped_column(String(30))
    status_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class LaborOrm(Base):
    __tablename__ = "labor"

    id: Mapped[str] = mapped_column(String(60), primary_key=True)
    person_id: Mapped[str | None] = mapped_column(String(60))
    status: Mapped[str | None] = mapped_column(String(30))
    status_description: Mapped[str | None] = mapped_column(Text)
    work_site: Mapped[str | None] = mapped_column(String(20))
    is_assigned: Mapped[bool | None] = mapped_column(Boolean)
    availability_factor: Mapped[float | None] = mapped_column(Float)
    reported_hours: Mapped[float | None] = mapped_column(Float)
    year_to_date_other_hours: Mapped[float | None] = mapped_column(Float)
    year_to_date_refused_hours: Mapped[float | None] = mapped_column(Float)


class SyncCursorOrm(Base):
    __tablename__ = "sync_cursor"

    scope: Mapped[str] = mapped_column(String(80), primary_key=True)
    watermark: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rows_seen: Mapped[int | None] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AssetReferenceCheckOrm(Base):
    """Local exact-identity lookup evidence, not an alias or asset registry."""
    __tablename__ = "asset_reference_check"
    asset_id: Mapped[str] = mapped_column(String(60), primary_key=True)
    outcome: Mapped[str] = mapped_column(String(40))
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    retry_after: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=1)


class CollectRunOrm(Base):
    """One row per sync run — observability (mirror of pi-collector)."""

    __tablename__ = "collect_run"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    object_structure: Mapped[str] = mapped_column(String(80))
    mode: Mapped[str] = mapped_column(String(20), default="full")
    rows_seen: Mapped[int] = mapped_column(Integer, default=0)
    upserted: Mapped[int] = mapped_column(Integer, default=0)
    skipped: Mapped[int] = mapped_column(Integer, default=0)
    errors: Mapped[int] = mapped_column(Integer, default=0)
    watermark: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
