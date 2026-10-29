"""Assemble source-corroborated AFM review drafts; all decisions Needs Review."""
from collections import Counter,defaultdict
from copy import deepcopy
from pathlib import Path
import argparse,html,json,re,unicodedata
import fitz
import archive_catalog as cat
import archive_release as prior
import archive_integrity
import afm_reconcile as afm
import afm_mcq
import afm_tables
import fr_corpus as fr
import gold_layout as gold
import layout_engine

ROOT=Path(__file__).resolve().parents[1]
BASIS='Owner-authorised private AFM research. Publication requires an existing matching source-wide rights declaration; no grant or academic approval supplied.'

def rich(q,doc,cache):
    key=gold.sha(afm.packed({k:q.get(k)for k in('lines','start','end_exclusive')}))
    if key not in cache:
        filekey=gold.sha(Path(doc.name).read_bytes())
        path=ROOT/'work/afm-complete/private/rich-cache'/gold.sha(Path(gold.__file__).read_bytes())/filekey/(key+'.json')
        if path.exists():cache[key]=json.loads(path.read_text())
        else:cache[key]=gold.reconstruct(q,doc,cache.setdefault('__table_cache__',{}));cat.write(path,cache[key])
    return afm_tables.normalize(cache[key],doc)

def context(r):
    d=r['identity'];period=d['exam_attempt'];legacy=d['actual_subject']=='SFM'
    key='afm-context-'+afm.slug(d['historical_paper_title']+'-'+period)
    official=(not legacy and period in('May 2025','September 2025','January 2026','May 2026','November 2026'))
    url='https://www.icai.org/post/sm-final-p2-may2026'if period in('May 2026','November 2026')else'https://www.icai.org/post/sm-final-p2-may2025'if official else'https://www.icai.org/post/sm-final-paper2-archives'
    title=d['historical_paper_title']+' — '+period+(' (historical SFM; AFM crosswalk provisional)'if legacy else'')
    ed=dict(edition_key=key,subject_code='AFM',title=title,applicability=period+'; original '+d['historical_paper_title']+' source context. '+('Exact study-material applicability requires historical review.'if not official else'Chapter titles source-backed; question-level editorial mappings remain provisional.'),source_url=url)
    nodes=[]
    for n,title in enumerate(afm.CHAPTERS,1):
        c=key+'-chapter-'+str(n)
        nodes.append(dict(node_key=c,edition_key=key,subject_code='AFM',parent_key='',node_type='chapter',title=title if official else title+' (Editorial AFM crosswalk)',heading_number=str(n)if official else'',heading_origin='official'if official else'editorial',source_url=url,source_location='Official chapter listing'if official else'Editorial crosswalk, not a historical official chapter number'))
        concepts=[label for cn,label,_ in afm.CONCEPTS if cn==n]or[title+' — source concept']
        for label in concepts:nodes.append(dict(node_key=c+'-'+afm.slug(label),edition_key=key,subject_code='AFM',parent_key=c,node_type='topic',title=label,heading_origin='editorial',source_url=url,source_location='Editorial search concept; source/requirement evidence saved with each question.'))
    # Honest review bucket, never an invented official syllabus heading.
    nodes.append(dict(node_key=key+'-topic-review',edition_key=key,subject_code='AFM',parent_key='',node_type='chapter',title='Topic Review Required (Editorial)',heading_origin='editorial',source_url=url,source_location='No reliable question-level classification established.'))
    return key,dict(batch_key='AFM-TAX-'+gold.sha(key)[:24],editions=[ed],nodes=nodes)

def source(r):
    app=deepcopy(r);app['identity']['actual_subject']='AFM'
    s=prior.source(app);s['title']=(r['identity']['historical_paper_title']+' — '+r['filename'])[:240]
    s['source_type']=r['identity']['source_type'];s['role']=r['identity']['role'];s['edition_key']=context(r)[0]
    s['technical_notes']='PDF hash and content read. Historical identity: '+r['identity']['historical_paper_title']+'. '+('Target attempt unconfirmed; issue period retained.'if r['identity'].get('target_pending')else'Target/source period reconciled from source and recorded authoritative evidence.')
    return s

