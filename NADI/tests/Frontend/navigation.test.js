import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const source = readFileSync(new URL('../../resources/js/app.js', import.meta.url), 'utf8');

function mount(matches) {
    const navigation = { open: true };
    const media = {
        matches,
        addEventListener(event, listener) {
            assert.equal(event, 'change');
            this.change = listener;
        },
    };
    vm.runInNewContext(source, {
        document: { querySelector: () => navigation },
        window: {
            matchMedia(query) {
                assert.equal(query, '(max-width: 700px)');
                return media;
            },
        },
    });
    return { navigation, media };
}

test('desktop navigation starts open', () => {
    assert.equal(mount(false).navigation.open, true);
});

test('mobile navigation starts collapsed', () => {
    assert.equal(mount(true).navigation.open, false);
});

test('resizing restores desktop navigation after the mobile menu was closed', () => {
    const { navigation, media } = mount(true);
    media.matches = false;
    media.change();
    assert.equal(navigation.open, true);
    media.matches = true;
    media.change();
    assert.equal(navigation.open, false);
    media.matches = false;
    media.change();
    assert.equal(navigation.open, true);
});

test('login and error pages do not require a navigation element', () => {
    assert.doesNotThrow(() => vm.runInNewContext(source, {
        document: { querySelector: () => null },
    }));
});
