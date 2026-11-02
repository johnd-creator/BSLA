import {hasPortfolioRead,portfolioRoutes} from './factual-policy';
import {readBounded} from './bounded-http';
import {localGuardEnabled,verifyLocalSession,PRIVATE_HEADERS,type LocalSession} from './local-session';
import {EMPTY_FACTUAL_READ,canonicalBsrAsset,factualAssets,registeredRead,readFactualRead,sameFactualRead,recordFactualRead,type FactualReadSnapshot,type FactualPolicyReader,type FactualReadAuditor} from './factual-read-policy';
import {scopedAsset,scopedMaintenancePage,scopedOverview,scopedRegister} from './factual-scoped-reader';
const assetSuffixes=new Set(['','context','condition-evidence','integration-status','timeline','fmea','health-assessments','health/latest']);
const collections=new Set(['maintenance-events','fmea','asset-health','overhauls']);
const queryKeys=new Set(['offset','limit','sort','asset_ref','asset_number','status','unit','asset_type','site_code','organization_code','lifecycle_status','source_number','source_failure_code','updated_from','updated_to','created_from','created_to','category','description','workorder_ref','source_work_order_number','planned_from','planned_to','actual_from','actual_to','window_days','min_events','work_order_id','event_type','date_from','date_to','node_ref']);
export function factualAccess(path:string[],params:URLSearchParams,session:LocalSession,read:FactualReadSnapshot=EMPTY_FACTUAL_READ):string|null {
 if(path.some(s=>!s||s==='.'||s==='..'||/[\\/\u0000-\u0020\u007f%]/.test(s)))return 'PATH_DENIED';
 for(const [key,value] of params){
  if(!queryKeys.has(key)||params.getAll(key).length!==1||value.length>200||/[\u0000-\u001f\u007f]/.test(value))return 'QUERY_DENIED';
  if(key==='limit'&&(!/^\d+$/.test(value)||+value<1||+value>200))return 'QUERY_DENIED';
  if(key==='offset'&&(!/^\d+$/.test(value)||+value>1000000))return 'QUERY_DENIED';
 }
 if(params.has('node_ref')&&!(path.length===5&&path[2]==='assets'&&path[4]==='hierarchy'))return 'QUERY_DENIED';
 if((params.has('site_code')&&params.get('site_code')!=='BSR')||(params.has('organization_code')&&params.get('organization_code')!=='IP'))return 'PORTFOLIO_SCOPE_DENIED';
 if(path.join('/')==='health'&&params.size===0)return null;
 if(path[0]!=='v1'||path[1]!=='reliability')return 'FACTUAL_SCOPE_GRANT_REQUIRED';
 if(!hasPortfolioRead(session)){
  const assets=factualAssets(read,['FACTUAL_ASSET_READ']);
  const registered=registeredRead(read,['FACTUAL_ASSET_READ']);
  if(path.join('/')==='v1/reliability/scoped-overview')return params.size===0&&(registeredRead(read,['FACTUAL_DASHBOARD_READ','FACTUAL_ASSET_READ','FACTUAL_MAINTENANCE_READ'])||factualAssets(read,['FACTUAL_DASHBOARD_READ','FACTUAL_ASSET_READ','FACTUAL_MAINTENANCE_READ']).length)?null:'FACTUAL_SCOPE_GRANT_REQUIRED';
  if(path.join('/')==='v1/reliability/assets'&&(assets.length||registered)){
   for(const key of params.keys())if(!['offset','limit','sort','status','unit','asset_type','site_code','organization_code'].includes(key))return 'QUERY_DENIED';
   if(params.has('sort')&&!['updated_desc','updated_asc','status'].includes(params.get('sort')!))return 'QUERY_DENIED';
   return null;
  }
  if(path.length===4&&path[2]==='assets'&&(assets.includes(path[3])||registered&&canonicalBsrAsset(path[3])))return params.size===0?null:'QUERY_DENIED';
  if(path.length===3&&path[2]==='maintenance-events'&&(factualAssets(read,['FACTUAL_ASSET_READ','FACTUAL_MAINTENANCE_READ']).includes(params.get('asset_ref')??'')||registeredRead(read,['FACTUAL_ASSET_READ','FACTUAL_MAINTENANCE_READ'])&&canonicalBsrAsset(params.get('asset_ref')??''))){
   for(const key of params.keys())if(!['asset_ref','offset','limit','sort','work_order_id','status','event_type','date_from','date_to','node_ref','site_code','organization_code'].includes(key))return 'QUERY_DENIED';
   return null;
  }
 }
 if(path.length===5&&path[2]==='assets'&&path[4]==='hierarchy'){
  if(!hasPortfolioRead(session))return 'PORTFOLIO_SCOPE_DENIED';
  const canonical=/^asset:MAXIMO:MXASSET:BSR:IP:[A-Za-z0-9_.-]{1,120}$/;
  if(!canonical.test(path[3]))return 'ASSET_SCOPE_DENIED';
  for(const key of params.keys())if(!['node_ref','offset','limit'].includes(key))return 'QUERY_DENIED';
  if(params.has('node_ref')&&!canonical.test(params.get('node_ref')!))return 'QUERY_DENIED';
  if(params.has('limit')&&+params.get('limit')!>50||params.has('offset')&&+params.get('offset')!>10000)return 'QUERY_DENIED';
  return null;
 }
 if(path[2]==='assets'&&path.length>=4&&assetSuffixes.has(path.slice(4).join('/'))){
  if(params.has('asset_ref')&&params.get('asset_ref')!==path[3])return 'ASSET_SCOPE_DENIED';
  // Context/integration DTOs also contain portfolio totals: exact asset grant alone is insufficient.
  if(!hasPortfolioRead(session)&&['context','integration-status'].includes(path.slice(4).join('/')))return 'PORTFOLIO_SCOPE_DENIED';
  return hasPortfolioRead(session)||session.asset_ids.includes(path[3])?null:'ASSET_SCOPE_DENIED';
 }
 if(hasPortfolioRead(session)&&portfolioRoutes.has(path.slice(2).join('/')))return null;
 if(path.length===3&&collections.has(path[2])){
  const asset=params.get('asset_ref');return asset&&session.asset_ids.includes(asset)?null:'ASSET_SCOPE_DENIED';
 }
 // No blanket ADMIN permission, guessed relationship, legacy population or export capability.
 return 'FACTUAL_SCOPE_GRANT_REQUIRED';
}
function denied(code:string,status:number){return Response.json({detail:{code}},{status,headers:PRIVATE_HEADERS});}
export async function factualGateway(request:Request,path:string[],requestFetch:typeof fetch=fetch,enabled=localGuardEnabled(),policyReader:FactualPolicyReader=readFactualRead,auditRead:FactualReadAuditor=recordFactualRead):Promise<Response>{
 if(!enabled)return denied('LOCAL_AUTH_NOT_ENABLED',503);
 const who=await verifyLocalSession(request.headers,requestFetch);
 if(who.state!=='authenticated')return denied(who.state==='anonymous'?'AUTHENTICATION_REQUIRED':'SESSION_AUTHORITY_UNAVAILABLE',who.state==='anonymous'?401:503);
 if(request.method!=='GET')return denied('READ_ONLY_GATEWAY',405);
 const url=new URL(request.url),legacyCode=factualAccess(path,url.searchParams,who.session);
 const usesReadPolicy=legacyCode!==null&&!hasPortfolioRead(who.session);
 let read:FactualReadSnapshot;
 try{read=usesReadPolicy?policyReader(who.session.subject):EMPTY_FACTUAL_READ;}catch{return denied('FACTUAL_READ_POLICY_UNAVAILABLE',503);}
 const code=factualAccess(path,url.searchParams,who.session,read);
 if(code)return denied(code,403);
 // No client-chosen destination, credentials, cookies or authorization headers upstream.
 const target=new URL('/'+path.map(encodeURIComponent).join('/'),'http://127.0.0.1:8000');target.search=url.search;
 const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),10000);
 const abort=()=>controller.abort();request.signal.addEventListener('abort',abort,{once:true});
 try{
  if(request.signal.aborted)controller.abort();
  const scoped=!hasPortfolioRead(who.session),route=path.join('/');
  const direct=scoped&&path.length===4&&path[2]==='assets'&&(factualAssets(read,['FACTUAL_ASSET_READ']).includes(path[3])||registeredRead(read,['FACTUAL_ASSET_READ']));
  let bytes:Uint8Array,status=200;
  if(scoped&&route==='v1/reliability/assets')bytes=new TextEncoder().encode(JSON.stringify(await scopedRegister(url.searchParams,read,requestFetch,controller.signal)));
  else if(scoped&&route==='v1/reliability/scoped-overview')bytes=new TextEncoder().encode(JSON.stringify(await scopedOverview(read,requestFetch,controller.signal)));
  else if(direct)bytes=new TextEncoder().encode(JSON.stringify(await scopedAsset(path[3],registeredRead(read,['FACTUAL_ASSET_READ'])?null:factualAssets(read,['FACTUAL_ASSET_READ']),requestFetch,controller.signal)));
  else{
  const assetId=path[0]==='v1'&&path[1]==='reliability'&&path[2]==='assets'&&path.length>=4?path[3]:url.searchParams.get('asset_ref');
  if(assetId){
   // Registry membership + BSR/IP is verified server-side before any asset subresource read.
   const lookup=new URL('/v1/reliability/assets/'+encodeURIComponent(assetId),'http://127.0.0.1:8000');
   const registry=await requestFetch(lookup,{method:'GET',headers:{accept:'application/json'},cache:'no-store',redirect:'error',signal:controller.signal});
   if(registry.status!==200)return denied('ASSET_SCOPE_DENIED',403);
   const asset=JSON.parse(new TextDecoder().decode(await readBounded(registry.body,256*1024,controller.signal)));
   if(asset.canonical_id!==assetId||asset.site_code!=='BSR'||asset.organization_code!=='IP')return denied('ASSET_SCOPE_DENIED',403);
  }
  const upstream=await requestFetch(target,{method:'GET',headers:{accept:'application/json'},cache:'no-store',redirect:'error',signal:controller.signal});
  if(upstream.status>=300&&upstream.status<400)return denied('UPSTREAM_REDIRECT_DENIED',502);
  const type=upstream.headers.get('content-type')??'';
  if(!type.toLowerCase().startsWith('application/json'))return denied('UPSTREAM_TYPE_DENIED',502);
  bytes=await readBounded(upstream.body,2*1024*1024,controller.signal);status=upstream.status;
  if(scoped&&usesReadPolicy&&route==='v1/reliability/maintenance-events'&&status===200){
   const page=scopedMaintenancePage(JSON.parse(new TextDecoder().decode(bytes)),url.searchParams.get('asset_ref')!,Number(url.searchParams.get('offset')??0),Number(url.searchParams.get('limit')??50));
   bytes=new TextEncoder().encode(JSON.stringify(page));
  }
  }
  if(bytes.byteLength>2*1024*1024)return denied('SCOPED_RESPONSE_TOO_LARGE',502);
  // Recheck revocation/expiry after upstream read, before releasing protected data.
  const final=await verifyLocalSession(request.headers,requestFetch);
  if(final.state!=='authenticated')return denied(final.state==='anonymous'?'SESSION_INVALID':'SESSION_AUTHORITY_UNAVAILABLE',final.state==='anonymous'?401:503);
  const finalRead=usesReadPolicy?policyReader(final.session.subject):EMPTY_FACTUAL_READ;
  if(final.session.subject!==who.session.subject||!sameFactualRead(read,finalRead)||factualAccess(path,url.searchParams,final.session,finalRead))return denied('ASSET_SCOPE_DENIED',403);
  if(usesReadPolicy){
   auditRead(final.session.subject,finalRead,request.url);
   if(!sameFactualRead(finalRead,policyReader(final.session.subject)))return denied('ASSET_SCOPE_DENIED',403);
  }
  return new Response(bytes as BodyInit,{status,headers:{...PRIVATE_HEADERS,'Content-Type':'application/json'}});
 }catch(error){return error instanceof Error&&error.message==='ASSET_SCOPE_DENIED'?denied('ASSET_SCOPE_DENIED',403):denied('FACTUAL_UPSTREAM_UNAVAILABLE',503);}finally{clearTimeout(timer);request.signal.removeEventListener('abort',abort);}
}
