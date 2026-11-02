import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {mkdtempSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {createRequire} from 'node:module';
const temp=mkdtempSync(join(tmpdir(),'nadi-sprint02-history-'));
let count=0;const test=(name,fn)=>{fn();count++;console.log('PASS '+name);};
try{
 execFileSync(process.execPath,['node_modules/typescript/bin/tsc','lib/pdm-history.ts','--outDir',temp,'--target','ES2022','--module','commonjs','--skipLibCheck'],{stdio:'pipe'});
 const {historyHref,readHistoryContext,nativeFilterQuery,pointQuery,preciseInstant,samplePlot,historyEligibility}=createRequire(import.meta.url)(join(temp,'pdm-history.js'));
 const row={record_id:'inspection:SYNTHETIC-02',canonical_asset_id:'asset:SYNTHETIC',method:'VIBRATION'};
 test('native exact context includes asset/method and exact origin record',()=>{const p=new URL(historyHref(row),'https://synthetic.invalid').searchParams;assert.equal(p.get('asset_id'),row.canonical_asset_id);assert.equal(p.get('method'),'VIBRATION');assert.equal(readHistoryContext(p).originRecord,row.record_id);assert.equal(p.get('pdm_view'),'history');});
 test('provisional link does not invent asset/point/source binding',()=>{const p=new URL(historyHref({...row,input_capture:{}}),'https://synthetic.invalid').searchParams;assert.equal(p.get('history_kind'),'excel');for(const key of ['asset_id','method','point','source_ref'])assert.equal(p.has(key),false);});
 test('unknown origin record is not made into a detail link',()=>assert.equal(readHistoryContext(new URLSearchParams('from_inspection=https://secret.invalid')).originRecord,''));
 test('native query is allowlisted and retains exact text',()=>{const p=new URLSearchParams({asset_id:'asset:SYNTHETIC',method:'VIBRATION',point:' A & B ',quantity:'velocity',actor:'ADMIN',offset:'99'});assert.equal(nativeFilterQuery(p),'&asset_id=asset%3ASYNTHETIC&method=VIBRATION');assert.equal(pointQuery(' A & B ','velocity'),'&point=+A+%26+B+&quantity=velocity');});
 test('ISO offsets and fractions remain precise; no date/time-only coercion',()=>{assert(preciseInstant('2026-10-09T14:00:00.123+07:00'));for(const x of [null,'2026-10-09','14:00:00','2026-10-09T14:00:00','2026-02-30T00:00:00Z','2026-13-01T00:00:00Z','2026-10-09T24:00:00Z'])assert(!preciseInstant(x),String(x));});
 test('bounded native event page context survives exact links',()=>{for(const limit of [1,10,25]){const c=readHistoryContext(new URLSearchParams({event_limit:String(limit),event_offset:'50'}));assert.equal(c.nativeLimit,limit);assert.equal(c.nativeOffset,50);}for(const n of ['-1','10001','1.5'])assert.equal(readHistoryContext(new URLSearchParams({event_offset:n})).nativeOffset,0);});
 const sample=(value=0,time='2026-10-09T01:00:00Z')=>({record_id:row.record_id,revision:1,canonical_asset_id:row.canonical_asset_id,method:row.method,method_version:'SYNTHETIC-1',operating_context:'SYNTHETIC',method_extension:{instrument_ref:'SYNTHETIC-I',procedure_ref:'SYNTHETIC-P',orientation:'SYNTHETIC-O'},measurement:{point_ref:'point:SYNTHETIC',quantity:'velocity',unit:'mm/s',value,measured_at:time,provenance:'HUMAN_ENTERED_MEASUREMENT'}});
 test('same-inspection actual sparse samples and zero retained without filling gaps',()=>{const p=samplePlot([sample(0),sample(2,'2026-10-10T08:13:00+07:00')]);assert.equal(p.points.length,2);assert.equal(p.points[0].value,0);assert.equal(p.points[1].label,'2026-10-10T08:13:00+07:00');});
 test('null/boolean/source text do not become numeric plot points',()=>{for(const value of [null,false,'0','trace'])assert.equal(samplePlot([sample(value)]).points.length,0);});
 test('partial clocks stay in raw table, never midnight samples',()=>{for(const value of ['2026-10-09','14:00:00',null])assert.equal(samplePlot([sample(1,value)]).points.length,0);});
 test('multiple records/revisions cannot form a real trend',()=>{assert.equal(samplePlot([sample(),{...sample(),record_id:'inspection:SYNTHETIC-other'}]).points.length,0);assert.equal(samplePlot([sample(),{...sample(),revision:2}]).points.length,0);});
 test('different asset cannot be silently grouped',()=>assert.equal(samplePlot([sample(),{...sample(),canonical_asset_id:'asset:OTHER'}]).points.length,0));
 test('unit and physical context differences remain blocked',()=>{for(const key of ['unit','point_ref','quantity']){const other=sample();other.measurement[key]='OTHER';assert.equal(samplePlot([sample(),other]).points.length,0);}assert.equal(samplePlot([sample(),{...sample(),operating_context:'OTHER'}]).points.length,0);});
 test('complete stored fields never manufacture engineer signoff',()=>{const c=historyEligibility([sample()]);assert(c.some(x=>x.state==='PENDING_ENGINEER_VALIDATION'));assert(c.some(x=>x.label.includes('acquisition')&&x.state==='UNKNOWN'));assert(c.filter(x=>x.state==='RECORDED').length>0);});
 test('APPROVED record does not approve comparability policy',()=>assert.equal(historyEligibility([{...sample(),status:'APPROVED'}]).at(-1).state,'PENDING_ENGINEER_VALIDATION'));
 console.log(`Sprint2 history contracts PASS ${count}`);
}finally{rmSync(temp,{recursive:true,force:true});}
