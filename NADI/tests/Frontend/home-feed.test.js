import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import postcss from 'postcss';
const read = (path) => readFileSync(new URL('../../' + path, import.meta.url), 'utf8');
test('home feed has four sections, explicit filter scope and native safe navigation', () => {
    const view = read('resources/views/home.blade.php');
    for (const title of ['Perlu perhatian', 'Aktivitas terbaru', 'Kandidat untuk ditinjau', 'Kualitas data']) assert.ok(view.includes(title));
    for (const name of ['scope', 'freshness', 'activity_type', 'period']) assert.ok(view.includes('name="' + name + '"'));
    assert.ok(view.includes("@include('overview.metrics')"));
    assert.ok(view.includes('Jenis dan waktu hanya memfilter Aktivitas terbaru'));
    assert.ok(!view.includes('setInterval'));
    assert.ok(!view.includes('{!!'));
});
test('home layout collapses without fixed widths and audit anchors remain visible', () => {
    const css = postcss.parse(read('resources/css/home-feed.css'));
    assert.ok(css.nodes.some(n => n.type === 'atrule' && n.params === '(max-width: 1000px)' && n.toString().includes('grid-column: auto')));
    assert.ok(css.nodes.some(n => n.type === 'atrule' && n.params === '(max-width: 600px)' && n.toString().includes('flex-basis: 100%')));
    assert.ok(css.toString().includes('overflow-wrap: anywhere'));
    assert.ok(css.toString().includes('.workspace-audit:target'));
});
