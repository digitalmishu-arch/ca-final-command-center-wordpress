/* global CAFCCExplorer */
(() => {
    'use strict';
    const statuses = {not_started: 'Not Started', attempted: 'Attempted', needs_revision: 'Needs Revision', completed: 'Completed'};
    const sourceLabels = {rtp: 'RTP', mtp: 'MTP', exam: 'Examination', study_material: 'Study material', case_study: 'Case study', other: 'Other'};
    const node = (tag, text, cls) => { const n = document.createElement(tag); if (text !== undefined) n.textContent = text; if (cls) n.className = cls; return n; };
    const option = (value, label) => { const n = node('option', label); n.value = value; return n; };
    async function api(path, body, v1 = false, practice = false) {
        const [route, query = ''] = path.split('?');
        const target = new URL((practice ? CAFCCExplorer.practice : v1 ? CAFCCExplorer.v1 : CAFCCExplorer.url) + route);
        new URLSearchParams(query).forEach((value, key) => target.searchParams.set(key, value));
        const response = await fetch(target, {method: body ? 'PUT' : 'GET', credentials: 'same-origin', cache: 'no-store', headers: {'X-WP-Nonce': CAFCCExplorer.nonce, 'Content-Type': 'application/json'}, body: body ? JSON.stringify(body) : undefined});
        const data = await response.json();
        if (!response.ok) throw new Error(data.message || 'The request failed. Reload and try again.');
        return data;
    }
    function link(url, label) {
        const u = new URL(url);
        if (u.protocol !== 'https:' || !/(^|\.)(icai\.org|icai\.nic\.in)$/.test(u.hostname)) return node('span', 'Official source unavailable');
        const a = node('a', label, 'cc-source-link'); a.href = u.href; a.target = '_blank'; a.rel = 'noopener noreferrer'; return a;
    }
    document.querySelectorAll('[data-cafcc-explorer]').forEach(root => {
        const fields = Object.fromEntries([...root.querySelectorAll('[data-filter]')].map(n => [n.dataset.filter, n]));
        const chain = ['subject_id', 'edition_id', 'chapter_id', 'unit_id', 'topic_id', 'subtopic_id'];
        const jump = node('button', 'Filters ↑', 'cc-mobile-filters'); jump.type = 'button';
        jump.addEventListener('click', () => root.querySelector('.cc-filters').scrollIntoView({behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'start'})); root.append(jump);
        if ('IntersectionObserver' in window) { const observer = new IntersectionObserver(entries => { jump.hidden = entries[0].isIntersecting; }); observer.observe(root.querySelector('.cc-filters')); }
        const feedback = root.querySelector('.cc-feedback'), list = root.querySelector('.cc-question-list'), summary = root.querySelector('.cc-summary'), pager = root.querySelector('.cc-pagination');
        let page = 1, generation = 0;
        const tell = (message, error = false) => { feedback.textContent = message; feedback.classList.toggle('cc-error', error); };
        function params() {
            const p = new URLSearchParams({page: String(page)});
            Object.entries(fields).forEach(([key, field]) => { if (field.type === 'checkbox') { if (field.checked) p.set(key, '1'); } else if (field.value.trim()) p.set(key, field.value.trim()); });
            return p.toString();
        }
        function fill(key, rows, first, text) {
            const select = fields[key], selected = select.value;
            select.replaceChildren(option('', first));
            rows.forEach(row => select.append(option(row.id === undefined ? row : row.id, text ? text(row) : row.title)));
            if ([...select.options].some(o => o.value === selected)) select.value = selected;
        }
        function drawSummary(data) {
            summary.replaceChildren();
            Object.entries(statuses).forEach(([key, title]) => { const card = node('div', undefined, 'cc-stat cc-' + key); card.append(node('span', title), node('strong', String(data.counts[key])), node('small', data.total ? 'In this selection' : 'Waiting for verified questions')); summary.append(card); });
        }
        function drawQuestions(data) {
            list.replaceChildren(); pager.replaceChildren();
            root.querySelector('.cc-result-count').textContent = data.total + (data.total === 1 ? ' reference' : ' references');
            if (!data.items.length) {
                const empty = node('section', undefined, 'cc-empty'); empty.append(node('span', 'A CLEAR START', 'cc-eyebrow'), node('h4', 'Your question library is taking shape'), node('p', 'No verified, published questions match this path yet. Try a broader selection or return after the academic records have been reviewed.'));
                list.append(empty);
            }
            data.items.forEach(q => {
                const card = node('article', undefined, 'cc-question');
                card.dataset.subject = q.subject_code;
                card.dataset.questionId = q.id;
                const head = node('div', undefined, 'cc-card-top'); head.append(node('span', q.subject_code, 'cc-subject cc-subject-' + q.subject_code.toLowerCase()), node('span', q.stable_key, 'cc-stable-id'));
                card.append(head, node('h4', q.title), node('p', q.chapter_title + ' · ' + q.syllabus_version, 'cc-meta'));
                const tags = node('div', undefined, 'cc-tags');
                q.classifications.forEach(t => tags.append(node('span', t.title + (t.heading_origin === 'editorial' ? ' · Editorial' : ' · ICAI'), 'cc-tag')));
                card.append(tags);
                if (q.practice_content) {
                    const content = q.practice_content, question = node('details', undefined, 'cc-question-content'); question.open = true;
                    const body = node('div', undefined, 'cc-rich-content');
                    // Only rights-reviewed HTML from the server's explicit allowlist.
                    body.innerHTML = content.body_html;
                    question.append(node('summary', 'Question'), node('p', content.rights_label + ' · ' + content.author_name, 'cc-credit'), body);
                    if (content.mcq_options.length) {
                        const choices = node('fieldset', undefined, 'cc-mcq-options'), group = 'cc-choice-' + q.id + '-' + Math.random().toString(16).slice(2); choices.append(node('legend', 'Choose an option to practise'));
                        content.mcq_options.forEach(o => { const label = node('label'), radio = node('input'); radio.type = 'radio'; radio.name = group; radio.value = o.key; label.append(radio, node('span', o.key + '. ' + o.text)); choices.append(label); }); question.append(choices);
                    }
                    card.append(question);
                } else card.append(node('p', 'Question reference · open the official source to practise this question.', 'cc-reference-note'));
                if (q.legacy_reference) card.append(node('p', 'Version 0.1 reference · connected edition/classification awaits review. Your existing progress is retained.', 'cc-note'));
                const sources = node('div', undefined, 'cc-occurrences');
                if (!q.occurrences.length && q.legacy_reference) {
                    sources.append(node('p', q.document_title + ' · ' + q.exam_attempt), link(q.official_url, 'Open Official Question Source'));
                }
                q.occurrences.forEach(o => {
                    const source = node('div', undefined, 'cc-occurrence');
                    source.append(node('span', sourceLabels[o.source_type] || o.source_type, 'cc-source-type'), node('strong', o.title));
                    const details = [o.exam_attempt, o.issue_period, o.mtp_series ? 'Series ' + o.mtp_series : '', o.page_reference ? 'Page ' + o.page_reference : '', 'Q ' + o.question_number + (o.subquestion_number ? ' (' + o.subquestion_number + ')' : ''), o.marks !== null ? o.marks + ' verified marks' : ''].filter(Boolean);
                    source.append(node('p', details.join(' · '), 'cc-meta'), link(o.official_url, 'Open Official Question Source')); sources.append(source);
                });
                card.append(sources);
                const actions = node('div', undefined, 'cc-card-actions'), answerButton = node('button', 'Show Answer', 'cc-secondary'), panel = node('div', undefined, 'cc-answer-panel');
                answerButton.type = 'button'; panel.id = 'cc-answer-' + q.id + '-' + Math.random().toString(16).slice(2); panel.hidden = true; answerButton.setAttribute('aria-controls', panel.id); answerButton.setAttribute('aria-expanded', 'false');
                panel.setAttribute('aria-live', 'polite');
                answerButton.addEventListener('click', async () => {
                    if (!panel.hidden) { panel.hidden = true; panel.replaceChildren(); answerButton.textContent = 'Show Answer'; answerButton.setAttribute('aria-expanded', 'false'); return; }
                    panel.hidden = false; answerButton.textContent = 'Hide Answer'; answerButton.setAttribute('aria-expanded', 'true'); panel.setAttribute('aria-busy', 'true');
                    panel.replaceChildren(node('p', 'Loading reviewed answer references…')); answerButton.disabled = true;
                    try {
                        const result = await api('answers/' + q.id); panel.replaceChildren();
                        if (!result.items.length) panel.append(node('p', result.empty_message));
                        result.items.forEach(a => {
                            if (a.mode === 'permitted_html') { const body = node('div', undefined, 'cc-rich-content'); body.innerHTML = a.body_html; panel.append(node('p', a.rights_label + ' · ' + a.author_name + (a.source_location ? ' · ' + a.source_location : ''), 'cc-credit'), body); }
                            else if (a.mode === 'official_link') panel.append(node('p', 'Official answer · ' + a.source_location), link(a.official_url, 'View Official Answer'));
                            else panel.append(node('strong', a.rights_label), node('p', a.answer_text, 'cc-solution-text'));
                        });
                    } catch (e) { panel.replaceChildren(node('p', e.message, 'cc-error')); }
                    finally { answerButton.disabled = false; panel.removeAttribute('aria-busy'); }
                });
                const progressLabel = node('label', 'Practice status'), select = node('select'); Object.entries(statuses).forEach(([key, text]) => select.append(option(key, text))); select.value = q.progress_status;
                let saved = q.progress_status;
                select.addEventListener('change', async () => {
                    select.disabled = true;
                    try { const result = await api('progress/' + q.id, {status: select.value}, true); saved = result.status; tell('Your progress is saved.'); drawSummary(await api('summary?' + params())); }
                    catch (e) { select.value = saved; tell(e.message, true); }
                    finally { select.disabled = false; }
                });
                const bookmark = node('button', q.notebook.bookmarked ? '★ Bookmarked' : '☆ Bookmark', 'cc-secondary cc-bookmark'); bookmark.type = 'button'; bookmark.setAttribute('aria-pressed', String(q.notebook.bookmarked));
                bookmark.addEventListener('click', async () => { bookmark.disabled = true; try { const saved = await api('notebook/' + q.id, {bookmarked: bookmark.getAttribute('aria-pressed') !== 'true'}, false, true); bookmark.setAttribute('aria-pressed', String(saved.bookmarked)); bookmark.textContent = saved.bookmarked ? '★ Bookmarked' : '☆ Bookmark'; tell('Your bookmark is saved.'); } catch (e) { tell(e.message, true); } finally { bookmark.disabled = false; } });
                const notes = node('details', undefined, 'cc-private-notes'), noteLabel = node('label', 'Your private note'), noteText = node('textarea'), saveNote = node('button', 'Save my note', 'cc-secondary'); noteText.value = q.notebook.note_text; noteText.maxLength = 10000; noteText.rows = 4; saveNote.type = 'button'; noteLabel.append(noteText); notes.append(node('summary', 'My private notes'), noteLabel, saveNote);
                saveNote.addEventListener('click', async () => { saveNote.disabled = true; try { await api('notebook/' + q.id, {note_text: noteText.value}, false, true); tell('Your private note is saved.'); } catch (e) { tell(e.message, true); } finally { saveNote.disabled = false; } });
                progressLabel.append(select); const buttons = node('div', undefined, 'cc-action-buttons'); buttons.append(answerButton, bookmark); actions.append(buttons, progressLabel); card.append(actions, panel, notes); list.append(card);
            });
            const max = Math.max(1, Math.ceil(data.total / data.per_page)), prev = node('button', 'Previous', 'cc-secondary'), next = node('button', 'Next', 'cc-secondary');
            prev.type = next.type = 'button'; prev.disabled = page <= 1; next.disabled = page >= max;
            prev.addEventListener('click', () => { page--; refresh(false); }); next.addEventListener('click', () => { page++; refresh(false); });
            pager.append(prev, node('span', 'Page ' + page + ' of ' + max), next);
        }
        async function refresh(loadCatalog = true) {
            const token = ++generation; tell('Loading verified references…'); root.setAttribute('aria-busy', 'true'); list.replaceChildren(); pager.replaceChildren();
            try {
                if (loadCatalog) {
                    const data = await api('catalog?' + params()); if (token !== generation) return;
                    fill('subject_id', data.subjects, 'All subjects', s => s.code + ' — ' + s.name);
                    fill('edition_id', data.editions, 'Choose an edition', e => e.title);
                    fields.edition_id.disabled = !fields.subject_id.value || !data.editions.length;
                    if (fields.subject_id.value && !fields.edition_id.value && data.editions.length === 1) { fields.edition_id.value = data.editions[0].id; await refresh(true); return; }
                    for (const [key, rows, first] of [['chapter_id', data.chapters, 'All chapters'], ['unit_id', data.units, data.units.length ? 'All listed units' : 'No separate units listed'], ['topic_id', data.topics, data.topics.length ? 'All topics' : 'No reviewed topics yet'], ['subtopic_id', data.subtopics, data.subtopics.length ? 'All subtopics' : 'No reviewed subtopics yet']]) {
                        fill(key, rows, first, n => n.title + (n.heading_origin === 'editorial' ? ' · Editorial tag' : ' · ICAI')); fields[key].disabled = !rows.length;
                    }
                    fill('exam_attempt', data.exam_attempts, 'All available attempts', s => s); fill('source_type', data.source_types, 'All available sources', s => sourceLabels[s] || s);
                    fields.exam_attempt.disabled = !data.exam_attempts.length; fields.source_type.disabled = !data.source_types.length;
                    const edition = data.editions.find(e => String(e.id) === fields.edition_id.value);
                    root.querySelector('.cc-edition-note').textContent = edition ? [edition.edition_month ? 'Edition ' + edition.edition_month : 'Publication month not stated', edition.reprint_month ? 'Reprint ' + edition.reprint_month : '', edition.applicability].filter(Boolean).join(' · ') : 'Choose a subject and its reviewed syllabus edition. Earlier versions remain separate.';
                }
                const selectedPath = ['chapter_id', 'unit_id', 'topic_id', 'subtopic_id'].filter(key => fields[key].value).map(key => fields[key].selectedOptions[0].textContent);
                root.querySelector('.cc-selected-path').textContent = selectedPath.join(' → ');
                const [questions, counts] = await Promise.all([api('questions?' + params()), api('summary?' + params())]); if (token !== generation) return;
                drawQuestions(questions); drawSummary(counts); tell('');
            } catch (e) { if (token === generation) tell(e.message, true); }
            finally { if (token === generation) root.removeAttribute('aria-busy'); }
        }
        chain.forEach((key, index) => fields[key].addEventListener('change', () => { chain.slice(index + 1).forEach(k => { fields[k].value = ''; }); page = 1; refresh(); }));
        ['exam_attempt', 'source_type'].forEach(key => fields[key].addEventListener('change', () => { page = 1; refresh(false); }));
        fields.bookmarked.addEventListener('change', () => { page = 1; refresh(false); });
        root.querySelector('.cc-search').addEventListener('submit', e => { e.preventDefault(); page = 1; refresh(false); });
        root.querySelector('.cc-reset').addEventListener('click', () => { Object.values(fields).forEach(f => { if (f.type === 'checkbox') f.checked = false; else f.value = ''; }); page = 1; refresh(); });
        refresh();
    });
})();
