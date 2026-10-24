#!/usr/bin/env python3
"""Offline, metadata-only RTP research. No network, WordPress writes or publication.

Poppler's pdftotext is the only external executable. Source PDFs, working text and
outputs belong in ignored work/. Confidence describes extraction, never approval.
"""
import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / 'ca-final-command-center/templates'
CATALOGUE = ROOT / 'ca-final-command-center/data/syllabus-catalogue.json'
SUBJECTS = {'FR', 'AFM', 'AUDIT', 'DT', 'IDT', 'IBS'}
KEY = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.:-]{1,119}$')
ANSWERS = re.compile(r'^\s*SUGGESTED\s+ANSWERS?(?:/HINTS)?\s*$', re.M | re.I)
QUESTIONS = re.compile(r'^\s*QUESTIONS\s*$', re.M)
MONTHS = r'JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST|SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER'


def official_url(value):
    """Match the existing plugin policy; acquisition URLs are never CSV sources."""
    p = urlsplit(value)
    return bool(p.scheme == 'https' and p.hostname and
                any(p.hostname == h or p.hostname.endswith('.' + h) for h in ('icai.org', 'icai.nic.in'))
                and not (p.query or p.fragment or p.username or p.password or p.port))


def header(kind):
    with (TEMPLATES / (kind + '.csv')).open(newline='', encoding='utf-8-sig') as f:
        return next(csv.reader(f))


def write_csv(path, fields, rows):
    def safe(value):
        value = str(value)
        return "'" + value if value.lstrip().startswith(('=', '+', '-', '@', '\t')) else value
    with path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fields, extrasaction='raise', lineterminator='\n')
        writer.writeheader()
        writer.writerows({k: safe(r.get(k, '')) for k in fields} for r in rows)


def page_at(text, offset):
    return text.count('\f', 0, offset) + 1


def sequence(text, decimal=False):
    """Find the longest ordered numbering run; skip nested lists/restarted facts.

    This is a candidate detector, not a claim of complete subquestion extraction.
    Decimal references are IBS case.item identifiers. Options are never subparts.
    """
    pattern = r'^\s{0,16}(\d{1,2}\.\d{1,2})\s+(?=\S)' if decimal else r'^\s{0,16}(\d{1,2})[.)]\s+(?=\S)'
    hits = list(re.finditer(pattern, text, re.M))
    runs = []
    for start, match in enumerate(hits):
        if match[1] != ('1.1' if decimal else '1'):
            continue
        run = [match]
        for h in hits[start + 1:]:
            if decimal:
                case, item = map(int, run[-1][1].split('.'))
                valid = h[1] == f'{case}.{item + 1}' or h[1] == f'{case + 1}.1'
            else:
                valid = int(h[1]) == int(run[-1][1]) + 1
            if valid:
                run.append(h)
        runs.append(run)
    # Repeated fact-list numbering before actual MCQs can yield an equally long
    # subsequence. Prefer the later complete run; report all extents as candidates.
    return max(runs, key=lambda run: (len(run), run[0].start()), default=[])


def extract(text, subject):
    text = text.replace('\f', '\f\n')
    answer = ANSWERS.search(text)
    marker = QUESTIONS.search(text)
    if not marker or not answer or marker.end() >= answer.start():
        return [], ['section_boundaries_missing']
    start, end = marker.end(), answer.start()
    body = text[start:end]
    hits = sequence(body, subject == 'IBS')
    results = []
    for index, m in enumerate(hits):
        last = hits[index + 1].start() if index + 1 < len(hits) else len(body)
        chunk = body[m.start():last]
        # Store markers only. Never put question/answer prose in research exports.
        roman = sorted(set(re.findall(r'^\s{0,16}([IVX]{1,5})\.\s+', chunk, re.M)))
        letters = sorted(set(re.findall(r'^\s{0,16}\(([a-zivx]{1,5})\)\s+', chunk, re.M)))
        apattern = (r'^\s{0,16}' + re.escape(m[1]) + (r'\s+' if subject == 'IBS' else r'\.\s+'))
        # Answer tables may have two columns; preserve every candidate page.
        answer_hits = list(re.finditer(apattern, text[answer.end():], re.M))
        answer_pages = sorted(set(page_at(text, answer.end() + a.start() + len(a[0]) - len(a[0].lstrip())) for a in answer_hits))
        # A question ends immediately before the next Q marker; a heading may occur
        # in this range. Therefore page ranges are candidate extents, not exact spans.
        qstart = start + m.start()
        first_nonspace = qstart + len(m[0]) - len(m[0].lstrip())
        qend = start + last
        results.append(dict(reference=m[1], pdf_page=page_at(text, first_nonspace),
                            candidate_end_page=page_at(text, max(first_nonspace, qend - 1)),
                            answer_pages=answer_pages, subpart_candidates=roman + letters,
                            marker_confidence='medium', _private_chunk=chunk))
    return results, ([] if results else ['question_markers_missing'])


