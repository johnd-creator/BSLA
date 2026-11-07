"""CockpitStore: map domain models <-> ORM rows and persist to Postgres.

Stores only the cockpit's OWN normalized data; never writes to Maximo/PI.
Follows reliability-data-contracts field names.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from typing import Any

from src.domain.downtime import Downtime
from src.domain.equipment import Equipment
from src.domain.failure import Failure
from src.domain.item import Item
from src.domain.labor import Labor
from src.domain.person import Person
from src.domain.reliability_kpi import ReliabilityKpi
from src.domain.service_request import ServiceRequest
from src.domain.work_order import WorkOrder
from src.repositories import models
from src.repositories.database import Database


def _utc(value: datetime | None) -> datetime | None:
    return value


class CockpitStore:
    def __init__(self, db: Database):
        self._db = db

    # -- equipment --------------------------------------------------------
    def upsert_equipment(self, item: Equipment) -> None:
        with self._db.session() as session:
            row = session.get(models.EquipmentOrm, item.id)
            src = item.maximo_source
            if row is None:
                row = models.EquipmentOrm(id=item.id)
            row.name = item.name
            row.description = item.description
            row.location_id = item.location_id
            row.equipment_class = item.equipment_class
            row.unit = item.unit
            row.status = item.status
            row.status_description = item.status_description
            row.is_running = item.is_running
            row.priority = item.priority
            row.parent_id = item.parent_id
            row.ancestor_id = item.ancestor_id
            row.has_children = item.has_children
            row.failure_code = item.failure_code
            row.is_safety_critical = item.is_safety_critical
            row.is_calibration = item.is_calibration
            row.installed_at = item.installed_at
            row.status_changed_at = item.status_changed_at
            row.source_changed_at = item.source_changed_at
            row.purchase_price = item.purchase_price
            row.replacement_cost = item.replacement_cost
            row.total_cost = item.total_cost
            row.downtime_total_hours = item.downtime_total_hours
            row.manufacturer = item.manufacturer
            row.vendor = item.vendor
            if src:
                row.src_assetid = src.assetid
                row.src_siteid = src.siteid
                row.src_orgid = src.orgid
            session.add(row)
            session.commit()

    def upsert_work_order(self, item: WorkOrder) -> None:
        with self._db.session() as session:
            row = session.get(models.WorkOrderOrm, item.id)
            if row is None:
                row = models.WorkOrderOrm(id=item.id)
            row.equipment_id = item.equipment_id
            row.location_id = item.location_id
            row.status = item.status
            row.status_description = item.status_description
            row.work_type = item.work_type
            row.work_class = item.work_class
            row.description = item.description
            row.reported_at = item.reported_at
            row.source_changed_at = item.source_changed_at
            row.status_changed_at = item.status_changed_at
            row.scheduled_start = item.scheduled_start
            row.scheduled_finish = item.scheduled_finish
            row.target_completion = item.target_completion
            row.estimated_duration_hours = item.estimated_duration_hours
            row.downtime_hours = item.downtime_hours
            row.priority = item.priority
            row.priority_description = item.priority_description
            row.reported_by = item.reported_by
            row.supervisor = item.supervisor
            row.lead = item.lead
            row.failure_code = item.failure_code
            row.is_task = item.is_task
            # No verified parent mapping exists. Retain old stored observations
            # for provenance; read paths quarantine them instead of asserting a
            # relationship. New rows keep the nullable column empty.
            row.has_children = item.has_children
            row.estimated_labor_cost = item.estimated_labor_cost
            row.estimated_material_cost = item.estimated_material_cost
            row.actual_labor_cost = item.actual_labor_cost
            row.actual_material_cost = item.actual_material_cost
            row.actual_labor_hours = item.actual_labor_hours
            if item.sources:
                wo_id = item.sources.get("maximo", {}).get("workorderid")
                row.src_workorderid = wo_id
            session.add(row)
            session.commit()

    def upsert_service_request(self, item: ServiceRequest) -> None:
        with self._db.session() as session:
            row = session.get(models.ServiceRequestOrm, item.id)
            if row is None:
                row = models.ServiceRequestOrm(id=item.id)
            row.description = item.description
            row.status = item.status
            row.status_description = item.status_description
            row.work_type = item.work_type
            row.equipment_id = item.equipment_id
            row.location_id = item.location_id
            row.reported_by = item.reported_by
            row.reported_by_name = item.reported_by_name
            row.reported_at = item.reported_at
            row.source_changed_at = item.source_changed_at
            row.affected_at = item.affected_at
            row.actual_start = item.actual_start
            row.actual_finish = item.actual_finish
            row.target_start = item.target_start
            row.target_finish = item.target_finish
            row.internal_priority = item.internal_priority
            row.reported_priority = item.reported_priority
            row.actual_labor_hours = item.actual_labor_hours
            row.actual_labor_cost = item.actual_labor_cost
            row.risk_area_environment = item.risk_area_environment
            row.risk_area_process = item.risk_area_process
            row.risk_area_human = item.risk_area_human
            row.risk_area_reputation = item.risk_area_reputation
            row.class_label = item.class_label
            if item.sources:
                row.src_ticketuid = item.sources.get("maximo", {}).get("ticketuid")
            session.add(row)
            session.commit()

    def upsert_person(self, item: Person) -> None:
        with self._db.session() as session:
            row = session.get(models.PersonOrm, item.id)
            if row is None:
                row = models.PersonOrm(id=item.id)
            row.display_name = item.display_name
            row.first_name = item.first_name
            row.status = item.status
            row.status_changed_at = item.status_changed_at
            row.location_org = item.location_org
            session.add(row)
            session.commit()

    def upsert_item(self, item: Item) -> None:
        with self._db.session() as session:
            row = session.get(models.ItemOrm, item.id)
            if row is None:
                row = models.ItemOrm(id=item.id)
            row.description = item.description
            row.status = item.status
            row.item_type = item.item_type
            row.lot_type = item.lot_type
            row.issue_unit = item.issue_unit
            row.order_unit = item.order_unit
            row.is_rotating = item.is_rotating
            row.is_kit = item.is_kit
            row.is_crew = item.is_crew
            row.inspection_required = item.inspection_required
            row.meter_name = item.meter_name
            row.item_set_id = item.item_set_id
            row.status_changed_at = item.status_changed_at
            session.add(row)
            session.commit()

    def upsert_labor(self, item: Labor) -> None:
        with self._db.session() as session:
            row = session.get(models.LaborOrm, item.id)
            if row is None:
                row = models.LaborOrm(id=item.id)
            row.person_id = item.person_id
            row.status = item.status
            row.status_description = item.status_description
            row.work_site = item.work_site
            row.is_assigned = item.is_assigned
            row.availability_factor = item.availability_factor
            row.reported_hours = item.reported_hours
            row.year_to_date_other_hours = item.year_to_date_other_hours
            row.year_to_date_refused_hours = item.year_to_date_refused_hours
            session.add(row)
            session.commit()

    def upsert_kpi(self, item: ReliabilityKpi) -> None:
        with self._db.session() as session:
            row = session.get(models.ReliabilityKpiOrm, item.id)
            if row is None:
                row = models.ReliabilityKpiOrm(id=item.id)
            row.equipment_id = item.equipment_id
            row.metric = item.metric
            row.value = item.value
            row.unit = item.unit
            row.period_start = item.period_start
            row.period_end = item.period_end
            row.computed_at = item.computed_at or datetime.now(timezone.utc)
            row.inputs_json = json.dumps(item.inputs or {})
            session.add(row)
            session.commit()

    def get_latest_kpi(self, equipment_id: str, metric: str) -> ReliabilityKpi | None:
        with self._db.session() as session:
            row = (
                session.query(models.ReliabilityKpiOrm)
                .filter(
                    models.ReliabilityKpiOrm.equipment_id == equipment_id,
                    models.ReliabilityKpiOrm.metric == metric,
                )
                .order_by(models.ReliabilityKpiOrm.period_end.desc())
                .first()
            )
            if row is None:
                return None
            return ReliabilityKpi(
                id=row.id,
                equipment_id=row.equipment_id,
                metric=row.metric,
                value=row.value,
                unit=row.unit,
                period_start=row.period_start,
                period_end=row.period_end,
                computed_at=row.computed_at,
            )

    # -- sync cursor ------------------------------------------------------
    def get_cursor(self, object_structure: str) -> datetime | None:
        with self._db.session() as session:
            row = session.get(models.SyncCursorOrm, object_structure)
            return row.last_changedate if row else None

    def set_cursor(self, object_structure: str, last_changedate: datetime | None, rows_seen: int) -> None:
        with self._db.session() as session:
            row = session.get(models.SyncCursorOrm, object_structure)
            if row is None:
                row = models.SyncCursorOrm(
                    object_structure=object_structure,
                    last_changedate=last_changedate,
                    last_synced_at=datetime.now(timezone.utc),
                    rows_seen=rows_seen,
                )
            else:
                row.last_changedate = last_changedate
                row.last_synced_at = datetime.now(timezone.utc)
                row.rows_seen = rows_seen
            session.add(row)
            session.commit()

    # -- reads (for KPI + API) --------------------------------------------
    def get_equipment(self, equipment_id: str) -> Equipment | None:
        """Single-row primary-key lookup (avoids loading + filtering a page)."""
        with self._db.session() as session:
            row = session.get(models.EquipmentOrm, equipment_id)
            return _equipment_from_row(row) if row else None

    def list_equipment(self, limit: int = 500) -> list[Equipment]:
        with self._db.session() as session:
            rows = session.query(models.EquipmentOrm).order_by(models.EquipmentOrm.id).limit(limit).all()
            return [_equipment_from_row(r) for r in rows]

    def count_work_orders(self, equipment_id: str | None = None, status: str | None = None) -> int:
        with self._db.session() as session:
            query = session.query(models.WorkOrderOrm)
            if equipment_id:
                query = query.filter(models.WorkOrderOrm.equipment_id == equipment_id)
            if status:
                query = query.filter(models.WorkOrderOrm.status == status)
            return query.count()

    def list_work_orders(
        self,
        equipment_id: str | None = None,
        offset: int = 0,
        limit: int = 50,
        status: str | None = None,
    ) -> list[WorkOrder]:
        with self._db.session() as session:
            q = session.query(models.WorkOrderOrm)
            if equipment_id:
                q = q.filter(models.WorkOrderOrm.equipment_id == equipment_id)
            if status:
                q = q.filter(models.WorkOrderOrm.status == status)
            rows = (
                q.order_by(
                    models.WorkOrderOrm.reported_at.desc().nulls_last(),
                    models.WorkOrderOrm.id.asc(),
                )
                .offset(offset)
                .limit(limit)
                .all()
            )
            return [_work_order_from_row(r) for r in rows]

    def list_work_order_statuses(self) -> list[str]:
        with self._db.session() as session:
            rows = (
                session.query(models.WorkOrderOrm.status)
                .filter(models.WorkOrderOrm.status.is_not(None))
                .distinct()
                .order_by(models.WorkOrderOrm.status)
                .all()
            )
            return [status for (status,) in rows if status]


def _equipment_from_row(r: models.EquipmentOrm) -> Equipment:
    return Equipment(
        id=r.id,
        name=r.name,
        description=r.description,
        location_id=r.location_id,
        equipment_class=r.equipment_class,
        unit=r.unit,
        status=r.status,
        status_description=r.status_description,
        is_running=r.is_running,
        priority=r.priority,
        parent_id=r.parent_id,
        ancestor_id=r.ancestor_id,
        has_children=r.has_children,
        failure_code=r.failure_code,
        is_safety_critical=r.is_safety_critical,
        is_calibration=r.is_calibration,
        installed_at=r.installed_at,
        status_changed_at=r.status_changed_at,
        source_changed_at=r.source_changed_at,
        purchase_price=r.purchase_price,
        replacement_cost=r.replacement_cost,
        total_cost=r.total_cost,
        downtime_total_hours=r.downtime_total_hours,
        manufacturer=r.manufacturer,
        vendor=r.vendor,
    )


def _work_order_from_row(r: models.WorkOrderOrm) -> WorkOrder:
    return WorkOrder(
        id=r.id,
        equipment_id=r.equipment_id,
        location_id=r.location_id,
        status=r.status,
        status_description=r.status_description,
        work_type=r.work_type,
        work_class=r.work_class,
        description=r.description,
        reported_at=r.reported_at,
        source_changed_at=r.source_changed_at,
        status_changed_at=r.status_changed_at,
        scheduled_start=r.scheduled_start,
        scheduled_finish=r.scheduled_finish,
        target_completion=r.target_completion,
        estimated_duration_hours=r.estimated_duration_hours,
        downtime_hours=r.downtime_hours,
        priority=r.priority,
        priority_description=r.priority_description,
        reported_by=r.reported_by,
        supervisor=r.supervisor,
        lead=r.lead,
        failure_code=r.failure_code,
        is_task=r.is_task,
        parent_wo=None,  # Existing legacy values have no verified parent provenance.
        has_children=r.has_children,
        estimated_labor_cost=r.estimated_labor_cost,
        estimated_material_cost=r.estimated_material_cost,
        actual_labor_cost=r.actual_labor_cost,
        actual_material_cost=r.actual_material_cost,
        actual_labor_hours=r.actual_labor_hours,
        sources={"maximo": {"hierarchy": {
            "schema_version": 1, "parent_wo_state": "UNKNOWN",
            "legacy_parent_wo": r.parent_wo,
        }}},
    )
