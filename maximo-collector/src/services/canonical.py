"""Bounded canonical collection interface for MX-009R consumers."""

from __future__ import annotations

import logging
from itertools import islice
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping

from src.adapters.maximo.canonical_mappers import (
    asset_health_assessment_from_payload,
    asset_master_from_payload,
    fmea_assessment_from_payload,
    maintenance_event_from_payload,
    overhaul_event_from_payload,
    rcfa_analysis_from_payload,
)
from src.adapters.maximo.oslc_client import OslcClient
from src.config import MaximoConfig
from src.contracts.validator import ContractValidationError, validate_record
from src.contracts.mapping_drift import assert_mapping_contract

LOG = logging.getLogger(__name__)


@dataclass(frozen=True)
class CanonicalSourceConfig:
    object_structure: str
    canonical_entity: str
    mapper: Callable[..., dict[str, Any]]
    scope_clause: str = 'siteid="BSR"'
    select: tuple[str, ...] = ()
    required_values: tuple[tuple[str, str], ...] = ()
    prefix_field: str | None = None
    allowed_prefixes: tuple[str, ...] = ()
    order_by: str | None = None
    page_size: int | None = None
    max_pages: int = 1000


@dataclass
class CanonicalStats:
    source_records_read: int = 0
    canonical_records_emitted: int = 0
    records_skipped: int = 0
    mapping_errors: int = 0
    validation_errors: int = 0


@dataclass
class CanonicalCollection:
    canonical_entity: str
    records: list[dict[str, Any]] = field(default_factory=list)
    stats: CanonicalStats = field(default_factory=CanonicalStats)
    completeness: str = "UNKNOWN"  # EXHAUSTED | CAPPED | FAILED
    pages: int = 0
    failure_class: str | None = None


CANONICAL_CONFIGS: dict[str, CanonicalSourceConfig] = {
    "mxasset": CanonicalSourceConfig(
        "mxasset", "asset_master", asset_master_from_payload,
        select=("assetnum", "assetid", "description", "location", "siteid", "orgid", "status", "assettype", "plant", "eq11", "parent", "changedate", "priority"),
        required_values=(("eq11", "CS01"),), order_by="-changedate",
    ),
    "mxwodetail": CanonicalSourceConfig(
        "mxwodetail", "maintenance_event", maintenance_event_from_payload,
        select=("wonum", "assetnum", "siteid", "orgid", "status", "description", "worktype", "reportdate", "schedstart", "schedfinish", "actstart", "actfinish", "changedate", "downtime", "actlabhrs"),
        prefix_field="wonum", order_by=None, page_size=25,
    ),
    "ipfmea": CanonicalSourceConfig(
        "ipfmea", "fmea_assessment", fmea_assessment_from_payload,
        select=("fmeaid", "fmeanum", "revision", "status", "description", "assetnum", "failurecode", "siteid", "orgid", "lastmodifieddate", "statusdate"), order_by="-lastmodifieddate",
    ),
    "iprcfa": CanonicalSourceConfig(
        "iprcfa", "rcfa_analysis", rcfa_analysis_from_payload,
        select=("rcfaid", "norcfa", "revisi", "status", "kategori", "siteid", "orgid", "createddate", "req_date"), order_by="-createddate",
    ),
    "ipbhm": CanonicalSourceConfig(
        "ipbhm", "asset_health_assessment", asset_health_assessment_from_payload,
        select=("bhmid", "eid", "revision", "status", "description", "fungsi", "assetnum", "siteid", "orgid", "createddate", "lastmodifieddate", "statusdate"), order_by="-lastmodifieddate",
    ),
    "ip_dom_oh": CanonicalSourceConfig(
        "ip_dom_oh", "overhaul_event", overhaul_event_from_payload,
        select=("domid", "domohnum", "wonum", "inspeksinum", "status", "siteid", "orgid", "tgl_mulai", "tgl_selesai", "tgl_actual_mulai", "tgl_actual_selesai", "changedate", "createdate", "progress", "perfomance_test"), order_by="-changedate",
    ),
}


def canonical_config_for(name: str, runtime_config: MaximoConfig | None = None) -> CanonicalSourceConfig:
    """Resolve only the explicit canonical source allowlist."""
    key = name.strip().lower()
    try:
        config = CANONICAL_CONFIGS[key]
    except KeyError as exc:
        raise KeyError(f"unsupported canonical source: {name}") from exc
    runtime = runtime_config or MaximoConfig()
    if runtime.site_id != "BSR" or runtime.org_id != "IP":
        raise ValueError("canonical collection is restricted to BSR/IP")
    if key == "mxasset":
        return CanonicalSourceConfig(**{**config.__dict__, "required_values": (("eq11", runtime.equipment_unit),)})
    if key == "mxwodetail":
        return CanonicalSourceConfig(**{**config.__dict__, "allowed_prefixes": runtime.wo_prefixes})
    return config


