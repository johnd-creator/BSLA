// Render actual components and clocks with synthetic data; no network/server.
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createRequire} from 'node:module';
import {resolve,dirname} from 'node:path';
const require=createRequire(import.meta.url),ts=require('typescript'),React=require('react');
const {renderToStaticMarkup}=require('react-dom/server');
const cache=new Map();
function load(file){file=resolve(file);if(cache.has(file))return cache.get(file);const module={exports:{}};cache.set(file,module.exports);const js=ts.transpileModule(readFileSync(file,'utf8'),{compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX}}).outputText;const local=name=>name.startsWith('.')?(name.endsWith('.json')?require(resolve(dirname(file),name)):load(resolve(dirname(file),name)+(name.includes('components/')||name==='./ui'?'.tsx':'.ts'))):require(name);new Function('require','module','exports',js)(local,module,module.exports);cache.set(file,module.exports);return module.exports;}
const {woDate}=load('lib/wo-date.ts'),{WorkOrderSourceDetail,WorkOrderClock}=load('components/WorkOrderSourceDetail.tsx');
const {validateMaintenance}=load('lib/asset-evidence.ts');
const raw='2026-10-23T07:51:51.123400Z';
assert.equal(woDate(raw),'23 Okt 2026, 14.51 WIB');
assert.equal(woDate('2026-10-23T14:51:51+07:00'),'23 Okt 2026, 14.51 WIB');
assert.equal(woDate('2026-10-23T23:51:51Z'),'24 Okt 2026, 06.51 WIB');
assert.match(woDate('2026-10-23T07:51:51'),/07.51 · zona waktu belum diverifikasi/);
assert.match(woDate('2026-10-23T07:51:51-00:00'),/zona waktu belum diverifikasi/);
assert.match(woDate('2026-10-23t07:51:51-00:00'),/zona waktu belum diverifikasi/);
for(const date of ['2026-02-30T07:51:51Z','garbage'])assert.equal(woDate(date),'Format waktu tidak valid');
assert.equal(woDate(null),'BELUM TERSEDIA');
const row={...JSON.parse(readFileSync('fixtures/asset-evidence.synthetic.json')).maintenance[0],source_detail:{work_order_number:'WO-SYNTHETIC-42',asset_number:'ASSET-SYNTHETIC',reported_at:raw,scheduled_start:null,scheduled_finish:null},actual_start:null,actual_finish:null,duration_hours:0,labor_hours:0,downtime_hours:null};
const render=(component,props)=>renderToStaticMarkup(React.createElement(component,props));
const html=render(WorkOrderSourceDetail,{row});
for(const label of ['WO-SYNTHETIC-42','Klasifikasi pekerjaan','Kronologi pekerjaan','Hubungan aset','Terakhir Diubah di Maximo','23 Okt 2026, 14.51 WIB','BELUM TERSEDIA','Belum diverifikasi','NOT_ELIGIBLE','<details>','<code','0</dd>'])assert.ok(html.includes(label),label);
assert.ok(html.includes(raw));assert.ok(render(WorkOrderClock,{value:raw}).includes('dateTime="'+raw+'"'));
assert.ok(!html.includes('>UNKNOWN<'));assert.equal(row.source_detail.reported_at,raw);
assert.ok(render(WorkOrderSourceDetail,{row:{...row,source_detail:undefined}}).includes('TIDAK DIEKSPOS'));
const page=()=>({items:[structuredClone(row)],meta:{total:1,offset:0,limit:25,has_more:false}});
validateMaintenance(page(),row.equipment_id,0);
for(const detail of [[],{...row.source_detail,reported_at:'2026-02-30T07:51:51Z'},{...row.source_detail,work_order_number:{}},{...row.source_detail,asset_number:'x'.repeat(201)}]){const p=page();p.items[0].source_detail=detail;assert.throws(()=>validateMaintenance(p,row.equipment_id,0));}
const expanded={...row,source_detail:{...row.source_detail,fields:{description:{value:'<img src=x onerror=alert(1)> original WO',state:'SOURCE_VALUE',origin:'MAXIMO_RESPONSE'},priority:{value:null,state:'SOURCE_CONFIRMED_EMPTY',origin:'MAXIMO_RESPONSE'},estimated_duration_hours:{value:0,state:'RETAINED_LEGACY_VALUE',origin:'LEGACY_COLUMN'}}}};
const detailHtml=render(WorkOrderSourceDetail,{row:expanded});
assert(detailHtml.includes('&lt;img'));assert(!detailHtml.includes('<img'));
assert(detailHtml.includes('original WO'));assert(detailHtml.includes('Belum diisi di Maximo'));
assert(detailHtml.includes('Estimasi durasi sumber'));assert(detailHtml.includes('0</dd>'));
console.log('WO detail actual-component/date/offset/naive/null/zero/legacy/redaction contracts PASS');
if(process.argv.includes('--api-receipt')){
 const rows=JSON.parse(readFileSync(0,'utf8'));
 for(const row of rows){const p={items:[row],meta:{total:1,offset:0,limit:25,has_more:false}};validateMaintenance(p,row.equipment_id,0);const html=render(WorkOrderSourceDetail,{row});assert(html.includes('WO-SYNTHETIC-API'));assert(!html.includes('PRIVATE-PERSON'));}
 console.log(`API-to-actual-React WO receipt PASS: ${rows.length} serialized variants, zero skips`);
}