def suggest(chunk, subject, catalogue):
    """Conservative literal signals, local to one Q, from existing catalogue only.

    These are future-edition suggestions, never automatic historical mappings.
    No semantic model, repeat scoring, or invented official headings is involved.
    """
    tags = []
    for node in catalogue['nodes']:
        if subject != 'IBS' and node['subject_code'] != subject:
            continue
        if node['node_type'] not in ('chapter', 'unit') or node['heading_origin'] != 'official':
            continue
        title = node['title']
        standard = re.search(r'Ind AS\s+(\d+)', title, re.I)
        signal = None
        if standard and re.search(r'\bInd\s*AS\s*' + standard[1] + r'\b', chunk, re.I):
            signal = 'Ind AS ' + standard[1]
        else:
            label = re.sub(r'^(?:Chapter|Unit)\s*[-\dIVX]+\s*[:.-]?\s*', '', title, flags=re.I).strip()
            if len(label) >= 12 and label.casefold() in chunk.casefold():
                signal = label
        if signal:
            tags.append(dict(node_key=node['node_key'], title=title, node_type=node['node_type'],
                             edition_key=node['edition_key'], subject_code=node['subject_code'],
                             source_url=node['source_url'], signal=signal,
                             confidence='low', status='suggested_cross_edition_not_applied'))
    return tags


def check_manifest(source):
    if source.get('subject') not in SUBJECTS or not KEY.fullmatch(source.get('document_key', '')):
        raise ValueError('Invalid subject or document_key')
    if not source.get('access_authorised') or not source.get('access_evidence'):
        raise ValueError('Authorised acquisition evidence is required before opening a PDF')
    if not official_url(source.get('official_url', '')):
        raise ValueError('A direct official ICAI URL is required; private links are acquisition-only')
    if source.get('source_type') != 'rtp':
        raise ValueError('This proof of concept accepts RTPs only')
    if not source.get('title') or not source.get('attempt') or not source.get('title_evidence_page'):
        raise ValueError('Provide source title, attempt and evidence page after inspecting the source')
    if not KEY.fullmatch(source.get('edition_key', '')):
        raise ValueError('An explicit, separately provisioned historical edition key is required')


