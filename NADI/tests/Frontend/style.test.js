import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import postcss from 'postcss';

const stylesheet = postcss.parse(readFileSync(new URL('../../resources/css/app.css', import.meta.url), 'utf8'));
const rules = stylesheet.nodes.filter((node) => node.type === 'rule');
const declarations = (selector) => Object.fromEntries(rules.find((rule) => rule.selector === selector).nodes.filter((node) => node.type === 'decl').map(({ prop, value }) => [prop, value]));
const tokens = declarations(':root');

function luminance(hex) {
    const channels = hex.replace('#', '').match(/../g).map((value) => parseInt(value, 16) / 255);
    const [r, g, b] = channels.map((value) => value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4);
    return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function contrast(first, second) {
    const values = [luminance(first), luminance(second)].sort((a, b) => b - a);
    return (values[0] + 0.05) / (values[1] + 0.05);
}

test('polish retains the approved compact desktop dimensions', () => {
    assert.equal(tokens['--sidebar-width'], '208px');
    assert.equal(declarations('.content').padding, '16px');
    assert.equal(declarations('td').padding, '8px 12px');
    assert.equal(declarations('table')['font-size'], '13px');
    assert.equal(declarations('th')['font-size'], '12px');
    assert.equal(declarations('.topbar')['min-height'], '52px');
});

test('core text, navigation, and primary action colors meet normal text contrast', () => {
    for (const [name, foreground, background] of [
        ['body', tokens['--text'], tokens['--canvas']],
        ['secondary text', tokens['--muted'], tokens['--surface']],
        ['sidebar', tokens['--nav-text'], tokens['--ink']],
        ['active navigation', '#c7f0ef', '#22434e'],
        ['primary button', '#ffffff', tokens['--accent']],
        ['table links', tokens['--link'], tokens['--surface']],
    ]) {
        assert.ok(contrast(foreground, background) >= 4.5, `${name} must retain at least 4.5:1 contrast`);
    }
});

test('reduced motion overrides both transition and animation timing', () => {
    const reduced = stylesheet.nodes.find((node) => node.type === 'atrule' && node.params === '(prefers-reduced-motion: reduce)');
    const rule = reduced.nodes[0];
    for (const prop of ['transition-duration', 'animation-duration']) {
        const declaration = rule.nodes.find((node) => node.prop === prop);
        assert.equal(declaration.value, '0.01ms');
        assert.equal(declaration.important, true);
    }
});

test('mobile logout stays a reachable topbar control with a touch-sized target', () => {
    const mobile = stylesheet.nodes.find((node) => node.type === 'atrule' && node.params === '(max-width: 700px)');
    const logout = mobile.nodes.find((node) => node.selector === '.logout');
    assert.equal(logout.nodes.find((node) => node.prop === 'min-height').value, '40px');
    assert.equal(declarations('.topbar').position, 'sticky');
    assert.equal(declarations('.topbar').top, '0');
});

test('asset summary is compact, four columns on desktop and two on narrow screens', () => {
    assert.equal(declarations('.asset-summary-grid')['grid-template-columns'], 'repeat(4, minmax(0, 1fr))');
    assert.equal(declarations('.asset-summary-card').padding, '12px');
    const compact = stylesheet.nodes.find((node) => node.type === 'atrule' && node.params === '(max-width: 1100px)');
    const grid = compact.nodes.find((node) => node.selector.includes('.asset-summary-grid'));
    assert.equal(grid.nodes.find((node) => node.prop === 'grid-template-columns').value, 'repeat(2, minmax(0, 1fr))');
});


test('WO review summary stays compact and wraps to two columns on narrow screens', () => {
    assert.equal(declarations('.history-review-summary')['grid-template-columns'], 'repeat(4, minmax(0, 1fr))');
    assert.equal(declarations('.history-review-summary > div').padding, '10px 12px');
    const narrow = stylesheet.nodes.find((node) => node.type === 'atrule' && node.params === '(max-width: 900px)' && node.nodes.some((rule) => rule.selector === '.history-review-summary'));
    const grid = narrow.nodes.find((node) => node.selector === '.history-review-summary');
    assert.equal(grid.nodes.find((node) => node.prop === 'grid-template-columns').value, 'repeat(2, minmax(0, 1fr))');
    assert.equal(declarations('.history-table td')['vertical-align'], 'top');
});
