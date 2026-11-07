"""Hermetic manual inventory tests. No Maximo network or operational data."""
from contextlib import contextmanager
from datetime import datetime, timezone
from unittest import TestCase
from sqlalchemy import select
from src.config import DbConfig
from src.repositories.database import Database
from src.repositories.store import CollectorStore
from src.repositories.models import EquipmentOrm, WorkOrderOrm, SyncCursorOrm
from src.repositories.asset_inventory import AssetInventoryStore, AssetInventoryOrm
from src.services.asset_inventory import classify, resolve_scope, refresh_inventory
from src.adapters.maximo.mappers import equipment_from_payload
from src.adapters.maximo.oslc_client import OslcPaginationLimitError

REF={'sha256':'a'*64,'name':'synthetic.xlsx','index':{
 'ROOT':[{'role':'S','row':2,'column':'old_kks'}],
 'E1':[{'role':'E','row':3,'column':'old_kks'}],
 'C1':[{'role':'C','row':4,'column':'old_kks'}],
 'P1':[{'role':'P','row':5,'column':'old_kks'}],
 'CLASH':[{'role':'E','row':6,'column':'old_kks'},{'role':'C','row':7,'column':'new_kks'}]}}

def raw(identity,unit=None,parent=None,**values):
 return {'assetnum':identity,'siteid':'BSR','orgid':'IP','eq11':unit,'parent':parent,
         'changedate':'2020-01-01T00:00:00Z','description':'synthetic','status':'OPERATING',**values}
class Client:
 def __init__(self,pages,error=None):self.pages=pages;self.error=error;self.request_telemetry={'business_requests':0};self.calls=[]
 @contextmanager
 def bounded_requests(self,limit):self.limit=limit;yield
 def iterate_pages(self,name,**kw):
  self.calls.append((name,kw))
  for page in self.pages:
   if self.request_telemetry['business_requests']>=self.limit: raise RuntimeError('budget')
   self.request_telemetry['business_requests']+=1;yield page
  if self.error:raise self.error

class TestStore(CollectorStore):
 @contextmanager
 def work_order_recovery_lock(self): yield True

