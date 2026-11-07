"""Asset-specific WO reads for the collected inventory, without Registry changes."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select

from src.repositories.asset_inventory import InventoryQuery
from src.repositories.mart_models import AssetMasterMart, MaintenanceEventMart
from src.repositories.mart_reader import _page


class InventoryWorkOrderQuery:
    def __init__(self, database):
        self.database = database

    def list(self, *, asset_ref: str, work_order_id: str | None = None,
             status: str | None = None, date_from: datetime | None = None,
             date_to: datetime | None = None, offset: int = 0,
             limit: int = 25, sort: str = "date_desc"):
        if not asset_ref or not 0 <= offset <= 1_000_000 or not 1 <= limit <= 200:
            raise ValueError("invalid bounded inventory WO query")
        if sort not in {"date_asc", "date_desc", "status"}:
            raise ValueError("invalid inventory WO sort")
        inventory = InventoryQuery.base().where(
            # Exact canonical identity only; no parent, substring or fuzzy matching.
            AssetMasterMart.canonical_id == asset_ref
        ).subquery()
        work = MaintenanceEventMart
        statement = select(work).join(inventory, inventory.c.canonical_id == work.equipment_id).where(
            work.site_code == "BSR", work.organization_code == "IP",
            work.equipment_id == asset_ref,
        )
        if work_order_id:
            statement = statement.where(work.work_order_id == work_order_id)
        if status:
            statement = statement.where(work.status == status)
        record_date = func.coalesce(work.actual_start, work.source_changed_at)
        if date_from:
            statement = statement.where(record_date >= date_from)
        if date_to:
            statement = statement.where(record_date <= date_to)
        order = work.status.asc() if sort == "status" else (
            record_date.asc().nulls_last() if sort == "date_asc" else record_date.desc().nulls_last()
        )
        # Timestamp ties must not shuffle identities between adjacent pages.
        statement = statement.order_by(order, work.canonical_id.asc())
        with self.database.read_session() as session:
            return _page(session, statement, offset, limit)
