"""Transactional keyset checkpoints, in the existing Maximo database only."""
from datetime import datetime,timezone
import uuid
from sqlalchemy import BigInteger,Boolean,DateTime,Integer,JSON,String,UniqueConstraint,func,select,update
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped,mapped_column
from src.repositories.database import Base

_json=JSONB().with_variant(JSON(),'sqlite')

def now():return datetime.now(timezone.utc)

class InventorySweepOrm(Base):
    __tablename__='asset_inventory_sweep'
    id:Mapped[str]=mapped_column(String(36),primary_key=True)
    reference_sha:Mapped[str]=mapped_column(String(64),nullable=False)
    state:Mapped[str]=mapped_column(String(24),nullable=False)
    upper_id:Mapped[int]=mapped_column(BigInteger,nullable=False,default=0)
    collect_cursor:Mapped[int]=mapped_column(BigInteger,nullable=False,default=0)
    verify_cursor:Mapped[int]=mapped_column(BigInteger,nullable=False,default=0)
    delta_cursor:Mapped[int]=mapped_column(BigInteger,nullable=False,default=0)
    requests:Mapped[int]=mapped_column(Integer,nullable=False,default=0)
    rounds:Mapped[int]=mapped_column(Integer,nullable=False,default=1)
    started_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False,default=now)
    updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False,default=now)
    result:Mapped[dict]=mapped_column(_json,nullable=False,default=dict)

class InventoryStageOrm(Base):
    __tablename__='asset_inventory_stage'
    __table_args__=(UniqueConstraint('sweep_id','assetnum',name='uq_inventory_sweep_source_identity'),)
    sweep_id:Mapped[str]=mapped_column(String(36),primary_key=True)
    assetid:Mapped[int]=mapped_column(BigInteger,primary_key=True)
    assetnum:Mapped[str]=mapped_column(String(60),nullable=False)
    payload:Mapped[dict]=mapped_column(_json,nullable=False)
    signature:Mapped[str]=mapped_column(String(64),nullable=False)
    verified:Mapped[bool]=mapped_column(Boolean,nullable=False,default=False)

