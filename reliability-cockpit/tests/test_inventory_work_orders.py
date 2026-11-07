"""Hermetic inventory WO scope, chronology and DTO regression checks."""
from datetime import datetime, timedelta, timezone
from unittest import TestCase

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.api.reliability import inventory_maintenance_events, InventoryMaintenancePage
from src.config import MartDbConfig
from src.repositories.asset_inventory import AssetInventoryMart
from src.repositories.inventory_work_orders import InventoryWorkOrderQuery
from src.repositories.mart_database import MartDatabase
from src.repositories.mart_models import AssetMasterMart, MaintenanceEventMart, MartBase, ReliabilityAssetRegistryMart
from src.repositories.mart_reader import MartQueryRepository
from src.services.reliability import ReliabilityQueryService

NOW = datetime(2026, 11, 6, 12, tzinfo=timezone.utc)


class InventoryWorkOrderTests(TestCase):
    def setUp(self):
        self.db = MartDatabase(MartDbConfig(dsn='sqlite+pysqlite:///:memory:'))
        MartBase.metadata.create_all(self.db.engine)
        self.addCleanup(self.db.engine.dispose)
        self.query = InventoryWorkOrderQuery(self.db)
        self.repo = MartQueryRepository(self.db)
        self.service = ReliabilityQueryService(self.repo)
        with Session(self.db.engine) as s:
            for key, site, org, active in [('A', 'BSR', 'IP', True), ('B', 'BSR', 'IP', True), ('FOREIGN', 'OTHER', 'IP', True), ('FOREIGN-ORG', 'BSR', 'OTHER', True), ('INACTIVE', 'BSR', 'IP', False)]:
                s.add(AssetMasterMart(canonical_id='asset:'+key, source_asset_number=key,
                    contract_version='1.0', site_code=site, organization_code=org,
                    sources={}, provenance={}, relationship_evidence={}, mart_created_at=NOW, mart_updated_at=NOW))
                s.add(AssetInventoryMart(asset_id=key, category='component', scope_basis='SOURCE_PARENT_CHAIN',
                    active=active, evidence={}, assessed_at=NOW))
            s.add(ReliabilityAssetRegistryMart(asset_ref='asset:B', source_asset_number='B', site_code='BSR', organization_code='IP', registry_source='SYNTHETIC', snapshot_sha256='a'*64, snapshot_row_count=1, snapshot_imported_at=NOW))
            for key, asset, status, actual, changed, site, org in [
                ('1', 'A', 'CLOSE', NOW, NOW+timedelta(days=5), 'BSR', 'IP'),
                ('2', 'A', 'WAPPR', None, NOW, 'BSR', 'IP'),
                ('3', 'A', 'CAN', None, None, 'BSR', 'IP'),
                ('4', 'B', 'CLOSE', None, NOW, 'BSR', 'IP'),
                ('5', 'FOREIGN', 'CLOSE', None, NOW, 'OTHER', 'IP'),
                ('6', 'FOREIGN-ORG', 'CLOSE', None, NOW, 'BSR', 'OTHER'),
                ('7', 'INACTIVE', 'CLOSE', None, NOW, 'BSR', 'IP'),
                ('8', 'A', 'CLOSE', None, NOW, 'OTHER', 'IP'),
                ('9', 'A', 'CLOSE', None, NOW, 'BSR', 'OTHER'),
            ]:
                s.add(MaintenanceEventMart(canonical_id='maintenance:'+key, id=key, equipment_id='asset:'+asset,
                    work_order_id='wo:'+key, status=status, actual_start=actual, source_changed_at=changed,
                    contract_version='1.0', site_code=site, organization_code=org, reported_by='PRIVATE',
                    sources={'maximo': {'description': 'Synthetic local WO', 'private': 'PRIVATE-RAW'}},
                    provenance={}, relationship_evidence={}, mart_created_at=NOW, mart_updated_at=NOW))
            s.commit()

    def endpoint(self, **kwargs):
        defaults = dict(asset_ref='asset:A', work_order_id=None, status=None, date_from=None, date_to=None,
            offset=0, limit=25, sort='date_desc', service=self.service)
        return inventory_maintenance_events(**(defaults | kwargs))

    def test_non_registry_inventory_work_orders_exist_without_expanding_registry(self):
        self.assertEqual(self.query.list(asset_ref='asset:A').total, 3)
        self.assertEqual(self.repo.list_maintenance(asset_ref='asset:A').total, 0)
        self.assertEqual(self.repo.list_assets().total, 1)
        self.assertEqual(self.repo.list_maintenance().total, 1)
        self.assertEqual(self.query.list(asset_ref='asset:B').total, 1)
        with self.db.read_session() as s:
            self.assertEqual(s.scalar(select(func.count()).select_from(ReliabilityAssetRegistryMart)), 1)

    def test_foreign_inactive_unknown_and_fuzzy_assets_are_not_exposed(self):
        for asset in ['asset:FOREIGN', 'asset:FOREIGN-ORG', 'asset:INACTIVE', 'asset:MISSING', 'asset:A%']:
            self.assertEqual(self.query.list(asset_ref=asset).total, 0)
            with self.assertRaises(HTTPException) as error:
                self.endpoint(asset_ref=asset)
            self.assertEqual(error.exception.status_code, 404)

    def test_dates_use_actual_start_then_change_and_keep_undated_only_without_range(self):
        dated = self.query.list(asset_ref='asset:A', date_from=NOW, date_to=NOW)
        self.assertEqual([r.id for r in dated.items], ['1', '2'])
        self.assertEqual(self.query.list(asset_ref='asset:A', date_from=NOW+timedelta(days=1)).total, 0)
        self.assertEqual(self.query.list(asset_ref='asset:A').total, 3)
        self.assertEqual(self.query.list(asset_ref='asset:A', status='WAPPR').total, 1)
        self.assertEqual(self.query.list(asset_ref='asset:A', work_order_id='wo:4').total, 0)

    def test_pagination_is_stable_for_equal_dates_and_nulls_are_last(self):
        for sort in ['date_asc', 'date_desc']:
            rows = [self.query.list(asset_ref='asset:A', offset=i, limit=1, sort=sort).items[0].id for i in range(3)]
            self.assertEqual(rows, ['1', '2', '3'])
        self.assertTrue(self.query.list(asset_ref='asset:A', limit=1).has_more)
        self.assertFalse(self.query.list(asset_ref='asset:A', offset=2, limit=1).has_more)

    def test_endpoint_is_allowlisted_and_carries_explicit_inventory_scope(self):
        result = InventoryMaintenancePage.model_validate(self.endpoint()).model_dump(mode='json')
        self.assertEqual(result['scope']['population'], 'COLLECTED_HIERARCHY')
        self.assertEqual(result['scope']['asset_ref'], 'asset:A')
        self.assertEqual(result['scope']['date_basis'], 'ACTUAL_START_OR_SOURCE_CHANGED')
        self.assertEqual(result['meta']['total'], 3)
        self.assertNotIn('PRIVATE', str(result))
        self.assertNotIn('sources', result['items'][0])

    def test_invalid_or_naive_date_bounds_are_rejected(self):
        for bounds in [dict(date_from=NOW+timedelta(days=1), date_to=NOW), dict(date_from=NOW.replace(tzinfo=None)), dict(date_to=NOW.replace(tzinfo=None))]:
            with self.assertRaises(HTTPException) as error:
                self.endpoint(**bounds)
            self.assertEqual(error.exception.status_code, 422)
        for query in [dict(asset_ref=''), dict(asset_ref='asset:A', limit=201), dict(asset_ref='asset:A', offset=-1), dict(asset_ref='asset:A', sort='unsafe')]:
            with self.assertRaises(ValueError):
                self.query.list(**query)
