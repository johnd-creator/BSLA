"""Source-bound executive regressions; reused against mandatory synthetic PG16."""
import copy,unittest
from datetime import timedelta
from sqlalchemy.orm import Session
from src.config import MartDbConfig
from src.repositories.mart_database import MartDatabase
from src.repositories.mart_models import MaintenanceEventMart,AssetMasterMart,ReliabilityAssetRegistryMart,MartBase
from test_reliability_mart import NOW,ASSET_A,_common
from src.services.wo_overview import wo_overview
from src.api.reliability import _maintenance
from test_wo_sr_classification import record

class ExecutiveEvidenceTest(unittest.TestCase):
 dsn='sqlite+pysqlite:///:memory:'
 def setUp(self):
  self.database=MartDatabase(MartDbConfig(dsn=self.dsn))
  self.fixture_engine=getattr(self,'fixture_engine',self.database.engine)
  MartBase.metadata.create_all(self.fixture_engine)
  with Session(self.fixture_engine) as s:
   s.add(AssetMasterMart(**_common(ASSET_A,'MXASSET'),source_asset_number='ASSET-A'))
   s.add(ReliabilityAssetRegistryMart(asset_ref=ASSET_A,source_asset_number='ASSET-A',site_code='BSR',organization_code='IP',registry_source='MAXIMO_LIST_OF_ASSETS',snapshot_sha256='a'*64,snapshot_row_count=1,snapshot_imported_at=NOW));s.commit()
 def tearDown(self):
  MartBase.metadata.drop_all(self.fixture_engine);self.fixture_engine.dispose();self.database.engine.dispose()
 def source(self):
  when=NOW-timedelta(days=2)
  identity={'wonum':'WO-SYNTHETIC','assetnum':'ASSET-A','siteid':'BSR','orgid':'IP'}
  return {'maximo':{'wonum':'WO-SYNTHETIC','assetnum':'ASSET-A',
   'wo_detail':{'schema_version':1,'identity':identity,'source_changed_at':NOW.isoformat(),'fields':{'reported_at':{'value':when.isoformat(),'state':'RETAINED_LEGACY_VALUE','origin':'LEGACY_COLUMN','source_changed_at':NOW.isoformat(),'epoch_seconds':when.timestamp()}}},
   'actual_dates':{'schema_version':1,'identity':identity,'fields':{key:{'state':'VALID','original':when.isoformat(),'normalized':when.isoformat(),'source_changed_at':NOW.isoformat()} for key in ('actstart','actfinish')}}}}
 def add(self,source,*,suffix='ONE',actual=False,asset=ASSET_A,site='BSR'):
  data=_common('maintenance:'+suffix,'MXWODETAIL');data.update(sources=source,site_code=site)
  with Session(self.fixture_engine) as s:
   when=NOW-timedelta(days=2)
   s.add(MaintenanceEventMart(**data,id=suffix,work_order_id='WO-SYNTHETIC',equipment_id=asset,status='WAPPR',source_changed_at=NOW,actual_start=when if actual else None,actual_finish=when if actual else None));s.commit()
 def overview(self):return wo_overview(self.database,as_of=NOW)
 def test_modification_never_counts_as_execution_and_duplicate_identity_counts_once(self):
  self.add(self.source());self.add(self.source(),suffix='TWO')
  data=self.overview()
  self.assertEqual(data['counts'],{'reported':1,'actual_started':0,'actual_finished':0,'record_modified':1})
  self.assertEqual(data['date_coverage']['total_unique_wo'],1)
  self.assertIsNone(data['backlog']['count']);self.assertEqual(data['freshness']['state'],'NOT_EXPOSED')
 def test_valid_older_field_evidence_and_equivalent_offsets_count(self):
  source=self.source()
  for key in ('actstart','actfinish'):
   item=source['maximo']['actual_dates']['fields'][key]
   item['source_changed_at']=(NOW-timedelta(days=1)).isoformat()
   item['original']=(NOW-timedelta(days=2)).astimezone(__import__('datetime').timezone(timedelta(hours=7))).isoformat()
  self.add(source,actual=True)
  self.assertEqual(self.overview()['counts'],{'reported':1,'actual_started':1,'actual_finished':1,'record_modified':1})
 def test_actual_evidence_versions_and_clock_binding(self):
  source=self.source()
  cases=[('source_changed_at',None),('source_changed_at',(NOW+timedelta(days=1)).isoformat()),('original',(NOW-timedelta(days=1)).isoformat()),('normalized','2026-01-13T12:00:00'),('original','2026-02-30T12:00:00Z'),('original','2026-01-13T12:00:00-00:00')]
  for i,(key,value) in enumerate(cases):
   bad=copy.deepcopy(source)
   for field in bad['maximo']['actual_dates']['fields'].values():field[key]=value
   self.add(bad,suffix=str(i),actual=True)
  data=self.overview();self.assertEqual(data['counts']['actual_started'],0);self.assertEqual(data['counts']['actual_finished'],0)
 def test_report_evidence_requires_value_epoch_origin_and_versions(self):
  cases=[('value',None),('value','2026-02-30T12:00:00Z'),('value','2026-01-13T12:00:00'),('epoch_seconds',NOW.timestamp()),('origin','GUESSED'),('source_changed_at',None),('source_changed_at',(NOW+timedelta(days=1)).isoformat())]
  for i,(key,value) in enumerate(cases):
   source=self.source();source['maximo']['wo_detail']['fields']['reported_at'][key]=value;self.add(source,suffix=str(i))
  source=self.source();source['maximo']['wo_detail']['source_changed_at']=(NOW-timedelta(days=1)).isoformat();self.add(source,suffix='BADROOT')
  self.assertEqual(self.overview()['counts']['reported'],0)
 def test_malformed_json_is_withheld_without_cast_failure(self):
  cases=[None,True,False,'1','invalid',{},[],10**300]
  for i,value in enumerate(cases):
   source=self.source();source['maximo']['wo_detail']['schema_version']=value;source['maximo']['actual_dates']['schema_version']=value;self.add(source,suffix='schema'+str(i),actual=True)
   source=self.source();source['maximo']['wo_detail']['fields']['reported_at']['epoch_seconds']=value;source['maximo'].pop('actual_dates');self.add(source,suffix='epoch'+str(i))
  data=self.overview();self.assertEqual(data['counts']['reported'],0);self.assertEqual(data['counts']['actual_started'],0)
  self.assertEqual(data['status_snapshot'],[{'value':'WAPPR','count':1}])
 def test_wide_unrelated_source_evidence_does_not_change_verified_date_bases(self):
  source=self.source();source['maximo']['unrelated_vendor_fields']={str(i):'X'*4000 for i in range(20)}
  self.add(source,actual=True)
  data=self.overview();self.assertEqual(data['counts'],{'reported':1,'actual_started':1,'actual_finished':1,'record_modified':1})
  self.assertEqual(data['date_coverage']['total_unique_wo'],1)
 def test_only_registered_bsr_ip_counts(self):
  self.add(self.source(),site='OTHER')
  self.add(self.source(),suffix='TECH',asset='asset:TECHNICAL-ONLY')
  data=self.overview();self.assertEqual(data['date_coverage']['total_unique_wo'],0);self.assertEqual(data['status_snapshot'],[])

