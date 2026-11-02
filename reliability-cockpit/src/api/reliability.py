"""Read-only, vendor-neutral Reliability Mart API."""

from __future__ import annotations

from datetime import datetime
import re
from typing import Generic, Literal, TypeVar

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError

from src.services.condition_query import AssetConditionEvidence, ConditionQueryService
from src.domain.asset_af_mapping import AssetAfMapping
from src.repositories.mart_database import MartDatabase, MartDatabaseConfigError, get_mart_database
from src.repositories.mart_reader import MartQueryRepository, QueryPage
from src.services.asset_af_mapping import AssetAfMappingResolution
from src.services.reliability import ReliabilityQueryService, TimelineEvent

router = APIRouter(prefix="/v1/reliability", tags=["reliability-mart"])
Sort = Literal["updated_desc", "updated_asc", "status", "date_desc", "date_asc", "created_desc", "created_asc"]


class PageMeta(BaseModel):
    total: int
    offset: int
    limit: int
    has_more: bool


PageItem = TypeVar("PageItem")


class Page(BaseModel, Generic[PageItem]):
    items: list[PageItem]
    meta: PageMeta


class AssetView(BaseModel):
    canonical_id: str
    contract_version: str
    source_asset_number: str | None = None
    description: str | None = None
    status: str | None = None
    location_ref: str | None = None
    parent_asset_ref: str | None = None
    site_code: str
    organization_code: str
    asset_type: str | None = None
    plant: str | None = None
    unit: str | None = None
    source_updated_at: datetime | None = None


class RegisteredReadScope(BaseModel):
    site_code: Literal["BSR"] = "BSR"
    organization_code: Literal["IP"] = "IP"
    kind: Literal["REGISTERED_BSR_IP"] = "REGISTERED_BSR_IP"


class RegisteredMaintenanceSummary(BaseModel):
    registered_assets: int = Field(ge=0)
    maintenance_events: int = Field(ge=0)
    assets_with_maintenance: int = Field(ge=0)


class RegisteredMaintenanceAsset(BaseModel):
    canonical_id: str
    source_asset_number: str | None = None
    description: str | None = None
    maintenance_events: int = Field(ge=1)
    latest_retained_activity: datetime | None = None


class RegisteredMaintenanceOverview(BaseModel):
    scope: RegisteredReadScope
    as_of: datetime
    summary: RegisteredMaintenanceSummary
    assets: list[RegisteredMaintenanceAsset] = Field(max_length=10)
    restricted_sections: list[str]
    operational_kpis: Literal["NOT_ELIGIBLE"]


class WorkClassificationView(BaseModel):
    raw_work_type: str | None = None
    canonical_category: str | None = None
    state: Literal["CANONICAL_SUPPORTED", "UNMAPPED", "MISSING_RETAINED_TYPE", "CANONICAL_ONLY"]
    origin: Literal["RETAINED_MAXIMO_WORKTYPE", "CANONICAL_EVENT_TYPE", "NOT_AVAILABLE"]
    confidence: Literal["VERIFIED", "UNRESOLVED"]
    description: str | None = None
    workflow_name: str | None = None
    workflow_version: str | None = None
    workflow_state: Literal["NOT_AVAILABLE"] = "NOT_AVAILABLE"
    status_state: Literal["AVAILABLE", "MISSING_RETAINED_STATUS"]


class MaintenanceSourceDetailView(BaseModel):
    """Allowlisted retained scalars; no legacy-store join or source acquisition."""

    work_order_number: str | None = None
    asset_number: str | None = None
    reported_at: str | None = None
    scheduled_start: str | None = None
    scheduled_finish: str | None = None


class MaintenanceView(BaseModel):
    canonical_id: str
    contract_version: str
    id: str
    equipment_id: str
    work_order_id: str | None = None
    event_type: str | None = None
    classification: WorkClassificationView | None = None
    source_detail: MaintenanceSourceDetailView | None = None
    status: str | None = None
    actual_start: datetime | None = None
    actual_finish: datetime | None = None
    duration_hours: float | None = None
    labor_hours: float | None = None
    downtime_hours: float | None = None
    failure_code: str | None = None
    source_changed_at: datetime | None = None
    site_code: str
    organization_code: str


class FmeaView(BaseModel):
    canonical_id: str
    contract_version: str
    source_record_id: str | None = None
    source_number: str | None = None
    revision: str | None = None
    lifecycle_status: str | None = None
    description: str | None = None
    asset_ref: str | None = None
    failure_code_ref: str | None = None
    site_code: str
    organization_code: str
    source_updated_at: datetime | None = None
    status_changed_at: datetime | None = None
    source_asset_number: str | None = None
    asset_description: str | None = None
    source_failure_code: str | None = None
    fmea_record_date: datetime | None = None
    fmea_age_days: float | None = None


class RcfaView(BaseModel):
    canonical_id: str
    contract_version: str
    source_record_id: str | None = None
    source_number: str | None = None
    revision: str | None = None
    lifecycle_status: str | None = None
    category: str | None = None
    asset_ref: str | None = None
    location_ref: str | None = None
    workorder_ref: str | None = None
    failure_event_ref: str | None = None
    site_code: str
    organization_code: str
    source_created_at: datetime | None = None
    requested_at: datetime | None = None
    rcfa_record_date: datetime | None = None
    rcfa_age_days: float | None = None
    relationship_status: str = "UNRESOLVED"


class HealthView(BaseModel):
    canonical_id: str
    contract_version: str
    source_record_id: str | None = None
    revision: str | None = None
    lifecycle_status: str | None = None
    description: str | None = None
    function_description: str | None = None
    asset_ref: str | None = None
    site_code: str
    organization_code: str
    source_created_at: datetime | None = None
    source_updated_at: datetime | None = None
    status_changed_at: datetime | None = None
    source_asset_number: str | None = None
    asset_description: str | None = None
    assessment_record_date: datetime | None = None
    assessment_age_days: float | None = None


