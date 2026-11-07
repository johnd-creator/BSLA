"""Local Collector -> Reliability Mart projection.

This module is intentionally downstream-only: it reads the Collector's local
operational tables and writes validated Contract v1 records to the Mart.  It
never constructs a Maximo client and never changes a Maximo SyncCursor.
"""

from __future__ import annotations

from src.adapters.maximo.actual_dates import retained_values

import os
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import delete, func, or_, select

from src.adapters.maximo.canonical_mappers import (
    asset_master_from_payload,
    maintenance_event_from_payload,
)
from src.canonical_identity import scoped_reference
from src.config import DbConfig, MaximoConfig
from src.repositories import mart_models, models
from src.repositories.database import Database
from src.services.asset_registry_reconciliation import (
    RegistrySnapshot,
    normalize_identifier,
    parse_registry_file,
)
from src.services.canonical import CanonicalCollection
from src.services.mart import MartWriter


LOG = logging.getLogger(__name__)

REGISTRY_SOURCE = "MAXIMO_LIST_OF_ASSETS"
SITE_CODE = "BSR"
ORGANIZATION_CODE = "IP"
DEFAULT_BATCH_SIZE = 500
DEFAULT_OVERLAP = timedelta(days=1)


@dataclass
class ProjectionReport:
    projection_key: str
    mode: str
    rows_seen: int = 0
    rows_written: int = 0
    rows_inserted: int = 0
    rows_updated: int = 0
    rows_unchanged: int = 0
    skipped_missing_equipment: int = 0
    skipped_scope: int = 0
    skipped_unproven_scope: int = 0
    skipped_mapping: int = 0
    null_source_changed_at: int = 0
    watermark: datetime | None = None
    completed: bool = False
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def as_dict(self) -> dict[str, Any]:
        return {
            "projection_key": self.projection_key,
            "mode": self.mode,
            "rows_seen": self.rows_seen,
            "rows_written": self.rows_written,
            "inserted": self.rows_inserted,
            "updated": self.rows_updated,
            "unchanged": self.rows_unchanged,
            "skipped_missing_equipment": self.skipped_missing_equipment,
            "skipped_scope": self.skipped_scope,
            "skipped_unproven_scope": self.skipped_unproven_scope,
            "skipped_mapping": self.skipped_mapping,
            "null_source_changed_at": self.null_source_changed_at,
            "watermark": self.watermark.isoformat() if self.watermark else None,
            "completed": self.completed,
        }


