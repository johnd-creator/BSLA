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
for (const page of pages) assert.equal(readFileSync(resolve(root, page), 'utf8'), git('show', `${base}:${page}`), `${page} changed`);
const protectedPaths = ['reliability-cockpit/src', 'reliability-cockpit/migrations', 'reliability-cockpit/application-migrations', 'reliability-data-contracts', 'maximo-collector', 'pi-collector', 'cems-collector', 'deploy/development', 'reliability-cockpit/web/middleware.ts', 'reliability-cockpit/web/app/api', ...['pdm-input.ts', 'pdm-capture.ts', 'product-records.ts', 'engineering-http.ts'].map(p => `reliability-cockpit/web/lib/${p}`), ...['PdmDraftContext.tsx', 'useQaRecords.ts', 'usePdmCommand.ts'].map(p => `reliability-cockpit/web/components/${p}`)];
const reviewedParity = {
  "reliability-cockpit/src/services/local_authentication.py": "cac45c151340fe3c5074d29bfbc1e6f3d8c77b98c5efa3369e5e3975c8fb542c",
  "reliability-cockpit/src/services/local_demo_accounts.py": "0fc519222fdc6c390f7f98d22c53cac7be5895c93ed0b5ec2bd08b90771ef10c",
  "reliability-cockpit/src/services/pdm_source_history.py": "2c164f070a5ae71c31ec513aff187b61183e5636a1807db9dc1e6ffbb8e2c478",
  "reliability-cockpit/src/services/pdm_source_interpretation.py": "a533d9b159397891b3b7353ec0ff699d3bb0f8f9acb675069df41d00052931e3",
  "reliability-cockpit/src/qa/users.py": "1b4075ffd90185332bccc33ab5b0e1f1596a97d0ade9b5a230983785fa406262",
  "deploy/development/local_fixture.py": "882155448dde67db32bdacda4fe22c3f39df64c8ad5496c598f680e84d329138"
};
for (const path of git('diff', '--name-only', base, '--', ...protectedPaths).trim().split('\n').filter(Boolean)) {
 assert.ok(Object.hasOwn(reviewedParity, path), `Unreviewed protected boundary: ${path}`);
 assert.equal(createHash('sha256').update(readFileSync(resolve(root,path))).digest('hex'),reviewedParity[path], `Reviewed parity bytes changed: ${path}`);
}
for (const [path,hash] of Object.entries(reviewedParity)) assert.equal(createHash('sha256').update(readFileSync(resolve(root,path))).digest('hex'),hash, `Missing/changed parity file: ${path}`);
console.log(`PASS: all ${pages.length} page entries byte-identical; only exact reviewed F23/F24 parity is admitted; remaining protected boundaries unchanged`);
