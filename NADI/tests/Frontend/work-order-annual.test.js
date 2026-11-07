import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import postcss from 'postcss';

const css = postcss.parse(readFileSync(new URL('../../resources/css/work-order-annual.css', import.meta.url), 'utf8'));
const view = readFileSync(new URL('../../resources/views/work-orders/annual.blade.php', import.meta.url), 'utf8');

test('annual comparison keeps a horizontally scrollable compact table and wrapping codes', () => {
    assert.match(view, /class="table-scroll"/);
    const table = css.nodes.find((node) => node.selector === '.annual-wo-table');
    assert.equal(table.nodes.find((node) => node.prop === 'font-size').value, '12px');
    const groups = css.nodes.find((node) => node.selector === '.annual-wo-groups');
    assert.equal(groups.nodes.find((node) => node.prop === 'flex-wrap').value, 'wrap');
    assert.ok(css.nodes.some((node) => node.type === 'atrule' && node.params === '(max-width: 640px)'));
});

test('annual table exposes row headers, selection, explicit evidence and all-data scope', () => {
    for (const text of ['scope="row"', 'aria-current="true"', '<caption', 'Seluruh WO aset ini', 'historian DCS', 'Tahun belum diketahui', 'Pareto loss', 'bukan snapshot status akhir tahun']) {
        assert.ok(view.includes(text), text);
    }
});
