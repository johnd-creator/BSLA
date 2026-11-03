import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {mkdtempSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url),dir=mkdtempSync(join(tmpdir(),'nadi-hierarchy-'));
try{
 execFileSync(process.execPath,['node_modules/typescript/bin/tsc','lib/factual-gateway.ts','--outDir',dir,'--module','commonjs','--target','ES2022','--skipLibCheck'],{stdio:'pipe'});
 const {factualAccess,factualGateway}=require(join(dir,'factual-gateway.js'));
 const {LOCAL_PORTFOLIO_READ}=require(join(dir,'factual-policy.js'));
 const root='asset:MAXIMO:MXASSET:BSR:IP:SYNTHETIC-ROOT',path=['v1','reliability','assets',root,'hierarchy'];
 const admin={subject:LOCAL_PORTFOLIO_READ.subject,roles:['ADMIN'],asset_ids:[]};
 const narrow={subject:'local:synthetic-author',roles:['AUTHOR'],asset_ids:[root]};
 assert.equal(factualAccess(path,new URLSearchParams(),admin),null);
 assert.equal(factualAccess(path,new URLSearchParams(),narrow),'PORTFOLIO_SCOPE_DENIED');
 assert.equal(factualAccess(['v1','reliability','assets',root],new URLSearchParams('node_ref='+root),admin),'QUERY_DENIED');
 assert.equal(factualAccess(path,new URLSearchParams(),{...admin,subject:'local:other-admin'}),'PORTFOLIO_SCOPE_DENIED');
 for(const query of ['node_ref=asset:MAXIMO:MXASSET:OTHER:IP:HIDDEN','node_ref=bad%0aref','node_ref=A&node_ref=B','offset=10001','limit=51','asset_ref='+root,'sort=status']){
  assert(factualAccess(path,new URLSearchParams(query),admin),query);
 }
 const req=()=>new Request('https://localhost:3000/api/cockpit/'+path.map(encodeURIComponent).join('/'),{headers:{cookie:'__Host-nadi_session='+'a'.repeat(43)}});
 let hierarchyReads=0;
 const badRoot=await factualGateway(req(),path,async url=>{
  if(String(url).includes(':13036'))return Response.json(admin);
  if(String(url).endsWith('/hierarchy'))hierarchyReads++;
  return Response.json({canonical_id:root,site_code:'OTHER',organization_code:'IP'});
 },true);
 assert.equal(badRoot.status,403);assert.equal(hierarchyReads,0);
 let sessions=0;
 const revoked=await factualGateway(req(),path,async url=>{
  if(String(url).includes(':13036'))return ++sessions===1?Response.json(admin):new Response(null,{status:401});
  return Response.json(String(url).endsWith('/hierarchy')?{synthetic:'withhold-after-revoke'}:{canonical_id:root,site_code:'BSR',organization_code:'IP'});
 },true);
 assert.equal(revoked.status,401);assert(!(await revoked.text()).includes('withhold-after-revoke'));
 let factual=0;
 const denied=await factualGateway(req(),path,async url=>{if(String(url).includes(':8000'))factual++;return Response.json(narrow);},true);
 assert.equal(denied.status,403);assert.equal(factual,0);
 // A hierarchy READ is independently approved for an exact registered root.
 const {parseFactualRead}=require(join(dir,'factual-read-policy.js'));
 const {scopedHierarchyPage}=require(join(dir,'factual-hierarchy-reader.js'));
 const caps=['FACTUAL_ASSET_READ','FACTUAL_HIERARCHY_READ'];
 const read={head:'1'.repeat(64),version:1,permissions:{[root]:caps}};
 assert.equal(factualAccess(path,new URLSearchParams(),narrow,read),null);
 assert.equal(factualAccess(path,new URLSearchParams(),narrow,{...read,permissions:{[root]:['FACTUAL_HIERARCHY_READ']}}),'PORTFOLIO_SCOPE_DENIED');
 assert.equal(factualAccess(path,new URLSearchParams(),narrow,{...read,permissions:{},registered:caps}),'PORTFOLIO_SCOPE_DENIED');
 assert.equal(factualAccess(path,new URLSearchParams('node_ref=asset:MAXIMO:MXASSET:BSR:IP:SYNTHETIC-ANCESTOR'),narrow,read),null);
 const prefix='asset:MAXIMO:MXASSET:BSR:IP:';
 const makeNode=(id,parent,registered=false)=>({canonical_id:prefix+id,source_asset_number:id,description:'SYNTHETIC',description_shortened:false,parent_asset_ref:parent?prefix+parent:null,status:'OPERATING',asset_type:'PRODUCTION',unit:null,registered,hierarchy_role:'UNKNOWN',source_has_children:true,source_updated_at:null,secret:'do-not-release'});
 const anchor=makeNode('SYNTHETIC-ROOT','SYNTHETIC-PARENT',true),parent=makeNode('SYNTHETIC-PARENT',null),part=makeNode('PART','SYNTHETIC-ROOT'),subpart=makeNode('SUBPART','PART');
 const page={root_ref:root,node:anchor,node_relation:'ROOT',path:[anchor],ancestors:[parent],ancestor_state:'NO_RETAINED_PARENT',unresolved_parent_ref:null,items:[part],total:1,offset:0,limit:25,has_more:false,completeness:'PARTIAL',source:'RETAINED_MAXIMO_PARENT',depth_limit:32,private:'do-not-release'};
 const permittedRequest=(id=root,query='')=>new Request('https://localhost:3000/api/cockpit/v1/reliability/assets/'+encodeURIComponent(id)+'/hierarchy'+query,{headers:{cookie:'__Host-nadi_session='+'a'.repeat(43)}});
 let upstreamCalls=0;
 const fetcher=async url=>{
  const u=new URL(url);
  if(u.port==='13036')return Response.json(narrow);
  upstreamCalls++;
  return Response.json(u.pathname.endsWith('/hierarchy')?page:{canonical_id:root,site_code:'BSR',organization_code:'IP'});
 };
 const release=await factualGateway(permittedRequest(),path,fetcher,true,()=>read,()=>{});
 assert.equal(release.status,200);const body=await release.text();assert(!body.includes('do-not-release'));assert(body.includes('PART'));assert(body.includes('"unit":null'));
 const before=upstreamCalls,foreign=prefix+'SYNTHETIC-OTHER';
 assert.equal((await factualGateway(permittedRequest(foreign),['v1','reliability','assets',foreign,'hierarchy'],fetcher,true,()=>read,()=>{})).status,403);assert.equal(upstreamCalls,before);
 const ancestorPage={...page,node:parent,node_relation:'ANCESTOR',path:[parent,anchor],items:[anchor]};
 assert.equal(scopedHierarchyPage(ancestorPage,root,parent.canonical_id,0,25).items[0].canonical_id,root);
 const descendantPage={...page,node:part,node_relation:'DESCENDANT',path:[anchor,part],items:[subpart]};
 assert.equal(scopedHierarchyPage(descendantPage,root,part.canonical_id,0,25).items[0].unit,null);
 for(const mutate of [
  p=>{p.root_ref=foreign;},p=>{p.path=[];},p=>{p.total=999;},p=>{p.items[0].parent_asset_ref=foreign;},
  p=>{p.node.description={private:'bad'};},p=>{p.node_relation='ANCESTOR';},p=>{p.ancestors[0].canonical_id=foreign;},
  p=>{p.items[0].canonical_id='asset:MAXIMO:MXASSET:OTHER:IP:PRIVATE';},p=>{p.items[0].hierarchy_role='SYSTEM';},
 ]){
  const corrupt=structuredClone(page);mutate(corrupt);assert.throws(()=>scopedHierarchyPage(corrupt,root,root,0,25));
  const response=await factualGateway(permittedRequest(),path,async url=>new URL(url).pathname.endsWith('/hierarchy')?Response.json(corrupt):fetcher(url),true,()=>read,()=>{});
  assert.equal(response.status,503);assert(!(await response.text()).includes('do-not-release'));
 }
 const sibling=makeNode('SIBLING','SYNTHETIC-PARENT');
 assert.throws(()=>scopedHierarchyPage({...ancestorPage,items:[sibling]},root,parent.canonical_id,0,25));
 let reads=0;
 const policyRevoked=await factualGateway(permittedRequest(),path,fetcher,true,()=>++reads===1?read:{...read,permissions:{}},()=>{});
 assert.equal(policyRevoked.status,403);assert(!(await policyRevoked.text()).includes('SYNTHETIC'));
 const membershipDenied=await factualGateway(permittedRequest(root,'?node_ref='+foreign),path,async url=>new URL(url).pathname.endsWith('/hierarchy')?Response.json({detail:'not found'},{status:404}):fetcher(url),true,()=>read,()=>{});
 assert.equal(membershipDenied.status,403);
 // Python and Node retain old three-capability grants and reject broad hierarchy grants.
 const {createHash}=await import('node:crypto');
 const canonical=v=>Array.isArray(v)?'['+v.map(canonical).join(',')+']':v!==null&&typeof v==='object'?'{'+Object.keys(v).sort().map(k=>JSON.stringify(k)+':'+canonical(v[k])).join(',')+'}':JSON.stringify(v);
 const now=Date.now(),stamp=n=>new Date(n).toISOString().replace(/\.\d{3}Z$/,'Z');
 const unsigned={action:'ISSUE',version:1,previous_sha256:'0'.repeat(64),grant_id:'synthetic-hierarchy',subject:narrow.subject,assets:[root],capabilities:caps,not_before:stamp(now-1000),expires_at:stamp(now+3600000),actor:'local:c759c2d1-19a4-4291-9b66-9218dbd12dea',approval_ref:'synthetic',operator_ref:'synthetic',at:stamp(now)};
 const ledger=fields=>{const e={...unsigned,...fields};e.sha256=createHash('sha256').update(canonical(e)).digest('hex');return '{"schema_version":1}\n'+canonical(e)+'\n';};
 assert.deepEqual(parseFactualRead(ledger({}),narrow.subject).permissions[root],caps);
 assert.throws(()=>parseFactualRead(ledger({scope_kind:'REGISTERED_BSR_IP',assets:[]}),narrow.subject));
 assert.throws(()=>parseFactualRead(ledger({capabilities:['FACTUAL_HIERARCHY_READ']}),narrow.subject));
 const script='import sys,importlib.util; s=importlib.util.spec_from_file_location("p", "src/services/factual_read_entitlements.py");m=importlib.util.module_from_spec(s);s.loader.exec_module(m);e=m.decode(sys.stdin.buffer.read());assert "FACTUAL_HIERARCHY_READ" in e[0]["capabilities"];print("PASS")';
 assert.equal(execFileSync('python3',['-c',script],{cwd:'..',input:ledger({}),encoding:'utf8',env:{PATH:process.env.PATH,PYTHONDONTWRITEBYTECODE:'1'}}).trim(),'PASS');
 assert.deepEqual(narrow.asset_ids,[root]);assert.deepEqual(narrow.roles,['AUTHOR']);
 console.log('Exact-root hierarchy READ, ancestor branch DTO, off-root denial, UNKNOWN, ledger parity and revocation PASS');
 console.log('Hierarchy gateway scope, Registry-before-read, paging and revocation checks PASS');
}finally{rmSync(dir,{recursive:true,force:true});}
