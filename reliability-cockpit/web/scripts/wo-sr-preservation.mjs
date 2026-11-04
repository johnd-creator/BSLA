// Hash-pinned authorized WO/SR exceptions; historical assertions remain active.
import {reviewedWoDetailHashes} from './wo-detail-preservation.mjs';
import {reviewedFactualReadHashes} from './factual-read-preservation.mjs';
import {reviewedWoReconciliationHashes} from './wo-reconciliation-preservation.mjs';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
const root=execFileSync('git',['rev-parse','--show-toplevel'],{encoding:'utf8'}).trim();
const exceptions={
  "reliability-cockpit/src/api/reliability.py": "4d00b97d3506169aab502a666a78336e799b533626fc6b8f8248c2376fb6468b",
  "reliability-cockpit/web/lib/api.ts": "b4aaf25de56b19e767d63784c47afdeb1afeab584c583d2fd363f7dc94db6b7a",
  "reliability-cockpit/web/lib/asset-evidence.ts": "f7c38766b41ce29d546c5fd318d6644adbc7d97f847a96782c2f38d726ab511b",
  "reliability-cockpit/web/components/AssetMaintenanceEvidence.tsx": "0faa448e9995d085ff2aeaebe571f3187f37841253d8c8336ff8cd8a2f7c2c95"
};
for(const [path,hash] of Object.entries(exceptions))assert.equal(createHash('sha256').update(execFileSync('git',['-C',root,'show','119ba2f1472facedd71433d65b74f3b7d64a6434:'+path])).digest('hex'),hash,'historical classification pin changed: '+path);
for(const [path,hash] of Object.entries(reviewedWoDetailHashes))assert.equal(createHash('sha256').update(execFileSync('git',['-C',root,'show','49ff4d1088a96673f85070bcaa1f293b5810f8f4:'+path])).digest('hex'),hash,'historical WO detail pin changed: '+path);
const current={...exceptions,...reviewedWoDetailHashes,...reviewedFactualReadHashes,...reviewedWoReconciliationHashes(root)};
for(const [path,hash] of Object.entries(current))assert.equal(createHash('sha256').update(readFileSync(root+'/'+path)).digest('hex'),hash,'unreviewed WO detail change: '+path);
export const reviewedClassificationPaths=Object.keys(current);

export const reviewedClassificationHashes=current;
