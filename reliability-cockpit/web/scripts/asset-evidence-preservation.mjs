import {reviewedClassificationPaths} from './wo-sr-preservation.mjs';
// Immutable Sprint3 scope fence. Runtime/source/auth behavior stays at parent3a.
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {readFileSync} from 'node:fs';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url),ts=require('typescript');
const base='3a01e842b5bfca08a5d508b8988dc6deb32c2961';
const root=execFileSync('git',['rev-parse','--show-toplevel'],{encoding:'utf8'}).trim();
const git=(...args)=>execFileSync('git',['-C',root,...args],{encoding:'utf8'});
const paths=['reliability-cockpit/src','reliability-data-contracts','reliability-cockpit/migrations','reliability-cockpit/application-migrations','deploy','maximo-collector/src','pi-collector','cems-collector','reliability-cockpit/web/app/api','reliability-cockpit/web/middleware.ts',...['factual-gateway.ts','factual-policy.ts','local-session.ts','navigation.ts','engineering-http.ts','pdm-input.ts','pdm-capture.ts','product-records.ts','pdm-history.ts'].map(p=>'reliability-cockpit/web/lib/'+p)];
assert.equal(git('diff','--name-only',base,'--',...paths).trim().split('\n').filter(path => path && !reviewedClassificationPaths.includes(path)).join('\n'),'','source/auth/controller/storage/collector contracts changed');
assert.equal(git('ls-files','--others','--exclude-standard','--',...paths).trim(),'','untracked source-boundary file');
const emit=source=>ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022,removeComments:true}}).outputText;
const api='reliability-cockpit/web/lib/api.ts',apiText=readFileSync(root+'/'+api,'utf8');
// Revised task permits exactly this additive scoped GET; every existing emitted API stays pinned.
const scopedRead='  scopedOverview: () => get<import(\'./factual-read-contract\').ScopedFactualOverview>("/v1/reliability/scoped-overview"),\n';
assert.equal(apiText.split(scopedRead).length,2,'exact reviewed scoped READ method required');
assert.equal(emit(apiText.replace(scopedRead,'')),emit(git('show',base+':'+api)),'existing API emitted code changed');
const pages=git('ls-tree','-r','--name-only',base,'reliability-cockpit/web/app').trim().split('\n').filter(x=>x.endsWith('/page.tsx'));
assert.equal(pages.length,28);assert.equal(git('ls-files','--others','--exclude-standard','--','reliability-cockpit/web/app').trim(),'','no parallel app routes');
console.log('Sprint3 preservation PASS: F01–F24 historical pins and exact revised Factual READ exceptions; remaining source/session/collector/schema/navigation unchanged; existing API emitted JS identical plus one reviewed scoped GET;28 routes retained');
