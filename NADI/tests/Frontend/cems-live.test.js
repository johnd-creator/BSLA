import test from 'node:test';
import assert from 'node:assert/strict';
import { setupCems } from '../../resources/js/cems-live.js';

class Element {
    constructor(kind, children = [], data = {}) { this.kind = kind; this.childNodes = []; this.dataset = data; this.value = 'SO2'; children.forEach(child => this.append(child)); }
    contains(node) { return this === node || this.childNodes.some(child => child.contains(node)); }
    append(node) { this.insertBefore(node, null); }
    insertBefore(node, before) {
        if (node.kind === 'fragment') { for (const child of [...node.childNodes]) this.insertBefore(child, before); return; }
        node.remove(); node.parentElement = this;
        const index = before === null ? this.childNodes.length : this.childNodes.indexOf(before);
        this.childNodes.splice(index, 0, node);
    }
    remove() { if (this.parentElement) { const siblings = this.parentElement.childNodes; siblings.splice(siblings.indexOf(this), 1); this.parentElement = null; } }
    replaceChildren(...children) { for (const child of [...this.childNodes]) child.remove(); children.forEach(child => this.append(child)); }
    matches(selector) { return ({ '[data-cems-filter]': 'form', '[name="parameter"]': 'select', '.cems-history': 'history', '.cems-history-scroll': 'table' })[selector] === this.kind || (selector === '[data-cems-quality="good"]' && this.dataset.cemsQuality === 'good'); }
    querySelector(selector) { return this.querySelectorAll(selector)[0] || null; }
    querySelectorAll(selector) { return this.childNodes.flatMap(child => [...(child.matches(selector) ? [child] : []), ...child.querySelectorAll(selector)]); }
    closest(selector) { return this.matches(selector) ? this : this.parentElement?.closest(selector); }
    addEventListener(event, fn) { this.events ||= {}; this.events[event] = fn; }
}
function fixture({ focused = false, observedOffset = 0, age = '0' } = {}) {
    let now = Date.parse('2026-11-08T12:00:00Z'), mono = 0, resolveFetch, calls = 0, timerID = 0;
    const callbacks = {}, timers = new Map(), urls = [];
    const tree = (label, offset = 0) => {
        const card = new Element('card', [], { cemsQuality: 'good', cemsObservedAt: new Date(now + offset).toISOString(), cemsAgeSeconds: age }); card.label = label;
        const select = new Element('select');
        return new Element('fragment', [new Element('cards', [card]), new Element('history', [new Element('heading'), new Element('form', [select]), new Element('table')])]);
    };
    const content = new Element('content');content.append(tree('initial', observedOffset));
    const originalSelect = content.querySelector('[name="parameter"]');
    const status = {};
    const doc = { hidden: false, activeElement: focused ? originalSelect : null, addEventListener(event, fn) { callbacks[event] = fn; }, createElement(kind) {
        if (kind !== 'template') return new Element(kind);
        return { set innerHTML(html) { this.content = html ? tree(html) : new Element('fragment'); } };
    } };
    const win = { Date: {now:()=>now}, performance:{now:()=>mono}, location:{origin:'http://localhost'}, setTimeout(fn,ms){const id=++timerID;timers.set(id,{fn,ms});return id;}, clearTimeout(id){timers.delete(id);}, setInterval(fn,ms){callbacks[ms]=fn;return ms;}, clearInterval(id){delete callbacks[id];}, addEventListener(event,fn){callbacks[event]=fn;}, fetch(url){calls++;urls.push(url.toString());return new Promise(r=>{resolveFetch=r;});} };
    const root = {dataset:{refreshUrl:'/operations/cems/refresh'},querySelector:selector=>selector==='[data-cems-content]'?content:status};
    return {...setupCems(root,doc,win),doc,content,status,callbacks,timers,originalSelect,urls,calls:()=>calls,advance(ms){now+=ms;mono+=ms;},finish(ok=true){resolveFetch({ok,headers:{get:()=> '1'},text:async()=> 'fresh'});}};
}
test('CEMS prevents overlapping requests, hidden-page polls, and polling after pagehide', async () => {
    const f=fixture();const pending=f.refresh();await f.refresh();assert.equal(f.calls(),1);f.finish();await pending;
    f.doc.hidden=true;f.callbacks.visibilitychange();await f.refresh();assert.equal(f.calls(),1);assert.equal(f.content.querySelectorAll('[data-cems-quality="good"]').length,0);
    f.doc.hidden=false;f.callbacks.pagehide();await f.refresh();assert.equal(f.calls(),1);assert.equal(f.callbacks[1000],undefined);assert.equal(f.callbacks[5000],undefined);
});
test('focused filter never pauses polling and its exact DOM node survives refresh', async () => {
    const f=fixture({focused:true});const pending=f.refresh();assert.equal(f.calls(),1);f.finish();await pending;
    assert.equal(f.content.querySelector('[name="parameter"]'),f.originalSelect);assert.equal(f.doc.activeElement,f.originalSelect);
    assert.equal(f.content.querySelectorAll('[data-cems-quality="good"]')[0].label,'fresh');assert(f.content.querySelector('.cems-history-scroll'));
});
test('selection changed during request is preserved without showing history for the old parameter', async () => {
    const f=fixture({focused:true});const pending=f.refresh();f.originalSelect.value='Hg';f.finish();await pending;
    assert.equal(f.content.querySelector('[name="parameter"]').value,'Hg');assert.equal(f.content.querySelector('.cems-history-scroll'),null);
    const next=f.refresh();assert(f.urls[1].includes('parameter=Hg'));f.finish();await next;assert(f.content.querySelector('.cems-history-scroll'));
});
test('watchdog hides good values at 15 seconds while filter is focused and a request is pending', async () => {
    const f=fixture({focused:true});const pending=f.refresh();f.advance(14999);f.checkFreshness();assert.equal(f.content.querySelectorAll('[data-cems-quality="good"]').length,1);
    f.advance(1);f.checkFreshness();assert.equal(f.content.querySelectorAll('[data-cems-quality="good"]').length,0);assert.equal(f.content.querySelector('[name="parameter"]'),f.originalSelect);assert.match(f.status.textContent,/kedaluwarsa/);
    f.finish();await pending;assert.equal(f.content.querySelectorAll('[data-cems-quality="good"]').length,1);
});
test('future timestamps and already stale age metadata fail closed in browser', () => {
    for(const options of [{observedOffset:1},{observedOffset:-15000},{age:'15'},{age:''},{age:'NaN'}]){
        const f=fixture(options);assert.equal(f.content.querySelectorAll('[data-cems-quality="good"]').length,0);assert.match(f.status.textContent,/kedaluwarsa/);
    }
});
test('failed refresh clears values but keeps a focused filter and recovers', async () => {
    const f=fixture({focused:true});const pending=f.refresh();f.finish(false);await pending;
    assert.equal(f.content.querySelectorAll('[data-cems-quality="good"]').length,0);assert.equal(f.content.querySelector('[name="parameter"]'),f.originalSelect);assert.match(f.status.textContent,/terputus/);
    const next=f.refresh();f.finish();await next;assert.equal(f.content.querySelectorAll('[data-cems-quality="good"]').length,1);
});