def mart_write_database() -> Database:
    """Return the configured local Mart writer database.

    The current development deployment co-locates Collector and Mart tables,
    so DATABASE_URL remains the safe fallback.  Production can use a distinct
    PostgreSQL DSN without changing the projection code.
    """

    dsn = os.getenv("RELIABILITY_MART_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("RELIABILITY_MART_DATABASE_URL or DATABASE_URL is required")
    return Database(DbConfig(dsn=dsn))


def _maximo_source(row: models.EquipmentOrm) -> dict[str, Any]:
    source = dict((row.sources or {}).get("maximo") or {})
    source.setdefault("assetnum", row.id)
    source.setdefault("description", row.description or row.name)
    source.setdefault("status", row.status)
    source.setdefault("assettype", row.equipment_class)
    source.setdefault("eq11", row.unit)
    source.setdefault("location", row.location_id)
    source.setdefault("parent", row.parent_id)
    source.setdefault("ancestor", row.ancestor_id)
    source.setdefault("changedate", _timestamp_value(row.source_changed_at))
    source.setdefault("installdate", _timestamp_value(row.installed_at))
    source.setdefault("isrunning", row.is_running)
    source.setdefault("children", row.has_children)
    source.setdefault("priority", row.priority)
    source.setdefault("failurecode", row.failure_code)
    source.setdefault("totdowntime", row.downtime_total_hours)
    return source


def _timestamp_value(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def _asset_record(row: models.EquipmentOrm) -> dict[str, Any] | None:
    source = _maximo_source(row)
    if source.get("siteid") != SITE_CODE or source.get("orgid") != ORGANIZATION_CODE:
        return None
    record = asset_master_from_payload(source)
    parent = normalize_identifier(source.get("parent"))
    if parent:
        record["parent_asset_ref"] = scoped_reference(
            "asset", "MXASSET", parent, SITE_CODE, ORGANIZATION_CODE
        )
        record.setdefault("relationship_evidence", {})["parent_asset_ref"] = {
            "status": "DIRECT_VERIFIED",
            "notes": "local Collector Maximo parent field",
        }
    return record


def _work_order_payload(row: models.WorkOrderOrm) -> dict[str, Any] | None:
    equipment_id = normalize_identifier(row.equipment_id)
    if not equipment_id:
        return None
    proof = (row.sources or {}).get("maximo", {}).get("actual_dates")
    actual = retained_values(proof, row.id, equipment_id, row.source_changed_at) if row.status == "CLOSE" else {}
    source = (row.sources or {}).get("maximo") or {}
    # Explicit contradicting scope is never repaired by an asset join.
    if any(source.get(key) not in (None, expected) for key, expected in (("siteid", SITE_CODE), ("orgid", ORGANIZATION_CODE))):
        return None
    direct_scope = source.get("siteid") == SITE_CODE and source.get("orgid") == ORGANIZATION_CODE
    # Only approved scalar fields are reconstructed.  Person fields and raw
    # source JSON are intentionally excluded from the canonical payload.
    return {
        "wonum": row.id,
        "assetnum": equipment_id,
        "siteid": SITE_CODE,
        "orgid": ORGANIZATION_CODE,
        "status": row.status,
        "istask": row.is_task,
        "collector_scope_evidence": "DIRECT_SOURCE" if direct_scope else "LEGACY_ASSET_JOIN_UNVERIFIED_WO_SCOPE",
        "worktype": row.work_type,
        # New retained source clocks keep uncertainty in disposable/naive stores.
        # Existing source_changed_at normalization is outside this correction.
        "reportdate": row.reported_at.isoformat() if row.reported_at else None,
        "schedstart": row.scheduled_start.isoformat() if row.scheduled_start else None,
        "schedfinish": row.scheduled_finish.isoformat() if row.scheduled_finish else None,
        "changedate": _timestamp_value(row.source_changed_at),
        # Legacy numeric downtime may be a coerced source boolean. Never replay as hours.
        "failurecode": row.failure_code,
        "collector_reliability_evidence": source.get("reliability_evidence"),
        "actlabhrs": row.actual_labor_hours,
        "description": row.description,
        # Replay only scoped/versioned retained actual-clock evidence.
        "collector_actual_dates": proof,
        "actstart": actual.get("actstart"),
        "actfinish": actual.get("actfinish"),
    }


class CollectorMartProjector:
    """Project local Equipment and Work Orders in bounded idempotent batches."""

    def __init__(
        self,
        collector_db: Database,
        mart_db: Database,
        *,
        batch_size: int = DEFAULT_BATCH_SIZE,
        overlap: timedelta = DEFAULT_OVERLAP,
        work_order_prefixes: tuple[str, ...] | None = None,
    ) -> None:
        if batch_size < 1 or batch_size > 5000:
            raise ValueError("batch_size must be between 1 and 5000")
        self.collector_db = collector_db
        self.mart_db = mart_db
        self.batch_size = batch_size
        self.overlap = overlap
        self.work_order_prefixes = tuple(
            prefix.upper() for prefix in (work_order_prefixes or MaximoConfig.from_environment().wo_prefixes)
        )
        self.writer = MartWriter(mart_db)

    def _state(self, key: str) -> mart_models.MartProjectionStateOrm | None:
        with self.mart_db.session() as session:
            return session.get(mart_models.MartProjectionStateOrm, key)

    def _save_state(self, report: ProjectionReport) -> None:
        now = datetime.now(timezone.utc)
        with self.mart_db.session() as session:
            state = session.get(mart_models.MartProjectionStateOrm, report.projection_key)
            if state is None:
                state = mart_models.MartProjectionStateOrm(
                    projection_key=report.projection_key,
                    watermark=report.watermark,
                    last_status="SUCCEEDED",
                    last_success_at=report.started_at,
                    rows_seen=report.rows_seen,
                    rows_written=report.rows_written,
                    updated_at=now,
                )
                session.add(state)
            else:
                state.watermark = report.watermark
                state.last_status = "SUCCEEDED"
                state.last_success_at = report.started_at
                state.rows_seen = report.rows_seen
                state.rows_written = report.rows_written
                state.updated_at = now
            session.commit()

    def _save_failure(self, projection_key: str) -> None:
        """Record failed attempt without advancing the last successful checkpoint."""
        now = datetime.now(timezone.utc)
        with self.mart_db.session() as session:
            state = session.get(mart_models.MartProjectionStateOrm, projection_key)
            if state is None:
                state = mart_models.MartProjectionStateOrm(
                    projection_key=projection_key, watermark=None, last_status="FAILED",
                    last_success_at=None, rows_seen=0, rows_written=0, updated_at=now,
                )
                session.add(state)
            else:
                state.last_status = "FAILED"
                state.updated_at = now
            session.commit()

    def _equipment_ids(self) -> set[str]:
        with self.collector_db.session() as session:
            return {
                normalize_identifier(value) or ""
                for value in session.scalars(select(models.EquipmentOrm.id)).all()
            }

    def project(self, projection_key: str, *, incremental: bool = False) -> ProjectionReport:
        if projection_key not in {"asset_master", "maintenance_event"}:
            raise ValueError("unsupported local projection")
        try:
            return self._project(projection_key, incremental=incremental)
        except Exception:
            try:
                self._save_failure(projection_key)
            except Exception:
                # Preserve the original failure and avoid logging source payloads,
                # credentials or exception text. An unavailable target cannot attest.
                LOG.error("Local projection failed; FAILED state could not be persisted")
            raise

    def _project(self, projection_key: str, *, incremental: bool = False) -> ProjectionReport:
        previous = self._state(projection_key)
        mode = "incremental" if incremental else "full"
        if incremental and (previous is None or previous.watermark is None):
            mode = "full"
            incremental = False
        if previous and previous.watermark and previous.watermark.tzinfo is None:
            previous.watermark = previous.watermark.replace(tzinfo=timezone.utc)
        report = ProjectionReport(projection_key, mode)
        model = models.EquipmentOrm if projection_key == "asset_master" else models.WorkOrderOrm
        equipment_ids = self._equipment_ids() if projection_key == "maintenance_event" else set()
        last_id = None
        while True:
            with self.collector_db.session() as session:
                statement = select(model).order_by(model.id).limit(self.batch_size)
                if last_id is not None:
                    statement = statement.where(model.id > last_id)
                if incremental and previous and previous.watermark:
                    lower = previous.watermark - self.overlap
                    changed = [model.source_changed_at.is_(None), model.source_changed_at >= lower]
                    if previous.last_success_at:
                        local_lower = previous.last_success_at
                        if local_lower.tzinfo is None:
                            local_lower = local_lower.replace(tzinfo=timezone.utc)
                        local_lower = (local_lower - self.overlap).astimezone(timezone.utc).isoformat()
                        changed.append(model.sources["maximo"]["collector_updated_at"].as_string() >= local_lower)
                        if projection_key == "maintenance_event":
                            # Old retained WOs skipped for a missing asset become
                            # projectable when that exact asset arrives locally.
                            recovered = select(models.EquipmentOrm.id).where(
                                models.EquipmentOrm.sources["maximo"]["collector_updated_at"].as_string() >= local_lower)
                            changed.append(model.equipment_id.in_(recovered))
                    statement = statement.where(or_(*changed))
                rows = list(session.scalars(statement).all())
            if not rows:
                break
            last_id = rows[-1].id
            records: list[dict[str, Any]] = []
            for row in rows:
                report.rows_seen += 1
                if row.source_changed_at is None:
                    report.null_source_changed_at += 1
                if projection_key == "asset_master":
                    try:
                        record = _asset_record(row)
                    except Exception:
                        record = None
                    if record is None:
                        report.skipped_unproven_scope += 1
                    else:
                        records.append(record)
                else:
                    if not str(row.id).upper().startswith(self.work_order_prefixes):
                        report.skipped_scope += 1
                        continue
                    equipment_id = normalize_identifier(row.equipment_id)
                    if equipment_id is None or equipment_id not in equipment_ids:
                        report.skipped_missing_equipment += 1
                        continue
                    try:
                        record = maintenance_event_from_payload(_work_order_payload(row) or {})
                    except Exception:
                        report.skipped_mapping += 1
                    else:
                        records.append(record)
            if records:
                collection = CanonicalCollection(projection_key, records=records)
                stats = self.writer.persist_collection(collection)
                report.rows_written += stats.records_inserted + stats.records_updated + stats.records_unchanged
                report.rows_inserted += stats.records_inserted
                report.rows_updated += stats.records_updated
                report.rows_unchanged += stats.records_unchanged
            if len(rows) < self.batch_size:
                break

        with self.collector_db.session() as session:
            watermark = session.scalar(select(func.max(model.source_changed_at)))
        if watermark is not None and watermark.tzinfo is None:
            watermark = watermark.replace(tzinfo=timezone.utc)
        report.watermark = watermark
        report.completed = True
        self._save_state(report)
        return report

    def project_all(self, *, incremental: bool = False) -> dict[str, dict[str, Any]]:
        return {
            "asset_master": self.project("asset_master", incremental=incremental).as_dict(),
            "maintenance_event": self.project("maintenance_event", incremental=incremental).as_dict(),
        }


class RegistryImportError(ValueError):
    """Registry snapshot failed semantic activation validation."""


def validate_registry_snapshot_semantics(snapshot: RegistrySnapshot) -> None:
    ids = [normalize_identifier(row.asset) for row in snapshot.records]
    nonblank = [value for value in ids if value]
    if snapshot.sheet.strip().lower() != "list of assets":
        raise RegistryImportError("REGISTRY_SHEET_INVALID")
    if not nonblank:
        raise RegistryImportError("REGISTRY_ASSET_COLUMN_EMPTY")
    if len(nonblank) != len(set(nonblank)):
        raise RegistryImportError("REGISTRY_DUPLICATE_ASSET")
    if any(row.site != SITE_CODE for row in snapshot.records):
        raise RegistryImportError("REGISTRY_SITE_OUTSIDE_SCOPE")


def import_registry_snapshot(
    snapshot: RegistrySnapshot,
    collector_db: Database,
    mart_db: Database,
    *,
    expected_sha256: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Atomically activate a semantically valid current registry snapshot."""

    validate_registry_snapshot_semantics(snapshot)
    if expected_sha256 and snapshot.sha256 != expected_sha256:
        raise RegistryImportError("REGISTRY_FINGERPRINT_MISMATCH")
    registry_ids = {
        normalize_identifier(row.asset)
        for row in snapshot.records
        if normalize_identifier(row.asset)
    }
    with collector_db.session() as session:
        equipment_ids = {
            normalize_identifier(value) or ""
            for value in session.scalars(select(models.EquipmentOrm.id)).all()
        }
    missing_collector = registry_ids - equipment_ids
    if missing_collector:
        raise RegistryImportError("REGISTRY_ASSET_NOT_RESOLVED_TO_COLLECTOR")

    with mart_db.session() as session:
        source_rows = session.execute(
            select(
                mart_models.AssetMasterMartOrm.canonical_id,
                mart_models.AssetMasterMartOrm.source_asset_number,
                mart_models.AssetMasterMartOrm.site_code,
                mart_models.AssetMasterMartOrm.organization_code,
            ).where(
                mart_models.AssetMasterMartOrm.source_asset_number.in_(registry_ids),
                mart_models.AssetMasterMartOrm.site_code == SITE_CODE,
                mart_models.AssetMasterMartOrm.organization_code == ORGANIZATION_CODE,
            )
        ).all()
        by_source = {normalize_identifier(row.source_asset_number): row for row in source_rows}
        if any(asset_id not in by_source for asset_id in registry_ids):
            raise RegistryImportError("REGISTRY_ASSET_NOT_RESOLVED_TO_ASSET_MASTER")
        if dry_run:
            return {
                "rows": snapshot.rows,
                "unique_assets": len(registry_ids),
                "resolved": len(registry_ids),
                "sha256": snapshot.sha256,
                "dry_run": True,
            }
        imported_at = datetime.now(timezone.utc)
        session.execute(delete(mart_models.ReliabilityAssetRegistryMartOrm))
        for asset_id in sorted(registry_ids):
            row = by_source[asset_id]
            session.add(
                mart_models.ReliabilityAssetRegistryMartOrm(
                    asset_ref=row.canonical_id,
                    source_asset_number=asset_id,
                    site_code=SITE_CODE,
                    organization_code=ORGANIZATION_CODE,
                    registry_source=REGISTRY_SOURCE,
                    snapshot_sha256=snapshot.sha256,
                    snapshot_row_count=snapshot.rows,
                    snapshot_imported_at=imported_at,
                )
            )
        session.commit()
    return {
        "rows": snapshot.rows,
        "unique_assets": len(registry_ids),
        "resolved": len(registry_ids),
        "sha256": snapshot.sha256,
        "dry_run": False,
    }


def bootstrap_local_mart(
    registry_file: str | Path,
    collector_db: Database,
    mart_db: Database,
    *,
    expected_sha256: str,
    batch_size: int = DEFAULT_BATCH_SIZE,
    dry_run: bool = False,
) -> dict[str, Any]:
    snapshot = parse_registry_file(registry_file)
    if snapshot.sha256 != expected_sha256:
        raise RegistryImportError("REGISTRY_FINGERPRINT_MISMATCH")
    projector = CollectorMartProjector(collector_db, mart_db, batch_size=batch_size)
    if dry_run:
        registry = import_registry_snapshot(snapshot, collector_db, mart_db, expected_sha256=expected_sha256, dry_run=True)
        return {"registry": registry, "dry_run": True}
    assets = projector.project("asset_master")
    maintenance = projector.project("maintenance_event")
    registry = import_registry_snapshot(snapshot, collector_db, mart_db, expected_sha256=expected_sha256)
    return {
        "registry": registry,
        "asset_master": assets.as_dict(),
        "maintenance_event": maintenance.as_dict(),
        "dry_run": False,
    }
