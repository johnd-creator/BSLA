"""CollectorStore: persist contract-shaped domain models into Postgres."""

from __future__ import annotations

from contextlib import contextmanager
import dataclasses
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import desc, func, or_, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert

from src.adapters.maximo.actual_dates import merge_evidence, version
from src.domain import models as domain
from src.repositories import models as orm
from src.repositories.database import Database

_UPSERT_COLUMNS: dict[type, list[str]] = {}


def _json_safe(value: Any) -> Any:
    """Convert nested datetimes/dataclasses to values accepted by JSONB."""
    if isinstance(value, datetime):
        return value.isoformat()
    if dataclasses.is_dataclass(value):
        return _json_safe(dataclasses.asdict(value))
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


def _upsert_columns(orm_cls: type) -> list[str]:
    cols = _UPSERT_COLUMNS.get(orm_cls)
    if cols is None:
        cols = [c.name for c in orm_cls.__table__.columns if c.name != "id"]
        _UPSERT_COLUMNS[orm_cls] = cols
    return cols


def _row(entity: object) -> dict:
    """dataclass -> column dict; maximo_source flattens into the sources JSON."""
    row: dict[str, Any] = {}
    for f in dataclasses.fields(entity):
        value = getattr(entity, f.name)
        if f.name == "maximo_source" and value:
            # Equipment keeps its vendor source in a dedicated dataclass;
            # the ORM contract stores it in the shared JSONB ``sources``
            # column. Do not leave the dataclass field as an ORM kwarg.
            row["sources"] = _json_safe({"maximo": value})
            continue
        row[f.name] = _json_safe(value)
    return row