class DetailReadTest(unittest.TestCase):
 def detail(self):
  r=record(sources={'maximo':{'wonum':'WO-SYNTHETIC','assetnum':'ASSET-SYNTHETIC'}});r.source_changed_at=NOW
  fields={'description':{'value':'Original <script>text</script>','state':'SOURCE_VALUE','origin':'MAXIMO_RESPONSE','source_changed_at':NOW.isoformat()},'priority':{'value':None,'state':'SOURCE_CONFIRMED_EMPTY','origin':'MAXIMO_RESPONSE','source_changed_at':NOW.isoformat()},'reportedby':{'value':'PRIVATE','state':'SOURCE_VALUE','origin':'MAXIMO_RESPONSE','source_changed_at':NOW.isoformat()}}
  r.sources['maximo']['wo_detail']={'schema_version':1,'identity':{'wonum':'WO-SYNTHETIC','assetnum':'ASSET-SYNTHETIC','siteid':'BSR','orgid':'IP'},'source_changed_at':NOW.isoformat(),'fields':fields};return r
 def test_allowlist_description_and_source_null_versus_unverified(self):
  r=self.detail();dto=_maintenance(r)
  self.assertEqual(dto.source_detail.fields['description'].value,'Original <script>text</script>')
  self.assertEqual(dto.source_detail.fields['priority'].state,'SOURCE_CONFIRMED_EMPTY');self.assertNotIn('PRIVATE',dto.model_dump_json())
  r.source_changed_at=NOW+timedelta(days=1);self.assertEqual(_maintenance(r).source_detail.fields,{})
 def test_absent_future_and_old_null_field_versions_withheld(self):
  for value in (None,(NOW+timedelta(days=1)).isoformat()):
   r=self.detail()
   for item in r.sources['maximo']['wo_detail']['fields'].values():item['source_changed_at']=value
   self.assertEqual(_maintenance(r).source_detail.fields,{})
  r=self.detail()
  for item in r.sources['maximo']['wo_detail']['fields'].values():item['source_changed_at']=(NOW-timedelta(days=1)).isoformat()
  self.assertIn('description',_maintenance(r).source_detail.fields);self.assertNotIn('priority',_maintenance(r).source_detail.fields)
 def test_early_and_advanced_status_never_fabricate_dates(self):
  for status in ('WAPPR','WMATL','COMP','CLOSE'):
   r=record();r.status=status;r.actual_start=None;r.actual_finish=None
   self.assertEqual(_maintenance(r).source_detail.actual_dates_state,'SOURCE_NOT_YET_VERIFIED')
