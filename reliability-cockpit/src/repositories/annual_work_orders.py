"""Full-population yearly WO context, never an availability or incident metric."""
from __future__ import annotations

from sqlalchemy import Integer, case, cast, func, or_, select, true

from src.repositories.asset_inventory import InventoryQuery
from src.repositories.mart_models import AssetMasterMart, MaintenanceEventMart as WO, ReliabilityAssetRegistryMart
from src.repositories.mart_reader import MartQueryRepository, _page


class AnnualWorkOrderQuery:
    def __init__(self, database):
        self.database = database

    def _relations(self, asset_ref, population):
        if population == 'COLLECTED_HIERARCHY':
            if InventoryQuery(self.database).get(asset_ref) is None:
                raise LookupError('inventory asset not found')
            membership = InventoryQuery.base().with_only_columns(AssetMasterMart.canonical_id)
        elif population == 'REGISTRY':
            if MartQueryRepository(self.database).get_asset(asset_ref) is None:
                raise LookupError('registered asset not found')
            membership = select(ReliabilityAssetRegistryMart.asset_ref).where(
                ReliabilityAssetRegistryMart.site_code == 'BSR', ReliabilityAssetRegistryMart.organization_code == 'IP')
        else:
            raise ValueError('invalid WO population')
        missing_identity = or_(WO.work_order_id.is_(None), func.trim(WO.work_order_id) == '')
        identity = case((missing_identity, None), else_=WO.work_order_id)
        if self.database.engine.dialect.name == 'postgresql':
            year = cast(func.extract('year', func.timezone('Asia/Jakarta', WO.actual_start)), Integer)
        else:
            # Hermetic SQLite fixture dates are stored as UTC, as in the local store.
            year = cast(func.strftime('%Y', func.datetime(WO.actual_start, '+7 hours')), Integer)
        work_type = func.coalesce(func.nullif(func.trim(WO.sources['maximo']['worktype'].as_string()), ''),
                                  func.nullif(func.trim(WO.event_type), ''))
        records = select(WO.canonical_id, identity.label('wo_identity'), year.label('year'),
                         work_type.label('work_type'), func.nullif(func.trim(WO.status), '').label('status')).where(
            WO.site_code == 'BSR', WO.organization_code == 'IP', WO.equipment_id == asset_ref,
            WO.equipment_id.in_(membership)).cte('annual_records')
        identities = select(records.c.wo_identity, func.count().label('rows')).where(
            records.c.wo_identity.is_not(None)).group_by(records.c.wo_identity).cte('annual_identities')
        eligible = select(records).join(identities, identities.c.wo_identity == records.c.wo_identity).where(
            identities.c.rows == 1).cte('annual_eligible')
        return records, identities, eligible

    def summary(self, *, asset_ref, population):
        records, identities, eligible = self._relations(asset_ref, population)
        scalar_count = lambda relation, *conditions: select(func.count()).select_from(relation).where(*conditions).scalar_subquery()
        metrics = select(
            scalar_count(records).label('record_count'),
            scalar_count(identities).label('work_order_count'),
            scalar_count(identities, identities.c.rows > 1).label('duplicate_work_order_count'),
            func.coalesce(select(func.sum(identities.c.rows)).where(identities.c.rows > 1).scalar_subquery(), 0).label('duplicate_record_count'),
            scalar_count(records, records.c.wo_identity.is_(None)).label('missing_identity_record_count'),
        ).cte('annual_metrics')
        groups = select(eligible.c.year, eligible.c.work_type, eligible.c.status, func.count().label('count')).group_by(
            eligible.c.year, eligible.c.work_type, eligible.c.status).cte('annual_groups')
        # Metrics and all distributions share one SQL snapshot. Never aggregate the UI page.
        statement = select(*metrics.c, groups.c.year, groups.c.work_type, groups.c.status, groups.c.count).select_from(
            metrics.outerjoin(groups, true())).order_by(groups.c.year.desc().nulls_last(), groups.c.work_type, groups.c.status).limit(10001)
        with self.database.read_session() as session:
            rows = session.execute(statement).mappings().all()
        if len(rows) > 10000:
            raise RuntimeError('annual summary exceeds bounded aggregate shape')
        counts = {key: int(rows[0][key]) for key in metrics.c.keys()}
        buckets = {}
        for row in rows:
            if row['count'] is None:
                continue
            bucket = buckets.setdefault(row['year'], {'year': row['year'], 'work_orders': 0, 'work_types': {}, 'statuses': {}})
            count = int(row['count'])
            bucket['work_orders'] += count
            for key, field in [('work_types', 'work_type'), ('statuses', 'status')]:
                bucket[key][row[field]] = bucket[key].get(row[field], 0) + count
        def output(bucket):
            return {**bucket, **{key: [{'value': value, 'count': count} for value, count in sorted(bucket[key].items(), key=lambda item: (-item[1], item[0] or ''))] for key in ['work_types', 'statuses']}}
        unknown = buckets.pop(None, {'year': None, 'work_orders': 0, 'work_types': {}, 'statuses': {}})
        years = [output(buckets[year]) for year in sorted(buckets, reverse=True)]
        counts['dated_work_order_count'] = sum(row['work_orders'] for row in years)
        counts['unknown_date_work_order_count'] = unknown['work_orders']
        return {'counts': counts, 'years': years, 'unknown_year': output(unknown)}

    def list_year(self, *, asset_ref, population, year, status=None, offset=0, limit=25, sort='date_desc'):
        if year != 'unknown' and (not str(year).isdigit() or not 1 <= int(year) <= 9999):
            raise ValueError('invalid annual WO year')
        if offset < 0 or offset > 1000000 or not 1 <= limit <= 200 or sort not in ['date_asc', 'date_desc']:
            raise ValueError('invalid annual WO pagination')
        _, _, eligible = self._relations(asset_ref, population)
        statement = select(WO).join(eligible, eligible.c.canonical_id == WO.canonical_id).where(
            eligible.c.year.is_(None) if year == 'unknown' else eligible.c.year == int(year))
        if status:
            statement = statement.where(WO.status == status)
        date = WO.source_changed_at if year == 'unknown' else WO.actual_start
        order = date.asc().nulls_last() if sort == 'date_asc' else date.desc().nulls_last()
        with self.database.read_session() as session:
            return _page(session, statement.order_by(order, WO.canonical_id), offset, limit)
