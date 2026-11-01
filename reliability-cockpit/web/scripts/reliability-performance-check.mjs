import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {readFileSync,readdirSync,mkdtempSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {createHash} from 'node:crypto';
const requireHash=bytes=>createHash('sha256').update(bytes).digest('hex');
import {createRequire} from 'node:module';
const base='3778584a7d4f97b98aae44cea37838a34b61f5d0',root=execFileSync('git',['rev-parse','--show-toplevel'],{encoding:'utf8'}).trim();
const git=(...args)=>execFileSync('git',['-C',root,...args],{encoding:'utf8'});
const protectedPaths=['reliability-cockpit/src','reliability-cockpit/migrations','reliability-cockpit/application-migrations','reliability-data-contracts','maximo-collector','pi-collector','cems-collector','deploy','reliability-cockpit/web/app','reliability-cockpit/web/middleware.ts',...['api.ts','factual-gateway.ts','factual-policy.ts','local-session.ts','navigation.ts','pdm-input.ts','pdm-capture.ts','pdm-history.ts','product-records.ts','engineering-http.ts','reports.ts'].map(p=>'reliability-cockpit/web/lib/'+p)];
const styles='reliability-cockpit/web/app/experience.css';
const changed=git('diff','--name-only',base,'--',...protectedPaths).trim().split('\n').filter(Boolean);assert.deepEqual(changed.filter(p=>p!==styles),[],'retained source/auth/collector/legacy/route boundary changed');
assert.equal(requireHash(readFileSync(root+'/'+styles)), 'e15c51beea07374586acf2b15e7c571bb00c643e74ad368930406bdfbd8440f2');assert.equal(git('ls-files','--others','--exclude-standard','--',...protectedPaths).trim(),'');
function files(dir){return readdirSync(dir,{withFileTypes:true}).flatMap(e=>e.isDirectory()?files(join(dir,e.name)):[join(dir,e.name)]);}
for(const dir of ['app','components','lib'])for(const file of files(dir).filter(f=>/\.(ts|tsx)$/.test(f)))assert(!/ReliabilityCalculationDemonstrator|reliability-performance-result\.synthetic|contracts[./]sprint4/.test(readFileSync(file,'utf8')),file+' imports synthetic calculation into app');
assert.deepEqual([...new Set([...readFileSync('components/ReliabilityPerformance.tsx','utf8').matchAll(/reliabilityApi\.(\w+)/g)].map(m=>m[1]))],['asset']);
const temp=mkdtempSync(join(tmpdir(),'nadi-s4-check-'));try{
 execFileSync(process.execPath,['node_modules/typescript/bin/tsc','lib/reliability-performance.ts','--outDir',temp,'--target','ES2022','--module','commonjs','--skipLibCheck']);
 const m=createRequire(import.meta.url)(join(temp,'reliability-performance.js'));
 assert.equal(m.performanceInput('asset:SYNTHETIC:A','2026-01-01T00:00:00Z','2026-02-01T00:00:00Z'),null);
 for(const [asset,a,b] of [['','',''],['asset:SYNTHETIC:A','2026-01-01','2026-02-01'],['asset:SYNTHETIC:A','2026-02-01T00:00:00Z','2026-01-01T00:00:00Z']])assert(m.performanceInput(asset,a,b));
 const url=new URL(m.performanceHref('asset:SYNTHETIC:A&B','2026-01-01T00:00:00+07:00','2026-02-01T00:00:00+07:00'),'https://fixture.invalid');assert.equal(url.pathname,'/reports');assert.equal(url.searchParams.get('rp_asset'),'asset:SYNTHETIC:A&B');assert.equal(url.searchParams.get('report_view'),'reliability');
 assert(m.prerequisites.some(p=>p.input==='Active repair dan restoration'&&p.status==='MISSING'));
 assert(m.prerequisites.some(p=>p.input==='Functional failure event'&&p.status==='MISSING'));assert(m.prerequisites.some(p=>p.input==='Operating exposure (jam)'&&p.status==='MISSING'));
 console.log('Sprint4 UI/scope PASS: authorized Asset only, safe period/context, no app engine/fixture import, all legacy/source/auth/28routes/5navigation bytes unchanged');
}finally{rmSync(temp,{recursive:true,force:true});}
