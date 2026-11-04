"""Disabled B1 local capture candidate. No CLI, environment DSN or startup hook.

One PostgreSQL engine MUST own source, target and receipts. Domain locks fence
participating writers only; exclusive canonical-writer ownership is a rollout
prerequisite, never proven merely by the explicit opt-in below.
"""
from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import String, case, cast, exists, func, insert, select, text, update, or_
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from src.adapters.maximo.canonical_mappers import maintenance_event_from_payload
from src.repositories import models
from src.repositories import projection_models as pm
from src.services.canonical import CanonicalCollection
from src.services.local_mart_projector import _asset_record, _work_order_payload
from src.services.mart import ENTITY_SPECS, MartWriter
from src.services.asset_registry_reconciliation import normalize_identifier

EPOCH = "contract1.0-local-mapper-b1-v1"
SCOPE = {"source": "MAXIMO", "site": "BSR", "organization": "IP", "wo_prefixes": ["BSR"]}
TERMINAL = frozenset({"PROJECTED", "UNCHANGED", "EXPECTED_EXCLUSION"})


class CaptureError(RuntimeError):
    """Sanitized candidate refusal, never raw input/DB exception text."""


class FencedOut(CaptureError):
    pass


class BudgetExceeded(CaptureError):
    pass


def encode(value):
    def scalar(v):
        if isinstance(v, datetime):
            return v.astimezone(timezone.utc).isoformat()
        raise TypeError("unsupported captured scalar")
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=scalar,
                      ensure_ascii=True, allow_nan=False).encode()


def fingerprint(domain, source_id, payload):
    return hashlib.sha256(encode([EPOCH, SCOPE, domain, source_id, payload])).hexdigest()


@dataclass(frozen=True)
class Budget:
    rows: int = 10000
    bytes: int = 16 * 1024 * 1024
    seconds: float = 15
    page: int = 100
    lease_seconds: int = 60

    def __post_init__(self):
        if not (1 <= self.rows <= 100000 and 1 <= self.bytes <= 64 * 1024 * 1024
                and 0 < self.seconds <= 60 and 1 <= self.page <= 500
                and 5 <= self.lease_seconds <= 300):
            raise ValueError("invalid candidate resource budget")


@dataclass(frozen=True)
class Ticket:
    run_id: str
    domain: str
    owner: str
    fence: int


MAX_SCALAR_BYTES = 8192


def bounded_query(identity, fields):
    # Fetch bounded scalars, never a potentially unbounded description/JSON value.
    oversized = [func.octet_length(cast(value, String)) > MAX_SCALAR_BYTES
                 for value in fields.values()]
    return select(identity.label("source_id"), *[
        case((too_large, None), else_=value).label(key)
        for (key, value), too_large in zip(fields.items(), oversized)
    ], func.coalesce(or_(*oversized), False).label("_oversized"))


def source_query(domain):
    """Select approved scalars only, never the complete quarantined JSON/persons."""
    if domain == "asset_master":
        e = models.EquipmentOrm
        fallback = {
            "assetnum": e.id, "description": func.coalesce(e.description, e.name),
            "status": e.status, "assettype": e.equipment_class, "eq11": e.unit,
            "location": e.location_id, "parent": e.parent_id,
            "changedate": e.source_changed_at,
        }
        keys = (*fallback, "assetid", "siteid", "orgid", "plant")
        fields = {k: case((e.sources["maximo"].op("?")(k), e.sources["maximo"][k].astext),
                  else_=cast(fallback[k], String) if k in fallback else None) for k in keys}
        invalid = or_(*[func.jsonb_typeof(e.sources["maximo"][k]).in_(["object", "array"])
                        for k in keys])
        return bounded_query(e.id, fields).add_columns(
            func.coalesce(invalid, False).label("_invalid_input"))
    if domain == "maintenance_event":
        w = models.WorkOrderOrm
        fields = ("equipment_id", "status", "work_type", "reported_at", "scheduled_start",
                  "scheduled_finish", "source_changed_at", "downtime_hours", "actual_labor_hours")
        # Normalization matches the legacy projector (strip/uppercase, no fuzzy match).
        dependency = exists(select(models.EquipmentOrm.id).where(
            models.EquipmentOrm.id == func.upper(func.btrim(w.equipment_id))))
        return bounded_query(w.id, {**{k:getattr(w,k) for k in fields},
                                    "local_equipment_present":dependency})
    raise CaptureError("unsupported capture domain")