class OverhaulView(BaseModel):
    canonical_id: str
    contract_version: str
    source_record_id: str | None = None
    source_number: str | None = None
    lifecycle_status: str | None = None
    workorder_ref: str | None = None
    source_work_order_number: str | None = None
    asset_ref: str | None = None
    source_asset_number: str | None = None
    asset_description: str | None = None
    work_order_resolution: Literal["SOURCE_LINK_VERIFIED_AND_MART_RESOLVED", "SOURCE_LINK_VERIFIED_BUT_MART_UNRESOLVED", "SOURCE_WORK_ORDER_MISSING"] = "SOURCE_WORK_ORDER_MISSING"
    asset_resolution: Literal["ASSET_RESOLVED_REGISTERED", "ASSET_RESOLVED_TECHNICAL_CONTEXT", "ASSET_UNRESOLVED"] = "ASSET_UNRESOLVED"
    site_code: str
    organization_code: str
    planned_start_at: datetime | None = None
    planned_finish_at: datetime | None = None
    actual_start_at: datetime | None = None
    actual_finish_at: datetime | None = None
    progress: object | None = None
    unresolved_attributes_present: bool = False


class TimelineView(BaseModel):
    event_id: str
    event_type: Literal["MAINTENANCE", "FMEA", "ASSET_HEALTH", "OVERHAUL"]
    event_at: datetime | None = None
    summary: str | None = None
    status: str | None = None
    canonical_ref: str


class IntegrityView(BaseModel):
    asset_refs_total: int = 0
    asset_refs_resolved: int = 0
    asset_refs_unresolved: int = 0
    workorder_refs_total: int = 0
    workorder_refs_resolved: int = 0
    workorder_refs_unresolved: int = 0
    technical_asset_context_total: int = 0
    registered_assets_total: int = 0
    registered_assets_resolved: int = 0
    registered_assets_unresolved: int = 0
    maintenance_registered_total: int = 0


class RegistryView(BaseModel):
    registered_asset_count: int
    snapshot_sha256: str | None = None
    snapshot_row_count: int | None = None
    snapshot_imported_at: datetime | None = None
    source: str


class PiAfReferenceView(BaseModel):
    pi_source_id: str
    af_server_ref: str
    af_database_ref: str
    af_element_ref: str
    af_path_snapshot: str | None = None
    af_element_name_snapshot: str | None = None


class AssetAfMappingCandidateView(BaseModel):
    mapping_id: str
    mapping_status: Literal["PROPOSED", "VERIFIED", "RETIRED"]
    mapping_role: Literal["PRIMARY_EQUIPMENT"]
    evidence_method: Literal["NATIVE_IDENTIFIER", "GOVERNED_LOOKUP", "MANUAL_VERIFICATION", "MIGRATED_VERIFIED"]
    verified_at: datetime | None = None
    retired_at: datetime | None = None
    pi_af: PiAfReferenceView


class AssetAfMappingResponse(BaseModel):
    asset_id: str
    mapping_state: Literal["UNMAPPED", "MAPPED", "AMBIGUOUS"]
    pi_af: PiAfReferenceView | None = None
    candidates: list[AssetAfMappingCandidateView] = Field(default_factory=list)


EvidenceClass = Literal["VERIFIED", "DERIVED_SAFE", "BUSINESS_SEMANTICS_REQUIRED", "DATA_NOT_AVAILABLE", "DEFERRED"]
PopulationType = Literal["LOCAL_COLLECTOR_PROJECTION", "CONTROLLED_MART_POPULATION", "BUSINESS_REGISTRY", "TECHNICAL_CONTEXT"]
ReadinessStatus = Literal["AVAILABLE", "BLOCKED", "NOT_AVAILABLE", "DEFERRED"]


class EvidenceValue(BaseModel):
    value: int
    evidence_class: EvidenceClass


class DataTrustScopeView(BaseModel):
    site_code: Literal["BSR"]
    organization_code: Literal["IP"]
    source_system: Literal["MAXIMO"]
    registered_asset_boundary: str
    sync_freshness: Literal["NOT_AVAILABLE"]
    interpretation: str


class DataTrustPopulationView(BaseModel):
    registered_reliability_assets: int
    registry_resolved: int
    registry_unresolved: int
    technical_asset_context: int
    maintenance_total: int
    registry_maintenance: int
    fmea: int
    asset_health: int
    rcfa: int
    overhaul: int


class DataTrustDomainView(BaseModel):
    domain: Literal["ASSET", "MAINTENANCE", "FMEA", "ASSET_HEALTH", "RCFA", "OVERHAUL"]
    source_system: Literal["MAXIMO"]
    source_object: str
    population_type: PopulationType
    record_count: int
    scoped_record_count: int | None = None
    registered_assets_represented: int | None = None
    business_scope: str
    relationship_state: str
    latest_record_date: datetime | None = None
    date_basis: str
    known_limitation: str
    evidence_class: EvidenceClass


class DataTrustRelationshipView(BaseModel):
    relationship: str
    evidence: Literal["VERIFIED", "DIRECT_VERIFIED", "DERIVED_VERIFIED_PATH", "RESOLUTION_MEASURED", "UNRESOLVED"]
    resolved_count: int | None = None
    unresolved_count: int | None = None
    technical_context_count: int | None = None
    interpretation: str


class DataTrustReadinessView(BaseModel):
    capability: str
    evidence_class: EvidenceClass
    status: ReadinessStatus
    reason: str


class DataTrustView(BaseModel):
    scope: DataTrustScopeView
    population: DataTrustPopulationView
    domains: list[DataTrustDomainView]
    relationships: list[DataTrustRelationshipView]
    semantic_readiness: list[DataTrustReadinessView]
    integrity: IntegrityView
    limitations: list[str]


class DecisionScopeView(BaseModel):
    site_code: Literal["BSR"]
    organization_code: Literal["IP"]
    registry_scope: str
    maintenance_source: str
    date_basis: str


class DataMaturityView(BaseModel):
    asset_maintenance: str
    controlled_domains: str
    rcfa_relationship: str
    technical_context: str


class DecisionSummaryView(BaseModel):
    registered_assets: EvidenceValue
    maintenance_activity_7d: EvidenceValue
    maintenance_activity_30d: EvidenceValue
    maintenance_activity_90d: EvidenceValue
    assets_active_7d: EvidenceValue
    assets_active_30d: EvidenceValue
    assets_active_90d: EvidenceValue


class ActivityTrendView(BaseModel):
    period_start: datetime
    period_end: datetime
    event_count: EvidenceValue


