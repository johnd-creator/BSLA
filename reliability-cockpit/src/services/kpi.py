"""Reliability KPI computation (vendor-neutral).

Formulas use explicit units. These are computed by the cockpit from normalized
data (equipment + work orders); they are not direct Maximo fields.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, timezone

from src.domain.reliability_kpi import ReliabilityKpi
from src.domain.work_order import WorkOrder
from src.repositories.store import CockpitStore

LOG = logging.getLogger(__name__)

PM_WORK_TYPE = "PM"
COMPLETED_STATUSES = frozenset({"CLOSE", "CLOSED", "COMP", "COMPLETE", "COMPLETED"})

# Work-order classification and calendar hours do not establish these inputs.
# Pure formula helpers above/below remain usable with separately governed data.
WORK_ORDER_KPI_BLOCKERS = {
    "MTBF": ("FAILURE_OCCURRENCES_UNVERIFIED", "OPERATING_EXPOSURE_UNAVAILABLE"),
    "MTTR": ("FAILURE_OCCURRENCES_UNVERIFIED", "RESTORATION_INTERVALS_UNAVAILABLE"),
    "AVAILABILITY": ("OPERATING_EXPOSURE_UNAVAILABLE", "DOWNTIME_INTERVALS_UNAVAILABLE"),
}


def _kpi_id(equipment_id: str, metric: str, period_start: date, period_end: date) -> str:
    return f"{equipment_id}:{metric}:{period_start.isoformat()}:{period_end.isoformat()}"


def compute_mtbf(
    equipment_id: str,
    *,
    failures: int,
    total_operating_hours: float,
    period_start: date,
    period_end: date,
) -> ReliabilityKpi:
    value = total_operating_hours / failures if failures > 0 else None
    return ReliabilityKpi(
        id=_kpi_id(equipment_id, "MTBF", period_start, period_end),
        equipment_id=equipment_id,
        metric="MTBF",
        value=value,
        unit="hours",
        period_start=period_start,
        period_end=period_end,
        computed_at=datetime.now(timezone.utc),
        inputs={"failures": failures, "total_operating_hours": total_operating_hours},
    )


def compute_mttr(
    equipment_id: str,
    *,
    total_downtime_hours: float,
    failures: int,
    period_start: date,
    period_end: date,
) -> ReliabilityKpi:
    value = total_downtime_hours / failures if failures > 0 else None
    return ReliabilityKpi(
        id=_kpi_id(equipment_id, "MTTR", period_start, period_end),
        equipment_id=equipment_id,
        metric="MTTR",
        value=value,
        unit="hours",
        period_start=period_start,
        period_end=period_end,
        computed_at=datetime.now(timezone.utc),
        inputs={"failures": failures, "total_downtime_hours": total_downtime_hours},
    )


def compute_availability(
    equipment_id: str,
    *,
    total_downtime_hours: float,
    total_operating_hours: float,
    period_start: date,
    period_end: date,
) -> ReliabilityKpi:
    total = total_operating_hours + total_downtime_hours
    value = (total - total_downtime_hours) / total * 100 if total > 0 else None
    return ReliabilityKpi(
        id=_kpi_id(equipment_id, "AVAILABILITY", period_start, period_end),
        equipment_id=equipment_id,
        metric="AVAILABILITY",
        value=value,
        unit="percent",
        period_start=period_start,
        period_end=period_end,
        computed_at=datetime.now(timezone.utc),
        inputs={"total_downtime_hours": total_downtime_hours, "total_operating_hours": total_operating_hours},
    )


def compute_pm_compliance(
    equipment_id: str,
    *,
    pm_scheduled: int,
    pm_completed: int,
    period_start: date,
    period_end: date,
) -> ReliabilityKpi:
    value = pm_completed / pm_scheduled * 100 if pm_scheduled > 0 else None
    return ReliabilityKpi(
        id=_kpi_id(equipment_id, "PM_COMPLIANCE", period_start, period_end),
        equipment_id=equipment_id,
        metric="PM_COMPLIANCE",
        value=value,
        unit="percent",
        period_start=period_start,
        period_end=period_end,
        computed_at=datetime.now(timezone.utc),
        inputs={"pm_scheduled": pm_scheduled, "pm_completed": pm_completed},
    )


__all__ = [
    "KpiPeriod",
    "KpiService",
    "compute_mtbf",
    "compute_mttr",
    "compute_availability",
    "compute_pm_compliance",
]


@dataclass(frozen=True)
class KpiPeriod:
    """Inclusive day window [start, end] over which KPIs are aggregated."""

    start: date
    end: date

    @property
    def total_hours(self) -> float:
        """Full calendar hours spanned, counting both start and end days."""
        return ((self.end - self.start).days + 1) * 24.0


def _in_period(reported_at: datetime | None, period: KpiPeriod) -> bool:
    if reported_at is None:
        return False
    day = reported_at.date() if isinstance(reported_at, datetime) else reported_at
    return period.start <= day <= period.end


def _aggregate(work_orders: list[WorkOrder], period: KpiPeriod) -> dict[str, float | int]:
    """Roll up the work-order facts that feed the KPI formulas."""
    in_period = [wo for wo in work_orders if _in_period(wo.reported_at, period)]
    pm_orders = [wo for wo in in_period if (wo.work_type or "").upper() == PM_WORK_TYPE]
    pm_scheduled = len(pm_orders)
    pm_completed = sum(1 for wo in pm_orders if (wo.status or "").upper() in COMPLETED_STATUSES)
    return {
        "pm_scheduled": pm_scheduled,
        "pm_completed": pm_completed,
        "work_orders_in_period": len(in_period),
    }


class KpiService:
    """Aggregates normalized work orders into reliability KPIs and persists them.

    Reads only from the cockpit store (never from Maximo/PI). The computed KPIs
    are upserted so the ``/kpis/*`` API endpoint can serve them.
    """

    def __init__(self, store: CockpitStore):
        self._store = store

    def compute_for_equipment(self, equipment_id: str, period: KpiPeriod) -> list[ReliabilityKpi]:
        work_orders = self._store.list_work_orders(equipment_id=equipment_id, limit=10000)
        facts = _aggregate(work_orders, period)
        return [
            *(ReliabilityKpi(
                id=_kpi_id(equipment_id, metric, period.start, period.end),
                equipment_id=equipment_id, metric=metric, value=None,
                unit="percent" if metric == "AVAILABILITY" else "hours",
                period_start=period.start, period_end=period.end,
                computed_at=datetime.now(timezone.utc),
                inputs={"readiness": "NOT_READY", "basis": "WORK_ORDER_ONLY",
                        "blockers": list(blockers),
                        "work_orders_in_period": facts["work_orders_in_period"]},
            ) for metric, blockers in WORK_ORDER_KPI_BLOCKERS.items()),
            compute_pm_compliance(
                equipment_id,
                pm_scheduled=facts["pm_scheduled"],
                pm_completed=facts["pm_completed"],
                period_start=period.start,
                period_end=period.end,
            ),
        ]

    def compute_all(
        self, period: KpiPeriod, equipment_id: str | None = None, *, persist: bool = True
    ) -> list[ReliabilityKpi]:
        equipment = self._store.list_equipment(limit=10000)
        if equipment_id:
            equipment = [e for e in equipment if e.id == equipment_id]
        results: list[ReliabilityKpi] = []
        for eq in equipment:
            kpis = self.compute_for_equipment(eq.id, period)
            if persist:
                for kpi in kpis:
                    self._store.upsert_kpi(kpi)
            results.extend(kpis)
        LOG.info(
            "computed %d KPIs across %d equipment for %s..%s",
            len(results),
            len(equipment),
            period.start,
            period.end,
        )
        return results

def compute_all(period: KpiPeriod, equipment_id: str | None = None) -> list[ReliabilityKpi]:
    """Compute KPIs for all (or a specific) equipment over the given period."""
    from src.services.kpi import KpiService
    from src.repositories.database import get_database, Database
    store = CockpitStore(get_database())
    service = KpiService(store)
    return service.compute_all(period, equipment_id=equipment_id)
