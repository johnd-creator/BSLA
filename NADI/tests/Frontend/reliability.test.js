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

test('review queue is server-rendered, scoped and keeps independent pagination', () => {
 const view=read('resources/views/reliability/review-queue.blade.php');
 for(const text of ['method="get"','name="review_state"','name="review_period"','@forelse($reviewQueue as $row)','table-wrap table-scroll','Filter hanya menyaring tabel ini','Reset antrean','Onset fungsi · review','Tanggal observasi saja']) assert.ok(view.includes(text));
 assert.ok(!view.includes('name="review_page"'));
 assert.ok(!view.includes('name="page"'));
 assert.ok(view.includes("route('reliability.snapshots.show', $snapshot)"));
 assert.ok(read('resources/css/reliability.css').includes('grid-template-columns: minmax(0, 1fr)'));
});

test('calculation and charts separate pilot, official authorization and trace populations', () => {
 const card=read('resources/views/reliability/calculation-card.blade.php');
 for(const text of ['PILOT · BELUM RESMI','KPI resmi: belum disahkan','numerator_seconds','denominator_episodes','Telusuri pembilang']) assert.ok(card.includes(text));
 const chart=read('resources/views/reliability/trends.blade.php');
 for(const text of ['role="img"','<title>','method="get"','trend_basis','trend_month','trace_metric','excluded_incomplete','excluded_conflicting_episodes']) assert.ok(chart.includes(text));
 assert.doesNotMatch(chart,/<script|style=/);
 const trace=read('resources/views/reliability/calculation.blade.php');
 for(const text of ['Snapshot lama ini belum menyimpan','exposureRows','traceRows','event_version','review_revision','matched_exposure_segments'])assert.ok(trace.includes(text));
});
