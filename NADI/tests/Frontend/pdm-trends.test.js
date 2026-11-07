import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
const css = readFileSync(new URL('../../resources/css/pdm-trends.css', import.meta.url), 'utf8');
const view = readFileSync(new URL('../../resources/views/pdm/trends.blade.php', import.meta.url), 'utf8');

test('trend chart is responsive, labelled, and backed by an accessible evidence table', () => {
    assert.match(css, /\.pdm-trend-chart svg[^}]*width: 100%/);
    assert.match(css, /@media \(max-width: 700px\)/);
    assert.match(view, /role="img" aria-labelledby="pdm-trend-title pdm-trend-desc"/);
    assert.match(view, /aria-label="Bukti nilai PdM, dapat digeser"/);
    assert.match(view, /<label for="point">/);
    assert.match(view, /<label for="activity">/);
});

test('trend does not interpolate, hide sparse data, or invent alarm thresholds', () => {
    assert.doesNotMatch(view, /<polyline|<path|<script|style=/);
    assert.match(view, /Data belum cukup untuk tren bermakna/);
    assert.match(view, /Banyaknya titik saja tidak membuktikan tren bermakna/);
    assert.match(view, /bukan keterlambatan jadwal/);
    assert.match(view, /Tanggal saja · jam\/zona tidak dicatat/);
    assert.match(view, /OLD\/NEW/);
});


test('mobile axes use unscaled HTML labels and the evidence links have touch targets', () => {
    assert.match(view, /<dl class="pdm-trend-range">/);
    assert.match(view, /<div class="pdm-trend-dates"/);
    assert.doesNotMatch(view, /<text class="pdm-trend-label"/);
    assert.match(css, /\.pdm-trend-range[^}]*font-size: 12px/);
    assert.match(css, /\.pdm-trend-dates[^}]*font-size: 12px/);
    assert.match(css, /\.pdm-trend-evidence-link[^}]*min-height: 44px/);
    assert.match(css, /\.pdm-trend-dot[^}]*vector-effect: non-scaling-stroke/);
    assert.match(view, /Buka detail melalui nomor aktivitas pada tabel bukti/);
});
