// Leases live only in this page's memory. No browser cache, storage or source URL.
export function visibleReading(row, now, interval) {
    const stamp = Date.parse(row.source_at);
    const age = Number.isFinite(stamp) ? Math.max(0, (now - stamp) / 1000) : null;
    const fresh = age !== null && stamp <= now + 1000 && age < interval * 3;
    return { ...row, value: fresh && row.quality === 'good' ? row.value : null,
        quality: !fresh && row.quality === 'good' ? 'stale' : row.quality, age_seconds: age };
}

export function setupHistorian(root, doc = document, win = window) {
    const status = root.querySelector('[data-historian-status]');
    const values = root.querySelector('[data-historian-values]');
    const context = root.querySelector('[data-historian-context]');
    const historyButton = root.querySelector('[data-history-load]');
    const historyTag = root.querySelector('[data-history-tag]');
    const historyResult = root.querySelector('[data-history-result]');
    const endpoint = root.dataset.url.replace(/subscribe$/, '');
    let lease = null, latest = null, busy = false, stopped = false, version = 0;
    let timer, controller, historyController, historyBusy = false, historyVersion = 0;
    let client = win.crypto.randomUUID();
    const controllers = new Set();

    const release = (token) => {
        if (!token) return;
        // CSRF-protected same-origin POST; expiry handles lost/offline beacons.
        const data = new FormData();
        data.set('_token', root.dataset.csrf);
        data.set('subscription', token);
        win.navigator.sendBeacon?.(`${endpoint}release`, data);
    };
    const clear = () => {
        latest = null;
        values.replaceChildren();
        historyResult.replaceChildren();
        historyButton.disabled = true;
    };
    const request = async (action, body, activeController) => {
        controllers.add(activeController);
        const timeout = win.setTimeout(() => activeController.abort(), 4500);
        try {
            const response = await win.fetch(`${endpoint}${action}`, {
                method: 'POST', credentials: 'same-origin', cache: 'no-store', redirect: 'error',
                headers: { Accept: 'application/json', 'Content-Type': 'application/json', 'X-CSRF-TOKEN': root.dataset.csrf },
                body: JSON.stringify(body), signal: activeController.signal,
            });
            if (!response.ok) throw new Error('unavailable');
            return await response.json();
        } finally {
            controllers.delete(activeController);
            win.clearTimeout(timeout);
        }
    };
    const cell = (tr, text) => { const td = doc.createElement('td'); td.textContent = text; tr.appendChild(td); };
    const render = () => {
        if (!latest || stopped || doc.hidden) return;
        values.replaceChildren();
        for (const raw of latest.tags) {
            const row = visibleReading(raw, Date.now(), latest.sample_seconds);
            const tr = doc.createElement('tr');
            cell(tr, `${row.label} (${row.tag})`);
            cell(tr, row.value === null ? '—' : `${row.value} ${row.unit}`);
            cell(tr, row.source_at?.replace(/\.\d+Z$/, 'Z') ?? 'Belum ada sampel');
            cell(tr, `${row.age_seconds === null ? '—' : `${Math.floor(row.age_seconds)} dtk`} · ${row.quality}`);
            values.appendChild(tr);
        }
    };
    const refresh = async () => {
        if (busy || stopped || doc.hidden) return;
        busy = true;
        const currentVersion = version;
        controller = new AbortController();
        try {
            const data = await request(lease ? 'heartbeat' : 'subscribe', lease ? { subscription: lease } : { page: root.dataset.page, client }, controller);
            if (currentVersion !== version || stopped || doc.hidden) { release(data.subscription); return; }
            lease = data.subscription;
            latest = data;
            render();
            status.textContent = data.status === 'no_data' ? 'Belum ada sampel. Cache dingin, menunggu pembacaan simulasi.' : `SIMULASI · cache bersama · sampel target ${data.sample_seconds} detik. Umur/kualitas tiap tag diperiksa terpisah.`;
            context.textContent = data.context_enabled ? 'Konteks umum simulasi diaktifkan setiap 60 detik untuk tag yang dikonfigurasi. Bukan status running equipment.' : 'Konteks umum per menit tidak aktif. Tanpa viewer, pembacaan berhenti setelah grace period.';
            historyButton.disabled = historyBusy;
        } catch {
            if (currentVersion === version && !stopped && !doc.hidden) {
                release(lease); lease = null;
                clear();
                status.textContent = 'Data tidak tersedia. Nilai lama disembunyikan; mencoba kembali saat halaman aktif.';
            }
        } finally {
            busy = false;
            if (!stopped && !doc.hidden) {
                win.clearTimeout(timer);
                timer = win.setTimeout(refresh, (latest?.sample_seconds ?? 5) * 1000);
            }
        }
    };
    const loadHistory = async () => {
        if (!lease || historyBusy || stopped || doc.hidden) return;
        historyBusy = true; historyButton.disabled = true;
        const historyRequest = ++historyVersion;
        const currentVersion = version;
        historyController = new AbortController();
        const end = new Date(); end.setMilliseconds(0);
        const start = new Date(end.getTime() - 15 * 60 * 1000);
        const date = (value) => value.toISOString().replace('.000Z', 'Z');
        historyResult.textContent = 'Memuat riwayat simulasi sesuai permintaan…';
        try {
            const result = await request('history', { subscription: lease, tag: historyTag.value, start: date(start), end: date(end), limit: 120 }, historyController);
            if (historyRequest !== historyVersion || currentVersion !== version || stopped || doc.hidden) return;
            historyResult.replaceChildren();
            const caption = doc.createElement('p');
            caption.textContent = `SIMULASI · ${result.tag} · ${result.points.length} titik. Cakupan kontinu tidak dinyatakan.`;
            historyResult.appendChild(caption);
            const table = doc.createElement('table'); table.className = 'data-table';
            const heading = doc.createElement('tr');
            for (const title of ['Waktu sumber', 'Nilai', 'Kualitas']) { const th = doc.createElement('th'); th.textContent = title; heading.appendChild(th); }
            const head = doc.createElement('thead'); head.appendChild(heading); table.appendChild(head);
            const body = doc.createElement('tbody');
            for (const point of result.points) {
                const tr = doc.createElement('tr');
                cell(tr, point.source_at); cell(tr, point.value === null ? '—' : String(point.value)); cell(tr, point.quality);
                body.appendChild(tr);
            }
            table.appendChild(body); historyResult.appendChild(table);
        } catch {
            if (historyRequest === historyVersion && currentVersion === version && !stopped && !doc.hidden) historyResult.textContent = 'Riwayat tidak tersedia. Tidak ada data pengganti.';
        } finally {
            historyBusy = false;
            historyButton.disabled = !lease;
        }
    };
    const pause = () => {
        version++;
        win.clearTimeout(timer);
        controllers.forEach(item => item.abort());
        release(lease); lease = null;
        clear();
        client = win.crypto.randomUUID();
        status.textContent = 'Halaman tidak aktif. Subscription dilepas; nilai disembunyikan.';
    };
    historyButton.addEventListener('click', loadHistory);
    historyTag.addEventListener('change', () => { historyVersion++; historyController?.abort(); historyResult.replaceChildren(); });
    doc.addEventListener('visibilitychange', () => { if (doc.hidden) pause(); else refresh(); });
    const freshnessTimer = win.setInterval(render, 1000);
    win.addEventListener('pagehide', () => { stopped = true; pause(); win.clearInterval(freshnessTimer); });
    win.addEventListener('pageshow', event => { if (event.persisted) win.location.reload(); });
    refresh();
    return { refresh, pause, loadHistory };
}
