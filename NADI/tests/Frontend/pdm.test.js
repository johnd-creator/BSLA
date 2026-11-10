import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const css = readFileSync(new URL('../../resources/css/pdm.css', import.meta.url), 'utf8');
const form = readFileSync(new URL('../../resources/views/pdm/form.blade.php', import.meta.url), 'utf8');

test('PdM point fields stack on mobile and keep values beside explicit units', () => {
    assert.match(css, /\.pdm-fields\s*\{[^}]*grid-template-columns:\s*repeat\(2/);
    assert.match(css, /@media \(max-width: 700px\)[\s\S]*\.pdm-fields\s*\{[^}]*grid-template-columns:\s*1fr/);
    assert.match(css, /\.pdm-value\s*\{[^}]*display:\s*flex/);
    assert.match(css, /\.pdm-form[^}]*overflow-wrap:\s*anywhere/);
    assert.match(css, /\.pdm-workbook-hash[^}]*overflow-wrap:\s*anywhere/);
    assert.match(css, /\[data-time-fields\]\[hidden\][^}]*display:\s*none/);
});

test('PdM inputs have labels, grouped points, provenance hints and explicit draft consent', () => {
    assert.match(form, /<fieldset class="pdm-field-group">/);
    assert.match(form, /<legend>/);
    assert.match(form, /aria-describedby="hint-/);
    assert.match(form, /name="acknowledge_draft" value="1" required/);
    assert.match(form, /type="datetime-local"/);
    assert.match(form, /name="time_precision" required/);
    assert.match(form, /type="date" name="measured_on"/);
    assert.match(form, /data-time-fields="datetime"/);
});

import { setupPdmTime } from '../../resources/js/pdm-time.js';

test('precision switch requires only the active fields and retains entered values', () => {
    let onChange;
    const precision = { value: 'date', addEventListener: (_type, handler) => { onChange = handler; } };
    const date = { value: '2026-07-08' };
    const time = { value: '2026-07-08T00:15:37' };
    const zone = { value: 'Asia/Jakarta' };
    const groups = [['date', [date]], ['datetime', [time, zone]]].map(([kind, inputs]) => ({ dataset: { timeFields: kind }, querySelectorAll: () => inputs }));
    setupPdmTime({ querySelector: () => precision, querySelectorAll: () => groups });
    assert.equal(date.required, true);
    assert.equal(time.disabled, true);
    assert.equal(zone.disabled, true);
    precision.value = 'datetime'; onChange();
    assert.equal(date.disabled, true);
    assert.equal(time.required, true);
    assert.equal(zone.required, true);
    assert.equal(groups[0].hidden, true);
    precision.value = 'date'; onChange();
    assert.equal(date.value, '2026-07-08');
    assert.equal(time.value, '2026-07-08T00:15:37');
    assert.equal(zone.value, 'Asia/Jakarta');
});

test('plan-guided measurement keeps context review explicit and marks only the planned point', () => {
    assert.match(form, /Konteks awal dari rencana inspeksi/);
    assert.match(form, /Nilai dan tanggal tetap kosong/);
    assert.match(form, /pdm-planned-point/);
    assert.match(form, /route\('pdm.plans.show', \$planContext\)/);
    assert.match(css, /\.pdm-plan-context\s*\{[^}]*overflow-wrap:\s*anywhere/);
});
