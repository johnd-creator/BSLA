// Actual React components; every request is intercepted. SYNTHETIC evidence only.
import assert from "node:assert/strict";
import { readFileSync, writeFileSync, mkdirSync, rmSync } from "node:fs";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";
import { browserBundle } from "./localization-browser-build.mjs";
const { chromium } = await import(
  process.env.NADI_PLAYWRIGHT_MODULE
    ? pathToFileURL(process.env.NADI_PLAYWRIGHT_MODULE).href
    : "playwright"
);
const Axe = process.env.NADI_AXE_MODULE
  ? (await import(pathToFileURL(process.env.NADI_AXE_MODULE).href)).default
  : null;
const out = resolve(
  process.env.NADI_BROWSER_OUTPUT ?? "/tmp/nadi-simplification-evidence",
);
mkdirSync(out, { recursive: true });
const baseline = process.env.NADI_SIMPLIFICATION_BASELINE === "1",
  base = "https://experience.synthetic.invalid";
const bundle = await browserBundle(),
  browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({
    viewport: { width: 1440, height: 1086 },
  }),
  page = await ctx.newPage();
const fixture = JSON.parse(readFileSync("fixtures/ux-bundle-b.json")),
  overview = JSON.parse(readFileSync("fixtures/executive-overview.json"));
fixture.inspections[0].engineering_analysis={notes:'SYNTHETIC — analisis manual tetap terlihat.',recommended_follow_up:'SYNTHETIC — verifikasi oleh engineer.'};
const copy = JSON.parse(readFileSync("lib/id-messages.json")),
  t = (k) => copy[k] ?? k;
const asset = fixture.asset.canonical_id,
  now = "2026-10-11T08:00:00+07:00",
  checks = [],
  errors = [],
  requests = [],
  violations = [];
