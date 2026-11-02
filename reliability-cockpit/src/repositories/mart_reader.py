"""Read-only query repository for the MX-009R Reliability Mart."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, TypeVar

from sqlalchemy import Select, String, asc, case, cast, desc, func, literal, select

from src.repositories.mart_models import (
    AssetHealthAssessmentMart,
    AssetAfMappingMart,
    AssetMasterMart,
    FmeaAssessmentMart,
    MaintenanceEventMart,
    OverhaulEventMart,
    RcfaAnalysisMart,
    ReliabilityAssetRegistryMart,
)
from src.repositories.mart_database import MartDatabase

T = TypeVar("T")
SITE_CODE = "BSR"
ORGANIZATION_CODE = "IP"


def _raw_work_type(column: Any) -> Any:
    """Read the quarantined source Work Type on PostgreSQL and SQLite."""

    return func.nullif(func.trim(column["maximo"]["worktype"].as_string()), "")


def _raw_failure_code(column: Any) -> Any:
    """Read the approved source Failure Code value on PostgreSQL and SQLite."""

    return func.nullif(func.trim(column["maximo"]["failurecode"].as_string()), "")


def _raw_work_order_number(column: Any) -> Any:
    """Read the approved source Work Order number on PostgreSQL and SQLite."""

    return func.nullif(func.trim(column["maximo"]["wonum"].as_string()), "")


def _fmea_record_date(column: type[FmeaAssessmentMart]) -> Any:
    """Return the transparent source timestamp fallback for an FMEA record."""

    return func.coalesce(column.status_changed_at, column.source_updated_at)


def _rcfa_record_date(column: type[RcfaAnalysisMart]) -> Any:
    """Return the explicit RCFA record-date source used by the workspace."""

    return column.requested_at


def _assessment_date(column: type[AssetHealthAssessmentMart]) -> Any:
    """Return the verified source timestamp fallback for an assessment record."""

    return func.coalesce(column.status_changed_at, column.source_updated_at, column.source_created_at)


def _contains(value: str) -> str:
    """Escape wildcard characters for bounded user-facing contains filters."""

    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


@dataclass(frozen=True)
class QueryPage:
    items: list[Any]
    total: int
    offset: int
    limit: int

    @property
    def has_more(self) -> bool:
        return self.offset + len(self.items) < self.total


def _page(session: Any, statement: Select[Any], offset: int, limit: int) -> QueryPage:
    count_statement = select(func.count()).select_from(statement.order_by(None).subquery())
    total = int(session.scalar(count_statement) or 0)
    items = list(session.scalars(statement.offset(offset).limit(limit)).all())
    return QueryPage(items=items, total=total, offset=offset, limit=limit)


def _page_rows(session: Any, statement: Select[Any], offset: int, limit: int) -> QueryPage:
    count_statement = select(func.count()).select_from(statement.order_by(None).subquery())
    total = int(session.scalar(count_statement) or 0)
    items = list(session.execute(statement.offset(offset).limit(limit)).all())
    return QueryPage(items=items, total=total, offset=offset, limit=limit)


class MartQueryRepository:
    """SQL-only read access to the six canonical Mart entities.

    Scope is applied in every method as defense in depth.  This repository has
    no persistence methods and receives a ``MartDatabase`` that exposes only a
    read-only session wrapper.
    """

    def __init__(self, database: MartDatabase):
        self.database = database

    @staticmethod
    def _scope(statement: Select[Any], model: type) -> Select[Any]:
        return statement.where(
            model.site_code == SITE_CODE,
            model.organization_code == ORGANIZATION_CODE,
        )

    @staticmethod
    def _sort(statement: Select[Any], column: Any, reverse: bool = True) -> Select[Any]:
        return statement.order_by(desc(column) if reverse else asc(column), asc(column))

    def _gap_days(self, later: Any, earlier: Any) -> Any:
        if self.database.engine.dialect.name == "sqlite":
            return func.julianday(later) - func.julianday(earlier)
        return func.extract("epoch", later - earlier) / 86400.0

    def list_assets(
        self,
        *,
        status: str | None = None,
        unit: str | None = None,
        asset_type: str | None = None,
        offset: int = 0,
        limit: int = 50,
        sort: str = "updated_desc",
    ) -> QueryPage:
        statement = self._scope(
            select(AssetMasterMart)
            .join(ReliabilityAssetRegistryMart, ReliabilityAssetRegistryMart.asset_ref == AssetMasterMart.canonical_id)
            .where(
                ReliabilityAssetRegistryMart.site_code == SITE_CODE,
                ReliabilityAssetRegistryMart.organization_code == ORGANIZATION_CODE,
            ),
            AssetMasterMart,
        )
        if status:
            statement = statement.where(AssetMasterMart.status == status)
        if unit:
            statement = statement.where(AssetMasterMart.unit == unit)
        if asset_type:
            statement = statement.where(AssetMasterMart.asset_type == asset_type)
        if sort == "status":
            statement = self._sort(statement, AssetMasterMart.status, False)
        else:
            statement = self._sort(statement, AssetMasterMart.source_updated_at, sort != "updated_asc")
        with self.database.read_session() as session:
            return _page(session, statement, offset, limit)

    def get_asset(self, canonical_id: str) -> AssetMasterMart | None:
        statement = self._scope(
            select(AssetMasterMart)
            .join(ReliabilityAssetRegistryMart, ReliabilityAssetRegistryMart.asset_ref == AssetMasterMart.canonical_id)
            .where(
                AssetMasterMart.canonical_id == canonical_id,
                ReliabilityAssetRegistryMart.site_code == SITE_CODE,
                ReliabilityAssetRegistryMart.organization_code == ORGANIZATION_CODE,
            ),
            AssetMasterMart,
        )
        with self.database.read_session() as session:
            return session.scalar(statement)

    def list_asset_af_mappings(self, canonical_id: str | None = None) -> list[AssetAfMappingMart]:
        """Return governance rows for registered BSR/IP Assets.

        Retired rows remain visible so the API can explain governance history;
        readiness logic deliberately ignores their retired state. Supplying an
        Asset ID keeps the read bounded to that canonical Asset.
        """

        statement = (
            select(AssetAfMappingMart)
            .join(AssetMasterMart, AssetMasterMart.canonical_id == AssetAfMappingMart.canonical_asset_id)
            .join(ReliabilityAssetRegistryMart, ReliabilityAssetRegistryMart.asset_ref == AssetMasterMart.canonical_id)
            .where(
                AssetMasterMart.site_code == SITE_CODE,
                AssetMasterMart.organization_code == ORGANIZATION_CODE,
                ReliabilityAssetRegistryMart.site_code == SITE_CODE,
                ReliabilityAssetRegistryMart.organization_code == ORGANIZATION_CODE,
            )
            .order_by(AssetAfMappingMart.created_at, AssetAfMappingMart.id)
        )
        if canonical_id is not None:
            statement = statement.where(AssetAfMappingMart.canonical_asset_id == canonical_id)
        with self.database.read_session() as session:
            return list(session.scalars(statement).all())

    def list_maintenance(
        self,
        *,
        asset_ref: str | None = None,
        work_order_id: str | None = None,
        status: str | None = None,
        event_type: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        offset: int = 0,
        limit: int = 50,
        sort: str = "date_desc",
    ) -> QueryPage:
        statement = self._scope(
            select(MaintenanceEventMart)
            .join(ReliabilityAssetRegistryMart, ReliabilityAssetRegistryMart.asset_ref == MaintenanceEventMart.equipment_id)
            .where(
                ReliabilityAssetRegistryMart.site_code == SITE_CODE,
                ReliabilityAssetRegistryMart.organization_code == ORGANIZATION_CODE,
            ),
            MaintenanceEventMart,
        )
        if asset_ref:
            statement = statement.where(MaintenanceEventMart.equipment_id == asset_ref)
        if work_order_id:
            statement = statement.where(MaintenanceEventMart.work_order_id == work_order_id)
        if status:
            statement = statement.where(MaintenanceEventMart.status == status)
        if event_type:
            statement = statement.where(MaintenanceEventMart.event_type == event_type)
        date_column = func.coalesce(MaintenanceEventMart.actual_start, MaintenanceEventMart.source_changed_at)
        if date_from:
            statement = statement.where(date_column >= date_from)
        if date_to:
            statement = statement.where(date_column <= date_to)
        column = MaintenanceEventMart.status if sort == "status" else date_column
        statement = self._sort(statement, column, sort not in {"date_asc"})
        with self.database.read_session() as session:
            return _page(session, statement, offset, limit)

    def list_fmea(
        self,
        *,
        asset_ref: str | None = None,
        lifecycle_status: str | None = None,
        source_number: str | None = None,
        updated_from: datetime | None = None,
        updated_to: datetime | None = None,
        offset: int = 0,
        limit: int = 50,
        sort: str = "updated_desc",
    ) -> QueryPage:
        statement = self._scope(select(FmeaAssessmentMart), FmeaAssessmentMart)
        if asset_ref:
            statement = statement.where(FmeaAssessmentMart.asset_ref == asset_ref)
        if lifecycle_status:
            statement = statement.where(FmeaAssessmentMart.lifecycle_status == lifecycle_status)
        if source_number:
            statement = statement.where(FmeaAssessmentMart.source_number == source_number)
        if updated_from:
            statement = statement.where(FmeaAssessmentMart.source_updated_at >= updated_from)
        if updated_to:
            statement = statement.where(FmeaAssessmentMart.source_updated_at <= updated_to)
        column = FmeaAssessmentMart.lifecycle_status if sort == "status" else FmeaAssessmentMart.source_updated_at
        statement = self._sort(statement, column, sort != "updated_asc")
        with self.database.read_session() as session:
            return _page(session, statement, offset, limit)

    def list_fmea_workspace(
        self,
        *,
        asset_ref: str | None = None,
        asset_number: str | None = None,
        lifecycle_status: str | None = None,
        source_number: str | None = None,
        source_failure_code: str | None = None,
        updated_from: datetime | None = None,
        updated_to: datetime | None = None,
        offset: int = 0,
        limit: int = 50,
        sort: str = "updated_desc",
        as_of: datetime | None = None,
    ) -> QueryPage:
        """Return Registry-scoped FMEA rows with business-facing projections."""

        current = as_of or datetime.now(timezone.utc)
        if current.tzinfo is None:
            current = current.replace(tzinfo=timezone.utc)
        record_date = _fmea_record_date(FmeaAssessmentMart)
        raw_failure_code = _raw_failure_code(FmeaAssessmentMart.sources)
        columns = (
            FmeaAssessmentMart.canonical_id,
            FmeaAssessmentMart.contract_version,
            FmeaAssessmentMart.source_record_id,
            FmeaAssessmentMart.source_number,
            FmeaAssessmentMart.revision,
            FmeaAssessmentMart.lifecycle_status,
            FmeaAssessmentMart.description,
            FmeaAssessmentMart.asset_ref,
            FmeaAssessmentMart.failure_code_ref,
            FmeaAssessmentMart.site_code,
            FmeaAssessmentMart.organization_code,
            FmeaAssessmentMart.source_updated_at,
            FmeaAssessmentMart.status_changed_at,
            ReliabilityAssetRegistryMart.source_asset_number.label("source_asset_number"),
            AssetMasterMart.description.label("asset_description"),
            raw_failure_code.label("source_failure_code"),
            record_date.label("fmea_record_date"),
            self._gap_days(literal(current), record_date).label("fmea_age_days"),
        )
        statement = (
            select(*columns)
            .select_from(FmeaAssessmentMart)
            .join(ReliabilityAssetRegistryMart, ReliabilityAssetRegistryMart.asset_ref == FmeaAssessmentMart.asset_ref)
            .outerjoin(
                AssetMasterMart,
                (AssetMasterMart.canonical_id == FmeaAssessmentMart.asset_ref)
                & (AssetMasterMart.site_code == SITE_CODE)
                & (AssetMasterMart.organization_code == ORGANIZATION_CODE),
            )
            .where(
                FmeaAssessmentMart.site_code == SITE_CODE,
                FmeaAssessmentMart.organization_code == ORGANIZATION_CODE,
                ReliabilityAssetRegistryMart.site_code == SITE_CODE,
                ReliabilityAssetRegistryMart.organization_code == ORGANIZATION_CODE,
            )
        )
        if asset_ref:
            statement = statement.where(FmeaAssessmentMart.asset_ref == asset_ref)
        if asset_number:
            statement = statement.where(ReliabilityAssetRegistryMart.source_asset_number.ilike(f"%{_contains(asset_number)}%", escape="\\"))
        if lifecycle_status:
            statement = statement.where(FmeaAssessmentMart.lifecycle_status == lifecycle_status)
        if source_number:
            statement = statement.where(FmeaAssessmentMart.source_number.ilike(f"%{_contains(source_number)}%", escape="\\"))
        if source_failure_code:
            statement = statement.where(raw_failure_code.ilike(f"%{_contains(source_failure_code)}%", escape="\\"))
        if updated_from:
            statement = statement.where(FmeaAssessmentMart.source_updated_at >= updated_from)
        if updated_to:
            statement = statement.where(FmeaAssessmentMart.source_updated_at <= updated_to)
        order_column = FmeaAssessmentMart.lifecycle_status if sort == "status" else record_date
        statement = statement.order_by(desc(order_column) if sort != "updated_asc" else asc(order_column), asc(FmeaAssessmentMart.canonical_id))
        with self.database.read_session() as session:
            return _page_rows(session, statement, offset, limit)

    def list_health(
        self,
        *,
        asset_ref: str | None = None,
        lifecycle_status: str | None = None,
        updated_from: datetime | None = None,
        updated_to: datetime | None = None,
        offset: int = 0,
        limit: int = 50,
        sort: str = "updated_desc",
    ) -> QueryPage:
        statement = self._scope(select(AssetHealthAssessmentMart), AssetHealthAssessmentMart)
        if asset_ref:
            statement = statement.where(AssetHealthAssessmentMart.asset_ref == asset_ref)
        if lifecycle_status:
            statement = statement.where(AssetHealthAssessmentMart.lifecycle_status == lifecycle_status)
        if updated_from:
            statement = statement.where(AssetHealthAssessmentMart.source_updated_at >= updated_from)
        if updated_to:
            statement = statement.where(AssetHealthAssessmentMart.source_updated_at <= updated_to)
        column = AssetHealthAssessmentMart.lifecycle_status if sort == "status" else AssetHealthAssessmentMart.source_updated_at
        statement = self._sort(statement, column, sort != "updated_asc")
        with self.database.read_session() as session:
            return _page(session, statement, offset, limit)

    def list_health_workspace(
        self,
        *,
        asset_ref: str | None = None,
        asset_number: str | None = None,
        description: str | None = None,
        lifecycle_status: str | None = None,
        updated_from: datetime | None = None,
        updated_to: datetime | None = None,
        offset: int = 0,
        limit: int = 50,
        sort: str = "updated_desc",
        as_of: datetime | None = None,
    ) -> QueryPage:
        """Return Registry-scoped Asset Health rows with management identity."""

        current = as_of or datetime.now(timezone.utc)
        if current.tzinfo is None:
            current = current.replace(tzinfo=timezone.utc)
        record_date = _assessment_date(AssetHealthAssessmentMart)
        columns = (
            AssetHealthAssessmentMart.canonical_id,
            AssetHealthAssessmentMart.contract_version,
            AssetHealthAssessmentMart.source_record_id,
            AssetHealthAssessmentMart.revision,
            AssetHealthAssessmentMart.lifecycle_status,
            AssetHealthAssessmentMart.description,
            AssetHealthAssessmentMart.function_description,
            AssetHealthAssessmentMart.asset_ref,
            AssetHealthAssessmentMart.site_code,
            AssetHealthAssessmentMart.organization_code,
            AssetHealthAssessmentMart.source_created_at,
            AssetHealthAssessmentMart.source_updated_at,
            AssetHealthAssessmentMart.status_changed_at,
            ReliabilityAssetRegistryMart.source_asset_number.label("source_asset_number"),
            AssetMasterMart.description.label("asset_description"),
            record_date.label("assessment_record_date"),
            self._gap_days(literal(current), record_date).label("assessment_age_days"),
        )
        statement = (
            select(*columns)
            .select_from(AssetHealthAssessmentMart)
            .join(ReliabilityAssetRegistryMart, ReliabilityAssetRegistryMart.asset_ref == AssetHealthAssessmentMart.asset_ref)
            .outerjoin(
                AssetMasterMart,
                (AssetMasterMart.canonical_id == AssetHealthAssessmentMart.asset_ref)
                & (AssetMasterMart.site_code == SITE_CODE)
                & (AssetMasterMart.organization_code == ORGANIZATION_CODE),
            )
            .where(
                AssetHealthAssessmentMart.site_code == SITE_CODE,
                AssetHealthAssessmentMart.organization_code == ORGANIZATION_CODE,
                ReliabilityAssetRegistryMart.site_code == SITE_CODE,
                ReliabilityAssetRegistryMart.organization_code == ORGANIZATION_CODE,
            )
        )
        if asset_ref:
            statement = statement.where(AssetHealthAssessmentMart.asset_ref == asset_ref)
        if asset_number:
            statement = statement.where(ReliabilityAssetRegistryMart.source_asset_number.ilike(f"%{_contains(asset_number)}%", escape="\\"))
        if description:
            statement = statement.where(AssetMasterMart.description.ilike(f"%{_contains(description)}%", escape="\\"))
        if lifecycle_status:
            statement = statement.where(AssetHealthAssessmentMart.lifecycle_status == lifecycle_status)
        if updated_from:
            statement = statement.where(AssetHealthAssessmentMart.source_updated_at >= updated_from)
        if updated_to:
            statement = statement.where(AssetHealthAssessmentMart.source_updated_at <= updated_to)
        order_column = AssetHealthAssessmentMart.lifecycle_status if sort == "status" else record_date
        statement = statement.order_by(desc(order_column) if sort != "updated_asc" else asc(order_column), asc(AssetHealthAssessmentMart.canonical_id))
        with self.database.read_session() as session:
            return _page_rows(session, statement, offset, limit)

    def latest_health(self, asset_ref: str) -> AssetHealthAssessmentMart | None:
        statement = self._scope(
            select(AssetHealthAssessmentMart).where(AssetHealthAssessmentMart.asset_ref == asset_ref),
            AssetHealthAssessmentMart,
        ).order_by(desc(_assessment_date(AssetHealthAssessmentMart)), desc(AssetHealthAssessmentMart.canonical_id))
        with self.database.read_session() as session:
            return session.scalar(statement.limit(1))

    def latest_health_workspace(self, asset_ref: str, *, as_of: datetime | None = None) -> Any | None:
        page = self.list_health_workspace(asset_ref=asset_ref, offset=0, limit=1, as_of=as_of)
        return page.items[0] if page.items else None

    def list_rcfa(
        self,
        *,
        lifecycle_status: str | None = None,
        category: str | None = None,
        source_number: str | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        offset: int = 0,
        limit: int = 50,
        sort: str = "created_desc",
    ) -> QueryPage:
        statement = self._scope(select(RcfaAnalysisMart), RcfaAnalysisMart)
        if lifecycle_status:
            statement = statement.where(RcfaAnalysisMart.lifecycle_status == lifecycle_status)
        if category:
            statement = statement.where(RcfaAnalysisMart.category == category)
        if source_number:
            statement = statement.where(RcfaAnalysisMart.source_number == source_number)
        if created_from:
            statement = statement.where(RcfaAnalysisMart.source_created_at >= created_from)
        if created_to:
            statement = statement.where(RcfaAnalysisMart.source_created_at <= created_to)
        column = RcfaAnalysisMart.lifecycle_status if sort == "status" else RcfaAnalysisMart.source_created_at
        statement = self._sort(statement, column, sort != "created_asc")
        with self.database.read_session() as session:
            return _page(session, statement, offset, limit)

    def list_rcfa_workspace(
        self,
        *,
        lifecycle_status: str | None = None,
        category: str | None = None,
        source_number: str | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        offset: int = 0,
        limit: int = 50,
        sort: str = "created_desc",
        as_of: datetime | None = None,
    ) -> QueryPage:
        """Return the global RCFA population without relationship projections."""

        current = as_of or datetime.now(timezone.utc)
        if current.tzinfo is None:
            current = current.replace(tzinfo=timezone.utc)
        record_date = _rcfa_record_date(RcfaAnalysisMart)
        columns = (
            RcfaAnalysisMart.canonical_id,
            RcfaAnalysisMart.contract_version,
            RcfaAnalysisMart.source_record_id,
            RcfaAnalysisMart.source_number,
            RcfaAnalysisMart.revision,
            RcfaAnalysisMart.lifecycle_status,
            RcfaAnalysisMart.category,
            RcfaAnalysisMart.asset_ref,
            RcfaAnalysisMart.location_ref,
            RcfaAnalysisMart.workorder_ref,
            RcfaAnalysisMart.failure_event_ref,
            RcfaAnalysisMart.site_code,
            RcfaAnalysisMart.organization_code,
            RcfaAnalysisMart.source_created_at,
            RcfaAnalysisMart.requested_at,
            record_date.label("rcfa_record_date"),
            self._gap_days(literal(current), record_date).label("rcfa_age_days"),
        )
        statement = self._scope(select(*columns), RcfaAnalysisMart)
        if lifecycle_status:
            statement = statement.where(RcfaAnalysisMart.lifecycle_status == lifecycle_status)
        if category:
            statement = statement.where(RcfaAnalysisMart.category.ilike(f"%{_contains(category)}%", escape="\\"))
        if source_number:
            statement = statement.where(RcfaAnalysisMart.source_number.ilike(f"%{_contains(source_number)}%", escape="\\"))
        if created_from:
            statement = statement.where(RcfaAnalysisMart.source_created_at >= created_from)
        if created_to:
            statement = statement.where(RcfaAnalysisMart.source_created_at <= created_to)
        order_column = RcfaAnalysisMart.lifecycle_status if sort == "status" else record_date
        statement = statement.order_by(desc(order_column) if sort != "created_asc" else asc(order_column), asc(RcfaAnalysisMart.canonical_id))
        with self.database.read_session() as session:
            return _page_rows(session, statement, offset, limit)

    def list_overhauls(
        self,
        *,
        asset_ref: str | None = None,
        workorder_ref: str | None = None,
        lifecycle_status: str | None = None,
        planned_from: datetime | None = None,
        planned_to: datetime | None = None,
        actual_from: datetime | None = None,
        actual_to: datetime | None = None,
        offset: int = 0,
        limit: int = 50,
        sort: str = "date_desc",
    ) -> QueryPage:
        statement = self._scope(select(OverhaulEventMart), OverhaulEventMart)
        if asset_ref:
            statement = statement.where(OverhaulEventMart.asset_ref == asset_ref)
        if workorder_ref:
            statement = statement.where(OverhaulEventMart.workorder_ref == workorder_ref)
        if lifecycle_status:
            statement = statement.where(OverhaulEventMart.lifecycle_status == lifecycle_status)
        if planned_from:
            statement = statement.where(OverhaulEventMart.planned_start_at >= planned_from)
        if planned_to:
            statement = statement.where(OverhaulEventMart.planned_start_at <= planned_to)
        if actual_from:
            statement = statement.where(OverhaulEventMart.actual_start_at >= actual_from)
        if actual_to:
            statement = statement.where(OverhaulEventMart.actual_start_at <= actual_to)
        column = OverhaulEventMart.lifecycle_status if sort == "status" else OverhaulEventMart.actual_start_at
        statement = self._sort(statement, column, sort != "date_asc")
        with self.database.read_session() as session:
            return _page(session, statement, offset, limit)

    def list_overhaul_workspace(
        self,
        *,
        source_number: str | None = None,
        asset_ref: str | None = None,
        workorder_ref: str | None = None,
        source_work_order_number: str | None = None,
        lifecycle_status: str | None = None,
        planned_from: datetime | None = None,
        planned_to: datetime | None = None,
        actual_from: datetime | None = None,
        actual_to: datetime | None = None,
        offset: int = 0,
        limit: int = 50,
        sort: str = "date_desc",
    ) -> QueryPage:
        """Return Overhaul rows with factual relationship projections.

        The Asset relationship is never derived here.  ``asset_ref`` is the
        already-projected result of the verified Work Order path; this query
        only checks whether that reference resolves locally.
        """

        source_work_order = _raw_work_order_number(OverhaulEventMart.sources)
        maintenance_work_orders = select(MaintenanceEventMart.work_order_id).where(
            MaintenanceEventMart.site_code == SITE_CODE,
            MaintenanceEventMart.organization_code == ORGANIZATION_CODE,
            MaintenanceEventMart.work_order_id.is_not(None),
        )
        asset_master_refs = select(AssetMasterMart.canonical_id).where(
            AssetMasterMart.site_code == SITE_CODE,
            AssetMasterMart.organization_code == ORGANIZATION_CODE,
        )
        registry_refs = select(ReliabilityAssetRegistryMart.asset_ref).where(
            ReliabilityAssetRegistryMart.site_code == SITE_CODE,
            ReliabilityAssetRegistryMart.organization_code == ORGANIZATION_CODE,
        )
        workorder_resolution = case(
            (OverhaulEventMart.workorder_ref.is_(None), literal("SOURCE_WORK_ORDER_MISSING")),
            (OverhaulEventMart.workorder_ref.in_(maintenance_work_orders), literal("SOURCE_LINK_VERIFIED_AND_MART_RESOLVED")),
            else_=literal("SOURCE_LINK_VERIFIED_BUT_MART_UNRESOLVED"),
        )
        asset_resolution = case(
            (OverhaulEventMart.asset_ref.in_(registry_refs), literal("ASSET_RESOLVED_REGISTERED")),
            (OverhaulEventMart.asset_ref.in_(asset_master_refs), literal("ASSET_RESOLVED_TECHNICAL_CONTEXT")),
            else_=literal("ASSET_UNRESOLVED"),
        )
        date_column = func.coalesce(
            OverhaulEventMart.actual_start_at,
            OverhaulEventMart.planned_start_at,
            OverhaulEventMart.source_updated_at,
        )
        columns = (
            OverhaulEventMart.canonical_id,
            OverhaulEventMart.contract_version,
            OverhaulEventMart.source_record_id,
            OverhaulEventMart.source_number,
            OverhaulEventMart.lifecycle_status,
            OverhaulEventMart.workorder_ref,
            OverhaulEventMart.asset_ref,
            OverhaulEventMart.site_code,
            OverhaulEventMart.organization_code,
            OverhaulEventMart.planned_start_at,
            OverhaulEventMart.planned_finish_at,
            OverhaulEventMart.actual_start_at,
            OverhaulEventMart.actual_finish_at,
            OverhaulEventMart.progress,
            OverhaulEventMart.source_created_at,
            OverhaulEventMart.source_updated_at,
            OverhaulEventMart.unresolved_source_attributes,
            OverhaulEventMart.sources,
            ReliabilityAssetRegistryMart.source_asset_number.label("source_asset_number"),
            AssetMasterMart.description.label("asset_description"),
            source_work_order.label("source_work_order_number"),
            workorder_resolution.label("work_order_resolution"),
            asset_resolution.label("asset_resolution"),
        )
        statement = (
            select(*columns)
            .select_from(OverhaulEventMart)
            .outerjoin(
                AssetMasterMart,
                (AssetMasterMart.canonical_id == OverhaulEventMart.asset_ref)
                & (AssetMasterMart.site_code == SITE_CODE)
                & (AssetMasterMart.organization_code == ORGANIZATION_CODE),
            )
            .outerjoin(
                ReliabilityAssetRegistryMart,
                (ReliabilityAssetRegistryMart.asset_ref == OverhaulEventMart.asset_ref)
                & (ReliabilityAssetRegistryMart.site_code == SITE_CODE)
                & (ReliabilityAssetRegistryMart.organization_code == ORGANIZATION_CODE),
            )
            .where(
                OverhaulEventMart.site_code == SITE_CODE,
                OverhaulEventMart.organization_code == ORGANIZATION_CODE,
            )
        )
        if asset_ref:
            statement = statement.where(OverhaulEventMart.asset_ref == asset_ref)
        if workorder_ref:
            statement = statement.where(OverhaulEventMart.workorder_ref == workorder_ref)
        if source_number:
            statement = statement.where(OverhaulEventMart.source_number.ilike(f"%{_contains(source_number)}%", escape="\\"))
        if source_work_order_number:
            statement = statement.where(source_work_order.ilike(f"%{_contains(source_work_order_number)}%", escape="\\"))
        if lifecycle_status:
            statement = statement.where(OverhaulEventMart.lifecycle_status == lifecycle_status)
        if planned_from:
            statement = statement.where(OverhaulEventMart.planned_start_at >= planned_from)
        if planned_to:
            statement = statement.where(OverhaulEventMart.planned_start_at <= planned_to)
        if actual_from:
            statement = statement.where(OverhaulEventMart.actual_start_at >= actual_from)
        if actual_to:
            statement = statement.where(OverhaulEventMart.actual_start_at <= actual_to)
        order_column = OverhaulEventMart.lifecycle_status if sort == "status" else date_column
        statement = statement.order_by(desc(order_column) if sort != "date_asc" else asc(order_column), asc(OverhaulEventMart.canonical_id))
        with self.database.read_session() as session:
            return _page_rows(session, statement, offset, limit)

    def integrity_summary(self) -> dict[str, int]:
        with self.database.read_session() as session:
            technical_asset_total = session.scalar(select(func.count(AssetMasterMart.canonical_id)).where(
                AssetMasterMart.site_code == SITE_CODE,
                AssetMasterMart.organization_code == ORGANIZATION_CODE,
            )) or 0
            registered_total = session.scalar(select(func.count(ReliabilityAssetRegistryMart.asset_ref)).where(
                ReliabilityAssetRegistryMart.site_code == SITE_CODE,
                ReliabilityAssetRegistryMart.organization_code == ORGANIZATION_CODE,
            )) or 0
            registered_resolved = session.scalar(select(func.count(ReliabilityAssetRegistryMart.asset_ref)).join(
                AssetMasterMart, ReliabilityAssetRegistryMart.asset_ref == AssetMasterMart.canonical_id
            ).where(
                ReliabilityAssetRegistryMart.site_code == SITE_CODE,
                ReliabilityAssetRegistryMart.organization_code == ORGANIZATION_CODE,
            )) or 0
            maintenance_registered_total = session.scalar(select(func.count(MaintenanceEventMart.canonical_id)).join(
                ReliabilityAssetRegistryMart, ReliabilityAssetRegistryMart.asset_ref == MaintenanceEventMart.equipment_id
            ).where(
                MaintenanceEventMart.site_code == SITE_CODE,
                MaintenanceEventMart.organization_code == ORGANIZATION_CODE,
            )) or 0
            asset_total = session.scalar(select(func.count(FmeaAssessmentMart.canonical_id)).where(
                FmeaAssessmentMart.site_code == SITE_CODE,
                FmeaAssessmentMart.organization_code == ORGANIZATION_CODE,
                FmeaAssessmentMart.asset_ref.is_not(None),
            )) or 0
            asset_total += session.scalar(select(func.count(AssetHealthAssessmentMart.canonical_id)).where(
                AssetHealthAssessmentMart.site_code == SITE_CODE,
                AssetHealthAssessmentMart.organization_code == ORGANIZATION_CODE,
                AssetHealthAssessmentMart.asset_ref.is_not(None),
            )) or 0
            asset_total += session.scalar(select(func.count(MaintenanceEventMart.canonical_id)).where(
                MaintenanceEventMart.site_code == SITE_CODE,
                MaintenanceEventMart.organization_code == ORGANIZATION_CODE,
                MaintenanceEventMart.equipment_id.is_not(None),
            )) or 0
            asset_total += session.scalar(select(func.count(OverhaulEventMart.canonical_id)).where(
                OverhaulEventMart.site_code == SITE_CODE,
                OverhaulEventMart.organization_code == ORGANIZATION_CODE,
                OverhaulEventMart.asset_ref.is_not(None),
            )) or 0
            asset_master_ids = select(AssetMasterMart.canonical_id).where(
                AssetMasterMart.site_code == SITE_CODE,
                AssetMasterMart.organization_code == ORGANIZATION_CODE,
            )
            asset_resolved = session.scalar(select(func.count(FmeaAssessmentMart.canonical_id)).where(
                FmeaAssessmentMart.site_code == SITE_CODE,
                FmeaAssessmentMart.organization_code == ORGANIZATION_CODE,
                FmeaAssessmentMart.asset_ref.in_(asset_master_ids),
            )) or 0
            asset_resolved += session.scalar(select(func.count(AssetHealthAssessmentMart.canonical_id)).where(
                AssetHealthAssessmentMart.site_code == SITE_CODE,
                AssetHealthAssessmentMart.organization_code == ORGANIZATION_CODE,
                AssetHealthAssessmentMart.asset_ref.in_(asset_master_ids),
            )) or 0
            asset_resolved += session.scalar(select(func.count(MaintenanceEventMart.canonical_id)).where(
                MaintenanceEventMart.site_code == SITE_CODE,
                MaintenanceEventMart.organization_code == ORGANIZATION_CODE,
                MaintenanceEventMart.equipment_id.in_(asset_master_ids),
            )) or 0
            asset_resolved += session.scalar(select(func.count(OverhaulEventMart.canonical_id)).where(
                OverhaulEventMart.site_code == SITE_CODE,
                OverhaulEventMart.organization_code == ORGANIZATION_CODE,
                OverhaulEventMart.asset_ref.in_(asset_master_ids),
            )) or 0
            work_total = session.scalar(select(func.count(OverhaulEventMart.canonical_id)).where(
                OverhaulEventMart.site_code == SITE_CODE,
                OverhaulEventMart.organization_code == ORGANIZATION_CODE,
                OverhaulEventMart.workorder_ref.is_not(None),
            )) or 0
            work_resolved = session.scalar(select(func.count(OverhaulEventMart.canonical_id)).where(
                OverhaulEventMart.site_code == SITE_CODE,
                OverhaulEventMart.organization_code == ORGANIZATION_CODE,
                OverhaulEventMart.workorder_ref.in_(
                    select(MaintenanceEventMart.work_order_id).where(
                        MaintenanceEventMart.site_code == SITE_CODE,
                        MaintenanceEventMart.organization_code == ORGANIZATION_CODE,
                        MaintenanceEventMart.work_order_id.is_not(None),
                    )
                ),
            )) or 0
        return {
            "asset_refs_total": int(asset_total),
            "asset_refs_resolved": int(min(asset_resolved, asset_total)),
            "asset_refs_unresolved": int(max(asset_total - asset_resolved, 0)),
            "workorder_refs_total": int(work_total),
            "workorder_refs_resolved": int(work_resolved),
            "workorder_refs_unresolved": int(work_total - work_resolved),
            "technical_asset_context_total": int(technical_asset_total),
            "registered_assets_total": int(registered_total),
            "registered_assets_resolved": int(registered_resolved),
            "registered_assets_unresolved": int(registered_total - registered_resolved),
            "maintenance_registered_total": int(maintenance_registered_total),
        }

    def registry_summary(self) -> dict[str, object]:
        with self.database.read_session() as session:
            row = session.execute(
                select(
                    func.count(ReliabilityAssetRegistryMart.asset_ref),
                    func.max(ReliabilityAssetRegistryMart.snapshot_sha256),
                    func.max(ReliabilityAssetRegistryMart.snapshot_row_count),
                    func.max(ReliabilityAssetRegistryMart.snapshot_imported_at),
                ).where(
                    ReliabilityAssetRegistryMart.site_code == SITE_CODE,
                    ReliabilityAssetRegistryMart.organization_code == ORGANIZATION_CODE,
                )
            ).one()
        return {
            "registered_asset_count": int(row[0] or 0),
            "snapshot_sha256": row[1],
            "snapshot_row_count": row[2],
            "snapshot_imported_at": row[3],
            "source": "MAXIMO_LIST_OF_ASSETS",
        }

    def data_trust_overview(self, *, as_of: datetime | None = None) -> dict[str, object]:
        """Return bounded population, relationship, and semantic evidence.

        This method composes aggregate-only domain evidence.  It deliberately
        does not read raw rows or consult Collector operational metadata, so a
        latest source-record date is never presented as ingestion freshness.
        """

        current = as_of or datetime.now(timezone.utc)
        if current.tzinfo is None:
            current = current.replace(tzinfo=timezone.utc)
        registry_scope = (
            ReliabilityAssetRegistryMart.site_code == SITE_CODE,
            ReliabilityAssetRegistryMart.organization_code == ORGANIZATION_CODE,
        )
        asset_scope = (
            AssetMasterMart.site_code == SITE_CODE,
            AssetMasterMart.organization_code == ORGANIZATION_CODE,
        )
        maintenance_scope = (
            MaintenanceEventMart.site_code == SITE_CODE,
            MaintenanceEventMart.organization_code == ORGANIZATION_CODE,
        )
        overhaul_scope = (
            OverhaulEventMart.site_code == SITE_CODE,
            OverhaulEventMart.organization_code == ORGANIZATION_CODE,
        )
        maintenance_date = func.coalesce(MaintenanceEventMart.actual_start, MaintenanceEventMart.source_changed_at)
        overhaul_date = func.coalesce(OverhaulEventMart.source_updated_at, OverhaulEventMart.source_created_at)
        population_statement = select(
            select(func.count(ReliabilityAssetRegistryMart.asset_ref)).where(*registry_scope).scalar_subquery().label("registered_assets"),
            select(func.count(ReliabilityAssetRegistryMart.asset_ref)).join(
                AssetMasterMart,
                (ReliabilityAssetRegistryMart.asset_ref == AssetMasterMart.canonical_id)
                & (AssetMasterMart.site_code == SITE_CODE)
                & (AssetMasterMart.organization_code == ORGANIZATION_CODE),
            ).where(*registry_scope).scalar_subquery().label("registry_resolved"),
            select(func.count(AssetMasterMart.canonical_id)).where(*asset_scope).scalar_subquery().label("technical_asset_context"),
            select(func.count(MaintenanceEventMart.canonical_id)).where(*maintenance_scope).scalar_subquery().label("maintenance_total"),
            select(func.count(MaintenanceEventMart.canonical_id)).join(
                ReliabilityAssetRegistryMart,
                ReliabilityAssetRegistryMart.asset_ref == MaintenanceEventMart.equipment_id,
            ).where(
                *maintenance_scope,
                *registry_scope,
            ).scalar_subquery().label("registry_maintenance"),
            select(func.max(AssetMasterMart.source_updated_at)).join(
                ReliabilityAssetRegistryMart,
                ReliabilityAssetRegistryMart.asset_ref == AssetMasterMart.canonical_id,
            ).where(*asset_scope, *registry_scope).scalar_subquery().label("asset_latest"),
            select(func.max(maintenance_date)).join(
                ReliabilityAssetRegistryMart,
                ReliabilityAssetRegistryMart.asset_ref == MaintenanceEventMart.equipment_id,
            ).where(
                *maintenance_scope,
                *registry_scope,
                maintenance_date.is_not(None),
            ).scalar_subquery().label("maintenance_latest"),
            select(func.max(overhaul_date)).where(*overhaul_scope, overhaul_date.is_not(None)).scalar_subquery().label("overhaul_latest"),
        )
        with self.database.read_session() as session:
            population = session.execute(population_statement).one()._mapping

        fmea = self.fmea_overview(as_of=current)
        health = self.asset_health_overview(as_of=current)
        rcfa = self.rcfa_overview(as_of=current)
        overhaul = self.overhaul_overview()
        fmea_summary = fmea["summary"]
        health_summary = health["summary"]
        rcfa_summary = rcfa["summary"]
        overhaul_summary = overhaul["summary"]
        registered_assets = int(population["registered_assets"] or 0)
        registry_resolved = int(population["registry_resolved"] or 0)
        maintenance_total = int(population["maintenance_total"] or 0)
        registry_maintenance = int(population["registry_maintenance"] or 0)
        fmea_records = int(fmea_summary["fmea_records"] or 0)
        health_records = int(health_summary["assessment_records"] or 0)
        rcfa_records = int(rcfa_summary["rcfa_records"] or 0)
        overhaul_records = int(overhaul_summary["overhaul_records"] or 0)

        domains = [
            {
                "domain": "ASSET",
                "source_system": "MAXIMO",
                "source_object": "MXASSET / registry projection",
                "population_type": "BUSINESS_REGISTRY",
                "record_count": registered_assets,
                "business_scope": "Registered Reliability Assets",
                "relationship_state": "Registry → Asset Master verified",
                "latest_record_date": population["asset_latest"],
                "date_basis": "asset_master.source_updated_at",
                "known_limitation": "asset_master is broader technical context; the Registry remains the business boundary.",
                "evidence_class": "VERIFIED",
            },
            {
                "domain": "MAINTENANCE",
                "source_system": "MAXIMO",
                "source_object": "MXWODETAIL",
                "population_type": "LOCAL_COLLECTOR_PROJECTION",
                "record_count": maintenance_total,
                "scoped_record_count": registry_maintenance,
                "business_scope": "Registry-scoped Maintenance Events",
                "relationship_state": "Direct Registry scope verified",
                "latest_record_date": population["maintenance_latest"],
                "date_basis": "COALESCE(actual_start, source_changed_at)",
                "known_limitation": "Latest activity evidence is not a sync freshness or failure-rate measure.",
                "evidence_class": "VERIFIED",
            },
            {
                "domain": "FMEA",
                "source_system": "MAXIMO",
                "source_object": "IPFMEA",
                "population_type": "CONTROLLED_MART_POPULATION",
                "record_count": fmea_records,
                "registered_assets_represented": int(fmea_summary["registered_assets_represented"] or 0),
                "business_scope": "Current controlled FMEA population",
                "relationship_state": "Direct verified source relationship; resolution measured",
                "latest_record_date": fmea["record_recency"]["latest_record_at"],
                "date_basis": fmea["record_recency"]["date_basis"],
                "known_limitation": "IPFMEAITEM failure-mode details and RPN remain deferred.",
                "evidence_class": "VERIFIED",
            },
            {
                "domain": "ASSET_HEALTH",
                "source_system": "MAXIMO",
                "source_object": "IPBHM",
                "population_type": "CONTROLLED_MART_POPULATION",
                "record_count": health_records,
                "registered_assets_represented": int(health_summary["registered_assets_represented"] or 0),
                "business_scope": "Current controlled Asset Health assessment population",
                "relationship_state": "Direct verified Asset relationship; resolution measured",
                "latest_record_date": health["record_recency"]["latest_record_at"],
                "date_basis": health["record_recency"]["date_basis"],
                "known_limitation": "Assessment records are not a verified Health or Wellness Score.",
                "evidence_class": "VERIFIED",
            },
            {
                "domain": "RCFA",
                "source_system": "MAXIMO",
                "source_object": "IPRCFA",
                "population_type": "CONTROLLED_MART_POPULATION",
                "record_count": rcfa_records,
                "business_scope": "Global RCFA analysis records",
                "relationship_state": "Asset, Work Order, and Failure Event relationships unresolved",
                "latest_record_date": rcfa["record_recency"]["latest_record_at"],
                "date_basis": rcfa["record_recency"]["date_basis"],
                "known_limitation": "No Asset coverage, root-cause taxonomy, or completion KPI is claimed.",
                "evidence_class": "VERIFIED",
            },
            {
                "domain": "OVERHAUL",
                "source_system": "MAXIMO",
                "source_object": "IP_DOM_OH",
                "population_type": "CONTROLLED_MART_POPULATION",
                "record_count": overhaul_records,
                "business_scope": "Current controlled Overhaul population",
                "relationship_state": "Work Order direct verified; Asset derived through Work Order",
                "latest_record_date": population["overhaul_latest"],
                "date_basis": "COALESCE(source_updated_at, source_created_at)",
                "known_limitation": "Work Order Mart resolution and Asset resolution are measured separately; no execution KPI is claimed.",
                "evidence_class": "VERIFIED",
            },
        ]
        relationships = [
            {
                "relationship": "Registry → Asset Master",
                "evidence": "VERIFIED",
                "resolved_count": registry_resolved,
                "unresolved_count": max(registered_assets - registry_resolved, 0),
                "interpretation": "Business Asset Registry resolution; asset_master remains broader technical context.",
            },
            {
                "relationship": "Maintenance → Registered Asset",
                "evidence": "DIRECT_VERIFIED",
                "resolved_count": registry_maintenance,
                "interpretation": "The product Maintenance count is explicitly Registry-scoped.",
            },
            {
                "relationship": "FMEA → Asset",
                "evidence": "DIRECT_VERIFIED",
                "resolved_count": int(fmea_summary["registry_resolved"] or 0),
                "unresolved_count": int(fmea_summary["unresolved_asset_refs"] or 0),
                "technical_context_count": int(fmea_summary["technical_non_registry_records"] or 0),
                "interpretation": "Registered, technical, and unresolved references remain distinct.",
            },
            {
                "relationship": "Asset Health → Asset",
                "evidence": "DIRECT_VERIFIED",
                "resolved_count": int(health_summary["registry_resolved"] or 0),
                "unresolved_count": int(health_summary["unresolved_asset_refs"] or 0),
                "technical_context_count": int(health_summary["technical_non_registry_records"] or 0),
                "interpretation": "Registered, technical, and unresolved references remain distinct.",
            },
            {"relationship": "RCFA → Asset", "evidence": "UNRESOLVED", "interpretation": "No Asset join or coverage metric is exposed."},
            {"relationship": "RCFA → Work Order", "evidence": "UNRESOLVED", "interpretation": "No Work Order join is exposed."},
            {"relationship": "RCFA → Failure Event", "evidence": "UNRESOLVED", "interpretation": "RCFA is not treated as a failure event."},
            {
                "relationship": "Overhaul → Work Order",
                "evidence": "DIRECT_VERIFIED",
                "resolved_count": int(overhaul_summary["records_with_work_order"] or 0),
                "unresolved_count": int(overhaul_summary["work_order_source_missing"] or 0),
                "interpretation": "Source relationship is verified; local Mart resolution is separate.",
            },
            {
                "relationship": "Overhaul Work Order → local maintenance_event",
                "evidence": "RESOLUTION_MEASURED",
                "resolved_count": int(overhaul_summary["work_orders_resolved_in_mart"] or 0),
                "unresolved_count": int(overhaul_summary["work_orders_unresolved_in_mart"] or 0),
                "interpretation": "A source Work Order can be identified while its local Mart context is unavailable.",
            },
            {
                "relationship": "Overhaul → Asset",
                "evidence": "DERIVED_VERIFIED_PATH",
                "resolved_count": int(overhaul_summary["registered_assets_resolved"] or 0),
                "unresolved_count": int(overhaul_summary["asset_refs_unresolved"] or 0),
                "technical_context_count": int(overhaul_summary["technical_non_registry"] or 0),
                "interpretation": "Only an existing Work Order-derived asset_ref may resolve to a Registered Asset.",
            },
        ]
        readiness = [
            ("Registered Reliability Assets", "VERIFIED", "AVAILABLE", "Business Asset boundary is reliability_asset_registry."),
            ("Maintenance Activity", "DERIVED_SAFE", "AVAILABLE", "Registry-scoped event counts use factual activity dates."),
            ("Repeat Activity", "DERIVED_SAFE", "AVAILABLE", "Repeated events are descriptive activity, not repeated failure."),
            ("Activity Concentration", "DERIVED_SAFE", "AVAILABLE", "Event concentration is an investigation signal only."),
            ("FMEA Records", "VERIFIED", "AVAILABLE", "Current controlled IPFMEA records are available."),
            ("Asset Health Assessment Records", "VERIFIED", "AVAILABLE", "Current controlled IPBHM records are available."),
            ("RCFA Records", "VERIFIED", "AVAILABLE", "Global controlled RCFA records are available."),
            ("Overhaul Records", "VERIFIED", "AVAILABLE", "Current controlled Overhaul records are available."),
            ("Raw Source Status distributions", "DERIVED_SAFE", "AVAILABLE", "Statuses remain exactly source values."),
            ("Raw Work Type", "DERIVED_SAFE", "AVAILABLE", "Preferred source work type is preserved before canonical fallback."),
            ("Record Recency", "DERIVED_SAFE", "AVAILABLE", "Domain-specific latest source-record dates are factual only."),
            ("Repeat Failure", "BUSINESS_SEMANTICS_REQUIRED", "BLOCKED", "Failure identity, occurrence, qualifying statuses, and governed repeat rules are unavailable."),
            ("MTBF", "BUSINESS_SEMANTICS_REQUIRED", "BLOCKED", "Verified failure events and operating exposure are unavailable."),
            ("MTTR", "BUSINESS_SEMANTICS_REQUIRED", "BLOCKED", "Verified failure and repair-completion boundaries are unavailable."),
            ("Availability", "DATA_NOT_AVAILABLE", "NOT_AVAILABLE", "Operating-time and outage boundaries are not in the current model."),
            ("Health Score", "BUSINESS_SEMANTICS_REQUIRED", "BLOCKED", "No verified numerical source, normalization, or governance exists."),
            ("Wellness Score", "BUSINESS_SEMANTICS_REQUIRED", "BLOCKED", "The report clue is not verified as an IPBHM source or calculation."),
            ("Risk Score", "DATA_NOT_AVAILABLE", "NOT_AVAILABLE", "No verified risk inputs, formula, or thresholds exist."),
            ("Reliability Score", "DEFERRED", "DEFERRED", "Intentionally postponed until reliability semantics are governed."),
            ("Bad Actor", "DEFERRED", "DEFERRED", "Activity count is not a bad-actor rule."),
            ("FMEA RPN", "BUSINESS_SEMANTICS_REQUIRED", "BLOCKED", "Severity, Occurrence, Detectability, scales, and governance are unavailable."),
            ("Failure Mode analytics", "DATA_NOT_AVAILABLE", "NOT_AVAILABLE", "IPFMEAITEM remains outside the current controlled dataset."),
            ("RCFA Completion KPI", "BUSINESS_SEMANTICS_REQUIRED", "BLOCKED", "Completion status semantics and action evidence are unavailable."),
            ("RCFA Root Cause taxonomy", "BUSINESS_SEMANTICS_REQUIRED", "BLOCKED", "Category is a raw source value with unverified taxonomy."),
            ("Overhaul Schedule Variance", "BUSINESS_SEMANTICS_REQUIRED", "BLOCKED", "Planned/actual boundaries and completion rules are unverified."),
            ("Overhaul Completion KPI", "BUSINESS_SEMANTICS_REQUIRED", "BLOCKED", "Raw lifecycle status is not a verified completion mapping."),
            ("Overhaul Progress KPI", "BUSINESS_SEMANTICS_REQUIRED", "BLOCKED", "Progress scale and business meaning are unverified."),
            ("PdM alerts", "DATA_NOT_AVAILABLE", "NOT_AVAILABLE", "PI/DCS signals are not in the current NADI decision model."),
            ("Recommendations", "DEFERRED", "DEFERRED", "No governed action rules are implemented."),
        ]
        return {
            "scope": {
                "site_code": SITE_CODE,
                "organization_code": ORGANIZATION_CODE,
                "source_system": "MAXIMO",
                "registered_asset_boundary": "reliability_asset_registry",
                "sync_freshness": "NOT_AVAILABLE",
                "interpretation": "Trust dimensions are factual evidence, not a weighted score.",
            },
            "population": {
                "registered_reliability_assets": registered_assets,
                "registry_resolved": registry_resolved,
                "registry_unresolved": max(registered_assets - registry_resolved, 0),
                "technical_asset_context": int(population["technical_asset_context"] or 0),
                "maintenance_total": maintenance_total,
                "registry_maintenance": registry_maintenance,
                "fmea": fmea_records,
                "asset_health": health_records,
                "rcfa": rcfa_records,
                "overhaul": overhaul_records,
            },
            "domains": domains,
            "relationships": relationships,
            "semantic_readiness": [
                {"capability": capability, "evidence_class": evidence_class, "status": status, "reason": reason}
                for capability, evidence_class, status, reason in readiness
            ],
            "integrity": self.integrity_summary(),
            "limitations": [
                "Latest available record dates are not sync freshness or SLA measurements.",
                "Controlled Mart populations are bounded evidence, not complete historical claims.",
                "PI/DCS/CEMS integrations are deferred from the current NADI decision model.",
                "A capability marked blocked is intentionally withheld because its business semantics or required source evidence are not yet verified. It does not mean the source system is defective.",
            ],
        }

    def decision_overview(
        self,
        *,
        window_days: int = 30,
        as_of: datetime | None = None,
    ) -> dict[str, object]:
        """Return bounded, read-only aggregates for the NADI decision surface.

        The method deliberately keeps all maintenance metrics on the Registry
        join.  It never selects maintenance rows into Python; only grouped and
        scalar aggregate results cross the Mart boundary.
        """
        if window_days not in {7, 30, 90}:
            raise ValueError("window_days must be one of 7, 30, or 90")
        current = as_of or datetime.now(timezone.utc)
        if current.tzinfo is None:
            current = current.replace(tzinfo=timezone.utc)
        window_start = current - timedelta(days=window_days)
        date_column = func.coalesce(MaintenanceEventMart.actual_start, MaintenanceEventMart.source_changed_at)
        maintenance_scope = (
            select(MaintenanceEventMart)
            .join(ReliabilityAssetRegistryMart, ReliabilityAssetRegistryMart.asset_ref == MaintenanceEventMart.equipment_id)
            .where(
                MaintenanceEventMart.site_code == SITE_CODE,
                MaintenanceEventMart.organization_code == ORGANIZATION_CODE,
                ReliabilityAssetRegistryMart.site_code == SITE_CODE,
                ReliabilityAssetRegistryMart.organization_code == ORGANIZATION_CODE,
            )
        ).subquery()
        scoped_date = func.coalesce(maintenance_scope.c.actual_start, maintenance_scope.c.source_changed_at)

        week_start = datetime(current.year, current.month, current.day, tzinfo=current.tzinfo) - timedelta(days=current.weekday())
        trend_starts = [week_start - timedelta(weeks=offset) for offset in range(11, -1, -1)]
        trend_counts = [
            func.count(maintenance_scope.c.canonical_id).filter(
                scoped_date >= start,
                scoped_date < start + timedelta(weeks=1),
            ).label(f"week_{index}")
            for index, start in enumerate(trend_starts)
        ]

        summary_statement = select(
            func.count(maintenance_scope.c.canonical_id).filter(scoped_date >= current - timedelta(days=7), scoped_date <= current).label("maintenance_7d"),
            func.count(maintenance_scope.c.canonical_id).filter(scoped_date >= current - timedelta(days=30), scoped_date <= current).label("maintenance_30d"),
            func.count(maintenance_scope.c.canonical_id).filter(scoped_date >= current - timedelta(days=90), scoped_date <= current).label("maintenance_90d"),
            func.count(func.distinct(maintenance_scope.c.equipment_id)).filter(scoped_date >= current - timedelta(days=7), scoped_date <= current).label("assets_active_7d"),
            func.count(func.distinct(maintenance_scope.c.equipment_id)).filter(scoped_date >= current - timedelta(days=30), scoped_date <= current).label("assets_active_30d"),
            func.count(func.distinct(maintenance_scope.c.equipment_id)).filter(scoped_date >= current - timedelta(days=90), scoped_date <= current).label("assets_active_90d"),
        )
        status_value = func.coalesce(maintenance_scope.c.status, "UNKNOWN")
        raw_work_type = _raw_work_type(maintenance_scope.c.sources)
        canonical_work_type = func.nullif(func.trim(maintenance_scope.c.event_type), "")
        work_type_value = func.coalesce(raw_work_type, canonical_work_type, "UNKNOWN")
        window_statement = select(
            status_value.label("value"),
            func.count(maintenance_scope.c.canonical_id).label("count"),
        ).where(scoped_date >= window_start, scoped_date <= current).group_by(status_value).order_by(status_value)
        work_type_statement = select(
            work_type_value.label("value"),
            func.count(maintenance_scope.c.canonical_id).label("count"),
        ).where(scoped_date >= window_start, scoped_date <= current).group_by(work_type_value).order_by(work_type_value)
        concentration_count = func.count(maintenance_scope.c.canonical_id).label("event_count")
        concentration_latest = func.max(scoped_date).label("latest_activity")
        concentration_statement = (
            select(
                ReliabilityAssetRegistryMart.asset_ref,
                ReliabilityAssetRegistryMart.source_asset_number,
                AssetMasterMart.description,
                concentration_count,
                concentration_latest,
            )
            .select_from(maintenance_scope)
            .join(ReliabilityAssetRegistryMart, ReliabilityAssetRegistryMart.asset_ref == maintenance_scope.c.equipment_id)
            .outerjoin(AssetMasterMart, AssetMasterMart.canonical_id == maintenance_scope.c.equipment_id)
            .where(scoped_date >= window_start, scoped_date <= current)
            .group_by(
                ReliabilityAssetRegistryMart.asset_ref,
                ReliabilityAssetRegistryMart.source_asset_number,
                AssetMasterMart.description,
            )
            .order_by(desc(concentration_count), desc(concentration_latest), asc(ReliabilityAssetRegistryMart.source_asset_number), asc(ReliabilityAssetRegistryMart.asset_ref))
            .limit(10)
        )
        trend_statement = select(*trend_counts)

        records_statement = select(
            select(func.count(FmeaAssessmentMart.canonical_id)).where(
                FmeaAssessmentMart.site_code == SITE_CODE,
                FmeaAssessmentMart.organization_code == ORGANIZATION_CODE,
            ).scalar_subquery().label("fmea_records"),
            select(func.count(func.distinct(FmeaAssessmentMart.asset_ref))).select_from(FmeaAssessmentMart).join(
                ReliabilityAssetRegistryMart, ReliabilityAssetRegistryMart.asset_ref == FmeaAssessmentMart.asset_ref
            ).where(
                FmeaAssessmentMart.site_code == SITE_CODE,
                FmeaAssessmentMart.organization_code == ORGANIZATION_CODE,
                FmeaAssessmentMart.asset_ref.is_not(None),
                ReliabilityAssetRegistryMart.site_code == SITE_CODE,
                ReliabilityAssetRegistryMart.organization_code == ORGANIZATION_CODE,
            ).scalar_subquery().label("fmea_assets_represented"),
            select(func.count(AssetHealthAssessmentMart.canonical_id)).where(
                AssetHealthAssessmentMart.site_code == SITE_CODE,
                AssetHealthAssessmentMart.organization_code == ORGANIZATION_CODE,
            ).scalar_subquery().label("asset_health_records"),
            select(func.count(func.distinct(AssetHealthAssessmentMart.asset_ref))).select_from(AssetHealthAssessmentMart).join(
                ReliabilityAssetRegistryMart, ReliabilityAssetRegistryMart.asset_ref == AssetHealthAssessmentMart.asset_ref
            ).where(
                AssetHealthAssessmentMart.site_code == SITE_CODE,
                AssetHealthAssessmentMart.organization_code == ORGANIZATION_CODE,
                AssetHealthAssessmentMart.asset_ref.is_not(None),
                ReliabilityAssetRegistryMart.site_code == SITE_CODE,
                ReliabilityAssetRegistryMart.organization_code == ORGANIZATION_CODE,
            ).scalar_subquery().label("asset_health_assets_represented"),
            select(func.count(RcfaAnalysisMart.canonical_id)).where(
                RcfaAnalysisMart.site_code == SITE_CODE,
                RcfaAnalysisMart.organization_code == ORGANIZATION_CODE,
            ).scalar_subquery().label("rcfa_records"),
            select(func.count(OverhaulEventMart.canonical_id)).where(
                OverhaulEventMart.site_code == SITE_CODE,
                OverhaulEventMart.organization_code == ORGANIZATION_CODE,
            ).scalar_subquery().label("overhaul_records"),
        )
        registry_statement = select(func.count(ReliabilityAssetRegistryMart.asset_ref)).where(
            ReliabilityAssetRegistryMart.site_code == SITE_CODE,
            ReliabilityAssetRegistryMart.organization_code == ORGANIZATION_CODE,
        )

        with self.database.read_session() as session:
            summary = session.execute(summary_statement).one()
            trend = session.execute(trend_statement).one()
            statuses = session.execute(window_statement).all()
            work_types = session.execute(work_type_statement).all()
            concentration = session.execute(concentration_statement).all()
            records = session.execute(records_statement).one()
            registered_assets = int(session.scalar(registry_statement) or 0)

        integrity = self.integrity_summary()
        summary_values = summary._mapping
        trend_values = trend._mapping
        record_values = records._mapping
        return {
            "registered_assets": registered_assets,
            "summary": {
                "maintenance_activity_7d": int(summary_values["maintenance_7d"] or 0),
                "maintenance_activity_30d": int(summary_values["maintenance_30d"] or 0),
                "maintenance_activity_90d": int(summary_values["maintenance_90d"] or 0),
                "assets_active_7d": int(summary_values["assets_active_7d"] or 0),
                "assets_active_30d": int(summary_values["assets_active_30d"] or 0),
                "assets_active_90d": int(summary_values["assets_active_90d"] or 0),
            },
            "trend": [
                {"period_start": start, "period_end": start + timedelta(weeks=1), "event_count": int(trend_values[f"week_{index}"] or 0)}
                for index, start in enumerate(trend_starts)
            ],
            "status_distribution": [{"value": row.value, "count": int(row.count)} for row in statuses],
            "work_type_distribution": [{"value": row.value, "count": int(row.count)} for row in work_types],
            "activity_concentration": [
                {
                    "asset_ref": row.asset_ref,
                    "source_asset_number": row.source_asset_number,
                    "description": row.description,
                    "event_count": int(row.event_count),
                    "latest_activity": row.latest_activity,
                }
                for row in concentration
            ],
            "records": {key: int(record_values[key] or 0) for key in record_values.keys()},
            "integrity": integrity,
            "window_start": window_start,
            "as_of": current,
        }

    def overhaul_overview(self) -> dict[str, object]:
        """Return aggregate-only evidence for the controlled Overhaul population."""

        scoped = (
            OverhaulEventMart.site_code == SITE_CODE,
            OverhaulEventMart.organization_code == ORGANIZATION_CODE,
        )
        maintenance_work_orders = select(MaintenanceEventMart.work_order_id).where(
            MaintenanceEventMart.site_code == SITE_CODE,
            MaintenanceEventMart.organization_code == ORGANIZATION_CODE,
            MaintenanceEventMart.work_order_id.is_not(None),
        )
        asset_master_refs = select(AssetMasterMart.canonical_id).where(
            AssetMasterMart.site_code == SITE_CODE,
            AssetMasterMart.organization_code == ORGANIZATION_CODE,
        )
        registry_refs = select(ReliabilityAssetRegistryMart.asset_ref).where(
            ReliabilityAssetRegistryMart.site_code == SITE_CODE,
            ReliabilityAssetRegistryMart.organization_code == ORGANIZATION_CODE,
        )
        source_work_order = _raw_work_order_number(OverhaulEventMart.sources)
        inspection_number = func.nullif(func.trim(OverhaulEventMart.unresolved_source_attributes["inspection_number"].as_string()), "")
        performance_test = func.nullif(func.trim(OverhaulEventMart.unresolved_source_attributes["performance_test"].as_string()), "")
        summary_statement = select(
            select(func.count(OverhaulEventMart.canonical_id)).where(*scoped).scalar_subquery().label("overhaul_records"),
            select(func.count(OverhaulEventMart.source_record_id)).where(*scoped).scalar_subquery().label("source_record_id_present"),
            select(func.count(OverhaulEventMart.source_number)).where(*scoped).scalar_subquery().label("source_number_present"),
            select(func.count(OverhaulEventMart.workorder_ref)).where(*scoped).scalar_subquery().label("records_with_work_order"),
            select(func.count(OverhaulEventMart.workorder_ref).filter(OverhaulEventMart.workorder_ref.in_(maintenance_work_orders))).where(*scoped).scalar_subquery().label("work_orders_resolved_in_mart"),
            select(func.count(source_work_order)).where(*scoped).scalar_subquery().label("source_work_order_number_available"),
            select(func.count(OverhaulEventMart.asset_ref)).where(*scoped).scalar_subquery().label("records_with_asset"),
            select(func.count(OverhaulEventMart.asset_ref).filter(OverhaulEventMart.asset_ref.in_(asset_master_refs))).where(*scoped).scalar_subquery().label("asset_master_resolved"),
            select(func.count(OverhaulEventMart.asset_ref).filter(OverhaulEventMart.asset_ref.in_(registry_refs))).where(*scoped).scalar_subquery().label("registered_assets_resolved"),
            select(func.count(OverhaulEventMart.asset_ref).filter(OverhaulEventMart.asset_ref.in_(asset_master_refs), OverhaulEventMart.asset_ref.not_in(registry_refs))).where(*scoped).scalar_subquery().label("technical_non_registry"),
            select(func.count(OverhaulEventMart.planned_start_at)).where(*scoped).scalar_subquery().label("planned_start_present"),
            select(func.count(OverhaulEventMart.planned_finish_at)).where(*scoped).scalar_subquery().label("planned_finish_present"),
            select(func.count(OverhaulEventMart.actual_start_at)).where(*scoped).scalar_subquery().label("actual_start_present"),
            select(func.count(OverhaulEventMart.actual_finish_at)).where(*scoped).scalar_subquery().label("actual_finish_present"),
            select(func.count(OverhaulEventMart.planned_start_at).filter(OverhaulEventMart.planned_finish_at.is_not(None))).where(*scoped).scalar_subquery().label("planned_duration_available"),
            select(func.count(OverhaulEventMart.actual_start_at).filter(OverhaulEventMart.actual_finish_at.is_not(None))).where(*scoped).scalar_subquery().label("actual_duration_available"),
            select(func.count(func.nullif(cast(OverhaulEventMart.progress, String), "null"))).where(*scoped).scalar_subquery().label("records_with_progress"),
            select(func.count(inspection_number)).where(*scoped).scalar_subquery().label("inspection_number_present"),
            select(func.count(performance_test)).where(*scoped).scalar_subquery().label("performance_test_present"),
        )
        status_statement = select(
            func.coalesce(OverhaulEventMart.lifecycle_status, "UNKNOWN").label("value"),
            func.count(OverhaulEventMart.canonical_id).label("count"),
        ).where(*scoped).group_by(OverhaulEventMart.lifecycle_status).order_by(asc(OverhaulEventMart.lifecycle_status))
        with self.database.read_session() as session:
            summary = session.execute(summary_statement).one()._mapping
            statuses = session.execute(status_statement).all()

        values = {key: int(value or 0) for key, value in summary.items()}
        values["work_orders_unresolved_in_mart"] = values["records_with_work_order"] - values["work_orders_resolved_in_mart"]
        values["work_order_source_missing"] = values["overhaul_records"] - values["records_with_work_order"]
        values["asset_ref_absent"] = values["overhaul_records"] - values["records_with_asset"]
        values["asset_refs_unresolved"] = values["overhaul_records"] - values["asset_master_resolved"]
        values["technical_non_registry"] = max(values["technical_non_registry"], 0)
        return {
            "scope": {
                "site_code": SITE_CODE,
                "organization_code": ORGANIZATION_CODE,
                "population": "CONTROLLED_MART_POPULATION",
                "workorder_relationship": "DIRECT_VERIFIED",
                "asset_relationship": "DERIVED_VIA_WORK_ORDER",
                "interpretation": "OVERHAUL_RECORDS_NOT_PERFORMANCE_SCORE",
            },
            "summary": values,
            "status_distribution": [{"value": row.value, "count": int(row.count)} for row in statuses],
            "date_availability": {
                "planned_start_present": values["planned_start_present"],
                "planned_finish_present": values["planned_finish_present"],
                "actual_start_present": values["actual_start_present"],
                "actual_finish_present": values["actual_finish_present"],
                "planned_duration_available": values["planned_duration_available"],
                "actual_duration_available": values["actual_duration_available"],
            },
            "relationship_integrity": {
                "workorder_refs_present": values["records_with_work_order"],
                "workorder_refs_resolved_in_mart": values["work_orders_resolved_in_mart"],
                "workorder_refs_unresolved_in_mart": values["work_orders_unresolved_in_mart"],
                "workorder_source_missing": values["work_order_source_missing"],
                "asset_refs_present": values["records_with_asset"],
                "asset_refs_resolved_to_asset_master": values["asset_master_resolved"],
                "registered_assets_resolved": values["registered_assets_resolved"],
                "technical_non_registry": values["technical_non_registry"],
                "asset_refs_unresolved": values["asset_refs_unresolved"],
            },
            "evidence": {
                "overhaul_records": "VERIFIED",
                "overhaul_number": "VERIFIED",
                "workorder_source_relationship": "VERIFIED",
                "workorder_mart_resolution": "VERIFIED",
                "asset_derived_relationship": "VERIFIED",
                "lifecycle_status": "VERIFIED",
                "planned_duration": "DERIVED_SAFE",
                "actual_duration": "DERIVED_SAFE",
                "progress_value": "VERIFIED",
                "progress_scale": "BUSINESS_SEMANTICS_REQUIRED",
                "schedule_variance": "BUSINESS_SEMANTICS_REQUIRED",
                "overhaul_completion": "BUSINESS_SEMANTICS_REQUIRED",
                "inspection_number": "VERIFIED",
                "inspection_relationship": "DATA_NOT_AVAILABLE",
                "performance_test": "VERIFIED",
                "performance_test_semantics": "BUSINESS_SEMANTICS_REQUIRED",
            },
        }

    def rcfa_overview(self, *, as_of: datetime | None = None) -> dict[str, object]:
        """Return global aggregate-only evidence for the controlled RCFA population."""

        current = as_of or datetime.now(timezone.utc)
        if current.tzinfo is None:
            current = current.replace(tzinfo=timezone.utc)
        record_date = _rcfa_record_date(RcfaAnalysisMart)
        summary_statement = select(
            select(func.count(RcfaAnalysisMart.canonical_id)).where(
                RcfaAnalysisMart.site_code == SITE_CODE,
                RcfaAnalysisMart.organization_code == ORGANIZATION_CODE,
            ).scalar_subquery().label("rcfa_records"),
            select(func.count(RcfaAnalysisMart.category)).where(
                RcfaAnalysisMart.site_code == SITE_CODE,
                RcfaAnalysisMart.organization_code == ORGANIZATION_CODE,
            ).scalar_subquery().label("records_with_category"),
            select(func.count(RcfaAnalysisMart.revision)).where(
                RcfaAnalysisMart.site_code == SITE_CODE,
                RcfaAnalysisMart.organization_code == ORGANIZATION_CODE,
            ).scalar_subquery().label("records_with_revision"),
            select(func.count(RcfaAnalysisMart.requested_at)).where(
                RcfaAnalysisMart.site_code == SITE_CODE,
                RcfaAnalysisMart.organization_code == ORGANIZATION_CODE,
            ).scalar_subquery().label("records_with_requested_at"),
            select(func.count(RcfaAnalysisMart.source_created_at)).where(
                RcfaAnalysisMart.site_code == SITE_CODE,
                RcfaAnalysisMart.organization_code == ORGANIZATION_CODE,
            ).scalar_subquery().label("records_with_source_created_at"),
            select(func.count(record_date)).where(
                RcfaAnalysisMart.site_code == SITE_CODE,
                RcfaAnalysisMart.organization_code == ORGANIZATION_CODE,
            ).scalar_subquery().label("record_date_available"),
            select(func.min(record_date)).where(
                RcfaAnalysisMart.site_code == SITE_CODE,
                RcfaAnalysisMart.organization_code == ORGANIZATION_CODE,
            ).scalar_subquery().label("oldest_record_at"),
            select(func.max(record_date)).where(
                RcfaAnalysisMart.site_code == SITE_CODE,
                RcfaAnalysisMart.organization_code == ORGANIZATION_CODE,
            ).scalar_subquery().label("latest_record_at"),
        )
        status_statement = select(
            func.coalesce(RcfaAnalysisMart.lifecycle_status, "UNKNOWN").label("value"),
            func.count(RcfaAnalysisMart.canonical_id).label("count"),
        ).where(
            RcfaAnalysisMart.site_code == SITE_CODE,
            RcfaAnalysisMart.organization_code == ORGANIZATION_CODE,
        ).group_by(RcfaAnalysisMart.lifecycle_status).order_by(asc(RcfaAnalysisMart.lifecycle_status))
        category_statement = select(
            func.coalesce(RcfaAnalysisMart.category, "UNKNOWN").label("value"),
            func.count(RcfaAnalysisMart.canonical_id).label("count"),
        ).where(
            RcfaAnalysisMart.site_code == SITE_CODE,
            RcfaAnalysisMart.organization_code == ORGANIZATION_CODE,
        ).group_by(RcfaAnalysisMart.category).order_by(asc(RcfaAnalysisMart.category))
        revision_statement = select(
            func.coalesce(RcfaAnalysisMart.revision, "UNKNOWN").label("value"),
            func.count(RcfaAnalysisMart.canonical_id).label("count"),
        ).where(
            RcfaAnalysisMart.site_code == SITE_CODE,
            RcfaAnalysisMart.organization_code == ORGANIZATION_CODE,
        ).group_by(RcfaAnalysisMart.revision).order_by(asc(RcfaAnalysisMart.revision))
        with self.database.read_session() as session:
            summary = session.execute(summary_statement).one()._mapping
            statuses = session.execute(status_statement).all()
            categories = session.execute(category_statement).all()
            revisions = session.execute(revision_statement).all()
        latest = summary["latest_record_at"]
        latest_age_days = None
        if latest is not None:
            if latest.tzinfo is None:
                latest = latest.replace(tzinfo=timezone.utc)
            latest_age_days = (current - latest).total_seconds() / 86400.0
        return {
            "scope": {
                "site_code": SITE_CODE,
                "organization_code": ORGANIZATION_CODE,
                "population": "CONTROLLED_MART_POPULATION",
                "asset_relationship": "UNRESOLVED",
                "workorder_relationship": "UNRESOLVED",
                "failure_event_relationship": "UNRESOLVED",
                "interpretation": "GLOBAL_RCFA_RECORDS",
            },
            "summary": {key: int(summary[key] or 0) for key in (
                "rcfa_records", "records_with_category", "records_with_revision", "records_with_requested_at",
                "records_with_source_created_at", "record_date_available",
            )},
            "status_distribution": [{"value": row.value, "count": int(row.count)} for row in statuses],
            "category_distribution": [{"value": row.value, "count": int(row.count)} for row in categories],
            "revision_distribution": [{"value": row.value, "count": int(row.count)} for row in revisions],
            "record_recency": {
                "oldest_record_at": summary["oldest_record_at"],
                "latest_record_at": latest,
                "as_of": current,
                "latest_rcfa_age_days": latest_age_days,
                "date_basis": "requested_at (source_created_at unavailable in current population)",
            },
            "evidence": {
                "rcfa_records": "VERIFIED",
                "rcfa_number": "VERIFIED",
                "revision": "VERIFIED",
                "lifecycle_status": "VERIFIED",
                "category": "VERIFIED",
                "rcfa_record_age": "DERIVED_SAFE",
                "request_to_created_gap": "DATA_NOT_AVAILABLE",
                "category_taxonomy": "BUSINESS_SEMANTICS_REQUIRED",
                "asset_relationship": "DATA_NOT_AVAILABLE",
                "workorder_relationship": "DATA_NOT_AVAILABLE",
                "failure_event_relationship": "DATA_NOT_AVAILABLE",
                "root_cause_details": "DATA_NOT_AVAILABLE",
                "root_cause_taxonomy": "BUSINESS_SEMANTICS_REQUIRED",
                "rcfa_completion": "BUSINESS_SEMANTICS_REQUIRED",
            },
        }

    def fmea_overview(self, *, as_of: datetime | None = None) -> dict[str, object]:
        """Return aggregate-only evidence for the controlled FMEA population."""

        current = as_of or datetime.now(timezone.utc)
        if current.tzinfo is None:
            current = current.replace(tzinfo=timezone.utc)
        record_date = _fmea_record_date(FmeaAssessmentMart)
        raw_failure_code = _raw_failure_code(FmeaAssessmentMart.sources)
        relation = (
            select(
                FmeaAssessmentMart.canonical_id.label("record_id"),
                FmeaAssessmentMart.asset_ref,
                ReliabilityAssetRegistryMart.asset_ref.label("registered_ref"),
                AssetMasterMart.canonical_id.label("asset_master_ref"),
            )
            .select_from(FmeaAssessmentMart)
            .outerjoin(
                ReliabilityAssetRegistryMart,
                (ReliabilityAssetRegistryMart.asset_ref == FmeaAssessmentMart.asset_ref)
                & (ReliabilityAssetRegistryMart.site_code == SITE_CODE)
                & (ReliabilityAssetRegistryMart.organization_code == ORGANIZATION_CODE),
            )
            .outerjoin(
                AssetMasterMart,
                (AssetMasterMart.canonical_id == FmeaAssessmentMart.asset_ref)
                & (AssetMasterMart.site_code == SITE_CODE)
                & (AssetMasterMart.organization_code == ORGANIZATION_CODE),
            )
            .where(
                FmeaAssessmentMart.site_code == SITE_CODE,
                FmeaAssessmentMart.organization_code == ORGANIZATION_CODE,
            )
            .subquery()
        )
        registered_groups = (
            select(
                FmeaAssessmentMart.asset_ref,
                func.count(FmeaAssessmentMart.canonical_id).label("record_count"),
            )
            .join(ReliabilityAssetRegistryMart, ReliabilityAssetRegistryMart.asset_ref == FmeaAssessmentMart.asset_ref)
            .where(
                FmeaAssessmentMart.site_code == SITE_CODE,
                FmeaAssessmentMart.organization_code == ORGANIZATION_CODE,
                ReliabilityAssetRegistryMart.site_code == SITE_CODE,
                ReliabilityAssetRegistryMart.organization_code == ORGANIZATION_CODE,
            )
            .group_by(FmeaAssessmentMart.asset_ref)
            .subquery()
        )
        summary_statement = select(
            select(func.count(FmeaAssessmentMart.canonical_id)).where(
                FmeaAssessmentMart.site_code == SITE_CODE,
                FmeaAssessmentMart.organization_code == ORGANIZATION_CODE,
            ).scalar_subquery().label("fmea_records"),
            select(func.count()).select_from(relation).where(relation.c.asset_ref.is_not(None)).scalar_subquery().label("records_with_asset_ref"),
            select(func.count()).select_from(relation).where(relation.c.asset_ref.is_(None)).scalar_subquery().label("records_without_asset_ref"),
            select(func.count()).select_from(relation).where(relation.c.asset_master_ref.is_not(None)).scalar_subquery().label("asset_master_resolved"),
            select(func.count()).select_from(relation).where(relation.c.registered_ref.is_not(None)).scalar_subquery().label("registry_resolved"),
            select(func.count()).select_from(relation).where(relation.c.asset_ref.is_not(None), relation.c.asset_master_ref.is_not(None), relation.c.registered_ref.is_(None)).scalar_subquery().label("technical_non_registry_records"),
            select(func.count()).select_from(relation).where(relation.c.asset_ref.is_not(None), relation.c.asset_master_ref.is_(None)).scalar_subquery().label("unresolved_asset_refs"),
            select(func.count(func.distinct(relation.c.registered_ref))).select_from(relation).scalar_subquery().label("registered_assets_represented"),
            select(func.count()).select_from(registered_groups).where(registered_groups.c.record_count >= 2).scalar_subquery().label("assets_with_multiple_records"),
            select(func.max(registered_groups.c.record_count)).select_from(registered_groups).scalar_subquery().label("maximum_records_per_asset"),
            select(func.count(raw_failure_code)).where(
                FmeaAssessmentMart.site_code == SITE_CODE,
                FmeaAssessmentMart.organization_code == ORGANIZATION_CODE,
            ).scalar_subquery().label("records_with_failure_code"),
            select(func.count(record_date)).where(
                FmeaAssessmentMart.site_code == SITE_CODE,
                FmeaAssessmentMart.organization_code == ORGANIZATION_CODE,
            ).scalar_subquery().label("record_date_available"),
            select(func.min(record_date)).where(
                FmeaAssessmentMart.site_code == SITE_CODE,
                FmeaAssessmentMart.organization_code == ORGANIZATION_CODE,
            ).scalar_subquery().label("oldest_record_at"),
            select(func.max(record_date)).where(
                FmeaAssessmentMart.site_code == SITE_CODE,
                FmeaAssessmentMart.organization_code == ORGANIZATION_CODE,
            ).scalar_subquery().label("latest_record_at"),
        )
        status_statement = select(
            func.coalesce(FmeaAssessmentMart.lifecycle_status, "UNKNOWN").label("value"),
            func.count(FmeaAssessmentMart.canonical_id).label("count"),
        ).where(
            FmeaAssessmentMart.site_code == SITE_CODE,
            FmeaAssessmentMart.organization_code == ORGANIZATION_CODE,
        ).group_by(FmeaAssessmentMart.lifecycle_status).order_by(asc(FmeaAssessmentMart.lifecycle_status))
        revision_statement = select(
            func.coalesce(FmeaAssessmentMart.revision, "UNKNOWN").label("value"),
            func.count(FmeaAssessmentMart.canonical_id).label("count"),
        ).where(
            FmeaAssessmentMart.site_code == SITE_CODE,
            FmeaAssessmentMart.organization_code == ORGANIZATION_CODE,
        ).group_by(FmeaAssessmentMart.revision).order_by(asc(FmeaAssessmentMart.revision))
        with self.database.read_session() as session:
            summary = session.execute(summary_statement).one()._mapping
            statuses = session.execute(status_statement).all()
            revisions = session.execute(revision_statement).all()
        latest = summary["latest_record_at"]
        latest_age_days = None
        if latest is not None:
            if latest.tzinfo is None:
                latest = latest.replace(tzinfo=timezone.utc)
            latest_age_days = (current - latest).total_seconds() / 86400.0
        return {
            "scope": {
                "site_code": SITE_CODE,
                "organization_code": ORGANIZATION_CODE,
                "registry_scope": "reliability_asset_registry",
                "population": "CONTROLLED_MART_POPULATION",
                "interpretation": "ASSESSMENT_RECORDS_NOT_RISK_SCORE",
            },
            "summary": {key: int(summary[key] or 0) for key in (
                "fmea_records", "records_with_asset_ref", "records_without_asset_ref", "asset_master_resolved",
                "registry_resolved", "technical_non_registry_records", "unresolved_asset_refs",
                "registered_assets_represented", "assets_with_multiple_records", "maximum_records_per_asset",
                "records_with_failure_code", "record_date_available",
            )},
            "status_distribution": [{"value": row.value, "count": int(row.count)} for row in statuses],
            "revision_distribution": [{"value": row.value, "count": int(row.count)} for row in revisions],
            "record_recency": {
                "oldest_record_at": summary["oldest_record_at"],
                "latest_record_at": latest,
                "as_of": current,
                "latest_fmea_age_days": latest_age_days,
                "date_basis": "COALESCE(status_changed_at, source_updated_at)",
            },
            "evidence": {
                "fmea_records": "VERIFIED",
                "registered_assets_represented": "DERIVED_SAFE",
                "assets_with_multiple_records": "DERIVED_SAFE",
                "records_with_failure_code": "VERIFIED",
                "fmea_record_age": "DERIVED_SAFE",
                "lifecycle_status": "VERIFIED",
                "revision": "VERIFIED",
                "failure_mode_details": "DATA_NOT_AVAILABLE",
                "rpn": "BUSINESS_SEMANTICS_REQUIRED",
                "risk_classification": "BUSINESS_SEMANTICS_REQUIRED",
            },
        }

    def asset_health_overview(self, *, as_of: datetime | None = None) -> dict[str, object]:
        """Return aggregate-only evidence for the controlled Asset Health population."""

        current = as_of or datetime.now(timezone.utc)
        if current.tzinfo is None:
            current = current.replace(tzinfo=timezone.utc)
        record_date = _assessment_date(AssetHealthAssessmentMart)
        relation = (
            select(
                AssetHealthAssessmentMart.canonical_id.label("record_id"),
                AssetHealthAssessmentMart.asset_ref,
                ReliabilityAssetRegistryMart.asset_ref.label("registered_ref"),
                AssetMasterMart.canonical_id.label("asset_master_ref"),
            )
            .select_from(AssetHealthAssessmentMart)
            .outerjoin(
                ReliabilityAssetRegistryMart,
                (ReliabilityAssetRegistryMart.asset_ref == AssetHealthAssessmentMart.asset_ref)
                & (ReliabilityAssetRegistryMart.site_code == SITE_CODE)
                & (ReliabilityAssetRegistryMart.organization_code == ORGANIZATION_CODE),
            )
            .outerjoin(
                AssetMasterMart,
                (AssetMasterMart.canonical_id == AssetHealthAssessmentMart.asset_ref)
                & (AssetMasterMart.site_code == SITE_CODE)
                & (AssetMasterMart.organization_code == ORGANIZATION_CODE),
            )
            .where(
                AssetHealthAssessmentMart.site_code == SITE_CODE,
                AssetHealthAssessmentMart.organization_code == ORGANIZATION_CODE,
            )
            .subquery()
        )
        registered_groups = (
            select(
                AssetHealthAssessmentMart.asset_ref,
                func.count(AssetHealthAssessmentMart.canonical_id).label("record_count"),
            )
            .join(ReliabilityAssetRegistryMart, ReliabilityAssetRegistryMart.asset_ref == AssetHealthAssessmentMart.asset_ref)
            .where(
                AssetHealthAssessmentMart.site_code == SITE_CODE,
                AssetHealthAssessmentMart.organization_code == ORGANIZATION_CODE,
                ReliabilityAssetRegistryMart.site_code == SITE_CODE,
                ReliabilityAssetRegistryMart.organization_code == ORGANIZATION_CODE,
            )
            .group_by(AssetHealthAssessmentMart.asset_ref)
            .subquery()
        )
        summary_statement = select(
            select(func.count(AssetHealthAssessmentMart.canonical_id)).where(
                AssetHealthAssessmentMart.site_code == SITE_CODE,
                AssetHealthAssessmentMart.organization_code == ORGANIZATION_CODE,
            ).scalar_subquery().label("assessment_records"),
            select(func.count()).select_from(relation).where(relation.c.asset_ref.is_not(None)).scalar_subquery().label("records_with_asset_ref"),
            select(func.count()).select_from(relation).where(relation.c.asset_ref.is_(None)).scalar_subquery().label("records_without_asset_ref"),
            select(func.count()).select_from(relation).where(relation.c.asset_master_ref.is_not(None)).scalar_subquery().label("asset_master_resolved"),
            select(func.count()).select_from(relation).where(relation.c.registered_ref.is_not(None)).scalar_subquery().label("registry_resolved"),
            select(func.count()).select_from(relation).where(relation.c.asset_ref.is_not(None), relation.c.asset_master_ref.is_not(None), relation.c.registered_ref.is_(None)).scalar_subquery().label("technical_non_registry_records"),
            select(func.count()).select_from(relation).where(relation.c.asset_ref.is_not(None), relation.c.asset_master_ref.is_(None)).scalar_subquery().label("unresolved_asset_refs"),
            select(func.count(func.distinct(relation.c.registered_ref))).select_from(relation).scalar_subquery().label("registered_assets_represented"),
            select(func.count()).select_from(registered_groups).where(registered_groups.c.record_count >= 2).scalar_subquery().label("assets_with_multiple_records"),
            select(func.max(registered_groups.c.record_count)).select_from(registered_groups).scalar_subquery().label("maximum_records_per_asset"),
            select(func.min(record_date)).where(
                AssetHealthAssessmentMart.site_code == SITE_CODE,
                AssetHealthAssessmentMart.organization_code == ORGANIZATION_CODE,
            ).scalar_subquery().label("oldest_record_at"),
            select(func.max(record_date)).where(
                AssetHealthAssessmentMart.site_code == SITE_CODE,
                AssetHealthAssessmentMart.organization_code == ORGANIZATION_CODE,
            ).scalar_subquery().label("latest_record_at"),
        )
        status_statement = select(
            func.coalesce(AssetHealthAssessmentMart.lifecycle_status, "UNKNOWN").label("value"),
            func.count(AssetHealthAssessmentMart.canonical_id).label("count"),
        ).where(
            AssetHealthAssessmentMart.site_code == SITE_CODE,
            AssetHealthAssessmentMart.organization_code == ORGANIZATION_CODE,
        ).group_by(AssetHealthAssessmentMart.lifecycle_status).order_by(asc(AssetHealthAssessmentMart.lifecycle_status))
        with self.database.read_session() as session:
            summary = session.execute(summary_statement).one()._mapping
            statuses = session.execute(status_statement).all()
        latest = summary["latest_record_at"]
        latest_age_days = None
        if latest is not None:
            if latest.tzinfo is None:
                latest = latest.replace(tzinfo=timezone.utc)
            latest_age_days = (current - latest).total_seconds() / 86400.0
        return {
            "scope": {
                "site_code": SITE_CODE,
                "organization_code": ORGANIZATION_CODE,
                "registry_scope": "reliability_asset_registry",
                "population": "CONTROLLED_MART_POPULATION",
                "interpretation": "ASSESSMENT_RECORDS_NOT_HEALTH_SCORE",
            },
            "summary": {key: int(summary[key] or 0) for key in (
                "assessment_records", "records_with_asset_ref", "records_without_asset_ref",
                "asset_master_resolved", "registry_resolved", "technical_non_registry_records",
                "unresolved_asset_refs", "registered_assets_represented", "assets_with_multiple_records",
                "maximum_records_per_asset",
            )},
            "status_distribution": [{"value": row.value, "count": int(row.count)} for row in statuses],
            "record_recency": {
                "oldest_record_at": summary["oldest_record_at"],
                "latest_record_at": latest,
                "as_of": current,
                "latest_assessment_age_days": latest_age_days,
                "date_basis": "COALESCE(status_changed_at, source_updated_at, source_created_at)",
            },
            "evidence": {
                "assessment_records": "VERIFIED",
                "registered_assets_represented": "DERIVED_SAFE",
                "assets_with_multiple_records": "DERIVED_SAFE",
                "latest_assessment_record": "DERIVED_SAFE",
                "assessment_age": "DERIVED_SAFE",
                "lifecycle_status": "VERIFIED",
                "health_score": "BUSINESS_SEMANTICS_REQUIRED",
                "wellness_score": "BUSINESS_SEMANTICS_REQUIRED",
                "condition_classification": "BUSINESS_SEMANTICS_REQUIRED",
            },
        }

    def maintenance_investigation(
        self,
        *,
        window_days: int = 90,
        min_events: int = 2,
        offset: int = 0,
        limit: int = 25,
        sort: str = "event_count_desc",
        as_of: datetime | None = None,
    ) -> dict[str, object]:
        """Return bounded Registry-scoped repeat-activity aggregates.

        Repeat activity is deliberately an event-count description.  The
        query uses SQL window functions for chronology and never loads raw
        maintenance rows into Python.
        """
        if window_days not in {30, 90, 180}:
            raise ValueError("window_days must be one of 30, 90, or 180")
        if min_events not in {2, 3, 5}:
            raise ValueError("min_events must be one of 2, 3, or 5")
        if sort not in {"event_count_desc", "latest_activity_desc", "latest_gap_asc"}:
            raise ValueError("unsupported maintenance investigation sort")

        current = as_of or datetime.now(timezone.utc)
        if current.tzinfo is None:
            current = current.replace(tzinfo=timezone.utc)
        window_start = current - timedelta(days=window_days)
        activity_date = func.coalesce(MaintenanceEventMart.actual_start, MaintenanceEventMart.source_changed_at)
        raw_work_type = _raw_work_type(MaintenanceEventMart.sources)
        canonical_work_type = func.nullif(func.trim(MaintenanceEventMart.event_type), "")
        work_type = func.coalesce(raw_work_type, canonical_work_type, "UNKNOWN")

        scoped = (
            select(
                MaintenanceEventMart.equipment_id.label("asset_ref"),
                ReliabilityAssetRegistryMart.source_asset_number.label("source_asset_number"),
                MaintenanceEventMart.canonical_id.label("event_ref"),
                activity_date.label("activity_date"),
                work_type.label("work_type"),
            )
            .join(ReliabilityAssetRegistryMart, ReliabilityAssetRegistryMart.asset_ref == MaintenanceEventMart.equipment_id)
            .where(
                MaintenanceEventMart.site_code == SITE_CODE,
                MaintenanceEventMart.organization_code == ORGANIZATION_CODE,
                ReliabilityAssetRegistryMart.site_code == SITE_CODE,
                ReliabilityAssetRegistryMart.organization_code == ORGANIZATION_CODE,
                activity_date >= window_start,
                activity_date <= current,
                activity_date.is_not(None),
            )
            .subquery()
        )
        latest_rank = func.row_number().over(
            partition_by=scoped.c.asset_ref,
            order_by=(desc(scoped.c.activity_date), desc(scoped.c.event_ref)),
        ).label("latest_rank")
        prior_activity = func.lag(scoped.c.activity_date).over(
            partition_by=scoped.c.asset_ref,
            order_by=(asc(scoped.c.activity_date), asc(scoped.c.event_ref)),
        ).label("prior_activity")
        chronology = select(scoped, latest_rank, prior_activity).subquery()

        event_count = func.count(chronology.c.event_ref).label("event_count")
        latest_activity = func.max(chronology.c.activity_date).label("latest_activity")
        previous_activity = func.max(case((chronology.c.latest_rank == 2, chronology.c.activity_date), else_=None)).label("previous_activity")
        minimum_gap = func.min(self._gap_days(chronology.c.activity_date, chronology.c.prior_activity)).label("minimum_gap_days")
        latest_work_type = func.max(case((chronology.c.latest_rank == 1, chronology.c.work_type), else_=None)).label("latest_work_type")
        aggregate = (
            select(
                chronology.c.asset_ref,
                event_count,
                latest_activity,
                previous_activity,
                minimum_gap,
                latest_work_type,
            )
            .group_by(chronology.c.asset_ref)
            .subquery()
        )

        type_count = func.count(chronology.c.event_ref).label("type_event_count")
        type_counts = select(chronology.c.asset_ref, chronology.c.work_type, type_count).group_by(chronology.c.asset_ref, chronology.c.work_type).subquery()
        type_rank = func.row_number().over(
            partition_by=type_counts.c.asset_ref,
            order_by=(desc(type_counts.c.type_event_count), asc(type_counts.c.work_type)),
        ).label("type_rank")
        dominant_type = select(type_counts, type_rank).subquery()

        asset_statement = (
            select(
                aggregate.c.asset_ref,
                ReliabilityAssetRegistryMart.source_asset_number,
                AssetMasterMart.description,
                aggregate.c.event_count,
                aggregate.c.latest_activity,
                aggregate.c.previous_activity,
                self._gap_days(aggregate.c.latest_activity, aggregate.c.previous_activity).label("latest_gap_days"),
                aggregate.c.minimum_gap_days,
                aggregate.c.latest_work_type,
                dominant_type.c.work_type.label("dominant_work_type"),
            )
            .select_from(aggregate)
            .join(ReliabilityAssetRegistryMart, ReliabilityAssetRegistryMart.asset_ref == aggregate.c.asset_ref)
            .outerjoin(AssetMasterMart, AssetMasterMart.canonical_id == aggregate.c.asset_ref)
            .outerjoin(dominant_type, (dominant_type.c.asset_ref == aggregate.c.asset_ref) & (dominant_type.c.type_rank == 1))
            .where(
                ReliabilityAssetRegistryMart.site_code == SITE_CODE,
                ReliabilityAssetRegistryMart.organization_code == ORGANIZATION_CODE,
                aggregate.c.event_count >= min_events,
            )
        )
        tie_breakers = (asc(ReliabilityAssetRegistryMart.source_asset_number), asc(aggregate.c.asset_ref))
        if sort == "latest_activity_desc":
            asset_statement = asset_statement.order_by(desc(aggregate.c.latest_activity), *tie_breakers)
        elif sort == "latest_gap_asc":
            asset_statement = asset_statement.order_by(self._gap_days(aggregate.c.latest_activity, aggregate.c.previous_activity).nulls_last(), *tie_breakers)
        else:
            asset_statement = asset_statement.order_by(desc(aggregate.c.event_count), *tie_breakers)

        summary_statement = select(
            select(func.count(ReliabilityAssetRegistryMart.asset_ref)).where(
                ReliabilityAssetRegistryMart.site_code == SITE_CODE,
                ReliabilityAssetRegistryMart.organization_code == ORGANIZATION_CODE,
            ).scalar_subquery().label("registered_assets"),
            select(func.count()).select_from(scoped).scalar_subquery().label("maintenance_events"),
            select(func.count()).select_from(aggregate).scalar_subquery().label("assets_with_activity"),
            select(func.count()).select_from(aggregate).where(aggregate.c.event_count >= 2).scalar_subquery().label("assets_with_2plus_events"),
            select(func.count()).select_from(aggregate).where(aggregate.c.event_count >= 3).scalar_subquery().label("assets_with_3plus_events"),
            select(func.coalesce(func.sum(case((aggregate.c.event_count > 1, aggregate.c.event_count - 1), else_=0)), 0)).select_from(aggregate).scalar_subquery().label("repeat_activity_events"),
        )

        with self.database.read_session() as session:
            summary = session.execute(summary_statement).one()._mapping
            total = int(session.scalar(select(func.count()).select_from(asset_statement.order_by(None).subquery())) or 0)
            rows = session.execute(asset_statement.offset(offset).limit(limit)).all()

        assets = [
            {
                "asset_ref": row.asset_ref,
                "source_asset_number": row.source_asset_number,
                "description": row.description,
                "event_count": int(row.event_count or 0),
                "repeat_activity_events": max(int(row.event_count or 0) - 1, 0),
                "latest_activity": row.latest_activity,
                "previous_activity": row.previous_activity,
                "latest_gap_days": float(row.latest_gap_days) if row.latest_gap_days is not None else None,
                "minimum_gap_days": float(row.minimum_gap_days) if row.minimum_gap_days is not None else None,
                "latest_work_type": row.latest_work_type,
                "dominant_work_type": row.dominant_work_type,
            }
            for row in rows
        ]
        return {
            "scope": {
                "site_code": SITE_CODE,
                "organization_code": ORGANIZATION_CODE,
                "registry_scope": "reliability_asset_registry",
                "date_basis": "COALESCE(actual_start, source_changed_at)",
                "interpretation": "ACTIVITY_NOT_FAILURE",
            },
            "window": {"days": window_days, "start": window_start, "as_of": current},
            "summary": {key: int(summary[key] or 0) for key in summary.keys()},
            "assets": assets,
            "meta": {"total": total, "offset": offset, "limit": limit, "has_more": offset + len(assets) < total},
            "evidence": {
                "repeat_activity": "DERIVED_SAFE",
                "work_type_source": "sources.maximo.worktype → event_type → UNKNOWN",
                "activity_date": "Activity date uses actual start when available, otherwise source change time.",
                "repeat_failure": "BUSINESS_SEMANTICS_REQUIRED",
            },
        }
