// Sprint scope guard: unchanged pages/boundaries plus six exact reviewed runtime-parity exceptions.
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { createHash } from 'node:crypto';
const root = execFileSync('git', ['rev-parse', '--show-toplevel'], { encoding: 'utf8' }).trim();
const base = '2437fdb3b12f8ab63d56236dbb532caa7e39b671';
const git = (...args) => execFileSync('git', ['-C', root, ...args], { encoding: 'utf8' });
const pages = git('ls-tree', '-r', '--name-only', base, 'reliability-cockpit/web/app').trim().split('\n').filter(p => p.endsWith('/page.tsx'));
assert.equal(pages.length, 28, 'baseline application page inventory changed');
// Sprint3 authorizes two exact reviewed Asset presentation entries; all other pages stay pinned.
const reviewedSprint3Pages = {
  "reliability-cockpit/web/app/(workspace)/assets/page.tsx": "787bbdee909841de5157fe80809dcdd4ce333a24af7f8d85738cbed40b325570",
  "reliability-cockpit/web/app/(workspace)/assets/[...canonicalId]/page.tsx": "2d8e040fa7a753fdf443cae0aa40fa8b00d28aa8a7d2a842d428addacf8c0df6"
};
for (const page of pages) {if(Object.hasOwn(reviewedSprint3Pages,page))assert.equal(createHash('sha256').update(readFileSync(resolve(root,page))).digest('hex'),reviewedSprint3Pages[page],page);else assert.equal(readFileSync(resolve(root,page),'utf8'),git('show',`${base}:${page}`),`${page} changed`);}
const protectedPaths = ['reliability-cockpit/src', 'reliability-cockpit/migrations', 'reliability-cockpit/application-migrations', 'reliability-data-contracts', 'reliability-cockpit/contracts', 'maximo-collector', 'pi-collector', 'cems-collector', 'deploy/development', 'reliability-cockpit/web/middleware.ts', 'reliability-cockpit/web/app/api', ...['pdm-input.ts', 'pdm-capture.ts', 'product-records.ts', 'engineering-http.ts'].map(p => `reliability-cockpit/web/lib/${p}`), ...['PdmDraftContext.tsx', 'useQaRecords.ts', 'usePdmCommand.ts'].map(p => `reliability-cockpit/web/components/${p}`)];
const reviewedParity = {
  "reliability-cockpit/src/services/local_authentication.py": "cac45c151340fe3c5074d29bfbc1e6f3d8c77b98c5efa3369e5e3975c8fb542c",
  "reliability-cockpit/src/services/local_demo_accounts.py": "0fc519222fdc6c390f7f98d22c53cac7be5895c93ed0b5ec2bd08b90771ef10c",
  "reliability-cockpit/src/services/pdm_source_history.py": "2c164f070a5ae71c31ec513aff187b61183e5636a1807db9dc1e6ffbb8e2c478",
  "reliability-cockpit/src/services/pdm_source_interpretation.py": "a533d9b159397891b3b7353ec0ff699d3bb0f8f9acb675069df41d00052931e3",
  "reliability-cockpit/src/qa/users.py": "1b4075ffd90185332bccc33ab5b0e1f1596a97d0ade9b5a230983785fa406262",
  "deploy/development/local_fixture.py": "882155448dde67db32bdacda4fe22c3f39df64c8ad5496c598f680e84d329138"
};
// Sprint2 explicitly authorizes only this compatible bounded read change.
// Exact bytes remain pinned; DTO/schema/auth/source and the six F23/F24 pins stay protected.
const reviewedSprint2 = {
  "reliability-cockpit/src/services/human_records.py": "35e6ec70f1d3862da21db99b5606d702a1f5dd82a4e626dd584875c1d8dc0000",
  "reliability-cockpit/src/services/pdm_read_budget.py": "cc9bfd952d81f0c6c29de8d4f9eadd103a15138b9b85844447a19c31f224aac0",
  "reliability-cockpit/web/components/useQaRecords.ts": "59b015a5ae8fc7a57e352f4b16d3ab4855e10bdc8db629c2429ae4c45cba039c"
};
// Additive offline contracts and one synthetic collector regression only; operational files remain protected.
const reviewedSprint3 = {
  "reliability-cockpit/contracts/sprint3/catalog/evidence_readiness.py": "70285f9305e3cd856f65a35972885fff47d029130ecfc675c88b12ca3201c2e9",
  "reliability-cockpit/contracts/sprint3/schemas/asset-crosswalk-decision.schema.json": "791cca00323506d69a871e58c2bca4b22bd07de6a8abd7850272b0aec36b4cdc",
  "reliability-cockpit/contracts/sprint3/schemas/reliability-kpi-readiness.schema.json": "1965706b2eb7518b1265b687e46ae4eab92719a3a36af322295e9048f669ede6",
  "reliability-cockpit/contracts/sprint3/examples/sprint3-crosswalk.synthetic.json": "0f130b589bdd0a927405255c00eec71708bcc4e18ca2269dd3392a8fb506389a",
  "reliability-cockpit/contracts/sprint3/examples/sprint3-kpi-readiness.synthetic.json": "0578fe1bcee00c1c762eb760782b8692d931df66e3122f86d8d89afb6927a68e",
  "reliability-cockpit/contracts/sprint3/tests/test_sprint3_evidence.py": "a63a91083e3839a51e35b3ff308e15dfe0041c5471fc61bb171e08163c1df221"
};
const admitted={...reviewedParity,...reviewedSprint2,...reviewedSprint3};
const changed=[...git('diff','--name-only',base,'--',...protectedPaths).trim().split('\n'),...git('ls-files','--others','--exclude-standard','--',...protectedPaths).trim().split('\n')].filter(Boolean);
for(const path of changed){
 assert.ok(Object.hasOwn(admitted,path),`Unreviewed protected boundary: ${path}`);
 assert.equal(createHash('sha256').update(readFileSync(resolve(root,path))).digest('hex'),admitted[path],`Reviewed bytes changed: ${path}`);
}
for(const [path,hash] of Object.entries(admitted))assert.equal(createHash('sha256').update(readFileSync(resolve(root,path))).digest('hex'),hash,`Missing/changed reviewed file: ${path}`);
console.log(`PASS: ${pages.length} preserved page entries (two exact Sprint3 presentation exceptions); six F23/F24 and three Sprint2 read pins; additive offline Sprint3 contracts/tests; auth/source/runtime unchanged`);
