"""Additive inventory evidence in the existing Maximo database, not Registry enrollment."""
from datetime import datetime, timezone
from sqlalchemy import DateTime, Integer, JSON, String, Boolean, update
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from src.repositories.database import Base

_json=JSONB().with_variant(JSON(), 'sqlite')

class AssetInventoryOrm(Base):
    __tablename__='asset_inventory'
    asset_id: Mapped[str] = mapped_column(String(60), primary_key=True)
    category: Mapped[str] = mapped_column(String(20), nullable=False)
    scope_basis: Mapped[str] = mapped_column(String(40), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    evidence: Mapped[dict] = mapped_column(_json, nullable=False)
    assessed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

class AssetInventoryScanOrm(Base):
    __tablename__='asset_inventory_scan'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    result: Mapped[dict] = mapped_column(_json, nullable=False)

class AssetInventoryStore:
    def __init__(self, database): self.db=database
    def create_tables(self):
        Base.metadata.create_all(self.db.engine, tables=[AssetInventoryOrm.__table__, AssetInventoryScanOrm.__table__])
    def upsert(self, identity, category, basis, evidence, at, *, seen_in_source):
        with self.db.session() as session:
            row=session.get(AssetInventoryOrm, identity)
            if row is None:
                row=AssetInventoryOrm(asset_id=identity);session.add(row)
            row.active=True;row.category=category;row.scope_basis=basis;row.evidence=evidence;row.assessed_at=at
            if seen_in_source:row.source_observed_at=at
            session.commit()
    def deactivate_outside(self, admitted):
        with self.db.session() as session:
            session.execute(update(AssetInventoryOrm).where(AssetInventoryOrm.asset_id.not_in(list(admitted))).values(active=False))
            session.commit()
    def record_scan(self, result, started):
        with self.db.session() as session:
            session.add(AssetInventoryScanOrm(started_at=started,finished_at=datetime.now(timezone.utc),result=result))
            session.commit()
