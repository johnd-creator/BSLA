// Actual mounted components. Every request is intercepted; no listening server,
// operational login, source access, TLS bypass, or live database.
import assert from 'node:assert/strict';
import {mkdirSync,writeFileSync} from 'node:fs';
import {resolve} from 'node:path';
import {pathToFileURL} from 'node:url';
import {browserBundle} from './localization-browser-build.mjs';
const {chromium}=await import(process.env.NADI_PLAYWRIGHT_MODULE?pathToFileURL(process.env.NADI_PLAYWRIGHT_MODULE).href:'playwright');
const out=resolve(process.env.NADI_BROWSER_OUTPUT??'/tmp/nadi-pdm-date-evidence');mkdirSync(out,{recursive:true});
const bundle=await browserBundle('scripts/pdm-date/entry.tsx');
const browser=await chromium.launch({headless:true,...(process.env.NADI_CHROMIUM_EXECUTABLE?{executablePath:process.env.NADI_CHROMIUM_EXECUTABLE}:{})});
const checks=[],errors=[],requests=[],base='https://pdm-dates.synthetic.invalid';
const check=(label,result)=>{assert.ok(result,label);checks.push(label);console.log('PASS '+label);};
const asset='asset:SYNTHETIC:A',record='inspection:SYNTHETIC-DATE',instant='2026-10-20T23:30:00Z';
const sourceClock=(precision,value,raw_value,role='SAMPLE')=>({role,precision,value,raw_value,source_label:'DEMO claim '+precision});
const clocks=[sourceClock('DATE','2019-01-03','Conflicting raw claim: 2020-02-04'),sourceClock('DATETIME','2019-01-03T00:15+09:00','Reported WIT clock','ANALYSIS'),sourceClock('LOCAL_DATETIME','2019-01-03T14:30','Local clock','REPORT'),sourceClock('TIME','14:30','Time-only clock'),sourceClock('RAW',null,'03/01/2019 / 43865'),sourceClock('UNKNOWN',null,null)];
const measurement={point_ref:'point:DEMO',quantity:'DEMO vibration',value:0,unit:'mm/s',quality:'INSPECTOR_REPORTED',provenance:'HUMAN_ENTERED_MEASUREMENT',measured_at:instant};
const native={record_id:record,canonical_asset_id:asset,revision:2,status:'DRAFT',created_by:'synthetic-author',inspector_ref:'synthetic-author',method:'VIBRATION',method_version:'synthetic',inspected_at:instant,created_at:instant,updated_at:'2026-10-21T00:15:00+09:00',review:null,field_approval:'ENGINEER_FIELDS_PENDING',assessment:'NOT_ASSESSED',operating_context:'DEMO steady regime',observations:['DEMO date fixture'],interpretations:[],measurements:[measurement,{...measurement,measured_at:'2026-10-21T00:15:00+09:00'}],attachments:[],case_refs:[],method_extension:{instrument_ref:'DEMO instrument',procedure_ref:'DEMO procedure',orientation:'DEMO horizontal'},provenance:'NADI_MANUAL_INSPECTION'};
const capture={schema_version:'1.0',purpose:'PROVISIONAL_INPUT_ONLY',source_ref:'DEMO-WORKBOOK',source_sha256:null,sheet_index:0,profile_id:'DEMO-PROFILE',profile_version:'synthetic',clocks,rows:[{row_id:'source-0',source_label:'DEMO field',raw_value:'0',unit:null,source_point:null,source_axis:null,header_cells:[],value_origin:'SOURCE_LITERAL',row_role:'INPUT',contexts:[],clock:clocks[0]}]};
let sourceMode=false;
try {
 // Browser locale intentionally differs; the product must remain Indonesian.
 for(const timezoneId of ['America/Los_Angeles','Pacific/Kiritimati']){
  const ctx=await browser.newContext({locale:'en-US',timezoneId,viewport:{width:1440,height:1100}}),p=await ctx.newPage();
  p.on('pageerror',error=>errors.push(error.message));
  await ctx.route('**/*',async route=>{
   const request=route.request(),url=new URL(request.url()),path=decodeURIComponent(url.pathname);requests.push({method:request.method(),url:request.url()});
   if(url.origin!==base){errors.push('Unexpected origin '+url.origin);return route.abort('blockedbyclient');}
   if(path==='/candidate.js')return route.fulfill({contentType:'application/javascript',body:bundle.js});
   if(path==='/candidate.css')return route.fulfill({contentType:'text/css',body:bundle.css});
   if(request.isNavigationRequest())return route.fulfill({contentType:'text/html',body:'<!doctype html><html lang="id"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="/candidate.css"></head><body><div id="root"></div><script src="/candidate.js"></script></body></html>'});
   if(request.method()!=='GET'){errors.push('Unexpected mutation');return route.abort();}
   const row=sourceMode?{...native,inspected_at:null,measurements:[],input_capture:capture}:native;
   if(path==='/api/engineering-qa/asset-context/'+asset)return route.fulfill({json:{canonical_asset_id:asset,identity_availability:'AVAILABLE',identity:{description:'DEMO equipment',location_ref:'DEMO AREA'}}});
   if(path==='/api/engineering-qa/session')return route.fulfill({json:{subject:'synthetic-author',roles:['AUTHOR'],asset_ids:[asset],csrf_token:'SYNTHETIC_NON_SESSION'}});
   // This date fixture has no imported full-source batch; keep the GET contract explicit.
   if(path==='/api/engineering-qa/source-history/batches')return route.fulfill({json:{scope:'AUTHORIZED_PROVISIONAL_SOURCE',items:[],has_more:false,next_after:null}});
   if(path==='/api/engineering-qa/source-history')return route.fulfill({json:{scope:'AUTHORIZED_PROVISIONAL_SOURCE',items:[],total:0,has_more:false,next_after:null}});
   if(path==='/api/engineering-qa/inspections/measurement-history')return route.fulfill({json:{items:native.measurements.map((m,i)=>({...native,measurement:m,measurement_index:i})),total:2,offset:0,limit:25,has_more:false,filter_scope:'AUTHORIZED_POPULATION',event_time_basis:'MEASURED_AT'}});
   if(path.endsWith('/history'))return route.fulfill({json:[{revision:1,action:'CREATE',actor:'synthetic-author',occurred_at:instant,reason:'DEMO audit reason',snapshot:row}]});
   if(path==='/api/engineering-qa/inspections/'+record)return route.fulfill({json:row});
   if(path==='/api/engineering-qa/inspections')return route.fulfill({json:{items:[row],total:1,offset:0,limit:Number(url.searchParams.get('limit')??25),has_more:false,filter_scope:'AUTHORIZED_POPULATION',event_time_basis:'INSPECTED_AT'}});
   errors.push('Unexpected path '+path);return route.abort();
  });
  const button=name=>p.getByRole('button',{name,exact:name!=='Buka inspeksi'}),go=async()=>{await p.goto(base+'/pdm');await button('Buka inspeksi').waitFor();};
  sourceMode=false;await go();
  check('register known instant in WIB '+timezoneId,await p.locator('.pdm-register').getByText('21 Oktober 2026, 06.30.00 WIB',{exact:true}).isVisible());
  await button('Buka inspeksi').click();await p.locator('.product-record-detail').waitFor();
  check('detail same instant as list '+timezoneId,await p.locator('.asset-facts').getByText('21 Oktober 2026, 06.30.00 WIB',{exact:true}).count()===2);
  check('record provenance starts secondary without hiding measurement time '+timezoneId,!await p.locator('.inspection-provenance').getByText('20 Oktober 2026, 22.15.00 WIB',{exact:true}).isVisible());
  await p.locator('.inspection-provenance > summary').click();
  check('application revision crosses to correct WIB day '+timezoneId,await p.locator('.asset-facts').getByText('20 Oktober 2026, 22.15.00 WIB',{exact:true}).isVisible());
  const original=p.locator('.asset-facts details').first();await original.locator('summary').click();
  check('original ISO available in detail '+timezoneId,await original.getByText(instant,{exact:true}).isVisible());
  await button('Baca riwayat').click();await p.getByText('DEMO audit reason',{exact:true}).waitFor();
  check('audit time consistently WIB and separately labelled '+timezoneId,await p.getByText('Dicatat di NADI (audit)',{exact:true}).isVisible());
  await p.getByText('Baca isi revisi 1',{exact:true}).click();
  check('immutable revision retains native measurement time '+timezoneId,await p.locator('details[open] .product-record-detail').getByText('21 Oktober 2026, 06.30.00 WIB',{exact:true}).count()===3);
  await button('Riwayat & Tren').click();await p.locator('[aria-label="Riwayat measurement asli"] table').waitFor();
  check('measurement history same WIB as detail '+timezoneId,await p.locator('[aria-label="Riwayat measurement asli"] table').getByText('21 Oktober 2026, 06.30.00 WIB',{exact:true}).isVisible());
  await p.getByLabel('Plot sampel pada halaman ini (satu inspeksi)').selectOption(record);
  check('scatter labels use same known instant format '+timezoneId,(await p.locator('.pdm-raw-plot svg').textContent()).includes('21 Oktober 2026, 06.30.00 WIB'));
  await button('Input Pengukuran').click();
  await p.getByLabel('Waktu inspeksi asli (ISO + zona waktu)').fill('2026-10-20T23:30:00Z');
  check('native form readable preview preserves literal input '+timezoneId,await p.getByText('21 Oktober 2026, 06.30.00 WIB',{exact:true}).isVisible()&&await p.getByLabel('Waktu inspeksi asli (ISO + zona waktu)').inputValue()===instant);
  sourceMode=true;await go();
  const register=p.locator('.pdm-register');
  check('source list shows date-only without invented midnight '+timezoneId,await register.getByText('3 Januari 2019',{exact:true}).isVisible());
  check('source datetime retains reported WIT '+timezoneId,await register.getByText('3 Januari 2019, 00.15 WIT',{exact:true}).isVisible());
  check('source list clearly labels ambiguous local and time '+timezoneId,await register.getByText('3 Januari 2019, 14.30 zona waktu belum diketahui',{exact:true}).isVisible()&&await register.getByText('14.30 · tanggal dan zona waktu belum diketahui',{exact:true}).isVisible());
  await button('Buka inspeksi').click();await p.getByText('Data sumber provisional · nilai asli, formula & provenance',{exact:true}).click();await p.locator('.pdm-source-clock').first().waitFor();
  const clock=p.locator('.pdm-source-clock').first();
  check('source detail same date as list '+timezoneId,await clock.getByText('3 Januari 2019',{exact:true}).isVisible());
  await clock.locator('summary').click();
  check('conflicting raw claim preserved alongside explicit date '+timezoneId,(await clock.textContent()).includes('Conflicting raw claim: 2020-02-04')&&(await clock.textContent()).includes('2019-01-03'));
  for(const width of [1440,768,390]){
   await p.setViewportSize({width,height:1100});
   check('source detail no page overflow '+timezoneId+' '+width,await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
   if(timezoneId==='America/Los_Angeles'){await p.screenshot({path:out+'/source-detail-'+width+'.png',fullPage:true});await clock.screenshot({path:out+'/source-clock-'+width+'.png'});}
  }
  await button('Baca riwayat').click();await p.getByText('Baca isi revisi 1',{exact:true}).click();
  await p.locator('details[open] .product-record-detail').getByText('Data sumber provisional · nilai asli, formula & provenance',{exact:true}).click();
  check('source immutable revision same date '+timezoneId,await p.locator('details[open] .product-record-detail .pdm-source-clock').first().getByText('3 Januari 2019',{exact:true}).isVisible());
  await button('Ubah draf inspeksi').click();
  const explicit=p.getByLabel('Nilai waktu eksplisit',{exact:true}).first();
  check('source form readable date preview retains stored precision '+timezoneId,await explicit.inputValue()==='2019-01-03'&&await explicit.locator('..').getByText('3 Januari 2019',{exact:true}).isVisible());
  await ctx.close();
 }
 check('no browser errors or unexpected network requests',errors.length===0);
 check('no write requests',requests.every(r=>r.method==='GET'));
 writeFileSync(out+'/results.json',JSON.stringify({checks,errors,request_count:requests.length},null,2));
 console.log('PdM date browser checks: '+checks.length+'; evidence '+out);
} catch(error) {writeFileSync(out+'/failure.json',JSON.stringify({error:String(error),checks,errors,requests},null,2));throw error;} finally {await browser.close();}
