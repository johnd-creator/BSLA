import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import { errorFieldName, isEditing } from '../../resources/js/workspace-ui.js';

const read = (path) => readFileSync(new URL('../../' + path, import.meta.url), 'utf8');

test('nested server validation keys map to the original field names', () => {
    assert.equal(errorFieldName('requester_name'), 'requester_name');
    assert.equal(errorFieldName('readings.motor_de.value'), 'readings[motor_de][value]');
    assert.equal(errorFieldName('members.0.role'), 'members[0][role]');
});

test('search shortcut never overrides typing or editable controls', () => {
    assert.equal(isEditing({ closest: () => ({ tagName: 'INPUT' }) }), true);
    assert.equal(isEditing({ closest: () => null }), false);
    assert.equal(isEditing(null), false);
    const source = read('resources/js/workspace-ui.js');
    assert.ok(source.includes('event.ctrlKey || event.metaKey || event.altKey || isEditing(event.target)'));
    assert.ok(read('resources/views/assets/index.blade.php').includes('<kbd aria-hidden="true">/</kbd>'));
});

test('shared paginator fits available content without numeric page sprawl', () => {
    const view = read('resources/views/vendor/pagination/tailwind.blade.php');
    assert.ok(view.includes('previousPageUrl()'));
    assert.ok(view.includes('nextPageUrl()'));
    assert.ok(view.includes('currentPage()'));
    assert.ok(!view.includes('$elements'));
    assert.ok(!view.includes('sm:'));
});

test('empty tables lose the wide minimum and ordinary data retains real table semantics', () => {
    const css = read('resources/css/app.css');
    assert.ok(css.includes(':has(tbody tr:only-child > td:is(.empty-table, .board-empty)) table { min-width: 0; }'));
    assert.ok(css.includes('.table-scroll-hint[hidden] { display: none; }'));
    const view = read('resources/views/assets/index.blade.php');
    assert.ok(view.includes('role="region" tabindex="0" aria-label="Daftar aset"'));
    assert.ok(view.includes('<table>'));
    assert.ok(view.includes('record-scroll'));
});

test('validation stays server-rendered and error links target the exact fields', () => {
    for (const name of ['auth/login', 'users/form', 'inspections/form', 'pdm/form', 'disruptions/form', 'priorities/form']) {
        const view = read(`resources/views/${name}.blade.php`);
        assert.ok(view.includes('<x-field-error'), name);
        assert.ok(view.includes('aria-invalid="true"'), name);
        assert.ok(!view.includes('- @error'), 'PHP property arrows must stay intact');
    }
    const summary = read('resources/views/components/feedback.blade.php');
    assert.ok(summary.includes('data-error-field="{{ $field }}"'));
    assert.ok(summary.includes('tabindex="-1" data-error-summary'));
});

test('grouped actions preserve unavailable Asset Wellness and technical source caveats', () => {
    const detail = read('resources/views/assets/show.blade.php');
    for (const text of ['Catat & tindak lanjuti', 'Telusuri riwayat', 'Draft awal Asset Wellness tersedia untuk meninjau bukti.', 'Identitas teknis & waktu record sumber', 'Waktu record sumber bukan bukti kesegaran sinkronisasi']) assert.ok(detail.includes(text));
    assert.ok(detail.includes("@can('write-pdm-activities')"));
    assert.ok(detail.includes("@if($record['registered'])"));
});

test('aggregate condition labels consistently use Asset Wellness without renaming technical Reliability', () => {
    const paths = [
        'resources/views/assets/show.blade.php',
        'resources/views/assets/timeline.blade.php',
        'resources/views/action-board.blade.php',
        'resources/views/inspections/show.blade.php',
        'resources/views/work-orders/show.blade.php',
        'resources/views/work-orders/annual.blade.php',
        'resources/views/disruptions/summary.blade.php',
        'resources/views/home.blade.php',
        'resources/views/operations/index.blade.php',
        'resources/views/overview/reports.blade.php',
        'app/Services/DataOverview.php',
        'app/Services/AssetTimeline.php',
    ];
    for (const path of paths) {
        const source = read(path);
        assert.match(source, /Asset Wellness|ASSET WELLNESS/, path);
        assert.doesNotMatch(source, /reliability score|score reliability|asset health|health score|skor kesehatan/i, path);
    }
    const detail = read('resources/views/assets/show.blade.php');
    assert.ok(detail.includes('Reliability · bukti & review tahunan'));
    assert.ok(detail.includes('Data kosong bukan berarti aset sehat atau risikonya rendah.'));
    assert.ok(detail.includes('Belum cukup data'));
    assert.ok(detail.includes('Belum diverifikasi'));
    assert.doesNotMatch(detail, /<meter|<progress/);
});

test('keyboard disclosure focus clears the sticky save bar', () => {
    const css = read('resources/css/app.css');
    assert.ok(css.includes('html { scroll-padding-bottom: 100px; }'));
    assert.ok(css.includes('.form-panel :is(a, button, input, select, textarea, summary)'));
    assert.ok(css.includes('scroll-margin-bottom: 100px;'));
});
