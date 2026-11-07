"""Read-only inventory view, distinct from the governed Reliability Registry."""
from datetime import datetime
from sqlalchemy import DateTime, Integer, JSON, String, Boolean, func, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from src.repositories.mart_models import MartBase, AssetMasterMart, ReliabilityAssetRegistryMart

_json=JSONB().with_variant(JSON(), 'sqlite')

class AssetInventoryMart(MartBase):
    __tablename__='asset_inventory'
    asset_id: Mapped[str] = mapped_column(String(60), primary_key=True)
    category: Mapped[str] = mapped_column(String(20), nullable=False)
    scope_basis: Mapped[str] = mapped_column(String(40), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    evidence: Mapped[dict] = mapped_column(_json, nullable=False)
    assessed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

class AssetInventoryScanMart(MartBase):
    __tablename__='asset_inventory_scan'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    result: Mapped[dict] = mapped_column(_json, nullable=False)

class InventoryQuery:
    def __init__(self, database): self.database=database
    @staticmethod
    def base():
        a,i,r=AssetMasterMart,AssetInventoryMart,ReliabilityAssetRegistryMart
        registered=select(r.asset_ref).where(r.asset_ref==a.canonical_id,r.site_code=='BSR',r.organization_code=='IP').exists()
        return (select(a,i.category,i.scope_basis,registered.label('registered'))
            .join(i,i.asset_id==a.source_asset_number)
            .where(a.site_code=='BSR',a.organization_code=='IP',i.active.is_(True)))
    def summary(self):
        with self.database.read_session() as session:
            rows=session.execute(select(AssetInventoryMart.category,func.count())
                .join(AssetMasterMart,AssetMasterMart.source_asset_number==AssetInventoryMart.asset_id)
                .where(AssetMasterMart.site_code=='BSR',AssetMasterMart.organization_code=='IP',AssetInventoryMart.active.is_(True))
                .group_by(AssetInventoryMart.category)).all()
            counts={k:0 for k in ('system','equipment','component','part','unknown')}
            for category,count in rows: counts[category if category in counts else 'unknown']+=int(count)
            counts['total']=sum(counts.values())
            latest=session.scalar(select(AssetInventoryScanMart).order_by(AssetInventoryScanMart.id.desc()).limit(1))
            result=latest.result if latest else {}
            complete=result.get('full_source_baseline_complete') is True
            timestamp=latest.finished_at.isoformat() if latest and complete else None
            pending=int(session.scalar(select(func.count()).select_from(AssetInventoryMart)
                .outerjoin(AssetMasterMart,(AssetMasterMart.source_asset_number==AssetInventoryMart.asset_id)
                    & (AssetMasterMart.site_code=='BSR') & (AssetMasterMart.organization_code=='IP'))
                .where(AssetInventoryMart.active.is_(True),AssetMasterMart.canonical_id.is_(None))) or 0)
            return {'scope':{'site_code':'BSR','organization_code':'IP','unit':'CS01','population':'COLLECTED_HIERARCHY'},
                'counts':counts, 'coverage':{'state':'COMPLETE_AS_OF_MANUAL_SCAN' if complete and pending==0 else 'PARTIAL',
                    'full_source_baseline_complete':complete, 'last_completed_at':timestamp,
                    'pending_projection':pending,'retained_not_seen_in_scan':result.get('retained_not_seen_in_scan'),
                    'last_attempt_at':latest.finished_at.isoformat() if latest else None,
                    'stop_reason':result.get('stop_reason','NOT_SCANNED')},
                'classification':{'basis':'EXACT_SOURCE_ID_WORKBOOK_ROLE','status':'INDICATIVE_DOCUMENT_ROLE',
                    'unknown_count':counts['unknown'], 'note':'Kategori dari Excel engineer, berdasarkan KKS persis. Arti kode belum memiliki legenda resmi; konflik dan tanpa pasangan tetap unknown.'}}
    def list(self, *, offset=0,limit=50,status=None,unit=None,asset_type=None,category=None,q=None,sort='updated_desc'):
        from src.repositories.mart_reader import QueryPage
        statement=self.base()
        a=AssetMasterMart
        for value,column in ((status,a.status),(unit,a.unit),(asset_type,a.asset_type),(category,AssetInventoryMart.category)):
            if value:statement=statement.where(column==value)
        if q:
            safe=q.replace('\\','\\\\').replace('%','\\%').replace('_','\\_')
            statement=statement.where(a.source_asset_number.ilike('%'+safe+'%',escape='\\')|a.description.ilike('%'+safe+'%',escape='\\'))
        order=a.source_updated_at.asc() if sort=='updated_asc' else a.source_updated_at.desc()
        if sort=='status':order=a.status.asc()
        with self.database.read_session() as session:
            total=int(session.scalar(select(func.count()).select_from(statement.subquery())) or 0)
            rows=list(session.execute(statement.order_by(order,a.canonical_id).offset(offset).limit(limit)))
            return QueryPage(rows,total,offset,limit)
    def get(self, identity):
        with self.database.read_session() as session:
            return session.execute(self.base().where(AssetMasterMart.canonical_id==identity)).first()