def captured_payload(domain, row):
    data = dict(row)
    data.pop("source_id")
    if data.pop("_invalid_input", False):
        raise CaptureError("non-scalar captured input")
    if data.pop("_oversized", False):
        raise BudgetExceeded("capture scalar budget")
    # Exact JSON-safe typed scalars; timestamp NULL remains NULL.
    return json.loads(encode(data))


def map_input(domain, source_id, payload):
    """Internal reason codes only. Never classify unknown scope as exclusion."""
    from types import SimpleNamespace
    if domain == "asset_master":
        if payload["siteid"] != "BSR" or payload["orgid"] != "IP":
            return None, "DEFERRED", "UNPROVEN_SCOPE"
        # All fallback keys already materialized at capture; legacy mapper reused.
        record = _asset_record(SimpleNamespace(sources={"maximo": payload}, id=source_id,
            description=None, name=None, status=None, equipment_class=None, unit=None,
            location_id=None, parent_id=None, ancestor_id=None, source_changed_at=None,
            installed_at=None, is_running=None, has_children=None, priority=None,
            failure_code=None, downtime_total_hours=None))
        return record, None, None
    if not source_id.startswith("BSR"):
        return None, "EXPECTED_EXCLUSION", "APPROVED_WO_PREFIX"
    if not normalize_identifier(payload["equipment_id"]) or not payload["local_equipment_present"]:
        return None, "DEFERRED", "MISSING_LOCAL_EQUIPMENT"
    row = dict(payload)
    row.pop("local_equipment_present")
    for field in ("reported_at", "scheduled_start", "scheduled_finish", "source_changed_at"):
        if row[field] is not None:
            row[field] = datetime.fromisoformat(row[field])
    record = maintenance_event_from_payload(_work_order_payload(SimpleNamespace(id=source_id, **row)))
    return record, None, None


