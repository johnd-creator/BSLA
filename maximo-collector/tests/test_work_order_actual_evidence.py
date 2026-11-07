"""Hermetic actual-clock retention and local-only projection regression tests."""
import unittest
from datetime import datetime, timezone

from src.adapters.maximo.actual_dates import clock, evidence, execution_interval, retained_values
from src.adapters.maximo.canonical_mappers import maintenance_event_from_payload
from src.adapters.maximo.mappers import work_order_from_payload
from src.config import DbConfig
from jsonschema import Draft202012Validator, FormatChecker
import json
from pathlib import Path
from src.repositories.database import Database
from src.repositories.models import EquipmentOrm, WorkOrderOrm, SyncCursorOrm
from src.repositories.mart_models import MaintenanceEventMartOrm
from src.repositories.store import CollectorStore
from src.services.local_mart_projector import CollectorMartProjector


def member(**changes):
    return dict({'wonum': 'BSR-TEST', 'assetnum': 'ASSET-1', 'siteid': 'BSR', 'orgid': 'IP',
                 'status': 'CLOSE', 'description': 'Synthetic WO description', 'changedate': '2026-11-01T12:00:00Z',
                 'actstart': '2026-10-31T08:00:00Z', 'actfinish': '2026-10-31T10:30:00Z'}, **changes)


