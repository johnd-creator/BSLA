"use client";

/** Typed clients for the legacy Cockpit store and canonical Reliability Mart. */

export interface EquipmentView {
  id: string;
  name: string | null;
  location_id: string | null;
  equipment_class: string | null;
  unit: string | null;
  status: string | null;
  status_description: string | null;
  is_running: boolean | null;
  parent_id: string | null;
  ancestor_id: string | null;
  downtime_total_hours: number | null;
}

export interface WorkOrderView {
  id: string;
  equipment_id: string | null;
  status: string | null;
  work_type: string | null;
  description: string | null;
  reported_at: string | null;
  downtime_hours: number | null;
  failure_code: string | null;
}

export interface WorkOrderPage { items: WorkOrderView[]; total: number; offset: number; limit: number; has_more: boolean; }
export interface ReliabilityKpiView { id: string; equipment_id: string | null; metric: string | null; value: number | null; unit: string | null; period_start: string | null; period_end: string | null; }
export interface PageMeta { total: number; offset: number; limit: number; has_more: boolean; }
export interface Page<T> { items: T[]; meta: PageMeta; }

export interface AssetView {
  canonical_id: string; contract_version: string; source_asset_number: string | null; description: string | null; status: string | null;
  location_ref: string | null; parent_asset_ref: string | null; site_code: string; organization_code: string; asset_type: string | null;
  plant: string | null; unit: string | null; source_updated_at: string | null;
}
export interface WorkClassificationView {
  raw_work_type: string | null; canonical_category: string | null;
  state: 'CANONICAL_SUPPORTED' | 'UNMAPPED' | 'MISSING_RETAINED_TYPE' | 'CANONICAL_ONLY';
  origin: 'RETAINED_MAXIMO_WORKTYPE' | 'CANONICAL_EVENT_TYPE' | 'NOT_AVAILABLE';
  confidence: 'VERIFIED' | 'UNRESOLVED'; description: string | null;
  workflow_name: string | null; workflow_version: string | null; workflow_state: 'NOT_AVAILABLE';
  status_state: 'AVAILABLE' | 'MISSING_RETAINED_STATUS';
}
export interface MaintenanceEventView {
  classification?: WorkClassificationView | null;
  source_detail?: {work_order_number: string | null; asset_number: string | null; reported_at: string | null; scheduled_start: string | null; scheduled_finish: string | null} | null;
  canonical_id: string; contract_version: string; id: string; equipment_id: string; work_order_id: string | null; event_type: string | null;
  status: string | null; actual_start: string | null; actual_finish: string | null; duration_hours: number | null; labor_hours: number | null;
  downtime_hours: number | null; failure_code: string | null; source_changed_at: string | null; site_code: string; organization_code: string;
}
export interface FmeaView {
  canonical_id: string; contract_version: string; source_record_id: string | null; source_number: string | null; revision: string | null;
  lifecycle_status: string | null; description: string | null; asset_ref: string | null; failure_code_ref: string | null;
  site_code: string; organization_code: string; source_updated_at: string | null; status_changed_at: string | null;
  source_asset_number: string | null; asset_description: string | null; source_failure_code: string | null; fmea_record_date: string | null; fmea_age_days: number | null;
}
export interface RcfaView {
  canonical_id: string; contract_version: string; source_record_id: string | null; source_number: string | null; revision: string | null;
  lifecycle_status: string | null; category: string | null; asset_ref: string | null; location_ref: string | null; workorder_ref: string | null;
  failure_event_ref: string | null; site_code: string; organization_code: string; source_created_at: string | null; requested_at: string | null;
  rcfa_record_date: string | null; rcfa_age_days: number | null;
  relationship_status: "UNRESOLVED";
}
export interface AssetHealthView {
  canonical_id: string; contract_version: string; source_record_id: string | null; revision: string | null; lifecycle_status: string | null;
  description: string | null; function_description: string | null; asset_ref: string | null; site_code: string; organization_code: string;
  source_created_at: string | null; source_updated_at: string | null; status_changed_at: string | null;
  source_asset_number: string | null; asset_description: string | null; assessment_record_date: string | null; assessment_age_days: number | null;
}
export interface OverhaulView {
  canonical_id: string; contract_version: string; source_record_id: string | null; source_number: string | null; lifecycle_status: string | null;
  workorder_ref: string | null; source_work_order_number: string | null; asset_ref: string | null; source_asset_number: string | null; asset_description: string | null;
  work_order_resolution: "SOURCE_LINK_VERIFIED_AND_MART_RESOLVED" | "SOURCE_LINK_VERIFIED_BUT_MART_UNRESOLVED" | "SOURCE_WORK_ORDER_MISSING";
  asset_resolution: "ASSET_RESOLVED_REGISTERED" | "ASSET_RESOLVED_TECHNICAL_CONTEXT" | "ASSET_UNRESOLVED";
  site_code: string; organization_code: string; planned_start_at: string | null;
  planned_finish_at: string | null; actual_start_at: string | null; actual_finish_at: string | null; progress: unknown | null;
  unresolved_attributes_present: boolean;
}
export interface TimelineView {
  event_id: string;
  event_type: "MAINTENANCE" | "FMEA" | "ASSET_HEALTH" | "OVERHAUL";
  event_at: string | null;
  summary: string | null;
  status: string | null;
  canonical_ref: string;
}
export interface ContextView {
  asset: AssetView;
  maintenance: MaintenanceEventView[];
  fmea: FmeaView[];
  health: AssetHealthView[];
  overhauls: OverhaulView[];
  rcfa_relationship_status: "UNRESOLVED";
  relationship_health: IntegrityView;
}
export interface IntegrityView {
  asset_refs_total: number; asset_refs_resolved: number; asset_refs_unresolved: number;
  workorder_refs_total: number; workorder_refs_resolved: number; workorder_refs_unresolved: number;
  technical_asset_context_total: number; registered_assets_total: number; registered_assets_resolved: number;
  registered_assets_unresolved: number; maintenance_registered_total: number;
}
export interface RegistryView { registered_asset_count: number; snapshot_sha256: string | null; snapshot_row_count: number | null; snapshot_imported_at: string | null; source: string; }