def pair_sources(r,records,payloads):
    d=r['identity'];own=payloads[r['file_id']]
    if any(q['region']['side']=='answer'for q in own['records']):return [r]
    found=[]
    for other in records:
        od=other['identity']
        if other['file_id']==r['file_id']or od.get('document_kind')=='corrigendum':continue
        if any(od.get(k)!=d.get(k)for k in('actual_subject','source_type','exam_attempt','document_issue_period','series','scheme')):continue
        if any(q['region']['side']=='answer'for q in payloads[other['file_id']]['records']):found.append(other)
    # Copies are retained in inventory, not treated as independent answer choices.
    return list({x['content_fingerprint']:x for x in found}.values())

def build(manifest, checkpoints, output, target_registry):
    out=cat.private(output);out.mkdir(parents=True,exist_ok=True)
    records=json.loads(Path(manifest).read_text())['records'];payloads={r['file_id']:json.loads((Path(checkpoints)/'documents'/((r.get('legacy_copy_of')or r['file_id'])+'.json')).read_text())for r in records};targets=json.loads(Path(target_registry).read_text())
    for r in records:
        # Identity-only updates do not re-extract unchanged PDF regions.
        with fitz.open(r['local_path'])as doc:r['identity']=afm.identity(r,doc,targets)
        payloads[r['file_id']]['identity']=r['identity']
    preferred={};copies=[]
    for r in sorted(records,key=lambda r:('Exam_Question' in r['filename'],r['filename'])):
        if r['content_fingerprint']in preferred:copies.append(dict(file_id=r['file_id'],canonical_file_id=preferred[r['content_fingerprint']],reason='Full normalised native text agrees; distinct stored source copy retained.'))
        else:preferred[r['content_fingerprint']]=r['file_id']
    duplicate_ids={x['file_id']for x in copies}
    oldrows=json.loads((ROOT/'work/v081/private/release-r008/AFM/subjective-candidates.json').read_text());old={}
    for row in oldrows:
        d=row['import_record'];old[(d['source_hash'],d['reference'],d['subreference'],d['practice_structure'].get('alternative',''))]=d
    rows=[];mcqs=[];scenarios={};sources={};taxonomies={};coverage=[];reconciliation=[];parent_counts=Counter();mcq_context=[]
    for r in records:
        p=payloads[r['file_id']];d=r['identity'];key,tax=context(r);tax=taxonomies.setdefault(key,tax)
        count=dict(file_id=r['file_id'],filename=r['filename'],sha256=r['source_hash'],bytes=r['bytes'],pages=r['page_count'],source_url=prior.source_url(r),source_type=d['source_type'],historical_subject=d['actual_subject'],scheme=d['scheme'],attempt=d['exam_attempt'],issue_period=d['document_issue_period'],series=d['series'],role=d['role'],status=p['status'],subjective_parents=0,subjective_parts=0,mcq_candidates=0,source_corroborated_answers=0,answer_candidates=0,answer_pending=0,blocked_questions=0,import_subjective=0,import_mcq=0,exclusion_reasons=[])
        coverage.append(count)
        if r['file_id']in duplicate_ids:count['exclusion_reasons'].append('Duplicate source copy; canonical source occurrences imported once.');continue
        if d.get('document_kind')=='corrigendum':count['exclusion_reasons'].append('Corrigendum retained as targeted amendment evidence; not an extra invented question occurrence.');continue
        if not p['records']:count['exclusion_reasons'].append('No safe native regions; OCR source held for transcription and boundary verification.');continue
        sources[prior.source_key(r)]=source(r)
        candidates=pair_sources(r,[x for x in records if x['file_id']not in duplicate_ids],payloads);answer_source=candidates[0]if len(candidates)==1 else None
        if answer_source:sources[prior.source_key(answer_source)]=source(answer_source)
        parent_answers=[x['region']for x in payloads[answer_source['file_id']]['records']if x['region']['side']=='answer']if answer_source else[]
        with fitz.open(r['local_path'])as doc:
            ac=fitz.open(answer_source['local_path'])if answer_source else None;cache={};answercache={}
            try:
                for parent in p['records']:
                    q=parent['region']
                    if q['side']!='question' or q['format']in('MCQ','MCQ_CASE'):continue
                    count['subjective_parents']+=1;parent_counts[d['source_type']]+=1
                    matches=[a for a in parent_answers if a['reference']==q['reference']and a['format']=='SUBJECTIVE']
                    a=matches[0]if len(matches)==1 else None
                    qs,answers,warnings=afm.split_question({**q,'source_type':d['source_type']},a);amap={(x.get('subreference',''),x.get('alternative','')):x for x in answers}
                    for child in qs:
                        part=prior.subref(child);alt=child.get('alternative','');previous=old.get((r['source_hash'],child['reference'],part,alt))
                        stable=previous['stable_id']if previous else'R-'+layout_engine.identity(r['source_hash'],'descriptive'+(':'+alt if alt else''),child['reference'],child['subreference']+(':'+alt if alt else''))
                        body=rich(child,doc,cache);matched=amap.get((child.get('subreference',''),alt));answer_region=matched
                        if matched and matched.get('shared_lines'):
                            common=matched['shared_lines'];answer_region={**matched,'lines':common+matched['lines'],'start':fr.where(common[0])}
                        answer=rich(answer_region,ac,answercache)if answer_region and ac else None
                        evidence=afm.corroboration(child,matched)if matched else{}
                        state='A'if matched and evidence['corroborated']else'B'if matched else'C'if answer_source else'D'if not candidates else'E'
                        issues=list(warnings)+body['warnings']+(answer['warnings']if answer else[])
                        if d.get('target_pending'):issues.append('question_integrity_failed_target_attempt_unconfirmed')
                        if d['actual_subject']=='SFM':issues.append('historical_SFM_current_AFM_crosswalk_provisional')
                        if any('fidelity_failed'in w or 'possible_borderless_table'in w for w in body['warnings']):issues.append('question_integrity_failed_table_or_numeric_geometry')
                        if any(w.startswith('question_boundary')for w in warnings):issues.append('question_integrity_failed_independent_part_boundary_requires_review')
                        if state!='A':issues.append('answer_mapping_conflict_state_'+state+'_needs_review')
                        for side,value in [('question',body),('answer',answer)]:
                            if value and any(unicodedata.category(c)in('Co','Cn')or c=='\ufffd'for c in value['plain_text']):
                                value['fidelity']['passed']=False;issues.append(('question_integrity_failed_'if side=='question'else'answer_formula_conflict_')+'unsupported_source_font_glyph')
                        proposed=afm.tags(child,matched)
                        if not proposed:issues.append('TOPIC_REVIEW_REQUIRED')
                        chosen=proposed[0]if proposed else None;nodekey=key+'-chapter-'+str(chosen['chapter'])+'-'+afm.slug(chosen['label'])if chosen else key+'-topic-review'
                        # A source-heading tag may have no narrower editorial rule.
                        if chosen and not any(n['node_key']==nodekey for n in tax['nodes']):
                            tax['nodes'].append(dict(node_key=nodekey,edition_key=key,subject_code='AFM',parent_key=key+'-chapter-'+str(chosen['chapter']),node_type='topic',title=chosen['label'],heading_origin='editorial',source_url=tax['editions'][0]['source_url'],source_location='Question source heading; finer editorial path pending owner review.'))
                        scenario_key=None;common=child.get('shared_lines',[])
                        if common:
                            last=common[-1];shared={**child,'lines':common,'start':fr.where(common[0]),'end_exclusive':dict(page=last['page'],bbox=[last['bbox'][0],last['bbox'][3]+.1,last['bbox'][2],last['bbox'][3]+.1],column=0)}
                            sr=rich(shared,doc,cache);scenario_key='SC-'+gold.sha(r['source_hash']+'|'+sr['source_text_sha256'])[:48]
                            scenarios[scenario_key]=dict(scenario_key=scenario_key,source_hash=r['source_hash'],body_html=sr['body_html'],rights_basis=BASIS,evidence=dict(start=shared['start'],end=shared['end_exclusive']))
                            if not sr['fidelity']['passed']or archive_integrity.inspect(sr):issues.append('question_integrity_failed_shared_scenario_format')
                        marks=re.findall(r'\((\d{1,2})\s*Marks?\)',body['plain_text'],re.I);mark=int(marks[-1])if len(set(marks))==1 else None
                        practical=bool(re.search(r'\bcalculate|\bcompute|\bprepare|\bdetermine|\bevaluate|\badvi[cs]e',body['plain_text'],re.I)or any(b['type']=='table'for b in body['blocks']))
                        rec=dict(stable_id=stable,source_hash=r['source_hash'],source_key=prior.source_key(r),subject_code='AFM',source_type=d['source_type'],exam_attempt=d['exam_attempt'],mtp_series=d['series'],issue_period=d['document_issue_period'],scheme=d['scheme'],section='descriptive'+(':'+alt if alt else''),reference=child['reference'],subreference=part,title=(d['historical_paper_title']+' '+d['exam_attempt']+' Q'+child['reference']+afm.refpart(child)+(' — '+alt if alt else''))[:190],official_url=prior.source_url(r),edition_id=None,classification=[],question_page=prior.page(child),question_coordinates=dict(start=child['start'],end_exclusive=child['end_exclusive']),heading_evidence=child.get('heading')or{},question_type='practical'if practical else'theory',question_format='subjective',rights_mode='licensed_private_review',rights_basis=BASIS,reasoning='Provisional source heading / operative requirement / answer corroboration. '+('Historical SFM original identity retained; mapping to current AFM is a separate editorial proposal.'if d['actual_subject']=='SFM'else''),confidence='Source-corroborated candidate; not independent academic verification',blocking_exceptions=sorted(set(issues)),extraction_status='needs_review',source_revision=r['source_hash'],engine_revision=dict(engine=afm.VERSION),ai_proposal=dict(historical_edition=key,official_nodes=[],primary_path=[dict(node_key=nodekey,node_type='topic',title=chosen['label']if chosen else'Topic Review Required')],additional_node_keys=[],proposed_search_tags=[x['label']for x in proposed]),rich_content=dict(question=prior.content(body)),answer={},marks=mark,marks_verified=bool(mark),practice_structure=dict(parent_stable_id='P-'+gold.sha(r['source_hash']+'|'+q['reference'])[:48],alternative=alt,quality_required=True),quality_checks={},source_provenance=dict(drive_file_id=r['file_id'],historical_subject=d['actual_subject']),previous_corrections=previous.get('previous_corrections',[])if previous else[])
                        if scenario_key:rec['practice_structure']['scenario_key']=scenario_key
                        for extra in proposed[1:]:
                            ek=key+'-chapter-'+str(extra['chapter'])+'-'+afm.slug(extra['label'])
                            if not any(n['node_key']==ek for n in tax['nodes']):tax['nodes'].append(dict(node_key=ek,edition_key=key,subject_code='AFM',parent_key=key+'-chapter-'+str(extra['chapter']),node_type='topic',title=extra['label'],heading_origin='editorial',source_url=tax['editions'][0]['source_url'],source_location='Additional source-supported editorial concept'))
                            rec['ai_proposal']['additional_node_keys'].append(ek)
                        if answer:
                            rec['rich_content']['answer']=prior.content(answer);rec['answer']=dict(source_hash=answer_source['source_hash'],official_url=prior.source_url(answer_source),reference=child['reference'],subreference=part,alternative=alt,question_identity=stable,question_reference=child['reference'],question_subreference=part,question_source_hash=r['source_hash'],page=prior.page(matched),subject_code='AFM',source_type=d['source_type'],exam_attempt=d['exam_attempt'],mtp_series=d['series'],mode='licensed',notes='Matching state '+state+'. '+evidence['method']);rec['source_provenance']['answer_drive_file_id']=answer_source['file_id']
                        candidate=rich(a,ac,answercache)if not answer and a and ac else None
                        row=dict(import_record=rec,question=body,answer=answer,answer_candidate=candidate,answer_candidate_page=prior.page(a)if candidate else'',source_file_id=r['file_id'],answer_file_id=answer_source['file_id']if answer_source else'',match_state=state,match_evidence=evidence,proposed_topics=proposed,original_subject=d['actual_subject'],source_filename=r['filename'],import_eligible=True)
                        archive_integrity.hold(row)
                        rows.append(row);count['subjective_parts']+=1;count['import_subjective']+=1;count['source_corroborated_answers']+=state=='A';count['answer_candidates']+=bool(answer);count['answer_pending']+=state!='A';count['blocked_questions']+=any('question_integrity_failed'in w for w in rec['blocking_exceptions'])
                        reconciliation.append(dict(question_id=stable,previous_id=previous['stable_id']if previous else'',action='retain_stable_id_compare_only'if previous else'new_source_occurrence',source_hash=r['source_hash'],reference=child['reference'],subreference=part,alternative=alt))
                # MCQ keys use a separate printed section; no descriptive notes.
                all_lines=afm.cleaned_lines(doc)
                if d['source_type']=='mtp':
                    b=next((i for i,l in enumerate(all_lines)if re.match(r'^PART\s*[–-]?\s*I\b(?=\s*(?:[-–—:]|CASE\b|MULTIPLE\b|$))',l['text'],re.I)),None)
                    e=next((i for i,l in enumerate(all_lines)if re.match(r'^PART\s*[–-]?\s*II\b(?=\s*(?:[-–—:]|DESCRIPTIVE\b|SUBJECTIVE\b|$))',l['text'],re.I)),None)
                    mcq_parents=[afm.make_region(all_lines,b,e,doc)]if b is not None and e is not None else[]
                    for mp in mcq_parents:mp.update(reference='MCQ',format='MCQ_CASE')
                else:mcq_parents=[x['region']for x in p['records']if x['region']['side']=='question'and x['region']['format']=='MCQ_CASE']
                global_keys={}
                if ac and d['source_type']in('mtp','exam'):
                    als=afm.cleaned_lines(ac);begin=next((i for i,l in enumerate(als)if re.search(r'ANSWER\s+TO\s+PART\s*[–-]?\s*I\b|^Answer Key$',l['text'],re.I)),0);end=next((i for i,l in enumerate(als[begin+1:],begin+1)if re.match(r'^(?:ANSWERS?\s+(?:OF|TO)\s+)?PART\s*[–-]?\s*II\b',l['text'],re.I)),len(als));global_keys=afm_mcq.keys_in(als[begin:end],ac)
                for mp in mcq_parents:
                    ma=next((x for x in parent_answers if x['reference']==mp['reference']),None)
                    extracted=afm_mcq.extract(mp,doc,ma,ac,global_keys,scope='booklet'if d['source_type']=='other'else'')
                    for x in extracted:
                        stable='MCQ-'+gold.sha(r['source_hash']+'|'+x['source_section']+'|'+x['reference'])[:48]
                        # Keep all previous global MTP identities exactly.
                        if d['source_type']=='mtp'and x['source_section']=='part_i_mcq':stable='MCQ-'+gold.sha(r['source_hash']+'|part_i_mcq|'+x['reference'])[:48]
                        sc=x['scenario']
                        if sc:sc['key']='MCQ-CASE-'+gold.sha(r['source_hash']+'|'+str(sc['source_location']['start']))[:40];sc['source_hash']=r['source_hash']
                        if d.get('target_pending'):x['issues'].append('source_identity_conflict_target_attempt_pending')
                        if d['actual_subject']=='SFM':x['issues'].append('historical_SFM_current_AFM_mapping_requires_owner_decision')
                        tags=afm.tags(x['region'],ma);keydata=x['key'];answer_info=dict(source_key=prior.source_key(answer_source)if answer_source else'',source_hash=answer_source['source_hash']if answer_source else'',official_url=prior.source_url(answer_source)if answer_source else'',page=keydata['page']if keydata else'',key_evidence=keydata,question_source_hash=r['source_hash'],question_reference=x['reference'],subject_code='AFM',source_type=d['source_type'],exam_attempt=d['exam_attempt'],mtp_series=d['series'])
                        mc=dict(stable_id=stable,source_occurrence_id='MCO-'+stable[4:],subject_code='AFM',source_type=d['source_type'],exam_attempt=d['exam_attempt'],mtp_series=d['series'],issue_period=d['document_issue_period'],edition_key=key,scheme=d['scheme'],section=x['source_section'],reference=x['reference'],source_key=prior.source_key(r),source_hash=r['source_hash'],official_url=prior.source_url(r),question_page=x['region']['start']['page'],question_location=dict(start=x['region']['start'],end_exclusive=x['region']['end_exclusive']),question_html=x['question']['body_html'],question_checks=x['question']['fidelity'],question_structure=x['question']['blocks'],options=x['options'],scenario=sc,answer=answer_info,correct_options=keydata['correct_options']if keydata else[],key_policy='single'if keydata and len(keydata['correct_options'])==1 else'needs_owner_decision',key_verified=bool(keydata and not keydata.get('conflict')),explanation_html='',tags=[dict(label=t['label'],kind='concept',origin='editorial',evidence=t['evidence'])for t in tags],exceptions=[w[:185]for w in sorted(set(x['issues']))],review_status='needs_review',academic_approval=False,review_notes='Source-key evidence is not independent academic verification. Original historical identity: '+d['historical_paper_title'])
                        mc['key_verified']=bool(keydata and keydata['correct_options']and not keydata.get('conflict'))
                        if x.get('explanation'):
                            mc['explanation_html']=x['explanation']['body_html']
                            mc['exceptions']+=['source_explanation_'+w for w in x['explanation']['warnings']]
                        eligible=len(mc['options'])>=2 and len({o['id']for o in mc['options']})==len(mc['options'])
                        mcqs.append(dict(import_record=mc,source_file_id=r['file_id'],source_filename=r['filename'],question=x['question'],case_reference=x['case_reference'],original_subject=d['actual_subject'],import_eligible=eligible));count['mcq_candidates']+=1;count['import_mcq']+=eligible
                    mcq_context.append(dict(file_id=r['file_id'],parent_reference=mp['reference'],candidates=len(extracted),answer_key_rows=len(global_keys)))
            finally:
                if ac:ac.close()
        cat.write(out/'source-checkpoints'/(r['file_id']+'.json'),dict(coverage=count,subjective=[x for x in rows if x['source_file_id']==r['file_id']],mcqs=[x for x in mcqs if x['source_file_id']==r['file_id']]))
        print(json.dumps(dict(file_id=r['file_id'],subjective=count['subjective_parts'],mcq=count['mcq_candidates'],answers=count['source_corroborated_answers'])),flush=True)
    seen=set();distinct=[]
    for row in rows:
        sid=row['import_record']['stable_id']
        if sid in seen:raise ValueError('Duplicate new stable subjective identity '+sid)
        seen.add(sid);distinct.append(row)
    by_coverage={x['file_id']:x for x in coverage}
    for copy in copies:
        item=by_coverage[copy['file_id']];canonical=by_coverage[copy['canonical_file_id']]
        item['canonical_file_id']=copy['canonical_file_id'];item['represented_questions_in_copy']=canonical['subjective_parts'];item['represented_mcqs_in_copy']=canonical['mcq_candidates']
    result=dict(subjective=distinct,mcqs=mcqs,sources=sources,taxonomies=taxonomies,scenarios=scenarios,coverage=coverage,source_copies=copies,id_reconciliation=reconciliation,mcq_context=mcq_context,source_inventory=records)
    cat.write(out/'afm-bank.json',result)
    cat.write(out/'summary.json',dict(source_pdfs=len(records),source_pages=sum(r['page_count']for r in records),source_outcomes=dict(Counter(p['status']for p in payloads.values())),subjective_parents=dict(parent_counts),subjective_parts=len(rows),mcq_candidates=len(mcqs),mcq_import_drafts=sum(r['import_eligible']for r in mcqs),answer_matching=dict(Counter(r['match_state']for r in rows)),independent_academic_approvals=0,publications=0))
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('manifest');p.add_argument('--checkpoints',required=True);p.add_argument('--targets',required=True);p.add_argument('--output',required=True);a=p.parse_args();build(a.manifest,a.checkpoints,a.output,a.targets)
