"""Private, checkpointed FR corpus extraction. Never approves or publishes data.

Run against an authorised local inventory, not arbitrary remote URLs. Source
identity is the byte hash plus section and original reference. Each document is
committed independently to SQLite; changing the engine creates a new run while
retaining previous results. No source prose belongs in Git or a plugin build.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import html
import json
from pathlib import Path
import re
import sqlite3

import fitz
import layout_engine as layout

VERSION = 'fr-layout-3'
MONTHS = 'January February March April May June July August September October November December'.split()
_TABLE_CACHE = {}
STAMP = lambda: datetime.now(timezone.utc).isoformat()


def digest(value):
    return hashlib.sha256(value if isinstance(value, bytes) else json.dumps(value, sort_keys=True).encode()).hexdigest()


def attempt(text):
    m = re.search(r'\b(' + '|'.join(MONTHS) + r')\s*,?\s*(20\d{2})\b', text, re.I)
    return m[1].title() + ' ' + m[2] if m else ''


def identify(source, document):
    # Repeated running headers and the title, not scenario dates, identify attempt.
    first = document[0].get_text()
    headers = '\n'.join(p.get_text(clip=fitz.Rect(0, 0, p.rect.width, 140))+'\n'+p.get_text(clip=fitz.Rect(0,p.rect.height*.84,p.rect.width,p.rect.height)) for p in document)
    title = '\n'.join(first.splitlines()[:18])
    kind = 'rtp' if source['source_kind'] == 'RTP' else 'mtp' if source['source_kind'].startswith('MTP') else 'exam'
    header_labels=re.findall(r'(?:(?:FINAL(?:\s*\(NEW\))?\s+)?EXAMINATION\s*[:–-]?\s*(?:'+ '|'.join(MONTHS)+r')\s*,?\s*20\d{2}|(?:'+ '|'.join(MONTHS)+r')\s*,?\s*20\d{2}\s+EXAMINATION)',headers,re.I)
    values=[attempt(t) for t in header_labels];observed=Counter(values).most_common(1)[0][0] if values else (attempt(title) if kind=='mtp' and re.search('Mock Test Paper',title,re.I) else '')
    issue = observed if kind == 'mtp' else ''
    # An MTP issue month is not silently promoted to its target exam attempt.
    target = re.search(r'(?:FOR|TARGET)\s+(?:THE\s+)?(' + '|'.join(MONTHS) + r')\s*,?\s*(20\d{2})\s+(?:EXAM|ATTEMPT)', first, re.I)
    series = re.search(r'(?:Test Paper\s*[-–:]?\s*)?Series\s*[-–:]?\s*(I{1,3}|IV|[1-4])\b', title, re.I)
    subject = bool(re.search(r'FINANCIAL\s+REPORTING', first, re.I))
    role = 'answers' if source['source_kind'] == 'MTP answer' else 'questions_and_answers' if kind in ('rtp', 'exam') else 'questions'
    warnings = []
    if not observed: warnings.append('attempt_not_recovered_from_source_title_or_running_header')
    if not subject: warnings.append('paper_subject_not_confirmed_from_visible_title')
    if kind == 'mtp' and not target: warnings.append('mtp_target_attempt_not_established_issue_period_retained')
    if kind == 'mtp' and not series: warnings.append('mtp_series_not_printed_or_not_recovered')
    return dict(source_type=kind, role=role, attempt=(target[1].title() + ' ' + target[2]) if target else observed if kind != 'mtp' else '',
                issue_period=issue, series=series[1].upper() if series else '', subject_confirmed=subject,
                title_evidence=title, header_attempt=observed, warnings=warnings)


def all_lines(document):
    lines = []
    for p in document:
        for b in p.get_text('dict')['blocks']:
            for l in b.get('lines', []):
                spans = l['spans']; text = ''.join(s['text'] for s in spans).strip()
                if not text: continue
                main = max(spans, key=lambda s: len(s['text'])); c = main['color']
                box = [round(float(x), 2) for x in l['bbox']]
                # Keep the title/section information, exclude only running furniture.
                if box[1] < (135 if p.rect.width>590 and 'Segoe' in main['font'] else 65) and p.number > 0: continue
                if box[1] > p.rect.height * (.84 if p.rect.width>590 and 'Segoe' in main['font'] else .94): continue
                if re.match(r'^(?:FINAL.*EXAMINATION|PAPER\s*[–-]\s*1\s*:|©\s*The Institute)',text,re.I) and p.number>0:continue
                lines.append(dict(page=p.number + 1, bbox=box, text=text, font=main['font'], size=main['size'],
                                  bold=bool(main['flags'] & 16 or re.search('bold|black', main['font'], re.I)),
                                  rgb=[(c >> 16) & 255, (c >> 8) & 255, c & 255], column=0,
                                  spans=[dict(text=s['text'], bbox=list(s['bbox']), flags=s['flags']) for s in spans]))
    return sorted(lines, key=lambda l: (l['page'], round(l['bbox'][1] / 3), l['bbox'][0]))


def where(line):
    return {k: line[k] for k in ('page', 'bbox', 'column')}


def position(line): return line['page'], line['bbox'][1]


def boundaries(lines, identity):
    """Separate roles/sections before numbering. Never restart on working notes."""
    result = []; current = None; section = ''; role = identity['role']; side = 'answer' if role == 'answers' else 'question'
    expected = 1; pending = []; last_heading = None; warnings = []; scenario = []
    generic = identity['source_type'] != 'rtp'
    if generic and not re.search(r'PART\s*[–-]?\s*I\b.*(?:MCQ|Multiple)', '\n'.join(l['text'] for l in lines[:40]),re.I):section='descriptive'
    body_left = 108
    # Historical papers use a smaller page margin. Learn from repeated numbered starts.
    margins = Counter(round(l['bbox'][0]) for l in lines if re.match(r'^\d{1,2}\.(?:\s|$)', l['text']))
    if margins:
        plausible=[x for x,count in margins.items() if 50<=x<=110 and count>=3]
        body_left=min(plausible) if plausible else margins.most_common(1)[0][0]

    def end(at):
        nonlocal current
        if current:
            current['end_exclusive'] = where(at)
            current['lines'] = current.pop('_lines')
            result.append(current); current = None

    for index, line in enumerate(lines):
        t = line['text'].strip(); upper = t.upper(); change = None
        # Only standalone section headings, never a sentence describing the parts.
        if re.match(r'^(?:PART\s*[-–:]?\s*(?:I|1|A)\b|SECTION\s*[-–:]?\s*A\b)', upper) and re.search(r'MCQ|MULTIPLE CHOICE|OBJECTIVE', upper): change = 'mcq'
        if re.match(r'^(?:ANSWERS?\s+(?:OF\s+)?|SUGGESTED\s+ANSWERS?\s+)?(?:PART\s*[-–:]?\s*(?:II|2|B)\b|SECTION\s*[-–:]?\s*B\b)', upper) and re.search('DESCRIPTIVE|SUBJECTIVE', upper): change = 'descriptive'
        if upper in ('QUESTIONS', 'PART II: QUESTIONS', 'PART II : QUESTIONS') and not section: change = 'questions'
        if re.match(r'^SUGGESTED\s+(?:ANSWERS?|HINTS)|^ANSWERS?\s+(?:OF|TO)\s+PART', upper) and (identity['source_type'] == 'rtp' or role == 'answers'):
            end(pending[0] if pending else line); pending = []; last_heading = None; side = 'answer'; expected = 1
            if identity['source_type'] == 'rtp': section = 'answers'
        if change:
            end(pending[0] if pending else line); section = change; expected = 1; pending = []; last_heading = None
            if role == 'answers': side = 'answer'
            continue
        if upper in ('ANSWER','ANSWERS') and role=='questions_and_answers' and generic and current:
            ref=current['reference'];end(line);side='answer';current=dict(section=section,side=side,reference=ref,subreference='',start=where(line),heading=None,scenario_lines=[],_lines=[line],warnings=[]);continue
        if identity['source_type']=='rtp' and upper in ('SUGGESTED','ANSWERS') and index+1<len(lines) and (upper=='ANSWERS' or lines[index+1]['text'].upper()=='ANSWERS'):
            end(pending[0] if pending else line);pending=[];last_heading=None;side='answer';expected=1;section='answers';continue
        # Suggested-answer publications alternate explicit Question N / Answer N.
        explicit = re.match(r'^(Question|Answer)\s+(?:No\.?\s*)?(\d{1,2})\s*$', t, re.I)
        ref = None
        if explicit:
            side = 'question' if explicit[1].lower() == 'question' else 'answer'
            ref = explicit[2]
            if not section: section = 'descriptive'
        elif section and abs(line['bbox'][0] - body_left) < 11:
            m = re.match(r'^(\d{1,2})[.)](?:\s|$)', t)
            if m and (not generic or section != 'questions'):
                # A sequential parent start at the document margin. Numbered notes
                # are indented or belong to an already closed question sequence.
                if int(m[1]) == expected: ref = m[1]
        if ref:
            end(pending[0] if pending else line)
            if pending:
                last_heading = dict(text=' '.join(l['text'] for l in pending), spans=[{k:l[k] for k in ('text','page','bbox','font','size','bold','rgb')} for l in pending])
            pending = []
            # An explicit Answer N does not advance the next Question N counter.
            if not explicit or side == 'question': expected = int(ref) + 1
            current = dict(section=section, side=side, reference=ref, subreference='', start=where(line),
                           heading=last_heading if section != 'mcq' else None, scenario_lines=list(scenario), _lines=[line], warnings=[])
            continue
        if section and side == 'question' and (layout.styled_heading(line, layout.PROFILE) or (line['bold'] and re.match(r'^Ind(?:ian)?\s*(?:Accounting\s*)?AS\s*\d+(?:\s*[-–:].*)?$',t,re.I))) and not generic:
            # Pending heading owns the following question, even across pages.
            if not pending: end(line)
            pending.append(line); continue
        if re.match(r'^Case\s+(?:Scenario|Study)\s*[-–:]?\s*(?:[IVX\d]+)?$', t, re.I) and section == 'mcq':
            scenario = [line]
        elif scenario and current is None: scenario.append(line)
        if current: current['_lines'].append(line)
    if lines:
        last = lines[-1]; end({**last, 'bbox':[last['bbox'][0], last['bbox'][3]+1,last['bbox'][2],last['bbox'][3]+2]})
    for q in result:
        q['format'] = 'MCQ' if q['section'] == 'mcq' else 'SUBJECTIVE' if q['section'] == 'descriptive' else 'MIXED'
        if q['section'] in ('questions', 'answers'):
            text = '\n'.join(l['text'] for l in q['lines'])
            choices = set(re.findall(r'^\(?([a-dA-D])\)[ \t]*', text, re.M))
            cue = re.search(r'choose|most appropriate|multiple.choice|\bMCQ', text, re.I)
            if cue and len(choices) >= 4: q['format'] = 'MCQ'
            elif q['heading'] and not re.search('multiple choice|MCQ', q['heading']['text'], re.I): q['format'] = 'SUBJECTIVE'
            if q['format'] == 'MCQ' and q['side']=='question': q['section'] = 'mcq'
            elif q['format'] == 'SUBJECTIVE' and q['side']=='question': q['section'] = 'descriptive'
        if not generic and q['heading'] and re.search(r'multiple.choice|MCQs?',q['heading']['text'],re.I):q['format']='MCQ';q['section']='mcq' if q['side']=='question' else q['section']
        if q['format'] == 'MIXED': q['warnings'].append('question_format_not_established')
    return result, dict(body_left=body_left, profile='fr-adaptive-single-column@3', warnings=warnings)


def split_parts(q):
    """Letters alone are never an MCQ test. Keep complete parent facts for children."""
    if q['format'] == 'MCQ': return []
    candidates = []
    for i, l in enumerate(q['lines']):
        m = re.match(r'^\(([a-d])\)\s*', l['text'])
        if m and l['bbox'][0] < 165:
            candidates.append((m[1], i))
    if len(candidates) < 2 or len({x[0] for x in candidates}) != len(candidates): return []
    # Financial statements may contain lettered notes. Require operative language
    # inside each proposed independent requirement, otherwise leave the parent whole.
    children = []
    for n, (ref, i) in enumerate(candidates):
        end = candidates[n+1][1] if n+1<len(candidates) else len(q['lines'])
        rows = q['lines'][i:end]
        if not re.search(r'calculate|determine|explain|discuss|compute|advise|prepare|evaluate|account|recognis|recogniz', ' '.join(l['text'] for l in rows), re.I): return []
        children.append({**q, 'subreference':ref, 'start':where(rows[0]), 'end_exclusive':where(q['lines'][end]) if end<len(q['lines']) else q['end_exclusive'],
                         'lines':q['lines'][:candidates[0][1]] + rows, 'shared_parent':True,
                         'warnings':q['warnings'] + ['shared_parent_context_retained_independent_subpart_requires_review']})
    return children


def fidelity(source_text, rendered_text):
    token = lambda s: Counter(re.findall(r'(?<!\w)[−–-]?\(?\d[\d,]*(?:\.\d+)?\)?%?|[₹`%]|\b\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}\b', html.unescape(s)))
    before, after = token(source_text), token(rendered_text)
    missing = before-after; added = after-before
    return dict(numeric_tokens_source=sum(before.values()), missing=dict(missing), added=dict(added),
                passed=not missing and not added)


def rich(q, document):
    rows = q['lines']; blocks = []; used = set(); warnings = []
    for pn in sorted({l['page'] for l in rows}):
        page = document[pn-1]; selected=[(i,l) for i,l in enumerate(rows) if l['page']==pn]
        # Native vector/word table recognition; no invented cells or filled values.
        cache_key=(document.name,pn)
        try:
            if cache_key not in _TABLE_CACHE:_TABLE_CACHE[cache_key]=[dict(bbox=list(t.bbox),cells=t.cells,rows=t.extract()) for t in page.find_tables().tables]
            tables=_TABLE_CACHE[cache_key]
        except Exception: tables=[]; warnings.append('table_detection_failed_page_'+str(pn))
        for table in tables:
            bbox=fitz.Rect(table['bbox']); inside=[(i,l) for i,l in selected if bbox.contains(fitz.Point((l['bbox'][0]+l['bbox'][2])/2,(l['bbox'][1]+l['bbox'][3])/2))]
            if not inside: continue
            if not all(any(abs(c[1]-l['bbox'][1])<25 for c in table['cells'] if c) for _,l in inside):
                warnings.append('table_geometry_ambiguous_page_'+str(pn)); continue
            cells=table['rows']
            if len(cells)<2 or max(map(len,cells),default=0)<2: continue
            source='\n'.join(l['text'] for _,l in inside)
            check=fidelity(source,' '.join(str(c or '') for r in cells for c in r))
            if not check['passed']:
                warnings.append('table_numeric_fidelity_failed_page_'+str(pn));continue
            # Duplicate text must not be removed without cell-level fidelity.
            normal=lambda s:re.sub(r'\s+','',s)
            if normal(source)!=normal(''.join(str(c or '') for r in cells for c in r)):
                warnings.append('table_reading_order_requires_review_page_'+str(pn));continue
            used.update(i for i,_ in inside)
            blocks.append(dict(type='table',page=pn,bbox=list(bbox),rows=cells,merged_cells='not_inferred',requires_review=True))
    for i,l in enumerate(rows):
        if i in used: continue
        spans=[]
        for s in l.get('spans',[]):
            text=html.escape(s['text'])
            if s['flags']&1:text='<sup>'+text+'</sup>'
            if s['flags']&2:text='<em>'+text+'</em>'
            if s['flags']&16:text='<strong>'+text+'</strong>'
            spans.append(text)
        blocks.append(dict(type='paragraph',page=l['page'],bbox=l['bbox'],html=''.join(spans) or html.escape(l['text'])))
    blocks.sort(key=lambda b:(b['page'],b['bbox'][1],b['bbox'][0]))
    rendered=[]
    for b in blocks:
        if b['type']=='table':rendered.append('<table><tbody>'+''.join('<tr>'+''.join('<td>'+html.escape(str(c or '')).replace('\n','<br>')+'</td>' for c in r)+'</tr>' for r in b['rows'])+'</tbody></table>')
        else:rendered.append('<p>'+b['html']+'</p>')
    body='\n'.join(rendered); plain='\n'.join(l['text'] for l in rows)
    check=fidelity(plain,re.sub('<[^>]*>',' ',body))
    if not check['passed']:warnings.append('numeric_or_symbol_fidelity_failed')
    # Text columns without an accepted table must be reviewed, not called exact.
    if any(re.match(r'^[₹`(−–-]?\d[\d,.%() −–-]*$',l['text']) for l in rows) and not used:
        warnings.append('possible_unrecovered_table_or_calculation_columns')
    return dict(schema='cafcc-rich-v1',body_html=body,plain_text=plain,blocks=blocks,source_text_sha256=digest(plain.encode()),
                fidelity=check,warnings=sorted(set(warnings)),transcription_status='needs_review')


def process(inventory, output, limit=None):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(output/'checkpoints.sqlite');db.execute('PRAGMA journal_mode=WAL')
    db.execute('CREATE TABLE IF NOT EXISTS documents (file_id TEXT, source_hash TEXT, engine_hash TEXT, status TEXT, payload TEXT, updated TEXT, PRIMARY KEY(file_id,source_hash,engine_hash))')
    engine_hash=digest(Path(__file__).read_bytes()+Path(layout.__file__).read_bytes())
    done=0
    for source in inventory:
        sha=source['source_sha256'];key=(source['file_id'],sha,engine_hash)
        if db.execute('SELECT 1 FROM documents WHERE file_id=? AND source_hash=? AND engine_hash=?',key).fetchone():continue
        try:
            path=Path(source['local_path']);raw=path.read_bytes()
            if digest(raw)!=sha:raise ValueError('source_hash_changed')
            _TABLE_CACHE.clear()
            with fitz.open(path) as doc:
                identity=identify(source,doc);lines=all_lines(doc);sections,profile=boundaries(lines,identity);layout_issues=[]
                if identity['source_type']=='rtp' and any('Segoe' in l['font'] for l in lines):
                    old_lines,old_pages,old_issues,old_profile=layout.read_pdf(path)
                    old_qs,answer_lines,old_warnings,answer_starts=layout.segment(old_lines,old_profile);layout_issues=old_issues+old_warnings
                    if old_qs:
                        # Reuse corrected RTP starts/ends and exact existing IDs.
                        fallback_questions=[q for q in sections if q['side']=='question'];fallback_answers=[q for q in sections if q['side']=='answer']
                        sections=[]
                        first_answer=min([position(q['start']) for q in fallback_answers],default=(999999,999999))
                        for q in old_qs:
                            if position(q['start'])>=first_answer:continue
                            selected=[l for l in lines if position(l)>=position(q['start']) and position(l)<position(q['end_exclusive'])]
                            sections.append(dict(section=q['section'],side='question',reference=q['reference'],subreference='',start=q['start'],end_exclusive=q['end_exclusive'],heading=q['heading'],format='MCQ' if q['kind']=='mcq' else 'SUBJECTIVE' if q['section']=='descriptive' else 'MIXED',lines=selected,warnings=q['warnings']))
                        # Keep starts recovered by the adaptive profile but missed
                        # by the older pilot (for example an independent MCQ group).
                        known={(q['reference'],q['start']['page']) for q in sections}
                        for candidate in fallback_questions:
                            if (candidate['reference'],candidate['start']['page']) not in known and position(candidate['start'])<first_answer:sections.append(candidate)
                        sections+=fallback_answers
                for q in sections:
                    if q['side']=='question' and q['format']=='MIXED':
                        t='\n'.join(l['text'] for l in q['lines']); options=set(re.findall(r'^\(([a-d])\)',t,re.M))
                        if not (len(options)>=4 and re.search(r'choose|most appropriate|multiple.choice|\bMCQ',t,re.I)) and re.search(r'prepare|calculate|compute|explain|analyse|analyze|discuss|determine|elaborate|show how|journal entr|accounting treatment',t,re.I):
                            q['format']='SUBJECTIVE';q['warnings'].append('subjective_requirement_detected_without_section_heading_owner_must_confirm')
                for q in sections:
                    if q['side']=='question':
                        t='\n'.join(l['text'] for l in q['lines']);parts=re.split(r'^\(([a-d])\)\s*',t,flags=re.M)
                        option_texts=parts[2::2];keys=set(parts[1::2])
                        if keys>={'a','b','c','d'} and ('?' in parts[0] or re.search('which|what|choose|most appropriate',parts[0],re.I)) and not any(re.search(r'^(?:prepare|calculate|compute|explain|discuss|determine)\b',x.strip(),re.I) for x in option_texts):q['format']='MCQ';q['section']='mcq'
                records=[]
                for q in sections:
                    for v in [q]+split_parts(q):
                        v['warnings']=list(v['warnings'])+['layout_exception:'+issue['code'] for issue in layout_issues if issue.get('blocking') and (not issue.get('page') or v['start']['page']<=issue['page']<=v['end_exclusive']['page'])]
                        stable='R-'+layout.identity(sha,v['section'],v['reference'],v['subreference'])
                        records.append({k:v[k] for k in ('section','side','reference','subreference','start','end_exclusive','heading','format','warnings')}|
                            dict(stable_id=stable,parent_shared_context=bool(v.get('shared_parent')),content=rich(v,doc)))
                sparse=[p.number+1 for p in doc if len(p.get_text().strip())<80]
                payload=dict(source=source,identity=identity,profile=profile,records=records,pages=len(doc),
                             exceptions=layout_issues+[dict(code='scanned_or_sparse_page_requires_manual_or_ocr',page=p) for p in sparse],
                             processing_outcome='extracted_needs_review' if records else 'blocked_boundaries_not_recovered',
                             engine=VERSION,engine_hash=engine_hash,timestamp=STAMP())
        except Exception as error:payload=dict(source=source,processing_outcome='failed',exceptions=[dict(code=type(error).__name__,reason=str(error))],records=[],timestamp=STAMP())
        db.execute('INSERT INTO documents VALUES(?,?,?,?,?,?)',(*key,payload['processing_outcome'],json.dumps(payload,ensure_ascii=False),STAMP()));db.commit()
        done+=1;print(json.dumps(dict(file_id=source['file_id'],status=payload['processing_outcome'],candidates=len(payload['records']))),flush=True)
        if limit and done>=limit:break
    results=[json.loads(r[0]) for r in db.execute('SELECT payload FROM documents WHERE engine_hash=? ORDER BY file_id',(engine_hash,))]
    (output/'documents.json').write_text(json.dumps(results,ensure_ascii=False))
    return results


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('inventory');parser.add_argument('--output',required=True);parser.add_argument('--limit',type=int)
    args=parser.parse_args();path=Path(args.inventory)
    records=json.loads(path.read_text()) if path.suffix=='.json' else [json.loads(l) for l in path.read_text().splitlines() if l]
    process(records,args.output,args.limit)
