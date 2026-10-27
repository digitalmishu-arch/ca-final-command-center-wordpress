/* global CAFCCExplorer */
(() => {
    'use strict';
    const statuses = {not_started: 'Not Started', attempted: 'Attempted', needs_revision: 'Needs Revision', completed: 'Completed'};
    const sourceLabels = {rtp: 'RTP', mtp: 'MTP', exam: 'Examination', study_material: 'Study material', case_study: 'Case study', other: 'Other'};
    const node = (tag, text, cls) => { const n = document.createElement(tag); if (text !== undefined) n.textContent = text; if (cls) n.className = cls; return n; };
    const option = (value, label) => { const n = node('option', label); n.value = value; return n; };
    async function api(path, body, v1 = false, practice = false) {
        const v9=path.startsWith('v9/');if(v9)path=path.slice(3);
        const [route, query = ''] = path.split('?');
        const target = new URL((v9?CAFCCExplorer.library:practice ? CAFCCExplorer.practice : v1 ? CAFCCExplorer.v1 : CAFCCExplorer.url) + route);
        new URLSearchParams(query).forEach((value, key) => target.searchParams.set(key, value));
        const response = await fetch(target, {method: body ? 'PUT' : 'GET', credentials: 'same-origin', cache: 'no-store', headers: {'X-WP-Nonce': CAFCCExplorer.nonce, 'Content-Type': 'application/json'}, body: body ? JSON.stringify(body) : undefined});
        const data = await response.json();
        if (!response.ok) throw new Error(data.message || 'The request failed. Reload and try again.');
        return data;
    }
    function link(url, label, verifiedMirror = false, ownerPublic = false) {
        const u = new URL(url);
        const drive=u.hostname==='drive.google.com'&&/^\/file\/d\/[A-Za-z0-9_-]{10,120}\/view$/.test(u.pathname)&&ownerPublic;
        if (u.protocol !== 'https:' || (!/(^|\.)(icai\.org|icai\.nic\.in)$/.test(u.hostname) && !verifiedMirror&&!drive) || (/(^|\.)(drive|docs)\.google\.com$/.test(u.hostname)&&!drive)) return node('span', 'Official source unavailable');
        const a = node('a', label, 'cc-source-link'); a.href = u.href; a.target = '_blank'; a.rel = 'noopener noreferrer'; return a;
    }
    document.querySelectorAll('[data-cafcc-explorer]').forEach(root => {
        const readerOnly=root.hasAttribute('data-reader-only');
        const fields = Object.fromEntries([...root.querySelectorAll('[data-filter]')].map(n => [n.dataset.filter, n]));
        const chain = ['subject_id', 'edition_id', 'chapter_id', 'unit_id', 'topic_id', 'subtopic_id'];
        const jump = node('button', 'Filters ↑', 'cc-mobile-filters'); jump.type = 'button';
        jump.addEventListener('click', () => root.querySelector('.cc-filters').scrollIntoView({behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'start'})); root.append(jump);
        if ('IntersectionObserver' in window) { const observer = new IntersectionObserver(entries => { jump.hidden = entries[0].isIntersecting; }); observer.observe(root.querySelector('.cc-filters')); }
        const feedback = root.querySelector('.cc-feedback'), list = root.querySelector('.cc-question-list'), summary = root.querySelector('.cc-summary'), pager = root.querySelector('.cc-pagination');
        const savedParams=new URLSearchParams(location.search);for(const [key,f] of Object.entries(fields)){const value=savedParams.get(key);if(value===null)continue;if(f.type==='checkbox')f.checked=value==='1';else{if(f.tagName==='SELECT'&&![...f.options].some(o=>o.value===value))f.append(option(value,'Restoring selection…'));f.value=value;}}
        let page = Math.max(1,Number(savedParams.get('page'))||1), generation = 0, scope = savedParams.get('scope')==='practice'?'practice':'browse';
        const tell = (message, error = false) => { feedback.textContent = message; feedback.classList.toggle('cc-error', error); };
        function params() {
            const p = new URLSearchParams({page: String(page),scope});
            Object.entries(fields).forEach(([key, field]) => { if (field.type === 'checkbox') { if (field.checked) p.set(key, '1'); } else if (field.value.trim()) p.set(key, field.value.trim()); });
            if(readerOnly)return p.toString();if(root.dataset.view==='practice')p.set('personal',fields.personal?.value||'all');const address=new URL(location.href);for(const key of ['page','scope',...Object.keys(fields)])address.searchParams.delete(key);p.forEach((v,k)=>{if(k!=='private_tag')address.searchParams.set(k,v);});history.replaceState(null,'',address);return p.toString();
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
                const empty = node('section', undefined, 'cc-empty'); empty.append(node('span', 'A CLEAR START', 'cc-eyebrow'), node('h4', 'Your question library is taking shape'), node('p', root.dataset.view==='practice'?'No eligible questions match your saved practice view yet. Bookmark a published question or save a practice status to begin.':'No verified questions available yet. This reviewed syllabus path remains available to browse. Try another selection or return after question review.'));
                list.append(empty);
            }
            data.items.forEach(q => {
                const card = node('article', undefined, 'cc-question');
                card.dataset.subject = q.subject_code;
                card.dataset.questionId = q.id;
                const head = node('div', undefined, 'cc-card-top'); head.append(node('span', q.subject_code, 'cc-subject cc-subject-' + q.subject_code.toLowerCase()), node('span', q.stable_key, 'cc-stable-id'));
                const citations=node('div',undefined,'cc-source-citations');(q.source_citations||[]).forEach(c=>{const location=c.page?.match(/\d+/)?.[0],target=new URL(c.url);if(location&&c.page_jump_supported!==false&&!c.owner_public_copy)target.hash='page='+location;const a=link(target.href,c.authored?'Independently authored example · official syllabus background':c.label+(c.owner_public_copy?' · PDF page '+(c.page||'see source'):c.hosting_label==='Owner-verified ICAI mirror'?' · Verified mirror':''),c.hosting_label==='Owner-verified ICAI mirror',c.owner_public_copy===true);a.title=c.hosting_label||'Verified source PDF';a.classList.add('cc-official-citation');citations.append(a);});card.append(citations);
                card.append(head, node('h4', q.title), node('p', q.chapter_title + ' · ' + q.syllabus_version, 'cc-meta'));
                const tags = node('div', undefined, 'cc-tags');
                q.classifications.forEach(t => tags.append(node('span', t.title + (t.heading_origin === 'editorial' ? ' · Editorial' : ' · ICAI'), 'cc-tag')));
                (q.academic_tags||[]).filter(t=>t.kind==='standard'||t.kind==='concept'||t.kind==='owner_tag').forEach(t=>{const chip=node('button',t.label,'cc-tag');chip.type='button';chip.title='Provisional academic search tag';chip.onclick=()=>{fields.search.value=t.label;page=1;refresh();};tags.append(chip);});card.append(tags);if(q.academic_status)card.append(node('p',q.academic_status,'cc-meta'));if(q.answer_status==='pending')card.append(node('p','Answer Pending — this question is available while its solution is checked.','cc-meta'));
                if (q.practice_content) {
                    const content = q.practice_content, question = node('details', undefined, 'cc-question-content'); question.open = true;
                    const body = node('div', undefined, 'cc-rich-content');
                    // Only rights-reviewed HTML from the server's explicit allowlist.
                    body.innerHTML = content.body_html;
                    question.append(node('summary', 'Question'), node('p', content.rights_label + ' · ' + content.author_name + (content.attribution?' · '+content.attribution:''), 'cc-credit'), body);
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
                    const details = [o.exam_attempt,o.document_section ? 'Section ' + o.document_section : '', o.issue_period, o.mtp_series ? 'Series ' + o.mtp_series : '', o.page_reference ? 'Page ' + o.page_reference : '', 'Q ' + o.question_number + (o.subquestion_number ? ' (' + o.subquestion_number + ')' : ''), o.marks !== null ? o.marks + ' verified marks' : ''].filter(Boolean);
                    source.append(node('p', details.join(' · '), 'cc-meta'), link(o.official_url, o.source_type==='other'&&q.practice_content?.rights_label==='Independently authored'?'Official ICAI background resource':(o.owner_public_copy?'Open Google Drive source PDF':q.source_citations?.find(c=>c.occurrence_id===Number(o.id))?.hosting_label==='Owner-verified ICAI mirror'?'Open Verified Mirror PDF':'Open Official Question Source'),q.source_citations?.find(c=>c.occurrence_id===Number(o.id))?.hosting_label==='Owner-verified ICAI mirror',o.owner_public_copy===true)); sources.append(source);
                });
                card.append(sources);
                const actions = node('div', undefined, 'cc-card-actions'), answerButton = node('button', 'Show Answer', 'cc-secondary'), panel = node('div', undefined, 'cc-answer-panel');
                answerButton.type = 'button'; panel.id = 'cc-answer-' + q.id + '-' + Math.random().toString(16).slice(2); panel.hidden = true; answerButton.setAttribute('aria-controls', panel.id); answerButton.setAttribute('aria-expanded', 'false');
                panel.setAttribute('aria-live', 'polite');
                let answerGeneration=0;const closeAnswer=()=>{answerGeneration++;panel.hidden=true;panel.replaceChildren();answerButton.textContent='Show Answer';answerButton.setAttribute('aria-expanded','false');answerButton.disabled=false;panel.removeAttribute('aria-busy');};card.addEventListener('cafcc:hideanswer',closeAnswer);
                answerButton.addEventListener('click', async () => {
                    if (!panel.hidden) { closeAnswer(); return; }const answerToken=++answerGeneration;
                    panel.hidden = false; answerButton.textContent = 'Hide Answer'; answerButton.setAttribute('aria-expanded', 'true'); panel.setAttribute('aria-busy', 'true');
                    panel.replaceChildren(node('p', 'Loading reviewed answer references…')); answerButton.disabled = true;
                    try {
                        const result = await api('answers/' + q.id + (q.occurrence_id ? '?occurrence_id=' + q.occurrence_id : ''));if(answerToken!==answerGeneration)return; panel.replaceChildren();
                        if(result.notice)panel.append(node('p',result.notice,'cc-meta'));if (!result.items.length) panel.append(node('p', result.empty_message));
                        result.items.forEach(a => {
                            if (a.mode === 'permitted_html') { const body = node('div', undefined, 'cc-rich-content'); body.innerHTML = a.body_html; panel.append(node('p', a.rights_label + ' · ' + a.author_name + (a.attribution?' · '+a.attribution:'') + (a.source_location ? ' · ' + a.source_location : ''), 'cc-credit'), body);if(a.official_url)panel.append(link(a.official_url,(a.owner_public_copy?'Google Drive answer PDF':a.hosting_label==='Owner-verified ICAI mirror'?'Verified mirror answer source':'Official answer source')+' · '+(a.verified_page||a.source_location),a.hosting_label==='Owner-verified ICAI mirror',a.owner_public_copy===true)); }
                            else if (a.mode === 'official_link') panel.append(node('p', 'Official answer · ' + a.source_location), link(a.official_url, 'View Official Answer'+(a.verified_page?' · PDF page '+a.verified_page:''),false,a.owner_public_copy===true));
                            else panel.append(node('strong', a.rights_label), node('p', a.answer_text, 'cc-solution-text'));
                        });
                    } catch (e) {if(answerToken===answerGeneration)panel.replaceChildren(node('p', e.message, 'cc-error')); }
                    finally { if(answerToken===answerGeneration){answerButton.disabled = false; panel.removeAttribute('aria-busy');} }
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
                progressLabel.append(select); const buttons = node('div', undefined, 'cc-action-buttons'); buttons.append(answerButton, bookmark); actions.append(buttons, progressLabel); card.append(actions, panel, notes); list.append(card);document.dispatchEvent(new CustomEvent('cafcc:card',{detail:{card,q}}));
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
                    fill('edition_id', data.editions.filter(e => !fields.subject_id.value || fields.subject_id.selectedOptions[0]?.textContent.startsWith('IBS') || String(e.subject_id) === fields.subject_id.value), 'All available editions', e => e.title);
                    fields.edition_id.disabled = false;
                    fill('exam_attempt', data.exam_attempts, 'All available attempts', s => s + (data.attempt_metadata?.find(a=>a.value===s)?.has_questions?' · Practice available':' · No verified questions yet')); fill('source_type', data.source_types, 'All available sources', s => sourceLabels[s] || s);
                    await Promise.all(['chapter', 'unit', 'topic', 'subtopic'].map(async type => {
                        const key = type + '_id', filter = new URLSearchParams(params()); filter.set('type', type);filter.set('scope',scope); const levels=['chapter','unit','topic','subtopic'];levels.slice(levels.indexOf(type)).map(k=>k+'_id').concat(['search']).forEach(k => filter.delete(k));
                        const term = root.querySelector('[data-facet-search="' + key + '"]').value; if (term) filter.set('term', term);
                        const result = await api('concepts?' + filter); if (token !== generation) return;
                        const old = fields[key].selectedOptions[0], value = fields[key].value;
                        fill(key, result.items, 'Any available ' + type, n => n.title + ' · ' + n.subject_code + ' · ' + n.edition_title + (n.has_questions?'':' · No verified questions yet'));
                        if (value && ![...fields[key].options].some(o => o.value === value) && old) { fields[key].append(old.cloneNode(true)); fields[key].value = value; }
                        fields[key].disabled = false; fields[key]._concepts = result.items;
                    }));
                    root.querySelector('.cc-edition-note').textContent = 'Start with any filter. Browse Syllabus includes source-backed and owner-authorised provisional headings without questions; Practice Questions uses eligible occurrences. Some chapters have no numbered ICAI unit.';
                }
                drawChips();
                await standardFacets(token);
                const [questions, counts] = await Promise.all([api('questions?' + params()), api('summary?' + params())]); if (token !== generation) return;
                drawQuestions(questions); drawSummary(counts); tell('');
            } catch (e) { if (token === generation) tell(e.message, true); }
            finally { if (token === generation) root.removeAttribute('aria-busy'); }
        }
        async function standardFacets(token){
            if(readerOnly)return;const p=new URLSearchParams(params());p.delete('search');const [s,c]=await Promise.all([api('v9/standards?'+p),api('v9/standard-concepts?'+p)]);if(token!==generation)return;
            const currentStandard=fields.standard.value,currentConcept=fields.concept.value;
            fill('standard',s.items,'All tagged standards',n=>n.label+' · '+n.questions+' questions');
            fill('concept',c.items,'All matching concepts',n=>n.label+' · '+n.origin+' · '+n.questions+' questions');
            if(currentConcept&&![...fields.concept.options].some(o=>o.value===currentConcept))fields.concept.value='';
            if(currentStandard!==fields.standard.value)drawChips();
        }
        fields.standard.addEventListener('change',()=>{fields.concept.value='';['chapter_id','unit_id','topic_id','subtopic_id'].forEach(k=>fields[k].value='');page=1;refresh();});
        fields.concept.addEventListener('change',()=>{page=1;refresh(false);});
        const standardInput=root.querySelector('[data-standard-search]'),standardResults=root.querySelector('[data-standard-suggestions]');let standardTimer,standardGeneration=0;
        standardInput.addEventListener('input',()=>{clearTimeout(standardTimer);const stamp=++standardGeneration;standardTimer=setTimeout(async()=>{try{const p=new URLSearchParams(params());p.set('term',standardInput.value);p.delete('search');const d=await api('v9/standards?'+p);if(stamp!==standardGeneration)return;standardResults.replaceChildren();for(const item of d.items){const b=node('button',item.label+' · '+item.questions+' questions');b.type='button';b.setAttribute('role','option');b.onclick=()=>{const subject=[...fields.subject_id.options].find(o=>o.textContent.startsWith(item.subject_code+' —'));if(subject)fields.subject_id.value=subject.value;fields.edition_id.value='';['chapter_id','unit_id','topic_id','subtopic_id'].forEach(k=>fields[k].value='');if(![...fields.standard.options].some(o=>o.value===item.code))fields.standard.append(option(item.code,item.label));fields.standard.value=item.code;fields.concept.value='';fields.search.value='';standardResults.replaceChildren();standardInput.value=item.label;standardInput.setAttribute('aria-expanded','false');page=1;refresh();};standardResults.append(b);}if(!d.items.length)standardResults.append(node('p','No eligible published questions have this standard under the selected filters.'));standardInput.setAttribute('aria-expanded','true');}catch(e){tell(e.message,true);}},250);});
        standardInput.addEventListener('keydown',e=>{if(e.key==='ArrowDown'){e.preventDefault();standardResults.querySelector('button')?.focus();}if(e.key==='Escape'){standardResults.replaceChildren();standardInput.setAttribute('aria-expanded','false');}});
        function drawChips() {
            const chips = root.querySelector('.cc-filter-chips'); chips.replaceChildren();
            Object.entries(fields).forEach(([key, f]) => { if (key==='personal'||!f.value || (f.type === 'checkbox' && !f.checked)) return;
                const text = f.type === 'checkbox' ? 'Bookmarks' : f.tagName === 'SELECT' ? f.selectedOptions[0]?.textContent : f.value;
                const chip = node('button', text + ' ×', 'cc-chip'); chip.type = 'button'; chip.setAttribute('aria-label', 'Remove ' + text);
                chip.addEventListener('click', () => { if (f.type === 'checkbox') f.checked = false; else f.value = ''; page = 1; refresh(); }); chips.append(chip);
            });
        }
        function chooseConcept(item) {
            fields.standard.value='';fields.concept.value='';standardInput.value='';standardResults.replaceChildren();
            if(!fields.subject_id.selectedOptions[0]?.textContent.startsWith('IBS'))fields.subject_id.value = item.subject_id; if(![...fields.edition_id.options].some(o=>o.value===String(item.edition_id)))fields.edition_id.append(option(item.edition_id,item.edition_title)); fields.edition_id.value = item.edition_id; fields.search.value='';
            ['chapter_id','unit_id','topic_id','subtopic_id'].forEach(k => { fields[k].value = ''; });
            item.ancestors.forEach(a => { const f = fields[a.type + '_id']; if (f) { if (![...f.options].some(o => o.value === String(a.id))) f.append(option(a.id, a.title)); f.value = a.id; } });
            root.querySelector('.cc-selected-path').textContent = item.subject_code + ' · ' + item.edition_title + ' → ' + item.ancestors.map(a => a.title).join(' → ');
            root.querySelector('.cc-concept-results').replaceChildren(); root.querySelector('.cc-concept-input').setAttribute('aria-expanded','false'); page = 1; refresh();
        }
        chain.forEach(key => fields[key].addEventListener('change', () => {
            if (['subject_id','edition_id'].includes(key)) {
                ['chapter_id','unit_id','topic_id','subtopic_id'].forEach(k => { fields[k].value = ''; }); if (key === 'subject_id') fields.edition_id.value = '';
            } else { const item = (fields[key]._concepts || []).find(n => String(n.id) === fields[key].value); if (item) { chooseConcept(item); return; } }
            page = 1; refresh();
        }));
        let conceptTimer, conceptGeneration = 0;
        const input = root.querySelector('.cc-concept-input'), results = root.querySelector('.cc-concept-results');
        input.addEventListener('input', () => { clearTimeout(conceptTimer); const generation = ++conceptGeneration; conceptTimer = setTimeout(async () => {
            results.replaceChildren(); if (input.value.trim().length < 2) { input.setAttribute('aria-expanded','false'); return; }
            try { const result = await api('concepts?scope='+scope+'&term=' + encodeURIComponent(input.value.trim())); if (generation !== conceptGeneration) return;
                result.items.forEach(item => { const button = node('button', item.title + ' · ' + item.subject_code + ' · ' + item.edition_title+(item.has_questions?'':' · No verified questions yet')); button.type = 'button'; button.setAttribute('role','option'); button.addEventListener('click', () => chooseConcept(item)); results.append(button); });
                (result.tag_suggestions||[]).forEach(item=>{const b=node('button',item.label+' · '+item.subject_code+' · '+item.edition_title+' · Suggested search tag');b.type='button';b.setAttribute('role','option');b.onclick=()=>{fields.search.value=item.label;fields.subject_id.value=item.subject_id;if(![...fields.edition_id.options].some(o=>o.value===String(item.edition_id)))fields.edition_id.append(option(item.edition_id,item.edition_title));fields.edition_id.value=item.edition_id;['chapter_id','unit_id','topic_id','subtopic_id'].forEach(k=>fields[k].value='');results.replaceChildren();input.setAttribute('aria-expanded','false');page=1;refresh();};results.append(b);});
                if (!result.items.length&&!(result.tag_suggestions||[]).length) results.append(node('p','No reviewed syllabus path matches yet. Unreviewed drafts stay private.')); input.setAttribute('aria-expanded','true');
            } catch(e) { tell(e.message,true); }
        }, 250); });
        input.addEventListener('keydown', e => { if (e.key === 'ArrowDown') { e.preventDefault(); results.querySelector('button')?.focus(); } if (e.key === 'Escape') { results.replaceChildren(); input.setAttribute('aria-expanded','false'); } });
        results.addEventListener('keydown', e => { const buttons=[...results.querySelectorAll('button')], i=buttons.indexOf(document.activeElement); if(e.key==='ArrowDown'||e.key==='ArrowUp'){e.preventDefault();buttons[(i+(e.key==='ArrowDown'?1:buttons.length-1))%buttons.length]?.focus();}if(e.key==='Escape'){results.replaceChildren();input.focus();input.setAttribute('aria-expanded','false');} });
        root.querySelectorAll('[data-facet-search]').forEach(search => { let timer; search.addEventListener('input', () => { clearTimeout(timer); timer = setTimeout(() => refresh(),300); }); });
        ['exam_attempt', 'source_type','mtp_series','practice_status',...(fields.personal?['personal']:[])].forEach(key => fields[key].addEventListener('change', () => { if(key==='mtp_series'&&fields.mtp_series.value)fields.source_type.value='mtp';if(key==='source_type'&&fields.source_type.value&&fields.source_type.value!=='mtp')fields.mtp_series.value='';page = 1; refresh(); }));
        if(fields.private_tag)fields.private_tag.addEventListener('change',()=>{page=1;refresh(false);});
        fields.bookmarked.addEventListener('change', () => { page = 1; refresh(false); });
        root.querySelector('.cc-search').addEventListener('submit', e => { e.preventDefault(); page = 1; refresh(false); });
        root.querySelector('.cc-reset').addEventListener('click', () => { Object.values(fields).forEach(f => { if (f.type === 'checkbox') f.checked = false; else f.value = f===fields.personal?'all':''; }); root.querySelectorAll('[data-facet-search],.cc-concept-input,[data-standard-search]').forEach(f => { f.value=''; }); results.replaceChildren();standardResults.replaceChildren(); root.querySelector('.cc-selected-path').textContent=''; page = 1; refresh(); });
        root.querySelectorAll('[data-scope]').forEach(b=>b.addEventListener('click',()=>{scope=b.dataset.scope;root.querySelectorAll('[data-scope]').forEach(n=>n.setAttribute('aria-pressed',String(n===b)));results.replaceChildren();input.setAttribute('aria-expanded','false');page=1;refresh();}));
        root.querySelectorAll('[data-scope]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.scope===scope)));
        document.addEventListener('cafcc:activity',()=>{if(!readerOnly&&root.isConnected)api('summary?'+params()).then(drawSummary).catch(()=>{});});
        if(readerOnly){root.addEventListener('cafcc:open-reader',event=>{const q=event.detail;drawQuestions({items:[q],total:1,per_page:1,page:1});root.querySelector('.cc-pagination').hidden=true;root.dispatchEvent(new CustomEvent('cafcc:reader-ready',{detail:q}));});}else refresh();
    });
})();
