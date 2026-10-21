/* global CAFCCStudent */
(() => {
    'use strict';
    const labels = {not_started: 'Not Started', attempted: 'Attempted', needs_revision: 'Needs Revision', completed: 'Completed'};
    const el = (tag, text, cls) => {
        const node = document.createElement(tag);
        if (text !== undefined) node.textContent = text;
        if (cls) node.className = cls;
        return node;
    };
    async function api(path, method = 'GET', body) {
        const response = await fetch(CAFCCStudent.url + path, {
            method, credentials: 'same-origin', cache: 'no-store',
            headers: {'X-WP-Nonce': CAFCCStudent.nonce, 'Content-Type': 'application/json'},
            body: body ? JSON.stringify(body) : undefined
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.message || 'Request failed. Reload and try again.');
        return data;
    }
    document.querySelectorAll('.cafcc-student').forEach(async root => {
        const message = root.querySelector('.cafcc-message');
        const summary = root.querySelector('.cafcc-summary');
        const subject = root.querySelector('.cafcc-subject');
        const chapter = root.querySelector('.cafcc-chapter');
        const questions = root.querySelector('.cafcc-questions');
        const pages = root.querySelector('.cafcc-pages');
        let catalog, page = 1, generation = 0;
        const error = e => { message.textContent = e.message; message.classList.add('cafcc-error'); };
        const clear = text => { message.textContent = text; message.classList.remove('cafcc-error'); };
        const option = (value, text) => { const node = el('option', text); node.value = value; return node; };
        async function loadSummary() {
            const data = await api('summary');
            summary.replaceChildren();
            if (!data.total) {
                summary.append(el('p', 'No progress summary is available yet. Verified questions will appear after administrator review.', 'cafcc-empty'));
                return;
            }
            Object.entries(labels).forEach(([key, label]) => {
                const card = el('div', undefined, 'cafcc-stat');
                card.append(el('strong', String(data.counts[key])), el('span', label));
                summary.append(card);
            });
        }
        async function loadQuestions() {
            const token = ++generation;
            clear('Loading questions…');
            pages.replaceChildren();
            questions.replaceChildren();
            try {
                const params = new URLSearchParams({page: String(page)});
                if (subject.value) params.set('subject_id', subject.value);
                if (chapter.value) params.set('chapter_id', chapter.value);
                const data = await api('questions?' + params);
                if (token !== generation) return;
                clear('');
                if (!data.items.length) questions.append(el('p', 'No verified questions are available for this selection yet.', 'cafcc-empty'));
                data.items.forEach(q => {
                    const card = el('article', undefined, 'cafcc-question');
                    card.append(el('h4', q.subject_code + ' · Question ' + q.question_number + ' — ' + q.title));
                    card.append(el('p', q.chapter_title + ' · Syllabus: ' + q.syllabus_version));
                    card.append(el('p', q.document_title + ' · ' + q.source_type.toUpperCase().replaceAll('_', ' ') + ' · ' + q.exam_attempt, 'cafcc-muted'));
                    const url = new URL(q.official_url);
                    if (url.protocol === 'https:' && /(^|\.)(icai\.org|icai\.nic\.in)$/.test(url.hostname)) {
                        const link = el('a', 'Open official source');
                        link.href = url.href; link.target = '_blank'; link.rel = 'noopener noreferrer';
                        card.append(link);
                    }
                    const label = el('label', 'Your progress');
                    const select = el('select');
                    Object.entries(labels).forEach(([key, text]) => select.append(option(key, text)));
                    select.value = q.progress_status;
                    let saved = q.progress_status;
                    select.addEventListener('change', async () => {
                        select.disabled = true;
                        try {
                            const result = await api('progress/' + q.id, 'PUT', {status: select.value});
                            saved = result.status;
                            clear('Progress saved.');
                            await loadSummary();
                        } catch (e) { select.value = saved; error(e); }
                        finally { select.disabled = false; }
                    });
                    label.append(select); card.append(label); questions.append(card);
                });
                const max = Math.max(1, Math.ceil(data.total / data.per_page));
                const prev = el('button', 'Previous'); const next = el('button', 'Next');
                prev.type = next.type = 'button'; prev.disabled = page <= 1; next.disabled = page >= max;
                prev.addEventListener('click', () => { page--; loadQuestions(); });
                next.addEventListener('click', () => { page++; loadQuestions(); });
                pages.append(prev, el('span', 'Page ' + page + ' of ' + max), next);
            } catch (e) { if (token === generation) error(e); }
        }
        function chapterOptions() {
            chapter.replaceChildren(option('', 'All chapters'));
            catalog.chapters.filter(c => !subject.value || String(c.subject_id) === subject.value)
                .forEach(c => chapter.append(option(c.id, c.title + ' (' + c.syllabus_version + ')')));
        }
        try {
            catalog = await api('catalog');
            catalog.subjects.forEach(s => subject.append(option(s.id, s.code + ' — ' + s.name)));
            chapterOptions();
            subject.addEventListener('change', () => { page = 1; chapterOptions(); loadQuestions(); });
            chapter.addEventListener('change', () => { page = 1; loadQuestions(); });
            await loadSummary();
            await loadQuestions();
        } catch (e) { error(e); }
    });
})();