export type EvidenceClass = "VERIFIED" | "DERIVED_SAFE" | "BUSINESS_SEMANTICS_REQUIRED" | "DATA_NOT_AVAILABLE" | "DEFERRED";
export interface EvidenceValue { value: number; evidence_class: EvidenceClass; }
export type DataTrustPopulationType = "LOCAL_COLLECTOR_PROJECTION" | "CONTROLLED_MART_POPULATION" | "BUSINESS_REGISTRY" | "TECHNICAL_CONTEXT";
export type DataTrustReadinessStatus = "AVAILABLE" | "BLOCKED" | "NOT_AVAILABLE" | "DEFERRED";
export interface DataTrustView {
  scope: { site_code: "BSR"; organization_code: "IP"; source_system: "MAXIMO"; registered_asset_boundary: string; sync_freshness: "NOT_AVAILABLE"; interpretation: string };
  population: {
    registered_reliability_assets: number; registry_resolved: number; registry_unresolved: number; technical_asset_context: number;
    maintenance_total: number; registry_maintenance: number; fmea: number; asset_health: number; rcfa: number; overhaul: number;
  };
  domains: {
    domain: "ASSET" | "MAINTENANCE" | "FMEA" | "ASSET_HEALTH" | "RCFA" | "OVERHAUL"; source_system: "MAXIMO"; source_object: string;
    population_type: DataTrustPopulationType; record_count: number; scoped_record_count: number | null; registered_assets_represented: number | null;
    business_scope: string; relationship_state: string; latest_record_date: string | null; date_basis: string; known_limitation: string; evidence_class: EvidenceClass;
  }[];
  relationships: {
    relationship: string; evidence: "VERIFIED" | "DIRECT_VERIFIED" | "DERIVED_VERIFIED_PATH" | "RESOLUTION_MEASURED" | "UNRESOLVED";
    resolved_count: number | null; unresolved_count: number | null; technical_context_count: number | null; interpretation: string;
  }[];
  semantic_readiness: { capability: string; evidence_class: EvidenceClass; status: DataTrustReadinessStatus; reason: string }[];
  integrity: IntegrityView;
  limitations: string[];
}
export interface AssetHealthOverviewView {
  scope: { site_code: "BSR"; organization_code: "IP"; registry_scope: string; population: "CONTROLLED_MART_POPULATION"; interpretation: "ASSESSMENT_RECORDS_NOT_HEALTH_SCORE" };
  summary: {
    assessment_records: number; records_with_asset_ref: number; records_without_asset_ref: number; asset_master_resolved: number;
    registry_resolved: number; technical_non_registry_records: number; unresolved_asset_refs: number; registered_assets_represented: number;
    assets_with_multiple_records: number; maximum_records_per_asset: number;
  };
  status_distribution: { value: string; count: EvidenceValue }[];
  record_recency: { oldest_record_at: string | null; latest_record_at: string | null; as_of: string; latest_assessment_age_days: number | null; date_basis: string };
  evidence: {
    assessment_records: EvidenceClass; registered_assets_represented: EvidenceClass; assets_with_multiple_records: EvidenceClass;
    latest_assessment_record: EvidenceClass; assessment_age: EvidenceClass; lifecycle_status: EvidenceClass; health_score: EvidenceClass;
    wellness_score: EvidenceClass; condition_classification: EvidenceClass;
  };
}
export interface FmeaOverviewView {
  scope: { site_code: "BSR"; organization_code: "IP"; registry_scope: string; population: "CONTROLLED_MART_POPULATION"; interpretation: "ASSESSMENT_RECORDS_NOT_RISK_SCORE" };
  summary: {
    fmea_records: number; records_with_asset_ref: number; records_without_asset_ref: number; asset_master_resolved: number;
    registry_resolved: number; technical_non_registry_records: number; unresolved_asset_refs: number; registered_assets_represented: number;
    assets_with_multiple_records: number; maximum_records_per_asset: number; records_with_failure_code: number; record_date_available: number;
  };
  status_distribution: { value: string; count: EvidenceValue }[];
  revision_distribution: { value: string; count: EvidenceValue }[];
  record_recency: { oldest_record_at: string | null; latest_record_at: string | null; as_of: string; latest_fmea_age_days: number | null; date_basis: string };
  evidence: {
    fmea_records: EvidenceClass; registered_assets_represented: EvidenceClass; assets_with_multiple_records: EvidenceClass;
    records_with_failure_code: EvidenceClass; fmea_record_age: EvidenceClass; lifecycle_status: EvidenceClass; revision: EvidenceClass;
    failure_mode_details: EvidenceClass; rpn: EvidenceClass; risk_classification: EvidenceClass;
  };
}
export interface RcfaOverviewView {
  scope: { site_code: "BSR"; organization_code: "IP"; population: "CONTROLLED_MART_POPULATION"; asset_relationship: "UNRESOLVED"; workorder_relationship: "UNRESOLVED"; failure_event_relationship: "UNRESOLVED"; interpretation: "GLOBAL_RCFA_RECORDS" };
  summary: { rcfa_records: number; records_with_category: number; records_with_revision: number; records_with_requested_at: number; records_with_source_created_at: number; record_date_available: number };
  status_distribution: { value: string; count: EvidenceValue }[];
  category_distribution: { value: string; count: EvidenceValue }[];
  revision_distribution: { value: string; count: EvidenceValue }[];
  record_recency: { oldest_record_at: string | null; latest_record_at: string | null; as_of: string; latest_rcfa_age_days: number | null; date_basis: string };
  evidence: {
    rcfa_records: EvidenceClass; rcfa_number: EvidenceClass; revision: EvidenceClass; lifecycle_status: EvidenceClass; category: EvidenceClass;
    rcfa_record_age: EvidenceClass; request_to_created_gap: EvidenceClass; category_taxonomy: EvidenceClass; asset_relationship: EvidenceClass;
    workorder_relationship: EvidenceClass; failure_event_relationship: EvidenceClass; root_cause_details: EvidenceClass; root_cause_taxonomy: EvidenceClass; rcfa_completion: EvidenceClass;
  };
}
export interface OverhaulOverviewView {
  scope: { site_code: "BSR"; organization_code: "IP"; population: "CONTROLLED_MART_POPULATION"; workorder_relationship: "DIRECT_VERIFIED"; asset_relationship: "DERIVED_VIA_WORK_ORDER"; interpretation: "OVERHAUL_RECORDS_NOT_PERFORMANCE_SCORE" };
  summary: {
    overhaul_records: number; source_record_id_present: number; source_number_present: number; records_with_work_order: number;
    work_orders_resolved_in_mart: number; work_orders_unresolved_in_mart: number; source_work_order_number_available: number; work_order_source_missing: number;
    records_with_asset: number; asset_master_resolved: number; registered_assets_resolved: number; technical_non_registry: number; asset_ref_absent: number; asset_refs_unresolved: number;
    planned_start_present: number; planned_finish_present: number; actual_start_present: number; actual_finish_present: number; planned_duration_available: number; actual_duration_available: number;
    records_with_progress: number; inspection_number_present: number; performance_test_present: number;
  };
  status_distribution: { value: string; count: EvidenceValue }[];
  date_availability: { planned_start_present: number; planned_finish_present: number; actual_start_present: number; actual_finish_present: number; planned_duration_available: number; actual_duration_available: number };
  relationship_integrity: { workorder_refs_present: number; workorder_refs_resolved_in_mart: number; workorder_refs_unresolved_in_mart: number; workorder_source_missing: number; asset_refs_present: number; asset_refs_resolved_to_asset_master: number; registered_assets_resolved: number; technical_non_registry: number; asset_refs_unresolved: number };
  evidence: {
    overhaul_records: EvidenceClass; overhaul_number: EvidenceClass; workorder_source_relationship: EvidenceClass; workorder_mart_resolution: EvidenceClass;
    asset_derived_relationship: EvidenceClass; lifecycle_status: EvidenceClass; planned_duration: EvidenceClass; actual_duration: EvidenceClass;
    progress_value: EvidenceClass; progress_scale: EvidenceClass; schedule_variance: EvidenceClass; overhaul_completion: EvidenceClass;
    inspection_number: EvidenceClass; inspection_relationship: EvidenceClass; performance_test: EvidenceClass; performance_test_semantics: EvidenceClass;
  };
}
export interface DecisionOverviewView {
  scope: { site_code: "BSR"; organization_code: "IP"; registry_scope: string; maintenance_source: string; date_basis: string };
  data_maturity: { asset_maintenance: string; controlled_domains: string; rcfa_relationship: string; technical_context: string };
  window_days: 7 | 30 | 90;
  window_start: string;
  as_of: string;
  summary: {
    registered_assets: EvidenceValue;
    maintenance_activity_7d: EvidenceValue;
    maintenance_activity_30d: EvidenceValue;
    maintenance_activity_90d: EvidenceValue;
    assets_active_7d: EvidenceValue;
    assets_active_30d: EvidenceValue;
    assets_active_90d: EvidenceValue;
  };
  maintenance_activity: { period_start: string; period_end: string; event_count: EvidenceValue }[];
  status_distribution: { value: string; count: EvidenceValue }[];
  work_type_distribution: { value: string; count: EvidenceValue }[];
  activity_concentration: { asset_ref: string; source_asset_number: string; description: string | null; event_count: EvidenceValue; latest_activity: string | null }[];
  record_availability: {
    fmea_records: EvidenceValue;
    fmea_assets_represented: EvidenceValue;
    asset_health_records: EvidenceValue;
    asset_health_assets_represented: EvidenceValue;
    rcfa_records: EvidenceValue;
    overhaul_records: EvidenceValue;
  };
  integrity: IntegrityView;
}

