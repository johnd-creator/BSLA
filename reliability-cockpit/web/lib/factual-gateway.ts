import {hasPortfolioRead,portfolioRoutes} from './factual-policy';
import {readBounded} from './bounded-http';
import {localGuardEnabled,verifyLocalSession,PRIVATE_HEADERS,type LocalSession} from './local-session';
const assetSuffixes=new Set(['','context','condition-evidence','integration-status','timeline','fmea','health-assessments','health/latest']);
const collections=new Set(['maintenance-events','fmea','asset-health','overhauls']);
const queryKeys=new Set(['offset','limit','sort','asset_ref','asset_number','status','unit','asset_type','site_code','organization_code','lifecycle_status','source_number','source_failure_code','updated_from','updated_to','created_from','created_to','category','description','workorder_ref','source_work_order_number','planned_from','planned_to','actual_from','actual_to','window_days','min_events','work_order_id','event_type','date_from','date_to','node_ref']);
export function factualAccess(path:string[],params:URLSearchParams,session:LocalSession):string|null {
 if(path.some(s=>!s||s==='.'||s==='..'||/[\\/\u0000-\u0020\u007f%]/.test(s)))return 'PATH_DENIED';
 for(const [key,value] of params){
  if(!queryKeys.has(key)||params.getAll(key).length!==1||value.length>200||/[\u0000-\u001f\u007f]/.test(value))return 'QUERY_DENIED';
  if(key==='limit'&&(!/^\d+$/.test(value)||+value<1||+value>200))return 'QUERY_DENIED';
  if(key==='offset'&&(!/^\d+$/.test(value)||+value>1000000))return 'QUERY_DENIED';
 }
 if((params.has('site_code')&&params.get('site_code')!=='BSR')||(params.has('organization_code')&&params.get('organization_code')!=='IP'))return 'PORTFOLIO_SCOPE_DENIED';
 if(path.join('/')==='health'&&params.size===0)return null;
 if(path[0]!=='v1'||path[1]!=='reliability')return 'FACTUAL_SCOPE_GRANT_REQUIRED';
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
export async function factualGateway(request:Request,path:string[],requestFetch:typeof fetch=fetch,enabled=localGuardEnabled()):Promise<Response>{
 if(!enabled)return denied('LOCAL_AUTH_NOT_ENABLED',503);
 const who=await verifyLocalSession(request.headers,requestFetch);
 if(who.state!=='authenticated')return denied(who.state==='anonymous'?'AUTHENTICATION_REQUIRED':'SESSION_AUTHORITY_UNAVAILABLE',who.state==='anonymous'?401:503);
 if(request.method!=='GET')return denied('READ_ONLY_GATEWAY',405);
 const url=new URL(request.url),code=factualAccess(path,url.searchParams,who.session);
 if(code)return denied(code,403);
 // No client-chosen destination, credentials, cookies or authorization headers upstream.
 const target=new URL('/'+path.map(encodeURIComponent).join('/'),'http://127.0.0.1:8000');target.search=url.search;
 const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),10000);
 const abort=()=>controller.abort();request.signal.addEventListener('abort',abort,{once:true});
 try{
  if(request.signal.aborted)controller.abort();
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
  const bytes=await readBounded(upstream.body,2*1024*1024,controller.signal);
  // Recheck revocation/expiry after upstream read, before releasing protected data.
  const final=await verifyLocalSession(request.headers,requestFetch);
  if(final.state!=='authenticated')return denied(final.state==='anonymous'?'SESSION_INVALID':'SESSION_AUTHORITY_UNAVAILABLE',final.state==='anonymous'?401:503);
  if(final.session.subject!==who.session.subject||factualAccess(path,url.searchParams,final.session))return denied('ASSET_SCOPE_DENIED',403);
  return new Response(bytes,{status:upstream.status,headers:{...PRIVATE_HEADERS,'Content-Type':'application/json'}});
 }catch{return denied('FACTUAL_UPSTREAM_UNAVAILABLE',503);}finally{clearTimeout(timer);request.signal.removeEventListener('abort',abort);}
}
