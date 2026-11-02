/** Server-side read models built only from exact authorized Registry/WO requests. */
import {readBounded} from './bounded-http';
import {factualAssets,type FactualReadSnapshot} from './factual-read-policy';
import type {AssetView,MaintenanceEventView,Page} from './api';
import type {ScopedFactualOverview} from './factual-read-contract';
import {validateMaintenance} from './asset-evidence';
import {preciseInstant} from './pdm-history';
const BASE='http://127.0.0.1:8000';
const ASSET_FIELDS=['canonical_id','contract_version','source_asset_number','description','status','location_ref','parent_asset_ref','site_code','organization_code','asset_type','plant','unit','source_updated_at'];
const MAINTENANCE_FIELDS=['canonical_id','contract_version','id','equipment_id','work_order_id','event_type','status','actual_start','actual_finish','duration_hours','labor_hours','downtime_hours','failure_code','source_changed_at','site_code','organization_code'];
const CLASSIFICATION_FIELDS=['raw_work_type','canonical_category','state','origin','confidence','description','workflow_name','workflow_version','workflow_state','status_state'];
const SOURCE_FIELDS=['work_order_number','asset_number','reported_at','scheduled_start','scheduled_finish'];
function pick(value:Record<string,unknown>,fields:string[]):Record<string,unknown>{return Object.fromEntries(fields.filter(k=>Object.hasOwn(value,k)).map(k=>[k,value[k]]));}
function object(value:unknown):Record<string,unknown>{if(!value||typeof value!=='object'||Array.isArray(value))throw new Error('SCOPED_RESPONSE_INVALID');return value as Record<string,unknown>;}
async function json(target:URL,requestFetch:typeof fetch,signal:AbortSignal,max=2*1024*1024):Promise<unknown>{
 const response=await requestFetch(target,{method:'GET',headers:{accept:'application/json'},cache:'no-store',redirect:'error',signal});
 if(response.status!==200||!(response.headers.get('content-type')??'').toLowerCase().startsWith('application/json'))throw new Error('SCOPED_UPSTREAM_UNAVAILABLE');
 return JSON.parse(new TextDecoder().decode(await readBounded(response.body,max,signal)));
}
export async function scopedAsset(id:string,allowed:string[],requestFetch:typeof fetch,signal:AbortSignal):Promise<AssetView>{
 if(!allowed.includes(id))throw new Error('ASSET_SCOPE_DENIED');
 const asset=object(await json(new URL('/v1/reliability/assets/'+encodeURIComponent(id),BASE),requestFetch,signal,256*1024));
 if(asset.canonical_id!==id||asset.site_code!=='BSR'||asset.organization_code!=='IP')throw new Error('ASSET_SCOPE_DENIED');
 for(const key of ASSET_FIELDS){
  const value=asset[key];
  if(['canonical_id','contract_version','site_code','organization_code'].includes(key)){
   if(typeof value!=='string'||!value.length)throw new Error('SCOPED_ASSET_INVALID');
  }else if(value!==null&&typeof value!=='string')throw new Error('SCOPED_ASSET_INVALID');
 }
 if(asset.source_asset_number!==null&&asset.source_asset_number!==id.split(':').at(-1))throw new Error('SCOPED_ASSET_INVALID');
 if(asset.source_updated_at!==null&&!(preciseInstant(asset.source_updated_at as string)||/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?$/.test(asset.source_updated_at as string)&&preciseInstant(asset.source_updated_at+'Z')))throw new Error('SCOPED_ASSET_INVALID');
 const safe=pick(asset,ASSET_FIELDS);
 if(typeof safe.parent_asset_ref==='string'&&!allowed.includes(safe.parent_asset_ref))safe.parent_asset_ref=null;
 return safe as unknown as AssetView;
}
export function scopedMaintenancePage(value:unknown,id:string,offset:number,limit:number):Page<MaintenanceEventView>{
 const page=object(value),meta=object(page.meta);
 if(!Array.isArray(page.items)||page.items.length>200||['total','offset','limit'].some(k=>!Number.isSafeInteger(meta[k])||(meta[k] as number)<0)||!(meta.limit as number)||typeof meta.has_more!=='boolean'||page.items.length>(meta.limit as number)||page.items.length>(meta.total as number))throw new Error('SCOPED_PAGE_INVALID');
 validateMaintenance(page as unknown as Page<MaintenanceEventView>,id,offset,limit);
 const items=page.items.map(value=>{
  const row=object(value);if(row.equipment_id!==id||row.site_code!=='BSR'||row.organization_code!=='IP')throw new Error('SCOPED_WO_IDENTITY_INVALID');
  const safe=pick(row,MAINTENANCE_FIELDS);
  if(row.classification!=null)safe.classification=pick(object(row.classification),CLASSIFICATION_FIELDS);
  if(row.source_detail!=null){const detail=object(row.source_detail);if(detail.asset_number!=null&&detail.asset_number!==id.split(':').at(-1))throw new Error('SCOPED_WO_IDENTITY_INVALID');safe.source_detail=pick(detail,SOURCE_FIELDS);}
  return safe as unknown as MaintenanceEventView;
 });
 return {items,meta:{total:meta.total as number,offset:meta.offset as number,limit:meta.limit as number,has_more:meta.has_more}};
}
export async function scopedRegister(params:URLSearchParams,snapshot:FactualReadSnapshot,requestFetch:typeof fetch,signal:AbortSignal):Promise<Page<AssetView>>{
 const allowed=factualAssets(snapshot,['FACTUAL_ASSET_READ']);
 if(!allowed.length)throw new Error('FACTUAL_SCOPE_GRANT_REQUIRED');
 for(const key of params.keys())if(!['status','unit','asset_type','sort','offset','limit','site_code','organization_code'].includes(key))throw new Error('QUERY_DENIED');
 const sort=params.get('sort')??'updated_desc';if(!['updated_desc','updated_asc','status'].includes(sort))throw new Error('QUERY_DENIED');
 // No broad /assets query: authorization precedes every upstream lookup and total.
 let items=await Promise.all(allowed.map(id=>scopedAsset(id,allowed,requestFetch,signal)));
 for(const key of ['status','unit','asset_type'] as const)if(params.get(key))items=items.filter(asset=>asset[key]===params.get(key));
 items.sort((a,b)=>{
  const left=sort==='status'?a.status:a.source_updated_at,right=sort==='status'?b.status:b.source_updated_at;
  if(left==null||right==null)return left===right?a.canonical_id.localeCompare(b.canonical_id):left==null?1:-1;
  // Offset-aware source clocks compare as instants. Naive clocks retain unknown zone;
  // keep them after verified instants and use literal ordering only within that group.
  const zoned=(value:string)=>preciseInstant(value)?Date.parse(value):null;
  const l=sort==='status'?null:zoned(left),r=sort==='status'?null:zoned(right);
  if(sort!=='status'&&(l===null)!==(r===null))return l===null?1:-1;
  const result=l!==null&&r!==null?l-r:left===right?0:left<right?-1:1;
  return (sort==='updated_desc'?-result:result)||a.canonical_id.localeCompare(b.canonical_id);
 });
 const offset=Number(params.get('offset')??0),limit=Number(params.get('limit')??50),total=items.length;
 return {items:items.slice(offset,offset+limit),meta:{total,offset,limit,has_more:offset+limit<total}};
}
export async function scopedOverview(snapshot:FactualReadSnapshot,requestFetch:typeof fetch,signal:AbortSignal):Promise<ScopedFactualOverview>{
 const allowed=factualAssets(snapshot,['FACTUAL_DASHBOARD_READ','FACTUAL_ASSET_READ','FACTUAL_MAINTENANCE_READ']);
 if(!allowed.length)throw new Error('FACTUAL_SCOPE_GRANT_REQUIRED');
 const assets=await Promise.all(allowed.map(async id=>{
  const asset=await scopedAsset(id,allowed,requestFetch,signal);
  const target=new URL('/v1/reliability/maintenance-events',BASE);target.search=new URLSearchParams({asset_ref:id,offset:'0',limit:'1',sort:'date_desc'}).toString();
  const page=scopedMaintenancePage(await json(target,requestFetch,signal),id,0,1);
  const latest=page.items[0];
  return {canonical_id:id,source_asset_number:asset.source_asset_number,description:asset.description,
   maintenance_events:page.meta.total,latest_retained_activity:latest?.actual_start??latest?.source_changed_at??null};
 }));
 return {scope:{site_code:'BSR',organization_code:'IP',kind:'FACTUAL_ASSET_ALLOWLIST'},as_of:new Date().toISOString(),
  summary:{registered_assets:assets.length,maintenance_events:assets.reduce((n,a)=>n+a.maintenance_events,0),assets_with_maintenance:assets.filter(a=>a.maintenance_events>0).length},
  assets,restricted_sections:['PORTFOLIO_AGGREGATES','FMEA_HEALTH_PI','CROSS_INSPECTION_TRENDS'],operational_kpis:'NOT_ELIGIBLE'};
}