class CollectorStore:
    def __init__(self, db: Database):
        self._db = db

    # -- generic upsert -----------------------------------------------------
    def _upsert(self, orm_cls: type, row: dict) -> None:
        with self._db.session() as session:
            stmt = pg_insert(orm_cls).values(**row)
            stmt = stmt.on_conflict_do_update(
                index_elements=["id"],
                set_={c: getattr(stmt.excluded, c) for c in _upsert_columns(orm_cls)},
            )
            session.execute(stmt)
            session.commit()

    # -- entities ------------------------------------------------------------
    def upsert_equipment(self, e: domain.Equipment) -> str:
        row = _row(e)
        with self._db.session() as session:
            existing = session.get(orm.EquipmentOrm, e.id)
            if existing is None:
                session.add(orm.EquipmentOrm(**row))
                outcome = "inserted"
            else:
                # Asset master data is a baseline. Routine syncs only update
                # volatile operational fields and never overwrite the stored
                # description, hierarchy, cost or other master fields.
                for column in (
                    "status", "status_description", "is_running",
                    "status_changed_at", "source_changed_at",
                ):
                    setattr(existing, column, row[column])
                old_sources = dict(existing.sources or {})
                old_maximo = dict(old_sources.get("maximo") or {})
                new_maximo = dict((row.get("sources") or {}).get("maximo") or {})
                for key in ("status", "isrunning", "changedate"):
                    if key in new_maximo:
                        old_maximo[key] = new_maximo[key]
                old_sources["maximo"] = old_maximo
                existing.sources = old_sources
                outcome = "updated"
            session.commit()
        return outcome

    def upsert_work_order(self, w: domain.WorkOrder) -> str:
        with self._db.session() as session:
            outcome = self.upsert_work_order_in_session(session, w)
            session.commit()
            return outcome

    def upsert_work_order_in_session(self, session, w: domain.WorkOrder) -> str:
        """Shared transaction boundary for normal acquisition and exact recovery."""
        row = {f.name: getattr(w, f.name) for f in dataclasses.fields(w)}
        row["sources"] = _json_safe(w.sources)
        for key, value in row.items():
            if isinstance(value, datetime) and value.tzinfo is not None:
                row[key] = value.astimezone(timezone.utc)
        existing = session.get(orm.WorkOrderOrm, w.id, with_for_update=True)
        if existing is None:
            session.add(orm.WorkOrderOrm(**row))
            return "inserted"
        old_version = version(existing.source_changed_at)
        new_version = version(w.source_changed_at.isoformat()) if w.source_changed_at else None
        if old_version is not None and (new_version is None or new_version < old_version):
            return "unchanged"
        old_maximo = (existing.sources or {}).get("maximo", {})
        new_sources = row.get("sources") or {}
        new_maximo = dict(new_sources.get("maximo") or {})
        previous = old_maximo.get("actual_dates")
        incoming = new_maximo.get("actual_dates")
        if previous and incoming and previous.get("identity") != incoming.get("identity"):
            raise ValueError("WO clock identity changed")
        if incoming:
            new_maximo["actual_dates"] = merge_evidence(previous, incoming)
        elif previous:
            new_maximo["actual_dates"] = previous
        if new_maximo.get("wo_detail") and new_maximo["wo_detail"] != old_maximo.get("wo_detail"):
            from src.adapters.maximo.wo_detail import merge_details
            new_maximo["wo_detail"] = merge_details(old_maximo.get("wo_detail"), new_maximo["wo_detail"], existing, row)
        row["sources"] = {**new_sources, "maximo": new_maximo}
        changed = any(getattr(existing, key) != value for key, value in row.items())
        for key, value in row.items():
            setattr(existing, key, value)
        return "updated" if changed else "unchanged"

    def upsert_service_request(self, s: domain.ServiceRequest) -> None:
        self._upsert(orm.ServiceRequestOrm, _row(s))

    def upsert_person(self, p: domain.Person) -> None:
        self._upsert(orm.PersonOrm, _row(p))

    def upsert_item(self, i: domain.Item) -> None:
        self._upsert(orm.ItemOrm, _row(i))

    def upsert_labor(self, l: domain.Labor) -> None:
        self._upsert(orm.LaborOrm, _row(l))

    def upsert_for(self, entity_name: str, entity: object) -> object | None:
        mapping = {
            "equipment": self.upsert_equipment,
            "work_order": self.upsert_work_order,
            "service_request": self.upsert_service_request,
            "person": self.upsert_person,
            "item": self.upsert_item,
            "labor": self.upsert_labor,
        }
        return mapping[entity_name](entity)

    def upsert_many_for(self, entity_name: str, entities: list[object]) -> None:
        """Batch upsert master rows in one local transaction.

        This only writes the collector's own database. Maximo access has
        already completed through the GET-only OSLC client.
        """
        if not entities:
            return
        mapping = {
            "person": orm.PersonOrm,
            "item": orm.ItemOrm,
            "labor": orm.LaborOrm,
        }
        orm_cls = mapping.get(entity_name)
        if orm_cls is None:
            for entity in entities:
                self.upsert_for(entity_name, entity)
            return
        rows = [_row(entity) for entity in entities]
        with self._db.session() as session:
            stmt = pg_insert(orm_cls).values(rows)
            stmt = stmt.on_conflict_do_update(
                index_elements=["id"],
                set_={c: getattr(stmt.excluded, c) for c in _upsert_columns(orm_cls)},
            )
            session.execute(stmt)
            session.commit()

    def is_unchanged(
        self,
        entity_name: str,
        entity_id: str | None,
        compare_column: str,
        source_value: datetime,
    ) -> bool:
        """Return true when a local row already has this source timestamp."""
        if not entity_id or entity_name == "work_order":
            # Equality of changedate cannot prove newly selected clocks were
            # previously retained. The locked upsert handles no-op replay.
            return False
        mapping = {
            "equipment": orm.EquipmentOrm,
            "work_order": orm.WorkOrderOrm,
            "service_request": orm.ServiceRequestOrm,
            "person": orm.PersonOrm,
            "item": orm.ItemOrm,
        }
        orm_cls = mapping.get(entity_name)
        if orm_cls is None:
            return False
        with self._db.session() as session:
            existing = session.get(orm_cls, entity_id)
            return existing is not None and getattr(existing, compare_column) == source_value

    def record_equipment_status(self, equipment: domain.Equipment) -> None:
        """Append a status observation only when it differs from the last one."""
        with self._db.session() as session:
            last = session.execute(
                select(orm.EquipmentStatusHistoryOrm)
                .where(orm.EquipmentStatusHistoryOrm.equipment_id == equipment.id)
                .order_by(desc(orm.EquipmentStatusHistoryOrm.id))
                .limit(1)
            ).scalar_one_or_none()
            current = (
                equipment.status,
                equipment.status_description,
                equipment.is_running,
                equipment.status_changed_at,
            )
            previous = (
                last.status,
                last.status_description,
                last.is_running,
                last.status_changed_at,
            ) if last else None
            if current == previous:
                return
            session.add(
                orm.EquipmentStatusHistoryOrm(
                    equipment_id=equipment.id,
                    status=equipment.status,
                    status_description=equipment.status_description,
                    is_running=equipment.is_running,
                    status_changed_at=equipment.status_changed_at,
                    source_changed_at=equipment.source_changed_at,
                    captured_at=datetime.now(timezone.utc),
                )
            )
            session.commit()

    def seed_equipment_status_history(self) -> int:
        """Create one local baseline observation for existing equipment rows."""
        with self._db.session() as session:
            assets = list(session.execute(select(orm.EquipmentOrm)).scalars())
            known = set(
                session.execute(
                    select(orm.EquipmentStatusHistoryOrm.equipment_id).distinct()
                ).scalars()
            )
            added = 0
            for equipment in assets:
                if equipment.id in known:
                    continue
                session.add(
                    orm.EquipmentStatusHistoryOrm(
                        equipment_id=equipment.id,
                        status=equipment.status,
                        status_description=equipment.status_description,
                        is_running=equipment.is_running,
                        status_changed_at=equipment.status_changed_at,
                        source_changed_at=equipment.source_changed_at,
                        captured_at=datetime.now(timezone.utc),
                    )
                )
                added += 1
            session.commit()
            return added

    # -- queries (API layer) ---------------------------------------------------
    def list_rows(
        self,
        orm_cls: type,
        *,
        changed_column: str | None = None,
        changed_since=None,
        changed_until=None,
        offset: int = 0,
        limit: int = 1000,
        exact_filters: dict[str, str] | None = None,
        search: str | None = None,
        search_columns: tuple[str, ...] = (),
        prefix_column: str | None = None,
        prefixes: tuple[str, ...] = (),
        order_column: str | None = None,
        order_desc: bool = False,
    ) -> list[Any]:
        with self._db.session() as session:
            stmt = select(orm_cls)
            if changed_column and changed_since is not None:
                stmt = stmt.where(getattr(orm_cls, changed_column) > changed_since)
            if changed_column and changed_until is not None:
                stmt = stmt.where(getattr(orm_cls, changed_column) <= changed_until)
            for column, value in (exact_filters or {}).items():
                if value:
                    stmt = stmt.where(getattr(orm_cls, column) == value)
            if prefix_column and prefixes:
                stmt = stmt.where(
                    or_(*[
                        getattr(orm_cls, prefix_column).ilike(f"{prefix}%")
                        for prefix in prefixes
                    ])
                )
            if search and search_columns:
                needle = f"%{search.strip().lower()}%"
                stmt = stmt.where(
                    or_(*[func.lower(getattr(orm_cls, column)).like(needle) for column in search_columns])
                )
            sort_column = order_column or changed_column
            if sort_column:
                # Offset pagination must have a deterministic tie-breaker.
                # Changed timestamps are not unique, so ordering only by the
                # watermark column can repeat/skip rows between pages.
                column = getattr(orm_cls, sort_column)
                identity_column = getattr(orm_cls, "id", None) or getattr(orm_cls, "canonical_id")
                stmt = stmt.order_by(
                    (column.desc().nullslast() if order_desc else column.asc().nullsfirst()),
                    identity_column.asc(),
                )
            else:
                identity_column = getattr(orm_cls, "id", None) or getattr(orm_cls, "canonical_id")
                stmt = stmt.order_by(identity_column)
            stmt = stmt.offset(offset).limit(limit)
            return list(session.execute(stmt).scalars().all())

    def count(
        self,
        orm_cls: type,
        *,
        exact_filters: dict[str, str] | None = None,
        prefix_column: str | None = None,
        prefixes: tuple[str, ...] = (),
        search: str | None = None,
        search_columns: tuple[str, ...] = (),
    ) -> int:
        from sqlalchemy import func

        with self._db.session() as session:
            stmt = select(func.count()).select_from(orm_cls)
            for column, value in (exact_filters or {}).items():
                if value:
                    stmt = stmt.where(getattr(orm_cls, column) == value)
            if prefix_column and prefixes:
                stmt = stmt.where(
                    or_(*[
                        getattr(orm_cls, prefix_column).ilike(f"{prefix}%")
                        for prefix in prefixes
                    ])
                )
            if search and search_columns:
                needle = f"%{search.strip().lower()}%"
                stmt = stmt.where(
                    or_(*[func.lower(getattr(orm_cls, column)).like(needle) for column in search_columns])
                )
            return session.execute(stmt).scalar() or 0

    def list_equipment_status_history(self, equipment_id: str, limit: int = 100) -> list[Any]:
        with self._db.session() as session:
            stmt = (
                select(orm.EquipmentStatusHistoryOrm)
                .where(orm.EquipmentStatusHistoryOrm.equipment_id == equipment_id)
                .order_by(desc(orm.EquipmentStatusHistoryOrm.id))
                .limit(limit)
            )
            return list(session.execute(stmt).scalars().all())

    def list_runs(self, limit: int = 20) -> list[Any]:
        with self._db.session() as session:
            stmt = (
                select(orm.CollectRunOrm)
                .order_by(orm.CollectRunOrm.started_at.desc(), orm.CollectRunOrm.id.desc())
                .limit(limit)
            )
            return list(session.execute(stmt).scalars().all())

    def latest_run(self) -> Any | None:
        rows = self.list_runs(1)
        return rows[0] if rows else None

    # -- cursor / run log -------------------------------------------------------
    def latest_work_order_change(self) -> datetime | None:
        """Read local Collector evidence only; never mutate source or cursor."""
        with self._db.session() as session:
            return session.scalar(select(func.max(orm.WorkOrderOrm.source_changed_at)))

    @contextmanager
    def work_order_recovery_lock(self):
        """Serialize explicit recoveries across processes in the existing PG DB."""
        with self._db.engine.connect() as connection:
            # Session-scoped lock stays held while ordinary store sessions commit.
            acquired = connection.scalar(text("SELECT pg_try_advisory_lock(714025013)"))
            try:
                connection.commit()  # avoid an idle transaction during slow source reads
                yield bool(acquired)
            finally:
                if acquired:
                    connection.execute(text("SELECT pg_advisory_unlock(714025013)"))
                    connection.commit()

    def prepare_work_order_recovery_floor(self) -> datetime | None:
        """Persist a retry-stable floor before source reads, using existing run log.

        Caller must hold work_order_recovery_lock. Partial upserts must not raise
        the floor on retry; this marker is evidence, never a runtime cursor.
        """
        with self._db.session() as session:
            anchor = session.scalar(select(orm.CollectRunOrm).where(
                orm.CollectRunOrm.object_structure == "mxwodetail-recovery-floor"
            ).order_by(orm.CollectRunOrm.id).limit(1))
            if anchor is not None:
                return anchor.watermark
            floor = session.scalar(select(func.max(orm.WorkOrderOrm.source_changed_at)))
            if floor is None:
                return None
            now = datetime.now(timezone.utc)
            session.add(orm.CollectRunOrm(object_structure="mxwodetail-recovery-floor",
                mode="recovery-floor", watermark=floor, rows_seen=0, upserted=0,
                skipped=0, errors=0, started_at=now, finished_at=now))
            session.commit()
            return floor

    def get_cursor(self, scope: str) -> datetime | None:
        with self._db.session() as session:
            row = session.get(orm.SyncCursorOrm, scope)
            return row.watermark if row else None

    def set_cursor(self, scope: str, watermark: datetime | None, rows_seen: int) -> None:
        with self._db.session() as session:
            row = session.get(orm.SyncCursorOrm, scope)
            if row is None:
                row = orm.SyncCursorOrm(scope=scope)
            row.watermark = watermark
            row.rows_seen = rows_seen
            row.updated_at = datetime.now(timezone.utc)
            session.add(row)
            session.commit()

    def record_run(self, run) -> None:
        """Persist one completed sync run (SyncStats) for observability."""
        with self._db.session() as session:
            session.add(
                orm.CollectRunOrm(
                    object_structure=run.object_structure,
                    mode=run.mode,
                    rows_seen=run.rows_seen,
                    upserted=run.upserted,
                    skipped=run.skipped,
                    errors=run.errors,
                    watermark=run.watermark,
                    started_at=run.started_at,
                    finished_at=run.finished_at,
                )
            )
            session.commit()
