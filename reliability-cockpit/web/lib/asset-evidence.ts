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
    page.meta.total < offset + page.items.length && page.items.length > 0) throw new Error('Invalid page');
  for (const row of page.items) {
    if (!row.canonical_id || seen.has(row.canonical_id) || row.equipment_id !== asset ||
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
  if (!data || data.canonical_asset_id !== asset || !Array.isArray(data.items) || data.items.length > 5) throw new Error('Invalid asset evidence');
  const seen = new Set<string>(), mappings = new Set<string>();
  for (const {evidence} of data.items) {
    if (!evidence.signal_id || seen.has(evidence.signal_id) ||
      evidence.canonical_asset_id && evidence.canonical_asset_id !== asset ||
      data.mapping_readiness !== 'MAPPING_VERIFIED') throw new Error('Invalid approved evidence');
    if (evidence.sources?.pi && (evidence.sources.pi.mapping_status !== 'VERIFIED' || evidence.sources.pi.mapping_role !== 'PRIMARY_EQUIPMENT')) throw new Error('Invalid PI identity');
    seen.add(evidence.signal_id); mappings.add(evidence.mapping_id);
  }
  if (mappings.size > 1) throw new Error('Conflicting mapping');
  return data;
}
// Generated links have a closed set of same-origin destinations. No arbitrary return URL.
export function inspectionAssetHref(asset: string, inspection: string) {
  return `/assets/${encodeURIComponent(asset)}?${new URLSearchParams({record:inspection})}`;
}
export function assetReturnHref(q: URLSearchParams): string {
  const inspection = q.get('inspection');
  if (inspection && inspection.length <= 200) return `/pdm?${new URLSearchParams({record:inspection})}`;
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
