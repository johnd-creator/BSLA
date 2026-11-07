import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import postcss from 'postcss';

const stylesheet = postcss.parse(readFileSync(new URL('../../resources/css/asset-visual.css', import.meta.url), 'utf8'));
const declarations = (selector, parent = stylesheet) => Object.fromEntries(parent.nodes.find((node) => node.type === 'rule' && node.selector === selector).nodes.filter((node) => node.type === 'decl').map(({ prop, value }) => [prop, value]));
const media = (query) => stylesheet.nodes.find((node) => node.type === 'atrule' && node.params === query);

test('asset visual is compact and preserves thumbnail proportions', () => {
    assert.equal(declarations('.asset-visual').width, '196px');
    assert.equal(declarations('.asset-visual')['max-width'], '100%');
    assert.equal(declarations('.asset-visual-frame')['aspect-ratio'], '16 / 9');
    assert.equal(declarations('.asset-visual-image')['object-fit'], 'contain');
    assert.equal(declarations('.asset-heading-identity h2')['overflow-wrap'], 'anywhere');
});

test('desktop actions form equal-width rows below media in a right sidebar', () => {
    assert.equal(declarations('.asset-detail-layout')['grid-template-columns'], 'minmax(0, 1fr) 248px');
    assert.equal(declarations('.asset-detail-layout')['align-items'], 'start');
    assert.equal(declarations('.asset-detail-sidebar').display, 'grid');
    assert.equal(declarations('.asset-detail-sidebar .asset-visual').width, '100%');
    assert.equal(declarations('.asset-detail-actions')['grid-template-columns'], 'minmax(0, 1fr)');
    assert.equal(declarations('.asset-detail-actions .button').width, '100%');
    assert.equal(declarations('.asset-detail-actions .button')['text-align'], 'left');
    assert.equal(declarations('.asset-detail-actions .button')['overflow-wrap'], 'anywhere');
});

test('narrow desktop allows facts to wrap without squeezing the action rail', () => {
    const narrow = media('(min-width: 701px) and (max-width: 1000px)');
    assert.equal(declarations('.asset-detail-layout', narrow)['grid-template-columns'], 'minmax(0, 1fr) 212px');
    assert.equal(declarations('.asset-detail-facts .detail-grid', narrow)['grid-template-columns'], 'minmax(0, 1fr)');
});

test('mobile stacks the sidebar, keeps the thumbnail small and exposes touch-sized links', () => {
    const mobile = media('(max-width: 700px)');
    assert.equal(declarations('.asset-detail-layout', mobile)['grid-template-columns'], 'minmax(0, 1fr)');
    assert.equal(declarations('.asset-detail-sidebar .asset-visual', mobile).width, '176px');
    assert.equal(declarations('.asset-detail-actions', mobile)['grid-template-columns'], 'repeat(2, minmax(0, 1fr))');
    assert.equal(declarations('.asset-detail-actions .button', mobile)['min-height'], '44px');
    assert.equal(declarations('.asset-detail-actions', media('(max-width: 420px)'))['grid-template-columns'], 'minmax(0, 1fr)');
});

test('reliability placeholder remains neutral and its evidence list stacks on narrow screens', () => {
    assert.equal(declarations('.asset-reliability-pending').color, 'var(--muted)');
    assert.equal(declarations('.asset-reliability-inputs')['grid-template-columns'], 'repeat(2, minmax(0, 1fr))');
    assert.equal(declarations('.asset-reliability-inputs', media('(max-width: 1000px)'))['grid-template-columns'], 'minmax(0, 1fr)');
});
