"""Conservative legacy compatibility; no production source or store access."""
from copy import deepcopy
import unittest

from src.adapters.collector_client import work_order_from_view
from src.adapters.maximo.mappers import work_order_from_payload
from src.config import DbtConfig
from src.repositories.database import Database
from src.repositories.models import WorkOrderOrm
from src.repositories.store import CockpitStore


class WorkOrderHierarchyTest(unittest.TestCase):
    def test_source_adapter_does_not_alias_pctaskid_to_parent(self):
        entity = work_order_from_payload({'wonum': 'TEST', 'pctaskid': '10', 'parent': 'PARENT', 'wogroup': 'GROUP'})
        self.assertIsNone(entity.parent_wo)
        self.assertEqual(entity.sources['maximo']['hierarchy']['source_fields'], {'pctaskid': '10', 'parent': 'PARENT', 'wogroup': 'GROUP'})

    def test_old_collector_view_is_quarantined_without_mutating_it(self):
        view = {'id': 'TEST', 'parent_wo': '10', 'sources': {'maximo': {'wonum': 'TEST'}}}
        before = deepcopy(view)
        entity = work_order_from_view(view)
        self.assertIsNone(entity.parent_wo)
        self.assertEqual(entity.sources['maximo']['hierarchy']['legacy_parent_wo'], '10')
        self.assertEqual(entity.sources['maximo']['hierarchy']['parent_wo_state'], 'UNKNOWN')
        self.assertEqual(view, before)

    def test_existing_legacy_store_value_is_read_as_unknown_without_repair(self):
        db = Database(DbtConfig('sqlite+pysqlite:///:memory:'))
        db.create_all()
        try:
            with db.session() as session:
                session.add(WorkOrderOrm(id='TEST', parent_wo='OLD-UNKNOWN'))
                session.commit()
            store = CockpitStore(db)
            # Future routine sync also leaves the old observation intact.
            store.upsert_work_order(work_order_from_view({'id': 'TEST', 'parent_wo': 'NEW-UNPROVEN'}))
            entity = store.list_work_orders()[0]
            self.assertIsNone(entity.parent_wo)
            self.assertEqual(entity.sources['maximo']['hierarchy']['legacy_parent_wo'], 'OLD-UNKNOWN')
            with db.session() as session:
                self.assertEqual(session.get(WorkOrderOrm, 'TEST').parent_wo, 'OLD-UNKNOWN')
        finally:
            db._engine.dispose()
