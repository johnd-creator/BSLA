// SYNTHETIC full Engineer journey; no listener, real credentials or unmocked network.
import assert from 'node:assert/strict';
import {readFileSync,writeFileSync,mkdirSync,rmSync} from 'node:fs';
import {resolve} from 'node:path';
import {pathToFileURL} from 'node:url';
import {browserBundle} from './localization-browser-build.mjs';
const {chromium}=await import(pathToFileURL(process.env.NADI_PLAYWRIGHT_MODULE).href);
const Axe=process.env.NADI_AXE_MODULE?(await import(pathToFileURL(process.env.NADI_AXE_MODULE).href)).default:null;
const out=resolve(process.env.NADI_BROWSER_OUTPUT??'/tmp/nadi-factual-read-synthetic-browser');mkdirSync(out,{recursive:true,mode:0o700});
const bundle=await browserBundle('scripts/factual-read-entry.tsx'),base='https://factual-read.synthetic.invalid';
const fixture=JSON.parse(readFileSync('fixtures/asset-evidence.synthetic.json')),product=JSON.parse(readFileSync('fixtures/ux-bundle-b.json'));
const asset=fixture.asset.canonical_id,foreign=asset.replace('SYNTHETIC-03','SYNTHETIC-FOREIGN');
const row={...fixture.maintenance[0],actual_start:null,actual_finish:null,classification:{raw_work_type:'CM',canonical_category:'CM',state:'CANONICAL_SUPPORTED',origin:'RETAINED_MAXIMO_WORKTYPE',confidence:'VERIFIED',description:null,workflow_name:null,workflow_version:null,workflow_state:'NOT_AVAILABLE',status_state:'AVAILABLE'},source_detail:{work_order_number:'SYNTHETIC-WO-READ',asset_number:'SYNTHETIC-03',reported_at:null,scheduled_start:null,scheduled_finish:null}};
const identity={subject:'local:synthetic-engineer',username:'synthetic_engineer',roles:['AUTHOR'],asset_ids:['asset:DEMO-001'],csrf_token:'SYNTHETIC_CSRF_ONLY'};
const browser=await chromium.launch({headless:true}),ctx=await browser.newContext({viewport:{width:1440,height:1080}}),page=await ctx.newPage();
page.setDefaultTimeout(12000);
const requests=[],errors=[],checks=[],shots=[];let signedIn=false,mode='permitted';
page.on('pageerror',e=>errors.push(e.message));
const note=(name,yes)=>{assert(yes,name);checks.push(name);};
await ctx.route('**/*',async route=>{
 const r=route.request(),u=new URL(r.url());assert.equal(u.origin,base,'all egress intercepted');requests.push({path:u.pathname,method:r.method()});
 if(u.pathname==='/candidate.js')return route.fulfill({contentType:'application/javascript',body:bundle.js});
 if(u.pathname==='/candidate.css')return route.fulfill({contentType:'text/css',body:bundle.css});
 if(['/login/logo_nadi-white-cyan.png','/logo_nadi.png','/login/power-plant-night.png'].includes(u.pathname))return route.fulfill({contentType:'image/png',body:readFileSync('public'+u.pathname)});
 if(r.isNavigationRequest())return route.fulfill({contentType:'text/html',body:'<!doctype html><html lang="id"><head><meta charset="utf-8"><title>NADI · SYNTHETIC Engineer READ</title><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="/candidate.css"></head><body><div id="root"></div><script src="/candidate.js"></script></body></html>'});
 if(u.pathname==='/api/engineering-qa/auth/login'){assert.equal(r.method(),'POST');signedIn=true;return route.fulfill({json:{status:'AUTHENTICATED'}});}
 if(u.pathname==='/api/engineering-qa/session')return route.fulfill({status:signedIn?200:401,json:signedIn?identity:{detail:{code:'AUTHENTICATION_REQUIRED'}}});
 if(u.pathname==='/api/engineering-qa/inspections'){
  assert.equal(r.method(),'GET');const offset=Number(u.searchParams.get('offset')??0),limit=Number(u.searchParams.get('limit')??10),rows=product.inspections.filter(x=>identity.asset_ids.includes(x.canonical_asset_id));
  return route.fulfill({json:{items:rows.slice(offset,offset+limit),total:rows.length,offset,limit,has_more:offset+limit<rows.length,filter_scope:'AUTHORIZED_POPULATION',event_time_basis:'INSPECTED_AT'}});
 }
 if(u.pathname.startsWith('/api/engineering-qa/'))return route.fulfill({status:403,json:{detail:{code:'SYNTHETIC_UNAPPROVED_SCOPE'}}});
 if(!u.pathname.startsWith('/api/cockpit/'))return route.fulfill({status:404,json:{}});
 assert.equal(r.method(),'GET');const path=decodeURIComponent(u.pathname.replace('/api/cockpit','')),offset=Number(u.searchParams.get('offset')??0),limit=Number(u.searchParams.get('limit')??50);
 const denied=()=>route.fulfill({status:403,json:{detail:{code:'FACTUAL_SCOPE_GRANT_REQUIRED'}}});
 if(mode==='restricted'||path.includes(foreign)||u.searchParams.get('asset_ref')===foreign)return denied();
 if(path==='/v1/reliability/scoped-overview')return route.fulfill({json:{scope:{site_code:'BSR',organization_code:'IP',kind:'FACTUAL_ASSET_ALLOWLIST'},as_of:'2026-11-02T10:00:00Z',summary:{registered_assets:1,maintenance_events:1,assets_with_maintenance:1},assets:[{canonical_id:asset,source_asset_number:fixture.asset.source_asset_number,description:'SYNTHETIC permitted asset',maintenance_events:1,latest_retained_activity:row.source_changed_at}],restricted_sections:['PORTFOLIO_AGGREGATES','FMEA_HEALTH_PI','CROSS_INSPECTION_TRENDS'],operational_kpis:'NOT_ELIGIBLE'}});
 if(path==='/v1/reliability/assets')return route.fulfill({json:{items:offset?[]:[fixture.asset],meta:{total:1,offset,limit,has_more:false}}});
 if(path==='/v1/reliability/assets/'+asset)return route.fulfill({json:fixture.asset});
 if(path==='/v1/reliability/maintenance-events'&&u.searchParams.get('asset_ref')===asset)return route.fulfill({json:{items:offset?[]:[row],meta:{total:1,offset,limit,has_more:false}}});
 return denied();
});
const screenshot=async name=>{const file=name+'.png';await page.screenshot({path:out+'/'+file,fullPage:true});shots.push(file);};
try{
 await page.goto(base+'/login');await page.locator('input[name="username"]').fill('synthetic_engineer');await page.locator('input[name="password"]').fill('SYNTHETIC_ONLY_NOT_A_REAL_PASSWORD');await page.getByRole('button',{name:'Masuk',exact:true}).click();
 await page.getByRole('heading',{name:'Ringkasan Eksekutif',exact:true}).waitFor();await page.getByText('SYNTHETIC permitted asset',{exact:true}).waitFor();note('Login→Beranda actual components under AUTHOR and a separate read scope',new URL(page.url()).pathname==='/');await screenshot('01-engineer-scoped-home');
 note('explicit restricted sections and NOT_ELIGIBLE shown',await page.getByText('NOT_ELIGIBLE',{exact:true}).isVisible());
 for(const href of ['/assets','/pdm','/action-board','/reports'])note('existing navigation '+href,await page.locator('a[href="'+href+'"]').count()>0);
 await page.getByRole('link',{name:'Buka Aset →',exact:true}).click();await page.getByRole('link',{name:fixture.asset.source_asset_number,exact:true}).first().waitFor();
 note('Asset Register contains only permitted asset',await page.locator('table tbody tr').count()===1);await screenshot('02-engineer-register');
 await page.getByRole('link',{name:fixture.asset.source_asset_number,exact:true}).first().click();await page.getByRole('heading',{name:fixture.asset.source_asset_number,exact:true}).first().waitFor();
 await page.getByRole('button',{name:'Pemeliharaan',exact:true}).click();await page.getByRole('status').filter({hasText:'1 rekam sumber'}).waitFor();
 await page.getByRole('button',{name:'Buka rekam SYNTHETIC-WO-READ',exact:true}).click();await page.getByText('SYNTHETIC-WO-READ',{exact:true}).first().waitFor();
 note('Asset→Maintenance→WO Source Detail exact identity and missing-value disclosure',await page.getByText('Kronologi pekerjaan',{exact:true}).isVisible());await screenshot('03-engineer-wo-detail');
 await page.locator('a[href="/pdm"]').first().click();await page.getByRole('button',{name:'Input Pengukuran',exact:true}).waitFor();
 const options=await page.getByLabel('Aset filter berotorisasi').locator('option').allTextContents();note('PdM AUTHOR write scope remains original synthetic Engineering scope',options.includes('asset:DEMO-001')&&!options.includes(asset));await screenshot('04-pdm-author-preserved');
 mode='restricted';await page.goto(base+'/');await page.getByText(/tidak memiliki akses|scope|izin/i).first().waitFor();await page.getByRole('heading',{name:'Ringkasan Eksekutif',exact:true}).waitFor();note('page remains accessible while datasets are restricted',await page.getByRole('heading',{name:'Ringkasan Eksekutif',exact:true}).isVisible());
 await screenshot('05-restricted-data-page-access');mode='permitted';
 for(const width of [390,768,1440]){
  await page.setViewportSize({width,height:1080});await page.goto(base+'/');await page.getByText('SYNTHETIC permitted asset',{exact:true}).waitFor();note('no document overflow scoped home '+width,await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  if(Axe){const result=await new Axe({page}).withTags(['wcag2a','wcag2aa']).analyze();assert.deepEqual(result.violations.filter(x=>['serious','critical'].includes(x.impact)).map(x=>x.id),[]);}
  await screenshot('06-home-light-'+width);await page.getByRole('button',{name:'Ganti ke tema gelap'}).click();await screenshot('07-home-dark-'+width);await page.getByRole('button',{name:'Ganti ke tema terang'}).click();
 }
 note('no unhandled React/browser errors',errors.length===0);
 writeFileSync(out+'/results.json',JSON.stringify({label:'SYNTHETIC ONLY',checks,shots,errors,requests:requests.length,live_uat:false,actual_grant_issued:false},null,2));console.log('PASS synthetic integrated Engineer journey; '+checks.length+' checks, '+shots.length+' private screenshots; live UAT not claimed');
}catch(error){console.log('FAILED URL',page.url());console.log((await page.locator('body').innerText()).slice(0,2200));await screenshot('failure');throw error;}finally{await browser.close();rmSync(bundle.temp,{recursive:true,force:true});}
