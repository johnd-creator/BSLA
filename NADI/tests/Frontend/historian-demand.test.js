import test from 'node:test';
import assert from 'node:assert/strict';
import { setupHistorian, visibleReading } from '../../resources/js/historian-demand.js';

function node() { return { children: [], disabled: false, value: 'DEMO.TEMP', addEventListener(name, fn) { this[name] = fn; }, appendChild(n) { this.children.push(n); }, replaceChildren() { this.children = []; } }; }
function fixture() {
    const callbacks = {}, requests = [], timers = new Map(), beacons = [];
    const parts = Object.fromEntries(['status', 'values', 'context'].map(n => [`[data-historian-${n}]`, node()]));
    for (const n of ['load', 'tag', 'result']) parts[`[data-history-${n}]`] = node();
    const root = { dataset: { page: 'demo-temperature', url: '/operations/historian/subscribe', csrf: 'fixture' }, querySelector: key => parts[key] };
    const doc = { hidden: false, createElement: () => node(), addEventListener(name, fn) { callbacks[name] = fn; } };
    let sequence = 0;
    const win = { crypto: { randomUUID: () => `client-${++sequence}` }, navigator: { sendBeacon: (url, data) => beacons.push({url, data}) },
        setTimeout(fn, ms) { const id = ++sequence; timers.set(id, {fn, ms}); return id; }, clearTimeout(id) { timers.delete(id); },
        setInterval(fn) { callbacks.freshness = fn; return 90; }, clearInterval() {}, addEventListener(name, fn) { callbacks[name] = fn; }, location: { reload() { callbacks.reloaded = true; } },
        fetch(url, options) { return new Promise((resolve, reject) => requests.push({url, options, resolve, reject})); } };
    const api = setupHistorian(root, doc, win);
    const result = { subscription: 'a'.repeat(48), sample_seconds: 4, status: 'current', context_enabled: false,
        tags: [{ tag: 'DEMO.TEMP', label: 'Demo', value: 0, source_at: new Date().toISOString(), quality: 'good', unit: '°C' }] };
    const finish = async (n=0, value=result) => { requests[n].resolve({ok:true, json:async()=>value}); await new Promise(r=>setImmediate(r)); };
    return {api, doc, callbacks, parts, requests, finish, timers, beacons};
}

test('timestamp watchdog hides stale values but preserves valid zero', () => {
    const row = {value:0, source_at:'2026-11-08T00:00:00Z', quality:'good'};
    assert.equal(visibleReading(row, Date.parse(row.source_at)+5000, 4).value, 0);
    assert.equal(visibleReading(row, Date.parse(row.source_at)+12000, 4).value, null);
    assert.equal(visibleReading({...row,quality:'bad'}, Date.parse(row.source_at),4).value,null);
});
test('subscribe is immediate, overlap prevented, heartbeat shares lease and history stays on demand', async () => {
    const f = fixture(); await f.api.refresh(); assert.equal(f.requests.length,1); await f.finish();
    const pending = f.api.refresh(); assert.ok(f.requests[1].url.endsWith('heartbeat'));
    assert.equal(JSON.parse(f.requests[1].options.body).subscription,'a'.repeat(48)); await f.finish(1); await pending;
    assert.ok(f.requests.every(r=>!r.url.endsWith('history')));
});
test('hidden page releases lease, clears readings, then resumes with a new client', async () => {
    const f = fixture(); await f.finish(); f.doc.hidden=true; f.callbacks.visibilitychange();
    assert.equal(f.beacons.length,1); assert.equal(f.parts['[data-historian-values]'].children.length,0);
    await f.api.refresh(); assert.equal(f.requests.length,1);
    f.doc.hidden=false; f.callbacks.visibilitychange(); assert.ok(f.requests[1].url.endsWith('subscribe')); await f.finish(1);
    f.callbacks.pagehide(); await f.api.refresh(); assert.equal(f.requests.length,2);
    f.callbacks.pageshow({persisted:true}); assert.equal(f.callbacks.reloaded,true);
});
test('late subscribe after navigation cannot render or retain a lease', async () => {
    const f = fixture(); f.callbacks.pagehide(); await f.finish();
    assert.equal(f.parts['[data-historian-values]'].children.length,0); assert.equal(f.beacons.length,1);
});
test('network failure clears cached values and retries without stale lease', async () => {
    const f = fixture(); await f.finish(); const pending=f.api.refresh(); f.requests[1].reject(new Error('offline')); await pending;
    assert.equal(f.parts['[data-historian-values]'].children.length,0); assert.equal(f.parts['[data-history-load]'].disabled,true);
    const retry=f.api.refresh(); assert.ok(f.requests[2].url.endsWith('subscribe')); await f.finish(2); await retry;
});
test('history reads are click-only, bounded and prevent repeat overlap', async () => {
    const f=fixture(); await f.finish(); const pending=f.api.loadHistory(); await f.api.loadHistory();
    assert.equal(f.requests.length,2); const body=JSON.parse(f.requests[1].options.body);
    assert.equal(body.limit,120); assert.equal(Date.parse(body.end)-Date.parse(body.start),900000);
    await f.finish(1,{points:[]}); await pending;
});

test('changing history tag discards an older in-flight result', async () => {
    const f=fixture(); await f.finish(); const pending=f.api.loadHistory();
    f.parts['[data-history-tag]'].change(); await f.finish(1,{tag:'DEMO.TEMP',points:[]}); await pending;
    assert.equal(f.parts['[data-history-result]'].children.length,0);
});
