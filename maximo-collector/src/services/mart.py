"""Persistence boundary for NADI Reliability Mart Contract v1.

The writer accepts only validated canonical records. It applies a second BSR/IP
scope guard, stores approved canonical JSON blocks, and upserts by
``canonical_id``. It deliberately does not call Maximo or resolve references
through the network.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.contracts.validator import ContractValidationError, validate_record
from src.repositories import mart_models as orm
from src.repositories.database import Database

SUPPORTED_CONTRACT_VERSION = "1.0"
REQUIRED_SITE = "BSR"
REQUIRED_ORGANIZATION = "IP"


class MartPersistenceError(RuntimeError):
    """Base class for a rejected or failed Mart write."""


class ScopeViolation(MartPersistenceError):
    """Canonical record is outside the authorized persistence scope."""


class UnsupportedContractVersion(MartPersistenceError):
    """Canonical record uses a contract version not supported by this Mart."""


class UnsupportedCanonicalEntity(MartPersistenceError):
    """Entity is outside the Contract v1 persistence allowlist."""


class CanonicalRecordRejected(MartPersistenceError):
    """Record failed contract or payload-safety validation."""


@dataclass
class MartWriteStats:
    canonical_entity: str
    records_received: int = 0
    records_inserted: int = 0
    records_updated: int = 0
    records_unchanged: int = 0
    records_rejected: int = 0
    scope_violations: int = 0
    contract_errors: int = 0
    database_errors: int = 0


@dataclass(frozen=True)
class _EntitySpec:
    model: type
    row_builder: Any


def _parse_datetime(value: object, field: str) -> datetime | None:
    if value is None or isinstance(value, datetime):
        return value
    if not isinstance(value, str) or not value.strip():
        raise CanonicalRecordRejected(f"{field} must be an ISO-8601 datetime or null")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise CanonicalRecordRejected(f"{field} is not a valid ISO-8601 datetime") from error
    if parsed.tzinfo is None:
        raise CanonicalRecordRejected(f"{field} must preserve timezone information")
    return parsed


def _string_or_none(value: object) -> str | None:
    return None if value is None else str(value)


def _source_created(record: Mapping[str, Any]) -> datetime | None:
    return _parse_datetime(record.get("provenance", {}).get("source_created_at"), "provenance.source_created_at")


def _source_updated(record: Mapping[str, Any]) -> datetime | None:
    value = record.get("source_updated_at")
    if value is None:
        value = record.get("provenance", {}).get("source_updated_at")
    return _parse_datetime(value, "source_updated_at")


def _common(record: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "canonical_id": record["canonical_id"],
        "contract_version": record["contract_version"],
        "site_code": record.get("site_code"),
        "organization_code": record.get("organization_code"),
        "provenance": copy.deepcopy(record["provenance"]),
        "relationship_evidence": copy.deepcopy(record.get("relationship_evidence") or {}),
        "sources": copy.deepcopy(record.get("sources")),
    }


def _asset_row(record: Mapping[str, Any]) -> dict[str, Any]:
    row = _common(record)
    row.update({
        "source_asset_number": record.get("source_asset_number"),
        "description": record.get("description"),
        "status": record.get("status"),
        "location_ref": record.get("location_ref"),
        "parent_asset_ref": record.get("parent_asset_ref"),
        "asset_type": record.get("asset_type"),
        "plant": record.get("plant"),
        "unit": record.get("unit"),
        "criticality": record.get("criticality"),
        "source_updated_at": _source_updated(record),
    })
    return row


def _maintenance_row(record: Mapping[str, Any]) -> dict[str, Any]:
    row = _common(record)
    row.update({
        "id": record["id"],
        "equipment_id": record["equipment_id"],
        "work_order_id": record.get("work_order_id"),
        "event_type": record.get("event_type"),
        "status": record.get("status"),
        "actual_start": _parse_datetime(record.get("actual_start"), "actual_start"),
        "actual_finish": _parse_datetime(record.get("actual_finish"), "actual_finish"),
        "duration_hours": record.get("duration_hours"),
        "labor_hours": record.get("labor_hours"),
        "downtime_hours": record.get("downtime_hours"),
        "failure_code": record.get("failure_code"),
        "reported_by": record.get("reported_by"),
        "lead": record.get("lead"),
        "source_changed_at": _parse_datetime(record.get("source_changed_at"), "source_changed_at"),
    })
    return row


def _fmea_row(record: Mapping[str, Any]) -> dict[str, Any]:
    row = _common(record)
    row.update({
        "source_record_id": record.get("source_record_id"),
        "source_number": record.get("source_number"),
        "revision": _string_or_none(record.get("revision")),
        "lifecycle_status": record.get("lifecycle_status"),
        "description": record.get("description"),
        "asset_ref": record.get("asset_ref"),
        "failure_code_ref": record.get("failure_code_ref"),
        "source_updated_at": _source_updated(record),
        "status_changed_at": _parse_datetime(record.get("status_changed_at"), "status_changed_at"),
    })
    return row


def _rcfa_row(record: Mapping[str, Any]) -> dict[str, Any]:
    row = _common(record)
    row.update({
        "source_record_id": record.get("source_record_id"),
        "source_number": record.get("source_number"),
        "revision": _string_or_none(record.get("revision")),
        "lifecycle_status": record.get("lifecycle_status"),
        "category": record.get("category"),
        "asset_ref": record.get("asset_ref"),
        "location_ref": record.get("location_ref"),
        "workorder_ref": record.get("workorder_ref"),
        "failure_event_ref": record.get("failure_event_ref"),
        "source_created_at": _parse_datetime(record.get("source_created_at"), "source_created_at"),
        "requested_at": _parse_datetime(record.get("requested_at"), "requested_at"),
    })
    return row


def _bhm_row(record: Mapping[str, Any]) -> dict[str, Any]:
    row = _common(record)
    row.update({
        "source_record_id": record.get("source_record_id"),
        "revision": _string_or_none(record.get("revision")),
        "lifecycle_status": record.get("lifecycle_status"),
        "description": record.get("description"),
        "function_description": record.get("function_description"),
        "asset_ref": record.get("asset_ref"),
        "source_created_at": _source_created(record),
        "source_updated_at": _source_updated(record),
        "status_changed_at": _parse_datetime(record.get("status_changed_at"), "status_changed_at"),
    })
    return row


def _overhaul_row(record: Mapping[str, Any]) -> dict[str, Any]:
    row = _common(record)
    row.update({
        "source_record_id": record.get("source_record_id"),
        "source_number": record.get("source_number"),
        "lifecycle_status": record.get("lifecycle_status"),
        "workorder_ref": record.get("workorder_ref"),
        "asset_ref": record.get("asset_ref"),
        "planned_start_at": _parse_datetime(record.get("planned_start_at"), "planned_start_at"),
        "planned_finish_at": _parse_datetime(record.get("planned_finish_at"), "planned_finish_at"),
        "actual_start_at": _parse_datetime(record.get("actual_start_at"), "actual_start_at"),
        "actual_finish_at": _parse_datetime(record.get("actual_finish_at"), "actual_finish_at"),
        "progress": record.get("progress"),
        "source_created_at": _parse_datetime(record.get("source_created_at"), "source_created_at"),
        "source_updated_at": _source_updated(record),
        "unresolved_source_attributes": copy.deepcopy(record.get("unresolved_source_attributes")),
    })
    return row


ENTITY_SPECS: dict[str, _EntitySpec] = {
    "asset_master": _EntitySpec(orm.AssetMasterMartOrm, _asset_row),
    "maintenance_event": _EntitySpec(orm.MaintenanceEventMartOrm, _maintenance_row),
    "fmea_assessment": _EntitySpec(orm.FmeaAssessmentMartOrm, _fmea_row),
    "rcfa_analysis": _EntitySpec(orm.RcfaAnalysisMartOrm, _rcfa_row),
    "asset_health_assessment": _EntitySpec(orm.AssetHealthAssessmentMartOrm, _bhm_row),
    "overhaul_event": _EntitySpec(orm.OverhaulEventMartOrm, _overhaul_row),
}

_RAW_PAYLOAD_KEYS = frozenset({
    "raw_payload", "raw_source", "raw_response", "oslc_response", "maximo_json", "source_blob",
})


def _assert_no_raw_payload(value: object, path: str = "record") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key).lower() in _RAW_PAYLOAD_KEYS:
                raise CanonicalRecordRejected(f"raw payload field is not allowed: {path}.{key}")
            _assert_no_raw_payload(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _assert_no_raw_payload(child, f"{path}[{index}]")


def _assert_scope(record: Mapping[str, Any]) -> None:
    provenance = record.get("provenance")
    if not isinstance(provenance, Mapping):
        raise ScopeViolation("provenance is required for scoped persistence")
    if provenance.get("source_system") != "MAXIMO":
        raise ScopeViolation("provenance.source_system must be MAXIMO")
    if provenance.get("source_site") != REQUIRED_SITE:
        raise ScopeViolation("provenance.source_site is outside BSR scope")
    if provenance.get("source_organization") != REQUIRED_ORGANIZATION:
        raise ScopeViolation("provenance.source_organization is outside IP scope")

    for field, expected in (("site_code", REQUIRED_SITE), ("organization_code", REQUIRED_ORGANIZATION)):
        if field in record and record[field] is not None and record[field] != expected:
            raise ScopeViolation(f"{field} disagrees with authorized scope")

    maximo_source = (record.get("sources") or {}).get("maximo")
    if isinstance(maximo_source, Mapping):
        for field, expected in (("siteid", REQUIRED_SITE), ("orgid", REQUIRED_ORGANIZATION)):
            if field in maximo_source and maximo_source[field] is not None and maximo_source[field] != expected:
                raise ScopeViolation(f"sources.maximo.{field} is outside authorized scope")


def _validate_for_write(entity: str, record: Mapping[str, Any]) -> dict[str, Any]:
    if entity not in ENTITY_SPECS:
        raise UnsupportedCanonicalEntity(f"unsupported canonical entity: {entity}")
    if record.get("contract_version") != SUPPORTED_CONTRACT_VERSION:
        raise UnsupportedContractVersion(
            f"{entity} requires contract_version {SUPPORTED_CONTRACT_VERSION}"
        )
    if not record.get("canonical_id"):
        raise CanonicalRecordRejected(f"{entity}.canonical_id is required")
    _assert_no_raw_payload(record)
    _assert_scope(record)
    try:
        validated = validate_record(entity, record)
    except ContractValidationError as error:
        raise CanonicalRecordRejected(str(error)) from error
    return validated


class MartWriter:
    """Persist Contract v1 collections in one transaction per entity batch."""

    def __init__(self, db: Database):
        self._db = db

    def persist_collection(self, collection: Any, *, dry_run: bool = False) -> MartWriteStats:
        """Existing owning transaction API; validate before opening any session."""
        entity, stats, validated = self._prepare_collection(collection)
        if dry_run or not validated:
            return stats
        try:
            with self._db.session() as session:
                self._persist_validated(entity, stats, validated, session)
                session.commit()
        except MartPersistenceError:
            raise
        except Exception as error:
            stats.database_errors += 1
            raise MartPersistenceError(f"Mart transaction failed for {entity}") from error
        return stats

    def persist_in_session(
        self, collection: Any, session: Session, *, dry_run: bool = False
    ) -> MartWriteStats:
        """Caller owns commit/rollback. Never acknowledge work before it commits.

        Validate the entire batch before adding any rows. On error the caller
        MUST roll back its transaction, including any related receipts.
        """
        entity, stats, validated = self._prepare_collection(collection)
        if dry_run or not validated:
            return stats
        return self._persist_validated(entity, stats, validated, session)

    @staticmethod
    def _prepare_collection(collection: Any):
        entity = str(collection.canonical_entity)
        stats = MartWriteStats(entity, records_received=len(collection.records))
        if entity not in ENTITY_SPECS:
            stats.records_rejected = len(collection.records)
            stats.contract_errors = len(collection.records)
            raise UnsupportedCanonicalEntity(f"unsupported canonical entity: {entity}")

        validated: list[dict[str, Any]] = []
        for record in collection.records:
            try:
                validated.append(_validate_for_write(entity, record))
            except ScopeViolation:
                stats.records_rejected += 1
                stats.scope_violations += 1
                raise
            except (UnsupportedContractVersion, CanonicalRecordRejected):
                stats.records_rejected += 1
                stats.contract_errors += 1
                raise

        return entity, stats, validated

    @staticmethod
    def _persist_validated(entity, stats, validated, session):
        spec = ENTITY_SPECS[entity]
        try:
            for record in validated:
                row = spec.row_builder(record)
                existing = session.get(spec.model, record["canonical_id"])
                if existing is None:
                    now = datetime.now(timezone.utc)
                    row["mart_created_at"] = now
                    row["mart_updated_at"] = now
                    session.add(spec.model(**row))
                    stats.records_inserted += 1
                    continue

                changed = any(getattr(existing, key) != value for key, value in row.items())
                if not changed:
                    stats.records_unchanged += 1
                    continue
                for key, value in row.items():
                    setattr(existing, key, value)
                existing.mart_updated_at = _next_update_time(existing.mart_updated_at)
                stats.records_updated += 1
            session.flush()
        except MartPersistenceError:
            raise
        except Exception as error:  # pragma: no cover - database-specific failure
            stats.database_errors += 1
            raise MartPersistenceError(f"Mart transaction failed for {entity}") from error
        return stats


def _next_update_time(previous: datetime | None) -> datetime:
    now = datetime.now(timezone.utc)
    if previous is not None and now <= previous:
        return previous + timedelta(microseconds=1)
    return now


class MartIntegrityAuditor:
    """Report logical reference resolution without deleting unresolved rows."""

    def __init__(self, db: Database):
        self._db = db

    @staticmethod
    def _count(session: Any, model: type, field: str) -> int:
        column = getattr(model, field)
        return int(session.scalar(select(func.count()).select_from(model).where(column.is_not(None))) or 0)

    @staticmethod
    def _resolved(
        session: Any,
        model: type,
        field: str,
        target: type,
        target_field: str = "canonical_id",
    ) -> int:
        source_column = getattr(model, field)
        target_column = getattr(target, target_field)
        return int(
            session.scalar(
                # Count source rows, not join pairs. Work Order references are
                # intentionally non-unique in v1, so duplicate target rows
                # must not inflate the resolved count.
                select(func.count(func.distinct(model.canonical_id)))
                .select_from(model)
                .join(target, source_column == target_column)
                .where(source_column.is_not(None))
            )
            or 0
        )

    def audit(self) -> dict[str, int]:
        asset_refs = (
            (orm.FmeaAssessmentMartOrm, "asset_ref"),
            (orm.AssetHealthAssessmentMartOrm, "asset_ref"),
            (orm.MaintenanceEventMartOrm, "equipment_id"),
            (orm.OverhaulEventMartOrm, "asset_ref"),
        )
        with self._db.session() as session:
            asset_total = sum(self._count(session, model, field) for model, field in asset_refs)
            asset_resolved = sum(
                self._resolved(session, model, field, orm.AssetMasterMartOrm)
                for model, field in asset_refs
            )
            workorder_total = self._count(session, orm.OverhaulEventMartOrm, "workorder_ref")
            workorder_resolved = self._resolved(
                session,
                orm.OverhaulEventMartOrm,
                "workorder_ref",
                orm.MaintenanceEventMartOrm,
                "work_order_id",
            )
        return {
            "asset_reference_total": asset_total,
            "asset_reference_resolved": asset_resolved,
            "asset_reference_unresolved": asset_total - asset_resolved,
            "workorder_reference_total": workorder_total,
            "workorder_reference_resolved": workorder_resolved,
            "workorder_reference_unresolved": workorder_total - workorder_resolved,
        }
