// No listener or Next server. All requests are intercepted at a reserved synthetic origin.
import assert from 'node:assert/strict';
import {readFileSync,writeFileSync,mkdirSync,rmSync} from 'node:fs';
import {resolve} from 'node:path';
import {pathToFileURL} from 'node:url';
import {browserBundle} from './localization-browser-build.mjs';
const {chromium}=await import(process.env.NADI_PLAYWRIGHT_MODULE?pathToFileURL(process.env.NADI_PLAYWRIGHT_MODULE).href:'playwright');
const {default:AxeBuilder}=await import(process.env.NADI_AXE_MODULE?pathToFileURL(process.env.NADI_AXE_MODULE).href:'@axe-core/playwright');
const accessibility=[];
const fixture=JSON.parse(readFileSync('fixtures/integration-ui.json','utf8'));
const out=resolve(process.env.NADI_INTEGRATION_OUTPUT??'/tmp/nadi-integration-ui-evidence');mkdirSync(out,{recursive:true});
const bundle=await browserBundle('scripts/integration-entry.tsx');
const browser=await chromium.launch({headless:true}),checks=[],requests=[],errors=[],violations=[];
const ctx=await browser.newContext({viewport:{width:1440,height:1080},serviceWorkers:'block'}),p=await ctx.newPage();
const base='https://integration.synthetic.invalid';let mode='normal';
const check=(name,result)=>{assert.ok(result,name);checks.push(name);console.log('PASS '+name);};
p.on('pageerror',error=>errors.push(error.message));
await ctx.route('**/*',async route=>{
 const r=route.request(),u=new URL(r.url());
 if(u.origin!==base){violations.push({path:u.pathname,method:r.method()});return route.abort('blockedbyclient');}
 if(u.pathname==='/candidate.js')return route.fulfill({contentType:'application/javascript',body:bundle.js});
 if(u.pathname==='/candidate.css')return route.fulfill({contentType:'text/css',body:bundle.css});
 if(r.isNavigationRequest())return route.fulfill({contentType:'text/html',body:'<!doctype html><html lang="id"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>DEMO — QA SINTETIS Integrasi NADI</title><link rel="stylesheet" href="/candidate.css"></head><body><div id="root"></div><script src="/candidate.js"></script></body></html>'});
 requests.push({mode,path:u.pathname,method:r.method()});
 if(r.method()!=='GET'||!['/api/cockpit/v1/reliability/integration-status','/api/cockpit/v1/reliability/data-trust'].includes(u.pathname)){violations.push({path:u.pathname,method:r.method()});return route.abort('blockedbyclient');}
 const integration=u.pathname.endsWith('integration-status');
 if(mode==='loading')await new Promise(resolve=>setTimeout(resolve,600));
 if(mode==='unavailable'||(mode==='integration-error'&&integration)||(mode==='trust-error'&&!integration))return route.fulfill({status:503,json:{detail:'SYNTHETIC PRIVATE ERROR MUST NOT RENDER'}});
 if(mode==='denied')return route.fulfill({status:403,json:{detail:'SYNTHETIC PRIVATE AUTH DETAIL MUST NOT RENDER'}});
 const data=structuredClone(integration?fixture.integration:fixture.trust);
 if(mode==='missing'){
  if(integration){data.components=[];for(const key of Object.keys(data.coverage))data.coverage[key]=null;data.governance_schema_ready=null;data.condition_schema_ready=null;}
  else {data.domains=[];data.relationships=[];}
 }
 if(mode==='empty'){
  if(integration){for(const key of Object.keys(data.coverage))data.coverage[key]=0;}
  else {for(const key of Object.keys(data.population))data.population[key]=0;data.domains=[];data.relationships=[];}
 }
 if(mode==='unknown-policy'&&integration){for(const c of data.components)for(const key of ['collection_freshness','source_freshness','projection_freshness'])c[key]={state:'UNKNOWN',observed_at:null,max_age_seconds:null};}
 return route.fulfill({json:data});
});
async function go(next){mode=next;await p.goto(base+'/system-integration',{waitUntil:next==='loading'?'domcontentloaded':'networkidle'});}
const metrics=p.locator('.integration-summary');
try{
 await go('normal');await p.locator('.integration-component').first().waitFor();
 check('five canonical DTO components',await p.locator('.integration-component').count()===5);
 check('registered and broader technical populations remain separate',await metrics.locator('.stat-card').filter({hasText:'Aset bisnis terdaftar'}).locator('strong').innerText()==='12'&&await metrics.locator('.stat-card').filter({hasText:'Konteks aset teknis'}).locator('strong').innerText()==='120');
 check('unsupported projected count is UNKNOWN',await metrics.locator('.stat-card').filter({hasText:'Aset dengan bukti kondisi terproyeksi'}).locator('strong').innerText()==='Belum diketahui (UNKNOWN)');
 const mx=p.getByRole('article',{name:'Maximo Collector',exact:true}),pi=p.getByRole('article',{name:'PI Collector',exact:true}),mart=p.getByRole('article',{name:'Reliability Mart',exact:true});
 check('availability and degradation coexist',await mx.getByText('Tersedia (AVAILABLE)',{exact:true}).isVisible()&&await mx.getByText('Terbatas (DEGRADED)',{exact:true}).isVisible());
 check('collection CURRENT remains independent of source/projection UNKNOWN',await mx.locator('.integration-dimension').filter({hasText:'Freshness pengumpulan'}).getByText(/CURRENT/).isVisible()&&await mx.locator('.integration-dimension').filter({hasText:'Freshness sumber'}).getByText(/UNKNOWN/).first().isVisible());
 check('old source remains STALE while projection CURRENT is preserved',await pi.locator('.integration-dimension').filter({hasText:'Freshness sumber'}).getByText('Usang (STALE)',{exact:true}).isVisible()&&await mart.locator('.integration-dimension').filter({hasText:'Freshness proyeksi'}).getByText(/CURRENT/).isVisible());
 check('source record date never becomes collection freshness',await p.getByText('Data Trust tidak menyediakan timestamp observasi mandiri.',{exact:false}).isVisible()&&await pi.getByText('2020-01-01 00:00:00 UTC',{exact:true}).count()>0);
 const disclosure=mx.locator('summary');await disclosure.focus();await p.keyboard.press('Enter');
 check('reasons disclosure works using keyboard',await mx.getByText('COLLECTOR_ERRORS',{exact:true}).isVisible());
 check('keyboard has visible focus indicator',await disclosure.evaluate(node=>parseFloat(getComputedStyle(node).outlineWidth)>=3));
 await p.keyboard.press('Enter');
 for(const href of ['/system-integration','/data-quality','/maintenance','/maintenance/investigation','/work-orders','/fmea','/rcfa','/overhauls'])check('existing technical navigation '+href,await p.locator(`.nadi-utility-nav a[href="${href}"]`).count()===1);
 check('integration overview has correct active route',await p.locator('#nav-integration a[aria-current="page"]').getAttribute('href')==='/system-integration');
 check('no invented PI or CEMS route',await p.locator('a[href^="/pi"],a[href^="/cems"]').count()===0);
 check('one main and one page heading',await p.getByRole('main').count()===1&&await p.getByRole('heading',{level:1}).count()===1);
 check('tables identify column and row headers',await p.locator('th[scope="col"]').count()===5&&await p.locator('th[scope="row"]').count()===6);
 for(const width of [1440,1920,768,390]){
  await p.setViewportSize({width,height:1080});
  for(const theme of ['light','dark']){
   await p.evaluate(theme=>{document.documentElement.dataset.theme=theme;localStorage.setItem('nadi-theme',theme);},theme);
   await p.evaluate(()=>scrollTo(0,0));
   check(`no horizontal page overflow ${width} ${theme}`,await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
   const table=p.getByRole('region',{name:'Cakupan domain Data Trust'});await table.focus();
   check(`contained table remains keyboard accessible ${width} ${theme}`,await table.evaluate(node=>document.activeElement===node&&node.scrollWidth>=node.clientWidth));
   check(`readable theme tokens ${width} ${theme}`,await p.locator('.integration-component').first().evaluate(node=>getComputedStyle(node).backgroundColor!==getComputedStyle(node).color));
   const audit=await new AxeBuilder({page:p}).withTags(['wcag2a','wcag2aa','wcag21a','wcag21aa']).analyze();
   accessibility.push({width,theme,violations:audit.violations.map(v=>({id:v.id,impact:v.impact,nodes:v.nodes.map(n=>n.target)})),incomplete:audit.incomplete.map(v=>({id:v.id,nodes:v.nodes.map(n=>({target:n.target,summary:n.failureSummary}))}))});
   check(`axe WCAG A/AA ${width} ${theme}`,audit.violations.length===0);
   await p.evaluate(()=>scrollTo(0,0));await p.screenshot({path:resolve(out,`integration-${theme}-${width}.png`),fullPage:true});
  }
 }
 await p.getByRole('button',{name:'Buka navigasi',exact:true}).click();
 check('mobile drawer focus and group links available',await p.getByRole('dialog').isVisible()&&await p.locator('#nav-integration a[href="/system-integration"]').isVisible());
 await p.keyboard.press('Escape');check('mobile drawer closes with Escape',await p.getByRole('dialog').count()===0);
 await p.setViewportSize({width:1440,height:1080});
 await go('missing');
 check('missing component evidence does not invent a disconnected source',await p.getByText('Belum ada bukti komponen.',{exact:true}).isVisible()&&await p.locator('.integration-component').count()===0);
 check('missing coverage never defaults to zero',await metrics.locator('strong').allTextContents().then(xs=>xs[0].includes('UNKNOWN')&&xs[1].includes('UNKNOWN')&&xs[3].includes('UNKNOWN')));
 await go('empty');check('real empty population displays zero',await metrics.locator('strong').allTextContents().then(xs=>xs.every(x=>x==='0'))&&await p.getByText('Populasi domain belum dilaporkan.',{exact:true}).isVisible());
 await go('unknown-policy');check('unknown freshness policy never turns CURRENT',await p.locator('.integration-dimensions').getByText(/CURRENT/).count()===0&&await p.getByText('Batas usia kebijakan: Belum diketahui / tidak dikonfigurasi (UNKNOWN)',{exact:true}).count()===15);
 await go('integration-error');check('integration error does not hide Data Trust',await p.getByRole('heading',{name:'Bukti integrasi tidak tersedia',exact:true}).isVisible()&&await p.getByRole('region',{name:'Cakupan domain Data Trust'}).isVisible());
 mode='normal';await p.getByRole('button',{name:'Baca ulang bukti lokal'}).click();await p.getByRole('article',{name:'Maximo Collector',exact:true}).waitFor();check('manual reread recovers only stored integration evidence',await p.getByRole('article',{name:'Maximo Collector',exact:true}).isVisible());
 await go('trust-error');check('Data Trust error does not hide integration evidence',await p.getByRole('heading',{name:'Data Trust tidak tersedia',exact:true}).isVisible()&&await p.getByRole('article',{name:'Maximo Collector',exact:true}).isVisible());
 await go('unavailable');check('both unavailable APIs show explicit errors and unknown counts',await p.getByRole('alert').count()===2&&await metrics.locator('strong').allTextContents().then(xs=>xs.every(x=>x.includes('UNKNOWN'))));
 await go('denied');check('denied access retained without raw server details',await p.getByText('Akses bukti ditolak.',{exact:false}).count()===2&&!((await p.locator('body').innerText()).includes('SYNTHETIC PRIVATE')));
 await go('loading');await p.getByRole('status').first().waitFor();check('loading is announced independently',await p.getByRole('status').count()===2);await p.getByRole('article',{name:'Maximo Collector',exact:true}).waitFor();
 check('no JavaScript errors',errors.length===0);check('no request escaped synthetic origin or local GET allowlist',violations.length===0&&requests.every(x=>x.method==='GET'));
 writeFileSync(resolve(out,'browser-results.json'),JSON.stringify({status:'PASS',passed:checks.length,total:checks.length,checks,errors,violations,requests,accessibility,scope:'SYNTHETIC COMPONENTS ONLY; no server, operational network or DB'},null,2));
 console.log(`Integration browser checks passed: ${checks.length}`);
}catch(error){writeFileSync(resolve(out,'browser-results.json'),JSON.stringify({status:'FAIL',passed:checks.length,checks,errors,violations,requests,accessibility,failure:String(error)},null,2));throw error;}
finally{await browser.close();rmSync(bundle.temp,{recursive:true,force:true});}
