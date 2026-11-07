"""Evidence-only WO activity aggregates; never substitute a record-change clock.

One latest retained BSR/IP WO, after which Registry and execution eligibility
are applied. Unknown task flags and clocks are reported, never coerced to false
or to zero activity. No operational source or write path is used here.
"""
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import and_, case, desc, func, or_, select

from src.repositories.mart_models import MaintenanceEventMart as Event, ReliabilityAssetRegistryMart as Registry

ACTIVITY_TIMEZONE = "Asia/Jakarta"
ACTIVITY_DATE_BASIS = "actual_start of CLOSE WO with verified actual clock and non-task evidence; no timestamp fallback"
ACTIVITY_COUNT_BASIS = "One latest retained WO identity in BSR/IP and the governed Asset Registry; not incidents or labor actions"


def current_utc(value: datetime | None = None) -> datetime:
    value = value or datetime.now(timezone.utc)
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def calendar_start(current: datetime, days: int) -> datetime:
    local = current.astimezone(ZoneInfo(ACTIVITY_TIMEZONE))
    return datetime.combine(local.date() - timedelta(days=days - 1), time.min, local.tzinfo).astimezone(timezone.utc)


def _task_state(database, sources, *, maximo_only: bool = False):
    # JSON strings "false" / "true", numbers, missing values and malformed
    # markers are UNKNOWN. Only observed JSON booleans establish task status.
    marker = sources["istask"] if maximo_only else sources["maximo"]["istask"]
    if database.engine.dialect.name == "postgresql":
        known = func.jsonb_typeof(marker) == "boolean"
        is_true, is_false = marker.as_string() == "true", marker.as_string() == "false"
    else:
        known = func.json_type(sources, "$.istask" if maximo_only else "$.maximo.istask").in_(("true", "false"))
        is_true, is_false = marker.as_boolean().is_(True), marker.as_boolean().is_(False)
    return case(
        (and_(known, is_true), "TASK"),
        (and_(known, is_false), "NON_TASK"),
        else_="UNKNOWN",
    )


