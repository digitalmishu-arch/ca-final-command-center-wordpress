/* global CAFCCAdmin */
(() => {
    'use strict';
    const root = document.getElementById('cafcc-admin');
    if (!root) return;
    const entity = root.querySelector('#cafcc-entity');
    const records = root.querySelector('#cafcc-records');
    const pages = root.querySelector('#cafcc-pages');
    const form = root.querySelector('#cafcc-form');
    const fields = root.querySelector('#cafcc-fields');
    const message = root.querySelector('#cafcc-message');
    let catalog = {}, editing = 0, page = 1, busy = false;
    const el = (tag, text) => { const node = document.createElement(tag); if (text !== undefined) node.textContent = text; return node; };
    const label = key => key.replaceAll('_', ' ').replace(/\b\w/g, c => c.toUpperCase());
    const option = (value, text) => { const node = el('option', text); node.value = value; return node; };
    const tell = (text, bad = false) => { message.textContent = text; message.classList.toggle('cafcc-error', bad); };
    async function api(path, method = 'GET', body) {
        const [route, query = ''] = path.split('?');
        const target = new URL(CAFCCAdmin.url + 'admin/' + route);
        new URLSearchParams(query).forEach((value, key) => target.searchParams.set(key, value));
        const response = await fetch(target, {
            method, credentials: 'same-origin', cache: 'no-store',
            headers: {'X-WP-Nonce': CAFCCAdmin.nonce, 'Content-Type': 'application/json'},
            body: body ? JSON.stringify(body) : undefined
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.message || 'Request failed.');
        return data;
    }
    function setBusy(value) {
        busy = value;
        root.querySelectorAll('button, input, select').forEach(node => { node.disabled = value; });
    }
    async function loadCatalog() {
        const results = await Promise.all(Object.keys(CAFCCAdmin.fields).map(async name => {
            const all = [];
            let n = 1, result;
            do {
                result = await api(name + '?page=' + n++);
                all.push(...result.items);
                if (n > 101 && all.length < result.total) throw new Error('Admin picker limit reached. Use a smaller reviewed corpus in version 0.1.0.');
            } while (all.length < result.total);
            return [name, all];
        }));
        catalog = Object.fromEntries(results);
    }
    function editor(record = {}) {
        editing = record.id || 0;
        root.querySelector('#cafcc-form-title').textContent = editing ? 'Edit record #' + editing : 'New ' + entity.value.replace(/s$/, '') + ' record';
        fields.replaceChildren();
        const relations = {subject_id: 'subjects', chapter_id: 'chapters', topic_id: 'topics', document_id: 'documents'};
        Object.entries(CAFCCAdmin.fields[entity.value]).forEach(([key, type]) => {
            const wrapper = el('label', label(key));
            let input;
            if (relations[key]) {
                input = el('select');
                input.append(option('', type === 'optional_id' ? 'No topic (optional)' : 'Select a record'));
                (catalog[relations[key]] || []).forEach(row => {
                    const text = (row.code ? row.code + ' — ' : '') + (row.title || row.name) + (row.syllabus_version ? ' · ' + row.syllabus_version : '');
                    input.append(option(row.id, '#' + row.id + ' ' + text));
                });
            } else if (['source', 'verification', 'publication'].includes(type)) {
                input = el('select');
                const choices = type === 'source' ? CAFCCAdmin.sources : type === 'verification' ? CAFCCAdmin.verification : ['draft', 'published'];
                choices.forEach(value => input.append(option(value, label(value))));
            } else {
                input = el('input');
                input.type = type === 'url' ? 'url' : type === 'position' ? 'number' : 'text';
                if (typeof type === 'number') input.maxLength = type;
                if (type === 'position') { input.min = '0'; input.max = '999999'; input.step = '1'; input.value = '0'; }
                if (key === 'official_url') input.placeholder = 'https://www.icai.org/…';
            }
            input.name = key;
            input.required = !['optional_id', 'url', 'position'].includes(type);
            if (record[key] !== undefined && record[key] !== null) input.value = record[key];
            wrapper.append(input); fields.append(wrapper);
        });
        fields.append(el('p', 'For questions, select a topic from the chosen chapter and match the source and chapter syllabus versions exactly. To approve, set Verification Status to Verified. Publish only after checking the official source.'));
    }
    function renderRecords() {
        records.replaceChildren(); pages.replaceChildren();
        const rows = catalog[entity.value] || [];
        const max = Math.max(1, Math.ceil(rows.length / 100));
        page = Math.min(page, max);
        if (!rows.length) records.append(el('p', 'No records yet. Add the first reviewed record using the form.'));
        rows.slice((page - 1) * 100, page * 100).forEach(row => {
            const card = el('div'); card.className = 'cafcc-record';
            card.append(el('strong', '#' + row.id + ' · ' + (row.code || row.question_number || '') + ' ' + (row.title || row.name)));
            if (row.verification_status) card.append(el('p', label(row.verification_status) + (row.publication_status ? ' · ' + label(row.publication_status) : '')));
            const edit = el('button', 'Edit'); edit.type = 'button'; edit.className = 'button';
            edit.addEventListener('click', () => { if (!busy) { editor(row); form.scrollIntoView({block: 'start', behavior: 'smooth'}); } });
            const remove = el('button', 'Delete'); remove.type = 'button'; remove.className = 'button';
            remove.addEventListener('click', async () => {
                if (busy || !window.confirm('Delete this academic record? Records with dependencies or student progress cannot be deleted.')) return;
                setBusy(true);
                try {
                    await api(entity.value + '/' + row.id, 'DELETE');
                    await loadCatalog(); renderRecords(); editor(); tell('Record deleted.');
                } catch (e) { tell(e.message, true); }
                finally { setBusy(false); }
            });
            card.append(edit, document.createTextNode(' '), remove); records.append(card);
        });
        if (max > 1) {
            const prev = el('button', 'Previous'); const next = el('button', 'Next'); prev.type = next.type = 'button';
            prev.disabled = page <= 1; next.disabled = page >= max;
            prev.addEventListener('click', () => { if (page > 1 && !busy) { page--; renderRecords(); } });
            next.addEventListener('click', () => { if (page < max && !busy) { page++; renderRecords(); } });
            pages.append(prev, el('span', 'Page ' + page + ' of ' + max), next);
        }
    }
    entity.addEventListener('change', () => { page = 1; renderRecords(); editor(); tell(''); });
    root.querySelector('#cafcc-new').addEventListener('click', () => { if (!busy) editor(); });
    form.addEventListener('submit', async event => {
        event.preventDefault();
        if (busy) return;
        const data = Object.fromEntries(new FormData(form));
        setBusy(true);
        try {
            await api(entity.value + (editing ? '/' + editing : ''), editing ? 'PATCH' : 'POST', data);
            await loadCatalog(); renderRecords(); editor(); tell('Record saved.');
        } catch (e) { tell(e.message, true); }
        finally { setBusy(false); }
    });
    (async () => {
        setBusy(true);
        try { await loadCatalog(); renderRecords(); editor(); }
        catch (e) { tell(e.message, true); }
        finally { setBusy(false); }
    })();
})();
