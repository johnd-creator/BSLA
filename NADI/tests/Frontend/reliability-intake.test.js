import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
const read = path => readFileSync(new URL('../../' + path, import.meta.url), 'utf8');

test('intake guides real evidence without auto-import, score or approval', () => {
    const view = read('resources/views/reliability/intake.blade.php');
    for (const text of ['1. Tetapkan aset & periode', '2. Temukan catatan asal', '3. Lengkapi fungsi, waktu & bukti', '4. Rekonsiliasi sebelum snapshot', 'Periksa tanpa menyimpan', 'belum tersimpan', 'Tanggal observasi', 'Historian bukan syarat wajib MTTR']) assert.ok(view.includes(text));
    assert.ok(view.includes("@can('write-asset-disruptions')"));
    assert.ok(view.includes('table-wrap table-scroll'));
    assert.doesNotMatch(view, /<script|style=|<progress|<meter/);
});

test('draft uses existing review form with original version and explicit attestation', () => {
    const view = read('resources/views/reliability/review.blade.php');
    for (const text of ['reliability.reviews.store', 'review_revision', 'event_version', 'Draft dari pratinjau', 'tidak ada attestation otomatis', 'intakePeriod->query()']) assert.ok(view.includes(text));
    assert.ok(read('app/Http/Controllers/ReliabilityIntakeController.php').includes("redirect()->route('reliability.reviews'"));
});
