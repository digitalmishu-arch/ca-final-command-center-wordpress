/* global CAFCCManager */
(() => {
    'use strict';
    const root = document.getElementById('cafcc-manager'); if (!root) return;
    const definitions = CAFCCManager.definitions, kind = root.querySelector('#cc-kind'), editor = root.querySelector('#cc-editor'), fieldBox = root.querySelector('#cc-editor-fields'), records = root.querySelector('#cc-records'), message = root.querySelector('.cc-admin-feedback');
    const choices = {review: ['needs_review', 'verified', 'rejected'], publication: ['draft', 'published'], node_type: ['module', 'chapter', 'unit', 'topic', 'subtopic'], origin: ['editorial', 'official'], source: ['exam', 'rtp', 'mtp', 'study_material', 'case_study', 'other'], question_type: ['unknown', 'practical', 'theory', 'mcq', 'case_study', 'case_scenario'], answer_mode: ['official_link', 'authored', 'licensed'], comparison: ['same_concept', 'adaptation', 'possible_repeat', 'unrelated'], mapping: ['equivalent', 'renamed', 'split', 'merged', 'removed']};
    const names = {editions: 'Syllabus editions & applicability', taxonomy: 'Modules / chapters / units / topics / subtopics', documents: 'Source documents', questions: 'Stable question records', occurrences: 'Question source occurrences', tags: 'Question-topic mappings', subject_tags: 'IBS subject mappings', answers: 'Solutions & official answer references', families: 'Question families', comparisons: 'Question comparisons', edition_mappings: 'Historical edition mappings'};
    const el = (tag, text, cls) => { const n = document.createElement(tag); if (text !== undefined) n.textContent = text; if (cls) n.className = cls; return n; };
    const label = value => value.replaceAll('_', ' ').replace(/\b\w/g, c => c.toUpperCase());
    const option = (value, text) => { const n = el('option', text); n.value = value; return n; };
    const tell = (text, bad = false) => { message.textContent = text; message.classList.toggle('cc-error', bad); };
    let cache = {}, legacy = {}, editing = 0, page = 1, busy = false, token = null;
    async function api(path, method = 'GET', body, v1 = false) {
        const [route, query = ''] = path.split('?');
        const target = new URL((v1 ? CAFCCManager.v1 : CAFCCManager.url) + route);
        new URLSearchParams(query).forEach((value, key) => target.searchParams.set(key, value));
        const response = await fetch(target, {method, credentials: 'same-origin', cache: 'no-store', headers: {'X-WP-Nonce': CAFCCManager.nonce, 'Content-Type': 'application/json'}, body: body ? JSON.stringify(body) : undefined});
        const data = await response.json(); if (!response.ok) throw new Error(data.message || 'Request failed. Reload and try again.'); return data;
    }
    function lock(value) { busy = value; root.querySelectorAll('button,input,select,textarea').forEach(n => { n.disabled = value; }); root.querySelector('#cc-commit').disabled = value || !token; }
    async function all(path, v1 = false) {
        let result, p = 1; const rows = [];
        do { result = await api(path + '?page=' + p++, 'GET', undefined, v1); rows.push(...result.items); if (p > 101 && rows.length < result.total) throw new Error('Manager picker limit reached (10,000 records).'); } while (rows.length < result.total);
        return rows;
    }
    async function load() {
        const sets = await Promise.all(Object.keys(definitions).map(async key => [key, await all('admin/' + key)])); cache = Object.fromEntries(sets);
        const old = await Promise.all(['subjects', 'documents', 'questions'].map(async key => [key, await all('admin/' + key, true)])); legacy = Object.fromEntries(old);
        const review = root.querySelector('#cc-review-edition'); review.replaceChildren(option('', 'Select edition to review'));
        cache.editions.forEach(e => review.append(option(e.id, e.title + ' · ' + e.review_status)));
        await batches();
    }
    function related(type, key) {
        if (type === 'subjects') return legacy.subjects;
        if (type === 'questions' && kind.value === 'questions' && key === 'question_id') return legacy.questions;
        if (type === 'documents' && kind.value === 'documents' && key === 'document_id') return legacy.documents;
        return cache[type] || [];
    }
    function fields(record = {}) {
        editing = record.id || 0; fieldBox.replaceChildren(); root.querySelector('#cc-edit-title').textContent = editing ? 'Edit #' + editing : 'New ' + names[kind.value];
        Object.entries(definitions[kind.value]).forEach(([key, rule]) => {
            const type = rule.replace('!', ''), wrapper = el('label', label(key)); let input;
            if (choices[type]) { input = el('select'); choices[type].forEach(c => input.append(option(c, label(c)))); }
            else if (['subjects', 'editions', 'taxonomy', 'documents', 'questions', 'occurrences', 'families'].includes(type)) {
                input = el('select'); input.append(option('', rule.endsWith('!') ? 'Select a record' : (key === 'question_id' || key === 'document_id') ? 'Create new record / no existing ID' : 'None (optional)'));
                related(type, key).forEach(r => input.append(option(r.id, '#' + r.id + ' · ' + (r.stable_key || r.node_key || r.document_key || r.occurrence_key || r.code || '') + ' ' + (r.title || r.name || ''))));
            } else if (['answer', 'rights', 'long'].includes(type)) { input = el('textarea'); input.rows = type === 'answer' ? 8 : 3; }
            else { input = el('input'); input.type = type === 'url' ? 'url' : ['position', 'bool', 'marks'].includes(type) ? 'number' : 'text'; if (type === 'month') input.placeholder = 'YYYY-MM; blank if not established'; }
            input.name = key; input.required = rule.endsWith('!') || type === 'key';
            if (type === 'position' || type === 'bool') { input.min = '0'; input.step = '1'; input.value = '0'; input.max = type === 'bool' ? '1' : '999999'; }
            if (type === 'marks') { input.min = '0'; input.max = '100'; input.step = '0.01'; }
            if (record[key] !== undefined && record[key] !== null) input.value = record[key];
            wrapper.append(input); fieldBox.append(wrapper);
        });
        const help = {taxonomy: 'Official unit headings require an ICAI source. Use Editorial for finer tags that are not exact published headings. Parent must be in the same edition. Position controls order.', documents: 'A new source requires its official HTTPS ICAI URL. To classify a Version 0.1 source without rewriting it, select its existing Document ID.', questions: 'Stable ID groups multiple source appearances. To classify an existing Version 0.1 question, choose its ID and the same primary source; the first connection adds metadata without changing the old row. Then add occurrences and topic mappings.', occurrences: 'Each official appearance is unique by document, edition, page and question/subquestion location. Leave marks blank unless verified; set Marks Verified to 1 only after checking the source.', answers: 'Official Link: provide URL and location and leave Answer Text empty. Authored/Licensed: provide your solution and clear authorship/reproduction-rights evidence. Unreviewed answers never reach students.'};
        fieldBox.append(el('p', help[kind.value] || 'Review before publishing. Historical mappings do not reassign questions or student progress.', 'cc-note'));
        if (kind.value === 'questions') {
            const edition = editor.elements.edition_id, chapter = editor.elements.chapter_node_id, primary = editor.elements.primary_subject_id;
            const update = () => { const previous = chapter.value, ed = cache.editions.find(e => String(e.id) === edition.value); if (ed) primary.value = ed.subject_id; chapter.replaceChildren(option('', 'No primary chapter (editorial case collection)')); cache.taxonomy.filter(n => n.node_type === 'chapter' && String(n.edition_id) === edition.value).forEach(n => chapter.append(option(n.id, n.title + ' · ' + n.heading_origin))); if ([...chapter.options].some(o => o.value === previous)) chapter.value = previous; };
            edition.addEventListener('change', update); update();
        }
        if (kind.value === 'taxonomy') {
            const edition = editor.elements.edition_id, subject = editor.elements.subject_id, nodeType = editor.elements.node_type, parent = editor.elements.parent_id;
            const update = () => {
                const previous = parent.value, allowed = {module: [], chapter: ['module'], unit: ['chapter'], topic: ['unit', 'chapter'], subtopic: ['topic']};
                parent.replaceChildren(option('', 'No parent (module/chapter only)'));
                cache.taxonomy.filter(r => String(r.edition_id) === edition.value && String(r.subject_id) === subject.value && allowed[nodeType.value].includes(r.node_type) && String(r.id) !== String(editing)).forEach(r => parent.append(option(r.id, r.title + ' · ' + r.node_key)));
                if ([...parent.options].some(o => o.value === previous)) parent.value = previous;
            };
            edition.addEventListener('change', () => { const ed = cache.editions.find(e => String(e.id) === edition.value); if (ed) subject.value = ed.subject_id; update(); });
            [subject, nodeType].forEach(n => n.addEventListener('change', update)); update();
        }
    }
    function draw() {
        records.replaceChildren(); const text = root.querySelector('#cc-record-search').value.toLowerCase();
        const rows = (cache[kind.value] || []).filter(r => JSON.stringify(r).toLowerCase().includes(text)); const max = Math.max(1, Math.ceil(rows.length / 30)); page = Math.min(page, max);
        rows.slice((page - 1) * 30, page * 30).forEach(r => {
            const card = el('article', undefined, 'cc-record'); card.append(el('strong', '#' + r.id + ' · ' + (r.title || r.node_key || r.answer_key || r.occurrence_key || ('Question ' + r.question_id))));
            card.append(el('p', [r.node_type, r.heading_origin, r.review_status || r.verification_status, r.publication_status, r.stable_key || r.node_key || r.document_key, r.batch_id ? 'Import batch ' + r.batch_id : ''].filter(Boolean).join(' · ')));
            const edit = el('button', 'Edit / review', 'cc-secondary'); edit.type = 'button'; edit.addEventListener('click', () => { if (!busy) { fields(r); editor.scrollIntoView({behavior: 'smooth', block: 'start'}); } }); card.append(edit); records.append(card);
        });
        if (!rows.length) records.append(el('p', 'No matching records. Create one using the form.', 'cc-note'));
        const pagination = root.querySelector('#cc-record-pages'), prev = el('button', 'Previous', 'cc-secondary'), next = el('button', 'Next', 'cc-secondary'); pagination.replaceChildren(); prev.type = next.type = 'button'; prev.disabled = page <= 1; next.disabled = page >= max;
        prev.addEventListener('click', () => { if (page > 1) { page--; draw(); } }); next.addEventListener('click', () => { if (page < max) { page++; draw(); } }); pagination.append(prev, document.createTextNode(' Page ' + page + ' of ' + max + ' '), next);
    }
    Object.keys(definitions).forEach(key => kind.append(option(key, names[key])));
    Object.keys(CAFCCManager.templates).forEach(key => root.querySelector('#cc-import-type').append(option(key, label(key))));
    root.querySelectorAll('[data-panel]').forEach(button => button.addEventListener('click', () => root.querySelectorAll('[data-pane]').forEach(pane => { pane.hidden = pane.dataset.pane !== button.dataset.panel; })));
    kind.addEventListener('change', () => { page = 1; draw(); fields(); tell(''); });
    root.querySelector('#cc-record-search').addEventListener('input', () => { page = 1; draw(); });
    root.querySelector('#cc-new').addEventListener('click', () => fields());
    editor.addEventListener('submit', async event => {
        event.preventDefault(); if (busy) return; const body = Object.fromEntries(new FormData(editor)); lock(true);
        try { await api('admin/' + kind.value + (editing ? '/' + editing : ''), editing ? 'PATCH' : 'POST', body); await load(); draw(); fields(); tell('Record saved. Stable question IDs and student progress are retained.'); }
        catch (e) { tell(e.message, true); } finally { lock(false); }
    });
    root.querySelector('#cc-review-publish').addEventListener('click', async () => {
        const id = root.querySelector('#cc-review-edition').value;
        if (!id || !root.querySelector('#cc-source-reviewed').checked) { tell('Choose an edition and confirm your source review.', true); return; }
        lock(true); try { const result = await api('admin/review-hierarchy/' + id, 'POST', {source_reviewed: true}); await load(); draw(); tell(result.published_official_headings + ' official headings published. Editorial tags remain separate drafts.'); }
        catch (e) { tell(e.message, true); } finally { lock(false); }
    });
    root.querySelector('#cc-template').addEventListener('click', () => {
        const type = root.querySelector('#cc-import-type').value, blob = new Blob(['\uFEFF' + CAFCCManager.templates[type].join(',') + '\r\n'], {type: 'text/csv;charset=utf-8'}), url = URL.createObjectURL(blob), a = el('a');
        a.href = url; a.download = 'cafcc-' + type + '-template.csv'; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
    });
    function invalidatePreview() { token = null; root.querySelector('#cc-commit').disabled = true; root.querySelector('#cc-import-preview').replaceChildren(); }
    root.querySelector('#cc-csv').addEventListener('change', invalidatePreview); root.querySelector('#cc-import-type').addEventListener('change', invalidatePreview);
    root.querySelector('#cc-preview').addEventListener('click', async () => {
        const file = root.querySelector('#cc-csv').files[0]; invalidatePreview();
        if (!file || file.size > 524288) { tell('Choose a CSV smaller than 512 KB.', true); return; }
        lock(true);
        try {
            const result = await api('admin/import/preview', 'POST', {type: root.querySelector('#cc-import-type').value, csv: await file.text()}); token = result.token;
            const preview = root.querySelector('#cc-import-preview'); preview.append(el('p', result.row_count + ' rows validated. ' + result.record_count + ' records will be created as Draft/Needs Review. Nothing committed yet.'));
            const scroll = el('div', undefined, 'cc-import-table'), table = el('table'), tr = el('tr'); Object.keys(result.preview[0]).forEach(key => tr.append(el('th', label(key)))); table.append(tr);
            result.preview.forEach(row => { const r = el('tr'); Object.values(row).forEach(value => r.append(el('td', value))); table.append(r); }); scroll.append(table); preview.append(scroll); tell('Preview ready. Check the rows, then import the draft batch.');
        } catch (e) { tell(e.message, true); } finally { lock(false); }
    });
    root.querySelector('#cc-commit').addEventListener('click', async () => {
        if (!token || busy) return; lock(true);
        try { const result = await api('admin/import/commit', 'POST', {token}); invalidatePreview(); await load(); draw(); tell('Batch #' + result.batch_id + ' imported. Review records before publication.'); }
        catch (e) { tell(e.message, true); } finally { lock(false); }
    });
    async function batches() {
        const rows = await api('admin/import/batches'), container = root.querySelector('#cc-batches'); container.replaceChildren();
        rows.forEach(b => {
            const card = el('div', undefined, 'cc-record'); card.append(el('strong', 'Batch #' + b.id + ' · ' + label(b.import_type)), el('p', b.created_at + ' UTC · ' + b.status));
            if (b.status === 'committed') {
                const withdraw = el('button', 'Withdraw batch safely', 'cc-secondary'); withdraw.type = 'button'; withdraw.addEventListener('click', async () => {
                    if (busy || !window.confirm('Withdraw this entire batch from student access, including any records you later published? Rows and student progress will be retained. Dependent resources may become unavailable.')) return;
                    lock(true); try { const result = await api('admin/import/rollback/' + b.id, 'POST', {withdraw: true}); await load(); draw(); tell(result.message); } catch (e) { tell(e.message, true); } finally { lock(false); }
                }); card.append(withdraw);
            }
            container.append(card);
        });
        if (!rows.length) container.append(el('p', 'No import batches yet.', 'cc-note'));
    }
    (async () => { lock(true); try { await load(); draw(); fields(); tell('Catalogue loaded. Bundled research remains Draft/Needs Review until approved.'); } catch (e) { tell(e.message, true); } finally { lock(false); } })();
})();
