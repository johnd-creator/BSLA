import {validRecordId} from './product-records';
import {preciseInstant} from './pdm-history';
import {ApiError, type AssetConditionEvidence, type MaintenanceEventView, type Page, type MaintenanceFilters} from './api';

export const EVIDENCE_LIMIT = 25;
const text = (q: URLSearchParams, key: string) => q.get(key)?.trim().slice(0, 200) || undefined;
export function maintenanceFilters(q: URLSearchParams, asset: string): MaintenanceFilters {
  const offset = Number(q.get('me_offset') ?? 0);
  const sort = q.get('me_sort');
  return {asset_ref: asset, limit: EVIDENCE_LIMIT,
    offset: Number.isSafeInteger(offset) && offset >= 0 && offset <= 1000000 ? offset : 0,
    status: text(q, 'me_status'), event_type: text(q, 'me_type'), work_order_id: text(q, 'me_wo'),
    date_from: text(q, 'me_from'), date_to: text(q, 'me_to'),
    sort: sort === 'date_asc' || sort === 'status' ? sort : 'date_desc'};
}
export function maintenanceFilterError(filters: MaintenanceFilters): string | null {
  for (const value of [filters.date_from, filters.date_to]) if (value && !preciseInstant(value)) return 'Waktu filter harus ISO-8601 lengkap dengan zona, misalnya 2026-01-01T00:00:00+07:00.';
  if (filters.date_from && filters.date_to && Date.parse(filters.date_from) > Date.parse(filters.date_to)) return 'Batas waktu awal melebihi batas akhir.';
  return null;
}
export function evidenceErrorKind(error: unknown): 'access' | 'session' | 'request' | 'service' {
  if (error instanceof ApiError) return error.status === 403 ? 'access' : error.status === 401 ? 'session' : error.status === 400 || error.status === 422 ? 'request' : 'service';
  return 'service';
}
export function evidenceError(error: unknown): string {
  if (error instanceof ApiError && error.status === 403) return '403 · Anda tidak memiliki akses evidence untuk lingkup ini.';
  if (error instanceof ApiError && error.status === 401) return '401 · Sesi perlu diautentikasi kembali.';
  return 'Evidence tidak tersedia atau respons tidak memenuhi kontrak. Coba lagi; jangan menarik kesimpulan kondisi.';
}
// Validate the bounded response before rendering; never silently discard a duplicate.
export function validateMaintenance(page: Page<MaintenanceEventView>, asset: string, offset: number) {
  const seen = new Set<string>();
  if (!page || !Array.isArray(page.items) || page.items.length > EVIDENCE_LIMIT || !page.meta ||
    page.meta.offset !== offset || page.meta.limit !== EVIDENCE_LIMIT || !Number.isSafeInteger(page.meta.total) ||
    page.meta.total < 0 || typeof page.meta.has_more !== 'boolean' ||
    page.meta.total < offset + page.items.length && page.items.length > 0) throw new Error('Invalid page');
  if (page.items.length !== Math.min(EVIDENCE_LIMIT,Math.max(0,page.meta.total-offset)) || page.meta.has_more !== (offset+page.items.length < page.meta.total)) throw new Error('Incomplete page proof');
  for (const row of page.items) {
    if (typeof row.canonical_id !== 'string' || !row.canonical_id || seen.has(row.canonical_id) || row.equipment_id !== asset ||
      row.site_code !== 'BSR' || row.organization_code !== 'IP') throw new Error('Invalid source identity');
    seen.add(row.canonical_id);
  }
  return page;
}
export function conflictingWorkOrders(rows: MaintenanceEventView[]): Set<string> {
  const count = new Map<string, number>();
  for (const row of rows) if (row.work_order_id) count.set(row.work_order_id, (count.get(row.work_order_id) ?? 0) + 1);
  return new Set([...count].filter(([, n]) => n > 1).map(([id]) => id));
}
export function validateCondition(data: AssetConditionEvidence, asset: string) {
  const ref = (v: unknown, max = 200): v is string => typeof v === 'string' && v.length > 0 && v.length <= max && v === v.trim();
  const strings = (v: unknown): v is string[] => Array.isArray(v) && v.length <= 30 && v.every(x => ref(x, 100));
  const time = (v: unknown, nullable = false) => nullable && v === null || typeof v === 'string' && preciseInstant(v);
  if (!data || data.canonical_asset_id !== asset || !Array.isArray(data.items) || data.items.length > 5 ||
    !['MAPPING_VERIFIED','MAPPING_UNVERIFIED','MAPPING_AMBIGUOUS','MAPPING_UNKNOWN'].includes(data.mapping_readiness) ||
    !strings(data.statuses) || !Number.isInteger(data.expected_signals) || data.expected_signals < data.items.length || data.expected_signals > 5 ||
    !time(data.latest_attempt_at, true) || !time(data.collector_last_success_at, true)) throw new Error('Invalid asset evidence');
  const seen = new Set<string>(), attributes = new Set<string>(), identities = new Set<string>();
  for (const item of data.items) {
    const e = item?.evidence, pi = e?.sources?.pi, provenance = e?.provenance;
    if (!e || !ref(e.signal_id) || seen.has(e.signal_id) || e.canonical_asset_id !== asset ||
      data.mapping_readiness !== 'MAPPING_VERIFIED' || e.contract_version !== '1.0' || !ref(e.mapping_id) ||
      !ref(e.semantic_name,80) || !/^[a-z][a-z0-9_]*$/.test(e.semantic_name) ||
      !pi || pi.pi_source_id !== 'CENTRAL_PI' || pi.mapping_status !== 'VERIFIED' || pi.mapping_role !== 'PRIMARY_EQUIPMENT' ||
      ![pi.af_server_ref,pi.af_database_ref,pi.af_element_ref].every(v => ref(v)) || !ref(pi.attribute_ref,512) || !(pi.attribute_name == null || typeof pi.attribute_name === 'string' && pi.attribute_name.length <= 240) ||
      attributes.has(pi.attribute_ref) || !provenance || provenance.source_boundary !== 'GOVERNED_PI_SOURCE' ||
      !ref(provenance.selection_evidence_ref,500) || !ref(provenance.selection_approved_by,160) || !time(provenance.selection_approved_at) ||
      !time(e.source_timestamp,true) || !time(e.collected_at) || !time(item.projected_at) || !strings(item.statuses) ||
      !item.freshness || !['collector','source','projection','mapping'].every(k => ref(item.freshness[k as keyof typeof item.freshness],100)) ||
      item.freshness.mapping !== 'MAPPING_VERIFIED' || !(e.unit === null || typeof e.unit === 'string' && e.unit.length <= 40)) throw new Error('Invalid approved lineage');
    const value = e.value;
    const valid = e.value_type === 'NULL' ? value === null
      : e.value_type === 'NUMERIC' ? typeof value === 'number' && Number.isFinite(value)
      : e.value_type === 'TEXT' ? typeof value === 'string' && value.length <= 4096
      : e.value_type === 'BOOLEAN' ? typeof value === 'boolean'
      : e.value_type === 'DIGITAL_STATE' && value !== null && typeof value === 'object' &&
        (value.name === null || typeof value.name === 'string') && (value.code === null || typeof value.code === 'number' && Number.isFinite(value.code)) &&
        (value.is_system === null || typeof value.is_system === 'boolean');
    const quality = e.quality_good === false || e.quality_questionable === true ? 'BAD_QUALITY' : value === null ? 'UNKNOWN_VALUE' : e.quality_good === null ? 'UNKNOWN_QUALITY' : 'EVIDENCE_AVAILABLE';
    if (!valid || [e.quality_good,e.quality_questionable,e.quality_substituted,e.quality_annotated].some(v => v !== null && typeof v !== 'boolean') || e.evidence_status !== quality) throw new Error('Invalid typed source value');
    seen.add(e.signal_id); attributes.add(pi.attribute_ref);
    identities.add(JSON.stringify([e.mapping_id,pi.pi_source_id,pi.af_server_ref,pi.af_database_ref,pi.af_element_ref]));
  }
  if (identities.size > 1) throw new Error('Conflicting mapping');
  return data;
}
// Generated links have a closed set of same-origin destinations. No arbitrary return URL.
const pdmOriginKeys = ['search','asset_id','method','status','since','until','per_page','pdm_offset'] as const;
export function inspectionAssetHref(asset: string, inspection: string, origin = new URLSearchParams()) {
  const q = new URLSearchParams();
  if (validRecordId(inspection)) q.set('inspection',inspection);
  for (const key of pdmOriginKeys) {const value=text(origin,key);if(value)q.set('origin_pdm_'+key,value);}
  return `/assets/${encodeURIComponent(asset)}${q.size ? '?' + q : ''}`;
}
export function assetReturnHref(q: URLSearchParams): string {
  const inspection = q.get('inspection');
  if (validRecordId(inspection)) {const next=new URLSearchParams({record:inspection!});for(const key of pdmOriginKeys){const value=text(q,'origin_pdm_'+key);if(value)next.set(key,value);}return '/pdm?'+next;}
  const result = new URLSearchParams();
  for (const key of ['status', 'unit', 'asset_type', 'offset', 'search']) {
    const value = text(q, `origin_${key}`); if (value) result.set(key, value);
  }
  return `/assets${result.size ? '?' + result : ''}`;
}
export function assetDetailHref(asset: string, origin: URLSearchParams) {
  const q = new URLSearchParams();
  for (const key of ['status', 'unit', 'asset_type', 'offset', 'search']) {
    const value = text(origin, key); if (value) q.set(`origin_${key}`, value);
  }
  return `/assets/${encodeURIComponent(asset)}${q.size ? '?' + q : ''}`;
}
