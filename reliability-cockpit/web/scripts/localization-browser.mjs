// Network-isolated candidate component regression. No listener, deployment or persistent QA write.
import assert from 'node:assert/strict';
import {readFileSync,writeFileSync,mkdirSync,rmSync} from 'node:fs';
import {resolve} from 'node:path';
import {pathToFileURL} from 'node:url';
import {browserBundle} from './localization-browser-build.mjs';
const {chromium}=await import(process.env.NADI_PLAYWRIGHT_MODULE?pathToFileURL(process.env.NADI_PLAYWRIGHT_MODULE).href:'playwright');
const a11yFailures=[];
const AxeBuilder=process.env.NADI_AXE_MODULE?(await import(pathToFileURL(process.env.NADI_AXE_MODULE).href)).default:null;
const base='https://localization.synthetic.invalid',out=resolve(process.env.NADI_BROWSER_OUTPUT??'/tmp/nadi-id-evidence');mkdirSync(out,{recursive:true});
const copy=JSON.parse(readFileSync('lib/id-messages.json')),t=k=>{assert.ok(copy[k],k);return copy[k];};
const fixture=JSON.parse(readFileSync('fixtures/ux-bundle-b.json')),overview=JSON.parse(readFileSync('fixtures/executive-overview.json'));
const bundle=await browserBundle(),browser=await chromium.launch({headless:true}),checks=[],errors=[],commands=[];
const check=(name,value)=>{assert.ok(value,name);checks.push(name);console.log('PASS '+name);};
const context=await browser.newContext({viewport:{width:1440,height:1086}}),page=await context.newPage();
page.on('pageerror',error=>{errors.push(error.message);console.error('Candidate browser exception:',error.message);});
let role='AUTHOR',subject='demo-author',signedIn=true,qaFailure=0,factualFailure=false,saveFailure=true,stale=false,loginDelay=0;
const asset=fixture.asset.canonical_id,now='2026-10-11T00:00:00Z';
let cases=[],recommendations=structuredClone(fixture.recommendations),advisories=[],ack=null;
const review=()=>({reviewer:subject,decision:'APPROVED',rationale:'Review QA SINTETIS',decided_at:now});
const pageOf=(rows,url)=>{const offset=Number(url?.searchParams.get('offset')??0),limit=Number(url?.searchParams.get('limit')??25);return {items:rows.slice(offset,offset+limit),total:rows.length,offset,limit,has_more:offset+limit<rows.length};};
const inbox=()=>advisories.filter(a=>a.publication).map(a=>({...a.publication,current_revision:a.revision,availability:a.availability,acknowledgement:ack,follow_up_status:'PLANNED',viewed_status:'NOT_RECORDED'}));
await context.route('**/*',async route=>{
 const request=route.request(),url=new URL(request.url()),path=url.pathname,method=request.method();
 // Every candidate request is fulfilled here. Nothing falls through to localhost or external sources.
 if(url.origin!==base)return route.abort('blockedbyclient');
 if(path==='/candidate.js')return route.fulfill({contentType:'application/javascript; charset=utf-8',body:bundle.js});
 if(path==='/candidate.css')return route.fulfill({contentType:'text/css',body:bundle.css});
 if(['/logo_nadi.png','/login/logo_nadi-white-cyan.png','/login/power-plant-night.png'].includes(path))return route.fulfill({contentType:'image/png',body:readFileSync('public'+path)});
 if(request.isNavigationRequest())return route.fulfill({contentType:'text/html; charset=utf-8',body:'<!doctype html><html lang="id"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>NADI QA SINTETIS — kandidat lokalisasi</title><link rel="stylesheet" href="/candidate.css"></head><body><div id="root"></div><script src="/candidate.js"></script></body></html>'});
 if(path.startsWith('/api/engineering-qa/')){
  const relative=path.slice('/api/engineering-qa/'.length),parts=relative.split('/'),resource=parts[0],id=decodeURIComponent(parts[1]??''),action=parts[2],body=request.postDataJSON();
  const fail=(status,code)=>route.fulfill({status,json:{detail:{code}}});
  if(method!=='GET'){commands.push({resource,id,action,method,body,csrf:request.headers()['x-csrf-token']});check('command has no localized identity/authority fields '+commands.length,!Object.keys(body).some(k=>['actor','roles','subject'].includes(k)));}
  if(relative==='auth/login'){if(loginDelay)await new Promise(resolve=>setTimeout(resolve,loginDelay));if(qaFailure)return fail(qaFailure,'AUTHENTICATION_REQUIRED');signedIn=true;return route.fulfill({json:{authenticated:true}});}
  if(!signedIn)return fail(401,'AUTHENTICATION_REQUIRED');
  if(relative==='session/logout'){check('logout preserves CSRF contract',request.headers()['x-csrf-token']==='DEMO_BROWSER_ONLY');signedIn=false;return route.fulfill({json:{revoked:true}});}
  if(resource==='session')return route.fulfill({json:{subject,roles:[role],asset_ids:[asset],csrf_token:'DEMO_BROWSER_ONLY'}});
  if(qaFailure)return fail(qaFailure,qaFailure===403?'ACCESS_DENIED':'SYNTHETIC_FAILURE');
  if(resource==='advisory-capability')return route.fulfill({json:{persistence:'READY',scope:'SYNTHETIC_QA_ONLY'}});
  if(resource==='inbox'){
   const items=inbox(),item=items.find(x=>x.snapshot.record_id===id);
   if(action==='acknowledge'){ack={actor:subject,updated_at:now,status:'ACKNOWLEDGED',meaning:'RECEIPT_ONLY_NOT_APPROVAL_OR_WORK_AUTHORIZATION'};return route.fulfill({json:ack});}
   return route.fulfill({json:id?item:pageOf(items)});
  }
  let rows=resource==='cases'?cases:resource==='recommendations'?recommendations:resource==='advisories'?advisories:fixture[resource]??[],row=rows.find(r=>(r.case_id??r.record_id)===id);
  if(method==='GET'&&resource==='inspections'&&!id)return route.fulfill({json:{...pageOf(rows,url),filter_scope:'AUTHORIZED_POPULATION',event_time_basis:'INSPECTED_AT'}});
  if(method==='GET')return route.fulfill({json:action==='history'?[{revision:1,actor:'demo-author',action:'CREATE',occurred_at:now,reason:'QA SINTETIS — nilai rekam asli'}]:id?row:pageOf(rows)});
  if(resource==='cases'&&!id){
   if(saveFailure){saveFailure=false;return fail(503,'SYNTHETIC_RETRY_FAILURE');}
   check('original category and priority in case DTO',body.draft.category==='INVESTIGATION'&&body.draft.priority==='NORMAL');
   row={...body.draft,case_id:'case:DEMO-ID',status:'DRAFT',revision:1,created_by:subject,updated_at:now,review:null,evidence:[],notes:[]};cases.push(row);
  }else if(resource==='recommendations'&&!id){
   row={...fixture.recommendations[0],...body.draft,record_id:'recommendation:DEMO-ID',revision:1,status:'DRAFT',created_by:subject,review:null,follow_up_status:'PROPOSED',completion_verification:null,supporting_evidence:cases[0].evidence};recommendations.push(row);
  }else if(resource==='advisories'&&!id){
   const c=cases[0],r=recommendations.find(x=>x.record_id===body.draft.recommendation_ref);
   row={...body.draft,record_id:'advisory:DEMO-ID',revision:1,status:'DRAFT',created_by:subject,review:null,availability:'UNPUBLISHED',publication:null,scope:'SYNTHETIC_QA_ONLY_NOT_WORK_AUTHORIZATION',upstream:{case_id:c.case_id,case_revision:c.revision,case_sha256:'a'.repeat(64),recommendation_id:r.record_id,recommendation_revision:r.revision,recommendation_sha256:'b'.repeat(64),case_reviewer:'demo-reviewer',recommendation_reviewer:'demo-reviewer',recommended_action:r.proposed_action,rationale:r.rationale,responsible_person_ref:null,responsible_team_ref:null,target_date:null,existing_work_order_ref:null,evidence:c.evidence}};advisories.push(row);
  }else {
   if(!row)return fail(404,'NOT_FOUND');
   if(stale){stale=false;return fail(409,'REVISION_CONFLICT');}
   check('exact CAS revision is numeric and unchanged enum payload',Number.isInteger(body.expected_revision));
   if(action==='evidence')row.evidence.push({reference_id:'reference:DEMO',...body,stable_version:'DEMO-1',source_timestamp:null,snapshot:{label:'QA SINTETIS — bukti beku',availability:'AVAILABLE'}});
   else if(action==='submit')row.status='IN_REVIEW';
   else if(action==='review'){check('review payload retains APPROVED enum',body.decision==='APPROVED');row.status=body.decision;row.review=review();}
   else if(action==='publish'){row.availability='IN_APP_QA_AVAILABLE';row.publication={version:row.revision+1,published_at:now,published_by:subject,snapshot:structuredClone(row)};}
   else if(action==='followup')row.follow_up_status=body.status;
   else if(method==='PUT')Object.assign(row,body.draft);
   row.revision++;
  }
  return route.fulfill({json:row});
 }
 if(path.startsWith('/api/cockpit/')){
  check('factual transport remains read-only '+checks.length,method==='GET');
  if(factualFailure)return route.fulfill({status:503,json:{detail:'Unavailable'}});
  const meta=items=>({items,meta:{total:items.length,offset:0,limit:50,has_more:false}});let body;
  if(path.includes('decision-overview'))body=overview;
  else if(path==='/api/cockpit/v1/reliability/assets')body=meta([fixture.asset]);
  else if(path.endsWith('/context'))body={asset:fixture.asset,maintenance:fixture.maintenance,fmea:[],health:[],overhauls:[],rcfa_relationship_status:'UNRESOLVED',relationship_health:{asset_refs_resolved:1,asset_refs_total:1}};
  else if(path.endsWith('/health/latest'))return route.fulfill({status:404,json:{detail:'Missing'}});
  else if(path.endsWith('/condition-evidence'))body={canonical_asset_id:asset,mapping_readiness:'UNMAPPED',statuses:['UNKNOWN'],expected_signals:0,latest_attempt_at:null,collector_last_success_at:null,items:[]};
  else if(path.endsWith('/integration-status'))body={observed_at:now,coverage:{},components:[]};
  else if(path.includes('/maintenance-events'))body=meta(fixture.maintenance);
  else if(path.includes('/assets/'))body=path.endsWith('/'+encodeURIComponent(asset))?fixture.asset:meta([]);
  else return route.fulfill({status:503,json:{detail:'Unavailable'}});
  return route.fulfill({json:body});
 }
 return route.fulfill({status:404,body:''});
});
const button=k=>page.getByRole('button',{name:t(k),exact:true}),label=k=>page.getByLabel(t(k),{exact:true});
const go=async path=>{await page.goto(base+path,{waitUntil:'networkidle'});await page.locator('#main-content').waitFor({timeout:10000});};
try{
 // Login exercises the real component and unchanged transport using fictional, non-account inputs.
 signedIn=false;await go('/login');check('login has no application shell or navigation',await page.locator('.nadi-shell,.nadi-sidebar,.nadi-topbar,.nadi-development-status').count()===0);check('login has no dashboard link',await page.locator('a[href="/"]').count()===0);check('empty login remains disabled',await button('Sign in').isDisabled());
 await label('Username').fill('DEMO_NOT_AN_ACCOUNT');await label('Password').fill('DEMO_NOT_A_CREDENTIAL');
 await button('Show password').click();check('password visibility works',await label('Password').getAttribute('type')==='text');await button('Hide password').click();
 qaFailure=401;loginDelay=250;await button('Sign in').click();await page.getByRole('form',{name:t('NADI sign-in')}).locator('button[type="submit"] .spinner[aria-hidden="true"]').waitFor();check('submission announces busy and disables fields',await page.getByRole('form',{name:t('NADI sign-in')}).getAttribute('aria-busy')==='true'&&await label('Password').isDisabled()&&await label('Username').isDisabled()&&await button('Signing in…').isDisabled());await page.getByRole('alert').waitFor();loginDelay=0;check('localized generic login rejection',await page.getByRole('alert').innerText()===t('Unable to sign in. Check your credentials.'));check('password cleared after rejection',await label('Password').inputValue()==='');
 check('rejection moves focus to feedback',await page.getByRole('alert').evaluate(n=>n===document.activeElement));
 await go('/login?expired=1&returnTo=%2Fengineering%2Flocal');check('session expiry feedback is explicit',await page.getByRole('status').filter({hasText:t('Your session expired or was revoked. Sign in again.')}).isVisible());await label('Username').fill('DEMO_NOT_AN_ACCOUNT');qaFailure=0;await label('Password').fill('DEMO_NOT_A_CREDENTIAL');await button('Sign in').click();await page.waitForURL(base+'/engineering/local');check('login still navigates to existing QA route',true);await page.locator('.nadi-shell').waitFor();await page.getByRole('button',{name:'Keluar dari NADI',exact:true}).click();await page.getByRole('dialog',{name:'Keluar dari NADI?'}).waitFor();check('logout confirmation does not revoke before consent',signedIn);await page.getByRole('button',{name:'Ya, keluar',exact:true}).click();await page.waitForURL(base+'/login');check('logout returns to standalone login',await page.locator('.nadi-shell').count()===0);await go('/engineering/local');await page.waitForURL(base+'/login?returnTo=%2Fengineering%2Flocal');check('unauthenticated QA component redirects to bounded standalone login; server guard tested separately',true);await label('Username').fill('DEMO_NOT_AN_ACCOUNT');await label('Password').fill('DEMO_NOT_A_CREDENTIAL');await button('Sign in').click();await page.waitForURL(base+'/engineering/local');
 await page.goBack({waitUntil:'networkidle'});check('back navigation cannot add login shell',await page.locator('.nadi-shell').count()===0);await page.goForward({waitUntil:'networkidle'});await page.locator('.nadi-shell').waitFor();qaFailure=401;await button('Load records').click();await page.waitForURL(base+'/login?returnTo=%2Fengineering%2Flocal&expired=1');check('revoked session clears workspace and redirects fullscreen',await page.locator('.nadi-shell').count()===0&&await page.getByRole('status').isVisible());qaFailure=0;await label('Username').fill('DEMO_NOT_AN_ACCOUNT');await label('Password').fill('DEMO_NOT_A_CREDENTIAL');await button('Sign in').click();await page.waitForURL(base+'/engineering/local');
 await go('/panduan/istilah');check('glossary navigation marks exact active route',await page.getByRole('link',{name:'Panduan & Istilah',exact:true}).getAttribute('aria-current')==='page');await page.getByLabel('Cari istilah atau pengertian').fill('ACK');check('glossary EN search',await page.locator('.glossary-grid article').count()>0);await page.getByLabel('Cari istilah atau pengertian').fill('kemutakhiran');check('glossary ID search',await page.locator('.glossary-grid article').count()===1);await page.getByLabel('Cari istilah atau pengertian').fill('does-not-exist');check('glossary empty state',await page.getByText('Istilah tidak ditemukan.',{exact:true}).isVisible());
 await go('/engineering/cases');await button('New case').click();await label('Case title').fill('QA SINTETIS — investigasi lokalisasi');await label('Problem statement').fill('Pertanyaan QA SINTETIS; bukan diagnosis pembangkit.');await page.locator('#case-observations').fill('Observasi asli QA SINTETIS.');await page.locator('#case-hypotheses').fill('Hipotesis manusia belum tervalidasi.');
 await button('Save case').click();await page.getByRole('alert').filter({hasText:'SYNTHETIC_RETRY_FAILURE'}).waitFor();check('retry retains untranslated record input',await label('Case title').inputValue()==='QA SINTETIS — investigasi lokalisasi');await button('Save case').click();await page.getByRole('heading',{name:cases[0]?.title??'QA SINTETIS — investigasi lokalisasi',exact:true}).waitFor();
 const attempts=commands.filter(x=>x.resource==='cases'&&!x.id);check('retry idempotency retained',attempts.length===2&&attempts[0].body.request_id===attempts[1].body.request_id);
 await button('Edit case').click();await label('Case title').fill('QA SINTETIS — judul revisi');stale=true;await button('Save case').click();await page.getByRole('alert').filter({hasText:'REVISION_CONFLICT'}).waitFor();check('stale revision keeps unsaved form',await label('Case title').inputValue()==='QA SINTETIS — judul revisi');await button('Save case').click();await page.getByRole('heading',{name:'QA SINTETIS — judul revisi',exact:true}).waitFor();
 await label('Exact evidence record reference').fill(asset);await button('Link frozen evidence').click();await page.getByRole('region',{name:t('Case evidence provenance'),exact:true}).waitFor();await button('Submit case for review').click();await button('Submit case for review').waitFor({state:'hidden'});
 role='REVIEWER';subject='demo-reviewer';await go('/engineering/cases?record=case:DEMO-ID');await label('Review / revision rationale').fill('Review independen QA SINTETIS.');await button('Approve case').click();await button('Approve case').waitFor({state:'hidden'});
 role='AUTHOR';subject='demo-author';await go('/engineering/cases?record=case:DEMO-ID');await label('Recommendation rationale').fill('Rasional QA SINTETIS asli.');await label('Proposed local follow-up').fill('Tindak lanjut lokal; bukan izin pekerjaan.');await button('Create linked recommendation').click();await page.waitForURL(/\/recommendations\?record=/);await button('Submit recommendation for review').click();await button('Submit recommendation for review').waitFor({state:'hidden'});
 role='REVIEWER';subject='demo-reviewer';await go('/recommendations?record=recommendation:DEMO-ID');await label('Recommendation review / follow-up rationale').fill('Review rekomendasi QA SINTETIS.');await button('Approve recommendation').click();await button('Approve recommendation').waitFor({state:'hidden'});
 role='AUTHOR';subject='demo-author';await go('/engineering/advisories');await button('New advisory').click();await page.getByLabel(t('Approved recommendation on this server page')).selectOption('recommendation:DEMO-ID');await label('Advisory summary').fill('QA SINTETIS — advisory bahasa Indonesia');await label('Engineering finding').fill('Temuan sintetis, tidak untuk distribusi nyata.');await label('Evidence limits / UNKNOWN context').fill('Kondisi peralatan belum diketahui.');await page.getByRole('checkbox').first().check();await button('Save advisory draft').click();await button('Submit advisory for review').click();await button('Submit advisory for review').waitFor({state:'hidden'});
 role='REVIEWER';subject='demo-reviewer';await go('/engineering/advisories?record=advisory:DEMO-ID');await label('Advisory review / publication rationale').fill('Review advisory sintetis.');await button('Approve advisory').click();await button('Publish to QA inbox').waitFor();await label('Advisory review / publication rationale').fill('Publikasi simulasi ke QA.');await button('Publish to QA inbox').click();await button('Withdraw advisory').waitFor();
 await go('/engineering/inbox?record=advisory:DEMO-ID');await button('Acknowledge receipt only').click();await page.waitForFunction(text=>[...document.querySelectorAll('button')].some(b=>b.textContent===text&&b.disabled),t('Acknowledge receipt only')); check('ACK remains receipt only',ack.meaning==='RECEIPT_ONLY_NOT_APPROVAL_OR_WORK_AUTHORIZATION');await page.reload({waitUntil:'networkidle'});check('simulated reload keeps ACK display',await button('Acknowledge receipt only').isDisabled());
 check('all protected commands retain CSRF',commands.filter(x=>x.resource!=='auth').every(x=>x.csrf==='DEMO_BROWSER_ONLY'));check('structured case observation/hypothesis preserved',cases[0].investigation.observations[0]==='Observasi asli QA SINTETIS.'&&cases[0].investigation.hypotheses[0]==='Hipotesis manusia belum tervalidasi.');
 qaFailure=403;await go('/engineering/cases');check('denied access clears previous records',await page.getByRole('alert').filter({hasText:t('Record access unavailable or denied')}).isVisible()&&await page.getByText(cases[0].title,{exact:true}).count()===0);qaFailure=0;
 // Full visual route coverage, including honest unavailable/error states for absent fixture contracts.
 await go('/engineering/cases');
 await page.getByLabel('Cari pada halaman Case ini').fill('no-such-case-synthetic');
 check('Case search is confined to the loaded page',await page.locator('tbody tr').count()===0);
 await page.getByLabel('Cari pada halaman Case ini').fill('');
 check('clearing Case search restores the authorized rows',await page.locator('tbody tr').count()===cases.length);
 await page.screenshot({path:out+'/case-register-1440.png',fullPage:true});
 const routes=['/','/assets','/assets/'+encodeURIComponent(asset),'/asset-health','/maintenance','/maintenance/investigation','/work-orders','/fmea','/rcfa','/overhauls','/data-quality','/login','/pdm','/recommendations?record=recommendation:DEMO-ID','/action-board?record=recommendation:DEMO-ID','/engineering/cases?record=case:DEMO-ID','/engineering/advisories?record=advisory:DEMO-ID','/engineering/inbox?record=advisory:DEMO-ID','/engineering','/engineering/lab','/engineering/workflow','/panduan/istilah','/equipment/DEMO','/engineering/qa'];
 for(const width of (process.env.NADI_BROWSER_WIDTHS??"1440,768,390").split(",").map(Number)){
  await page.setViewportSize({width,height:1086});
  for(const [i,path] of routes.entries()){
   if(process.env.NADI_BROWSER_ONLY_ROUTE&&!path.startsWith(process.env.NADI_BROWSER_ONLY_ROUTE))continue;
   await go(path);if(path==='/pdm'){await page.locator('.pdm-register').waitFor();check('localized PdM renders qualified bounded records '+width,await page.locator('.record-open').count()===Math.min(10,fixture.inspections.length));}if(path==='/login'){check('standalone login '+width,await page.locator('.nadi-shell,.nadi-sidebar,.nadi-topbar').count()===0);await page.getByRole('button',{name:'Ganti ke tema gelap'}).click();check('standalone dark theme '+width,await page.locator('html').getAttribute('data-theme')==='dark');await page.screenshot({path:out+'/login-dark-'+width+'.png',fullPage:true});await page.reload({waitUntil:'networkidle'});check('login refresh preserves theme '+width,await page.locator('html').getAttribute('data-theme')==='dark');await page.getByRole('button',{name:'Ganti ke tema terang'}).click();await label('Username').focus();await page.keyboard.press('Tab');check('keyboard reaches password '+width,await label('Password').evaluate(n=>n===document.activeElement));}check('one main '+path+' '+width,await page.getByRole('main').count()===1);check('no horizontal page overflow '+path+' '+width,await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
   // All input controls in the rendered candidate have an accessible name.
   const unnamed=await page.locator('input:not([type=hidden]),select,textarea').evaluateAll(nodes=>nodes.filter(n=>!n.labels?.length&&!n.getAttribute('aria-label')&&!n.getAttribute('aria-labelledby')).length);check('controls labeled '+path+' '+width,unnamed===0);
   if(AxeBuilder && ((width===1440 && [0,1,2,12,13,14,15,18,20].includes(i)) || (width===390 && i===12))){
     const result=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21a','wcag21aa']).analyze();
     writeFileSync(out+'/a11y-'+i+'-'+width+'.json',JSON.stringify(result.violations,null,2));
     a11yFailures.push(...result.violations.map(v=>({route:path,width,id:v.id,nodes:v.nodes.map(n=>n.target)})));
     console.log('A11Y '+path+' '+width+': '+result.violations.length+' violations');
   }
   await page.screenshot({path:out+'/'+String(i).padStart(2,'0')+'-'+width+'.png',fullPage:true});
  }
  if(width<1440){await page.getByRole('button',{name:t('Open navigation'),exact:true}).click();const dialog=page.getByRole('dialog');check('mobile drawer localized '+width,await dialog.isVisible());await page.keyboard.press('Escape');check('drawer closes with keyboard '+width,!await dialog.isVisible());}
 }
 await page.setViewportSize({width:1440,height:1086});await go('/');await page.getByRole('button',{name:'Rekam aset & maintenance',exact:true}).focus();await page.keyboard.press('Enter');check('translated technical submenu works by keyboard',await page.getByRole('link',{name:t('Maintenance Investigation'),exact:true}).isVisible());await page.getByRole('link',{name:t('Maintenance Investigation'),exact:true}).click();await page.waitForURL(base+'/maintenance/investigation');check('deep navigation retains original URL',true);await page.setViewportSize({width:390,height:1086});await go('/');await page.getByRole('button',{name:'Ganti ke tema gelap',exact:true}).click();check('dark mode retained',await page.locator('html').getAttribute('data-theme')==='dark');await page.screenshot({path:out+'/dark-390.png',fullPage:true});
 factualFailure=true;await page.reload({waitUntil:'networkidle'});check('localized factual unavailable state',await page.getByRole('alert').isVisible());
 check('valid UTF-8 in candidate rendered text',!/[âÃÂ]/.test(await page.locator('body').innerText()));
 check('WCAG A/AA automated scans',a11yFailures.length===0);
 check('no candidate browser exceptions',errors.length===0);
 writeFileSync(out+'/browser-results.json',JSON.stringify({scope:'Network-isolated actual candidate components; fixture workflow only, not persistent-runtime acceptance',checks,errors,commands:commands.map(({body,...rest})=>({...rest,keys:Object.keys(body)})),screenshots:routes.length*3},null,2));
 console.log('Localization browser PASS '+checks.length+' checks; '+out);
}catch(error){await page.screenshot({path:out+'/failure.png',fullPage:true});writeFileSync(out+'/failure.json',JSON.stringify({message:error.message,errors,overflow:await page.evaluate(()=>[...document.querySelectorAll('*')].filter(n=>n.getBoundingClientRect().right>innerWidth+1).map(n=>({tag:n.tagName,cls:n.className,width:n.getBoundingClientRect().width,text:n.textContent?.slice(0,160)})))},null,2));throw error;}finally{await browser.close();rmSync(bundle.temp,{recursive:true,force:true});}
