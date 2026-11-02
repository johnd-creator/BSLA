// Every request is intercepted: synthetic components, no server/live QA or source access.
import assert from 'node:assert/strict';
import {readFileSync,writeFileSync,mkdirSync} from 'node:fs';
import {resolve} from 'node:path';
import {pathToFileURL} from 'node:url';
import {browserBundle} from './localization-browser-build.mjs';
import {pdmKeyboardChecks} from './pdm-keyboard-browser.mjs';
const {chromium}=await import(process.env.NADI_PLAYWRIGHT_MODULE?pathToFileURL(process.env.NADI_PLAYWRIGHT_MODULE).href:'playwright');
const base='https://pdm.synthetic.invalid',out=resolve(process.env.NADI_BROWSER_OUTPUT??'/tmp/nadi-pdm-input-evidence');mkdirSync(out,{recursive:true});
const bundle=await browserBundle(),browser=await chromium.launch({headless:true}),checks=[],errors=[],commands=[];
const check=(label,result)=>{assert.ok(result,label);checks.push(label);console.log('PASS '+label);};
const ctx=await browser.newContext({viewport:{width:1440,height:1086}}),p=await ctx.newPage();p.on('pageerror',e=>errors.push(e.message));
const asset='asset:SYNTHETIC:A',time='2026-10-09T01:00:00Z';let subject='synthetic-author',role='AUTHOR',failSave=true,failLink=true,denied=0,proof=true;const inspections=[],cases=[],receipts=new Map(),audit=new Map();
// Distinct browser tabs model distinct legitimate actors. A retained reviewer
// must never inherit the author tab's global fixture identity during focus/timer refresh.
const pageIdentities=new Map(),sessionReads=[];
const pageOf=(items,url,basis='INSPECTED_AT')=>{const offset=Number(url.searchParams.get('offset')??0),limit=Number(url.searchParams.get('limit')??25);return {items:items.slice(offset,offset+limit),total:items.length,offset,limit,has_more:offset+limit<items.length,...(proof?{filter_scope:'AUTHORIZED_POPULATION',event_time_basis:basis}:{})};};
await ctx.route('**/*',async route=>{
 const r=route.request(),u=new URL(r.url()),path=u.pathname,method=r.method();
 const actor=pageIdentities.get(r.frame().page())??{subject,role};
 if(u.origin!==base)return route.abort('blockedbyclient');
 if(path==='/candidate.js')return route.fulfill({contentType:'application/javascript',body:bundle.js});
 if(path==='/candidate.css')return route.fulfill({contentType:'text/css',body:bundle.css});
 if(path==='/logo_nadi.png')return route.fulfill({contentType:'image/png',body:readFileSync('public/logo_nadi.png')});
 if(r.isNavigationRequest())return route.fulfill({contentType:'text/html',body:'<!doctype html><html lang="id"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="/candidate.css"></head><body><div id="root"></div><script src="/candidate.js"></script></body></html>'});
 if(!path.startsWith('/api/engineering-qa/'))return route.fulfill({status:404,body:''});
 const [resource,idRaw,action]=path.slice('/api/engineering-qa/'.length).split('/'),id=decodeURIComponent(idRaw??'');
 const fail=(status,code)=>route.fulfill({status,json:{detail:{code}}});
 if(resource==='session'){if(denied)return fail(denied,'AUTHENTICATION_REQUIRED');sessionReads.push({page:r.frame().page(),subject:actor.subject});return route.fulfill({json:{subject:actor.subject,roles:[actor.role],asset_ids:[asset],csrf_token:'SYNTHETIC_NON_SESSION'}});}
 if(denied)return fail(denied,'FORBIDDEN');
 if(resource==='asset-context')return route.fulfill({json:{canonical_asset_id:asset,identity_availability:'AVAILABLE',identity:{description:'DEMO — equipment sintetis',location_ref:'SYNTHETIC AREA'}}});
 if(resource==='source-history'&&method==='GET')return route.fulfill({json:{scope:'AUTHORIZED_PROVISIONAL_SOURCE',items:[],total:0,has_more:false,next_after:null}});
 if(resource==='inspections'&&id==='measurement-history'){
  let events=inspections.flatMap(row=>row.measurements.map((measurement,measurement_index)=>({...row,measurement,measurement_index})));
  for(const [param,key] of [['point','point_ref'],['quantity','quantity']])if(u.searchParams.get(param))events=events.filter(e=>e.measurement[key]===u.searchParams.get(param));
  return route.fulfill({json:pageOf(events,u,'MEASURED_AT')});
 }
 const rows=resource==='inspections'?inspections:cases;let row=rows.find(x=>(x.record_id??x.case_id)===id);
 if(method==='GET'){
  if(action==='history'){const events=audit.get(id)??[];const offset=Number(u.searchParams.get('offset')??0),limit=Number(u.searchParams.get('limit')??1);return route.fulfill({json:events.slice(offset,offset+limit)});}
  if(id)return row?route.fulfill({json:row}):fail(404,'NOT_FOUND');
  let result=rows;
  if(u.searchParams.get('status'))result=result.filter(x=>x.status===u.searchParams.get('status'));
  if(u.searchParams.get('method'))result=result.filter(x=>x.method===u.searchParams.get('method'));
  if(u.searchParams.get('search'))result=result.filter(x=>x.observations?.join(' ').includes(u.searchParams.get('search')));
  return route.fulfill({json:pageOf(result,u)});
 }
 const body=r.postDataJSON();commands.push({resource,id,action,body});
 check('CSRF unchanged '+commands.length,r.headers()['x-csrf-token']==='SYNTHETIC_NON_SESSION');
 if(failSave&&resource==='inspections'&&!id){failSave=false;return fail(503,'QA_BACKEND_UNAVAILABLE');}
 if(receipts.has(body.request_id))return route.fulfill({json:receipts.get(body.request_id)});
 if(row&&body.expected_revision!==row.revision)return fail(409,'REVISION_CONFLICT');
 if(!id){row={...body.draft,[resource==='cases'?'case_id':'record_id']:resource==='cases'?'case:SYNTHETIC-INPUT':'inspection:SYNTHETIC-INPUT',created_by:actor.subject,status:'DRAFT',revision:1,created_at:time,updated_at:time,review:null,contributors:[actor.subject],review_started_by:null,field_approval:'ENGINEER_FIELDS_PENDING',assessment:'NOT_ASSESSED',provenance:'NADI_MANUAL_INSPECTION',attachments:body.draft.attachments??[],case_refs:[],method_extension:body.draft.method_extension??{}};rows.push(row);}
 else if(method==='PUT')Object.assign(row,{...body.draft,revision:row.revision+1});
 else if(action==='submit'){row.status='SUBMITTED';row.revision++;}
 else if(action==='begin_review'){if(actor.subject===row.created_by)return fail(403,'INDEPENDENT_REVIEWER_REQUIRED');row.status='UNDER_REVIEW';row.review_started_by=actor.subject;row.revision++;}
 else if(action==='review'){row.status=body.decision;row.review={decision:body.decision,reviewer:actor.subject,decided_at:time,rationale:body.reason};row.revision++;}
 else if(action==='revise'){row.status='DRAFT';row.review=null;row.review_started_by=null;row.revision++;}
 else if(action==='evidence'){if(failLink){failLink=false;return fail(503,'QA_BACKEND_UNAVAILABLE');}check('handoff binds exact approved inspection revision',body.expected_inspection_revision===inspections[0].revision);row.evidence=[{record_id:inspections[0].record_id,stable_version:'SYNTHETIC-SHA',kind:'MANUAL_INSPECTION'}];row.revision++;}
 const key=row.record_id??row.case_id;const events=audit.get(key)??[];events.push({revision:row.revision,actor:actor.subject,action:action??(method==='PUT'?'UPDATE':'CREATE'),occurred_at:time,reason:body.reason??'SYNTHETIC',snapshot:structuredClone(row)});audit.set(key,events);receipts.set(body.request_id,structuredClone(row));return route.fulfill({json:row});
});
const button=name=>p.getByRole('button',{name,exact:true});const go=async()=>{await p.goto(base+'/pdm',{waitUntil:'networkidle'});await button('Input Pengukuran').waitFor();};
async function evidence(name){for(const width of [1440,768,390]){await p.setViewportSize({width,height:1086});check('no page overflow '+name+' '+width,await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await p.evaluate(()=>window.scrollTo(0,0));await p.screenshot({path:out+'/'+name+'-'+width+'.png',fullPage:true});}}
try{
 await go();
 const advanced=p.locator('.workspace-filters > summary');await advanced.focus();await p.keyboard.press('Enter');
 check('advanced time filters open by keyboard',await p.getByLabel('Waktu awal (ISO + zona waktu)').isVisible());
 const timeBasis=p.locator('.workspace-filters .help-details > summary');await timeBasis.focus();await p.keyboard.press('Enter');
 check('secondary time-basis guidance opens by keyboard',await p.getByText('Filter register memakai waktu inspeksi asli; filter riwayat memakai waktu measurement asli. Waktu yang belum diketahui tidak dimasukkan ke rentang waktu yang dipilih.',{exact:true}).isVisible());
 await timeBasis.focus();await p.keyboard.press('Enter');
 await advanced.focus();await p.keyboard.press('Enter');
 check('advanced filters collapse without hiding main search',!(await p.getByLabel('Waktu awal (ISO + zona waktu)').isVisible())&&await p.getByLabel('Cari inspeksi / observasi').isVisible());
 await pdmKeyboardChecks({p,button,go,check,out});
 // Workbook candidates: same mounted components, all network responses intercepted.
 const workbookOut=resolve(process.env.NADI_WORKBOOK_OUTPUT??out+'/workbook-candidates');mkdirSync(workbookOut,{recursive:true});
 for(const [context,method,units] of [['AREA_FAN','TRIBOLOGY',['Cst','mgKOH/g','ppm']],['AREA_MILL','TRIBOLOGY',['%','mg KOH/g','ppm']],['LOGSHEET_6KV','MCSA',['%','Ω','dB']]]){
  await go();await button('Input Pengukuran').click();await p.getByLabel('Konteks input kandidat').selectOption(context);
  check('workbook context never changes method '+context,await p.getByLabel('Metode',{exact:true}).inputValue()==='VIBRATION');
  check('workbook candidate requires explicit method '+context,await button('Gunakan baris kandidat').isDisabled());
  await p.getByLabel('Metode',{exact:true}).selectOption(method);await button('Gunakan baris kandidat').click();
  check('workbook creates only three native rows '+context,await p.locator('.pdm-measurement-row').count()===3);
  check('workbook version and pending label '+context,await p.getByText(/candidate-0.1.0/).isVisible()&&await p.locator('.pdm-workbook-template').getByText('Menunggu Validasi Engineer',{exact:true}).isVisible());
  for(let i=1;i<=3;i++){
   check('literal source unit '+context+' '+i,await p.getByLabel('Unit asli '+i,{exact:true}).inputValue()===units[i-1]);
   check('point and time unresolved '+context+' '+i,await p.getByLabel('Titik '+i,{exact:true}).inputValue()===''&&await p.getByLabel('Waktu measurement '+i,{exact:true}).inputValue()==='');
   check('no workbook reading prefilled '+context+' '+i,await p.getByLabel('Tipe nilai '+i,{exact:true}).inputValue()==='UNKNOWN'&&await p.getByLabel('Nilai asli '+i,{exact:true}).inputValue()==='');
  }
  await p.getByLabel('Tipe nilai 1',{exact:true}).selectOption('NUMERIC');await p.getByLabel('Nilai asli 1',{exact:true}).fill('0');
  p.once('dialog',dialog=>dialog.dismiss());await button('Gunakan baris kandidat').click();
  check('cancelled replacement preserves unsaved value '+context,await p.getByLabel('Nilai asli 1',{exact:true}).inputValue()==='0');
  for(const width of [1440,1920]){
   await p.setViewportSize({width,height:1200});await p.evaluate(()=>window.scrollTo(0,0));
   check('workbook desktop no page overflow '+context+' '+width,await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
   await p.screenshot({path:workbookOut+'/'+context.toLowerCase()+'-'+width+'.png',fullPage:true});
  }
  await p.evaluate(()=>document.documentElement.dataset.theme='dark');
  check('workbook dark labels remain visible '+context,await p.getByText(/Profil sumber/).isVisible());
  await p.screenshot({path:workbookOut+'/'+context.toLowerCase()+'-dark-1920.png',fullPage:true});
  await p.evaluate(()=>delete document.documentElement.dataset.theme);
  p.once('dialog',dialog=>dialog.accept());await button('Batal input').click();
 }

 // WORKBOOK-02: representative source families; standalone intercepted synthetic evidence.
 const nextOut=resolve(process.env.NADI_WORKBOOK2_OUTPUT??out+'/workbook-02');mkdirSync(nextOut,{recursive:true});
 for(const [context,profile,method,count,unit] of [
  ['VIBRATION_BOILER','boiler-three-point-rms','VIBRATION',9,'mm/s-rms'],
  ['VIBRATION_BOILER','boiler-five-axis','VIBRATION',5,'mm/s'],
  ['VIBRATION_BC','bc-irregular-axis','VIBRATION',11,'mm/s'],
  ['VIBRATION_TURBINE','turbine-four-point','VIBRATION',12,'mm/s'],
  ['CEP_CBM','cep-bearing-cbm','OTHER',4,'Ampere'],
  ['CEP_CBM','cep-ir-window','OTHER',1,'Ampere']]){
  await go();await button('Input Pengukuran').click();await p.getByLabel('Konteks input kandidat').selectOption(context);
  check('explicit new family selection '+profile,await button('Gunakan baris kandidat').count()===0);
  await p.getByLabel('Keluarga template kandidat').selectOption(profile);
  check('context keeps selected method '+profile,await p.getByLabel('Metode',{exact:true}).inputValue()==='VIBRATION');
  await p.getByLabel('Metode',{exact:true}).selectOption('MCSA');
  check('incompatible method refused '+profile,await button('Gunakan baris kandidat').isDisabled());
  await p.getByLabel('Metode',{exact:true}).selectOption(method);await button('Gunakan baris kandidat').click();
  check('exact family row count '+profile,await p.locator('.pdm-measurement-row').count()===count);
  check('literal family unit '+profile,await p.getByLabel('Unit asli 1',{exact:true}).inputValue()===unit);
  check('unbound physical point and unknown time '+profile,await p.getByLabel('Titik 1',{exact:true}).inputValue()===''&&await p.getByLabel('Waktu measurement 1',{exact:true}).inputValue()==='');
  check('no original source value copied '+profile,await p.getByLabel('Tipe nilai 1',{exact:true}).inputValue()==='UNKNOWN'&&await p.getByLabel('Nilai asli 1',{exact:true}).inputValue()==='');
  if(profile==='cep-bearing-cbm')check('ambiguous thermal units stay empty',await p.getByLabel('Unit asli 2',{exact:true}).inputValue()===''&&await p.getByText('CBM provisional: temperatur/IR Window belum membuktikan inspeksi IRT lengkap.',{exact:false}).isVisible());
  if(method==='VIBRATION')check('source axis remains a display hint, not physical quantity or canonical point '+profile,await p.locator('.workbook-field').first().getByText(/belum terikat ke titik kanonis/).isVisible()&&await p.getByLabel('Parameter 1',{exact:true}).inputValue()===''&&await p.locator('.pdm-measurement-row').first().getByText(/label sumber 1V/).isVisible());
  await p.getByLabel('Tipe nilai 1',{exact:true}).selectOption('NUMERIC');await p.getByLabel('Nilai asli 1',{exact:true}).fill('0');
  p.once('dialog',dialog=>dialog.dismiss());await button('Gunakan baris kandidat').click();
  check('replacement confirmation retains zero '+profile,await p.getByLabel('Nilai asli 1',{exact:true}).inputValue()==='0');
  for(const width of [1440,1920])for(const theme of ['light','dark']){
   await p.setViewportSize({width,height:1200});await p.evaluate(t=>document.documentElement.dataset.theme=t,theme);await p.evaluate(()=>window.scrollTo(0,0));
   check('family desktop no overflow '+profile+' '+width+' '+theme,await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
   await p.screenshot({path:nextOut+'/'+profile+'-'+theme+'-'+width+'.png',fullPage:true});
  }
  await p.evaluate(()=>delete document.documentElement.dataset.theme);p.once('dialog',dialog=>dialog.accept());await button('Batal input').click();
 }
 await p.setViewportSize({width:1440,height:1086});
 await p.goto(base+'/pdm?context=SYNTHETIC',{waitUntil:'networkidle'});await button('Input Pengukuran').click();await p.getByLabel('Konteks input kandidat').selectOption('AREA_FAN');check('template awaits validation',await p.getByText(/Menunggu Validasi Engineer\. Konteks kandidat/).isVisible());
 await p.getByLabel('Versi metode / prosedur').fill('candidate-1');await p.getByLabel('Waktu inspeksi asli').fill('2026-10-09T08:00:00+07:00');await p.getByLabel('Referensi instrumen').fill('instrument:SYNTHETIC');await p.getByLabel('Referensi prosedur').fill('procedure:SYNTHETIC');await p.getByLabel('Orientasi').fill('orientation:SYNTHETIC');await p.getByLabel('Konteks operasi',{exact:true}).fill('SYNTHETIC steady regime');
 for(let i=1;i<=3;i++){if(i>1)await button('Tambah baris').click();await p.getByLabel('Titik '+i,{exact:true}).fill('point:SYNTHETIC');await p.getByLabel('Parameter '+i,{exact:true}).fill(i===3?'synthetic_state':'synthetic_quantity');await p.getByLabel('Tipe nilai '+i,{exact:true}).selectOption(i===3?'UNKNOWN':'NUMERIC');if(i<3)await p.getByLabel('Nilai asli '+i,{exact:true}).fill(i===1?'0':'4.2');await p.getByLabel('Unit asli '+i,{exact:true}).fill(i===3?'':'unit-A');await p.getByLabel('Waktu measurement '+i,{exact:true}).fill(i===1?time:i===2?'2026-10-09T02:51:00Z':'');}
 await p.getByLabel('Observasi (satu per baris)').fill('SYNTHETIC reported observation');await p.getByLabel('Interpretasi / Hipotesis').fill('SYNTHETIC unconfirmed hypothesis');await p.getByLabel('Parameter 1',{exact:true}).focus();await p.keyboard.press('Tab');check('keyboard advances measurement fields',await p.getByLabel('Tipe nilai 1',{exact:true}).evaluate(el=>el===document.activeElement));
 await p.evaluate(()=>window.dispatchEvent(new Event('focus')));await p.getByLabel('Nilai asli 1',{exact:true}).waitFor();check('trusted-session refresh retains same-identity unsaved rows',await p.getByLabel('Nilai asli 1',{exact:true}).inputValue()==='0');check('candidate context survives authorized refresh',await p.getByLabel('Konteks input kandidat').inputValue()==='AREA_FAN');check('native controls have touch height',await p.getByLabel('Tipe nilai 1',{exact:true}).evaluate(el=>el.getBoundingClientRect().height>=44));await evidence('measurement-input');await p.setViewportSize({width:1440,height:1086});await button('Simpan draf inspeksi').click();await p.getByRole('alert').waitFor();check('failed save retains native rows',await p.getByLabel('Nilai asli 1',{exact:true}).inputValue()==='0');await p.evaluate(()=>window.dispatchEvent(new Event('focus')));await p.getByLabel('Nilai asli 1',{exact:true}).waitFor();await button('Simpan draf inspeksi').click();await p.getByRole('heading',{name:'Review & tindak lanjut inspeksi',exact:true}).waitFor();check('retry uses same request ID',commands[0].body.request_id===commands[1].body.request_id);check('zero and null preserved',inspections[0].measurements[0].value===0&&inspections[0].measurements[2].value===null);await evidence('inspection-detail');check('save completion preserves unrelated query',new URL(p.url()).searchParams.get('context')==='SYNTHETIC');await button('Kembali ke register').click();await p.locator('.record-open').first().click();await button('Ubah draf inspeksi').click();await p.getByLabel('Observasi (satu per baris)').fill('SYNTHETIC unsaved back check');const backDialog=p.waitForEvent('dialog');const dirtyBack=p.goBack();await (await backDialog).dismiss();await dirtyBack;await p.waitForURL(url=>url.searchParams.get('context')==='SYNTHETIC'&&url.searchParams.get('record')===inspections[0].record_id);check('cancelled browser Back after save preserves exact URL context and draft',new URL(p.url()).searchParams.get('context')==='SYNTHETIC'&&new URL(p.url()).searchParams.get('record')===inspections[0].record_id&&await p.getByLabel('Observasi (satu per baris)').inputValue()==='SYNTHETIC unsaved back check');p.once('dialog',d=>d.accept());await button('Batal input').click();
 await button('Riwayat & Tren').click();await p.getByRole('heading',{name:'Pengukuran Asli',exact:true}).waitFor();await p.getByLabel('Plot sampel pada halaman ini (satu inspeksi)',{exact:true}).selectOption(inspections[0].record_id);check('null/incompatible context not plotted',await p.getByText('Sampel satu inspeksi belum dapat diplot',{exact:true}).isVisible());await p.getByLabel('Parameter exact').fill('synthetic_quantity');await button('Terapkan filter measurement').click();await p.getByRole('heading',{name:'Pengukuran Asli',exact:true}).waitFor();await p.getByLabel('Plot sampel pada halaman ini (satu inspeksi)',{exact:true}).selectOption(inspections[0].record_id);await p.getByRole('img',{name:/Sampel measurement asli/}).waitFor();check('scatter has two actual samples without interpolation',await p.locator('.pdm-raw-plot circle').count()===2&&await p.locator('.pdm-raw-plot polyline').count()===0);await evidence('measurement-history');
 await button('Register Inspeksi').click();const inputRow=p.locator('.pdm-register tbody tr').filter({has:p.getByText(inspections[0].record_id,{exact:true})});await inputRow.getByText('Identitas inspeksi',{exact:true}).click();await inputRow.locator('.record-open').click();check('disclosed register identity opens exact saved record',new URL(p.url()).searchParams.get('record')===inspections[0].record_id);await button('Ajukan inspeksi').click();await p.locator('.product-record-detail .status-badge').filter({hasText:'SUBMITTED'}).waitFor();check('author has no self-review control',await button('Mulai review independen').count()===0);
 role='REVIEWER';subject='synthetic-reviewer';await p.goto(base+'/pdm?record='+encodeURIComponent(inspections[0].record_id),{waitUntil:'networkidle'});
 await p.getByLabel('Alasan review / revisi').fill('SYNTHETIC independent review');await button('Mulai review independen').click();await p.getByRole('radio',{name:'Setujui rekam inspeksi',exact:true}).waitFor();
 check('review has no preselected decision',await p.getByRole('radio').evaluateAll(nodes=>nodes.every(n=>!n.checked))&&await button('Simpan keputusan review').isDisabled());
 await p.getByLabel('Alasan review / revisi').fill('SYNTHETIC request corrected context');await p.getByRole('radio',{name:'Kembalikan untuk koreksi',exact:true}).check();await button('Simpan keputusan review').click();await p.locator('.product-record-detail .status-badge').filter({hasText:'RETURNED'}).waitFor();
 pageIdentities.set(p,{role:'REVIEWER',subject:'synthetic-reviewer'});const retainedSessionStart=sessionReads.length;
 role='AUTHOR';subject='synthetic-author';const authorPage=await ctx.newPage();pageIdentities.set(authorPage,{role:'AUTHOR',subject:'synthetic-author'});await authorPage.goto(base+'/pdm?record='+encodeURIComponent(inspections[0].record_id),{waitUntil:'networkidle'});
 await authorPage.getByLabel('Alasan review / revisi').fill('SYNTHETIC correct requested context');await authorPage.getByRole('button',{name:'Revisi rekam dikembalikan / ditolak',exact:true}).click();await authorPage.getByRole('button',{name:'Ubah draf inspeksi',exact:true}).click();await authorPage.getByLabel('Observasi (satu per baris)').fill('SYNTHETIC corrected observation');await authorPage.getByRole('button',{name:'Simpan revisi draf',exact:true}).click();await authorPage.getByRole('button',{name:'Ajukan inspeksi',exact:true}).click();await authorPage.locator('.product-record-detail .status-badge').filter({hasText:'SUBMITTED'}).waitFor();
 check('returned author revises through existing lifecycle',inspections[0].status==='SUBMITTED'&&audit.get(inspections[0].record_id).some(e=>e.action==='revise'));
 // Exercise the original race deliberately while the default actor is AUTHOR.
 const reviewerRefresh=p.waitForResponse(response=>response.url()===base+'/api/engineering-qa/session');
 await p.evaluate(()=>window.dispatchEvent(new Event('focus')));await reviewerRefresh;
 // Closing the author tab can focus/refresh the retained reviewer. Its fixture
 // identity stays bound to that tab throughout the author's revision workflow.
 role='REVIEWER';subject='synthetic-reviewer';await authorPage.close();pageIdentities.delete(authorPage);await button('Baca revisi terbaru').click();await button('Mulai review independen').waitFor();
 const retainedReads=sessionReads.slice(retainedSessionStart).filter(x=>x.page===p);
 check('retained reviewer session stays independent of author tab',retainedReads.length>0&&retainedReads.every(x=>x.subject==='synthetic-reviewer'));
 check('retained reviewer page clears prior rationale on new revision',await p.getByLabel('Alasan review / revisi').inputValue()===''&&await button('Mulai review independen').isDisabled());
 await p.getByLabel('Alasan review / revisi').fill('SYNTHETIC second independent review');await button('Mulai review independen').click();await p.getByRole('radio',{name:'Setujui rekam inspeksi',exact:true}).waitFor();
 check('retained reviewer page requires fresh decision and rationale',await p.getByRole('radio').evaluateAll(nodes=>nodes.every(n=>!n.checked))&&await p.getByLabel('Alasan review / revisi').inputValue()===''&&await button('Simpan keputusan review').isDisabled());
 await p.getByLabel('Alasan review / revisi').fill('SYNTHETIC record review only');await p.getByRole('radio',{name:'Setujui rekam inspeksi',exact:true}).check();await button('Simpan keputusan review').click();await p.locator('.product-record-detail .status-badge').filter({hasText:'APPROVED'}).waitFor();check('review does not classify condition',inspections[0].status==='APPROVED'&&inspections[0].assessment==='NOT_ASSESSED');
 // Resume deliberate single-page actor changes, including the role-loss test.
 pageIdentities.delete(p);
 role='AUTHOR';subject='synthetic-author';await p.goto(base+'/pdm?record='+encodeURIComponent(inspections[0].record_id),{waitUntil:'networkidle'});await button('Buat Engineering Case').click();await p.getByLabel('Judul kasus',{exact:true}).fill('SYNTHETIC investigation');await p.getByLabel('Pernyataan masalah',{exact:true}).fill('SYNTHETIC observation requires independent review');await button('Simpan kasus').click();await button('Coba tautkan versi evidence yang sama').waitFor();check('partial Case creation is explicit without duplicate',cases.length===1&&commands.filter(c=>c.resource==='cases'&&!c.id).length===1);await button('Coba tautkan versi evidence yang sama').click();await p.getByText('Evidence versi exact telah ditautkan.',{exact:false}).waitFor();check('Case existing workflow receives exact evidence',cases.length===1&&cases[0].evidence[0].record_id===inspections[0].record_id);const links=commands.filter(c=>c.action==='evidence');check('partial link retry preserves one Case, exact revision and request intent',links.length===2&&links[0].body.request_id===links[1].body.request_id&&links[0].body.expected_inspection_revision===links[1].body.expected_inspection_revision);check('no automatic Recommendation or Maximo writes',commands.every(c=>['inspections','cases'].includes(c.resource)));await button('Baca riwayat').click();await p.getByText('Baca isi revisi 1',{exact:true}).click();check('immutable original snapshot survives return revise and review',await p.getByRole('cell').filter({has:p.getByText('Baca isi revisi 1',{exact:true})}).getByText('SYNTHETIC reported observation',{exact:true}).isVisible());await evidence('engineering-handoff');
 await go();await button('Input Pengukuran').click();await p.getByLabel('Parameter 1',{exact:true}).fill('SYNTHETIC unsaved');role='REVIEWER';await p.evaluate(()=>window.dispatchEvent(new Event('focus')));await p.getByText('Input pengukuran hanya tersedia bagi author berotorisasi.',{exact:true}).waitFor();check('removed AUTHOR role clears native editor',await p.locator('.pdm-entry').count()===0);check('read-only reviewer has no measurement create control',await button('Input Pengukuran').count()===0);role='AUTHOR';subject='synthetic-author';proof=false;await p.goto(base+'/pdm',{waitUntil:'networkidle'});await p.getByText(/Kontrak filter PdM belum tersedia/).waitFor();check('older backend cannot silently claim global filters or accept new input',await button('Input Pengukuran').count()===0&&await p.getByRole('heading',{name:'Register inspeksi / temuan',exact:true}).count()===0);proof=true;denied=403;await p.goto(base+'/pdm',{waitUntil:'networkidle'});check('denied session exposes no records',await p.getByRole('heading',{name:'Register inspeksi / temuan',exact:true}).count()===0);denied=0;await go();await p.evaluate(()=>document.documentElement.dataset.theme='dark');await evidence('register-dark');check('no uncaught browser errors',errors.length===0);
 writeFileSync(out+'/results.json',JSON.stringify({status:'PASS',checks,errors,synthetic_fixtures:true,official_runtime_access:false,commands:commands.map(c=>({resource:c.resource,action:c.action}))},null,2));
}finally{await ctx.close();await browser.close();}
