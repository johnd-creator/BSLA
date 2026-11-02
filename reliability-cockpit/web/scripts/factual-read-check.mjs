import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {mkdtempSync,writeFileSync,readFileSync,chmodSync,symlinkSync,unlinkSync,rmSync,renameSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join,resolve} from 'node:path';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url),dir=mkdtempSync(join(tmpdir(),'synthetic-factual-read-'));
const asset='asset:MAXIMO:MXASSET:BSR:IP:SYNTHETIC-A',foreign=asset.replace('SYNTHETIC-A','SYNTHETIC-FOREIGN'),subject='local:synthetic-engineer';
const caps=['FACTUAL_ASSET_READ','FACTUAL_DASHBOARD_READ','FACTUAL_MAINTENANCE_READ'];
const now=Date.now(),stamp=n=>new Date(n).toISOString().replace(/\.\d{3}Z$/,'Z');
const canonical=v=>Array.isArray(v)?'['+v.map(canonical).join(',')+']':v!==null&&typeof v==='object'?'{'+Object.keys(v).sort().map(k=>JSON.stringify(k)+':'+canonical(v[k])).join(',')+'}':JSON.stringify(v);
function event(overrides={}){const e={action:'ISSUE',version:1,previous_sha256:'0'.repeat(64),grant_id:'synthetic-grant',subject,assets:[asset],capabilities:caps,not_before:stamp(now-2000),expires_at:stamp(now+3600000),actor:'local:c759c2d1-19a4-4291-9b66-9218dbd12dea',approval_ref:'synthetic-owner-approval',operator_ref:'synthetic-operator',at:stamp(now-1000),...overrides};return {...e,sha256:createHash('sha256').update(canonical(e)).digest('hex')};}
const issue=event(),ledger='{"schema_version":1}\n'+canonical(issue)+'\n';
let count=0;const check=async(name,fn)=>{await fn();count++;console.log('PASS '+name);};
try{
 chmodSync(dir,0o700);
 execFileSync(process.execPath,['node_modules/typescript/bin/tsc','lib/factual-gateway.ts','lib/factual-read-policy.ts','--outDir',dir,'--module','commonjs','--target','ES2022','--skipLibCheck'],{stdio:'pipe'});
 const {parseFactualRead,readFactualRead,EMPTY_FACTUAL_READ}=require(join(dir,'factual-read-policy.js'));
 const {factualAccess,factualGateway}=require(join(dir,'factual-gateway.js'));
 const {scopedRegister}=require(join(dir,'factual-scoped-reader.js'));
 const snapshot=parseFactualRead(ledger,subject),session={subject,roles:['AUTHOR'],asset_ids:['SYNTHETIC-QA']};
 const request=(path,method='GET')=>new Request('https://localhost:3000/api/cockpit/'+path,{method,headers:{cookie:'__Host-nadi_session='+'a'.repeat(43),'x-role':'ADMIN','x-asset-ids':foreign}});
 const row={canonical_id:'maintenance:SYNTHETIC-WO',contract_version:'1',id:'SYNTHETIC-WO',equipment_id:asset,work_order_id:'SYNTHETIC-WO',event_type:'CM',status:'COMP',actual_start:null,actual_finish:null,duration_hours:null,labor_hours:0,downtime_hours:0,failure_code:null,source_changed_at:'2026-11-01T01:00:00Z',site_code:'BSR',organization_code:'IP',classification:{raw_work_type:'CM',canonical_category:'CM',state:'CANONICAL_SUPPORTED',origin:'RETAINED_MAXIMO_WORKTYPE',confidence:'VERIFIED',description:null,workflow_name:null,workflow_version:null,workflow_state:'NOT_AVAILABLE',status_state:'AVAILABLE'},source_detail:{work_order_number:'SYNTHETIC-WO',asset_number:'SYNTHETIC-A',reported_at:null,scheduled_start:null,scheduled_finish:null}};
 const calls=[];
 function fakeFetch(url){const u=new URL(url);calls.push(u);
  if(u.port==='13036')return Response.json(session);
  if(u.pathname.startsWith('/v1/reliability/assets/'))return Response.json({canonical_id:decodeURIComponent(u.pathname.split('/').at(-1)),contract_version:'1',source_asset_number:'SYNTHETIC-A',description:'SYNTHETIC FIXTURE',status:'ACTIVE',location_ref:null,parent_asset_ref:foreign,site_code:'BSR',organization_code:'IP',asset_type:'TEST',plant:'SYNTHETIC',unit:'SYNTHETIC',source_updated_at:null,portfolio_secret:99999});
  if(u.pathname==='/v1/reliability/maintenance-events'){assert.equal(u.searchParams.get('asset_ref'),asset);const offset=Number(u.searchParams.get('offset')??0),limit=Number(u.searchParams.get('limit')??50),items=Array.from({length:Math.min(limit,Math.max(0,14-offset))},(_,i)=>({...row,canonical_id:row.canonical_id+'-'+(offset+i)}));return Response.json({items,meta:{total:14,offset,limit,has_more:offset+items.length<14},portfolio_secret:99999});}
  throw new Error('Broad/unapproved upstream path: '+u.pathname);
 }
 const run=(p,reader=()=>snapshot,fetcher=fakeFetch,method='GET')=>factualGateway(request(p,method),p.split('?')[0].split('/'),fetcher,true,reader,()=>{});
 await check('Python and server consume identical canonical policy bytes',()=>{
  const script='import sys,importlib.util; s=importlib.util.spec_from_file_location("factual_policy", "src/services/factual_read_entitlements.py"); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); e=m.decode(sys.stdin.buffer.read()); assert len(e)==1; print("PASS")';
  assert.equal(execFileSync('python3',['-c',script],{cwd:resolve('..'),input:ledger,encoding:'utf8',env:{PATH:process.env.PATH,PYTHONDONTWRITEBYTECODE:'1'}}).trim(),'PASS');
 });
 await check('immutable subject, exact BSR/IP scope and three READ capabilities',()=>{
  assert.deepEqual(snapshot.permissions[asset],caps);assert.deepEqual(parseFactualRead(ledger,'local:other').permissions,{});
  for(const overrides of [{assets:['*']},{assets:[asset.replace(':BSR:',':OTHER:')]},{capabilities:['ADMIN']},{actor:'local:other-admin'},{subject:issue.actor},{expires_at:stamp(now+2*86400000)}])assert.throws(()=>parseFactualRead('{"schema_version":1}\n'+canonical(event(overrides))+'\n',subject));
 });
 await check('expired grant supplies no permission; renewal cannot be forged',()=>{assert.deepEqual(parseFactualRead(ledger,subject,now+2*3600000).permissions,{});assert.equal(factualAccess(['v1','reliability','assets'],new URLSearchParams(),session,parseFactualRead(ledger,subject,now+2*3600000)),'FACTUAL_SCOPE_GRANT_REQUIRED');});
 await check('corruption, duplicate keys, invalid dates and truncated chain fail closed',()=>{
  for(const data of [ledger.slice(0,-1),ledger.replace('"version":1','"version":2'),ledger.replace('"action":"ISSUE"','"action":"REVOKE","action":"ISSUE"'),'{"schema_version":1}\n'+canonical(event({at:'2026-02-31T00:00:00Z'}))+'\n'])assert.throws(()=>parseFactualRead(data,subject));
 });
 await check('file reader requires private regular owned file and canonical parent',()=>{
  const file=join(dir,'grants.ndjson'),link=join(dir,'link.ndjson');writeFileSync(file,ledger,{mode:0o600});const before=process.env.NADI_FACTUAL_READ_POLICY_FILE;
  try{process.env.NADI_FACTUAL_READ_POLICY_FILE=file;assert.deepEqual(readFactualRead(subject),snapshot);chmodSync(file,0o644);assert.throws(()=>readFactualRead(subject));chmodSync(file,0o600);symlinkSync(file,link);process.env.NADI_FACTUAL_READ_POLICY_FILE=link;assert.throws(()=>readFactualRead(subject));unlinkSync(link);}
  finally{if(before===undefined)delete process.env.NADI_FACTUAL_READ_POLICY_FILE;else process.env.NADI_FACTUAL_READ_POLICY_FILE=before;}
 });
 await check('scoped Register applies exact allowlist before filter/count/page and strips foreign parent',async()=>{
  const r=await run('v1/reliability/assets?limit=1&status=ACTIVE'),p=await r.json();assert.equal(r.status,200);assert.equal(p.meta.total,1);assert.equal(p.items.length,1);assert.equal(p.items[0].parent_asset_ref,null);assert(!JSON.stringify(p).includes('portfolio_secret'));assert(calls.every(u=>u.port==='13036'||u.pathname!=='/v1/reliability/assets'));
  const filtered=await (await run('v1/reliability/assets?status=FOREIGN')).json();assert.equal(filtered.meta.total,0);
  const paged=await (await run('v1/reliability/assets?offset=1&limit=1')).json();assert.equal(paged.meta.total,1);assert.equal(paged.items.length,0);
 });
 await check('authorized detail, Maintenance, WO raw type/status and source detail remain readable',async()=>{
  assert.equal((await run('v1/reliability/assets/'+encodeURIComponent(asset).replaceAll('%3A',':'))).status,200);
  const r=await run('v1/reliability/maintenance-events?asset_ref='+encodeURIComponent(asset)+'&limit=50');assert.equal(r.status,200);const p=await r.json();assert.equal(p.meta.total,14);assert.equal(p.items[0].classification.raw_work_type,'CM');assert.equal(p.items[0].status,'COMP');assert.equal(p.items[0].source_detail.work_order_number,'SYNTHETIC-WO');assert(!JSON.stringify(p).includes('portfolio_secret'));
 });
 await check('Beranda read model uses only exact permitted Asset and WO queries',async()=>{
  const r=await run('v1/reliability/scoped-overview');assert.equal(r.status,200);const p=await r.json();assert.deepEqual(p.summary,{registered_assets:1,maintenance_events:14,assets_with_maintenance:1});assert.equal(p.operational_kpis,'NOT_ELIGIBLE');assert(!JSON.stringify(p).includes(foreign));assert(!calls.some(u=>['decision-overview','context','integration-status'].some(s=>u.pathname.endsWith('/'+s))));
 });
 await check('unrelated asset, portfolio aggregates, context, FMEA, health and PI denied before upstream',async()=>{
  for(const p of ['assets/'+foreign,'decision-overview','assets/'+asset+'/context','assets/'+asset+'/integration-status','assets/'+asset+'/condition-evidence','assets/'+asset+'/fmea','assets/'+asset+'/health/latest','fmea?asset_ref='+asset,'asset-health?asset_ref='+asset,'maintenance-events?asset_ref='+foreign,'maintenance-events']){
   const before=calls.filter(u=>u.port==='8000').length;const r=await run('v1/reliability/'+p);assert.equal(r.status,403,p);assert.equal(calls.filter(u=>u.port==='8000').length,before,p);
  }
 });
 await check('no Factual grant or client role/header grants never becomes portfolio or Engineering authority',async()=>{
  assert.equal((await run('v1/reliability/assets',()=>EMPTY_FACTUAL_READ)).status,403);assert.deepEqual(session.roles,['AUTHOR']);assert.deepEqual(session.asset_ids,['SYNTHETIC-QA']);
  for(const method of ['POST','PUT','PATCH','DELETE'])assert.equal((await run('v1/reliability/assets',()=>snapshot,fakeFetch,method)).status,405);
 });
 await check('dashboard capability alone never grants Asset or Maintenance',async()=>{
  const limited={...snapshot,permissions:{[asset]:['FACTUAL_DASHBOARD_READ']}};assert.equal((await run('v1/reliability/scoped-overview',()=>limited)).status,403);assert.equal((await run('v1/reliability/assets',()=>limited)).status,403);
 });
 await check('revocation/expiry/version/head change during upstream read discards protected body',async()=>{
  for(const final of [EMPTY_FACTUAL_READ,{...snapshot,head:'f'.repeat(64)},{...snapshot,permissions:{}}]){let reads=0;const r=await run('v1/reliability/scoped-overview',()=>++reads===1?snapshot:final);assert.equal(r.status,403);assert(!(await r.text()).includes('SYNTHETIC FIXTURE'));}
 });
 await check('cross-scope upstream rows and source identities fail closed with no body release',async()=>{
  const fetcher=url=>new URL(url).pathname==='/v1/reliability/maintenance-events'?Response.json({items:[{...row,equipment_id:foreign}],meta:{total:99999,offset:0,limit:1,has_more:true}}):fakeFetch(url);
  const r=await run('v1/reliability/scoped-overview',()=>snapshot,fetcher);assert.equal(r.status,503);assert(!(await r.text()).includes('99999'));
 });
 await check('typed scalar DTO and complete page proof reject nested data or misleading totals',async()=>{
  for(const corrupt of ['asset-object','empty-total','wrong-offset','wrong-limit','nested-classification']){
   const fetcher=async url=>{const response=await fakeFetch(url),p=await response.json(),u=new URL(url);
    if(u.port==='8000'&&u.pathname.startsWith('/v1/reliability/assets/')&&corrupt==='asset-object')p.description={private:'must-not-leak'};
    if(u.pathname==='/v1/reliability/maintenance-events'){
     if(corrupt==='empty-total')p.items=[];
     if(corrupt==='wrong-offset')p.meta.offset=1;
     if(corrupt==='wrong-limit')p.meta.limit=2;
     if(corrupt==='nested-classification')p.items[0].classification.raw_work_type={private:'must-not-leak'};
    }
    return Response.json(p);
   };
   const r=await run('v1/reliability/scoped-overview',()=>snapshot,fetcher);assert.equal(r.status,503,corrupt);assert(!(await r.text()).includes('must-not-leak'));
  }
 });
 await check('multi-asset ordering compares zoned instants and keeps unknown clocks last',async()=>{
  const ids=['A','B','C','D'].map(n=>asset.replace('SYNTHETIC-A','SYNTHETIC-'+n));
  const clocks=['2026-11-02T10:00:00+07:00','2026-11-02T04:00:00Z',null,'2026-11-02T12:00:00'];
  const multi={...snapshot,permissions:Object.fromEntries(ids.map(id=>[id,caps]))};
  const fetcher=async url=>{const response=await fakeFetch(url),p=await response.json(),id=decodeURIComponent(new URL(url).pathname.split('/').at(-1));p.source_asset_number=id.split(':').at(-1);p.source_updated_at=clocks[ids.indexOf(id)];return Response.json(p);};
  for(const [sort,expected] of [['updated_desc',[ids[1],ids[0],ids[3],ids[2]]],['updated_asc',[ids[0],ids[1],ids[3],ids[2]]]]){
   const page=await scopedRegister(new URLSearchParams({sort}),multi,fetcher,new AbortController().signal);assert.deepEqual(page.items.map(a=>a.canonical_id),expected);
  }
 });
 await check('bad new ledger does not remove existing health or legacy granted-asset rights',async()=>{
  const never=()=>{throw new Error('new ledger is invalid');};
  const fetcher=url=>new URL(url).pathname==='/health'?Response.json({status:'ok'}):fakeFetch(url);
  assert.equal((await run('health',never,fetcher)).status,200);
  const legacy={...session,asset_ids:[asset]};
  const fetchLegacy=url=>new URL(url).port==='13036'?Response.json(legacy):fakeFetch(url);
  assert.equal((await run('v1/reliability/assets/'+asset,never,fetchLegacy)).status,200);
  assert.equal((await run('v1/reliability/assets',never,fetcher)).status,503);
 });
 await check('real atomic ledger replacement revokes in-flight read and successful reads audit privately',async()=>{
  const file=join(dir,'grants.ndjson'),before=process.env.NADI_FACTUAL_READ_POLICY_FILE;writeFileSync(file,ledger,{mode:0o600});chmodSync(file,0o600);
  try{
   process.env.NADI_FACTUAL_READ_POLICY_FILE=file;const p='v1/reliability/scoped-overview';
   const good=await factualGateway(request(p),p.split('/'),fakeFetch,true);assert.equal(good.status,200);
   const audit=JSON.parse(readFileSync(join(dir,'reads.ndjson'),'utf8').trim());assert.equal(audit.subject,subject);assert.equal(audit.action,'FACTUAL_READ');assert(!JSON.stringify(audit).includes('nadi_session'));assert(!JSON.stringify(audit).includes('SYNTHETIC-WO'));
   const revoke=event({action:'REVOKE',version:2,previous_sha256:issue.sha256,at:stamp(now),approval_ref:'synthetic-revoke'}),revoked=ledger+canonical(revoke)+'\n';
   let changed=false;const fetcher=url=>{if(!changed&&new URL(url).port==='8000'){const next=join(dir,'next.ndjson');writeFileSync(next,revoked,{mode:0o600});renameSync(next,file);changed=true;}return fakeFetch(url);};
   const denied=await factualGateway(request(p),p.split('/'),fetcher,true);assert.equal(denied.status,403);assert(!(await denied.text()).includes('SYNTHETIC FIXTURE'));
  }finally{if(before===undefined)delete process.env.NADI_FACTUAL_READ_POLICY_FILE;else process.env.NADI_FACTUAL_READ_POLICY_FILE=before;}
 });
 await check('anonymous, production-disabled and unavailable policy fail closed',async()=>{
  const p='v1/reliability/assets';assert.equal((await factualGateway(new Request('https://localhost:3000/api/cockpit/'+p),p.split('/'),fakeFetch,true,()=>snapshot)).status,401);
  assert.equal((await factualGateway(request(p),p.split('/'),fakeFetch,false,()=>snapshot)).status,503);
  assert.equal((await run(p,()=>{throw new Error('invalid');})).status,503);
 });
 await check('scoped page separates page access and datasets, preserves admin component and navigation',()=>{
  const page=readFileSync('app/(workspace)/page.tsx','utf8'),component=readFileSync('components/ScopedExecutiveOverview.tsx','utf8');assert(page.includes('!hasPortfolioRead(who.session)'));assert(page.includes('return <ExecutiveOverview />'));assert(component.includes('reliabilityApi.scopedOverview()'));assert(!component.includes('decisionOverview('));for(const text of ['NOT_ELIGIBLE','href="/pdm"','href="/assets"','Bagian dibatasi'])assert(component.includes(text));
 });
 console.log('Separate Factual READ checks passed: '+count);
}finally{rmSync(dir,{recursive:true,force:true});}