class CanonicalCollector:
    """Collects canonical records without writing a Reliability Mart."""

    def __init__(self, client: OslcClient, *, validate: bool = True, runtime_config: MaximoConfig | None = None):
        self._client = client
        self._validate = validate
        self._runtime_config = runtime_config or MaximoConfig()
        # Fail fast if the committed source mapping has drifted from the
        # implementation's required identity/relationship semantics.
        assert_mapping_contract()

    def collect(
        self,
        name: str,
        *,
        workorder_index: Mapping[str, Mapping[str, Any]] | None = None,
        max_records: int | None = None,
        max_pages: int | None = None,
    ) -> CanonicalCollection:
        if max_records is not None and max_records < 1:
            raise ValueError("canonical max_records must be at least 1")
        if max_pages is not None and max_pages < 1:
            raise ValueError("canonical max_pages must be at least 1")
        config = canonical_config_for(name, self._runtime_config)
        if config.object_structure.lower() == "mxwodetail":
            raise ValueError("Collect WOs through the lifecycle collector, then project the local store")
        result = CanonicalCollection(config.canonical_entity)
        # MX-008S intentionally means one page when only max_records is given.
        # A caller must opt into multi-page traversal explicitly.
        effective_max_pages = (
            max_pages
            if max_pages is not None
            else (1 if max_records is not None else config.max_pages)
        )
        requested_page_size = config.page_size or self._runtime_config.page_size
        # Keep the response itself bounded by the source cap. islice alone
        # would stop yielding at the cap but could still download a larger
        # page from Maximo.
        effective_page_size = min(requested_page_size, max_records) if max_records is not None else config.page_size
        try:
            iterator = self._client.iterate(
                config.object_structure,
                where=config.scope_clause,
                required_scope=config.scope_clause,
                select=list(config.select),
                order_by=config.order_by,
                page_size=effective_page_size,
                max_pages=effective_max_pages,
                identity_field=config.prefix_field,
            )
            bounded_iterator = islice(iterator, max_records) if max_records is not None else iterator
            for raw in bounded_iterator:
                result.stats.source_records_read += 1
                if config.required_values and any(
                    str(raw.get(key) or "").strip().upper() != value.upper()
                    for key, value in config.required_values
                ):
                    result.stats.records_skipped += 1
                    continue
                if config.prefix_field and config.allowed_prefixes:
                    value = str(raw.get(config.prefix_field) or "").strip().upper()
                    if not value.startswith(tuple(prefix.upper() for prefix in config.allowed_prefixes)):
                        result.stats.records_skipped += 1
                        continue
                try:
                    if config.canonical_entity == "overhaul_event":
                        record = config.mapper(raw, workorder_index=workorder_index)
                    else:
                        record = config.mapper(raw)
                    if self._validate:
                        record = validate_record(config.canonical_entity, record)
                except ContractValidationError as error:
                    result.stats.records_skipped += 1
                    result.stats.validation_errors += 1
                    LOG.warning("skip canonical row resource=%s error_class=%s", config.object_structure, type(error).__name__)
                    continue
                except Exception as error:  # noqa: BLE001 — row-level isolation
                    result.stats.records_skipped += 1
                    result.stats.mapping_errors += 1
                    LOG.warning("skip canonical row resource=%s error_class=%s", config.object_structure, type(error).__name__)
                    continue
                result.records.append(record)
                result.stats.canonical_records_emitted += 1
            result.completeness = (
                "CAPPED"
                if max_records is not None and result.stats.source_records_read >= max_records
                else "EXHAUSTED"
            )
        except Exception as error:  # transport/auth/pagination failures are not row-level skips
            result.completeness = "FAILED"
            result.failure_class = type(error).__name__
            raise
        finally:
            result.pages = int(getattr(self._client, "last_iteration_pages", 0) or 0)
        return result

    def collect_assets(self, *, max_records: int | None = None, max_pages: int | None = None) -> CanonicalCollection:
        return self.collect("mxasset", max_records=max_records, max_pages=max_pages)

    def collect_workorders(self, *, max_records: int | None = None, max_pages: int | None = None) -> CanonicalCollection:
        return self.collect("mxwodetail", max_records=max_records, max_pages=max_pages)

    def collect_fmea(self, *, max_records: int | None = None, max_pages: int | None = None) -> CanonicalCollection:
        return self.collect("ipfmea", max_records=max_records, max_pages=max_pages)

    def collect_rcfa(self, *, max_records: int | None = None, max_pages: int | None = None) -> CanonicalCollection:
        return self.collect("iprcfa", max_records=max_records, max_pages=max_pages)

    def collect_bhm(self, *, max_records: int | None = None, max_pages: int | None = None) -> CanonicalCollection:
        return self.collect("ipbhm", max_records=max_records, max_pages=max_pages)

    def collect_overhauls(
        self,
        workorder_records: list[Mapping[str, Any]] | None = None,
        *,
        max_records: int | None = None,
        max_pages: int | None = None,
    ) -> CanonicalCollection:
        index = {
            str(record.get("provenance", {}).get("source_record_id")): record
            for record in (workorder_records or [])
            if record.get("provenance", {}).get("source_record_id")
        }
        return self.collect("ip_dom_oh", workorder_index=index, max_records=max_records, max_pages=max_pages)

    def collect_all(self) -> dict[str, CanonicalCollection]:
        workorders = self.collect_workorders()
        return {
            "asset_master": self.collect_assets(),
            "maintenance_event": workorders,
            "fmea_assessment": self.collect_fmea(),
            "rcfa_analysis": self.collect_rcfa(),
            "asset_health_assessment": self.collect_bhm(),
            "overhaul_event": self.collect_overhauls(workorders.records),
        }