export interface MaintenanceInvestigationView {
  scope: { site_code: "BSR"; organization_code: "IP"; registry_scope: string; date_basis: string; interpretation: "ACTIVITY_NOT_FAILURE" };
  window: { days: 30 | 90 | 180; start: string; as_of: string };
  summary: {
    registered_assets: number;
    maintenance_events: number;
    assets_with_activity: number;
    assets_with_2plus_events: number;
    assets_with_3plus_events: number;
    repeat_activity_events: number;
  };
  assets: {
    asset_ref: string;
    source_asset_number: string;
    description: string | null;
    event_count: number;
    repeat_activity_events: number;
    latest_activity: string | null;
    previous_activity: string | null;
    latest_gap_days: number | null;
    minimum_gap_days: number | null;
    latest_work_type: string | null;
    dominant_work_type: string | null;
  }[];
  meta: PageMeta;
  evidence: {
    repeat_activity: "DERIVED_SAFE";
    work_type_source: string;
    activity_date: string;
    repeat_failure: "BUSINESS_SEMANTICS_REQUIRED";
  };
}

export interface AssetFilters { status?: string; unit?: string; asset_type?: string; offset?: number; limit?: number; sort?: "updated_desc" | "updated_asc" | "status"; }
export interface MaintenanceFilters { asset_ref?: string; work_order_id?: string; status?: string; event_type?: string; date_from?: string; date_to?: string; offset?: number; limit?: number; sort?: "date_desc" | "date_asc" | "status"; }
export interface FmeaFilters { asset_ref?: string; asset_number?: string; lifecycle_status?: string; source_number?: string; source_failure_code?: string; updated_from?: string; updated_to?: string; offset?: number; limit?: number; sort?: "updated_desc" | "updated_asc" | "status"; }
export interface RcfaFilters { lifecycle_status?: string; category?: string; source_number?: string; created_from?: string; created_to?: string; offset?: number; limit?: number; sort?: "created_desc" | "created_asc" | "status"; }
export interface HealthFilters { asset_ref?: string; asset_number?: string; description?: string; lifecycle_status?: string; updated_from?: string; updated_to?: string; offset?: number; limit?: number; sort?: "updated_desc" | "updated_asc" | "status"; }
export interface OverhaulFilters { source_number?: string; asset_ref?: string; workorder_ref?: string; source_work_order_number?: string; lifecycle_status?: string; planned_from?: string; planned_to?: string; actual_from?: string; actual_to?: string; offset?: number; limit?: number; sort?: "date_desc" | "date_asc" | "status"; }
export interface AssetDetailPageFilters { offset?: number; limit?: number; }

