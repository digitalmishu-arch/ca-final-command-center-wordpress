"""Private layout research runner. No hosting, publication or bulk-run mode."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys

import corrections
import layout_engine as engine
import rtp_pipeline as csv_tools

ROOT=Path(__file__).resolve().parents[1]


def write_json(path, value):
    path.write_text(json.dumps(value,indent=2,ensure_ascii=False),encoding='utf-8')


def private_output(path):
    out=Path(path).resolve()
    if (ROOT/'work').resolve() not in out.parents or out.exists():
        raise ValueError('Use a new private run directory under ignored work/')
    out.mkdir(parents=True,mode=0o700)
    return out


def previous_record(records, document, section, reference, subreference):
    """Support both PR #3 and v2 sidecars without conflating restarted numbers."""
    candidates=[r for r in records if r['document_key']==document and r['reference']==reference and r.get('subreference',r.get('subquestion',''))==subreference]
    exact=[r for r in candidates if r.get('section')==section]
    legacy=[r for r in candidates if 'section' not in r]
    selected=exact or legacy
    return selected[0] if len(selected)==1 else {}


def run(manifest_path, output, ledger_path=None, previous_path=None, export_reviewed=False):
    manifest_path=Path(manifest_path).resolve();manifest=json.loads(manifest_path.read_text())
    if len(manifest['sources'])>6:raise ValueError('Reviewed-pilot gate: maximum six sources; no mass-run mode')
    out=private_output(output);stamp=datetime.now(timezone.utc).isoformat()
    code_hash=hashlib.sha256()
    for component in ('layout_engine.py','layout_pipeline.py','corrections.py','layout-profiles.json'):
        code_hash.update(component.encode()+b'\0'+(ROOT/'research'/component).read_bytes()+b'\0')
    engine_revision=dict(version='2.1.0',code_sha256=code_hash.hexdigest())
    ledger=json.loads(Path(ledger_path).read_text()) if ledger_path else {'version':1,'events':[]}
    corrections.validate(ledger)
    taxonomy=json.loads((manifest_path.parent/manifest['historical_taxonomy']).read_text())
    previous=json.loads(Path(previous_path).read_text()) if previous_path else []
    records=[];exceptions=[];sources=[];comparisons=[];private_segments=[]
    for source in manifest['sources']:
        records_before=len(records);comparison_before=len(comparisons);segments_before=len(private_segments)
        try:
            if not source.get('access_authorised') or not source.get('access_evidence'):raise ValueError('Authorised source access evidence required')
            if source.get('source_type') not in ('rtp','mtp','exam'):raise ValueError('Identify RTP, MTP or actual examination source before extraction')
            if source['source_type']=='mtp' and not source.get('mtp_series'):raise ValueError('MTP series must be retained, not guessed')
            if not csv_tools.official_url(source['official_url']):raise ValueError('Public resource must use an official ICAI URL')
            path=(manifest_path.parent/source['path']).resolve();raw=path.read_bytes()
            if len(raw)>32*1024*1024 or not raw.startswith(b'%PDF-'):raise ValueError('Invalid PDF or 32 MiB limit exceeded')
            sha=hashlib.sha256(raw).hexdigest()
            if any(s['sha256']==sha for s in sources):raise ValueError('Duplicate source bytes')
            profiles=json.loads((ROOT/'research/layout-profiles.json').read_text())
            chosen=source.get('layout_profile') or ('icai-bos-single-column@2' if source['source_type']=='rtp' else 'generic-question-paper@1')
            if chosen not in profiles:raise ValueError('Unknown layout profile/version; manual layout recovery required')
            lines,pages,issues,profile=engine.read_pdf(path,profiles[chosen])
            identification=engine.identify(lines,source)
            evidence=pages[0]['document_evidence'] if pages else {}
            identification['observed_evidence']=evidence
            identification['paper']=evidence.get('paper','');identification['issue_period']=source.get('issue_period','')
            expected_paper={'FR':'1','AFM':'2','AUDIT':'3','DT':'4','IDT':'5','IBS':'6'}.get(source['subject'])
            if not expected_paper or evidence.get('paper')!=expected_paper:raise ValueError('Subject/paper identity not confirmed from visible PDF title')
            if evidence.get('observed_type')!=source['source_type']:raise ValueError('Declared source type conflicts with visible document evidence')
            if not any(engine.norm(a)==engine.norm(source['attempt']) for a in evidence.get('attempts',[])):raise ValueError('Attempt not confirmed from examination headings; owner identification required')
            if source['source_type']=='mtp':
                roman={'i':'1','ii':'2','iii':'3','iv':'4'}
                canon=lambda v:roman.get(engine.norm(v),engine.norm(v))
                if {canon(v) for v in evidence.get('series',[])}!={canon(source['mtp_series'])}:raise ValueError('MTP series missing or ambiguous in visible source evidence')
            if evidence.get('role')=='answer_reference':raise ValueError('Answer-only document identified; pair with the exact question paper before matching')
            qs,answer_lines,seg_issues,answer_starts=engine.segment(lines,profile)
            issues+=seg_issues
            if not qs:issues.append(dict(code='question_markers_unrecovered',blocking=True))
            answer_hash=sha;answer_url=source['official_url'];answer_match_profile=profile
            pair=source.get('answer_document')
            if pair:
                if not pair.get('access_authorised') or not pair.get('access_evidence') or not csv_tools.official_url(pair.get('official_url','')):raise ValueError('Paired answer PDF requires authorised private access and an official URL')
                answer_path=(manifest_path.parent/pair['path']).resolve();answer_raw=answer_path.read_bytes()
                if len(answer_raw)>32*1024*1024 or not answer_raw.startswith(b'%PDF-'):raise ValueError('Invalid paired answer PDF')
                pair_profile=pair.get('layout_profile',chosen)
                if pair_profile not in profiles:raise ValueError('Unknown paired-answer layout profile')
                paired_lines,answer_pages,pair_issues,answer_profile=engine.read_pdf(answer_path,profiles[pair_profile])
                answer_match_profile=answer_profile
                pair_evidence=answer_pages[0]['document_evidence']
                if pair_evidence.get('paper')!=expected_paper or not any(engine.norm(a)==engine.norm(source['attempt']) for a in pair_evidence.get('attempts',[])) or pair_evidence.get('role') not in ('answer_reference','questions_and_answers'):raise ValueError('Paired answer paper/attempt/answer role does not match this question source')
                if source['source_type']=='mtp' and {canon(v) for v in pair_evidence.get('series',[])}!={canon(source['mtp_series'])}:raise ValueError('Paired MTP answer series mismatch, ambiguity or missing evidence')
                _,answer_lines,answer_issues,answer_starts=engine.segment(paired_lines,answer_profile)
                if not answer_starts:raise ValueError('Paired answer-section start not recovered safely')
                answer_hash=hashlib.sha256(answer_raw).hexdigest();answer_url=pair['official_url'];issues+=pair_issues+answer_issues
            if identification['review_required']:issues.append(dict(code='document_identification_requires_review',blocking=True))
            expected=source.get('expected_questions')
            if expected is not None and len(qs)!=expected:issues.append(dict(code='question_count_mismatch',expected=expected,detected=len(qs),blocking=True))
            for issue in issues:exceptions.append(dict(document_key=source['document_key'],**issue))
            edition=source.get('historical_edition_key','')
            for q in qs:
                # Parent records remain; independently classifiable children have
                # their own identities. Never delete/remap an existing WP question.
                variants=[q]
                for part in q['subparts']:
                    if part['ambiguous']:
                        exceptions.append(dict(document_key=source['document_key'],section=q['section'],reference=q['reference'],code='ambiguous_subpart',blocking=True));continue
                    part_lines=[l for l in lines if (l['page'],l['bbox'][1])>=(part['start']['page'],part['start']['bbox'][1]) and (l['page'],l['bbox'][1])<(part['end_exclusive']['page'],part['end_exclusive']['bbox'][1])]
                    variants.append({**q,'subreference':part['reference'],'start':part['start'],
                        'end_exclusive':part['end_exclusive'],'private_text':'\n'.join(l['text'] for l in part_lines),'subparts':[]})
                for item in variants:
                    classification=engine.classify(item,taxonomy['nodes'],source['subject'],edition)
                    # A correction binds to exact bytes, section and original ref.
                    event=corrections.applicable(ledger,sha,item['section'],item['reference'],item['subreference'])
                    state='needs_review';warnings=['Provisional academic classification; not permission to reproduce source text']+item.get('warnings',[])
                    proposed=classification
                    if event:
                        state=event['decision']
                        approved_boundary=event.get('labels',{}).get('boundary')
                        if approved_boundary and approved_boundary!=dict(start=item['start'],end_exclusive=item['end_exclusive']):
                            state='conflict';warnings.append('Previously approved boundary differs from this run; prior correction retained, explicit owner re-review required')
                        if state in ('approved','concept_approved'):
                            # Preserve automated proposal beside owner correction.
                            classification={**classification,**event.get('classification',{}),'method':'manual override'}
                        if state=='conflict':warnings.append('Conflict / Needs Owner Review')
                    if not classification.get('taxonomy_match'):warnings.append('Historical taxonomy mapping unresolved; May 2026 mapping not substituted')
                    answers=engine.answer_candidates(item,answer_lines,answer_match_profile)
                    answers=[{**a,'source_sha256':answer_hash,'official_url':answer_url} for a in answers]
                    if event and event['decision']=='approved' and 'answer_locations' in event.get('labels',{}):
                        chosen_answers=event['labels']['answer_locations']
                        if chosen_answers and all(a in answers for a in chosen_answers):answers=chosen_answers
                        elif chosen_answers!=answers:
                            state='conflict';warnings.append('Previously approved answer location/source differs; explicit owner re-review required')
                    if len(answers)!=1:warnings.append('Answer start absent or ambiguous; no verified answer location')
                    if any(i.get('blocking') for i in issues):warnings.append('Document layout/count exception requires owner boundary review')
                    if source['subject']=='FR' and item['reference']=='19':
                        warnings.append('Private archive Answer 19 predates official corrigendum; reference withheld');answers=[]
                    record=dict(question_identity=engine.identity(sha,item['section'],item['reference'],item['subreference']),
                        source_sha256=sha,document_key=source['document_key'],source_type=source['source_type'],
                        source_title=source.get('title',''),issue_period=source.get('issue_period',''),marks=None,marks_verified=False,
                        subject=source['subject'],attempt=source['attempt'],mtp_series=source.get('mtp_series',''),
                        section=item['section'],reference=item['reference'],subreference=item['subreference'],
                        start=item['start'],end_exclusive=item['end_exclusive'],heading=item['heading'],scenario=item['scenario'],
                        classification=classification,automated_proposal=proposed,answer_candidates=answers,
                        kind=item['kind'],warnings=warnings,owner_state=state,ledger_event=event,
                        review_status='needs_review',publication_status='draft',timestamp=stamp,
                        profile=dict(id=profile['id'],version=profile['version']),official_url=source['official_url'])
                    record['engine_revision']=engine_revision
                    record['layout_blocked']=any(i.get('blocking') for i in issues)
                    before=previous_record(previous,source['document_key'],item['section'],item['reference'],item['subreference'])
                    old_classification=before.get('classification',before.get('suggested_tags',[]))
                    record['existing_ai_classification']=old_classification
                    record['metric_values']=dict(boundary=dict(start=item['start'],end_exclusive=item['end_exclusive']),
                        chapter_key=next((n['node_key'] for n in classification.get('official_nodes',[]) if n['node_type']=='chapter'),None),
                        unit_topic_keys=sorted(n['node_key'] for n in classification.get('official_nodes',[]) if n['node_type'] in ('unit','topic','subtopic')),
                        answer_locations=answers)
                    comparisons.append(dict(document_key=source['document_key'],section=item['section'],reference=item['reference'],subreference=item['subreference'],
                        old=old_classification,new=classification,old_page=before.get('pdf_page',before.get('start',{}).get('page')),new_start=item['start'],
                        old_key=before.get('question_key',before.get('question_identity')),new_identity=record['question_identity'],owner_state=state))
                    private_segments.append(dict(identity=record['question_identity'],text=item['private_text'],scenario_text=item.get('private_scenario_text','')))
                    for warning in warnings:exceptions.append(dict(document_key=source['document_key'],section=item['section'],reference=item['reference'],subreference=item['subreference'],code=warning,blocking=True))
                    records.append(record)
            sources.append(dict(document_key=source['document_key'],title=source.get('title',''),official_url=source['official_url'],sha256=sha,pages=len(pages),
                identification=identification,profile=profile,questions=len(qs),answer_section_starts=answer_starts,
                notes=source.get('notes',''),timestamp=stamp,answer_source_sha256=answer_hash,answer_official_url=answer_url))
        except (ValueError,OSError) as e:
            records=records[:records_before];comparisons=comparisons[:comparison_before];private_segments=private_segments[:segments_before]
            exceptions.append(dict(document_key=source.get('document_key'),code=str(e),blocking=True))
    metrics=corrections.metrics(records,ledger)
    applied={(r['source_sha256'],r['section'],r['reference'],r['subreference']) for r in records}
    for event in ledger['events']:
        if (event['source_sha256'],event['section'],event['reference'],event.get('subreference','')) not in applied:
            exceptions.append(dict(source_sha256=event['source_sha256'],section=event['section'],reference=event['reference'],code='Owner correction has unresolved source section/numbering; not applied',blocking=True,event_hash=event['event_hash']))
    concept_records=[r for r in records if r['ledger_event'] and r['ledger_event']['decision']=='concept_approved']
    report=dict(engine_version=engine_revision['version'],engine_code_sha256=engine_revision['code_sha256'],timestamp=stamp,sources=sources,records=len(records),
        source_failures=len(manifest['sources'])-len(sources),
        exceptions=len(exceptions),metrics=metrics,bulk_gate='closed_until_owner_reviewed_pilot',
        previous_run_sha256=hashlib.sha256(Path(previous_path).read_bytes()).hexdigest() if previous_path else None,
        ledger_sha256=corrections.digest(ledger),publication_status='draft',database_changes='none')
    report['owner_concept_correction_agreement']=dict(matched=sum(engine.norm(r['automated_proposal'].get('concept') or '')==engine.norm(r['ledger_event']['classification'].get('concept') or '') for r in concept_records),supplied_labels=len(concept_records),scope='Supplied concept corrections only; not exact historical taxonomy/boundary approval or global accuracy')
    for name,value in [('review.json',records),('boundary-evidence.json',[{k:r[k] for k in ['question_identity','source_sha256','section','reference','subreference','start','end_exclusive','heading','profile']} for r in records]),
                       ('comparison.json',comparisons),('corrections-ledger.json',ledger),('exceptions.json',exceptions),('report.json',report)]:write_json(out/name,value)
    # Raw text is isolated and deliberately excluded by the deliverable builder.
    write_json(out/'PRIVATE-segments-do-not-distribute.json',private_segments)
    csv_tools.write_csv(out/'before-after.csv',['document_key','section','reference','subreference','old_key','new_identity','old','new','owner_state'],
        [{**c,'old':json.dumps(c['old'],ensure_ascii=False),'new':json.dumps(c['new'],ensure_ascii=False)} for c in comparisons])
    csv_tools.write_csv(out/'exception-report.csv',['document_key','section','reference','subreference','code','blocking'],exceptions)
    csv_tools.write_csv(out/'historical-review-queue.csv',['question_identity','document_key','section','reference','subreference','classification','owner_state'],
        [{**r,'classification':json.dumps(r['classification'],ensure_ascii=False)} for r in records])
    # Default pilot is empty. Explicit owner labels must approve exact boundaries,
    # historic chapter/topics and answer location before an import pilot is selected.
    eligible=[]
    for r in records:
        e=r['ledger_event'];labels=e.get('labels',{}) if e else {}
        if e and e['actor']=='owner' and e['decision']=='approved' and r['owner_state']=='approved' and all(k in labels and labels[k]==r['metric_values'][k] for k in ['boundary','chapter_key','unit_topic_keys','answer_locations']) and r['classification'].get('taxonomy_match') and not r['layout_blocked'] and len(r['answer_candidates'])==1:
            eligible.append(r)
    tables={k:[] for k in ['hierarchy','documents','occurrences','question_topics','answers']}
    if export_reviewed:
        if not eligible:raise ValueError('No fully owner-approved pilot rows; no import export released')
        if len(eligible)>10:raise ValueError('Small pilot export limit: ten independently reviewed references')
        documents={s['document_key']:s for s in manifest['sources']};exported_docs=set();exported_nodes=set()
        node_index={n['node_key']:n for n in taxonomy['nodes']}
        def hierarchy(key):
            if not key or key in exported_nodes:return
            n=node_index[key];hierarchy(n.get('parent_key'));exported_nodes.add(key)
            tables['hierarchy'].append(csv_tools.ordered('hierarchy',n))
        for r in eligible:
            doc=documents[r['document_key']];ed=r['classification']['historical_edition']
            if r['document_key'] not in exported_docs:
                tables['documents'].append(csv_tools.ordered('documents',dict(document_key=doc['document_key'],edition_key=ed,title=doc['title'],source_type=doc['source_type'],exam_attempt=doc['attempt'],official_url=doc['official_url'],issue_period=doc.get('issue_period',''),mtp_series=doc.get('mtp_series',''))));exported_docs.add(r['document_key'])
            key='R2-'+r['question_identity'][:32];occ=key+'-occ';label=r['metric_values'];a=r['answer_candidates'][0]
            for n in r['classification']['official_nodes']:
                hierarchy(n['node_key']);tables['question_topics'].append(csv_tools.ordered('question_topics',dict(question_key=key,node_key=n['node_key'])))
            tables['occurrences'].append(csv_tools.ordered('occurrences',dict(occurrence_key=occ,question_key=key,question_title=r['subject']+' '+r['attempt']+' '+r['section']+' Q'+r['reference'],document_key=doc['document_key'],edition_key=ed,chapter_key=label['chapter_key'],page_reference='PDF p.'+str(r['start']['page']),question_number=r['reference'],subquestion_number=r['subreference'],marks='',marks_verified='0',question_type=r['kind'])))
            tables['answers'].append(csv_tools.ordered('answers',dict(answer_key=key+'-answer',question_key=key,occurrence_key=occ,answer_mode='official_link',official_url=a.get('official_url',doc['official_url']),source_location='PDF p.'+str(a['page'])+'; '+r['section']+' Q'+r['reference']+(' ('+r['subreference']+')' if r['subreference'] else ''))))
    for kind,rows in tables.items():
        csv_tools.write_csv(out/('pilot-'+kind+'.csv'),csv_tools.header(kind),rows)
    edition_setup=taxonomy.get('editions',[])
    if export_reviewed:
        errors=csv_tools.validate_package(tables,{ed['edition_key']:ed for ed in edition_setup},taxonomy)
        if errors:
            for kind in tables:csv_tools.write_csv(out/('pilot-'+kind+'.csv'),csv_tools.header(kind),[])
            raise ValueError('Pilot CSV validation failed; files withheld: '+json.dumps(errors))
    write_json(out/'pilot-edition-setup.json',edition_setup)
    write_json(out/'pilot-gate.json',dict(eligible=len(eligible),exported=len(eligible) if export_reviewed else 0,status='needs_owner_review' if not eligible else 'reviewed_labels_ready_for_explicit_export',
        note='No real CSV import is authorised automatically. Empty files are not importable. Corrected metadata and evidence are in the review queue.'))
    data=json.dumps(dict(review=records,report=report,ledger=ledger),ensure_ascii=False).replace('<','\\u003c').replace('&','\\u0026')
    (out/'review.html').write_text((ROOT/'research/layout-review.html').read_text().replace('/*__DATA__*/',data))
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest');parser.add_argument('--output',required=True)
    parser.add_argument('--ledger');parser.add_argument('--previous')
    parser.add_argument('--export-reviewed',action='store_true')
    a=parser.parse_args()
    result=run(a.manifest,a.output,a.ledger,a.previous,a.export_reviewed)
    print(json.dumps({'sources':len(result['sources']),'records':result['records'],'bulk_gate':result['bulk_gate']}))
