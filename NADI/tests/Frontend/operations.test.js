import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import postcss from 'postcss';

const sheet = postcss.parse(readFileSync(new URL('../../resources/css/operations-draft.css', import.meta.url), 'utf8'));
const declarations = (selector, parent = sheet) => Object.fromEntries(parent.nodes.find((node) => node.type === 'rule' && node.selector === selector).nodes.filter((node) => node.type === 'decl').map(({ prop, value }) => [prop, value]));

test('draft detail status and mapping panels stack on mobile', () => {
    const mobile = sheet.nodes.find((node) => node.type === 'atrule' && node.params === '(max-width: 700px)');
    assert.equal(declarations('.ops-detail-body', mobile)['grid-template-columns'], '1fr');
    assert.equal(declarations('.ops-detail-states', mobile)['grid-template-columns'], '1fr');
    assert.equal(declarations('.ops-detail-heading', mobile)['flex-wrap'], 'wrap');
});

test('draft navigation exposes keyboard focus and selection beyond wellness color', () => {
    assert.equal(declarations('.ops-screen-tabs a:focus-visible, .ops-component-directory a:focus-visible').outline, '3px solid #276986');
    assert.equal(declarations('.ops-equipment:focus-visible').outline, '3px solid #276986');
    assert.equal(declarations('.ops-equipment:hover .ops-equipment-body, .ops-component-selected .ops-equipment-body')['stroke-dasharray'], '4 2');
});

test('only the diagram scrolls horizontally and anchored details clear the sticky header', () => {
    assert.equal(declarations('.ops-canvas-scroll')['overflow-x'], 'auto');
    assert.equal(declarations('.ops-canvas-scroll')['overscroll-behavior-x'], 'contain');
    assert.equal(declarations('.ops-detail, .ops-screen-placeholder')['scroll-margin-top'], '70px');
});
