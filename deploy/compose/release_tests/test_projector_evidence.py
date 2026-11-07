"""Exercise the projector role using stored Collector output, never source ingest."""
from copy import deepcopy
from datetime import datetime,timezone
import unittest
from src.adapters.maximo.canonical_mappers import maintenance_event_from_payload
from src.adapters.maximo.reliability_fields import evidence
from src.config import DbConfig
from src.repositories.database import Database
from src.repositories.models import EquipmentOrm,WorkOrderOrm
from src.repositories.mart_models import MaintenanceEventMartOrm
from src.repositories.store import CollectorStore
from src.services.local_mart_projector import _work_order_payload,CollectorMartProjector

NOW=datetime(2026,11,7,12,tzinfo=timezone.utc)

def stored():
    source={'wonum':'BSR-SYNTHETIC','assetnum':'ASSET-TEST','siteid':'BSR','orgid':'IP',
        'changedate':NOW.isoformat(),'failurecode':'CLASS-A','problemcode':'PROBLEM-A',
        'downtime':True,'hasfollowupwork':False,'parent':'BSR-PARENT','origrecordclass':'SR',
        'origrecordid':'ORIGIN-A','faildate':'2026-11-07T11:00:00+00:00'}
    return WorkOrderOrm(id=source['wonum'],equipment_id=source['assetnum'],status='APPR',
        work_type='CM',is_task=False,source_changed_at=NOW,failure_code='CLASS-A',downtime_hours=1.0,
        sources={'maximo':{'siteid':'BSR','orgid':'IP','reliability_evidence':evidence(source)}})

class ProjectorEvidenceTest(unittest.TestCase):
    def test_retained_evidence_reaches_canonical_without_boolean_hours(self):
        result=maintenance_event_from_payload(_work_order_payload(stored()))
        self.assertEqual(result['failure_code'],'CLASS-A');self.assertIsNone(result['downtime_hours'])
        proof=result['sources']['maximo']['reliability_evidence']['fields']
        self.assertEqual(proof['problemcode']['value'],'PROBLEM-A')
        self.assertEqual(proof['parent']['value'],'BSR-PARENT')
        self.assertIs(proof['downtime']['value'],True)
        self.assertEqual(proof['faildate']['state'],'VALID')
    def test_missing_evidence_never_recovers_legacy_numeric_downtime(self):
        row=stored();row.sources={'maximo':{'siteid':'BSR','orgid':'IP'}}
        result=maintenance_event_from_payload(_work_order_payload(row))
        self.assertEqual(result['failure_code'],'CLASS-A');self.assertIsNone(result['downtime_hours'])
        self.assertEqual(result['sources']['maximo']['reliability_evidence']['fields']['downtime']['state'],'UNAVAILABLE')
    def test_scope_contradiction_and_untrusted_identity_are_not_repaired(self):
        row=stored();row.sources['maximo']['siteid']='OTHER';self.assertIsNone(_work_order_payload(row))
        row=stored();row.sources['maximo']['reliability_evidence']['identity']['siteid']='OTHER'
        result=maintenance_event_from_payload(_work_order_payload(row))
        self.assertEqual(result['sources']['maximo']['reliability_evidence']['fields']['problemcode']['state'],'UNAVAILABLE')
    def test_projection_is_idempotent_and_preserves_cursor(self):
        db=Database(DbConfig('sqlite+pysqlite:///:memory:'));db.create_all();self.addCleanup(db.engine.dispose)
        with db.session() as session:
            session.add(EquipmentOrm(id='ASSET-TEST',sources={'maximo':{'siteid':'BSR','orgid':'IP'}}))
            session.add(stored());session.commit()
        store=CollectorStore(db);store.set_cursor('mxwodetail',NOW,1);before=store.get_cursor('mxwodetail')
        projector=CollectorMartProjector(db,db,batch_size=1)
        self.assertEqual(projector.project('maintenance_event').rows_inserted,1)
        self.assertEqual(projector.project('maintenance_event').rows_unchanged,1)
        with db.session() as session:
            row=session.query(MaintenanceEventMartOrm).one()
            self.assertEqual(row.failure_code,'CLASS-A');self.assertIsNone(row.downtime_hours)
            self.assertEqual(row.sources['maximo']['reliability_evidence']['fields']['problemcode']['value'],'PROBLEM-A')
        self.assertEqual(store.get_cursor('mxwodetail'),before)