export class ApiError extends Error {
  constructor(message: string, public readonly status: number) { super(message); this.name = "ApiError"; }
}

function query(filters: object): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if ((typeof value === "string" && value !== "") || typeof value === "number") params.set(key, String(value));
  }
  const encoded = params.toString();
  return encoded ? `?${encoded}` : "";
}

async function get<T>(path: string): Promise<T> {
  const response = await fetch(`/api/cockpit${path}`, { cache: "no-store" });
  if (!response.ok) {
    if(response.status===401){window.location.replace("/login?expired=1");throw new ApiError("Sesi berakhir. Silakan masuk kembali.",401);}
    if(response.status===403)throw new ApiError("Akses data faktual memerlukan grant scope yang disetujui. Peran ADMIN tidak memberikan akses seluruh aset.",403);
    if (response.status === 503) throw new ApiError("Reliability Mart unavailable", response.status);
    throw new ApiError(`Reliability API ${path}: HTTP ${response.status}`, response.status);
  }
  return response.json() as Promise<T>;
}

export const KPI_METRICS = ["MTBF", "MTTR", "AVAILABILITY", "PM_COMPLIANCE"] as const;
export const cockpitApi = {
  listEquipment: (limit = 200) => get<EquipmentView[]>(`/equipment?limit=${limit}`),
  getEquipment: (equipmentId: string) => get<EquipmentView>(`/equipment/${encodeURIComponent(equipmentId)}`),
  listWorkOrders: (equipmentId?: string, offset = 0, limit = 50, status?: string) => get<WorkOrderPage>(`/work-orders${query({ equipment_id: equipmentId, status, offset, limit })}`),
  listWorkOrderStatuses: () => get<string[]>("/work-orders/statuses"),
  getKpi: (equipmentId: string, metric: string) => get<ReliabilityKpiView>(`/kpis/${encodeURIComponent(equipmentId)}/${encodeURIComponent(metric)}`),
  health: () => get<{ status: string }>("/health"),
};