class ActualEvidenceTest(unittest.TestCase):
    def test_duration_uses_only_valid_actual_clocks(self):
        result = maintenance_event_from_payload(member(statusdate='2026-11-05T10:00:00Z', estdur=999, actlabhrs=777, downtime=666))
        self.assertEqual(result['duration_hours'], 2.5)
        self.assertEqual(result['description'], 'Synthetic WO description')
        self.assertEqual(result['sources']['maximo']['actual_timing_state'], 'AVAILABLE')

    def test_missing_actuals_never_fall_back_to_status_report_or_schedule(self):
        result = maintenance_event_from_payload(member(actstart=None, actfinish=None, statusdate='2026-10-01T00:00:00Z', reportdate='2026-10-01T00:00:00Z', schedstart='2026-10-01T00:00:00Z', schedfinish='2026-10-02T00:00:00Z'))
        self.assertIsNone(result['actual_start'])
        self.assertIsNone(result['actual_finish'])
        self.assertIsNone(result['duration_hours'])

    def test_invalid_naive_and_reversed_actuals_remain_unavailable(self):
        for start, finish, expected in [('bad', '2026-10-31T10:30:00Z', 'INVALID_ACTUAL_START'), ('2026-10-31T08:00:00', '2026-10-31T10:30:00Z', 'NAIVE_ACTUAL_START'), ('2026-10-31T12:00:00Z', '2026-10-31T10:30:00Z', 'INVALID_ACTUAL_ORDER')]:
            result = maintenance_event_from_payload(member(actstart=start, actfinish=finish))
            self.assertIsNone(result['duration_hours'])
            self.assertEqual(result['sources']['maximo']['actual_timing_state'], expected)
            schema = json.loads((Path(__file__).parents[2] / 'reliability-data-contracts/schemas/maintenance-event.schema.json').read_text())
            Draft202012Validator(schema, format_checker=FormatChecker()).validate(result)

    def test_wappr_and_comp_do_not_acquire_final_close_duration(self):
        for status in ['WAPPR', 'COMP', 'APPR']:
            result = maintenance_event_from_payload(member(status=status))
            self.assertEqual(result['status'], status)
            self.assertIsNone(result['duration_hours'])
            self.assertEqual(result['sources']['maximo']['actual_timing_state'], 'NOT_CLOSED')

    def test_explicit_offsets_and_zero_duration_are_valid(self):
        self.assertEqual(execution_interval('CLOSE', '2026-01-01T10:00:00+07:00', '2026-01-01T04:30:00Z')['duration_hours'], 1.5)
        self.assertEqual(execution_interval('CLOSE', '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z')['duration_hours'], 0)
        self.assertEqual(clock({'value': '2026-01-01T00:00:00Z'})['state'], 'INVALID')

    def test_wrong_asset_identity_or_future_source_version_cannot_replay(self):
        proof = evidence(member())
        now = datetime(2026, 11, 1, 12, tzinfo=timezone.utc)
        self.assertEqual(retained_values(proof, 'BSR-TEST', 'OTHER-ASSET', now), {})
        self.assertEqual(retained_values(proof, 'BSR-TEST', 'ASSET-1', datetime(2026, 10, 1, tzinfo=timezone.utc)), {})

    def test_store_preserves_valid_evidence_when_later_payload_omits_actuals(self):
        db = Database(DbConfig('sqlite+pysqlite:///:memory:'))
        db.create_all()
        try:
            store = CollectorStore(db)
            store.upsert_work_order(work_order_from_payload(member()))
            later = member(changedate='2026-11-02T12:00:00Z')
            del later['actstart']; del later['actfinish']
            store.upsert_work_order(work_order_from_payload(later))
            with db.session() as session:
                row = session.get(WorkOrderOrm, 'BSR-TEST')
                self.assertEqual(row.sources['maximo']['actual_dates']['fields']['actstart']['state'], 'VALID')
                self.assertEqual(session.query(SyncCursorOrm).count(), 0)
        finally:
            db.engine.dispose()

    def test_same_version_conflicting_clock_is_rolled_back(self):
        db = Database(DbConfig('sqlite+pysqlite:///:memory:'))
        db.create_all()
        try:
            store = CollectorStore(db)
            store.upsert_work_order(work_order_from_payload(member()))
            with self.assertRaises(ValueError):
                store.upsert_work_order(work_order_from_payload(member(actstart='2026-10-31T09:00:00Z')))
            with db.session() as session:
                self.assertEqual(session.get(WorkOrderOrm, 'BSR-TEST').sources['maximo']['actual_dates']['fields']['actstart']['original'], '2026-10-31T08:00:00Z')
        finally:
            db.engine.dispose()

    def test_older_observation_cannot_overwrite_newer_source_values(self):
        db = Database(DbConfig('sqlite+pysqlite:///:memory:'))
        db.create_all()
        try:
            store = CollectorStore(db)
            store.upsert_work_order(work_order_from_payload(member(description='New retained value')))
            store.upsert_work_order(work_order_from_payload(member(changedate='2026-10-01T12:00:00Z', description='Older value')))
            with db.session() as session:
                self.assertEqual(session.get(WorkOrderOrm, 'BSR-TEST').description, 'New retained value')
        finally:
            db.engine.dispose()

    def test_local_projector_carries_description_and_actuals_without_source_calls(self):
        collector = Database(DbConfig('sqlite+pysqlite:///:memory:'))
        mart = Database(DbConfig('sqlite+pysqlite:///:memory:'))
        collector.create_all(); mart.create_all()
        try:
            with collector.session() as session:
                session.add(EquipmentOrm(id='ASSET-1', unit='CS01', sources={'maximo': {'assetnum': 'ASSET-1', 'siteid': 'BSR', 'orgid': 'IP', 'eq11': 'CS01'}}))
                session.commit()
            CollectorStore(collector).upsert_work_order(work_order_from_payload(member()))
            CollectorMartProjector(collector, mart).project_all()
            with mart.session() as session:
                row = session.query(MaintenanceEventMartOrm).one()
                self.assertEqual(row.duration_hours, 2.5)
                self.assertEqual(row.sources['maximo']['description'], 'Synthetic WO description')
                self.assertEqual(row.actual_start.isoformat(), '2026-10-31T08:00:00+00:00')
            with collector.session() as session:
                self.assertEqual(session.query(SyncCursorOrm).count(), 0)
        finally:
            collector.engine.dispose(); mart.engine.dispose()

    def test_local_projector_preserves_the_reason_an_actual_clock_is_unusable(self):
        cases = [
            ({'actstart': '2026-10-31T08:00:00'}, (), 'NAIVE_ACTUAL_START'),
            ({'actfinish': 'invalid'}, (), 'INVALID_ACTUAL_FINISH'),
            ({'actstart': 'x' * 129}, (), 'INVALID_ACTUAL_START'),
            ({'actstart': None}, (), 'MISSING_ACTUAL_START'),
            ({}, ('actstart',), 'UNAVAILABLE_ACTUAL_START'),
            ({}, ('actfinish',), 'UNAVAILABLE_ACTUAL_FINISH'),
            ({'status': 'COMP', 'actstart': 'invalid'}, (), 'NOT_CLOSED'),
        ]
        for changes, omitted, expected in cases:
            with self.subTest(expected=expected):
                collector = Database(DbConfig('sqlite+pysqlite:///:memory:'))
                mart = Database(DbConfig('sqlite+pysqlite:///:memory:'))
                collector.create_all(); mart.create_all()
                try:
                    with collector.session() as session:
                        session.add(EquipmentOrm(id='ASSET-1', unit='CS01', sources={'maximo': {'assetnum': 'ASSET-1', 'siteid': 'BSR', 'orgid': 'IP', 'eq11': 'CS01'}}))
                        session.commit()
                    payload = member(**changes)
                    for field in omitted:
                        del payload[field]
                    CollectorStore(collector).upsert_work_order(work_order_from_payload(payload))
                    CollectorMartProjector(collector, mart).project_all()
                    with mart.session() as session:
                        row = session.query(MaintenanceEventMartOrm).one()
                        self.assertIsNone(row.duration_hours)
                        self.assertEqual(row.sources['maximo']['actual_timing_state'], expected)
                    with collector.session() as session:
                        self.assertEqual(session.query(SyncCursorOrm).count(), 0)
                finally:
                    collector.engine.dispose(); mart.engine.dispose()