class InventoryTests(TestCase):
 def setUp(self):
  self.db=Database(DbConfig(dsn='sqlite+pysqlite:///:memory:'));self.db.create_all()
  self.store=TestStore(self.db);AssetInventoryStore(self.db).create_tables()
 def tearDown(self):self.db.engine.dispose()
 def test_roles_exact_and_conflicts_unknown(self):
  self.assertEqual(classify('E1',REF)[0],'equipment');self.assertEqual(classify('E1x',REF)[0],'unknown')
  self.assertEqual(classify('CLASH',REF)[0],'unknown');self.assertEqual(classify('e1',REF)[0],'unknown')
 def test_all_depths_cycle_and_explicit_unit_boundary(self):
  rows=[raw('ROOT'),raw('E1','CS01','ROOT'),raw('C1',parent='E1'),raw('P1',parent='C1'),
        raw('SIBLING',parent='ROOT'),raw('OTHER','CS02','E1'),raw('OTHERCHILD',parent='OTHER'),
        raw('X',parent='Y'),raw('Y',parent='X'),raw('FOREIGN','CS01',siteid='OTHER')]
  self.assertEqual(resolve_scope(rows),{'E1':'DIRECT_SOURCE_UNIT','C1':'SOURCE_PARENT_CHAIN',
   'P1':'SOURCE_PARENT_CHAIN','ROOT':'SOURCE_ANCESTOR_CONTEXT'})
 def test_manual_scan_inserts_all_levels_without_unit_or_wo_rewrite(self):
  client=Client([[raw('ROOT'),raw('E1','CS01','ROOT')],[raw('C1',parent='E1'),raw('P1',parent='C1'),raw('OTHER','CS02')]])
  result=refresh_inventory(self.store,REF,client=client)
  self.assertTrue(result['full_source_baseline_complete']);self.assertEqual(result['inserted'],4)
  with self.db.session() as session:
   self.assertIsNone(session.get(EquipmentOrm,'C1').unit)
   self.assertIsNone(session.get(EquipmentOrm,'OTHER'))
   self.assertEqual(session.query(WorkOrderOrm).count(),0);self.assertEqual(session.query(SyncCursorOrm).count(),0)
  self.assertEqual(client.calls[0][1]['where'],'siteid="BSR"')
  self.assertFalse(client.calls[0][1]['allow_resource_links'])
 def test_source_error_partial_not_complete(self):
  result=refresh_inventory(self.store,REF,client=Client([[raw('E1','CS01')]],RuntimeError('do not leak secret')))
  self.assertFalse(result['full_source_baseline_complete']);self.assertEqual(result['inserted'],1)
  self.assertNotIn('secret',str(result));self.assertEqual(result['errors'],1)
 def test_bad_scope_page_not_admitted(self):
  result=refresh_inventory(self.store,REF,client=Client([[raw('E1','CS01'),raw('FOREIGN','CS01',orgid='OTHER')]]))
  self.assertEqual(result['source_rows'],0);self.assertEqual(result['inserted'],0)
 def test_older_source_does_not_overwrite_newer_local(self):
  self.store.upsert_equipment(equipment_from_payload(raw('E1','CS01',description='newer',changedate='2026-01-01T00:00:00Z')))
  result=refresh_inventory(self.store,REF,client=Client([[raw('E1','CS01',description='older')]]))
  self.assertEqual(result['unchanged'],1)
  with self.db.session() as session:self.assertEqual(session.get(EquipmentOrm,'E1').description,'newer')
 def test_manual_refresh_and_regular_baseline_are_separate(self):
  self.store.upsert_equipment(equipment_from_payload(raw('E1','CS01',description='original')))
  self.store.upsert_equipment(equipment_from_payload(raw('E1','CS01',description='routine')))
  with self.db.session() as session:self.assertEqual(session.get(EquipmentOrm,'E1').description,'original')
  refresh_inventory(self.store,REF,client=Client([[raw('E1','CS01',description='manual')]]))
  with self.db.session() as session:
   row=session.get(EquipmentOrm,'E1');self.assertEqual(row.description,'manual')
   self.assertIn('collector_updated_at',row.sources['maximo'])
 def test_local_only_never_claims_full_source(self):
  self.store.upsert_equipment(equipment_from_payload(raw('E1','CS01')))
  result=refresh_inventory(self.store,REF)
  self.assertEqual(result['requests'],0);self.assertFalse(result['full_source_baseline_complete'])
 def test_budget_validation(self):
  for kw in ({'max_requests':501},{'max_seconds':901}):
   with self.assertRaises(ValueError):refresh_inventory(self.store,REF,**kw)

 def test_missing_source_unit_never_uses_plant_or_derived_unit(self):
  with self.db.session() as session:
   session.add(EquipmentOrm(id='E1',unit='CS01',sources={'maximo':{'assetnum':'E1','siteid':'BSR','orgid':'IP'}}));session.commit()
  result=refresh_inventory(self.store,REF)
  self.assertEqual(result['inventory_assets'],0)
 def test_duplicate_on_same_page_is_rejected_as_partial(self):
  result=refresh_inventory(self.store,REF,client=Client([[raw('E1','CS01'),raw('E1','CS01')]]))
  self.assertFalse(result['full_source_baseline_complete']);self.assertEqual(result['inserted'],0)
 def test_deadline_checked_before_first_source_page(self):
  client=Client([[raw('E1','CS01')]]);times=iter([0,181])
  result=refresh_inventory(self.store,REF,client=client,monotonic=lambda:next(times))
  self.assertEqual(result['requests'],0);self.assertEqual(result['stop_reason'],'TIME_BUDGET')
 def test_source_busy_sends_no_request(self):
  @contextmanager
  def busy(): yield False
  self.store.work_order_recovery_lock=busy
  client=Client([[raw('E1','CS01')]])
  result=refresh_inventory(self.store,REF,client=client)
  self.assertEqual(result['stop_reason'],'SOURCE_BUSY');self.assertEqual(result['requests'],0)
 def test_older_source_does_not_replace_newer_unit_scope(self):
  self.store.upsert_equipment(equipment_from_payload(raw('E1','CS02',changedate='2026-01-01T00:00:00Z')))
  result=refresh_inventory(self.store,REF,client=Client([[raw('E1','CS01')]]))
  self.assertEqual(result['inventory_assets'],0)
 def test_missing_optional_value_preserves_core_and_quarantined_source(self):
  self.store.upsert_equipment(equipment_from_payload(raw('E1','CS01',status='OPERATING')))
  self.store.upsert_equipment_manual(equipment_from_payload(raw('E1','CS01',status=None)),raw=raw('E1','CS01',status=None))
  with self.db.session() as session:
   row=session.get(EquipmentOrm,'E1');self.assertEqual(row.status,'OPERATING')
   self.assertEqual(row.sources['maximo']['status'],'OPERATING')

 def test_source_removed_unit_cannot_be_reenrolled_by_local_refresh(self):
  refresh_inventory(self.store,REF,client=Client([[raw('E1','CS01')]]))
  moved=refresh_inventory(self.store,REF,client=Client([[raw('E1','CS02',changedate='2026-01-01T00:00:00Z')]]))
  self.assertEqual(moved['inventory_assets'],0)
  self.assertEqual(refresh_inventory(self.store,REF)['inventory_assets'],0)
  with self.db.session() as session:self.assertIsNotNone(session.get(EquipmentOrm,'E1'))
 def test_explicit_scope_null_and_parent_root_not_replaced_with_old_evidence(self):
  self.store.upsert_equipment(equipment_from_payload(raw('C1','CS01','OLD_PARENT')))
  payload=raw('C1',None,None,changedate='2026-01-01T00:00:00Z')
  self.store.upsert_equipment_manual(equipment_from_payload(payload),raw=payload)
  with self.db.session() as session:
   row=session.get(EquipmentOrm,'C1');self.assertIsNone(row.sources['maximo']['eq11'])
   self.assertIsNone(row.sources['maximo']['parent']);self.assertIsNone(row.parent_id)

 def test_manual_page_size_stays_explicit_and_bounded(self):
  client=Client([[raw('E1','CS01')]])
  refresh_inventory(self.store,REF,client=client,page_size=100)
  self.assertEqual(client.calls[0][1]['page_size'],100)
  with self.assertRaises(ValueError):refresh_inventory(self.store,REF,page_size=200)

 def test_manual_unit_remains_explicit_including_null_despite_plant(self):
  old=raw('C1','CS01',plant='BSR')
  self.store.upsert_equipment(equipment_from_payload(old))
  for identity in ('C1','P1'):
   payload=raw(identity,None,'E1',plant='BSR',changedate='2026-01-01T00:00:00Z')
   self.store.upsert_equipment_manual(equipment_from_payload(payload),raw=payload)
   with self.db.session() as session:
    row=session.get(EquipmentOrm,identity);self.assertIsNone(row.unit)
    self.assertEqual(row.sources['maximo']['plant'],'BSR')