class SweepStore:
    def __init__(self,db):self.db=db
    def create_tables(self):
        Base.metadata.create_all(self.db.engine,tables=[InventorySweepOrm.__table__,InventoryStageOrm.__table__])
    def get(self,identity):
        with self.db.session() as session:return session.get(InventorySweepOrm,identity)
    def choose(self,sha,*,identity=None,new=False):
        with self.db.session() as session:
            if identity:row=session.get(InventorySweepOrm,identity)
            elif not new:row=session.scalar(select(InventorySweepOrm).where(InventorySweepOrm.reference_sha==sha).order_by(InventorySweepOrm.started_at.desc()).limit(1))
            else:row=None
            if identity and row is None:raise ValueError('unknown sweep ID')
            if row and row.reference_sha!=sha:raise ValueError('reference fingerprint changed')
            if row:return row
            row=InventorySweepOrm(id=str(uuid.uuid4()),reference_sha=sha,state='INITIALIZING',upper_id=0,collect_cursor=0,verify_cursor=0,delta_cursor=0,requests=0,rounds=1,result={})
            session.add(row);session.commit();return row
    def initialize(self,identity,upper):
        with self.db.session() as session:
            row=session.get(InventorySweepOrm,identity,with_for_update=True)
            if row.state!='INITIALIZING':raise ValueError('stale initialization')
            row.upper_id=upper;row.state='COLLECTING';row.updated_at=now();session.commit()
    def stage(self,identity,assetid):
        with self.db.session() as session:return session.get(InventoryStageOrm,(identity,assetid))
    def save_collect_page(self,identity,cursor,records):
        """Stage the entire validated page and advance cursor in one transaction."""
        with self.db.session() as session:
            run=session.get(InventorySweepOrm,identity,with_for_update=True)
            if run.state!='COLLECTING' or run.collect_cursor!=cursor:raise ValueError('stale collection checkpoint')
            for assetid,payload,signature in records:
                if session.get(InventoryStageOrm,(identity,assetid)) is not None:raise ValueError('duplicate assetid across collection pages')
                session.add(InventoryStageOrm(sweep_id=identity,assetid=assetid,assetnum=payload['assetnum'],payload=payload,signature=signature,verified=False))
            if records:run.collect_cursor=records[-1][0]
            else:run.state='VERIFYING';run.verify_cursor=0
            run.updated_at=now();session.commit()
    def refresh_stage(self,identity,assetid,payload,signature):
        with self.db.session() as session:
            row=session.get(InventoryStageOrm,(identity,assetid))
            if row is None:
                row=InventoryStageOrm(sweep_id=identity,assetid=assetid);session.add(row)
            row.assetnum=payload['assetnum'];row.payload=payload;row.signature=signature;row.verified=False
            session.commit()
    def save_verify_page(self,identity,cursor,records,*,changes=False):
        with self.db.session() as session:
            run=session.get(InventorySweepOrm,identity,with_for_update=True)
            field='delta_cursor' if changes else 'verify_cursor'
            expected='CHANGES' if changes else 'VERIFYING'
            if run.state!=expected or getattr(run,field)!=cursor:raise ValueError('stale verification checkpoint')
            for assetid,signature in records:
                row=session.get(InventoryStageOrm,(identity,assetid))
                if row is None or row.signature!=signature:raise ValueError('verification lacks exact source snapshot')
                row.verified=True
            if records:setattr(run,field,records[-1][0])
            run.updated_at=now();session.commit()
    def finish_or_extend(self,identity,cursor,current_upper):
        with self.db.session() as session:
            run=session.get(InventorySweepOrm,identity,with_for_update=True)
            if run.state!='VERIFYING' or run.verify_cursor!=cursor:raise ValueError('stale final verification')
            if current_upper>run.upper_id:
                run.upper_id=current_upper;run.state='COLLECTING';run.verify_cursor=0;run.rounds+=1
                session.execute(update(InventoryStageOrm).where(InventoryStageOrm.sweep_id==identity).values(verified=False))
            else:run.state='CHANGES';run.delta_cursor=0
            run.updated_at=now();session.commit()
    def finish_changes(self,identity,cursor):
        with self.db.session() as session:
            row=session.get(InventorySweepOrm,identity,with_for_update=True)
            if row.state!='CHANGES' or row.delta_cursor!=cursor:raise ValueError('stale change checkpoint')
            row.state='VERIFIED';row.updated_at=now();session.commit()
    def verified_payloads(self,identity):
        with self.db.session() as session:
            return list(session.scalars(select(InventoryStageOrm.payload).where(InventoryStageOrm.sweep_id==identity,InventoryStageOrm.verified.is_(True))))
    def save_result(self,identity,result,*,published=False,requests=0):
        with self.db.session() as session:
            row=session.get(InventorySweepOrm,identity,with_for_update=True)
            row.requests+=requests;row.updated_at=now();row.result=result
            if published:row.state='PUBLISHED'
            session.commit()
    def summary(self,identity):
        row=self.get(identity)
        with self.db.session() as session:
            n=int(session.scalar(select(func.count()).select_from(InventoryStageOrm).where(InventoryStageOrm.sweep_id==identity)) or 0)
            verified=int(session.scalar(select(func.count()).select_from(InventoryStageOrm).where(InventoryStageOrm.sweep_id==identity,InventoryStageOrm.verified.is_(True))) or 0)
        return {'sweep_id':identity,'state':row.state,'upper_assetid':row.upper_id,'collect_cursor':row.collect_cursor,
            'verify_cursor':row.verify_cursor,'delta_cursor':row.delta_cursor,'staged_rows':n,'verified_rows':verified,'requests_total':row.requests,'rounds':row.rounds}