export const reliabilityApi = {
  decisionOverview: (windowDays: 7 | 30 | 90 = 30) => get<DecisionOverviewView>(`/v1/reliability/decision-overview?window_days=${windowDays}`),
  assetHealthOverview: () => get<AssetHealthOverviewView>("/v1/reliability/asset-health/overview"),
  fmeaOverview: () => get<FmeaOverviewView>("/v1/reliability/fmea/overview"),
  rcfaOverview: () => get<RcfaOverviewView>("/v1/reliability/rcfa/overview"),
  maintenanceInvestigation: (windowDays: 30 | 90 | 180 = 90, minEvents: 2 | 3 | 5 = 2, offset = 0, limit = 25, sort: "event_count_desc" | "latest_activity_desc" | "latest_gap_asc" = "event_count_desc") => get<MaintenanceInvestigationView>(`/v1/reliability/maintenance-investigation${query({ window_days: windowDays, min_events: minEvents, offset, limit, sort })}`),
  assets: (filters: AssetFilters = {}) => get<Page<AssetView>>(`/v1/reliability/assets${query(filters)}`),
  registry: () => get<RegistryView>("/v1/reliability/registry"),
  asset: (canonicalId: string) => get<AssetView>(`/v1/reliability/assets/${encodeURIComponent(canonicalId)}`),
  integrationStatus: (canonicalId?: string) => get<IntegrationStatus>(canonicalId ? `/v1/reliability/assets/${encodeURIComponent(canonicalId)}/integration-status` : "/v1/reliability/integration-status"),
  conditionEvidence: (canonicalId: string) => get<AssetConditionEvidence>(`/v1/reliability/assets/${encodeURIComponent(canonicalId)}/condition-evidence`),
  assetContext: (canonicalId: string) => get<ContextView>(`/v1/reliability/assets/${encodeURIComponent(canonicalId)}/context`),
  assetTimeline: (canonicalId: string, filters: AssetDetailPageFilters = {}) => get<Page<TimelineView>>(`/v1/reliability/assets/${encodeURIComponent(canonicalId)}/timeline${query(filters)}`),
  assetFmea: (canonicalId: string, filters: AssetDetailPageFilters = {}) => get<Page<FmeaView>>(`/v1/reliability/assets/${encodeURIComponent(canonicalId)}/fmea${query(filters)}`),
  assetHealthAssessments: (canonicalId: string, filters: AssetDetailPageFilters = {}) => get<Page<AssetHealthView>>(`/v1/reliability/assets/${encodeURIComponent(canonicalId)}/health-assessments${query(filters)}`),
  latestAssetHealth: (canonicalId: string) => get<AssetHealthView>(`/v1/reliability/assets/${encodeURIComponent(canonicalId)}/health/latest`),
  maintenance: (filters: MaintenanceFilters = {}) => get<Page<MaintenanceEventView>>(`/v1/reliability/maintenance-events${query(filters)}`),
  fmea: (filters: FmeaFilters = {}) => get<Page<FmeaView>>(`/v1/reliability/fmea${query(filters)}`),
  rcfa: (filters: RcfaFilters = {}) => get<Page<RcfaView>>(`/v1/reliability/rcfa${query(filters)}`),
  assetHealth: (filters: HealthFilters = {}) => get<Page<AssetHealthView>>(`/v1/reliability/asset-health${query(filters)}`),
  overhaulOverview: () => get<OverhaulOverviewView>("/v1/reliability/overhauls/overview"),
  overhauls: (filters: OverhaulFilters = {}) => get<Page<OverhaulView>>(`/v1/reliability/overhauls${query(filters)}`),
  dataTrust: () => get<DataTrustView>("/v1/reliability/data-trust"),
  integrity: () => get<IntegrityView>("/v1/reliability/integrity"),
};


