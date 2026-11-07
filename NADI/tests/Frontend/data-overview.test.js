import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import postcss from 'postcss';

const css = postcss.parse(readFileSync(new URL('../../resources/css/data-overview.css', import.meta.url), 'utf8'));
const rules = css.nodes.filter((node) => node.type === 'rule');
const rule = (selector) => Object.fromEntries(rules.find((node) => node.selector === selector).nodes.filter((node) => node.type === 'decl').map(({ prop, value }) => [prop, value]));

test('overview uses compact cards and responsive columns', () => {
    assert.equal(rule('.overview-metrics')['grid-template-columns'], 'repeat(4, minmax(0, 1fr))');
    assert.equal(rule('.overview-metric').padding, '12px');
    const responsive = css.nodes.filter((node) => node.type === 'atrule');
    assert.ok(responsive.some((node) => node.params === '(max-width: 1100px)' && node.toString().includes('repeat(2, minmax(0, 1fr))')));
    assert.ok(responsive.some((node) => node.params === '(max-width: 700px)' && node.toString().includes('.overview-columns')));
    assert.ok(responsive.some((node) => node.params === '(max-width: 380px)' && node.toString().includes('1fr')));
});

test('overview avoids polling, invented scores, and implicit historical reports', () => {
    const service = readFileSync(new URL('../../app/Services/DataOverview.php', import.meta.url), 'utf8');
    const report = readFileSync(new URL('../../resources/views/overview/reports.blade.php', import.meta.url), 'utf8');
    assert.ok(service.includes('bukan skor kepercayaan'));
    assert.ok(report.includes('bukan laporan tren atau periode historis'));
    assert.ok(report.includes('UNAVAILABLE'));
    assert.ok(!service.includes('Cache::'));
    assert.ok(!report.includes('setInterval'));
});
