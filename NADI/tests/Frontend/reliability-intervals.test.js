import test from 'node:test';
import assert from 'node:assert/strict';
import { parseIntervalText, intervalText } from '../../resources/js/reliability-intervals.js';

test('repair editor round trips explicit offsets and seconds without timezone guessing', () => {
 const text='2025-01-01T08:00:00+07:00 | 2025-01-01T08:30:11+07:00\n2025-01-01T02:00:00+00:00 | 2025-01-01T02:30:00+00:00';
 assert.equal(intervalText(parseIntervalText(text)),text);
 assert.equal(intervalText(parseIntervalText('2025-01-01T01:00:00Z | 2025-01-01T02:00:00Z')),'2025-01-01T01:00:00+00:00 | 2025-01-01T02:00:00+00:00');
});
test('repair editor leaves invalid source text for the native fallback', () => {
 for (const input of ['2025-01-01 | 2025-01-02', '2025-01-01T00:00:00-00:00 | 2025-01-01T01:00:00Z', 'no delimiter']) assert.throws(()=>parseIntervalText(input));
 assert.deepEqual(parseIntervalText(''),[]);
});
test('repair editor does not turn empty or incomplete intervals into zero duration', () => {
 assert.equal(intervalText([[{local:'',offset:'+07:00'},{local:'',offset:'+07:00'}]]),'');
 assert.equal(intervalText([[{local:'2025-01-01T08:00',offset:'+07:00'},{local:'',offset:'+07:00'}]]),'2025-01-01T08:00:00+07:00 | ');
});
