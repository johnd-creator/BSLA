import copy,unittest
from datetime import timedelta
from sqlalchemy.orm import Session
import test_reliability_mart as fixtures
from test_reliability_mart import NOW,ASSET_A,_common
from src.repositories.mart_models import MaintenanceEventMart
from src.services.wo_overview import wo_overview
from src.api.reliability import _maintenance
from test_wo_sr_classification import record

class ExecutiveEvidenceTest(unittest.TestCase):
 def setUp(self): fixtures.ReliabilityMartReadTest.setUpClass.__func__(type(self))
 def tearDown(self): self.database.engine.dispose()
 def test_modification_never_counts_as_execution_and_duplicate_identity_counts_once(self):
  with Session(self.database.engine) as s:
   for suffix in ('ONE','TWO'):
    data=_common('maintenance:DUP-'+suffix,'MXWODETAIL')
    data['sources']={'maximo':{'wonum':'WO-DUP','assetnum':'ASSET-A','wo_detail':{'schema_version':1,'identity':{'wonum':'WO-DUP','assetnum':'ASSET-A','siteid':'BSR','orgid':'IP'},'fields':{'reported_at':{'state':'RETAINED_LEGACY_VALUE','epoch_seconds':(NOW-timedelta(days=2)).timestamp()}}}}}
    s.add(MaintenanceEventMart(**data,id='DUP-'+suffix,work_order_id='WO-DUP',equipment_id=ASSET_A,status='WAPPR',source_changed_at=NOW))
   s.commit()
  data=wo_overview(self.database,as_of=NOW)
  self.assertEqual(data['counts']['reported'],1)
  self.assertEqual(data['counts']['actual_started'],0)
  self.assertEqual(data['counts']['actual_finished'],0)
  self.assertGreater(data['counts']['record_modified'],data['counts']['reported'])
  self.assertIsNone(data['backlog']['count']);self.assertEqual(data['freshness']['state'],'NOT_EXPOSED')
 def test_report_epoch_is_not_read_from_unverified_field(self):
  with Session(self.database.engine) as s:
   row=s.query(MaintenanceEventMart).filter_by(equipment_id=ASSET_A).first()
   row.sources={'maximo':{'wo_detail':{'fields':{'reported_at':{'epoch_seconds':NOW.timestamp()}}}}};s.commit()
  self.assertEqual(wo_overview(self.database,as_of=NOW)['counts']['reported'],0)

class DetailReadTest(unittest.TestCase):
 def test_allowlist_description_and_source_null_versus_unverified(self):
  r=record(sources={'maximo':{'wonum':'WO-SYNTHETIC','assetnum':'ASSET-SYNTHETIC'}})
  r.source_changed_at=NOW
  r.sources['maximo']['wo_detail']={'schema_version':1,'identity':{'wonum':'WO-SYNTHETIC','assetnum':'ASSET-SYNTHETIC','siteid':'BSR','orgid':'IP'},'source_changed_at':NOW.isoformat(),'fields':{'description':{'value':'Original <script>text</script>','state':'SOURCE_VALUE','origin':'MAXIMO_RESPONSE'},'priority':{'value':None,'state':'SOURCE_CONFIRMED_EMPTY','origin':'MAXIMO_RESPONSE'},'reportedby':{'value':'PRIVATE','state':'SOURCE_VALUE','origin':'MAXIMO_RESPONSE'}}}
  dto=_maintenance(r)
  self.assertEqual(dto.source_detail.fields['description'].value,'Original <script>text</script>')
  self.assertEqual(dto.source_detail.fields['priority'].state,'SOURCE_CONFIRMED_EMPTY')
  self.assertNotIn('PRIVATE',dto.model_dump_json())
  r.source_changed_at=NOW+timedelta(days=1)
  self.assertEqual(_maintenance(r).source_detail.fields,{})
 def test_early_and_advanced_status_never_fabricate_dates(self):
  for status in ('WAPPR','WMATL','COMP','CLOSE'):
   r=record();r.status=status;r.actual_start=None;r.actual_finish=None
   self.assertEqual(_maintenance(r).source_detail.actual_dates_state,'SOURCE_NOT_YET_VERIFIED')