class DistributionView(BaseModel):
    value: str
    count: EvidenceValue


class ActivityConcentrationView(BaseModel):
    asset_ref: str
    source_asset_number: str
    description: str | None = None
    event_count: EvidenceValue
    latest_activity: datetime | None = None


class RecordAvailabilityView(BaseModel):
    fmea_records: EvidenceValue
    fmea_assets_represented: EvidenceValue
    asset_health_records: EvidenceValue
    asset_health_assets_represented: EvidenceValue
    rcfa_records: EvidenceValue
    overhaul_records: EvidenceValue


class DecisionOverviewView(BaseModel):
    scope: DecisionScopeView
    data_maturity: DataMaturityView
    window_days: Literal[7, 30, 90]
    window_start: datetime
    as_of: datetime
    summary: DecisionSummaryView
    maintenance_activity: list[ActivityTrendView]
    status_distribution: list[DistributionView]
    work_type_distribution: list[DistributionView]
    activity_concentration: list[ActivityConcentrationView]
    record_availability: RecordAvailabilityView
    integrity: IntegrityView


class AssetHealthScopeView(BaseModel):
    site_code: Literal["BSR"]
    organization_code: Literal["IP"]
    registry_scope: str
    population: Literal["CONTROLLED_MART_POPULATION"]
    interpretation: Literal["ASSESSMENT_RECORDS_NOT_HEALTH_SCORE"]


class AssetHealthSummaryView(BaseModel):
    assessment_records: int
    records_with_asset_ref: int
    records_without_asset_ref: int
    asset_master_resolved: int
    registry_resolved: int
    technical_non_registry_records: int
    unresolved_asset_refs: int
    registered_assets_represented: int
    assets_with_multiple_records: int
    maximum_records_per_asset: int


class AssetHealthRecencyView(BaseModel):
    oldest_record_at: datetime | None = None
    latest_record_at: datetime | None = None
    as_of: datetime
    latest_assessment_age_days: float | None = None
    date_basis: str


class AssetHealthEvidenceView(BaseModel):
    assessment_records: EvidenceClass
    registered_assets_represented: EvidenceClass
    assets_with_multiple_records: EvidenceClass
    latest_assessment_record: EvidenceClass
    assessment_age: EvidenceClass
    lifecycle_status: EvidenceClass
    health_score: EvidenceClass
    wellness_score: EvidenceClass
    condition_classification: EvidenceClass


class AssetHealthOverviewView(BaseModel):
    scope: AssetHealthScopeView
    summary: AssetHealthSummaryView
    status_distribution: list[DistributionView]
    record_recency: AssetHealthRecencyView
    evidence: AssetHealthEvidenceView


class FmeaScopeView(BaseModel):
    site_code: Literal["BSR"]
    organization_code: Literal["IP"]
    registry_scope: str
    population: Literal["CONTROLLED_MART_POPULATION"]
    interpretation: Literal["ASSESSMENT_RECORDS_NOT_RISK_SCORE"]


class FmeaSummaryView(BaseModel):
    fmea_records: int
    records_with_asset_ref: int
    records_without_asset_ref: int
    asset_master_resolved: int
    registry_resolved: int
    technical_non_registry_records: int
    unresolved_asset_refs: int
    registered_assets_represented: int
    assets_with_multiple_records: int
    maximum_records_per_asset: int
    records_with_failure_code: int
    record_date_available: int


class FmeaRecencyView(BaseModel):
    oldest_record_at: datetime | None = None
    latest_record_at: datetime | None = None
    as_of: datetime
    latest_fmea_age_days: float | None = None
    date_basis: str


class FmeaEvidenceView(BaseModel):
    fmea_records: EvidenceClass
    registered_assets_represented: EvidenceClass
    assets_with_multiple_records: EvidenceClass
    records_with_failure_code: EvidenceClass
    fmea_record_age: EvidenceClass
    lifecycle_status: EvidenceClass
    revision: EvidenceClass
    failure_mode_details: EvidenceClass
    rpn: EvidenceClass
    risk_classification: EvidenceClass


class FmeaOverviewView(BaseModel):
    scope: FmeaScopeView
    summary: FmeaSummaryView
    status_distribution: list[DistributionView]
    revision_distribution: list[DistributionView]
    record_recency: FmeaRecencyView
    evidence: FmeaEvidenceView


class RcfaScopeView(BaseModel):
    site_code: Literal["BSR"]
    organization_code: Literal["IP"]
    population: Literal["CONTROLLED_MART_POPULATION"]
    asset_relationship: Literal["UNRESOLVED"]
    workorder_relationship: Literal["UNRESOLVED"]
    failure_event_relationship: Literal["UNRESOLVED"]
    interpretation: Literal["GLOBAL_RCFA_RECORDS"]


class RcfaSummaryView(BaseModel):
    rcfa_records: int
    records_with_category: int
    records_with_revision: int
    records_with_requested_at: int
    records_with_source_created_at: int
    record_date_available: int


class RcfaRecencyView(BaseModel):
    oldest_record_at: datetime | None = None
    latest_record_at: datetime | None = None
    as_of: datetime
    latest_rcfa_age_days: float | None = None
    date_basis: str


class RcfaEvidenceView(BaseModel):
    rcfa_records: EvidenceClass
    rcfa_number: EvidenceClass
    revision: EvidenceClass
    lifecycle_status: EvidenceClass
    category: EvidenceClass
    rcfa_record_age: EvidenceClass
    request_to_created_gap: EvidenceClass
    category_taxonomy: EvidenceClass
    asset_relationship: EvidenceClass
    workorder_relationship: EvidenceClass
    failure_event_relationship: EvidenceClass
    root_cause_details: EvidenceClass
    root_cause_taxonomy: EvidenceClass
    rcfa_completion: EvidenceClass


class RcfaOverviewView(BaseModel):
    scope: RcfaScopeView
    summary: RcfaSummaryView
    status_distribution: list[DistributionView]
    category_distribution: list[DistributionView]
    revision_distribution: list[DistributionView]
    record_recency: RcfaRecencyView
    evidence: RcfaEvidenceView


