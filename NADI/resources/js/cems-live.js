// Only this page polls the shared backend. No local/session storage or service worker.
export function setupCems(root, doc = document, win = window) {
    const content = root.querySelector('[data-cems-content]');
    const status = root.querySelector('[data-refresh-status]');
    const wallNow = () => (win.Date || Date).now();
    const monotonicNow = () => win.performance?.now() ?? wallNow();
    let busy = false;
    let stopped = false;
    let controller;
    let expiryTimer;
    let renderedAt = monotonicNow();
    let parameter = content.querySelector('[name="parameter"]')?.value;

    // Keep an open/keyboard-focused filter connected to the DOM. Only its data
    // siblings change, so polling never pauses and an open select is not replaced.
    const render = (html, requestedParameter = parameter) => {
        const template = doc.createElement('template');
        template.innerHTML = html;
        const fragment = template.content;
        const form = content.querySelector('[data-cems-filter]');
        const history = form?.closest('.cems-history');
        if (history && form.contains(doc.activeElement)) {
            const incoming = fragment.querySelector('.cems-history');
            const incomingForm = incoming?.querySelector('[data-cems-filter]');
            const currentParameter = form.querySelector('[name="parameter"]')?.value;
            const changed = currentParameter !== requestedParameter;
            for (const node of [...history.childNodes]) if (node !== form) node.remove();
            if (incoming && !changed) {
                let beforeForm = true;
                for (const node of [...incoming.childNodes]) {
                    if (node === incomingForm) { beforeForm = false; continue; }
                    history.insertBefore(node, beforeForm ? form : null);
                }
            } else {
                const note = doc.createElement('p');
                note.className = 'data-note';
                note.textContent = changed ? 'Pilihan berubah. Riwayat sedang diperbarui.' : 'Riwayat belum tersedia.';
                history.append(note);
            }
            incoming?.remove();
            for (const node of [...content.childNodes]) if (node !== history) node.remove();
            content.insertBefore(fragment, history);
        } else {
            content.replaceChildren(fragment);
        }
        renderedAt = monotonicNow();
    };
    const clearValues = (message) => {
        win.clearTimeout(expiryTimer);
        render('');
        status.textContent = message;
    };
    const remainingFreshness = () => {
        let remaining = Infinity;
        for (const card of content.querySelectorAll('[data-cems-quality="good"]')) {
            const observed = Date.parse(card.dataset.cemsObservedAt || '');
            const age = Number(card.dataset.cemsAgeSeconds);
            if (!Number.isFinite(observed) || card.dataset.cemsAgeSeconds == null || card.dataset.cemsAgeSeconds === '' || !Number.isFinite(age) || age < 0 || observed > wallNow()) return 0;
            const elapsed = Math.max(0, monotonicNow() - renderedAt);
            remaining = Math.min(remaining, 15000 - Math.max(wallNow() - observed, age * 1000 + elapsed));
        }
        return remaining;
    };
    const checkFreshness = () => {
        win.clearTimeout(expiryTimer);
        if (stopped || doc.hidden) return;
        const remaining = remainingFreshness();
        if (remaining <= 0) {
            clearValues('Data kedaluwarsa. Nilai lama disembunyikan sambil menunggu pembaruan.');
        } else if (Number.isFinite(remaining)) {
            expiryTimer = win.setTimeout(checkFreshness, remaining);
        }
    };
    const refresh = async () => {
        if (busy || stopped || doc.hidden) return;
        busy = true;
        controller = new AbortController();
        const timeout = win.setTimeout(() => controller.abort(), 9000);
        const url = new URL(root.dataset.refreshUrl, win.location.origin);
        const selected = content.querySelector('[name="parameter"]');
        if (selected) parameter = selected.value;
        const requestedParameter = parameter;
        if (parameter) url.searchParams.set('parameter', parameter);
        try {
            const response = await win.fetch(url, { headers: { Accept: 'text/html' }, cache: 'no-store', redirect: 'error', signal: controller.signal });
            if (!response.ok || response.headers.get('X-Cems-Fragment') !== '1') throw new Error('unavailable');
            const html = await response.text();
            if (!stopped && !doc.hidden) {
                render(html, requestedParameter);
                status.textContent = 'Pembaruan tampilan setiap 5 detik saat halaman terlihat.';
                checkFreshness();
            }
        } catch {
            if (!stopped && !doc.hidden) clearValues('Koneksi pembaruan terputus. Nilai lama disembunyikan; coba kembali atau masuk ulang.');
        } finally {
            win.clearTimeout(timeout);
            busy = false;
        }
    };
    content.addEventListener('submit', (event) => {
        if (!event.target.matches('[data-cems-filter]')) return;
        event.preventDefault();
        refresh();
    });
    content.addEventListener('change', (event) => {
        if (!event.target.matches('[name="parameter"]')) return;
        parameter = event.target.value;
        // Never label an earlier parameter's history with a newly selected name.
        content.querySelector('.cems-history-scroll')?.remove();
        refresh();
    });
    doc.addEventListener('visibilitychange', () => {
        if (doc.hidden) {
            controller?.abort();
            clearValues('Pembaruan dijeda saat halaman tidak terlihat.');
        } else { checkFreshness(); refresh(); }
    });
    const interval = win.setInterval(refresh, 5000);
    const watchdog = win.setInterval(checkFreshness, 1000);
    win.addEventListener('pagehide', () => {
        stopped = true;
        controller?.abort();
        win.clearInterval(interval);
        win.clearInterval(watchdog);
        clearValues('Pembaruan dijeda.');
    });
    win.addEventListener('pageshow', (event) => { if (event.persisted) win.location.reload(); });
    checkFreshness();
    return { refresh, checkFreshness };
}
