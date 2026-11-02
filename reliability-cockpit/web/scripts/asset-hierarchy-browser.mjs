// Synthetic component smoke; no listener, source system, live session or credential.
import assert from 'node:assert/strict';
import {mkdirSync,writeFileSync,rmSync} from 'node:fs';
import {resolve} from 'node:path';
import {pathToFileURL} from 'node:url';
import {browserBundle} from './localization-browser-build.mjs';
const {chromium}=await import(process.env.NADI_PLAYWRIGHT_MODULE?pathToFileURL(process.env.NADI_PLAYWRIGHT_MODULE).href:'playwright');
const Axe=process.env.NADI_AXE_MODULE?(await import(pathToFileURL(process.env.NADI_AXE_MODULE).href)).default:null;
const out=resolve(process.env.NADI_BROWSER_OUTPUT??'/tmp/nadi-hierarchy-synthetic-browser');mkdirSync(out,{recursive:true,mode:0o700});
const base='https://hierarchy.synthetic.invalid',prefix='asset:MAXIMO:MXASSET:BSR:IP:';
const item=(id,parent,registered=false)=>({canonical_id:prefix+id,source_asset_number:id,description:'SYNTHETIC Maximo <component> '+id,description_shortened:false,parent_asset_ref:parent?prefix+parent:null,status:'OPERATING',asset_type:'PRODUCTION',unit:'SYNTHETIC',registered,hierarchy_role:'UNKNOWN',source_has_children:true,source_updated_at:'2026-02-01T00:00:00Z'});
const root=item('SYNTHETIC-ROOT','SYNTHETIC-SYSTEM',true),part=item('PART-A','SYNTHETIC-ROOT'),partB=item('PART-B','SYNTHETIC-ROOT'),sub=item('SUBPART','PART-A');
const bundle=await browserBundle('scripts/hierarchy-entry.tsx'),browser=await chromium.launch({headless:true,...(process.env.NADI_CHROMIUM_EXECUTABLE?{executablePath:process.env.NADI_CHROMIUM_EXECUTABLE}:{})});
let mode='normal';const requests=[],errors=[],checks=[],shots=[];
const ctx=await browser.newContext(),page=await ctx.newPage();page.setDefaultTimeout(12000);page.on('pageerror',error=>errors.push(error.message));
try{
 await ctx.route('**/*',async route=>{
  const req=route.request(),url=new URL(req.url());assert.equal(url.origin,base);assert.equal(req.method(),'GET');
  if(req.resourceType()==='document')return route.fulfill({contentType:'text/html',body:'<!doctype html><html lang="id"><head><meta charset="utf-8"><title>Hierarchy synthetic</title><link rel="stylesheet" href="/fixture.css"></head><body><div id="root"></div><script src="/fixture.js"></script></body></html>'});
  if(url.pathname==='/fixture.js')return route.fulfill({contentType:'application/javascript',body:bundle.js});
  if(url.pathname==='/fixture.css')return route.fulfill({contentType:'text/css',body:bundle.css});
  assert(url.pathname.startsWith('/api/cockpit/v1/reliability/assets/'));assert(url.pathname.endsWith('/hierarchy'));requests.push(url.pathname+url.search);
  if(mode==='denied')return route.fulfill({status:403,contentType:'application/json',body:'{}'});
  if(mode==='unavailable')return route.fulfill({status:503,contentType:'application/json',body:'{}'});
  const child=url.searchParams.get('node_ref')===part.canonical_id,gapped=mode==='gapped';
  const payload={root_ref:root.canonical_id,node:child?part:root,path:child?[root,part]:[root],ancestors:[item('SYNTHETIC-SYSTEM',null)],ancestor_state:gapped?'UNRESOLVED_PARENT':'NO_RETAINED_PARENT',unresolved_parent_ref:gapped?prefix+'MISSING-PARENT':null,items:gapped?[]:child?[sub]:[part,partB],total:gapped?0:child?1:2,offset:0,limit:25,has_more:false,completeness:'PARTIAL',source:'RETAINED_MAXIMO_PARENT',depth_limit:32};
  return route.fulfill({contentType:'application/json',body:JSON.stringify(payload)});
 });
 for(const width of [390,768,1440]){
  await page.setViewportSize({width,height:1000});await page.goto(base);await page.getByRole('heading',{level:1}).waitFor();
  const before=requests.length;await page.waitForTimeout(100);assert.equal(requests.length,before,'closed panel never reads hierarchy');
  await page.getByText('Hierarki aset Maximo · parent dan komponen tersimpan',{exact:true}).click();
  await page.getByRole('button',{name:'Buka PART-A',exact:true}).waitFor();
  assert((await page.locator('main').innerText()).includes('Peran sistem/peralatan/komponen belum diverifikasi'));
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
  if(Axe){const result=await new Axe({page}).analyze();assert.equal(result.violations.length,0,JSON.stringify(result.violations));}
  await page.screenshot({path:resolve(out,'hierarchy-'+width+'.png'),fullPage:true});shots.push('hierarchy-'+width+'.png');
  await page.getByRole('button',{name:'Buka PART-A',exact:true}).focus();await page.keyboard.press('Enter');await page.getByRole('button',{name:'Buka SUBPART',exact:true}).waitFor();
  await page.getByRole('navigation',{name:'Jalur hierarki dalam aset terdaftar'}).getByRole('button',{name:'SYNTHETIC-ROOT',exact:true}).click();await page.getByRole('button',{name:'Buka PART-B',exact:true}).waitFor();checks.push('lazy-open/keyboard/drill/back/overflow/'+width);
 }
 for(const next of ['gapped','denied','unavailable']){
  mode=next;await page.goto(base);await page.getByText('Hierarki aset Maximo · parent dan komponen tersimpan',{exact:true}).click();
  await page.getByText(next==='gapped'?'Parent tercatat, tetapi rekam parent belum tersimpan.':next==='denied'?'Izin membaca konteks hierarki teknis belum tersedia untuk sesi ini.':'Konteks hierarki belum tersedia. Data sumber belum dapat dipastikan.',{exact:false}).first().waitFor();
  if(next==='gapped')assert((await page.locator('main').innerText()).includes('bukan bukti leaf sumber'));
  checks.push(next);
 }
 assert.equal(errors.length,0,JSON.stringify(errors));
 writeFileSync(resolve(out,'report.json'),JSON.stringify({synthetic:true,checks,shots,errors,requests},null,2),{mode:0o600});
 console.log('Hierarchy synthetic browser PASS '+checks.length+' checks; '+shots.length+' private screenshots');
}finally{await browser.close();rmSync(bundle.temp,{recursive:true,force:true});}
