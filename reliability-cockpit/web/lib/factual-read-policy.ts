/** Server only: private application READ ledger, independent from Engineering grants.
 * OS custody is trusted; a hash chain does not detect restoration of a valid prefix.
 * Keep this stable state outside release/data backups, including during rollback.
 */
import * as fs from 'node:fs';
import * as path from 'node:path';
import {createHash} from 'node:crypto';
import {FACTUAL_READ_CAPABILITIES,type FactualReadCapability} from './factual-read-contract';
const ZERO='0'.repeat(64),MAX_BYTES=4*1024*1024,ISSUER='local:c759c2d1-19a4-4291-9b66-9218dbd12dea';
const FIELDS=['action','version','previous_sha256','grant_id','subject','assets','capabilities','not_before','expires_at','actor','approval_ref','operator_ref','at','sha256'].sort();
type Event={action:'ISSUE'|'REVOKE';version:number;previous_sha256:string;grant_id:string;subject:string;assets:string[];scope_kind?:'EXACT_ASSETS'|'REGISTERED_BSR_IP';capabilities:FactualReadCapability[];not_before:string;expires_at:string;actor:string;approval_ref:string;operator_ref:string;at:string;sha256:string};
export type FactualReadSnapshot={head:string;version:number;permissions:Record<string,FactualReadCapability[]>;registered?:FactualReadCapability[]};
export type FactualPolicyReader=(subject:string)=>FactualReadSnapshot;
export type FactualReadAuditor=(subject:string,snapshot:FactualReadSnapshot,requestUrl:string)=>void;
export const EMPTY_FACTUAL_READ:FactualReadSnapshot={head:ZERO,version:0,permissions:{}};
function canonical(value:unknown):string {
 if(Array.isArray(value))return '['+value.map(canonical).join(',')+']';
 if(value!==null&&typeof value==='object')return '{'+Object.entries(value).sort(([a],[b])=>a<b?-1:a>b?1:0).map(([k,v])=>JSON.stringify(k)+':'+canonical(v)).join(',')+'}';
 return JSON.stringify(value);
}
function fail():never{throw new Error('FACTUAL_READ_POLICY_INVALID');}
function time(value:unknown):number{
 if(typeof value!=='string'||!/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$/.test(value))return fail();
 const n=Date.parse(value);if(!Number.isFinite(n)||new Date(n).toISOString().replace('.000Z','Z')!==value)return fail();return n;
}
function strings(value:unknown):value is string[]{return Array.isArray(value)&&value.every(x=>typeof x==='string')&&canonical(value)===canonical([...new Set(value)].sort());}
export function parseFactualRead(data:string,subject:string,now=Date.now()):FactualReadSnapshot {
 if(Buffer.byteLength(data)>MAX_BYTES||!data.endsWith('\n')||/[^\x00-\x7f]/.test(data))return fail();
 const lines=data.slice(0,-1).split('\n');if(lines[0]!=='{"schema_version":1}'||lines.length>401)return fail();
 let previous=ZERO,version=0,issues=0,lastTime=-Infinity;
 const states=new Map<string,Event>();
 for(const line of lines.slice(1)){
  const e:Event=JSON.parse(line);
  if(!e||Array.isArray(e)||![canonical(FIELDS),canonical([...FIELDS,'scope_kind'].sort())].includes(canonical(Object.keys(e).sort()))||canonical(e)!==line)return fail();
  if(!['ISSUE','REVOKE'].includes(e.action)||!Number.isSafeInteger(e.version)||e.version!==version+1||e.previous_sha256!==previous||!/^[a-f0-9]{64}$/.test(e.sha256))return fail();
  for(const key of ['subject','actor'] as const)if(typeof e[key]!=='string'||!/^local:[A-Za-z0-9-]{1,150}$/.test(e[key]))return fail();
  if(e.actor!==ISSUER||e.subject===e.actor)return fail();
  for(const key of ['grant_id','approval_ref','operator_ref'] as const)if(typeof e[key]!=='string'||! /^[A-Za-z0-9_.:-]{1,160}$/.test(e[key]))return fail();
  if(Object.hasOwn(e,'scope_kind')&&!['EXACT_ASSETS','REGISTERED_BSR_IP'].includes(e.scope_kind!))return fail();
  const scope=e.scope_kind??'EXACT_ASSETS';
  if(!['EXACT_ASSETS','REGISTERED_BSR_IP'].includes(scope)||!strings(e.assets)||(scope==='REGISTERED_BSR_IP'?e.assets.length!==0:e.assets.length<1||e.assets.length>20)||e.assets.some(a=>!/^asset:MAXIMO:MXASSET:BSR:IP:[A-Za-z0-9_.-]{1,120}$/.test(a)))return fail();
  if(!strings(e.capabilities)||!e.capabilities.length||e.capabilities.some(c=>!(FACTUAL_READ_CAPABILITIES as readonly string[]).includes(c)))return fail();
  if(e.capabilities.includes('FACTUAL_HIERARCHY_READ')&&(scope!=='EXACT_ASSETS'||!e.capabilities.includes('FACTUAL_ASSET_READ')))return fail();
  const start=time(e.not_before),end=time(e.expires_at),at=time(e.at);
  if(end<=start||end-start>86400000||at<lastTime||at>now+5000||e.action==='ISSUE'&&(at<start||at-start>3600000))return fail();
  const unsigned=Object.fromEntries(Object.entries(e).filter(([k])=>k!=='sha256'));
  if(createHash('sha256').update(canonical(unsigned)).digest('hex')!==e.sha256)return fail();
  const old=states.get(e.grant_id);
  if(e.action==='ISSUE'){if(old||++issues>200)return fail();}
  else if(!old||old.action!=='ISSUE'||(e.scope_kind??'EXACT_ASSETS')!==(old.scope_kind??'EXACT_ASSETS')||(['subject','assets','capabilities','not_before','expires_at'] as const).some(k=>canonical(e[k])!==canonical(old[k])))return fail();
  states.set(e.grant_id,e);previous=e.sha256;version=e.version;lastTime=at;
 }
 const permissions:Record<string,FactualReadCapability[]>={};
 const registered=new Set<FactualReadCapability>();
 for(const e of states.values())if(e.action==='ISSUE'&&e.subject===subject&&time(e.not_before)<=now&&now<time(e.expires_at)){
  if(e.scope_kind==='REGISTERED_BSR_IP')for(const cap of e.capabilities)registered.add(cap);
  for(const asset of e.assets)permissions[asset]=[...new Set([...(permissions[asset]??[]),...e.capabilities])].sort();
 }
 if(Object.keys(permissions).length>20)return fail(); // bounded exact lookups, never a portfolio fan-out
 return {head:previous,version,permissions,...(registered.size?{registered:[...registered].sort()}:{})};
}
export function readFactualRead(subject:string):FactualReadSnapshot {
 const name=process.env.NADI_FACTUAL_READ_POLICY_FILE;if(!name)return EMPTY_FACTUAL_READ;
 if(!path.isAbsolute(name)||path.resolve(name)!==name||fs.realpathSync(path.dirname(name))!==path.dirname(name))return fail();
 const parent=fs.lstatSync(path.dirname(name)),uid=process.getuid?.();
 if(!parent.isDirectory()||parent.isSymbolicLink()||parent.uid!==uid||(parent.mode&0o777)!==0o700)return fail();
 const fd=fs.openSync(name,fs.constants.O_RDONLY|fs.constants.O_NOFOLLOW|fs.constants.O_NONBLOCK);
 try{
  const s=fs.fstatSync(fd);if(!s.isFile()||s.uid!==uid||s.nlink!==1||(s.mode&0o777)!==0o600||s.size>MAX_BYTES)return fail();
  const bytes=Buffer.alloc(MAX_BYTES+1);let total=0,n=0;
  do{n=fs.readSync(fd,bytes,total,bytes.length-total,null);total+=n;}while(n&&total<bytes.length);
  if(total>MAX_BYTES)return fail();return parseFactualRead(bytes.subarray(0,total).toString('utf8'),subject);
 }finally{fs.closeSync(fd);}
}
export function factualAssets(snapshot:FactualReadSnapshot,required:FactualReadCapability[]):string[]{
 return Object.keys(snapshot.permissions).filter(id=>required.every(cap=>snapshot.permissions[id].includes(cap))).sort();
}
export function registeredRead(snapshot:FactualReadSnapshot,required:FactualReadCapability[]):boolean{
 return required.every(cap=>(snapshot.registered??[]).includes(cap));
}
export function canonicalBsrAsset(id:string):boolean{return /^asset:MAXIMO:MXASSET:BSR:IP:[A-Za-z0-9_.-]{1,120}$/.test(id);}
export function sameFactualRead(a:FactualReadSnapshot,b:FactualReadSnapshot):boolean{
 return a.head===b.head&&a.version===b.version&&canonical(a.permissions)===canonical(b.permissions)&&canonical(a.registered??[])===canonical(b.registered??[]);
}
export function recordFactualRead(subject:string,snapshot:FactualReadSnapshot,requestUrl:string):void{
 const policy=process.env.NADI_FACTUAL_READ_POLICY_FILE;if(!policy)throw new Error('PRIVATE_FACTUAL_READ_AUDIT_REQUIRED');
 const parent=path.dirname(policy),s=fs.lstatSync(parent),uid=process.getuid?.();
 if(!path.isAbsolute(policy)||path.resolve(policy)!==policy||fs.realpathSync(parent)!==parent||!s.isDirectory()||s.uid!==uid||(s.mode&0o777)!==0o700)throw new Error('PRIVATE_FACTUAL_READ_AUDIT_REQUIRED');
 const fd=fs.openSync(path.join(parent,'reads.ndjson'),fs.constants.O_APPEND|fs.constants.O_CREAT|fs.constants.O_WRONLY|fs.constants.O_NOFOLLOW|fs.constants.O_NONBLOCK,0o600);
 try{
  const file=fs.fstatSync(fd);if(!file.isFile()||file.nlink!==1||file.uid!==uid||(file.mode&0o777)!==0o600||file.size>16*1024*1024)throw new Error('PRIVATE_FACTUAL_READ_AUDIT_REQUIRED');
  // Application security activity only: no cookie, proof, raw URL/query, WO or source body.
  const entry=JSON.stringify({action:'FACTUAL_READ',outcome:'AUTHORIZED_RELEASE_CHECK',at:new Date().toISOString(),subject,policy_version:snapshot.version,policy_head_sha256:snapshot.head,request_sha256:createHash('sha256').update(requestUrl).digest('hex')})+'\n';
  const data=Buffer.from(entry);if(fs.writeSync(fd,data)!==data.length)throw new Error('PRIVATE_FACTUAL_READ_AUDIT_REQUIRED');fs.fsyncSync(fd);
  const directory=fs.openSync(parent,fs.constants.O_RDONLY|fs.constants.O_DIRECTORY|fs.constants.O_NOFOLLOW);
  try{fs.fsyncSync(directory);}finally{fs.closeSync(directory);}
 }finally{fs.closeSync(fd);}
}