def latest_registered_work_orders(database, *, compact: bool = False):
    """Return one current row per WO, *before* status/task/date filtering.

    Prefer the canonical scoped WO reference, falling back only to the retained
    source WO number. A missing identity stays unknown and cannot be activity.
    No grouping by parent/pctaskid is inferred.
    """
    key = func.coalesce(func.nullif(func.trim(Event.work_order_id), ""),
                        func.nullif(func.trim(Event.sources["maximo"]["wonum"].as_string()), ""))
    partition = (key.is_(None), func.coalesce(key, Event.canonical_id))
    source_site = Event.sources["maximo"]["siteid"].as_string()
    source_org = Event.sources["maximo"]["orgid"].as_string()
    # Investigation opts into a narrow sort: fetch payload only for the winning
    # identity. Filtering source scope and ranking order stay exactly the same.
    ranked = select(
        *([Event.canonical_id] if compact else [Event]), key.label("work_order_key"),
        func.count().over(partition_by=partition).label("identity_records"),
        func.row_number().over(partition_by=partition, order_by=(
            desc(Event.source_changed_at).nulls_last(), desc(Event.mart_updated_at), desc(Event.canonical_id)
        )).label("identity_rank"),
    ).where(
        Event.site_code == "BSR", Event.organization_code == "IP",
        or_(source_site.is_(None), source_site == "BSR"),
        or_(source_org.is_(None), source_org == "IP"),
    ).cte("ranked_work_orders")
    if compact:
        # Extract the source object once after the latest-identity/Registry join.
        # Carry no raw Event payload or irrelevant canonical fields downstream.
        ranked = select(
            Event.equipment_id, Event.status, Event.actual_start, Event.actual_finish, Event.event_type,
            Event.sources["maximo"].label("maximo"), Registry.source_asset_number,
            ranked.c.work_order_key, ranked.c.identity_records,
        ).join(ranked, Event.canonical_id == ranked.c.canonical_id).join(
            Registry, Registry.asset_ref == Event.equipment_id,
        ).where(ranked.c.identity_rank == 1, Registry.site_code == "BSR", Registry.organization_code == "IP"
        ).cte("latest_work_order_payload").prefix_with("MATERIALIZED", dialect="postgresql")
    maximo = ranked.c.maximo if compact else ranked.c.sources["maximo"]
    task_state = _task_state(database, maximo, maximo_only=True)
    invalid_order = and_(ranked.c.actual_start.is_not(None), ranked.c.actual_finish.is_not(None),
                         ranked.c.actual_finish < ranked.c.actual_start)
    start_verified = and_(ranked.c.actual_start.is_not(None),
        maximo["actual_dates"]["fields"]["actstart"]["state"].as_string() == "VALID")
    finish_verified = and_(ranked.c.actual_finish.is_not(None),
        maximo["actual_dates"]["fields"]["actfinish"]["state"].as_string() == "VALID")
    source_scope_verified = case((and_(
        maximo["scope_evidence"].as_string() == "DIRECT_SOURCE",
        maximo["siteid"].as_string() == "BSR",
        maximo["orgid"].as_string() == "IP",
    ), True), else_=False)
    if compact:
        # Scalar facts form a reusable checkpoint for metadata and chronology.
        facts = select(
            ranked.c.equipment_id, ranked.c.work_order_key, ranked.c.identity_records,
            ranked.c.status, ranked.c.actual_start, ranked.c.actual_finish,
            ranked.c.source_asset_number,
            func.coalesce(func.nullif(func.trim(maximo["worktype"].as_string()), ""),
                          func.nullif(func.trim(ranked.c.event_type), ""), "UNKNOWN").label("work_type"),
            task_state.label("task_state"), source_scope_verified.label("source_scope_verified"),
            invalid_order.label("invalid_actual_order"),
            case((and_(start_verified, ~invalid_order), True), else_=False).label("start_clock_verified"),
            case((and_(finish_verified, ~invalid_order), True), else_=False).label("finish_clock_verified"),
        ).cte("registered_work_order_facts").prefix_with("MATERIALIZED", dialect="postgresql")
        eligible = and_(facts.c.work_order_key.is_not(None), facts.c.status == "CLOSE",
                        facts.c.task_state == "NON_TASK", facts.c.source_scope_verified,
                        ~facts.c.invalid_actual_order)
        return select(
            facts,
            case((and_(eligible, facts.c.start_clock_verified), facts.c.actual_start), else_=None).label("activity_start"),
            case((and_(eligible, facts.c.finish_clock_verified), facts.c.actual_finish), else_=None).label("activity_finish"),
        ).cte("registered_work_orders")
    eligible = and_(ranked.c.work_order_key.is_not(None), ranked.c.status == "CLOSE", task_state == "NON_TASK", source_scope_verified, ~invalid_order)
    return select(
        ranked, Registry.source_asset_number,
        task_state.label("task_state"),
        source_scope_verified.label("source_scope_verified"),
        invalid_order.label("invalid_actual_order"),
        case((and_(start_verified, ~invalid_order), True), else_=False).label("start_clock_verified"),
        case((and_(finish_verified, ~invalid_order), True), else_=False).label("finish_clock_verified"),
        case((and_(eligible, start_verified), ranked.c.actual_start), else_=None).label("activity_start"),
        case((and_(eligible, finish_verified), ranked.c.actual_finish), else_=None).label("activity_finish"),
    ).join(Registry, Registry.asset_ref == ranked.c.equipment_id).where(
        ranked.c.identity_rank == 1, Registry.site_code == "BSR", Registry.organization_code == "IP",
    ).cte("registered_work_orders")


