// Sprint scope guard: existing page files, public contracts and trusted boundaries stay byte-identical.
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
const root = execFileSync('git', ['rev-parse', '--show-toplevel'], { encoding: 'utf8' }).trim();
const base = '2437fdb3b12f8ab63d56236dbb532caa7e39b671';
const git = (...args) => execFileSync('git', ['-C', root, ...args], { encoding: 'utf8' });
const pages = git('ls-tree', '-r', '--name-only', base, 'reliability-cockpit/web/app').trim().split('\n').filter(p => p.endsWith('/page.tsx'));
assert.equal(pages.length, 28, 'baseline application page inventory changed');
for (const page of pages) assert.equal(readFileSync(resolve(root, page), 'utf8'), git('show', `${base}:${page}`), `${page} changed`);
const protectedPaths = ['reliability-cockpit/src', 'reliability-cockpit/migrations', 'reliability-data-contracts', 'maximo-collector', 'pi-collector', 'cems-collector', 'deploy/development', 'reliability-cockpit/web/middleware.ts', 'reliability-cockpit/web/app/api', ...['pdm-input.ts', 'pdm-capture.ts', 'product-records.ts', 'engineering-http.ts'].map(p => `reliability-cockpit/web/lib/${p}`), ...['PdmDraftContext.tsx', 'useQaRecords.ts', 'usePdmCommand.ts'].map(p => `reliability-cockpit/web/components/${p}`)];
assert.equal(git('diff', '--name-only', base, '--', ...protectedPaths).trim(), '', 'Sprint crossed a protected boundary');
console.log(`PASS: all ${pages.length} page entries byte-identical; backend, DTO, auth, source, controller and draft/command boundaries unchanged`);
