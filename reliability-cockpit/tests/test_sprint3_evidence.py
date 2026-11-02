"""Real read repository/API against isolated synthetic SQLite, no live/source IO."""
import copy
import json
import time
from pathlib import Path
import unittest
from datetime import timedelta
from unittest.mock import patch
from sqlalchemy import event, insert, select, func
from sqlalchemy.orm import Session
from src.config import MartDbConfig
from src.repositories.mart_database import MartDatabase
from src.repositories.mart_models import MartBase, AssetMasterMart, MaintenanceEventMart, ReliabilityAssetRegistryMart
from src.repositories.mart_reader import MartQueryRepository
from src.api import reliability as api
from src.services.condition_query import AssetConditionEvidence
from test_reliability_mart import _common, NOW, ASSET_A, ASSET_B

class Sprint3EvidenceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db=MartDatabase(MartDbConfig(dsn='sqlite+pysqlite:///:memory:'))
        MartBase.metadata.create_all(cls.db.engine)
        with Session(cls.db.engine) as s:
            for asset in [ASSET_A,ASSET_B]:
                s.add(AssetMasterMart(**_common(asset,'MXASSET'),source_asset_number=asset.rsplit(':',1)[-1]))
                s.add(ReliabilityAssetRegistryMart(asset_ref=asset,source_asset_number=asset,site_code='BSR',organization_code='IP',registry_source='SYNTHETIC',snapshot_sha256='a'*64,snapshot_row_count=2,snapshot_imported_at=NOW))
            s.execute(insert(MaintenanceEventMart),[dict(**_common(f'maintenance:SYNTHETIC-{i:05}','MXWODETAIL'),id=f'SYNTHETIC-{i}',equipment_id=ASSET_A if i<10000 else ASSET_B,work_order_id=f'WO:SYNTHETIC-{i//2}',event_type='CM' if i%2 else 'PM',status='COMP' if i%3 else 'WAPPR',actual_start=NOW if i%2 else None,actual_finish=None,source_changed_at=NOW+timedelta(days=1)) for i in range(10025)])
            s.commit()
        cls.repository=MartQueryRepository(cls.db)
    @classmethod
    def tearDownClass(cls):cls.db.engine.dispose()

    def test_large_population_bounded_stable_pages_and_readonly(self):
        statements=[]
        def record(conn,cursor,statement,parameters,context,executemany):statements.append(statement)
        event.listen(self.db.engine,'before_cursor_execute',record)
        start=time.perf_counter()
        try:
            seen=set()
            for offset in range(0,1000,25):
                page=self.repository.list_maintenance(asset_ref=ASSET_A,limit=25,offset=offset)
                self.assertEqual(page.total,10000);self.assertEqual(len(page.items),25)
                ids={r.canonical_id for r in page.items};self.assertFalse(ids&seen);seen|=ids
                self.assertTrue(all(r.equipment_id==ASSET_A for r in page.items))
            self.assertLess(time.perf_counter()-start,15,'synthetic gross-regression budget, not operational SLA')
            self.assertEqual(self.repository.list_maintenance(asset_ref=ASSET_A,offset=10000,limit=25).items,[])
            self.assertTrue(all(x.lstrip().upper().startswith('SELECT') for x in statements))
            self.assertTrue(any('LIMIT' in x.upper() for x in statements))
        finally:event.remove(self.db.engine,'before_cursor_execute',record)

    def test_scope_filters_conflicting_wo_and_incomplete_dates_preserved(self):
        page=self.repository.list_maintenance(asset_ref=ASSET_A,work_order_id='WO:SYNTHETIC-0',limit=25)
        self.assertEqual(page.total,2);self.assertEqual(len({r.canonical_id for r in page.items}),2)
        self.assertEqual({r.event_type for r in page.items},{'CM','PM'})
        self.assertTrue(any(r.actual_start is None for r in page.items))
        self.assertTrue(all(r.actual_finish is None for r in page.items))
        self.assertEqual(self.repository.list_maintenance(asset_ref='asset:UNKNOWN',limit=25).total,0)
        self.assertEqual(self.repository.list_maintenance(asset_ref=ASSET_B,limit=25).total,25)
        for kind in ['CM','PM']:
            page=self.repository.list_maintenance(asset_ref=ASSET_A,event_type=kind,status='COMP',limit=25)
            self.assertTrue(all(r.event_type==kind and r.status=='COMP' for r in page.items))
        # Date filtering is activity COALESCE, not failure onset.
        page=self.repository.list_maintenance(asset_ref=ASSET_A,date_from=NOW+timedelta(hours=1),limit=25)
        self.assertEqual(page.total,5000);self.assertTrue(all(r.actual_start is None for r in page.items))

    def test_public_serialization_exposes_only_existing_contract(self):
        from src.services.reliability import ReliabilityQueryService
        page=api.maintenance_events(asset_ref=ASSET_A,work_order_id='WO:SYNTHETIC-0',status=None,event_type=None,date_from=None,date_to=None,offset=0,limit=25,sort='date_desc',service=ReliabilityQueryService(self.repository))
        payload=api.Page[api.MaintenanceView].model_validate(page).model_dump(mode='json')
        self.assertEqual(len(payload['items']),2)
        for row in payload['items']:
            self.assertEqual(row['equipment_id'],ASSET_A)
            for unavailable in ['synced_at','failure_event_id','mtbf','mttr','sources','provenance']:
                self.assertNotIn(unavailable,row)

    def test_browser_fixture_matches_actual_server_condition_contract(self):
        fixture=json.loads((Path(__file__).parents[1]/'web/fixtures/asset-evidence.synthetic.json').read_text())
        payload=AssetConditionEvidence.model_validate(fixture['condition']).model_dump(mode='json')
        self.assertEqual(payload['items'][0]['evidence']['value'],0)
        self.assertIs(payload['items'][1]['evidence']['value'],False)
        self.assertIsNone(payload['items'][2]['evidence']['value'])
        self.assertEqual(payload['items'][4]['evidence']['value']['code'],0)
        self.assertEqual(payload['items'][0]['evidence']['evidence_status'],'BAD_QUALITY')
        self.assertNotEqual(payload['items'][0]['evidence']['source_timestamp'],payload['items'][0]['evidence']['collected_at'])
