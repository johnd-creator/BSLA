import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
const read = path => readFileSync(new URL('../../'+path, import.meta.url),'utf8');
test('reliability keeps KPI null boundaries and sample definitions explicit', () => {
 const view=read('resources/views/reliability/report.blade.php');
 for (const text of ['NOT_READY', 'Standby bukan rusak', 'bukan MTTR resmi', 'Episode utuh masuk tahun onset', 'Coverage observasi', 'Bukti operasi manual']) assert.ok(view.includes(text));
 assert.doesNotMatch(view, /<meter|<progress/);
});
test('review form requires evidence and optimistic versions, without invented timestamps', () => {
 const view=read('resources/views/reliability/review.blade.php');
 for (const text of ['request_key', 'event_version', 'previous_revision', 'attestation', 'timing_evidence', 'active_intervals_text']) assert.ok(view.includes('name="'+text+'"'));
 assert.ok(view.includes('tanggal literal') || view.includes('tidak dibuat menjadi jam 00:00'));
 assert.ok(view.includes("@can('update-asset-disruption', $event)"));
});
test('reliability long IDs and evidence have contained mobile layout', () => {
 const css=read('resources/css/reliability.css');
 assert.match(css,/overflow-wrap: anywhere/);
 assert.match(css,/overflow-x: auto/);
 assert.match(css,/@media \(max-width: 700px\)/);
 assert.match(css,/min-height: 44px/);
});