let newerCaseRevision = false;
let overviewFailure = null;
const sourceEvent={event_key:'a'.repeat(64),source_ref:'WB-SYNTHETIC',source_sha256:'c'.repeat(64),sheet_index:0,sheet_label:'Peralatan DEMO',profile_id:'profile-synthetic',axis:'ROW',position:3,kind:'MEASUREMENT_SOURCE',classification:'RAW_UNRESOLVED',source_asset_label:'Label DEMO belum dipetakan',clocks:[{role:'UNSPECIFIED',precision:'DATE',value:'2019-01-03',raw_value:'2019-01-03'}],reasons:['UNIT_UNKNOWN'],distinct_source_cells:2,canonical_eligible:false};
const sourceField=(id,raw)=>({field_id:id,cell:id==='zero'?'B3':'C3',role:'INPUT',label_claim:'Velocity DEMO',unit_claim:null,source_point_claim:null,source_axis_claim:null,value:{coordinate:id==='zero'?'B3':'C3',raw_value:raw,formula_present:false,cache_status:'NOT_FORMULA'},headers:[],unit_evidence:[]});
const cases = [
  "DEMO — telaah pengukuran motor",
  "DEMO — variasi konteks akuisisi",
  "DEMO — verifikasi rujukan evidence",
  "DEMO — pemeriksaan lanjutan",
].map((title, i) => ({
  case_id: "case:DEMO-00" + (i + 1),
  title,
  problem_statement:
    "SYNTHETIC — Apakah perbedaan konteks akuisisi memengaruhi keterbandingan pengukuran?",
  canonical_asset_id: asset,
  category: "INVESTIGATION",
  priority: i === 0 ? "HIGH" : "NORMAL",
  assigned_engineer: "demo-engineer",
  created_by: "demo-engineer",
  status: i === 2 ? "IN_REVIEW" : "DRAFT",
  revision: 3,
  updated_at: now,
  investigation: {
    operating_context:
      "SYNTHETIC — beban dan konteks operasi dilaporkan inspector; bukan bukti pembangkit.",
    observed_symptoms: ["SYNTHETIC — observasi berulang pada titik yang sama."],
    observations: [
      "SYNTHETIC — nilai nol tercatat; parameter kedua belum diketahui.",
    ],
    hypotheses: [
      "SYNTHETIC — perbedaan akuisisi mungkin berpengaruh; belum tervalidasi.",
    ],
    open_questions: [
      "Apakah identitas titik dan instrumen sudah dikonfirmasi?",
    ],
    proposed_next_checks: ["Konfirmasi konteks sebelum membandingkan seri."],
  },
  review: null,
  evidence: [
    {
      reference_id: "reference:DEMO-001",
      kind: "MANUAL_INSPECTION",
      record_id: fixture.inspections[0].record_id,
      mode: "FROZEN_SNAPSHOT",
      stable_version: "SYNTHETIC-r3-sha256",
      source_timestamp: fixture.inspections[0].inspected_at,
      snapshot: {
        label: "DEMO — snapshot inspeksi",
        availability: "AVAILABLE",
      },
    },
  ],
  notes: [
    {
      text: "SYNTHETIC — konteks dicatat terpisah dari hipotesis.",
      actor: "demo-engineer",
    },
  ],
}));
const pageOf = (items,u) => {const offset=Number(u?.searchParams.get('offset')??0),limit=Number(u?.searchParams.get('limit')??25);return {items:items.slice(offset,offset+limit),total:items.length,offset,limit,has_more:offset+limit<items.length,filter_scope:'AUTHORIZED_POPULATION',event_time_basis:'INSPECTED_AT'};};
const check = (name, value) => {
  assert.ok(value, name);
  checks.push(name);
};
await ctx.route("**/*", async (route) => {
  const r = route.request(),
    u = new URL(r.url()),
    p = u.pathname;
  requests.push({
    path: p,
    query: u.search,
    method: r.method(),
    ...(r.method() !== "GET" ? { body: r.postDataJSON() } : {}),
  });
  if (u.origin !== base) return route.abort("blockedbyclient");
  if (p === "/candidate.js")
    return route.fulfill({
      contentType: "application/javascript",
      body: bundle.js,
    });
  if (p === "/candidate.css")
    return route.fulfill({ contentType: "text/css", body: bundle.css });
  if (p === "/logo_nadi.png")
    return route.fulfill({
      contentType: "image/png",
      body: readFileSync("public/logo_nadi.png"),
    });
  if (r.isNavigationRequest())
    return route.fulfill({
      contentType: "text/html",
      body: '<!doctype html><html lang="id"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>SYNTHETIC NADI design comparison</title><link rel="stylesheet" href="/candidate.css"></head><body><div id="root"></div><script src="/candidate.js"></script></body></html>',
    });
  if (p.includes("decision-overview")) {if(overviewFailure==="network")return route.abort();if(overviewFailure)return route.fulfill({status:overviewFailure,json:{detail:{code:"SYNTHETIC_DENIED"}}});return route.fulfill({ json: overview });}
  if (p.startsWith("/api/engineering-qa/")) {
    const [resource, encoded, action] = p
        .slice("/api/engineering-qa/".length)
        .split("/"),
      id = decodeURIComponent(encoded ?? "");
    if(resource==='auth'&&id==='login')return route.fulfill({json:{authenticated:true}});
    if (resource === "session")
      return route.fulfill({
        json: {
          subject: "demo-engineer",
          roles: ["AUTHOR"],
          asset_ids: [asset],
          csrf_token: "SYNTHETIC_NOT_A_SESSION",
        },
      });
    if(resource==='source-history'){
 if(id==='batches')return route.fulfill({json:{scope:'AUTHORIZED_PROVISIONAL_SOURCE',items:[{batch_id:'b'.repeat(64),state:'COMPLETE',counts:{cells:2,events:1},coverage:[{source_ref:'WB-SYNTHETIC',sheet_index:0,sheet_label:'Peralatan DEMO',populated_cells:2,terminal_cells:{INPUT:2},overlapping_value_claim_cells:0}]}],has_more:false,next_after:null}});
 if(id)return route.fulfill({json:{item:sourceEvent,fields:[sourceField('zero',0),sourceField('unknown',null)],field_total:2,offset:0,limit:25,has_more:false,next_offset:null,previous_offset:null,clock_evidence:[],aliases:[],profile_version:'SYNTHETIC-1',classification_hash:'e'.repeat(64),editable:false,canonical_eligible:false,...(process.env.NADI_SOURCE_INTERPRETATION_ACCEPTANCE==='1'?{derived_interpretation:{version:'SYNTHETIC',notice:'SYNTHETIC display-only estimate; not a measurement.',source_sha256:'a'.repeat(64),canonical_eligible:false,persisted:false,date:null,row_context:null,fields:[{field_id:'unknown',cell:'C3',kind:'SOURCE_HEADER',label:'SYNTHETIC point',unit:'mm/s',method:'SYNTHETIC_HEADER_PROOF',evidence:[{coordinate:'C2',raw_value:'SYNTHETIC point'}],estimate:{label:'ESTIMASI',value:1.5,unit:'mm/s',method:'LINEAR_TIME_INTERPOLATION_DISPLAY_ONLY_V1',gap_days:57,confidence:'LOW',notice:'SYNTHETIC estimate; bukan nilai terukur atau dasar alert/Case.',evidence:[{coordinate:'C1',raw_value:1},{coordinate:'C5',raw_value:2}]}}]}}:{})}});
 return route.fulfill({json:{scope:'AUTHORIZED_PROVISIONAL_SOURCE',items:[sourceEvent],total:1,has_more:false,next_after:null}});
 }
 if(resource==='inspections'&&id==='measurement-history')return route.fulfill({json:{...pageOf(fixture.inspections.flatMap(row=>row.measurements.map((measurement,measurement_index)=>({...row,measurement_index,measurement}))),u),event_time_basis:'MEASURED_AT'}});
 if (resource === "asset-context")
      return route.fulfill({
        json: {
          canonical_asset_id: asset,
          identity_availability: "AVAILABLE",
          identity: {
            description: "DEMO Motor 1 · QA SINTETIS",
            location_ref: "DEMO location",
          },
        },
      });
    if (action === "history")
      return route.fulfill({
        json: [
          {
            revision: 3,
            actor: "demo-engineer",
            action: "UPDATE",
            occurred_at: now,
            reason: "SYNTHETIC — observasi diperjelas",
          },
          {
            revision: 2,
            actor: "demo-engineer",
            action: "EVIDENCE",
            occurred_at: now,
            reason: "SYNTHETIC — snapshot exact",
          },
          {
            revision: 1,
            actor: "demo-engineer",
            action: "CREATE",
            occurred_at: now,
            reason: "SYNTHETIC — draf awal",
          },
        ],
      });
    const rows =
      resource === "cases"
        ? cases
        : resource === "inspections"
          ? fixture.inspections
          : resource === "recommendations" ? fixture.recommendations : [];
    if (r.method() !== "GET")
      return route.fulfill({
        status: 409,
        json: { detail: { code: "SYNTHETIC_CONFLICT" } },
      });
    let result = rows;
    if (u.searchParams.get("status"))
      result = result.filter((x) => x.status === u.searchParams.get("status"));
    if (u.searchParams.get("method"))
      result = result.filter((x) => x.method === u.searchParams.get("method"));
    if (u.searchParams.get("search"))
      result = result.filter((x) =>
        JSON.stringify(x).includes(u.searchParams.get("search")),
      );
    return route.fulfill({
      json: id
        ? {...rows.find((x) => (x.case_id ?? x.record_id) === id),...(resource==="cases"&&newerCaseRevision?{revision:4}:{})}
        : pageOf(result,u),
    });
  }
  return route.fulfill({ status: 404, body: "" });
});
page.on("pageerror", (e) => errors.push(e.message));
const button = (name) => page.getByRole("button", { name, exact: true });
const go = async (path) => {
  await page.goto(base + path, { waitUntil: "networkidle" });
  await page.locator(".loading-state").waitFor({ state: "hidden" });
};
async function editor() {
  await go("/pdm");
  await button("Input Pengukuran").click();
  await page
    .getByLabel("Versi metode / prosedur")
    .fill("SYNTHETIC-candidate-v1");
  await page.getByLabel("Waktu inspeksi asli").fill(now);
  for (let i = 1; i <= 3; i++) {
    if (i > 1) await button("Tambah baris").click();
    await page
      .getByLabel("Titik " + i, { exact: true })
      .fill("point:DEMO-" + i);
    await page
      .getByLabel("Parameter " + i, { exact: true })
      .fill("DEMO velocity");
    await page
      .getByLabel("Tipe nilai " + i, { exact: true })
      .selectOption(i === 3 ? "UNKNOWN" : "NUMERIC");
    if (i < 3)
      await page
        .getByLabel("Nilai asli " + i, { exact: true })
        .fill(i === 1 ? "0" : "4.2");
    await page.getByLabel("Unit asli " + i, { exact: true }).fill("mm/s");
    await page
      .getByLabel("Waktu measurement " + i, { exact: true })
      .fill(i === 3 ? "" : now);
  }
  await page
    .getByLabel("Observasi (satu per baris)")
    .fill("SYNTHETIC — titik kedua perlu konfirmasi konteks.");
}

