// Owner-private gallery only; CI publishes non-image receipt, never these PNG/HTML bytes.
import assert from 'node:assert/strict';
import {readFileSync,writeFileSync,chmodSync} from 'node:fs';
import {resolve} from 'node:path';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
const out=resolve(process.env.NADI_SPRINT5_OUTPUT??'/tmp/nadi-sprint05/browser');
const receipt=JSON.parse(readFileSync(resolve(out,'results.json')));
assert.equal(receipt.status,'PASS');assert.equal(receipt.classification,'SYNTHETIC_ONLY_PRIVATE');
const head=execFileSync('git',['rev-parse','HEAD'],{encoding:'utf8'}).trim();assert.equal(receipt.source_head,head);
const escape=s=>String(s).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
const hashes=[],cards=[];
for(const s of receipt.screens){assert(/^[\w-]+\.png$/.test(s.file));const digest=createHash('sha256').update(readFileSync(resolve(out,s.file))).digest('hex');hashes.push(digest+'  '+s.file);cards.push(`<article><h2>${escape(s.purpose)}</h2><p>SYNTHETIC ONLY · ${head} · ${s.viewport.width}×${s.viewport.height} · ${escape(s.theme)}</p><code>${escape(s.path)}</code><p>Factual data: none. Empty/error and semantic limitations: see NADI-SPRINT5-PRIVATE-REVIEW-PACKAGE.md and UAT checklist. Human acceptance: PENDING.</p><a href="${s.file}"><img loading="lazy" src="${s.file}" alt="${escape(s.purpose)} — SYNTHETIC ONLY"></a><p>SHA256: ${digest}</p></article>`);}
writeFileSync(resolve(out,'SHA256SUMS'),hashes.join('\n')+'\n');
writeFileSync(resolve(out,'index.html'),`<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Private Sprint5 synthetic review</title><style>body{font:16px system-ui;max-width:1200px;margin:32px auto;padding:20px;color:#172b3a;background:#f4f7fa}article{margin:40px 0;padding:24px;background:white;border:1px solid #bbc8d2}img{max-width:100%;height:auto}code,p{overflow-wrap:anywhere}</style><h1>Sprint5 · PRIVATE · SYNTHETIC ONLY</h1><p>Exact candidate ${head}; dirty source at capture: ${receipt.source_dirty}. Not localhost or plant data, not PO or engineer acceptance. Operational KPI: NOT_ELIGIBLE.</p>${cards.join('\n')}</html>`);
chmodSync(out,0o700);for(const f of ['index.html','SHA256SUMS','results.json'])chmodSync(resolve(out,f),0o600);
console.log('Private gallery generated: '+receipt.screens.length+' images, exact '+head);