class OverhaulScopeView(BaseModel):
    site_code: Literal["BSR"]
    organization_code: Literal["IP"]
    population: Literal["CONTROLLED_MART_POPULATION"]
    workorder_relationship: Literal["DIRECT_VERIFIED"]
    asset_relationship: Literal["DERIVED_VIA_WORK_ORDER"]
    interpretation: Literal["OVERHAUL_RECORDS_NOT_PERFORMANCE_SCORE"]


class OverhaulSummaryView(BaseModel):
    overhaul_records: int
    source_record_id_present: int
    source_number_present: int
    records_with_work_order: int
    work_orders_resolved_in_mart: int
    work_orders_unresolved_in_mart: int
    source_work_order_number_available: int
    work_order_source_missing: int
    records_with_asset: int
    asset_master_resolved: int
    registered_assets_resolved: int
    technical_non_registry: int
    asset_ref_absent: int
    asset_refs_unresolved: int
    planned_start_present: int
    planned_finish_present: int
    actual_start_present: int
    actual_finish_present: int
    planned_duration_available: int
    actual_duration_available: int
    records_with_progress: int
    inspection_number_present: int
    performance_test_present: int


class OverhaulDateAvailabilityView(BaseModel):
    planned_start_present: int
    planned_finish_present: int
    actual_start_present: int
    actual_finish_present: int
    planned_duration_available: int
    actual_duration_available: int


class OverhaulRelationshipIntegrityView(BaseModel):
    workorder_refs_present: int
    workorder_refs_resolved_in_mart: int
    workorder_refs_unresolved_in_mart: int
    workorder_source_missing: int
    asset_refs_present: int
    asset_refs_resolved_to_asset_master: int
    registered_assets_resolved: int
    technical_non_registry: int
    asset_refs_unresolved: int


class OverhaulEvidenceView(BaseModel):
    overhaul_records: EvidenceClass
    overhaul_number: EvidenceClass
    workorder_source_relationship: EvidenceClass
    workorder_mart_resolution: EvidenceClass
    asset_derived_relationship: EvidenceClass
    lifecycle_status: EvidenceClass
    planned_duration: EvidenceClass
    actual_duration: EvidenceClass
    progress_value: EvidenceClass
    progress_scale: EvidenceClass
    schedule_variance: EvidenceClass
    overhaul_completion: EvidenceClass
    inspection_number: EvidenceClass
    inspection_relationship: EvidenceClass
    performance_test: EvidenceClass
    performance_test_semantics: EvidenceClass


class OverhaulOverviewView(BaseModel):
    scope: OverhaulScopeView
    summary: OverhaulSummaryView
    status_distribution: list[DistributionView]
    date_availability: OverhaulDateAvailabilityView
    relationship_integrity: OverhaulRelationshipIntegrityView
    evidence: OverhaulEvidenceView


class InvestigationScopeView(BaseModel):
    site_code: Literal["BSR"]
    organization_code: Literal["IP"]
    registry_scope: str
    date_basis: str
    interpretation: Literal["ACTIVITY_NOT_FAILURE"]


class InvestigationWindowView(BaseModel):
    days: Literal[30, 90, 180]
    start: datetime
    as_of: datetime


class InvestigationSummaryView(BaseModel):
    registered_assets: int
    maintenance_events: int
    assets_with_activity: int
    assets_with_2plus_events: int
    assets_with_3plus_events: int
    repeat_activity_events: int


class InvestigationAssetView(BaseModel):
    asset_ref: str
    source_asset_number: str
    description: str | None = None
    event_count: int
    repeat_activity_events: int
    latest_activity: datetime | None = None
    previous_activity: datetime | None = None
    latest_gap_days: float | None = None
    minimum_gap_days: float | None = None
    latest_work_type: str | None = None
    dominant_work_type: str | None = None


class InvestigationEvidenceView(BaseModel):
    repeat_activity: Literal["DERIVED_SAFE"]
    work_type_source: str
    activity_date: str
    repeat_failure: Literal["BUSINESS_SEMANTICS_REQUIRED"]


class MaintenanceInvestigationView(BaseModel):
    scope: InvestigationScopeView
    window: InvestigationWindowView
    summary: InvestigationSummaryView
    assets: list[InvestigationAssetView]
    meta: PageMeta
    evidence: InvestigationEvidenceView


class ContextView(BaseModel):
    asset: AssetView
    maintenance: list[MaintenanceView]
    fmea: list[FmeaView]
    health: list[HealthView]
    overhauls: list[OverhaulView]
    rcfa_relationship_status: Literal["UNRESOLVED"]
    relationship_health: IntegrityView


def _db() -> MartDatabase:
    try:
        database = get_mart_database()
        if not database.healthcheck():
            raise MartDatabaseConfigError("Reliability Mart health check failed")
        return database
    except (MartDatabaseConfigError, ValueError, SQLAlchemyError) as error:
        raise HTTPException(status_code=503, detail="Reliability Mart is unavailable") from error


def _service(db: MartDatabase = Depends(_db)) -> ReliabilityQueryService:
    return ReliabilityQueryService(MartQueryRepository(db))


def _page(page: QueryPage, converter) -> dict:
    return {"items": [converter(item) for item in page.items], "meta": PageMeta(total=page.total, offset=page.offset, limit=page.limit, has_more=page.has_more)}


def _asset(row) -> AssetView:
    return AssetView.model_validate({k: getattr(row, k) for k in AssetView.model_fields})


def _mapping_candidate(mapping: AssetAfMapping) -> AssetAfMappingCandidateView:
    return AssetAfMappingCandidateView(
        mapping_id=mapping.id,
        mapping_status=mapping.mapping_status,
        mapping_role=mapping.mapping_role,
        evidence_method=mapping.evidence_method,
        verified_at=mapping.verified_at,
        retired_at=mapping.retired_at,
        pi_af=PiAfReferenceView(
            pi_source_id=mapping.pi_source_id,
            af_server_ref=mapping.af_server_ref,
            af_database_ref=mapping.af_database_ref,
            af_element_ref=mapping.af_element_ref,
            af_path_snapshot=mapping.af_path_snapshot,
            af_element_name_snapshot=mapping.af_element_name_snapshot,
        ),
    )