def validate_package(tables, editions, catalogue):
    """Preflight against V0.2 limits and relationships; WP preview is authoritative."""
    errors, seen = [], {}
    nodes = {n['node_key']: n for n in catalogue['nodes']}
    for kind, rows in tables.items():
        for index, row in enumerate(rows, 2):
            def error(message):
                errors.append(dict(type=kind, row=index, error=message))
            if list(row) != header(kind):
                error('Header order differs from V0.2 template')
            for k, v in row.items():
                if any(c in str(v) for c in ('\x00', '\r', '\n')):
                    error('Control/newline character in metadata')
                if str(v).lstrip().startswith(('=', '+', '-', '@', '\t')):
                    error('Spreadsheet formula prefix is not allowed in metadata')
                if k.endswith('_key') and v and not KEY.fullmatch(v):
                    error('Invalid stable key: ' + k)
                if 'url' in k and v and not official_url(v):
                    error('Non-official URL rejected')
                if 'google.com' in str(v).lower():
                    error('Private acquisition link must not enter importer CSV')
            for field, limit in {'title':190, 'question_title':190, 'page_reference':80,
                                 'question_number':40, 'subquestion_number':40,
                                 'source_location':190, 'exam_attempt':190,
                                 'issue_period':80, 'mtp_series':40}.items():
                if len(row.get(field, '').encode()) > limit:
                    error(field + ' exceeds database limit')
            if row.get('edition_key') and row['edition_key'] not in editions:
                error('Historical edition is not explicitly provisioned')
            unique = {'documents':'document_key', 'occurrences':'occurrence_key', 'answers':'answer_key'}.get(kind)
            if unique:
                key = (kind, row[unique])
                if key in seen:
                    error('Duplicate stable key')
                seen[key] = row
    docs = {r['document_key']:r for r in tables['documents']}
    questions = {r['question_key']:r for r in tables['occurrences']}
    locations, occurrences, pairs = set(), {}, set()
    for i, r in enumerate(tables['occurrences'], 2):
        error = None
        d = docs.get(r['document_key'])
        if not d or d['edition_key'] != r['edition_key']:
            error = 'Document/edition relationship mismatch'
        location = (d and d['official_url'], r['edition_key'], r['page_reference'].strip().lower(),
                    r['question_number'].strip().lower(), r['subquestion_number'].strip().lower())
        if location in locations:
            error = 'Duplicate source occurrence (not an academic repeat judgement)'
        locations.add(location)
        if r['marks'] and (r['marks_verified'] != '1' or not re.fullmatch(r'\d{1,3}(?:\.\d{1,2})?', r['marks']) or float(r['marks']) > 100):
            error = 'Marks require verified source evidence and range 0–100'
        if r['question_type'] not in {'unknown', 'practical', 'theory', 'mcq', 'case_study', 'case_scenario'}:
            error = 'Invalid question type'
        if r['chapter_key']:
            n = nodes.get(r['chapter_key'])
            if not n or n['edition_key'] != r['edition_key'] or n['node_type'] != 'chapter':
                error = 'Historical chapter mapping is unvalidated'
        if error:
            errors.append(dict(type='occurrences', row=i, error=error))
        occurrences[r['occurrence_key']] = r
    for i, r in enumerate(tables['question_topics'], 2):
        pair = (r['question_key'], r['node_key'])
        q, n = questions.get(r['question_key']), nodes.get(r['node_key'])
        if not q or not n or pair in pairs or (q['edition_key'] != n['edition_key'] and editions.get(q['edition_key'], {}).get('subject_code') != 'IBS'):
            errors.append(dict(type='question_topics', row=i, error='Duplicate or incompatible topic relationship'))
        pairs.add(pair)
    for i, r in enumerate(tables['answers'], 2):
        occurrence = occurrences.get(r['occurrence_key'])
        if (not occurrence or r['question_key'] != occurrence['question_key'] or
                r['answer_mode'] != 'official_link' or r['answer_text'] or
                not official_url(r['official_url']) or not r['source_location']):
            errors.append(dict(type='answers', row=i, error='Answer must be an official link/location for the same occurrence, without text'))
    return errors


def ordered(kind, data):
    return {k: str(data.get(k, '')) for k in header(kind)}


