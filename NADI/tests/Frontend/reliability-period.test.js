import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
const read = path => readFileSync(path, 'utf8');
test('period selection uses native fields and reports distinguish current knowledge from historical events', () => {
    const fields = read('resources/views/reliability/period-fields.blade.php');
    for (const name of ['period', 'start_date', 'end_date', 'year']) assert.ok(fields.includes(`name="${name}"`));
    assert.ok(fields.includes('bulan kalender, bukan 90/180/365 hari'));
    assert.ok(read('resources/views/reliability/report.blade.php').includes('bukan kondisi atau pengetahuan yang sudah diketahui'));
    assert.ok(read('resources/views/wellness/index.blade.php').includes('Usulan metode Wellness tahunan tidak diterapkan otomatis'));
    assert.ok(read('resources/views/reliability/period-hidden.blade.php').includes('fromReport($report)->query()'));
});
test('multi-year trends preserve year-month drilldown and avoid illegible long charts', () => {
    const view = read('resources/views/reliability/trends.blade.php');
    for (const text of ['trend_period_month', 'trace_period_month', "count($trendView['months']) <= 24", 'Gunakan tabel bulanan']) assert.ok(view.includes(text));
    assert.ok(read('resources/views/reliability/calculation.blade.php').includes('id="calculation-exposure"'));
});
