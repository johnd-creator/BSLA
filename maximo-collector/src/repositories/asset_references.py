"""Read local WO references and retain bounded source-lookup outcomes."""
from datetime import datetime, timedelta, timezone
from sqlalchemy import func, or_, select
from src.repositories import models as orm

RUN_OBJECT = "mxapiasset_reference"


def _aware(value):
    return value.replace(tzinfo=timezone.utc) if value and value.tzinfo is None else value


class AssetReferenceStore:
    def __init__(self, database):
        self.db = database

    def due(self, now, interval_seconds=3600):
        with self.db.session() as session:
            last = session.scalar(select(func.max(orm.CollectRunOrm.started_at)).where(
                orm.CollectRunOrm.object_structure == RUN_OBJECT))
        return last is None or now >= _aware(last) + timedelta(seconds=interval_seconds)

    def candidates(self, now, limit):
        w, e, c = orm.WorkOrderOrm, orm.EquipmentOrm, orm.AssetReferenceCheckOrm
        with self.db.session() as session:
            query = (select(w.equipment_id).outerjoin(e, e.id == w.equipment_id)
                .outerjoin(c, c.asset_id == w.equipment_id)
                .where(e.id.is_(None), w.equipment_id.is_not(None), w.equipment_id != "",
                    w.sources["maximo"]["siteid"].as_string() == "BSR",
                    w.sources["maximo"]["orgid"].as_string() == "IP",
                    or_(c.asset_id.is_(None), c.retry_after <= now))
                .group_by(w.equipment_id)
                .order_by(func.count().desc(), w.equipment_id).limit(limit))
            return list(session.scalars(query))

    def mark(self, identity, outcome, now):
        with self.db.session() as session:
            row = session.get(orm.AssetReferenceCheckOrm, identity)
            if row is None:
                row = orm.AssetReferenceCheckOrm(asset_id=identity, attempts=0)
                session.add(row)
            row.outcome = outcome
            row.checked_at = now
            row.retry_after = now + timedelta(days=7 if outcome == "NOT_FOUND_IN_SCOPE" else 1)
            row.attempts += 1
            session.commit()

    def coverage(self):
        w, e, c = orm.WorkOrderOrm, orm.EquipmentOrm, orm.AssetReferenceCheckOrm
        with self.db.session() as session:
            assetless = session.scalar(select(func.count()).select_from(w).where(
                or_(w.equipment_id.is_(None), w.equipment_id == "")))
            missing = (select(func.count(), func.count(func.distinct(w.equipment_id)))
                .select_from(w).outerjoin(e, e.id == w.equipment_id)
                .where(e.id.is_(None), w.equipment_id.is_not(None), w.equipment_id != ""))
            missing_wo, missing_assets = session.execute(missing).one()
            verified_wo, verified_ids = session.execute(missing.where(
                w.sources["maximo"]["siteid"].as_string() == "BSR",
                w.sources["maximo"]["orgid"].as_string() == "IP")).one()
            counts = dict(session.execute(select(c.outcome, func.count()).group_by(c.outcome)).all())
            last = session.scalar(select(orm.CollectRunOrm).where(
                orm.CollectRunOrm.object_structure == RUN_OBJECT).order_by(orm.CollectRunOrm.id.desc()).limit(1))
            return {"source_lookup_scope": {"site": "BSR", "org": "IP", "unit": "CS01"},
                "population": "ALL_RETAINED_LOCAL_WORK_ORDERS",
                "equipment": session.scalar(select(func.count()).select_from(e)),
                "work_orders_without_asset_id": assetless,
                "work_orders_with_missing_equipment": missing_wo,
                "distinct_missing_asset_ids": missing_assets,
                "source_verified_bsr_missing_wo": verified_wo,
                "source_verified_bsr_missing_asset_ids": verified_ids,
                "lookup_outcomes": counts,
                "last_run": None if last is None else {"mode": last.mode, "checked": last.rows_seen,
                    "upserted": last.upserted, "errors": last.errors,
                    "finished_at": last.finished_at.isoformat() if last.finished_at else None},
                "coverage_state": "EXACT_LOCAL_REFERENCES_NOT_FULL_SOURCE_BASELINE",
                "not_found_meaning": "Not returned by exact BSR/IP/CS01 lookup; not proof of deletion or an alias."}