def _mapping_response(resolution: AssetAfMappingResolution) -> AssetAfMappingResponse:
    selected = _mapping_candidate(resolution.selected) if resolution.selected else None
    return AssetAfMappingResponse(
        asset_id=resolution.asset_id,
        mapping_state=resolution.mapping_state,
        pi_af=selected.pi_af if selected else None,
        candidates=[_mapping_candidate(mapping) for mapping in resolution.candidates],
    )


def _maintenance(row) -> MaintenanceView:
    # Expose only reviewed scalar fields, never the vendor JSON or provenance.
    source = row.sources if isinstance(row.sources, dict) else {}
    maximo = source.get("maximo")
    maximo = maximo if isinstance(maximo, dict) else {}
    value = maximo.get("worktype")
    raw = value if isinstance(value, str) and value.strip() else None
    canonical = row.event_type if isinstance(row.event_type, str) and row.event_type.strip() else None
    state = ("CANONICAL_SUPPORTED" if canonical else "UNMAPPED") if raw else ("CANONICAL_ONLY" if canonical else "MISSING_RETAINED_TYPE")
    classification = WorkClassificationView(
        raw_work_type=raw, canonical_category=canonical, state=state,
        origin="RETAINED_MAXIMO_WORKTYPE" if raw else "CANONICAL_EVENT_TYPE" if canonical else "NOT_AVAILABLE",
        confidence="VERIFIED" if raw and canonical == raw else "UNRESOLVED",
        status_state="AVAILABLE" if isinstance(row.status, str) and row.status.strip() else "MISSING_RETAINED_STATUS",
    )
    def scalar(key: str) -> str | None:
        value = maximo.get(key)
        return value if isinstance(value, str) and value.strip() and len(value) <= 200 else None

    def clock(key: str) -> str | None:
        value = scalar(key)
        if value is None or not re.fullmatch(
            r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?(?:Z|[+-](?:[01][0-9]|2[0-3]):[0-5][0-9])?", value
        ):
            return None
        try:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        # Preserve the original offset, fractional precision and naive clocks.
        return value

    detail = MaintenanceSourceDetailView(
        work_order_number=scalar("wonum"), asset_number=scalar("assetnum"),
        reported_at=clock("reportdate"), scheduled_start=clock("schedstart"),
        scheduled_finish=clock("schedfinish"),
    )
    return MaintenanceView.model_validate({
        **{k: getattr(row, k) for k in MaintenanceView.model_fields if k not in {"classification", "source_detail"}},
        "classification": classification, "source_detail": detail,
    })


def _fmea(row) -> FmeaView:
    return FmeaView.model_validate({k: getattr(row, k, None) for k in FmeaView.model_fields})


def _rcfa(row) -> RcfaView:
    return RcfaView.model_validate({k: getattr(row, k) for k in RcfaView.model_fields if hasattr(row, k)})


def _health(row) -> HealthView:
    return HealthView.model_validate({k: getattr(row, k, None) for k in HealthView.model_fields})


def _source_attribute(row, key: str) -> str | None:
    sources = getattr(row, "sources", None) or {}
    maximo = sources.get("maximo") if isinstance(sources, dict) else None
    value = maximo.get(key) if isinstance(maximo, dict) else None
    return str(value) if value not in (None, "") else None


def _overhaul(row) -> OverhaulView:
    workorder_ref = getattr(row, "workorder_ref", None)
    asset_ref = getattr(row, "asset_ref", None)
    values = {
        key: getattr(row, key)
        for key in OverhaulView.model_fields
        if key not in {"unresolved_attributes_present", "source_work_order_number", "source_asset_number", "asset_description", "work_order_resolution", "asset_resolution"}
        and hasattr(row, key)
    }
    values.update({
        "source_work_order_number": getattr(row, "source_work_order_number", None) or _source_attribute(row, "wonum"),
        "source_asset_number": getattr(row, "source_asset_number", None),
        "asset_description": getattr(row, "asset_description", None),
        "work_order_resolution": getattr(
            row,
            "work_order_resolution",
            "SOURCE_LINK_VERIFIED_BUT_MART_UNRESOLVED" if workorder_ref else "SOURCE_WORK_ORDER_MISSING",
        ),
        "asset_resolution": getattr(
            row,
            "asset_resolution",
            "ASSET_RESOLVED_REGISTERED" if asset_ref else "ASSET_UNRESOLVED",
        ),
        "unresolved_attributes_present": bool(getattr(row, "unresolved_source_attributes", None)),
    })
    return OverhaulView.model_validate(values)


def _timeline(row: TimelineEvent) -> TimelineView:
    return TimelineView.model_validate(row.__dict__)


def _validate_range(start: datetime | None, end: datetime | None) -> None:
    if start and end and start > end:
        raise HTTPException(status_code=422, detail="date range start must not be after end")


def _evidence(value: int, evidence_class: EvidenceClass) -> EvidenceValue:
    return EvidenceValue(value=value, evidence_class=evidence_class)


