/* global CAFCCPractice */
(() => {
    'use strict';
    const root = document.getElementById('cc-practice-admin'); if (!root) return;
    const $ = id => document.getElementById(id), form = $('pc-editor');
    let current = null, page = 1;
    const tell = text => { $('pc-feedback').textContent = text; };
    async function api(path, method = 'GET', data) {
        const [route, query = ''] = path.split('?'), url = new URL(CAFCCPractice.url + route);
        new URLSearchParams(query).forEach((v, k) => url.searchParams.set(k, v));
        const response = await fetch(url, {method, credentials: 'same-origin', cache: 'no-store', headers: {'X-WP-Nonce': CAFCCPractice.nonce, 'Content-Type': 'application/json'}, body: data ? JSON.stringify(data) : undefined});
        const result = await response.json(); if (!response.ok) throw Error(result.message || 'Request failed'); return result;
    }
    function edit(row) {
        current = row; form.reset(); $('pc-confirm').checked = false;
        ['question_id', 'content_kind', 'rights_type', 'author_name', 'source_location', 'rights_basis', 'rights_expires', 'body_html'].forEach(k => { form.elements[k].value = row ? row[k] : (k === 'content_kind' ? 'question' : k === 'rights_type' ? 'reference_only' : ''); });
        form.elements.choice_lines.value = row ? JSON.parse(row.options_json).map(o => o.key + ' | ' + o.text).join('\n') : '';
        const editor = window.tinymce && window.tinymce.get('pc_body_html'); if (editor) { editor.setContent(row ? row.body_html : ''); editor.setDirty(false); }
        $('pc-title').textContent = row ? 'Content #' + row.id + ' · revision ' + row.revision + ' · ' + row.publication_status : 'New content';
        form.elements.question_id.readOnly = !!row; form.elements.content_kind.disabled = !!row;
        // This value was sanitised by the server's explicit rich-content allowlist.
        $('pc-preview').innerHTML = row ? row.body_html : ''; $('pc-approve').disabled = !row;
    }
    async function load() {
        const rows = await api('admin/practice?page=' + page); $('pc-records').replaceChildren();
        rows.forEach(row => { const b = document.createElement('button'); b.type = 'button'; b.textContent = '#' + row.id + ' · Q' + row.question_id + ' · ' + row.content_kind + ' · ' + row.rights_type + ' · ' + row.publication_status; b.addEventListener('click', () => edit(row)); $('pc-records').append(b); });
        $('pc-prev').disabled = page <= 1; $('pc-next').disabled = rows.length < 50;
    }
    form.addEventListener('submit', async event => {
        event.preventDefault();
        try {
            if (window.tinymce) window.tinymce.triggerSave();
            const data = {}; ['question_id', 'content_kind', 'rights_type', 'author_name', 'source_location', 'rights_basis', 'rights_expires', 'body_html'].forEach(k => { data[k] = form.elements[k].value; });
            data.question_id = Number(data.question_id); data.mcq_options = form.elements.choice_lines.value.split(/\r?\n/).map(s => s.trim()).filter(Boolean).map(s => { const match = /^([A-H])\s*[|:]\s*(.+)$/.exec(s); if (!match) throw Error('Enter each choice as A | your choice, using a unique letter A–H.'); return {key: match[1], text: match[2]}; }); if (current) data.expected_revision = current.revision;
            const row = await api('admin/practice' + (current ? '/' + current.id : ''), current ? 'PATCH' : 'POST', data);
            edit(row); tell('Draft saved. Review the saved revision and rights before approval.'); await load();
        } catch (e) { tell(e.message); }
    });
    form.addEventListener('input', event => { if (event.target.id !== 'pc-confirm') { $('pc-approve').disabled = true; $('pc-confirm').checked = false; } });
    $('pc-approve').addEventListener('click', async () => {
        if (!current || !$('pc-confirm').checked) { tell('Confirm review of the saved revision and publication rights.'); return; }
        const editor = window.tinymce && window.tinymce.get('pc_body_html'); if (editor && editor.isDirty()) { tell('Save your edited text as a draft before reviewing this revision.'); return; }
        try { const row = await api('admin/practice/' + current.id + '/approve', 'POST', {expected_revision: current.revision, rights_confirmed: true}); edit(row); tell('Revision approved. Students see it only while the academic question and rights remain available.'); await load(); } catch (e) { tell(e.message); }
    });
    function insert(html) { const editor = window.tinymce && window.tinymce.get('pc_body_html'); if (editor && !editor.isHidden()) editor.insertContent(html); else form.elements.body_html.value += html; $('pc-approve').disabled = true; $('pc-confirm').checked = false; }
    $('pc-table').onclick = () => insert('<table><caption>Calculation</caption><thead><tr><th scope="col">Item</th><th scope="col">Amount</th></tr></thead><tbody><tr><td>Replace with your authored input</td><td>0</td></tr></tbody></table>');
    $('pc-calculation').onclick = () => insert('<pre>Replace with your authored calculation\nResult = </pre>');
    $('pc-new').onclick = () => edit(null); $('pc-prev').onclick = () => { page--; load().catch(e => tell(e.message)); }; $('pc-next').onclick = () => { page++; load().catch(e => tell(e.message)); };
    load().catch(e => tell(e.message));
})();
