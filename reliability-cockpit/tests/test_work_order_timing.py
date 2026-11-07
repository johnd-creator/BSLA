"""Pure and public-DTO tests; no operational database or source access."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock
import unittest
from fastapi import HTTPException
from src.api.reliability import MaintenanceView, _maintenance, maintenance_event_detail
from src.services.work_order_timing import execution_interval

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def row(**changes):
    values = {key: None for key in MaintenanceView.model_fields}
    values.update(canonical_id='maintenance:TEST', contract_version='1.0', id='TEST', equipment_id='asset:TEST', site_code='BSR', organization_code='IP', status='CLOSE', actual_start=NOW, actual_finish=NOW+timedelta(hours=2.5), duration_hours=999, sources={'maximo': {'description': 'Synthetic safe description', 'reportedby': 'PRIVATE-PERSON', 'raw': 'PRIVATE-RAW'}})
    values.update(changes)
    return SimpleNamespace(**values)


class WorkOrderTimingTest(unittest.TestCase):
    def test_duration_is_recomputed_from_actuals_not_old_duration_or_status_date(self):
        result = _maintenance(row(status_changed_at=NOW+timedelta(days=90)))
        self.assertEqual(result.duration_hours, 2.5)
        self.assertEqual(result.actual_timing_state, 'AVAILABLE')
        self.assertEqual(result.description, 'Synthetic safe description')
        self.assertNotIn('PRIVATE-', result.model_dump_json())
        self.assertNotIn('sources', result.model_dump())

    def test_missing_or_invalid_actuals_are_not_zero(self):
        for start, finish in [(None, NOW), (NOW, None), (NOW.replace(tzinfo=None), NOW), (NOW, NOW-timedelta(hours=1))]:
            result = execution_interval('CLOSE', start, finish)
            self.assertIsNone(result['duration_hours'])
            self.assertNotEqual(result['actual_timing_state'], 'AVAILABLE')
        self.assertEqual(execution_interval('CLOSE', NOW, NOW)['duration_hours'], 0)

    def test_non_close_status_has_no_final_duration(self):
        for status in ['COMP', 'WAPPR', 'APPR', 'CAN', 'CANCEL', 'INPRG', None]:
            result = _maintenance(row(status=status))
            self.assertIsNone(result.actual_start)
            self.assertIsNone(result.actual_finish)
            self.assertIsNone(result.duration_hours)
            self.assertEqual(result.actual_timing_state, 'NOT_CLOSED')
            self.assertEqual(execution_interval(status, NOW, NOW+timedelta(hours=4))['actual_timing_state'], 'NOT_CLOSED')
            self.assertIsNone(execution_interval(status, NOW, NOW+timedelta(hours=4))['duration_hours'])

    def test_invalid_retained_clock_state_is_allowlisted_without_raw_value(self):
        result = _maintenance(row(actual_start=None, sources={'maximo': {'actual_timing_state': 'NAIVE_ACTUAL_START', 'raw': 'PRIVATE-RAW'}}))
        self.assertEqual(result.actual_timing_state, 'NAIVE_ACTUAL_START')
        self.assertIsNone(result.duration_hours)
        self.assertNotIn('PRIVATE-', result.model_dump_json())
        self.assertIsNone(_maintenance(row(sources=['invalid'])).description)

    def test_detail_uses_exact_canonical_filter_through_registry_repository(self):
        repository = Mock()
        repository.list_maintenance.return_value = SimpleNamespace(items=[row()])
        result = maintenance_event_detail('maintenance:TEST', service=SimpleNamespace(repository=repository))
        self.assertEqual(result.canonical_id, 'maintenance:TEST')
        repository.list_maintenance.assert_called_once_with(canonical_id='maintenance:TEST', limit=1)
        repository.list_maintenance.return_value = SimpleNamespace(items=[])
        with self.assertRaises(HTTPException) as error:
            maintenance_event_detail('missing', service=SimpleNamespace(repository=repository))
        self.assertEqual(error.exception.status_code, 404)

    def test_unavailable_observation_and_unknown_zone_keep_their_public_reason(self):
        for field, name in [('actual_start', 'START'), ('actual_finish', 'FINISH')]:
            for state in ['UNAVAILABLE', 'NAIVE', 'INVALID']:
                with self.subTest(field=field, state=state):
                    result = _maintenance(row(**{field: None}, sources={'maximo': {'actual_timing_state': state + '_ACTUAL_' + name}}))
                    self.assertEqual(result.actual_timing_state, state + '_ACTUAL_' + name)
                    self.assertIsNone(result.duration_hours)

    def test_clock_reason_cannot_be_taken_from_the_other_missing_field(self):
        result = _maintenance(row(actual_start=None, actual_finish=None, sources={'maximo': {'actual_timing_state': 'NAIVE_ACTUAL_FINISH'}}))
        self.assertEqual(result.actual_timing_state, 'MISSING_ACTUAL_START')
        self.assertIsNone(result.duration_hours)
        result = _maintenance(row(status='COMP', actual_start=None, sources={'maximo': {'actual_timing_state': 'INVALID_ACTUAL_START'}}))
        self.assertEqual(result.actual_timing_state, 'NOT_CLOSED')
