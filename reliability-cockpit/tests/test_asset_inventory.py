from datetime import datetime,timezone
from unittest import TestCase
from sqlalchemy.orm import Session
from src.config import MartDbConfig
from src.repositories.mart_database import MartDatabase
from src.repositories.mart_models import MartBase,AssetMasterMart,ReliabilityAssetRegistryMart
from src.repositories.asset_inventory import AssetInventoryMart,AssetInventoryScanMart,InventoryQuery
from src.repositories.mart_reader import MartQueryRepository
from src.api.reliability import _inventory_asset,router

NOW=datetime.now(timezone.utc)
class AssetInventoryTests(TestCase):
 def setUp(self):
  self.db=MartDatabase(MartDbConfig(dsn='sqlite+pysqlite:///:memory:'));MartBase.metadata.create_all(self.db.engine)
  self.query=InventoryQuery(self.db)
 def tearDown(self):self.db.engine.dispose()
 def add(self,identity,category='equipment',site='BSR',registered=False,active=True):
  with Session(self.db.engine) as s:
   s.add(AssetMasterMart(canonical_id='asset:'+identity,source_asset_number=identity,site_code=site,organization_code='IP',
    contract_version='1.0',sources={},provenance={},relationship_evidence={},mart_created_at=NOW,mart_updated_at=NOW))
   s.add(AssetInventoryMart(asset_id=identity,category=category,scope_basis='DIRECT_SOURCE_UNIT',active=active,evidence={},assessed_at=NOW))
   if registered:s.add(ReliabilityAssetRegistryMart(asset_ref='asset:'+identity,source_asset_number=identity,site_code=site,organization_code='IP',
    registry_source='SYNTHETIC',snapshot_sha256='a'*64,snapshot_row_count=1,snapshot_imported_at=NOW))
   s.commit()
 def test_global_counts_ignore_pagination_include_system_and_unknown(self):
  for key,cat in [('S','system'),('E','equipment'),('C','component'),('P','part'),('U','unknown')]:self.add(key,cat)
  self.add('FOREIGN',site='OTHER');self.add('INACTIVE',active=False)
  summary=self.query.summary();self.assertEqual(summary['counts'],dict(total=5,system=1,equipment=1,component=1,part=1,unknown=1))
  self.assertEqual(self.query.list(limit=1).total,5);self.assertEqual(len(self.query.list(limit=1).items),1)
  self.assertEqual(summary['coverage']['state'],'PARTIAL')
 def test_inventory_does_not_expand_registry(self):
  self.add('E',registered=True);self.add('C','component')
  self.assertEqual(MartQueryRepository(self.db).list_assets().total,1)
  self.assertEqual(self.query.list().total,2)
  self.assertFalse(_inventory_asset(self.query.get('asset:C')).registered)
  self.assertTrue(_inventory_asset(self.query.get('asset:E')).registered)
  self.assertIsNone(self.query.get('asset:missing'))
 def test_complete_source_and_pending_projection_are_separate(self):
  with Session(self.db.engine) as s:
   s.add(AssetInventoryScanMart(started_at=NOW,finished_at=NOW,result={'full_source_baseline_complete':True}))
   s.add(AssetInventoryMart(asset_id='PENDING',category='part',scope_basis='SOURCE_PARENT_CHAIN',active=True,evidence={},assessed_at=NOW));s.commit()
  coverage=self.query.summary()['coverage']
  self.assertEqual(coverage['state'],'PARTIAL');self.assertTrue(coverage['full_source_baseline_complete']);self.assertEqual(coverage['pending_projection'],1)
 def test_route_static_before_dynamic(self):
  paths=[r.path for r in router.routes]
  self.assertLess(paths.index('/v1/reliability/assets/inventory-summary'),paths.index('/v1/reliability/assets/{canonical_id}'))
 def test_summary_preserves_no_official_legend_warning(self):
  self.assertEqual(self.query.summary()['classification']['status'],'INDICATIVE_DOCUMENT_ROLE')