def legacy_run(manifest_path, output):
    manifest_path, output = Path(manifest_path).resolve(), Path(output).resolve()
    # Private by default, and impossible to accidentally export into tracked source.
    private = (ROOT / 'work').resolve()
    if private not in output.parents or output.exists():
        raise ValueError('Use a NEW output directory under ignored work/; never overwrite a research run')
    manifest = json.loads(manifest_path.read_text())
    catalogue = json.loads(CATALOGUE.read_text())
    editions = {e['edition_key']:{**e, 'review_status':'needs_review', 'publication_status':'draft'} for e in manifest.get('edition_setup', [])}
    output.mkdir(parents=True, mode=0o700)
    tables = {k:[] for k in ('hierarchy', 'documents', 'occurrences', 'question_topics', 'answers')}
    review, errors, source_report, hashes, identities = [], [], [], {}, set()
    for source in manifest['sources']:
        document = source.get('document_key', 'unknown')
        before = {kind:len(rows) for kind, rows in tables.items()}
        review_before = len(review)
        try:
            check_manifest(source)
            edition = editions.get(source['edition_key'])
            if not edition or edition['subject_code'] != source['subject'] or source['attempt'].casefold() not in edition['applicability'].casefold():
                raise ValueError('Separate historical edition setup must match subject and source attempt')
            path = (manifest_path.parent / source['path']).resolve()
            if not path.is_file() or path.is_symlink() or path.stat().st_size > 32 * 1024 * 1024:
                raise ValueError('Missing PDF or file exceeds 32 MiB')
            raw = path.read_bytes()
            if not raw.startswith(b'%PDF-'):
                raise ValueError('Source is not a PDF')
            digest = hashlib.sha256(raw).hexdigest()
            identity = (source['official_url'], source['edition_key'])
            if digest in hashes or identity in identities:
                raise ValueError('Duplicate PDF bytes or duplicate source/edition identity')
            hashes[digest], _ = document, identities.add(identity)
            result = subprocess.run(['pdftotext', '-layout', str(path), '-'], check=True, capture_output=True, timeout=60)
            text = result.stdout.decode('utf-8')
            pages = text.split('\f')
            if len(text.strip()) < 100:
                raise ValueError('No usable text layer; private OCR and visual review are required')
            found_attempts = sorted(set(re.findall(r'((?:' + MONTHS + r')\s+20\d{2})\s+EXAMINATION', text, re.I)))
            if source['attempt'].casefold() not in [a.casefold() for a in found_attempts]:
                raise ValueError('Declared exam attempt not found in PDF examination headings')
            if 'REVISION TEST PAPER' not in text.upper():
                raise ValueError('RTP document type not evidenced in PDF')
            evidence_page = source['title_evidence_page']
            if not isinstance(evidence_page, int) or evidence_page < 1 or evidence_page > len(pages) or not source.get('title_tokens'):
                raise ValueError('Invalid title evidence')
            normalized = re.sub(r'\s+', ' ', pages[evidence_page - 1]).casefold()
            if not all(token.casefold() in normalized for token in source['title_tokens']):
                raise ValueError('Actual source title tokens not found on evidence page')
            candidates, issues = extract(text, source['subject'])
            if issues:
                raise ValueError(', '.join(issues))
            expected = source.get('expected_questions')
            if expected is not None and len(candidates) != expected:
                raise ValueError(f'Question count differs from reviewed expectation: {len(candidates)} vs {expected}')
            tables['documents'].append(ordered('documents', dict(document_key=document, edition_key=source['edition_key'],
                title=source['title'], source_type='rtp', exam_attempt=source['attempt'],
                official_url=source['official_url'], issue_period=source.get('issue_period', ''))))
            for q in candidates:
                ref = q['reference']
                annotation = source.get('annotations', {}).get(ref, {})
                chunk = q.pop('_private_chunk')
                tags = suggest(chunk, source['subject'], catalogue)
                tags += annotation.get('suggested_tags', [])
                parts = annotation.get('parts') or ['']
                # Explicit part lists require source-evidence review; heuristic markers
                # alone stay in the sidecar because MCQ options are not subquestions.
                if parts != [''] and not annotation.get('parts_checked'):
                    errors.append(dict(document=document, reference=ref, error='Unreviewed parts withheld; parent reference retained'))
                    parts = ['']
                answer_pages = annotation.get('answer_pages', q['answer_pages'])
                question_page = annotation.get('pdf_page', q['pdf_page'])
                if any(not isinstance(p, int) or not 1 <= p <= len(pages) - 1 for p in answer_pages + [question_page]):
                    raise ValueError('Annotation page outside PDF')
                for part in parts:
                    part_page = annotation.get('part_pages', {}).get(part, question_page)
                    if not isinstance(part_page, int) or not 1 <= part_page < len(pages):
                        raise ValueError('Part page outside PDF')
                    key = document + '-q' + ref + ('-' + part if part else '')
                    occurrence = key + '-occ'
                    marks = annotation.get('marks', '') if len(parts) == 1 else ''
                    if marks and not annotation.get('marks_evidence'):
                        errors.append(dict(document=document, reference=ref, error='Unverified marks withheld'))
                        marks = ''
                    row = ordered('occurrences', dict(occurrence_key=occurrence, question_key=key,
                        question_title=source['subject'] + ' ' + source['attempt'] + ' RTP Q' + ref + (' (' + part + ')' if part else ''),
                        document_key=document, edition_key=source['edition_key'], chapter_key='',
                        page_reference='PDF p.' + str(part_page), question_number=ref, subquestion_number=part,
                        marks=marks, marks_verified='1' if marks else '0', question_type=annotation.get('question_type', 'unknown')))
                    tables['occurrences'].append(row)
                    warnings = ['Historical syllabus mapping pending; current-edition suggestions are not imported',
                                'Marks unavailable unless expressly evidenced; blank is not zero',
                                'Question/page extents and context require visual review',
                                'No repeat or globally-new conclusion; corpus comparison not performed']
                    if not annotation.get('location_checked'):
                        warnings.append('Location is a numbering heuristic, not human verified')
                    if len(answer_pages) != 1:
                        warnings.append('Answer locator missing or ambiguous')
                    if source.get('notes'):
                        warnings.append(source['notes'])
                    if annotation.get('notes'):
                        warnings.append(annotation['notes'])
                    if answer_pages and not annotation.get('withhold_answer'):
                        location = 'PDF p.' + ','.join(map(str, answer_pages)) + '; Q' + ref + (' (' + part + ')' if part else '')
                        tables['answers'].append(ordered('answers', dict(answer_key=key + '-answer', question_key=key,
                            occurrence_key=occurrence, answer_mode='official_link', official_url=source['official_url'], source_location=location)))
                    review.append(dict(document_key=document, subject=source['subject'], question_key=key, reference=ref,
                        subquestion=part, pdf_page=part_page, candidate_end_page=q['candidate_end_page'],
                        answer_pages=answer_pages, subpart_candidates=q['subpart_candidates'],
                        suggested_tags=tags, editorial_topics=annotation.get('editorial_topics', []),
                        editorial_subtopics=annotation.get('editorial_subtopics', []),
                        extraction_confidence='medium', classification_confidence='low',
                        review_status='needs_review', publication_status='draft', notes=warnings))
            source_report.append(dict(document_key=document, subject=source['subject'], sha256=digest,
                page_count=len(pages) - 1, text_characters=len(text), question_candidates=len(candidates),
                title=source['title'], attempt=source['attempt'], official_url=source['official_url'],
                title_evidence_page=evidence_page, observed_attempts=found_attempts,
                acquisition='Authorised private source supplied; no sharing changed', status='needs_review',
                notes=source.get('notes', '')))
        except (ValueError, OSError, subprocess.SubprocessError, UnicodeError) as e:
            # Errors omit paths and source text. A failed source contributes no rows.
            for kind in tables:
                tables[kind] = tables[kind][:before[kind]]
            review = review[:review_before]
            errors.append(dict(document=document, error=str(e) if isinstance(e, ValueError) else type(e).__name__))
    validation = validate_package(tables, editions, catalogue)
    errors.extend(validation)
    if validation:
        tables = {k:[] for k in tables}  # No invalid importer payloads are released.
    csv_manifest = []
    for kind, rows in tables.items():
        # Header-only files are explicitly not importable. Respect both row/byte caps.
        batches, current = [], []
        for row in rows:
            trial = io.StringIO(); w = csv.DictWriter(trial, header(kind)); w.writeheader(); w.writerows(current + [row])
            if len(current) == 200 or len(trial.getvalue().encode()) > 524288:
                batches.append(current); current = []
            current.append(row)
        batches.append(current)
        for i, batch in enumerate(batches, 1):
            name = f'{kind}-{i:03}.csv'
            write_csv(output / name, header(kind), batch)
            csv_manifest.append(dict(file=name, type=kind, rows=len(batch), importable=bool(batch), sha256=hashlib.sha256((output/name).read_bytes()).hexdigest()))
    (output / 'review.json').write_text(json.dumps(review, indent=2, ensure_ascii=False))
    sidecar = []
    for q in review:
        sidecar.append({**q, 'answer_pages':','.join(map(str,q['answer_pages'])),
            'suggested_tags':json.dumps(q['suggested_tags'], ensure_ascii=False),
            'editorial_topics':'; '.join(q['editorial_topics']), 'editorial_subtopics':'; '.join(q['editorial_subtopics']),
            'subpart_candidates':'; '.join(q['subpart_candidates']), 'notes':'; '.join(q['notes'])})
    fields = list(sidecar[0]) if sidecar else ['document_key','reference','review_status','publication_status']
    write_csv(output / 'review-sidecar.csv', fields, sidecar)
    write_csv(output / 'errors.csv', ['document','reference','type','row','error'], errors)
    issues = []
    for q in review:
        for note in q['notes']:
            issues.append(dict(document=q['document_key'], reference=q['reference'],
                subquestion=q['subquestion'], severity='needs_review', issue=note))
    write_csv(output / 'review-issues.csv', ['document','reference','subquestion','severity','issue'], issues)
    (output / 'edition-setup.json').write_text(json.dumps(list(editions.values()), indent=2, ensure_ascii=False))
    report = dict(pipeline_version='0.1.0', wordpress_version='0.2.0', academic_status='draft/needs_review',
        run_status='incomplete' if len(source_report) != len(manifest['sources']) or validation else 'prepared_for_review',
        sources=source_report, errors=errors, csv_files=csv_manifest,
        counts={k:len(v) for k,v in tables.items()},
        review_gaps=dict(historical_mapping_pending=len(review),
            classification_suggestions=sum(bool(q['suggested_tags']) for q in review),
            verified_marks=sum(bool(r['marks']) for r in tables['occurrences']),
            ambiguous_answer_locators=sum(len(q['answer_pages']) != 1 for q in review),
            withheld_answer_references=len(review)-len(tables['answers']),
            human_ca_approvals=0),
        duplicate_checks=dict(unique_source_bytes=len(source_report),
            unique_occurrence_locations=len(tables['occurrences']),scope='This six-file run only; no existing-site inventory or academic text comparison'),
        validation='passed' if not validation else 'failed_no_rows_released',
        comparison='No academic repetition comparison performed; byte and occurrence duplicate checks only',
        database_changes='None. No WordPress connection. Edition setup and admin preview required before any import.')
    (output / 'report.json').write_text(json.dumps(report, indent=2, ensure_ascii=False))
    data = json.dumps(dict(review=review, report=report), ensure_ascii=False).replace('<', '\\u003c').replace('&', '\\u0026')
    template = (ROOT / 'research/review.html').read_text()
    (output / 'review.html').write_text(template.replace('/*__RESEARCH_DATA__*/', data))
    print(json.dumps({'sources':len(source_report),'counts':report['counts'],'errors':len(errors),'validation':report['validation']}))
    return report


def run(manifest_path, output, **kwargs):
    """Safe default: layout engine. Legacy text engine is comparison-only."""
    from layout_pipeline import run as layout_run
    return layout_run(manifest_path, output, **kwargs)


if __name__ == '__main__':
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', help='Private local source manifest JSON')
    parser.add_argument('--output', required=True, help='New directory under ignored work/')
    parser.add_argument('--ledger', help='Persistent private owner corrections ledger')
    parser.add_argument('--previous', help='Previous private review.json for before/after comparison')
    parser.add_argument('--export-reviewed',action='store_true',help='Export at most ten fully owner-labelled draft pilot references')
    args = parser.parse_args()
    try:
        report = run(args.manifest, args.output, ledger_path=args.ledger, previous_path=args.previous, export_reviewed=args.export_reviewed)
        print(json.dumps({'sources':len(report['sources']),'records':report['records'],'bulk_gate':report['bulk_gate']}))
        raise SystemExit(1 if report['source_failures'] else 0)
    except (ValueError, KeyError, TypeError) as e:
        parser.exit(2, str(e) + '\n')
