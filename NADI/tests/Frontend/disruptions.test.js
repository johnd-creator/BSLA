import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
const css=readFileSync(new URL('../../resources/css/disruptions.css', import.meta.url),'utf8');
const form=readFileSync(new URL('../../resources/views/disruptions/form.blade.php', import.meta.url),'utf8');
const summary=readFileSync(new URL('../../resources/views/disruptions/summary.blade.php', import.meta.url),'utf8');
test('disruption form groups optional fields with native disclosure and preserves local timezone precision',()=>{
 assert.match(form,/<details class="disruption-options"/);
 assert.match(form,/name="occurred_on"/);assert.match(form,/type="time" step="1" name="occurred_time"/);
 assert.match(form,/name="restored_on"/);assert.match(form,/name="restored_time"/);
 assert.match(form,/name="timezone"/);assert.match(form,/name="correction_reason"[^>]*required/);
 assert.match(form,/name="request_key"/);assert.match(form,/name="version"/);
 assert.match(form,/Berikan|Berkas tidak diunggah/);
});
test('disruption summary is explicit about observation coverage, double counting and unknown health',()=>{
 assert.match(summary,/Belum ada catatan bukan berarti aset sehat/);
 assert.match(summary,/bukan downtime terverifikasi/);
 assert.match(summary,/Satu ID kejadian dihitung sekali/);
 assert.match(summary,/tidak mengikuti filter tabel/);
 assert.doesNotMatch(summary,/<meter|<progress/);
});
test('disruption metrics stack on mobile and long references remain contained',()=>{
 assert.match(css,/\.disruption-metrics\s*\{[^}]*repeat\(4/);
 assert.match(css,/@media \(max-width: 700px\)[\s\S]*repeat\(2/);
 assert.match(css,/\.disruption-table td\s*\{[^}]*overflow-wrap: anywhere/);
 assert.match(css,/\.disruption-prose\s*\{[^}]*white-space: pre-wrap/);
});
