import assert from 'node:assert/strict';
import {readFileSync,writeFileSync,mkdirSync} from 'node:fs';
import {resolve} from 'node:path';
import {pathToFileURL} from 'node:url';
import {browserBundle} from './localization-browser-build.mjs';
const {chromium}=await import(process.env.NADI_PLAYWRIGHT_MODULE?pathToFileURL(process.env.NADI_PLAYWRIGHT_MODULE).href:'playwright');
const Axe=process.env.NADI_AXE_MODULE?(await import(pathToFileURL(process.env.NADI_AXE_MODULE).href)).default:null;
const fixture=JSON.parse(readFileSync('fixtures/asset-evidence.synthetic.json')),product=JSON.parse(readFileSync('fixtures/ux-bundle-b.json'));
const asset=fixture.asset.canonical_id,origin='https://asset-evidence.synthetic.invalid',assetPath='/assets/'+encodeURIComponent(asset);
const bundle=await browserBundle('scripts/asset-evidence/entry.tsx');
const out=resolve(process.env.NADI_BROWSER_OUTPUT??'/tmp/nadi-sprint03/browser');mkdirSync(out,{recursive:true});
const browser=await chromium.launch({headless:true,...(process.env.NADI_CHROMIUM_EXECUTABLE?{executablePath:process.env.NADI_CHROMIUM_EXECUTABLE}:{})});
const ctx=await browser.newContext({viewport:{width:1440,height:1080}}),page=await ctx.newPage();
page.setDefaultTimeout(12000);page.setDefaultNavigationTimeout(15000);
const requests=[],errors=[],checks=[],shots=[],axe=[];let mode='normal';
page.on('pageerror',e=>errors.push(e.message));
const rows=Array.from({length:2000},(_,i)=>({...fixture.maintenance[i%5],canonical_id:'maintenance:SYNTHETIC-'+String(i).padStart(4,'0'),id:'SYNTHETIC-'+i,source_detail:{work_order_number:'SYNTHETIC-'+i,asset_number:'ASSET-SYNTHETIC',reported_at:'2026-10-23T07:51:51.123400Z',scheduled_start:null,scheduled_finish:null},actual_start:i===0?'2026-10-23T07:51:51Z':null,actual_finish:i===0?'2026-10-23T08:51:51Z':null,work_order_id:i<2?'WO:SYNTHETIC-SHARED':'WO:SYNTHETIC-'+i}));
// Synthetic valid raw code with no canonical mapping; no source data.
rows[0].event_type=null;rows[0].classification={raw_work_type:'CD',canonical_category:null,state:'UNMAPPED',origin:'RETAINED_MAXIMO_WORKTYPE',confidence:'UNRESOLVED',description:null,workflow_name:null,workflow_version:null,workflow_state:'NOT_AVAILABLE',status_state:'AVAILABLE'};
await ctx.route('**/*',async route=>{
 const req=route.request(),url=new URL(req.url());requests.push({path:url.pathname,query:url.search,method:req.method()});
 assert.equal(url.origin,origin,'all network must stay on intercepted synthetic origin');assert.equal(req.method(),'GET');
 if(req.resourceType()==='document')return route.fulfill({contentType:'text/html',body:'<!doctype html><html lang="id"><head><meta charset="utf-8"><title>NADI · SYNTHETIC Sprint3</title><link rel="stylesheet" href="/fixture.css"></head><body><div id="root"></div><script src="/fixture.js"></script></body></html>'});
 if(url.pathname==='/fixture.js')return route.fulfill({contentType:'application/javascript',body:bundle.js});
 if(url.pathname==='/fixture.css')return route.fulfill({contentType:'text/css',body:bundle.css});
 let status=200,data;const path=decodeURIComponent(url.pathname),q=url.searchParams,limit=Number(q.get('limit')??50),offset=Number(q.get('offset')??0);
 if(path.endsWith('/condition-evidence')){
   data=structuredClone(fixture.condition);data.items=data.items.slice(0,1);
   if(mode==='types')data=structuredClone(fixture.condition);
   if(mode==='unresolved'||mode==='ambiguous'||mode==='unknown'){data.items=[];data.expected_signals=0;data.mapping_readiness=mode==='ambiguous'?'MAPPING_AMBIGUOUS':mode==='unknown'?'MAPPING_UNKNOWN':'MAPPING_UNVERIFIED';data.statuses=['NO_VERIFIED_MAPPING'];}
   if(mode==='verified-empty'){data.items=[];data.expected_signals=0;data.statuses=['NO_APPROVED_SIGNALS'];}
   if(mode==='pi-conflict'){data.items.push(structuredClone(fixture.condition.items[1]));data.items[1].evidence.sources.pi.af_element_ref='SYNTHETIC-CONFLICT';}
   if(mode==='pi-403'){status=403;data={detail:'scope denied'};}
   if(mode==='service'){status=503;data={detail:'synthetic unavailable'};}
 }else if(path.endsWith('/maintenance-events')){
   assert.equal(q.get('asset_ref'),asset);assert(limit<=50);
   if(mode==='maintenance-403'){status=403;data={detail:'scope denied'};}
   else if(mode==='service'){status=503;data={detail:'synthetic unavailable'};}
   else {let selected=mode==='empty'?[]:rows;
     for(const [key,field] of [['status','status'],['event_type','event_type'],['work_order_id','work_order_id']])if(q.get(key))selected=selected.filter(r=>r[field]===q.get(key));
     const items=selected.slice(offset,offset+limit).map(row=>structuredClone(row));data={items,meta:{total:selected.length,offset,limit,has_more:offset+items.length<selected.length}};
     if(mode==='maintenance-invalid'&&limit===25)data.items[0].equipment_id='asset:FOREIGN';
   }
 }else if(path.endsWith('/assets'))data={items:[fixture.asset],meta:{total:1,offset:0,limit,has_more:false}};
 else if(path.endsWith('/'+asset))data=fixture.asset;
 else if(path.endsWith('/context')){status=403;data={detail:'portfolio capability required'};}
 else if(path.endsWith('/health/latest')){status=404;data={detail:'none'};}
 else if(['/fmea','/asset-health','/overhauls','/timeline','/health-assessments'].some(s=>path.endsWith(s)))data={items:[],meta:{total:0,offset,limit,has_more:false}};
 else throw new Error('Unexpected request '+path);
 return route.fulfill({status,contentType:'application/json',body:JSON.stringify(data)});
});
const go=async(path)=>{await page.goto(origin+path);await page.getByRole('heading',{name:'SYNTHETIC-03',exact:true}).first().waitFor();};
async function shot(name){await page.screenshot({path:resolve(out,name+'.png'),fullPage:true});shots.push(name+'.png');}
async function noOverflow(){assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));}
async function audit(name){if(Axe){const result=await new Axe({page}).withTags(['wcag2a','wcag2aa','wcag21a','wcag21aa']).analyze();axe.push({name,violations:result.violations});assert.deepEqual(result.violations.map(v=>v.id),[],name);}}
try{
 await page.goto(origin+'/assets?unit=SYNTHETIC-UNIT&search=SYNTHETIC');await page.getByRole('link',{name:'SYNTHETIC-03',exact:true}).waitFor();await shot('01-asset-register-desktop-light');await page.getByRole('link',{name:'SYNTHETIC-03',exact:true}).click();
 await page.locator('.condition-evidence-panel').waitFor();
 await page.getByText('0 mm/s',{exact:true}).waitFor();assert((await page.locator('main').innerText()).includes('NOT_QUALIFIED'));await shot('02-asset-condition-latest');
 const back=page.getByRole('link',{name:/Back to Asset|Kembali ke.*aset|Kembali ke Keandalan/i});
 assert(new URL(await back.first().getAttribute('href'),origin).searchParams.get('unit')==='SYNTHETIC-UNIT');
 console.log('stage maintenance');
 await page.getByRole('button',{name:'Pemeliharaan',exact:true}).click();await page.getByRole('status').filter({hasText:'2000 rekam sumber'}).waitFor();await audit('maintenance desktop');await shot('03-maintenance-register');
 assert.equal(await page.getByRole('table').locator('tbody tr').count(),25);await page.getByRole('cell',{name:/^CD/}).first().waitFor();assert((await page.locator('main').innerText()).includes('BELUM DIPETAKAN'));
 const before=requests.filter(r=>r.path.endsWith('maintenance-events')).length;
 await page.getByRole('button',{name:'Buka rekam SYNTHETIC-0',exact:true}).focus();await page.keyboard.press('Enter');await page.getByRole('heading',{name:'Detail rekam sumber Maximo'}).waitFor();assert.equal(await page.evaluate(()=>document.activeElement?.id),'maintenance-source-detail');assert.equal(requests.filter(r=>r.path.endsWith('maintenance-events')).length,before);await page.getByRole('heading',{name:'WO SYNTHETIC-0',exact:true}).waitFor();assert((await page.locator('#maintenance-source-detail').innerText()).includes('23 Okt 2026, 14.51 WIB'));await page.getByText('Identitas sumber, provenance dan detail teknis',{exact:true}).click();assert((await page.locator('#maintenance-source-detail').innerText()).includes('2026-10-23T07:51:51.123400Z'));await shot('04-maintenance-source-detail');
 await page.getByRole('button',{name:'Kembali ke register evidence'}).click();assert((await page.evaluate(()=>document.activeElement?.id)).startsWith('maintenance-open-'));
 console.log('stage filter');
 await page.getByLabel('Kategori kanonis (persis)',{exact:true}).fill('PM');await page.getByRole('button',{name:'Terapkan filter evidence'}).click();await page.getByRole('status').filter({hasText:'800 rekam sumber'}).waitFor();
 await page.getByRole('button',{name:'Halaman berikutnya'}).click();await page.waitForURL(/me_offset=25/);await page.getByRole('status').filter({hasText:'800 rekam sumber'}).waitFor();
 assert(requests.some(r=>r.query.includes('offset=25')&&r.query.includes('event_type=PM')));await page.goBack();await page.waitForURL(url=>!url.searchParams.has('me_offset'));checks.push('exact asset filters, paging, keyboard detail/return, browser-back');
 console.log('stage inspection context');
 await page.goto(origin+'/pdm?record='+product.inspections[0].record_id+'&per_page=5&method=VIBRATION&pdm_offset=10');await page.getByRole('link',{name:'Evidence aset · Maximo / PI'}).click();await page.locator('.condition-evidence-panel').waitFor();const pdmBack=page.getByRole('link',{name:'← Kembali ke inspeksi PdM'});const href=await pdmBack.getAttribute('href');assert.equal(new URL(href,origin).searchParams.get('record'),product.inspections[0].record_id);assert.equal(new URL(href,origin).searchParams.get('per_page'),'5');assert.equal(new URL(href,origin).searchParams.get('pdm_offset'),'10');await pdmBack.click();assert.equal(new URL(page.url()).searchParams.get('record'),product.inspections[0].record_id);checks.push('inspection→asset→exact inspection plus prior filter/page context');
 console.log('stage PI states');
 mode='types';await go(assetPath);await page.getByText('0 mm/s',{exact:true}).waitFor();for(const text of ['false','NULL · nilai tidak tersedia','code=0','Questionable: true'])assert((await page.locator('main').innerText()).includes(text));await page.locator('summary').filter({hasText:'Detail sumber PI'}).first().click();await page.locator('summary').filter({hasText:'Crosswalk Maximo'}).click();await shot('05-pi-source-crosswalk');checks.push('original zero/false/null/text/digital code; clocks, raw quality, stale/unknown source; lineage');
 for(const state of ['unresolved','ambiguous','unknown','verified-empty','pi-conflict','pi-403']){mode=state;await go(assetPath);await page.waitForFunction(()=>!document.querySelector('.condition-evidence-panel .loading-state'));const content=await page.locator('.condition-evidence-panel').innerText();if(state==='pi-403'){assert(content.includes('403'));assert(!content.includes('Coba muat ulang'));await shot('06-condition-403');}else if(state==='pi-conflict'){assert(content.includes('tidak memenuhi kontrak'));assert(!content.includes('0 mm/s'));}else {assert(!content.includes('0 mm/s'));if(state==='ambiguous')await shot('07-ambiguous-mapping');}}checks.push('mapping missing/ambiguous/unknown, verified-no-signal, contradictory PI and403 fail closed');
 for(const state of ['empty','maintenance-403','maintenance-invalid','service']){mode=state;await go(assetPath+'?tab=maintenance');await page.waitForFunction(()=>!document.querySelector('[aria-label="Evidence pemeliharaan Maximo"] .loading-state'));const content=await page.locator('[aria-label="Evidence pemeliharaan Maximo"]').innerText();if(state==='empty'){assert(content.includes('Tidak ada rekam'));await shot('08-maintenance-empty');}if(state==='maintenance-403')assert(content.includes('403')&&!content.includes('Coba muat ulang'));if(state==='maintenance-invalid')assert(!content.includes('WO:SYNTHETIC-SHARED'));if(state==='service')assert(content.includes('tidak tersedia'));}checks.push('empty/error/access/foreign identity handling');
 mode='normal';
 console.log('stage responsive');
 for(const width of [390,768,1440])for(const theme of ['light','dark']){await page.setViewportSize({width,height:1000});await page.addInitScript(value=>localStorage.setItem('nadi-theme',value),theme);await go(assetPath+'?tab=maintenance');await page.getByRole('status').filter({hasText:'2000 rekam sumber'}).waitFor();await page.evaluate(value=>document.documentElement.setAttribute('data-theme',value),theme);await noOverflow();await audit(width+'-'+theme);if(width===390||width===1440)await shot('09-maintenance-'+width+'-'+theme);await page.getByRole('button',{name:'Buka rekam SYNTHETIC-0',exact:true}).click();await page.getByRole('heading',{name:'WO SYNTHETIC-0',exact:true}).waitFor();await noOverflow();await audit('detail-'+width+'-'+theme);await shot('10-wo-detail-'+width+'-'+theme);await page.getByRole('button',{name:'Kembali ke register evidence'}).click();await page.getByRole('button',{name:'Buka rekam SYNTHETIC-1',exact:true}).click();await page.getByRole('heading',{name:'WO SYNTHETIC-1',exact:true}).waitFor();assert((await page.locator('#maintenance-source-detail').innerText()).includes('BELUM TERSEDIA'));await noOverflow();}
 checks.push('390/768/1440 responsive light/dark, no horizontal document overflow; WCAG automated tested states');
 assert(!requests.some(r=>/pi-mapping|history|snapshots|collector|j_security/.test(r.path)));assert.equal(errors.length,0,errors.join('\n'));
 writeFileSync(resolve(out,'results.json'),JSON.stringify({label:'SYNTHETIC ONLY',checks,requests:requests.length,errors,shots,axe:axe.map(a=>({name:a.name,violations:a.violations.length})),population:2000,maxMaintenanceRows:25},null,2));
 console.log('Sprint3 browser PASS '+checks.length+' groups / '+shots.length+' screenshots / '+axe.length+' axe states');
}catch(error){console.log('FAILED URL',page.url());console.log((await page.locator('main').innerText()).slice(0,2500));await page.screenshot({path:resolve(out,'failure.png'),fullPage:true});throw error;}finally{await browser.close();}
