"""Yearly summaries use all unique WOs and actual-start calendar years only."""
from datetime import datetime, timezone
from unittest import TestCase
from fastapi import HTTPException
from sqlalchemy.orm import Session
from src.api.reliability import AnnualWorkOrderSummary, annual_work_order_summary
from src.config import MartDbConfig
from src.repositories.asset_inventory import AssetInventoryMart
from src.repositories.annual_work_orders import AnnualWorkOrderQuery
from src.repositories.mart_database import MartDatabase
from src.repositories.mart_models import AssetMasterMart, MaintenanceEventMart, MartBase, ReliabilityAssetRegistryMart
from src.repositories.mart_reader import MartQueryRepository
from src.services.reliability import ReliabilityQueryService

NOW = datetime(2026, 11, 6, 12, tzinfo=timezone.utc)


class AnnualWorkOrderTests(TestCase):
    def setUp(self):
        self.db = MartDatabase(MartDbConfig(dsn='sqlite+pysqlite:///:memory:'))
        MartBase.metadata.create_all(self.db.engine)
        self.addCleanup(self.db.engine.dispose)
        self.query = AnnualWorkOrderQuery(self.db)
        self.service = ReliabilityQueryService(MartQueryRepository(self.db))
        with Session(self.db.engine) as s:
            for key in ['A', 'EMPTY']:
                s.add(AssetMasterMart(canonical_id='asset:'+key, source_asset_number=key,
                    contract_version='1.0', site_code='BSR', organization_code='IP', sources={},
                    provenance={}, relationship_evidence={}, mart_created_at=NOW, mart_updated_at=NOW))
                s.add(AssetInventoryMart(asset_id=key, category='equipment', scope_basis='SOURCE_PARENT_CHAIN',
                    active=True, evidence={}, assessed_at=NOW))
            s.add(ReliabilityAssetRegistryMart(asset_ref='asset:EMPTY', source_asset_number='EMPTY', site_code='BSR', organization_code='IP', registry_source='SYNTHETIC', snapshot_sha256='a'*64, snapshot_row_count=1, snapshot_imported_at=NOW))
            rows = [(str(i), 'wo:'+str(i), datetime(2024,6,1,tzinfo=timezone.utc), 'PM', 'CLOSE') for i in range(34)]
            rows += [('C'+str(i), 'wo:C'+str(i), datetime(2025,12,31,16,59,59,tzinfo=timezone.utc), 'CM', 'WAPPR') for i in range(3)]
            rows += [('BOUNDARY', 'wo:BOUNDARY', datetime(2025,12,31,17,tzinfo=timezone.utc), 'PM', 'APPR'),
                ('U1', 'wo:U1', None, 'PDM', 'CLOSE'), ('U2', 'wo:U2', None, None, None),
                ('D1', 'wo:DUPLICATE', datetime(2024,1,1,tzinfo=timezone.utc), 'PM','CLOSE'),
                ('D2', 'wo:DUPLICATE', datetime(2025,1,1,tzinfo=timezone.utc), 'PM','CLOSE'),
                ('MISSING', None, datetime(2024,1,1,tzinfo=timezone.utc), 'PM','CLOSE')]
            for key, identity, actual, kind, status in rows:
                s.add(MaintenanceEventMart(canonical_id='maintenance:'+key, id=key, equipment_id='asset:A',
                    work_order_id=identity, status=status, actual_start=actual, source_changed_at=NOW,
                    contract_version='1.0', site_code='BSR', organization_code='IP', reported_by='PRIVATE',
                    sources={'maximo': {'worktype': kind, 'private': 'PRIVATE'}}, provenance={},
                    relationship_evidence={}, mart_created_at=NOW, mart_updated_at=NOW))
            s.commit()

    def summary(self):
        return self.query.summary(asset_ref='asset:A', population='COLLECTED_HIERARCHY')

    def test_full_population_and_reconciliation(self):
        data = self.summary()
        self.assertEqual(data['counts'], dict(record_count=43, work_order_count=41, duplicate_work_order_count=1,
            duplicate_record_count=2, missing_identity_record_count=1, dated_work_order_count=38, unknown_date_work_order_count=2))
        self.assertEqual([(y['year'],y['work_orders']) for y in data['years']], [(2026,1),(2025,3),(2024,34)])
        for bucket in data['years'] + [data['unknown_year']]:
            for key in ['work_types', 'statuses']:
                self.assertEqual(sum(x['count'] for x in bucket[key]),bucket['work_orders'])

    def test_year_drilldown_is_complete_and_disjoint(self):
        query = dict(asset_ref='asset:A', population='COLLECTED_HIERARCHY',year='2024')
        first, second = self.query.list_year(**query), self.query.list_year(**query,offset=25)
        self.assertEqual((first.total,len(first.items),len(second.items)),(34,25,9))
        self.assertFalse(set(x.id for x in first.items) & set(x.id for x in second.items))
        self.assertNotIn('wo:DUPLICATE', [x.work_order_id for x in first.items+second.items])
        self.assertEqual(self.query.list_year(**(query|dict(year='2025',status='WAPPR'))).total,3)

    def test_wib_boundary_and_unknown_have_no_changedate_fallback(self):
        query = dict(asset_ref='asset:A', population='COLLECTED_HIERARCHY')
        self.assertEqual([x.id for x in self.query.list_year(**query,year='2026').items],['BOUNDARY'])
        self.assertEqual(self.query.list_year(**query,year='unknown').total,2)
        self.assertEqual(self.summary()['unknown_year']['work_types'],[{'value':None,'count':1},{'value':'PDM','count':1}])
        self.assertEqual(self.summary()['years'][1]['work_types'],[{'value':'CM','count':3}])

    def test_registry_does_not_expand_and_missing_assets_fail_closed(self):
        for population, asset in [('REGISTRY','asset:A'),('COLLECTED_HIERARCHY','asset:MISSING')]:
            with self.assertRaises(HTTPException) as error:
                annual_work_order_summary(asset_ref=asset,population=population,service=self.service)
            self.assertEqual(error.exception.status_code,404)
        self.assertEqual(self.service.repository.list_assets().total,1)
        with Session(self.db.engine) as s:
            s.get(AssetInventoryMart,'A').active=False
            s.commit()
        with self.assertRaises(LookupError):
            self.summary()

    def test_empty_summary_is_explicit_and_allowlisted(self):
        data = AnnualWorkOrderSummary.model_validate(annual_work_order_summary(asset_ref='asset:EMPTY',population='REGISTRY',service=self.service)).model_dump(mode='json')
        self.assertEqual(data['years'],[])
        self.assertEqual(data['counts']['work_order_count'],0)
        self.assertEqual(data['scope']['time_zone'],'Asia/Jakarta')
        self.assertEqual(data['availability_state'],'REQUIRES_VALIDATED_DCS_HISTORY')
        self.assertNotIn('PRIVATE',str(data))
        self.assertNotIn('duration',str(data))

    def test_invalid_inputs(self):
        for changes in [dict(year='0'),dict(year='10000'),dict(year='2026-01'),dict(limit=201),dict(offset=-1)]:
            with self.assertRaises(ValueError):
                self.query.list_year(**(dict(asset_ref='asset:A',population='COLLECTED_HIERARCHY',year='2024')|changes))
