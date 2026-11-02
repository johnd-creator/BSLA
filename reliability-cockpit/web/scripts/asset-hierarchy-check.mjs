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
 console.log('Hierarchy gateway scope, Registry-before-read, paging and revocation checks PASS');
}finally{rmSync(dir,{recursive:true,force:true});}
