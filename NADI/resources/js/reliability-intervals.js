export function parseIntervalText(text) {
    if (!text.trim()) return [];
    return text.trim().split(/\r?\n/).map(line => {
        const parts = line.split(' | ');
        if (parts.length !== 2) throw new Error('Format interval');
        return parts.map(part => {
            const match = /^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(Z|[+-]\d{2}:\d{2})$/.exec(part.trim());
            if (!match || match[2] === '-00:00') throw new Error('Waktu belum tepat');
            return {local: match[1], offset: match[2] === 'Z' ? '+00:00' : match[2]};
        });
    });
}

export function intervalText(rows) {
    return rows.filter(row => row.some(time => time.local)).map(row => row.map(time => {
        if (!time.local) return '';
        const local = time.local.length === 16 ? `${time.local}:00` : time.local;
        return `${local}${time.offset}`;
    }).join(' | ')).join('\n');
}

export function setupRepairIntervals(root) {
    if (root.dataset.intervalsReady) return;
    const textarea = root.querySelector('textarea');
    if (!textarea) return;
    let initial;
    try { initial = parseIntervalText(textarea.value); } catch { return; }
    root.dataset.intervalsReady = 'true';
    const doc = root.ownerDocument;
    const editor = doc.createElement('div');
    editor.className = 'repair-interval-editor stack';
    const list = doc.createElement('div');
    list.className = 'stack';
    const status = doc.createElement('p');
    status.setAttribute('role', 'status');
    status.className = 'field-hint';
    const add = doc.createElement('button');
    add.type = 'button'; add.className = 'button secondary'; add.textContent = 'Tambah interval kerja';
    let sequence = 0;
    const sync = () => {
        const rows = Array.from(list.children).map(row => Array.from(row.querySelectorAll('.repair-time')).map(time => ({local: time.querySelector('input').value, offset: time.querySelector('select').value})));
        textarea.value = intervalText(rows);
        add.disabled = rows.length >= 20;
        status.textContent = `${rows.length} dari maksimal 20 interval. Jeda di antara interval tidak dijumlahkan; validasi akhir dilakukan saat simpan.`;
    };
    const append = (values = [{local:'',offset:'+07:00'},{local:'',offset:'+07:00'}]) => {
        if (list.children.length >= 20) return;
        const row = doc.createElement('fieldset');
        row.className = 'repair-interval-row form-grid';
        const legend = doc.createElement('legend'); legend.textContent = `Interval kerja ${++sequence}`; row.append(legend);
        values.forEach((value, i) => {
            const group = doc.createElement('div'); group.className = 'repair-time';
            const label = doc.createElement('label'); label.textContent = i ? 'Akhir kerja aktif' : 'Awal kerja aktif';
            const input = doc.createElement('input'); input.type = 'datetime-local'; input.step = '1'; input.value = value.local;
            input.id = `repair-${sequence}-${i}`; label.htmlFor = input.id;
            const zoneLabel = doc.createElement('label'); zoneLabel.textContent = 'Offset zona sumber';
            const zone = doc.createElement('select'); zone.id = `${input.id}-zone`; zoneLabel.htmlFor = zone.id;
            for (const offset of [...new Set(['+07:00','+08:00','+09:00','+00:00',value.offset])]) {
                const option = doc.createElement('option'); option.value = offset; option.textContent = `UTC${offset}${offset === '+07:00' ? ' · WIB' : ''}`; zone.append(option);
            }
            zone.value = value.offset;
            input.addEventListener('input', sync); zone.addEventListener('change', sync);
            group.append(label, input, zoneLabel, zone); row.append(group);
        });
        const remove = doc.createElement('button'); remove.type='button'; remove.className='button secondary'; remove.textContent='Hapus interval dari draft';
        remove.addEventListener('click', () => { row.remove(); sync(); add.focus(); });
        row.append(remove); list.append(row); sync();
        return row;
    };
    add.addEventListener('click', () => append()?.querySelector('input').focus());
    editor.append(list, add, status);
    root.insertBefore(editor, textarea);
    // Keep the existing plain-text control as a no-JS/advanced fallback. It is
    // hidden only after successful enhancement, never disabled or discarded.
    textarea.hidden = true;
    const label = root.querySelector(`label[for="${textarea.id}"]`);
    if (label) label.hidden = true;
    initial.forEach(append);
    sync();
    textarea.form?.addEventListener('submit', sync);
}