def _decision_overview(raw: dict[str, object], window_days: int) -> DecisionOverviewView:
    summary = raw["summary"]
    records = raw["records"]
    assert isinstance(summary, dict)
    assert isinstance(records, dict)
    return DecisionOverviewView(
        scope=DecisionScopeView(
            site_code="BSR",
            organization_code="IP",
            registry_scope="reliability_asset_registry",
            maintenance_source="Local Collector → Reliability Mart",
            date_basis="COALESCE(actual_start, source_changed_at)",
        ),
        data_maturity=DataMaturityView(
            asset_maintenance="CURRENT LOCAL PROJECTION",
            controlled_domains="CONTROLLED MART POPULATION",
            rcfa_relationship="RELATIONSHIP UNRESOLVED",
            technical_context="TECHNICAL CONTEXT",
        ),
        window_days=window_days,
        window_start=raw["window_start"],
        as_of=raw["as_of"],
        summary=DecisionSummaryView(
            registered_assets=_evidence(int(raw["registered_assets"]), "VERIFIED"),
            maintenance_activity_7d=_evidence(int(summary["maintenance_activity_7d"]), "DERIVED_SAFE"),
            maintenance_activity_30d=_evidence(int(summary["maintenance_activity_30d"]), "DERIVED_SAFE"),
            maintenance_activity_90d=_evidence(int(summary["maintenance_activity_90d"]), "DERIVED_SAFE"),
            assets_active_7d=_evidence(int(summary["assets_active_7d"]), "DERIVED_SAFE"),
            assets_active_30d=_evidence(int(summary["assets_active_30d"]), "DERIVED_SAFE"),
            assets_active_90d=_evidence(int(summary["assets_active_90d"]), "DERIVED_SAFE"),
        ),
        maintenance_activity=[
            ActivityTrendView(
                period_start=row["period_start"],
                period_end=row["period_end"],
                event_count=_evidence(int(row["event_count"]), "DERIVED_SAFE"),
            )
            for row in raw["trend"]
        ],
        status_distribution=[
            DistributionView(value=row["value"], count=_evidence(int(row["count"]), "DERIVED_SAFE"))
            for row in raw["status_distribution"]
        ],
        work_type_distribution=[
            DistributionView(value=row["value"], count=_evidence(int(row["count"]), "DERIVED_SAFE"))
            for row in raw["work_type_distribution"]
        ],
        activity_concentration=[
            ActivityConcentrationView(
                asset_ref=row["asset_ref"],
                source_asset_number=row["source_asset_number"],
                description=row["description"],
                event_count=_evidence(int(row["event_count"]), "DERIVED_SAFE"),
                latest_activity=row["latest_activity"],
            )
            for row in raw["activity_concentration"]
        ],
        record_availability=RecordAvailabilityView(
            fmea_records=_evidence(int(records["fmea_records"]), "VERIFIED"),
            fmea_assets_represented=_evidence(int(records["fmea_assets_represented"]), "DERIVED_SAFE"),
            asset_health_records=_evidence(int(records["asset_health_records"]), "VERIFIED"),
            asset_health_assets_represented=_evidence(int(records["asset_health_assets_represented"]), "DERIVED_SAFE"),
            rcfa_records=_evidence(int(records["rcfa_records"]), "VERIFIED"),
            overhaul_records=_evidence(int(records["overhaul_records"]), "VERIFIED"),
        ),
        integrity=IntegrityView(**raw["integrity"]),
    )


def _maintenance_investigation(raw: dict[str, object]) -> MaintenanceInvestigationView:
    return MaintenanceInvestigationView(
        scope=InvestigationScopeView(**raw["scope"]),
        window=InvestigationWindowView(**raw["window"]),
        summary=InvestigationSummaryView(**raw["summary"]),
        assets=[InvestigationAssetView(**row) for row in raw["assets"]],
        meta=PageMeta(**raw["meta"]),
        evidence=InvestigationEvidenceView(**raw["evidence"]),
    )


def _asset_health_overview(raw: dict[str, object]) -> AssetHealthOverviewView:
    return AssetHealthOverviewView(
        scope=AssetHealthScopeView(**raw["scope"]),
        summary=AssetHealthSummaryView(**raw["summary"]),
        status_distribution=[
            DistributionView(value=row["value"], count=_evidence(int(row["count"]), "VERIFIED"))
            for row in raw["status_distribution"]
        ],
        record_recency=AssetHealthRecencyView(**raw["record_recency"]),
        evidence=AssetHealthEvidenceView(**raw["evidence"]),
    )


def _fmea_overview(raw: dict[str, object]) -> FmeaOverviewView:
    return FmeaOverviewView(
        scope=FmeaScopeView(**raw["scope"]),
        summary=FmeaSummaryView(**raw["summary"]),
        status_distribution=[
            DistributionView(value=row["value"], count=_evidence(int(row["count"]), "VERIFIED"))
            for row in raw["status_distribution"]
        ],
        revision_distribution=[
            DistributionView(value=row["value"], count=_evidence(int(row["count"]), "VERIFIED"))
            for row in raw["revision_distribution"]
        ],
        record_recency=FmeaRecencyView(**raw["record_recency"]),
        evidence=FmeaEvidenceView(**raw["evidence"]),
    )


def _rcfa_overview(raw: dict[str, object]) -> RcfaOverviewView:
    def distribution(rows):
        return [DistributionView(value=row["value"], count=_evidence(int(row["count"]), "VERIFIED")) for row in rows]

    return RcfaOverviewView(
        scope=RcfaScopeView(**raw["scope"]),
        summary=RcfaSummaryView(**raw["summary"]),
        status_distribution=distribution(raw["status_distribution"]),
        category_distribution=distribution(raw["category_distribution"]),
        revision_distribution=distribution(raw["revision_distribution"]),
        record_recency=RcfaRecencyView(**raw["record_recency"]),
        evidence=RcfaEvidenceView(**raw["evidence"]),
    )


def _overhaul_overview(raw: dict[str, object]) -> OverhaulOverviewView:
    return OverhaulOverviewView(
        scope=OverhaulScopeView(**raw["scope"]),
        summary=OverhaulSummaryView(**raw["summary"]),
        status_distribution=[
            DistributionView(value=row["value"], count=_evidence(int(row["count"]), "VERIFIED"))
            for row in raw["status_distribution"]
        ],
        date_availability=OverhaulDateAvailabilityView(**raw["date_availability"]),
        relationship_integrity=OverhaulRelationshipIntegrityView(**raw["relationship_integrity"]),
        evidence=OverhaulEvidenceView(**raw["evidence"]),
    )


def _data_trust(raw: dict[str, object]) -> DataTrustView:
    return DataTrustView(
        scope=DataTrustScopeView(**raw["scope"]),
        population=DataTrustPopulationView(**raw["population"]),
        domains=[DataTrustDomainView(**row) for row in raw["domains"]],
        relationships=[DataTrustRelationshipView(**row) for row in raw["relationships"]],
        semantic_readiness=[DataTrustReadinessView(**row) for row in raw["semantic_readiness"]],
        integrity=IntegrityView(**raw["integrity"]),
        limitations=list(raw["limitations"]),
    )


@router.get("/assets", response_model=Page[AssetView], summary="List Reliability Mart assets")
def list_assets(
    status: str | None = None,
    unit: str | None = None,
    asset_type: str | None = None,
    site_code: Literal["BSR"] = "BSR",
    organization_code: Literal["IP"] = "IP",
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    sort: Literal["updated_desc", "updated_asc", "status"] = "updated_desc",
    service: ReliabilityQueryService = Depends(_service),
):
    page = service.repository.list_assets(status=status, unit=unit, asset_type=asset_type, offset=offset, limit=limit, sort=sort)
    return _page(page, _asset)


