// Network-isolated mounted component checks. No server, login, TLS override or DB.
import assert from 'node:assert/strict';
import {mkdirSync,writeFileSync} from 'node:fs';
import {resolve} from 'node:path';
import {pathToFileURL} from 'node:url';
import {browserBundle} from './localization-browser-build.mjs';
const {chromium}=await import(process.env.NADI_PLAYWRIGHT_MODULE?pathToFileURL(process.env.NADI_PLAYWRIGHT_MODULE).href:'playwright');
const out=resolve(process.env.NADI_BROWSER_OUTPUT??'/tmp/nadi-source-history-browser');mkdirSync(out,{recursive:true});
const bundle=await browserBundle('scripts/pdm-source-history/entry.tsx');
const browser=await chromium.launch({headless:true});
const checks=[],errors=[],requests=[],base='https://history.synthetic.invalid';let mode='ready';
const check=(label,value)=>{assert.ok(value,label);checks.push(label);console.log('PASS '+label);};
const clock={role:'UNSPECIFIED',precision:'DATE',value:'2019-01-03',raw_value:'Conflicting original 2020-02-04'};
const event={event_key:'a'.repeat(64),source_ref:'WB-SYNTHETIC',source_sha256:'c'.repeat(64),sheet_index:0,sheet_label:'Peralatan DEMO',profile_id:'profile-synthetic',axis:'ROW',position:3,kind:'MEASUREMENT_SOURCE',classification:'RAW_UNRESOLVED',source_asset_label:'Label DEMO belum dipetakan',clocks:[clock],reasons:['UNIT_UNKNOWN'],distinct_source_cells:3,canonical_eligible:false};
const field=(id,raw_value)=>({field_id:id,cell:'B3',role:'INPUT',label_claim:'Velocity DEMO',unit_claim:null,source_point_claim:null,source_axis_claim:null,value:{coordinate:'B3',raw_value,formula_present:raw_value===null,formula_xml:raw_value===null?{expression:'1+1'}:null,cache_status:raw_value===null?'NO_STORED_FORMULA_RESULT':'NOT_FORMULA'},headers:[],unit_evidence:[]});
try{
 const ctx=await browser.newContext({locale:'en-US',timezoneId:'Pacific/Kiritimati',viewport:{width:1440,height:1100}}),p=await ctx.newPage();
 p.setDefaultTimeout(10000);
 p.on('pageerror',error=>errors.push(error.message));
 await ctx.route('**/*',async route=>{
  const request=route.request(),url=new URL(request.url()),path=url.pathname;requests.push({method:request.method(),path,query:url.search});
  if(url.origin!==base){errors.push('Unexpected origin');return route.abort();}
  if(path==='/candidate.js')return route.fulfill({contentType:'application/javascript',body:bundle.js});
  if(path==='/candidate.css')return route.fulfill({contentType:'text/css',body:bundle.css});
  if(request.isNavigationRequest())return route.fulfill({contentType:'text/html',body:'<!doctype html><html lang="id"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="/candidate.css"></head><body><div id="root"></div><script src="/candidate.js"></script></body></html>'});
  if(request.method()!=='GET'){errors.push('Unexpected write');return route.abort();}
  if(mode!=='ready')return route.fulfill({status:mode==='forbidden'?403:mode==='expired'?401:503,json:{detail:{code:mode==='forbidden'?'HISTORY_AUTHOR_SCOPE_REQUIRED':mode==='expired'?'SESSION_REQUIRED':'HISTORY_SCHEMA_PREREQUISITE'}}});
  if(path.endsWith('/batches'))return route.fulfill({json:{scope:'AUTHORIZED_PROVISIONAL_SOURCE',items:[{batch_id:'b'.repeat(64),state:'COMPLETE',counts:{cells:3,events:2},coverage:[{source_ref:'WB-SYNTHETIC',sheet_index:0,sheet_label:'Peralatan DEMO',populated_cells:3,terminal_cells:{INPUT:2,UNCLASSIFIED:1},overlapping_value_claim_cells:0}]}],has_more:false,next_after:null}});
  if(path.endsWith('/source-history')){const next=!!url.searchParams.get('after');return route.fulfill({json:{scope:'AUTHORIZED_PROVISIONAL_SOURCE',items:[next?{...event,event_key:'d'.repeat(64),clocks:[],kind:'RAW_SOURCE_ROW'}:event],total:2,has_more:!next,next_after:next?null:event.event_key}});}
  if(path.endsWith(event.event_key)){const next=url.searchParams.get('offset')==='2';return route.fulfill({json:{item:event,fields:next?[field('last','RAW text retained')]:[field('zero',0),field('formula',null)],field_total:3,offset:next?2:0,limit:next?1:2,has_more:!next,next_offset:next?null:2,previous_offset:next?0:null,clock_evidence:[{coordinate:'A3',raw_value:clock.raw_value}],aliases:[{record_id:'inspection:SYNTHETIC',source_revision:1,current_revision:9,relation:'SOURCE_PARTIAL'}],profile_version:'SYNTHETIC-1',classification_hash:'e'.repeat(64),editable:false,canonical_eligible:false}});}
  errors.push('Unexpected path '+path);return route.abort();
 });
 await p.goto(base+'/pdm');await p.getByRole('button',{name:'Baca kelompok sumber',exact:true}).waitFor();
 check('Indonesian source date with date-only precision',await p.getByText('3 Januari 2019',{exact:true}).isVisible());
 check('provisional and unmapped context explicit',(await p.textContent('main')).includes('belum menjadi measurement kanonis'));
 await p.getByRole('button',{name:'Baca kelompok sumber',exact:true}).click();await p.getByRole('region',{name:'Detail kelompok sumber'}).waitFor();
 check('zero and null remain distinct',(await p.locator('section[aria-label="Detail kelompok sumber"] tbody tr').first().locator('td').nth(1).textContent()).startsWith('0')&&(await p.locator('section[aria-label="Detail kelompok sumber"] tbody tr').nth(1).locator('td').nth(1).textContent()).startsWith('Kosong'));
 check('unknown unit is explicit',await p.getByText('Unit belum diketahui',{exact:false}).count()===2);
 await p.getByText('Alasan, versi dan jejak sumber',{exact:true}).click();
 check('conflicting raw date remains accessible',(await p.textContent('main')).includes(clock.raw_value));
 check('immutable source alias and current revision separated',(await p.textContent('main')).includes('revisi sumber 1, revisi kini 9'));
 for(const width of [1440,390]){
  await p.setViewportSize({width,height:1100});check('no page overflow '+width,await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await p.screenshot({path:out+'/detail-'+width+'.png',fullPage:true});
 }
 await p.getByRole('button',{name:'Nilai berikutnya',exact:true}).click();await p.getByRole('cell',{name:/RAW text retained/}).waitFor();check('detail advances actual byte-bounded cursor',requests.some(r=>r.path.endsWith(event.event_key)&&r.query.includes('offset=2')));
 await p.getByRole('button',{name:'Nilai sebelumnya',exact:true}).click();await p.getByRole('cell',{name:/Kosong/}).waitFor();
 await p.getByRole('button',{name:'Halaman berikutnya',exact:true}).click();await p.getByRole('cell',{name:/^Baris RAW \/ konteks sumber/}).waitFor();check('source keyset next page navigable',await p.getByText('Tanggal sumber belum diketahui',{exact:true}).isVisible());
 for(const [value,text] of [['forbidden','Akun ini tidak memiliki akses ke riwayat sumber.'],['unavailable','Riwayat sumber belum disiapkan pada backend ini.'],['expired','Sesi berakhir. Silakan masuk kembali.']]){
  mode=value;await p.reload();await p.getByText(text,{exact:true}).waitFor();check('access/schema/session distinction '+value,true);
 }
 check('no browser errors or unexpected network',errors.length===0);check('GET-only requests',requests.every(r=>r.method==='GET'));
 writeFileSync(out+'/results.json',JSON.stringify({checks,errors,requests},null,2));console.log('Source history browser checks '+checks.length);
}catch(error){writeFileSync(out+'/failure.json',JSON.stringify({error:String(error),checks,errors,requests},null,2));throw error;}finally{await browser.close();}