class ProjectionStore:
    def __init__(self, db, *, enabled=False, exclusive_writer=False, budget=None):
        # Refuse before opening a connection. No automatic DSN/default config.
        if not enabled:
            raise CaptureError("candidate is disabled")
        if not exclusive_writer:
            raise CaptureError("exclusive participating writers required")
        if db.engine.dialect.name != "postgresql":
            raise CaptureError("candidate requires co-located PostgreSQL")
        self.db = db
        self.budget = budget or Budget()
        self.writer = MartWriter(db)
        self._schema_preflight()

    def _schema_preflight(self):
        # Reviewed trigger bodies + exact table-column inventory. Missing/drifted
        # capability refuses the candidate, never falls back to legacy SUCCESS.
        from sqlalchemy import inspect
        expected_guards = {'mart_capture_item_guard': '94af2cb742f8de110e29ce8b593f875ad5a892a9b4dd19d6a989a2acc6119bf4', 'mart_capture_run_guard': '0dcda3c5f20e98a0820a8fea39b3c819039eb8a750fc2536cd98d69464e2900a'}
        with self.db.session() as s:
            self._limits(s)
            inspector = inspect(s.connection())
            for table in pm.metadata.sorted_tables:
                columns = {c["name"]:c for c in inspector.get_columns(table.name)}
                if set(columns) != set(table.c.keys()):
                    raise CaptureError("candidate schema column drift")
                for col in table.c:
                    actual = columns[col.name]
                    if (str(actual["type"].compile(dialect=self.db.engine.dialect)) !=
                            str(col.type.compile(dialect=self.db.engine.dialect))
                            or actual["nullable"] != col.nullable):
                        raise CaptureError("candidate schema type/nullability drift")
                if inspector.get_pk_constraint(table.name)["constrained_columns"] != [
                        c.name for c in table.primary_key]:
                    raise CaptureError("candidate schema identity drift")
            for name, digest in expected_guards.items():
                body = s.execute(text("""SELECT p.prosrc FROM pg_proc p
                    JOIN pg_namespace n ON n.oid=p.pronamespace
                    JOIN pg_trigger t ON t.tgfoid=p.oid
                    JOIN pg_class c ON c.oid=t.tgrelid
                    WHERE n.nspname=current_schema() AND p.proname=:name
                    AND t.tgname=:name AND t.tgenabled='O'
                    AND c.relnamespace=n.oid AND t.tgtype=:kind AND c.relname=:table"""),
                    {"name":name, "kind":31 if name.endswith("item_guard") else 27,
                     "table":"mart_capture_item" if name.endswith("item_guard") else "mart_capture_run"}
                ).scalar_one_or_none()
                if body is None or hashlib.sha256(body.encode()).hexdigest() != digest:
                    raise CaptureError("candidate schema guard drift")

    def _limits(self, s, seconds=None):
        seconds = self.budget.seconds if seconds is None else seconds
        s.execute(text("SET LOCAL lock_timeout = '1000ms'"))
        s.execute(text("SELECT set_config('statement_timeout', :v, true)"),
                  {"v": str(max(1, int(seconds * 1000)))})
        s.execute(text("SELECT set_config('idle_in_transaction_session_timeout', :v, true)"),
                  {"v": str(max(1000, int(seconds * 1000)))})

    def _lock(self, s, ticket):
        state = s.execute(select(pm.lease).where(pm.lease.c.domain == ticket.domain)
                          .with_for_update()).mappings().one()
        if (state["fence"] != ticket.fence or state["owner"] != ticket.owner
                or state["latest_run"] != ticket.run_id):
            raise FencedOut("stale domain writer")
        self._not_expired(s, ticket)
        return state

    def _not_expired(self, s, ticket):
        valid = s.scalar(select(pm.lease.c.lease_until > func.clock_timestamp()).where(
            pm.lease.c.domain == ticket.domain))
        if not valid:
            raise FencedOut("expired domain writer")

    def _new_attempt(self, domain, resume=None):
        source_query(domain)  # Reject unknown domains before connecting.
        owner, run_id = str(uuid.uuid4()), resume or str(uuid.uuid4())
        with self.db.session() as s, s.begin():
            self._limits(s)
            now = s.scalar(select(func.clock_timestamp()))
            s.execute(pg_insert(pm.lease).values(domain=domain, fence=1, owner=owner,
                lease_until=now).on_conflict_do_nothing())
            state = s.execute(select(pm.lease).where(pm.lease.c.domain == domain)
                              .with_for_update()).mappings().one()
            if state["lease_until"] > now:
                raise FencedOut("domain lease is still owned")
            if resume:
                old = s.execute(select(pm.run).where(pm.run.c.id == resume)).mappings().one()
                if (state["latest_run"] != resume or not old["sealed"]
                        or old["epoch"] != EPOCH or old["scope"] != SCOPE
                        or old["domain"] != domain or old["status"] == "COMPLETE"):
                    raise FencedOut("run is not resumable")
            else:
                s.execute(insert(pm.run).values(id=run_id, manifest_id=str(uuid.uuid4()),
                    domain=domain, epoch=EPOCH, scope=SCOPE, sealed=False, item_count=0,
                    byte_count=0, continuation=0, status="CAPTURING", started_at=now))
            fence = state["fence"] + 1
            s.execute(update(pm.lease).where(pm.lease.c.domain == domain).values(
                fence=fence, owner=owner, latest_run=run_id,
                lease_until=now + timedelta(seconds=self.budget.lease_seconds)))
        return Ticket(run_id, domain, owner, fence)

    def resume(self, domain, run_id):
        """New fencing identity, same immutable manifest; expired latest run only."""
        return self._new_attempt(domain, resume=run_id)

    def capture(self, domain, *, after_page=None):
        ticket = self._new_attempt(domain)
        started = time.monotonic()
        try:
            # Single DB/connection for REPEATABLE READ capture AND manifest inserts.
            with self.db.engine.connect().execution_options(isolation_level="REPEATABLE READ") as conn:
                with Session(bind=conn) as s, s.begin():
                    self._limits(s)
                    self._lock(s, ticket)
                    snapshot = s.scalar(select(func.pg_current_snapshot().cast(String)))
                    count, byte_count, last = 0, 0, None
                    digest = hashlib.sha256()
                    while True:
                        if time.monotonic() - started > self.budget.seconds:
                            raise BudgetExceeded("capture time budget")
                        query = source_query(domain)
                        pk = models.EquipmentOrm.id if domain == "asset_master" else models.WorkOrderOrm.id
                        if last is not None:
                            query = query.where(pk > last)
                        rows = s.execute(query.order_by(pk).limit(self.budget.page)).mappings().all()
                        if not rows:
                            break
                        for row in rows:
                            if time.monotonic() - started > self.budget.seconds:
                                raise BudgetExceeded("capture time budget")
                            payload = captured_payload(domain, row)
                            count += 1
                            byte_count += len(encode([row["source_id"], payload]))
                            if count > self.budget.rows or byte_count > self.budget.bytes:
                                raise BudgetExceeded("capture row/byte budget")
                            fp = fingerprint(domain, row["source_id"], payload)
                            digest.update(encode([count, row["source_id"], fp]))
                            s.execute(insert(pm.item).values(run_id=ticket.run_id, ordinal=count,
                                source_id=row["source_id"], fingerprint=fp, payload=payload))
                        last = rows[-1]["source_id"]
                        if after_page:
                            after_page(count)  # Deterministic synthetic race injection only.
                    if time.monotonic() - started > self.budget.seconds:
                        raise BudgetExceeded("capture time budget")
                    self._not_expired(s, ticket)
                    s.execute(update(pm.run).where(pm.run.c.id == ticket.run_id).values(
                        sealed=True, item_count=count, byte_count=byte_count,
                        manifest_digest=digest.hexdigest(), snapshot=snapshot, status="SEALED"))
            return ticket
        except Exception:
            # The failed capture transaction inserts zero durable items. Keep attempt.
            with self.db.session() as s, s.begin():
                self._limits(s)
                self._lock(s, ticket)
                s.execute(update(pm.run).where(pm.run.c.id == ticket.run_id).values(status="FAILED"))
            raise

    def release(self, ticket):
        """Explicit participating-worker stop; retain all evidence for safe resume."""
        with self.db.session() as s, s.begin():
            self._limits(s)
            self._lock(s, ticket)
            s.execute(update(pm.lease).where(pm.lease.c.domain == ticket.domain)
                      .values(lease_until=func.clock_timestamp()))

    def _target_digest(self, s, domain, canonical_id):
        model = ENTITY_SPECS[domain].model
        current = s.get(model, canonical_id, populate_existing=True)
        if current is None:
            return None
        return hashlib.sha256(encode({c.name: getattr(current, c.name)
                                      for c in model.__table__.columns})).hexdigest()

    def process(self, ticket, *, max_items=100, seconds=10, before_commit=None, after_commit=None):
        """Bounded scan, one item/target/receipt/continuation transaction at a time.

        Fault hooks are test-only caller injection. Any write/validation exception
        propagates and rolls back, leaving that ordinal visibly UNPROCESSED.
        """
        if not (1 <= max_items <= 500 and 0 < seconds <= 60):
            raise ValueError("invalid processing budget")
        started, processed = time.monotonic(), 0
        while processed < max_items and time.monotonic() - started < seconds:
            with self.db.session() as s, s.begin():
                self._limits(s, seconds)
                self._lock(s, ticket)
                r = s.execute(select(pm.run).where(pm.run.c.id == ticket.run_id)
                              .with_for_update()).mappings().one()
                if not r["sealed"] or r["epoch"] != EPOCH or r["scope"] != SCOPE:
                    raise CaptureError("unsealed or incompatible manifest")
                row = s.execute(select(pm.item).where(pm.item.c.run_id == ticket.run_id,
                    pm.item.c.ordinal == r["continuation"] + 1)).mappings().one_or_none()
                if row is None:
                    # No B2 resolution ledger: any historical unresolved/unprocessed
                    # sealed input conservatively blocks new complete coverage too.
                    unresolved = s.scalar(select(exists(select(pm.item.c.ordinal).join(
                        pm.run, pm.item.c.run_id == pm.run.c.id).where(pm.run.c.domain == ticket.domain,
                            pm.run.c.sealed, (pm.item.c.disposition.is_(None)
                            | pm.item.c.disposition.not_in(TERMINAL))))))
                    receipts = s.execute(select(pm.item.c.target_id, pm.item.c.target_digest).where(
                        pm.item.c.run_id == ticket.run_id,
                        pm.item.c.target_id.is_not(None))).mappings().all()
                    for receipt in receipts:
                        if (receipt["target_digest"] != self._target_digest(
                                s, ticket.domain, receipt["target_id"])):
                            raise FencedOut("acknowledged target drift")
                        if time.monotonic() - started > seconds:
                            raise BudgetExceeded("completion time budget")
                    status = "PARTIAL" if unresolved else "COMPLETE"
                    s.execute(update(pm.run).where(pm.run.c.id == ticket.run_id).values(
                        status=status, completed_at=func.clock_timestamp() if not unresolved else None))
                    if not unresolved:
                        s.execute(update(pm.lease).where(pm.lease.c.domain == ticket.domain).values(
                            last_complete_run=ticket.run_id, last_complete_at=func.clock_timestamp()))
                    self._not_expired(s, ticket)
                    return self.inspect(ticket.run_id, session=s)
                if row["fingerprint"] != fingerprint(ticket.domain, row["source_id"], row["payload"]):
                    raise CaptureError("manifest fingerprint mismatch")
                record, disposition, reason = map_input(ticket.domain, row["source_id"], row["payload"])
                target_id, target_digest = None, None
                if record is not None:
                    target_id = record["canonical_id"]
                    prior = s.execute(select(pm.target).where(pm.target.c.domain == ticket.domain,
                        pm.target.c.canonical_id == target_id)).mappings().one_or_none()
                    if prior and (prior["fence"] > ticket.fence or
                            prior["target_digest"] != self._target_digest(s, ticket.domain, target_id)
                            or (prior["run_id"] == ticket.run_id and prior["fingerprint"] != row["fingerprint"])):
                        raise FencedOut("target revision drift or canonical identity collision")
                    stats = self.writer.persist_in_session(CanonicalCollection(ticket.domain, [record]), s)
                    disposition = "UNCHANGED" if stats.records_unchanged else "PROJECTED"
                    target_digest = self._target_digest(s, ticket.domain, target_id)
                    values = dict(domain=ticket.domain, canonical_id=target_id, fence=ticket.fence,
                        run_id=ticket.run_id, fingerprint=row["fingerprint"], target_digest=target_digest)
                    s.execute(pg_insert(pm.target).values(**values).on_conflict_do_update(
                        index_elements=[pm.target.c.domain, pm.target.c.canonical_id], set_=values))
                s.execute(update(pm.item).where(pm.item.c.run_id == ticket.run_id,
                    pm.item.c.ordinal == row["ordinal"]).values(disposition=disposition, reason=reason,
                        acked_at=func.clock_timestamp(), target_id=target_id, target_digest=target_digest))
                s.execute(update(pm.run).where(pm.run.c.id == ticket.run_id).values(
                    continuation=row["ordinal"], status="PARTIAL"))
                if before_commit:
                    before_commit(s)
                if time.monotonic() - started > seconds:
                    raise BudgetExceeded("processing time budget")
                self._not_expired(s, ticket)
            processed += 1
            if after_commit:
                after_commit()
        return self.inspect(ticket.run_id)

    def inspect(self, run_id, session=None):
        if session is not None:
            return dict(session.execute(select(pm.run).where(pm.run.c.id == run_id)).mappings().one())
        with self.db.session() as s:
            return self.inspect(run_id, session=s)