@router.get("/registry", response_model=RegistryView, summary="Current registered Reliability Asset snapshot")
def registry(service: ReliabilityQueryService = Depends(_service)) -> RegistryView:
    return RegistryView(**service.repository.registry_summary())


@router.get("/registered-maintenance-overview", response_model=RegisteredMaintenanceOverview, summary="Registry BSR/IP Asset and retained WO summary only")
def registered_maintenance_overview(service: ReliabilityQueryService = Depends(_service)) -> RegisteredMaintenanceOverview:
    return RegisteredMaintenanceOverview(**service.repository.registered_maintenance_overview())


@router.get("/decision-overview", response_model=DecisionOverviewView, summary="Bounded factual Reliability decision overview")
def decision_overview(
    window_days: int = Query(30, json_schema_extra={"enum": [7, 30, 90]}),
    service: ReliabilityQueryService = Depends(_service),
) -> DecisionOverviewView:
    if window_days not in {7, 30, 90}:
        raise HTTPException(status_code=422, detail="window_days must be one of 7, 30, or 90")
    return _decision_overview(service.repository.decision_overview(window_days=window_days), window_days)


@router.get("/asset-health/overview", response_model=AssetHealthOverviewView, summary="Factual Asset Health assessment overview")
def asset_health_overview(service: ReliabilityQueryService = Depends(_service)) -> AssetHealthOverviewView:
    return _asset_health_overview(service.repository.asset_health_overview())


@router.get("/fmea/overview", response_model=FmeaOverviewView, summary="Factual FMEA assessment overview")
def fmea_overview(service: ReliabilityQueryService = Depends(_service)) -> FmeaOverviewView:
    return _fmea_overview(service.repository.fmea_overview())


@router.get("/rcfa/overview", response_model=RcfaOverviewView, summary="Global factual RCFA overview")
def rcfa_overview(service: ReliabilityQueryService = Depends(_service)) -> RcfaOverviewView:
    return _rcfa_overview(service.repository.rcfa_overview())


@router.get("/maintenance-investigation", response_model=MaintenanceInvestigationView, summary="Bounded repeat maintenance activity investigation")
def maintenance_investigation(
    window_days: int = Query(90, json_schema_extra={"enum": [30, 90, 180]}),
    min_events: int = Query(2, json_schema_extra={"enum": [2, 3, 5]}),
    offset: int = Query(0, ge=0),
    limit: int = Query(25, ge=1, le=100),
    sort: Literal["event_count_desc", "latest_activity_desc", "latest_gap_asc"] = "event_count_desc",
    service: ReliabilityQueryService = Depends(_service),
) -> MaintenanceInvestigationView:
    if window_days not in {30, 90, 180}:
        raise HTTPException(status_code=422, detail="window_days must be one of 30, 90, or 180")
    if min_events not in {2, 3, 5}:
        raise HTTPException(status_code=422, detail="min_events must be one of 2, 3, or 5")
    return _maintenance_investigation(service.repository.maintenance_investigation(window_days=window_days, min_events=min_events, offset=offset, limit=limit, sort=sort))


@router.get("/assets/{canonical_id}", response_model=AssetView)
def get_asset(canonical_id: str, service: ReliabilityQueryService = Depends(_service)) -> AssetView:
    row = service.repository.get_asset(canonical_id)
    if row is None:
        raise HTTPException(status_code=404, detail="asset not found")
    return _asset(row)


@router.get("/assets/{canonical_id}/condition-evidence", response_model=AssetConditionEvidence)
def asset_condition_evidence(canonical_id: str, db: MartDatabase = Depends(_db)) -> AssetConditionEvidence:
    response = ConditionQueryService(db).asset_evidence(canonical_id)
    if response is None:
        raise HTTPException(status_code=404, detail="asset not found")
    return response


@router.get("/assets/{canonical_id}/pi-mapping", response_model=AssetAfMappingResponse)
def asset_af_mapping(canonical_id: str, service: ReliabilityQueryService = Depends(_service)) -> AssetAfMappingResponse:
    if service.repository.get_asset(canonical_id) is None:
        raise HTTPException(status_code=404, detail="asset not found")
    try:
        return _mapping_response(service.asset_af_mapping(canonical_id))
    except SQLAlchemyError as error:
        raise HTTPException(status_code=503, detail="Asset to PI AF mapping registry is unavailable") from error


@router.get("/assets/{canonical_id}/context", response_model=ContextView)
def asset_context(canonical_id: str, service: ReliabilityQueryService = Depends(_service)) -> ContextView:
    context = service.asset_context(canonical_id)
    if context is None:
        raise HTTPException(status_code=404, detail="asset not found")
    return ContextView(
        asset=_asset(context["asset"]),
        maintenance=[_maintenance(row) for row in context["maintenance"].items],
        fmea=[_fmea(row) for row in context["fmea"].items],
        health=[_health(row) for row in context["health"].items],
        overhauls=[_overhaul(row) for row in context["overhauls"].items],
        rcfa_relationship_status=context["rcfa_relationship_status"],
        relationship_health=IntegrityView(**context["relationship_health"]),
    )


@router.get("/assets/{canonical_id}/fmea", response_model=Page[FmeaView])
def asset_fmea(canonical_id: str, offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200), service: ReliabilityQueryService = Depends(_service)):
    if service.repository.get_asset(canonical_id) is None:
        raise HTTPException(status_code=404, detail="asset not found")
    return _page(service.repository.list_fmea_workspace(asset_ref=canonical_id, offset=offset, limit=limit), _fmea)


@router.get("/assets/{canonical_id}/health-assessments", response_model=Page[HealthView])
def asset_health(canonical_id: str, offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200), service: ReliabilityQueryService = Depends(_service)):
    if service.repository.get_asset(canonical_id) is None:
        raise HTTPException(status_code=404, detail="asset not found")
    return _page(service.repository.list_health_workspace(asset_ref=canonical_id, offset=offset, limit=limit), _health)


