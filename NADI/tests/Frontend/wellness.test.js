import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import postcss from 'postcss';
const view = readFileSync('resources/views/wellness/index.blade.php', 'utf8');
const css = postcss.parse(readFileSync('resources/css/wellness.css', 'utf8'));
test('wellness draft is neutral and priority precedes any aggregate result', () => {
    for (const text of ['Bobot ilustratif', 'Belum cukup data', 'Confidence penilaian', 'Criticality aset', 'Perlu perhatian segera', 'Versi metode dan batas laporan', 'Data kosong bukan 100']) assert.ok(view.includes(text), text);
    assert.ok(view.indexOf('Perlu perhatian segera') < view.indexOf('SKOR WELLNESS'));
    assert.ok(!view.includes('type="range"'));
});
test('wellness has a no-JavaScript GET form and exact source links', () => {
    assert.ok(view.includes('method="get"'));
    for (const route of ['pdm.show', 'inspections.show', 'reliability.reviews', 'priorities.show']) assert.ok(view.includes(route));
});
test('wellness cards stack and allow long canonical identities to wrap', () => {
    const mobile = css.nodes.find(n => n.type === 'atrule' && n.params === '(max-width: 800px)');
    assert.ok(mobile.nodes.some(n => n.selector?.includes('.wellness-components') && n.nodes.some(d => d.prop === 'grid-template-columns' && d.value === 'minmax(0, 1fr)')));
    assert.ok(mobile.nodes.some(n => n.selector?.includes('.panel.wellness-summary')));
    assert.ok(css.nodes.some(n => n.selector === '.wellness-component' && n.nodes.some(d => d.prop === 'overflow-wrap' && d.value === 'anywhere')));
});

const policy = readFileSync('resources/views/wellness/policy.blade.php', 'utf8');
const summary = readFileSync('resources/views/wellness/policy-summary.blade.php', 'utf8');
test('wellness proposal form preserves unknowns, revision basis, and native navigation', () => {
    for (const text of ['method="post"', '@csrf', 'previous_revision', 'request_key', 'anchor_fingerprints', 'acknowledge_draft', 'Simpan revisi draft', 'Batal', 'Riwayat revisi draft']) assert.ok(policy.includes(text), text);
    assert.ok(policy.includes('write-wellness-policies'));
    assert.ok(!policy.includes('type="range"'));
    for (const text of ['Belum dinilai engineer', 'Di luar usulan rentang', 'bukan kategori sehat atau alarm', 'Acuan pengaturan berubah']) assert.ok(summary.includes(text), text);
});
