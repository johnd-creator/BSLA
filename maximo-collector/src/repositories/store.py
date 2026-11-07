"""CollectorStore: persist contract-shaped domain models into Postgres."""

from __future__ import annotations

from src.adapters.maximo.actual_dates import merge_evidence, version

from contextlib import contextmanager
import dataclasses
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import desc, func, or_, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert

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
        # Keep ORM date columns typed; only nested source JSON is serialized.
        for field in dataclasses.fields(e):
            value = getattr(e, field.name)
            if isinstance(value, datetime):
                row[field.name] = value
        with self._db.session() as session:
            existing = session.get(orm.EquipmentOrm, e.id)
            if existing is None:
                # A recovered old source row is new local evidence. Incremental
                # Mart projection must see it without rewriting its changedate.
                source = dict(row.get("sources") or {})
                maximo = dict(source.get("maximo") or {})
                maximo["collector_updated_at"] = datetime.now(timezone.utc).isoformat()
                source["maximo"] = maximo
                row["sources"] = source
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

    def upsert_equipment_manual(self, e: domain.Equipment, *, raw: dict) -> str:
        """Explicit master refresh, exact source ID only, preserving newer records.

        The caller is a manual bounded scan. Routine sync baseline policy stays
        unchanged. A verified source field may refresh the same asset, never a WO.
        """
        row = _row(e)
        for field in dataclasses.fields(e):
            value = getattr(e, field.name)
            if isinstance(value, datetime): row[field.name] = value
        with self._db.session() as session:
            existing = session.get(orm.EquipmentOrm, e.id, with_for_update=True)
            if existing is not None:
                def aware(v): return v.replace(tzinfo=timezone.utc) if v and v.tzinfo is None else v
                old, new = aware(existing.source_changed_at), aware(e.source_changed_at)
                if old is not None and (new is None or new < old): return "unchanged"
            sources = dict(existing.sources or {}) if existing is not None else {}
            source = dict(sources.get("maximo") or {})
            incoming = dict((row.get("sources") or {}).get("maximo") or {})
            # This manual projection owns the explicit source unit; plant is not a unit.
            row["unit"] = incoming.get("eq11")
            for key, value in incoming.items():
                if key == "extra":
                    source[key] = {**(source.get(key) or {}), **(value or {})}
                elif value is not None or key in {"eq11", "parent"}:
                    source[key] = value
            source["collector_updated_at"] = datetime.now(timezone.utc).isoformat()
            source["collection_mode"] = "MANUAL_HIERARCHY_REFRESH"
            sources["maximo"] = source; row["sources"] = sources
            if existing is None:
                session.add(orm.EquipmentOrm(**row)); outcome = "inserted"
            else:
                for key, value in row.items():
                    if key == "id": continue
                    # An omitted/null optional field never erases retained history.
                    # The manual full scalar projection includes parent; absent/null
                    # parent is a source root, not permission to reuse an old edge.
                    if value is not None or key in {"parent_id", "unit"}:
                        setattr(existing, key, value)
                outcome = "updated"
            session.commit()
        return outcome

    def upsert_work_order(self, w: domain.WorkOrder) -> str:
        from copy import deepcopy
        from src.services.workorder_policy import TERMINAL, normalized_status
        row = _row(w)
        for field in dataclasses.fields(w):
            value = getattr(w, field.name)
            if isinstance(value, datetime):
                row[field.name] = value.astimezone(timezone.utc) if value.tzinfo is not None else value
        incoming = deepcopy((row.get("sources") or {}).get("maximo") or {})
        with self._db.session() as session:
            existing = session.get(orm.WorkOrderOrm, w.id, with_for_update=True)
            if existing is None:
                if incoming.get("collection", {}).get("mode") == "STATUS_ONLY" and normalized_status(w.status) not in {"CAN", "CANCEL"}:
                    raise ValueError("a new WO requires an initial detail snapshot")
                source = dict(row.get("sources") or {})
                maximo = dict(source.get("maximo") or {})
                maximo["collector_updated_at"] = datetime.now(timezone.utc).isoformat()
                source["maximo"] = maximo
                row["sources"] = source
                session.add(orm.WorkOrderOrm(**row))
                outcome = "inserted"
            else:
                old_version, new_version = version(existing.source_changed_at), version(w.source_changed_at)
                if old_version is not None and (new_version is None or new_version < old_version):
                    return "unchanged"
                old_status, new_status = normalized_status(existing.status), normalized_status(w.status)
                if old_version == new_version and old_status != new_status:
                    observation = incoming.get("collection") or {}
                    if not (observation.get("same_version_status_confirmed") is True
                            and observation.get("prior_status") == old_status
                            and observation.get("status") == new_status
                            and version(observation.get("confirmed_status_changed_at")) is not None
                            and version(observation.get("confirmed_status_changed_at")) == version(w.status_changed_at)
                            and incoming.get("siteid") == "BSR" and incoming.get("orgid") == "IP"):
                        raise ValueError("WO status conflict requires matching source summary and exact-WO confirmation")
                sources = deepcopy(existing.sources or {})
                previous = sources.get("maximo") or {}
                old_proof = previous.get("actual_dates")
                new_proof = incoming.get("actual_dates")
                # Keep old evidence as history on observed reopen/cancellation, never reuse it on reclose.
                legacy_open_clocks = old_status != "CLOSE" and any(
                    item.get("state") == "VALID" for item in (old_proof or {}).get("fields", {}).values())
                if old_proof and ((old_status == "CLOSE" and new_status != "CLOSE") or legacy_open_clocks):
                    history = list(previous.get("actual_dates_history") or [])
                    history.append({"prior_status": old_status,
                                    "reason": "LEGACY_NONCLOSE_EVIDENCE" if legacy_open_clocks else "LEFT_CLOSE_STATUS",
                                    "closed_source_changed_at": old_version.isoformat() if old_version else None,
                                    "exit_source_changed_at": new_version.isoformat() if new_version else None,
                                    "evidence": deepcopy(old_proof)})
                    incoming["actual_dates_history"] = history
                if new_proof and old_status == new_status == "CLOSE":
                    incoming["actual_dates"] = merge_evidence(old_proof, new_proof)
                elif not new_proof and old_status == new_status == "CLOSE" and old_proof:
                    incoming["actual_dates"] = deepcopy(old_proof)
                terminal_frozen = old_status in TERMINAL and new_status in TERMINAL and not (new_status == "CLOSE" and old_status != "CLOSE")
                status_only = incoming.get("collection", {}).get("mode") == "STATUS_ONLY" or terminal_frozen
                fields = {"equipment_id":"assetnum", "location_id":"location", "status":"status", "status_description":"status_description",
                    "work_type":"worktype", "work_class":"woclass", "description":"description", "reported_at":"reportdate",
                    "source_changed_at":"changedate", "status_changed_at":"statusdate", "scheduled_start":"schedstart",
                    "scheduled_finish":"schedfinish", "target_completion":"targcompdate", "estimated_duration_hours":"estdur",
                    "downtime_hours":"downtime", "priority":"wopriority", "priority_description":"wopriority_description",
                    "reported_by":"reportedby", "supervisor":"supervisor", "lead":"lead", "failure_code":"failurecode",
                    "is_task":"istask", "has_children":"haschildren", "estimated_labor_cost":"estlabcost",
                    "estimated_material_cost":"estmatcost", "actual_labor_cost":"actlabcost", "actual_material_cost":"actmatcost",
                    "actual_labor_hours":"actlabhrs"}
                observed = incoming.get("observed_fields")
                allowed = {"status", "status_description", "source_changed_at", "status_changed_at"} if status_only else set(row)
                legacy_parent_before = existing.parent_wo
                before = {c.name: deepcopy(getattr(existing,c.name)) for c in existing.__table__.columns}
                for column, value in row.items():
                    if column in {"id", "sources"} or column not in allowed:
                        continue
                    if observed is not None and column in fields and fields[column] not in observed:
                        continue
                    setattr(existing, column, value)
                merged = {**previous, **incoming}
                merged["extra"] = {**(previous.get("extra") or {}), **(incoming.get("extra") or {})}
                old_h = previous.get("hierarchy") or {}
                new_h = incoming.get("hierarchy") or {}
                merged["hierarchy"] = {**old_h, **new_h,
                    "source_fields": {**(old_h.get("source_fields") or {}), **(new_h.get("source_fields") or {})}}
                if status_only:
                    for key in ("extra", "hierarchy", "workorderid"):
                        if key in previous:
                            merged[key] = deepcopy(previous[key])
                    # Summary asset changes cannot relabel retained terminal detail/evidence.
                    old_identity = (old_proof or {}).get("identity", {})
                    if old_identity.get("assetnum") not in (None, w.equipment_id):
                        merged["terminal_identity_change"] = {"state":"REQUIRES_REVIEW", "source_assetnum":w.equipment_id}
                old_hierarchy = previous.get("hierarchy") or {}
                legacy_parent = old_hierarchy.get("legacy_parent_wo", legacy_parent_before)
                if legacy_parent is not None:
                    merged["hierarchy"] = {**(merged.get("hierarchy") or {}), "schema_version":1,
                        "parent_wo_state":"UNKNOWN", "legacy_parent_wo":legacy_parent}
                existing.parent_wo = None
                sources["maximo"] = merged
                existing.sources = sources
                def differs(key, old):
                    new = getattr(existing, key)
                    if isinstance(new, datetime) and isinstance(old, datetime):
                        return version(new) != version(old)
                    return new != old
                outcome = "updated" if any(differs(key, value) for key,value in before.items()) else "unchanged"
                if outcome == "updated":
                    merged["collector_updated_at"] = datetime.now(timezone.utc).isoformat()
                    existing.sources = {**sources, "maximo": merged}
            session.commit()
        return outcome

    def work_order_snapshot(self, identity: str) -> dict | None:
        with self._db.session() as session:
            row = session.get(orm.WorkOrderOrm, identity)
            return {"status": row.status, "source_changed_at": row.source_changed_at} if row else None

    def active_work_order_candidates(self, prefixes, excluded, limit=25):
        """Round-robin only locally active WOs. Unknown source scope is rechecked by GET."""
        from src.services.workorder_age import window
        age_cutoff, age_now = window()
        with self._db.session() as session:
            model = orm.WorkOrderOrm
            stmt = select(model.id).where(
                model.reported_at >= age_cutoff, model.reported_at <= age_now,
                func.upper(func.trim(model.status)).not_in(("CLOSE", "CAN", "CANCEL")),
                or_(*(model.id.startswith(prefix) for prefix in prefixes)),
            ).order_by(model.sources["maximo"]["status_checked_at"].as_string().asc().nulls_first(), model.id).limit(limit)
            if excluded:
                stmt = stmt.where(model.id.not_in(excluded))
            return list(session.scalars(stmt))

    def mark_work_order_status_checked(self, identity, state="OBSERVED"):
        """Local check scheduling is not ingestion/activity and must not dirty Mart."""
        from copy import deepcopy
        with self._db.session() as session:
            row = session.get(orm.WorkOrderOrm, identity, with_for_update=True)
            if row is None or str(row.status or "").upper() in {"CLOSE", "CAN", "CANCEL"}:
                return
            sources = deepcopy(row.sources or {})
            maximo = dict(sources.get("maximo") or {})
            maximo.update(status_checked_at=datetime.now(timezone.utc).isoformat(), status_check_state=state)
            sources["maximo"] = maximo
            row.sources = sources
            session.commit()

    def work_order_catchup_pages(self, cursor, base: int, ceiling: int) -> int:
        with self._db.session() as session:
            marker = session.scalar(select(orm.CollectRunOrm).where(
                orm.CollectRunOrm.object_structure == "mxwodetail-catchup-budget"
            ).order_by(orm.CollectRunOrm.id.desc()).limit(1))
            if marker and version(marker.watermark) == version(cursor):
                return min(ceiling, max(base, marker.rows_seen))
        return base

    def save_work_order_catchup_pages(self, cursor, pages: int) -> None:
        now = datetime.now(timezone.utc)
        with self._db.session() as session:
            session.add(orm.CollectRunOrm(object_structure="mxwodetail-catchup-budget", mode="catchup-budget",
                rows_seen=pages, upserted=0, skipped=0, errors=0, watermark=cursor, started_at=now, finished_at=now))
            session.commit()

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
        if not entity_id:
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