@router.get("/assets/{canonical_id}/health/latest", response_model=HealthView)
def latest_health(canonical_id: str, service: ReliabilityQueryService = Depends(_service)) -> HealthView:
    if service.repository.get_asset(canonical_id) is None:
        raise HTTPException(status_code=404, detail="asset not found")
    row = service.repository.latest_health_workspace(canonical_id)
    if row is None:
        raise HTTPException(status_code=404, detail="health assessment not found")
    return _health(row)


@router.get("/assets/{canonical_id}/timeline", response_model=Page[TimelineView])
def asset_timeline(canonical_id: str, offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200), service: ReliabilityQueryService = Depends(_service)):
    if service.repository.get_asset(canonical_id) is None:
        raise HTTPException(status_code=404, detail="asset not found")
    return _page(service.timeline(canonical_id, offset=offset, limit=limit), _timeline)


@router.get("/maintenance-events", response_model=Page[MaintenanceView])
def maintenance_events(
    asset_ref: str | None = None, work_order_id: str | None = None, status: str | None = None, event_type: str | None = None,
    date_from: datetime | None = None, date_to: datetime | None = None, offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200),
    sort: Literal["date_desc", "date_asc", "status"] = "date_desc", service: ReliabilityQueryService = Depends(_service),
):
    _validate_range(date_from, date_to)
    return _page(service.repository.list_maintenance(asset_ref=asset_ref, work_order_id=work_order_id, status=status, event_type=event_type, date_from=date_from, date_to=date_to, offset=offset, limit=limit, sort=sort), _maintenance)


@router.get("/fmea", response_model=Page[FmeaView])
def fmea(asset_ref: str | None = None, asset_number: str | None = None, lifecycle_status: str | None = None, source_number: str | None = None, source_failure_code: str | None = None, updated_from: datetime | None = None, updated_to: datetime | None = None, offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200), sort: Literal["updated_desc", "updated_asc", "status"] = "updated_desc", service: ReliabilityQueryService = Depends(_service)):
    _validate_range(updated_from, updated_to)
    return _page(service.repository.list_fmea_workspace(asset_ref=asset_ref, asset_number=asset_number, lifecycle_status=lifecycle_status, source_number=source_number, source_failure_code=source_failure_code, updated_from=updated_from, updated_to=updated_to, offset=offset, limit=limit, sort=sort), _fmea)


@router.get("/asset-health", response_model=Page[HealthView])
def asset_health_list(asset_ref: str | None = None, asset_number: str | None = None, description: str | None = None, lifecycle_status: str | None = None, updated_from: datetime | None = None, updated_to: datetime | None = None, offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200), sort: Literal["updated_desc", "updated_asc", "status"] = "updated_desc", service: ReliabilityQueryService = Depends(_service)):
    _validate_range(updated_from, updated_to)
    return _page(service.repository.list_health_workspace(asset_ref=asset_ref, asset_number=asset_number, description=description, lifecycle_status=lifecycle_status, updated_from=updated_from, updated_to=updated_to, offset=offset, limit=limit, sort=sort), _health)


@router.get("/rcfa", response_model=Page[RcfaView])
def rcfa(lifecycle_status: str | None = None, category: str | None = None, source_number: str | None = None, asset_ref: str | None = None, created_from: datetime | None = None, created_to: datetime | None = None, offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200), sort: Literal["created_desc", "created_asc", "status"] = "created_desc", service: ReliabilityQueryService = Depends(_service)):
    if asset_ref is not None:
        raise HTTPException(status_code=422, detail="asset_ref filter is unavailable because RCFA asset relationship is unresolved")
    _validate_range(created_from, created_to)
    return _page(service.repository.list_rcfa_workspace(lifecycle_status=lifecycle_status, category=category, source_number=source_number, created_from=created_from, created_to=created_to, offset=offset, limit=limit, sort=sort), _rcfa)


@router.get("/overhauls/overview", response_model=OverhaulOverviewView, summary="Factual Overhaul execution overview")
def overhaul_overview(service: ReliabilityQueryService = Depends(_service)) -> OverhaulOverviewView:
    return _overhaul_overview(service.repository.overhaul_overview())


@router.get("/overhauls", response_model=Page[OverhaulView])
def overhauls(source_number: str | None = None, asset_ref: str | None = None, workorder_ref: str | None = None, source_work_order_number: str | None = None, lifecycle_status: str | None = None, planned_from: datetime | None = None, planned_to: datetime | None = None, actual_from: datetime | None = None, actual_to: datetime | None = None, offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200), sort: Literal["date_desc", "date_asc", "status"] = "date_desc", service: ReliabilityQueryService = Depends(_service)):
    _validate_range(planned_from, planned_to)
    _validate_range(actual_from, actual_to)
    return _page(service.repository.list_overhaul_workspace(source_number=source_number, asset_ref=asset_ref, workorder_ref=workorder_ref, source_work_order_number=source_work_order_number, lifecycle_status=lifecycle_status, planned_from=planned_from, planned_to=planned_to, actual_from=actual_from, actual_to=actual_to, offset=offset, limit=limit, sort=sort), _overhaul)


@router.get("/data-trust", response_model=DataTrustView, summary="Factual NADI Data Trust Center evidence")
def data_trust(service: ReliabilityQueryService = Depends(_service)) -> DataTrustView:
    return _data_trust(service.repository.data_trust_overview())


@router.get("/integrity", response_model=IntegrityView)
def integrity(service: ReliabilityQueryService = Depends(_service)) -> IntegrityView:
    return IntegrityView(**service.repository.integrity_summary())


def _integration_service():
    from src.services.integration_status import IntegrationStatusService
    try:
        database=get_mart_database()
    except (MartDatabaseConfigError, ValueError, SQLAlchemyError):
        database=None
    return IntegrationStatusService(database)

from src.domain.integration_status import IntegrationStatus

@router.get("/integration-status",response_model=IntegrationStatus)
def integration_status():
    return _integration_service().status()

@router.get("/assets/{canonical_id:path}/integration-status",response_model=IntegrationStatus)
def asset_integration_status(canonical_id: str):
    service=_integration_service()
    if service.database is not None:
        try:
            if MartQueryRepository(service.database).get_asset(canonical_id) is None:
                raise HTTPException(status_code=404,detail="registered asset not found")
        except SQLAlchemyError:
            pass
    return service.status(canonical_id)
