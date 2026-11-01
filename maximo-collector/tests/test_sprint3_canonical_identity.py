"""Synthetic canonical WO status replay; no collector/source or retained DB calls."""
import copy
import unittest
from sqlalchemy import func, select
from src.adapters.maximo.canonical_mappers import maintenance_event_from_payload
from src.config import DbConfig
from src.repositories.database import Database
from src.repositories.mart_models import MaintenanceEventMartOrm
from src.services.canonical import CanonicalCollection
from src.services.mart import MartWriter
from tests.fixtures.canonical_payloads import WORK_ORDER

class Sprint3CanonicalIdentityTest(unittest.TestCase):
    def test_repeated_source_and_status_updates_have_one_canonical_row(self):
        db=Database(DbConfig('sqlite+pysqlite:///:memory:'));db.create_all()
        try:
            writer=MartWriter(db)
            first=maintenance_event_from_payload(copy.deepcopy(WORK_ORDER))
            self.assertEqual(writer.persist_collection(CanonicalCollection('maintenance_event',records=[first])).records_inserted,1)
            self.assertEqual(writer.persist_collection(CanonicalCollection('maintenance_event',records=[first])).records_unchanged,1)
            update=copy.deepcopy(first);update['status']='SYNTHETIC_UPDATED'
            self.assertEqual(writer.persist_collection(CanonicalCollection('maintenance_event',records=[update])).records_updated,1)
            self.assertEqual(writer.persist_collection(CanonicalCollection('maintenance_event',records=[update])).records_unchanged,1)
            with db.session() as s:
                self.assertEqual(s.scalar(select(func.count()).select_from(MaintenanceEventMartOrm)),1)
                row=s.get(MaintenanceEventMartOrm,first['canonical_id'])
                self.assertEqual(row.status,'SYNTHETIC_UPDATED');self.assertEqual(row.work_order_id,first['work_order_id'])
        finally:db.engine.dispose()
