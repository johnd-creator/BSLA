// Immutable Sprint5 preservation boundary; only the reviewed corrupt-response helper changes.
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
const base='988af8d4875758b300e7b563c0a205f143ee184c';
const git=(...a)=>execFileSync('git',a,{encoding:'utf8'}).trim();
const root=git('rev-parse','--show-toplevel');
const protectedPaths=['reliability-cockpit/src','reliability-cockpit/migrations','reliability-cockpit/application-migrations','reliability-cockpit/contracts','reliability-cockpit/web/app','reliability-cockpit/web/components','reliability-cockpit/web/lib','reliability-cockpit/web/fixtures','reliability-cockpit/web/middleware.ts','reliability-data-contracts','maximo-collector','pi-collector','cems-collector','deploy'];
const exception='reliability-cockpit/web/lib/asset-evidence.ts';
const changed=git('-C',root,'diff','--name-only',base,'--',...protectedPaths).split('\n').filter(Boolean);
assert.deepEqual(changed,[exception],'unexpected runtime/auth/store/source/contract mutation');
assert.equal(createHash('sha256').update(readFileSync(root+'/'+exception)).digest('hex'),'b5caf3fc1ca1f12805eacf2b996dd9b219d9ddd6b325a0ef61f99476acbe6018');
assert.equal(git('-C',root,'ls-files','--others','--exclude-standard','--',...protectedPaths),'');
assert.equal(git('-C',root,'merge-base',base,'HEAD'),base);
console.log('Sprint5 preservation PASS: one exact helper exception; backend,28 routes,5 navigation, components, auth, active/proposed contracts, schema, collectors and controller unchanged');