def activity_evidence_statement(scope):
    c = scope.c
    known_identity = c.work_order_key.is_not(None)
    closed_non_task = and_(known_identity, c.status == "CLOSE", c.task_state == "NON_TASK")
    return select(
        func.coalesce(func.sum(c.identity_records), 0).label("retained_records"),
        func.count().filter(known_identity).label("unique_work_orders"),
        func.coalesce(func.sum(c.identity_records - 1), 0).label("duplicate_records_excluded"),
        func.count().filter(~known_identity).label("unknown_identity_records"),
        func.count().filter(known_identity, c.status != "CLOSE").label("not_closed_work_orders"),
        func.count().filter(known_identity, c.status.is_(None)).label("unknown_status_work_orders"),
        func.count().filter(known_identity, c.task_state == "TASK").label("task_work_orders_excluded"),
        func.count().filter(known_identity, c.task_state == "UNKNOWN").label("unknown_task_work_orders"),
        func.count().filter(known_identity, c.source_scope_verified.is_(False)).label("unknown_source_scope_work_orders"),
        func.count().filter(known_identity, c.status == "CLOSE").label("closed_work_orders"),
        func.count().filter(closed_non_task).label("closed_non_task_work_orders"),
        func.count(c.activity_start).label("verified_start_work_orders"),
        func.count(c.activity_finish).label("verified_finish_work_orders"),
        func.count().filter(known_identity, c.status == "CLOSE", c.start_clock_verified.is_(False)).label("unknown_start_work_orders"),
        func.count().filter(known_identity, c.status == "CLOSE", c.finish_clock_verified.is_(False)).label("unknown_finish_work_orders"),
        func.count().filter(closed_non_task, c.invalid_actual_order.is_(True)).label("invalid_actual_order_work_orders"),
    ).select_from(scope)


def format_activity_evidence(row):
    values = {k: int(v or 0) for k, v in row.items()}
    incomplete = any(values[k] for k in ("unknown_identity_records", "unknown_task_work_orders", "unknown_source_scope_work_orders", "unknown_status_work_orders", "unknown_start_work_orders", "unknown_finish_work_orders"))
    values["availability"] = "UNAVAILABLE" if values["verified_start_work_orders"] == 0 else ("PARTIAL" if incomplete else "AVAILABLE")
    values["interpretation"] = "Known evidence only. Zero dated WO does not establish zero maintenance. Open/cancelled WO, tasks and unknown evidence are not physical activity."
    return values


def activity_evidence(database, scope):
    with database.read_session() as session:
        return format_activity_evidence(session.execute(activity_evidence_statement(scope)).one()._mapping)


def daily_activity(database, scope, *, current: datetime, days: int):
    """Bounded calendar-day counts in WIB, with independent metadata series."""
    start = calendar_start(current, days)
    local_start = start.astimezone(ZoneInfo(ACTIVITY_TIMEZONE)).date()
    rows = {str(local_start + timedelta(days=i)): {
        "date": str(local_start + timedelta(days=i)), "started_work_orders": 0,
        "finished_work_orders": 0, "record_changed_work_orders": 0,
    } for i in range(days)}
    for column, field in ((scope.c.activity_start, "started_work_orders"),
                          (scope.c.activity_finish, "finished_work_orders"),
                          (scope.c.source_changed_at, "record_changed_work_orders")):
        if database.engine.dialect.name == "postgresql":
            day = func.to_char(func.timezone(ACTIVITY_TIMEZONE, column), "YYYY-MM-DD")
        else:
            # SQLite is used only by hermetic tests. The production clocks are
            # timestamptz; test fixtures are UTC. Jakarta has no DST.
            day = func.date(column, "+7 hours")
        statement = select(day.label("day"), func.count().label("count")).where(
            scope.c.work_order_key.is_not(None), column >= start, column <= current,
        ).group_by(day).order_by(day).limit(days)
        with database.read_session() as session:
            for row in session.execute(statement).all():
                if row.day in rows:
                    rows[row.day][field] = int(row.count)
    return list(rows.values())