async function openHistory(kind){
 await go('/pdm');await button('Riwayat & Tren').click();
 const tab=button(kind);if(await tab.count())await tab.click();
 if(kind==='Sumber Excel'){await button('Baca kelompok sumber').waitFor();await button('Baca kelompok sumber').click();await page.getByRole('region',{name:'Detail kelompok sumber'}).waitFor();}
 else {await page.locator('.pdm-history tbody tr').first().waitFor();await page.getByLabel('Plot sampel pada halaman ini (satu inspeksi)').selectOption(fixture.inspections[0].record_id);}
}
const screens=[
 ['navigation',()=>go('/action-board')],['pdm-register',()=>go('/pdm')],['measurement-editor',editor],
 ['inspection-detail',()=>go('/pdm?record='+encodeURIComponent(fixture.inspections[0].record_id))],
 ['native-history',()=>openHistory('Pengukuran Asli')],['excel-history',()=>openHistory('Sumber Excel')],
 ['case-handoff',async()=>{await go('/pdm?record='+encodeURIComponent(fixture.inspections[0].record_id));await page.getByRole('button',{name:/^(Mulai|Buat) Engineering Case$/}).click();await page.locator('#case-title').waitFor();}],
];
try{
 await page.setViewportSize({width:1440,height:900});await go('/pdm');await page.locator('.pdm-register tbody tr').first().waitFor();
 await page.evaluate(async()=>{await document.fonts.ready;await Promise.all(document.getAnimations().filter(a=>Number.isFinite(a.effect?.getComputedTiming().endTime)).map(a=>a.finished.catch(()=>{})));});
 const firstRow=await page.locator('.pdm-register tbody tr').first().boundingBox();
 writeFileSync(out+'/first-row.json',JSON.stringify({y:firstRow.y,bottom:firstRow.y+firstRow.height}));
 checks.push({name:'first register row at1440x900',pass:baseline||firstRow.y+firstRow.height<=900,y:firstRow.y,bottom:firstRow.y+firstRow.height});
 console.log('Register1440x900 bounds '+JSON.stringify({y:firstRow.y,bottom:firstRow.y+firstRow.height}));
 if(!baseline)assert.ok(firstRow.y+firstRow.height<=900,'entire first inspection row must fit inside1440x900: '+JSON.stringify(firstRow));
 await page.screenshot({path:out+'/register-1440x900.png',fullPage:true});
 for(const width of (process.env.NADI_BROWSER_WIDTHS??'390,768,1440,1920').split(',').map(Number))for(const theme of ['light','dark'])for(const [name,open]of screens){
  await page.setViewportSize({width,height:1086});await open();
  await page.evaluate(t=>{document.documentElement.dataset.theme=t;document.activeElement?.blur();window.scrollTo(0,0)},theme);
  if(name==='navigation'&&width<1024)await page.getByRole('button',{name:t('Open navigation'),exact:true}).click();
  await page.evaluate(()=>Promise.all(document.getAnimations().filter(a=>Number.isFinite(a.effect?.getComputedTiming().endTime)).map(a=>a.finished.catch(()=>{}))));
  check('no overflow '+name+width+theme,await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  if(Axe&&!baseline){const a=await new Axe({page}).withTags(['wcag2a','wcag2aa','wcag21a','wcag21aa']).analyze();violations.push(...a.violations.map(v=>({screen:name,width,theme,id:v.id,nodes:v.nodes.map(n=>({target:n.target,summary:n.failureSummary}))})));}
  await page.screenshot({path:out+'/'+name+'-'+theme+'-'+width+'.png',fullPage:true});console.log('CAPTURE '+name+' '+width+' '+theme);
 }

 if(!baseline){
  await page.setViewportSize({width:1440,height:900});
  for(const status of [403,401,503,500,'network']){
   overviewFailure=status;await go('/');if(status===401){await page.waitForURL(base+'/login?expired=1');check('401 follows existing legitimate login renewal',await page.getByRole('textbox',{name:t('Username'),exact:true}).count()===1);await page.screenshot({path:out+'/overview-401.png',fullPage:true});continue;}const alert=page.getByRole('alert');await alert.waitFor();
   const text=await alert.innerText();const retry=await alert.getByRole('button',{name:t('Try again'),exact:true}).count();
   if(status===403){check('403 has access guidance without outage or retry',text.includes('scope')&&!text.includes('belum dapat dibaca')&&retry===0);}
   else if(status===401){check('401 offers legitimate renewal without retry',await alert.getByRole('link',{name:'Masuk kembali'}).count()===1&&retry===0);}
   else check('retryable factual error '+status,retry===1&&text.includes('belum dapat dibaca'));
   await page.screenshot({path:out+'/overview-'+status+'.png',fullPage:true});
  }
  overviewFailure=null;
  await go('/pdm?record='+encodeURIComponent(fixture.inspections[0].record_id));check('manual analysis visible outside reference disclosures',await page.getByText('SYNTHETIC — analisis manual tetap terlihat.',{exact:true}).isVisible());
  await page.setViewportSize({width:1440,height:1086});await go('/login?returnTo=%2Fpdm');
  await page.getByRole('textbox',{name:t('Username'),exact:true}).fill('synthetic-engineer');await page.getByRole('textbox',{name:t('Password'),exact:true}).fill('SYNTHETIC-NOT-A-CREDENTIAL');await button(t('Sign in')).click();await page.waitForURL(base+'/pdm');await page.locator('.pdm-register').waitFor();check('actual login component leads authorized synthetic engineer to PdM',true);
  const primary=page.getByRole('group',{name:'Area kerja utama',exact:true});check('exact five primary entries',JSON.stringify(await primary.getByRole('link').allTextContents())===JSON.stringify(['Beranda','Aset','PdM Center','Tindak Lanjut','Laporan']));
  check('inspection request keeps limit one',requests.some(r=>r.path.endsWith('/inspections')&&new URLSearchParams(r.query).get('limit')==='1'));
  check('current page count is not the total inspection population',await page.locator('.record-open').count()===1&&(await page.locator('.pdm-status-strip').innerText()).includes('3'));
  await go('/pdm?context=SYNTHETIC');await page.locator('.record-open').first().click();await page.locator('#pdm-record-pane').waitFor();check('selection preserves unrelated query and exact record',new URL(page.url()).searchParams.get('context')==='SYNTHETIC'&&new URL(page.url()).searchParams.get('record')===fixture.inspections[0].record_id);
  await page.goBack();await page.locator('.pdm-register').waitFor();check('Back restores register with query',new URL(page.url()).searchParams.get('context')==='SYNTHETIC'&&!new URL(page.url()).searchParams.has('record'));
  await page.goForward();await page.locator('#pdm-record-pane').waitFor();check('Forward restores exact inspection detail',new URL(page.url()).searchParams.get('record')===fixture.inspections[0].record_id);
  check('no competing Input primary on detail',await button('Input Pengukuran').count()===0);
  await button('Buat Engineering Case').click();check('optional Case uses existing form only after deliberate action',await page.locator('#case-title').isVisible());
  await go('/pdm');await button('Input Pengukuran').click();check('entry has four continuous sections',await page.locator('#measurement-context').isVisible()&&await page.locator('#measurement-values').isVisible()&&await page.locator('#measurement-notes').isVisible()&&await page.locator('#measurement-follow-up').isVisible());check('entry has no competing new-input action',await button('Input Pengukuran').count()===0);
  await page.getByLabel('Parameter 1',{exact:true}).fill('SYNTHETIC draft');await button('Simpan draf inspeksi').click();check('required method version remains visible and focused',await page.getByLabel('Versi metode / prosedur').evaluate(n=>n===document.activeElement));await page.getByLabel('Versi metode / prosedur').fill('SYNTHETIC-1');
  let hashDialogs=0;const refuseHashDialog=async d=>{hashDialogs++;await d.dismiss();};page.on('dialog',refuseHashDialog);
  await page.locator('.editor-index a[href="#measurement-values"]').click();await page.locator('.editor-index a[href="#measurement-notes"]').click();await page.goBack();
  check('dirty section Back preserves mounted editor without discard',new URL(page.url()).hash==='#measurement-values'&&await page.getByLabel('Parameter 1',{exact:true}).inputValue()==='SYNTHETIC draft'&&hashDialogs===0);
  await page.goForward();check('dirty section Forward preserves draft and section',new URL(page.url()).hash==='#measurement-notes'&&await page.getByLabel('Parameter 1',{exact:true}).inputValue()==='SYNTHETIC draft'&&hashDialogs===0);page.off('dialog',refuseHashDialog);
  page.once('dialog',d=>d.dismiss());await button('Register Inspeksi').click();check('cancelled leave preserves draft',await page.getByLabel('Parameter 1',{exact:true}).inputValue()==='SYNTHETIC draft');
  await page.getByText('Tambahkan rujukan evidence yang berhak Anda laporkan (metadata saja)',{exact:true}).click();await page.getByLabel('Ukuran evidence (byte)',{exact:true}).fill('not-a-number');await page.getByText('Tambahkan rujukan evidence yang berhak Anda laporkan (metadata saja)',{exact:true}).click();
  await button('Simpan draf inspeksi').click();await page.getByRole('alert').filter({hasText:'Isian belum disimpan'}).waitFor();check('model validation announces failure and retains draft',await page.getByLabel('Parameter 1',{exact:true}).inputValue()==='SYNTHETIC draft'&&await page.getByRole('alert').filter({hasText:'Isian belum disimpan'}).evaluate(n=>n.parentElement===document.activeElement));
  page.once('dialog',d=>d.accept());await button('Batal input').click();await page.locator('.pdm-register').waitFor();
  await button('Riwayat & Tren').click();await button('Pengukuran Asli').click();check('native source panel hidden, separate counts',await page.locator('.pdm-history').isVisible()&&!await page.locator('.pdm-source-history').isVisible());await button('Sumber Excel').click();await button('Baca kelompok sumber').click();await page.getByRole('region',{name:'Detail kelompok sumber'}).waitFor();check('Excel panel separate and raw zero/null visible',!await page.locator('.pdm-history').isVisible()&&(await page.getByRole('region',{name:'Detail kelompok sumber'}).innerText()).includes('Tipe sumber: null'));
  if(process.env.NADI_SOURCE_INTERPRETATION_ACCEPTANCE==='1'){
   check('F23 estimate notice stays visible beside reading',await page.getByText('Pratinjau, sebagian nilai diestimasi',{exact:true}).isVisible());
   const estimate=page.getByLabel('Estimasi 1,50 mm/s, buka asal dan metode',{exact:true});await estimate.focus();await page.keyboard.press('Enter');
   check('F23 keyboard disclosure preserves raw blank and low confidence evidence',await page.getByText('Nilai asli:',{exact:false}).isVisible()&&await page.getByText('Keyakinan: rendah · jeda 57 hari.',{exact:true}).isVisible()&&await page.getByText('C1: 1',{exact:true}).isVisible()&&await page.getByText('C5: 2',{exact:true}).isVisible());
  }
  await page.setViewportSize({width:390,height:844});await go('/action-board');const menu=button(t('Open navigation'));await menu.click();await page.getByRole('dialog',{name:t('NADI navigation panel')}).waitFor();await page.keyboard.press('Escape');check('Escape closes mobile drawer and returns focus',await menu.evaluate(n=>document.activeElement===n)&&await menu.getAttribute('aria-expanded')==='false');
  await page.setViewportSize({width:1440,height:1086});await go('/recommendations');await button('Perangkat Engineering').click();check('only exact utility URL has aria-current page',await page.locator('.nadi-sidebar [aria-current="page"]').count()===1&&await page.locator('.nadi-primary-nav .active').innerText()==='Tindak Lanjut');
 }
 check('no browser exceptions',errors.length===0);check('WCAG A/AA automated',violations.length===0);
 writeFileSync(out+'/results.json',JSON.stringify({label:'SYNTHETIC actual components; fully intercepted; no live runtime',baseline,checks,errors,violations,requests},null,2));
 console.log('Simplification PASS '+checks.length+' checks');
}catch(e){writeFileSync(out+'/failure.json',JSON.stringify({error:String(e),checks,errors,violations,requests},null,2));throw e;}finally{await browser.close();rmSync(bundle.temp,{recursive:true,force:true});}
