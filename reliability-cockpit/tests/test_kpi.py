"""Unit tests for reliability KPI computations (pure math, no DB)."""

from __future__ import annotations

import unittest
from datetime import date, datetime, timezone

from src.domain.equipment import Equipment
from src.domain.reliability_kpi import ReliabilityKpi
from src.domain.work_order import WorkOrder
from src.services.kpi import (
    KpiPeriod,
    KpiService,
    compute_availability,
    compute_mtbf,
    compute_mttr,
    compute_pm_compliance,
)


class KpiTest(unittest.TestCase):
    def test_mtbf(self):
        kpi = compute_mtbf("A1", failures=4, total_operating_hours=7200.0, period_start=date(2026, 1, 1), period_end=date(2026, 3, 31))
        self.assertEqual(kpi.metric, "MTBF")
        self.assertEqual(kpi.value, 1800.0)
        self.assertEqual(kpi.unit, "hours")

    def test_mtbf_no_failures(self):
        kpi = compute_mtbf("A1", failures=0, total_operating_hours=7200.0, period_start=date(2026, 1, 1), period_end=date(2026, 3, 31))
        self.assertIsNone(kpi.value)

    def test_mttr(self):
        kpi = compute_mttr("A1", total_downtime_hours=40.0, failures=4, period_start=date(2026, 1, 1), period_end=date(2026, 3, 31))
        self.assertEqual(kpi.value, 10.0)

    def test_availability(self):
        kpi = compute_availability("A1", total_operating_hours=7200.0, total_downtime_hours=800.0, period_start=date(2026, 1, 1), period_end=date(2026, 3, 31))
        self.assertAlmostEqual(kpi.value, 90.0, places=6)
        self.assertEqual(kpi.unit, "percent")

    def test_pm_compliance(self):
        kpi = compute_pm_compliance("A1", pm_scheduled=10, pm_completed=8, period_start=date(2026, 1, 1), period_end=date(2026, 3, 31))
        self.assertEqual(kpi.value, 80.0)


def _wo(wonum, *, equipment_id="A1", failure_code=None, downtime=None, wtype=None, status=None, reported=None):
    return WorkOrder(
        id=wonum,
        equipment_id=equipment_id,
        failure_code=failure_code,
        downtime_hours=downtime,
        work_type=wtype,
        status=status,
        reported_at=reported,
    )


class FakeKpiStore:
    def __init__(self, equipment, work_orders):
        self._equipment = equipment
        self._work_orders = work_orders
        self.persisted: list[ReliabilityKpi] = []

    def list_equipment(self, limit=500):
        return self._equipment

    def list_work_orders(self, equipment_id=None, limit=500):
        return [wo for wo in self._work_orders if wo.equipment_id == equipment_id]

    def upsert_kpi(self, kpi):
        self.persisted.append(kpi)


class KpiServiceTest(unittest.TestCase):
    def test_period_total_hours_inclusive(self):
        period = KpiPeriod(start=date(2026, 8, 1), end=date(2026, 8, 31))
        self.assertEqual(period.total_hours, 31 * 24.0)

    def test_compute_for_equipment_aggregates_and_persists(self):
        period = KpiPeriod(start=date(2026, 8, 1), end=date(2026, 8, 31))
        work_orders = [
            _wo("W1", failure_code="BRG", downtime=8.0, reported=datetime(2026, 8, 5, tzinfo=timezone.utc)),
            _wo("W2", failure_code="SEAL", downtime=12.0, reported=datetime(2026, 8, 10, tzinfo=timezone.utc)),
            _wo("W3", wtype="PM", status="COMP", reported=datetime(2026, 8, 15, tzinfo=timezone.utc)),
            _wo("W4", wtype="PM", status="WAPPR", reported=datetime(2026, 8, 20, tzinfo=timezone.utc)),
            _wo("W5", wtype="PM", status="CLOSE", reported=datetime(2026, 7, 31, tzinfo=timezone.utc)),
        ]
        store = FakeKpiStore([Equipment(id="A1")], work_orders)
        service = KpiService(store)  # type: ignore[arg-type]

        kpis = service.compute_for_equipment("A1", period)
        by_metric = {k.metric: k for k in kpis}

        self.assertEqual(set(by_metric), {"MTBF", "MTTR", "AVAILABILITY", "PM_COMPLIANCE"})
        for metric in ("MTBF", "MTTR", "AVAILABILITY"):
            self.assertIsNone(by_metric[metric].value)
            self.assertEqual(by_metric[metric].inputs["readiness"], "NOT_READY")
            self.assertNotIn("failures", by_metric[metric].inputs)
            self.assertNotIn("total_operating_hours", by_metric[metric].inputs)
            self.assertTrue(by_metric[metric].inputs["blockers"])
        self.assertEqual(by_metric["PM_COMPLIANCE"].value, 50.0)

    def test_compute_all_persists_and_filters_by_equipment(self):
        period = KpiPeriod(start=date(2026, 8, 1), end=date(2026, 8, 2))
        work_orders = [_wo("W1", equipment_id="A1", failure_code="X", reported=datetime(2026, 8, 1, tzinfo=timezone.utc))]
        store = FakeKpiStore([Equipment(id="A1"), Equipment(id="A2")], work_orders)
        service = KpiService(store)  # type: ignore[arg-type]

        all_kpis = service.compute_all(period)
        self.assertEqual(len(all_kpis), 8)

        store.persisted.clear()
        one = service.compute_all(period, equipment_id="A2")
        self.assertEqual(len(one), 4)
        self.assertEqual(len(store.persisted), 4)

    def test_work_order_outside_period_is_ignored(self):
        period = KpiPeriod(start=date(2026, 8, 1), end=date(2026, 8, 31))
        work_orders = [
            _wo("W1", failure_code="X", downtime=5.0, reported=datetime(2026, 7, 31, tzinfo=timezone.utc)),
            _wo("W2", failure_code="Y", downtime=5.0, reported=datetime(2026, 9, 1, tzinfo=timezone.utc)),
        ]
        store = FakeKpiStore([Equipment(id="A1")], work_orders)
        service = KpiService(store)  # type: ignore[arg-type]

        kpis = {k.metric: k for k in service.compute_for_equipment("A1", period)}
        self.assertIsNone(kpis["MTBF"].value)
        self.assertIsNone(kpis["MTTR"].value)
        self.assertIsNone(kpis["AVAILABILITY"].value)


if __name__ == "__main__":
    unittest.main()