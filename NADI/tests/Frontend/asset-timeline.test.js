import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import postcss from 'postcss';

const css = postcss.parse(readFileSync(new URL('../../resources/css/asset-timeline.css', import.meta.url), 'utf8'));
const declaration = (selector, property, parent = css) => parent.nodes.find((node) => node.type === 'rule' && node.selector === selector).nodes.find((node) => node.prop === property)?.value;

test('timeline uses a bounded-width date rail and wrapping record references', () => {
    assert.equal(declaration('.asset-timeline > li', 'grid-template-columns'), '180px minmax(0, 1fr)');
    assert.equal(declaration('.timeline-event', 'overflow-wrap'), 'anywhere');
    assert.equal(declaration('.timeline-reference p', 'overflow-wrap'), 'anywhere');
});

test('mobile timeline stacks entries and exposes touch-sized history links', () => {
    const mobile = css.nodes.find((node) => node.type === 'atrule' && node.params === '(max-width: 600px)');
    assert.equal(declaration('.asset-timeline > li', 'grid-template-columns', mobile), 'minmax(0, 1fr)');
    assert.equal(declaration('.timeline-links .button', 'min-height', mobile), '44px');
});
