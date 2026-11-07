"""Old WO-derived snapshots must not escape the fail-closed API gate."""
from datetime import date
from types import SimpleNamespace
import unittest

from src.api.app import create_app
from src.domain.reliability_kpi import ReliabilityKpi


class KpiReadinessTest(unittest.TestCase):
    def test_old_numeric_mtbf_mttr_availability_are_not_served_as_valid(self):
        endpoint=next(route.endpoint for route in create_app().routes if route.path=='/kpis/{equipment_id}/{metric}')
        for metric in ('MTBF','MTTR','AVAILABILITY'):
            kpi=ReliabilityKpi(id='synthetic',equipment_id='A',metric=metric,value=999,
                               period_start=date(2026,1,1),period_end=date(2026,1,31))
            result=endpoint('A',metric,SimpleNamespace(get_latest_kpi=lambda *args:kpi))
            self.assertIsNone(result.value);self.assertEqual(result.readiness,'NOT_READY')
            self.assertTrue(result.blockers)
            self.assertEqual(kpi.value,999)  # read boundary does not rewrite stored history
    def test_pm_result_is_not_replaced(self):
        endpoint=next(route.endpoint for route in create_app().routes if route.path=='/kpis/{equipment_id}/{metric}')
        kpi=ReliabilityKpi(id='synthetic',equipment_id='A',metric='PM_COMPLIANCE',value=80)
        result=endpoint('A','PM_COMPLIANCE',SimpleNamespace(get_latest_kpi=lambda *args:kpi))
        self.assertEqual(result.value,80);self.assertFalse(result.blockers)
