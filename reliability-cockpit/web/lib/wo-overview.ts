import type {WoEvidence} from './wo-evidence-types';
const bases=['reported','actual_started','actual_finished','record_modified'];
function obj(v:unknown):Record<string,unknown>{if(!v||typeof v!=='object'||Array.isArray(v))throw new Error('WO_OVERVIEW_INVALID');return v as Record<string,unknown>;}
function count(v:unknown){if(!Number.isSafeInteger(v)||(v as number)<0)throw new Error('WO_OVERVIEW_INVALID');return v as number;}
export function safeWoOverview(value:unknown):WoEvidence|null{
 if(value==null)return null;
 const d=obj(value),population=obj(d.population),coverage=obj(d.date_coverage),counts=obj(d.counts);
 if(![7,30,90].includes(Number(d.window_days))||population.registry_scope!=='REGISTERED_BSR_IP'||population.site_code!=='BSR'||population.organization_code!=='IP'||population.wo_group!=='SEMANTICS_UNVERIFIED'||!Array.isArray(d.weekly)||d.weekly.length!==12||!Array.isArray(d.status_snapshot)||d.status_snapshot.length>200)throw new Error('WO_OVERVIEW_INVALID');
 const total=count(coverage.total_unique_wo);
 const cleanCounts=Object.fromEntries(bases.map(k=>[k,count(counts[k])]));
 const cleanCoverage=Object.fromEntries(['total_unique_wo',...bases].map(k=>[k,count(coverage[k])]));
 if(bases.some(k=>cleanCounts[k]>cleanCoverage[k]||cleanCoverage[k]>total))throw new Error('WO_OVERVIEW_INVALID');
 const weekly=d.weekly.map(v=>{const row=obj(v);if(typeof row.period_start!=='string'||typeof row.period_end!=='string'||!Number.isFinite(Date.parse(row.period_start))||!Number.isFinite(Date.parse(row.period_end)))throw new Error('WO_OVERVIEW_INVALID');return {period_start:row.period_start,period_end:row.period_end,...Object.fromEntries(bases.map(k=>[k,count(row[k])]))};});
 const statuses=d.status_snapshot.map(v=>{const row=obj(v);if(typeof row.value!=='string'||row.value.length>80)throw new Error('WO_OVERVIEW_INVALID');return {value:row.value,count:count(row.count)};});
 return {window_days:d.window_days as 7|30|90,counts:cleanCounts,date_coverage:cleanCoverage,weekly,population:{wo_group:'SEMANTICS_UNVERIFIED',counting_key:'DISTINCT_WORK_ORDER_REF_OR_UNRESOLVED_CANONICAL_ID'},backlog:{state:'DEFINITION_REQUIRES_APPROVAL',count:null},freshness:{state:'NOT_EXPOSED'},status_snapshot:statuses};
}