export interface AssetConditionEvidence {
  canonical_asset_id: string;
  mapping_readiness: string;
  statuses: string[];
  expected_signals: number;
  latest_attempt_at: string | null;
  collector_last_success_at: string | null;
  items: {
    evidence: {
      // Existing server DTO lineage; no request/auth/endpoint changes.
      contract_version: string; canonical_asset_id: string;
      sources: {pi: {pi_source_id: string; af_server_ref: string; af_database_ref: string;
        af_element_ref: string; mapping_role: string; mapping_status: string;
        attribute_ref: string; attribute_name?: string | null}};
      provenance: {selection_evidence_ref: string; selection_approved_by: string;
        selection_approved_at: string; source_boundary: string};
      signal_id: string; semantic_name: string; mapping_id: string;
      value: number | string | boolean | { name: string | null; code: number | null; is_system: boolean | null } | null;
      value_type: "NUMERIC" | "TEXT" | "DIGITAL_STATE" | "BOOLEAN" | "NULL";
      unit: string | null; source_timestamp: string | null; collected_at: string;
      quality_good: boolean | null; quality_questionable: boolean | null;
      quality_substituted: boolean | null; quality_annotated: boolean | null;
      evidence_status: string;
    };
    projected_at: string;
    statuses: string[];
    freshness: { collector: string; source: string; projection: string; mapping: string };
  }[];
}


export type TrustState = "CURRENT" | "STALE" | "UNKNOWN" | "BLOCKED" | "DEGRADED" | "NOT_CONFIGURED";
export interface FreshnessDimension { state: TrustState; observed_at: string | null; max_age_seconds: number | null }
export interface IntegrationStatus {
  contract_version: string; observed_at: string; canonical_asset_id: string | null;
  governance_schema_ready: boolean | null; condition_schema_ready: boolean | null;
  coverage: { registered_assets: number | null; verified_mapping_assets: number | null; ambiguous_mapping_assets: number | null;
    approved_signal_assets: number | null; projected_assets: number | null; approved_signals: number | null; projected_signals: number | null;
    technical_registry_total: number | null; technical_registry_active: number | null; technical_snapshots: number | null };
  components: Array<{ component: string; state: TrustState; availability: string;
    collection_freshness: FreshnessDimension; source_freshness: FreshnessDimension; projection_freshness: FreshnessDimension;
    mapping_readiness: string; quality: string; last_successful_activity: string | null; degraded_reasons: string[] }>;
}
