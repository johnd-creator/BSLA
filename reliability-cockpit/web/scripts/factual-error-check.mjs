import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {mkdtempSync,rmSync,readFileSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url),dir=mkdtempSync(join(tmpdir(),'nadi-factual-error-'));
try {
 execFileSync(process.execPath,['node_modules/typescript/bin/tsc','lib/factual-error.ts','lib/factual-gateway.ts','--outDir',dir,'--module','commonjs','--target','ES2022','--skipLibCheck'],{stdio:'pipe'});
 const {factualErrorMessage:message,factualErrorKind:kind}=require(join(dir,'factual-error.js')),{ApiError}=require(join(dir,'api.js')),{factualAccess}=require(join(dir,'factual-gateway.js')),{LOCAL_PORTFOLIO_READ}=require(join(dir,'factual-policy.js'));
 const path=['v1','reliability','decision-overview'],q=new URLSearchParams('window_days=30');
 assert.equal(factualAccess(path,q,{subject:LOCAL_PORTFOLIO_READ.subject,roles:['ADMIN'],asset_ids:[]}),null);
 assert.equal(factualAccess(path,q,{subject:'local:engineer',roles:['AUTHOR'],asset_ids:['NADI-ASSET-001']}),'FACTUAL_SCOPE_GRANT_REQUIRED');
 assert.equal(kind(new ApiError('SECRET',403)),'access');assert.equal(kind(new ApiError('SECRET',401)),'session');assert.equal(kind(new ApiError('SECRET',400)),'request');
 for(const reason of [new ApiError('SECRET',500),new TypeError('403 is just text'),'401',null])assert.equal(kind(reason),'service');
 assert.doesNotMatch(message(new ApiError('SECRET',400)),/belum tersedia|Coba lagi|SECRET/);
 assert.match(message(new ApiError('DO_NOT_EXPOSE_INTERNAL_SECRET',403)),/capability atau scope/);
 assert.doesNotMatch(message(new ApiError('SECRET',403)),/Layanan.*belum tersedia|SECRET/);
 assert.match(message(new ApiError('SECRET',401)),/Sesi berakhir/);
 for(const reason of [new ApiError('SECRET',503),new ApiError('SECRET',500),new TypeError('SECRET'),null]){assert.match(message(reason),/Layanan data faktual belum tersedia/);assert.doesNotMatch(message(reason),/SECRET|capability/);}
 assert.match(readFileSync('components/ExecutiveOverview.tsx','utf8'),/setError\(factualErrorMessage\(reason\)\)/);
 console.log('PASS operator policy, engineer403, session401, upstream503/500, network failure, no secret leakage, Overview wiring');
}finally{rmSync(dir,{recursive:true,force:true});}
