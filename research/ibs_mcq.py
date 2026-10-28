"""Private decimal-reference IBS MCQs; source key evidence, never invented options."""
from pathlib import Path
import re,copy
import fitz
import ibs_layout
import gold_layout as gold
from fr_corpus import where
from mcq_pipeline import strip_choice
CHOICE=re.compile(r'^\(([A-Da-d])\)(?:\s|$)|^([A-Da-d])[.)](?:\s|$)')
def piece(q,lines,doc):
 if not lines:return dict(body_html='',plain_text='',blocks=[],fidelity={'passed':False},source_text_sha256=gold.sha(''),warnings=['empty_region'])
 last=lines[-1];return gold.reconstruct({**q,'lines':lines,'start':where(lines[0]),'end_exclusive':dict(page=last['page'],bbox=[last['bbox'][0],last['bbox'][3]+.01,last['bbox'][2],last['bbox'][3]+.01],column=0)},doc,{})
def extract_group(group):
 qp=Path(group['question_path']);ap=Path(group['answer_path']);qh=gold.sha(qp.read_bytes());ah=gold.sha(ap.read_bytes());combined=qp==ap;records=[];reports=[];cases={}
 with fitz.open(qp)as qdoc,fitz.open(ap)as adoc:
  questions,profile=ibs_layout.discover(qdoc,dict(source_type=group['source_type'],role='questions_and_answers'if combined else'questions'));answers,_=ibs_layout.discover(adoc,dict(source_type=group['source_type'],role='questions_and_answers'if combined else'answers'));answer_index={}
  for a in answers:
   if a['side']=='answer'and a['format']=='MCQ':answer_index.setdefault((a['parent_reference'],a['reference']),[]).append(a)
  for q in questions:
   if q['side']!='question'or q['format']!='MCQ':continue
   lines=copy.deepcopy(q['lines']);markers=[(i,l,CHOICE.match(l['text']))for i,l in enumerate(lines)if CHOICE.match(l['text'])];letters=[(m[1]or m[2]).upper()for _,_,m in markers];warnings=[];options=[]
   if letters!=list('ABCD')or max([l['bbox'][0]for _,l,_ in markers]or[0])-min([l['bbox'][0]for _,l,_ in markers]or[0])>16:warnings.append('option_geometry_or_complete_ABCD_sequence_requires_review')
   else:
    for n,(i,l,m)in enumerate(markers):
     stop=markers[n+1][0]if n+1<len(markers)else len(lines);body=copy.deepcopy(lines[i:stop]);body[0]=strip_choice(body[0]);rich=piece(q,body,qdoc);options.append(dict(id=letters[n],html=rich['body_html'],checks=rich['fidelity'],source_location=dict(page=l['page'],bbox=l['bbox'])))
   stem=piece(q,lines[:markers[0][0]]if markers else lines,qdoc);candidates=answer_index.get((q['parent_reference'],q['reference']),[]);answer=candidates[0]if len(candidates)==1 else None;key=None;explanation=''
   if answer:
    first=answer['lines'][:4];text=' '.join(l['text']for l in first);match=re.search(r'(?:\bOption\s*|correct\s+answer\s+is\s*(?:option\s*)?)\(([A-D])\)',text,re.I)
    if not match:match=re.match(r'^\s*[1-9][0-9]?\.[1-9][0-9]?\s*\(([A-D])\)',text,re.I)
    if not match:
     label=next((l for l in first[1:]if re.fullmatch(r'\([A-D]\)',l['text'],re.I)),None)
     if label:match=re.search(r'\(([A-D])\)',label['text'],re.I)
    if match:key=dict(correct_options=[match[1].upper()],page=answer['start']['page'],bbox=answer['start']['bbox'],source_line=text,method='exact_decimal_reference_and_explicit_source_option');explanation=piece(answer,answer['lines'],adoc)['body_html']
   if not key:warnings.append('exact_correct_option_not_established')
   usable=key and key['correct_options'][0]in letters and len(options)==4
   shared=q.get('shared_lines',[]);scenario=None
   if shared:
    common=piece(q,shared,qdoc);sk='IBS-CASE-'+gold.sha(qh+'|'+q['parent_reference']+'|'+common['source_text_sha256'])[:40];scenario=dict(key=sk,source_hash=qh,html=common['body_html'],checks=common['fidelity'],structure=common['blocks'],source_location=dict(start=where(shared[0]),end=where(shared[-1])));cases[sk]=scenario
   else:warnings.append('common_case_facts_missing')
   stable='MCQ-'+gold.sha(qh+'|ibs_case|'+q['parent_reference']+'|'+q['reference'])[:48]
   record=dict(stable_id=stable,source_occurrence_id='MCO-'+gold.sha(qh+'|ibs_case|'+q['parent_reference']+'|'+q['reference'])[:48],subject_code='IBS',source_type=group['source_type'],exam_attempt=group['exam_attempt'],mtp_series=group.get('mtp_series',''),issue_period=group.get('issue_period',''),edition_key=group['edition_key'],scheme='final_six_paper_2023',section='case_'+q['parent_reference']+'_mcq',reference=q['reference'],source_key=group['question_source_key'],source_hash=qh,official_url=group['question_url'],question_page=q['start']['page'],question_location=dict(start=q['start'],end_exclusive=q['end_exclusive']),question_html=stem['body_html'],question_checks=stem['fidelity'],question_structure=stem['blocks'],options=options,scenario=scenario,answer=dict(source_key=group['answer_source_key'],source_hash=ah,official_url=group['answer_url'],page=key['page']if key else'',key_evidence=key,question_source_hash=qh,question_reference=q['reference'],subject_code='IBS',source_type=group['source_type'],exam_attempt=group['exam_attempt'],mtp_series=group.get('mtp_series','')),correct_options=key['correct_options']if usable else[],key_policy='single'if usable and not warnings else'needs_owner_decision',key_verified=bool(usable),explanation_html=explanation,academic_review_status='needs_review',publication_status='draft',classification_origin='provisional',tags=[],exceptions=warnings,rights_mode='licensed_public',attribution='The Institute of Chartered Accountants of India (ICAI). Exact case, PDF and answer-key identity retained.',record_revision=1,extractor='ibs-mcq-decimal-1');records.append(record)
 return records,dict(candidates=len(records),explicit_keys=sum(r['key_verified']for r in records),exceptions=[dict(stable_id=r['stable_id'],reference=r['reference'],exceptions=r['exceptions'])for r in records if r['exceptions']],question_profile=profile),list(cases.values())
