"""Unknown parent semantics stay unknown through mapping, storage and API reads."""
from copy import deepcopy
from dataclasses import asdict
import json
from pathlib import Path
import unittest

from jsonschema import Draft202012Validator, FormatChecker
from src.adapters.maximo.mappers import work_order_from_payload
from src.api.app import _serialize
from src.config import DbConfig
from src.repositories.database import Database
from src.repositories.models import WorkOrderOrm
from src.repositories.store import CollectorStore


class WorkOrderHierarchyTest(unittest.TestCase):
    def test_pctaskid_and_wogroup_never_become_a_parent_number(self):
        payload = {'wonum': 'BSR-TEST', 'status': 'CLOSE', 'pctaskid': '10',
                   'parent': 'BSR-PARENT', 'wogroup': 'BSR-GROUP'}
        entity = work_order_from_payload(payload)
        self.assertIsNone(entity.parent_wo)
        proof = entity.sources['maximo']['hierarchy']
        self.assertEqual(proof['parent_wo_state'], 'UNKNOWN')
        self.assertEqual(proof['source_fields'], {k: payload[k] for k in ('pctaskid', 'parent', 'wogroup')})
        schema = json.loads((Path(__file__).parents[2] / 'reliability-data-contracts/schemas/work-order.schema.json').read_text())
        Draft202012Validator(schema, format_checker=FormatChecker()).validate(asdict(entity))

    def test_unobserved_fields_are_not_synthesized_as_source_nulls(self):
        entity = work_order_from_payload({'wonum': 'BSR-TEST', 'pctaskid': None})
        self.assertEqual(entity.sources['maximo']['hierarchy']['source_fields'], {'pctaskid': None})
        self.assertIsNone(entity.parent_wo)

    def test_legacy_api_value_is_quarantined_without_mutating_orm_or_source(self):
        source = {'maximo': {'wonum': 'BSR-TEST', 'extra': {'bu': 'synthetic'}}}
        row = WorkOrderOrm(id='BSR-TEST', parent_wo='10', sources=deepcopy(source))
        result = _serialize(row)
        self.assertIsNone(result['parent_wo'])
        self.assertEqual(result['sources']['maximo']['hierarchy']['legacy_parent_wo'], '10')
        self.assertNotIn('source_fields', result['sources']['maximo']['hierarchy'])
        self.assertEqual(row.parent_wo, '10')
        self.assertEqual(row.sources, source)

    def test_routine_upsert_retains_legacy_provenance_across_repeated_observations(self):
        db = Database(DbConfig('sqlite+pysqlite:///:memory:'))
        db.create_all()
        try:
            with db.session() as session:
                session.add(WorkOrderOrm(id='BSR-TEST', parent_wo='OLD-UNKNOWN', sources={'maximo': {}}))
                session.commit()
            store = CollectorStore(db)
            for stamp in ('2026-11-01T00:00:00Z', '2026-11-02T00:00:00Z'):
                store.upsert_work_order(work_order_from_payload({'wonum': 'BSR-TEST', 'pctaskid': '20', 'changedate': stamp}))
            with db.session() as session:
                row = session.get(WorkOrderOrm, 'BSR-TEST')
                self.assertIsNone(row.parent_wo)
                proof = row.sources['maximo']['hierarchy']
                self.assertEqual(proof['legacy_parent_wo'], 'OLD-UNKNOWN')
                self.assertEqual(proof['source_fields'], {'pctaskid': '20'})
        finally:
            db.engine.dispose()
