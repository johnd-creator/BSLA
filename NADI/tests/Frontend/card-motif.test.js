import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
const read = (path) => readFileSync(new URL('../../' + path, import.meta.url), 'utf8');

test('card motifs are local decorative vectors, never focusable data or status', () => {
    const motif = read('resources/views/components/card-motif.blade.php');
    assert.ok(motif.includes('aria-hidden="true" focusable="false"'));
    assert.ok(motif.includes('viewBox="0 0 112 88"'));
    for (const text of ['href=', '<image', '<animate', 'script', 'foreignObject']) assert.ok(!motif.includes(text));
    for (const variant of ['records', 'measurement', 'inspection']) assert.ok(motif.includes(`@case('${variant}')`));
});

test('card art does not allocate space, block clicks or animate', () => {
    const css = read('resources/css/app.css');
    assert.ok(css.includes('pointer-events: none; user-select: none;'));
    assert.ok(css.includes('right: 5px; bottom: 9px; width: 100px; height: 79px;'));
    assert.ok(css.includes('.overview-metric > dd { position: relative; }'));
    assert.ok(css.includes('width: 66px; height: 52px; opacity: .30;'));
});

test('all four summary and work cards retain their original headings and source content', () => {
    const metrics = read('resources/views/overview/metrics.blade.php');
    assert.ok(metrics.includes("$metric['value'] === null ? '—'"));
    assert.ok(metrics.includes("$metric['scope']"));
    assert.ok(metrics.includes("route($metric['route'])"));
    const home = read('resources/views/home.blade.php');
    assert.equal((home.match(/class="card-motif--mark"/g) || []).length, 4);
    assert.ok(home.includes('Tidak ada aktivitas tercatat'));
    assert.ok(home.includes('Bukan konfirmasi kondisi sehat.'));
});
