"""Option-driven AFM MCQs; original case/roman references and exact key geometry.

No answer is solved or inferred. A missed key, conflicting row or incomplete
choice set remains a private review candidate. Historical schemes stay explicit.
"""
from copy import deepcopy
from collections import Counter
import re
import fr_corpus as fr
import gold_layout as gold
import mcq_pipeline as common
import afm_tables
from afm_reconcile import CASE, ANSWER_CASE, OPTION, ROMAN, pos, make_region

def number(text, roman=False):
    if roman:
        m=ROMAN.match(text)
        if m:return (m[1]or m[2]).upper()
        return text.upper()if re.fullmatch(r'[IVX]+',text,re.I)else None
    m=re.match(r'^(\d{1,2})(?:\.(?:\s|$)|\s*$)',text);return m[1]if m else None

def option_groups(lines):
    markers=[(i,l,(OPTION.match(l['text'])[1]or OPTION.match(l['text'])[2]).upper())for i,l in enumerate(lines)if OPTION.match(l['text'])]
    found=[]
    for n in range(max(0,len(markers)-3)):
        group=markers[n:n+4]
        if [a[2]for a in group]==list('ABCD')or(group[0][2]=='A'and group[-1][2]=='D'and len({x[2]for x in group})<4):
            found.append(group)
    return found

def keys_in(lines, doc):
    out={};conflicts=[]
    for i,l in enumerate(lines):
        t=l['text']; direct=re.match(r'^(\d{1,2}|[IVX]+)\.?\s+(?:Option\s*)?\(([A-D])\)',t,re.I)
        if not direct:direct=re.match(r'^(\d{1,2}|[IVX]+)\.?\s+Option\s+([A-D])\b',t,re.I)
        n=re.fullmatch(r'(\d{1,2}|[IVX]+)\.?',t,re.I)
        # A source can misplace the full stop before its key-row number.
        # Recover that printed row only with an explicit same-baseline choice.
        if not n:n=re.fullmatch(r'\.(\d{1,2})',t)
        if direct:ref=direct[1].upper();values=[direct[2].upper()];area=[l]
        elif n:
            cy=(l['bbox'][1]+l['bbox'][3])/2
            pair=[x for x in lines if x['page']==l['page'] and x['bbox'][0]>l['bbox'][2] and abs((x['bbox'][1]+x['bbox'][3])/2-cy)<5 and re.match(r'^(?:(?:Option\s*)?(?:\([A-D]\)|[A-D][.)]?$)|No correct option$)',x['text'],re.I)]
            if len(pair)!=1:continue
            ref=n[1].upper();values=[]if re.fullmatch('No correct option',pair[0]['text'],re.I)else re.findall(r'\(([A-D])\)',pair[0]['text'],re.I)or[re.sub(r'^Option\s+','',pair[0]['text'],flags=re.I).strip(' .)(').upper()];area=[l,pair[0]]
        else:continue
        value=dict(correct_options=[v.upper()for v in values],page=l['page'],bbox=[min(a['bbox'][0]for a in area),min(a['bbox'][1]for a in area),max(a['bbox'][2]for a in area),max(a['bbox'][3]for a in area)],source_line=' '.join(a['text']for a in area),method='explicit_source_key_and_row_geometry')
        if not values:value['no_correct_option']=True
        if ref in out and out[ref]['correct_options']!=value['correct_options']:conflicts.append(ref)
        out[ref]=value
    for ref in conflicts:out[ref]['conflict']=True
    return out

def explanation_for(key, keys, parent, doc, table_cache=None):
    """Keep source workings beside one booklet key, without the neighbouring key."""
    if not key or not parent:return None
    start=(key['page'],key['bbox'][1]-2)
    following=sorted((v['page'],v['bbox'][1]-2)for v in keys.values()if (v['page'],v['bbox'][1]-2)>start)
    end=following[0]if following else(parent['end_exclusive']['page'],parent['end_exclusive']['bbox'][1])
    rows=[]
    for l in parent['lines']:
        point=(l['page'],l['bbox'][1])
        if point<start or point>=end:continue
        # Remove only the question-number/key columns on the first row.
        if l['page']==key['page']and abs(l['bbox'][1]-key['bbox'][1])<5 and l['bbox'][0]<key['bbox'][2]+2:continue
        rows.append(l)
    if not rows:return None
    return gold.reconstruct(dict(lines=rows,start=fr.where(rows[0]),end_exclusive=dict(page=end[0],bbox=[0,end[1],0,end[1]],column=0)),doc,table_cache)

def extract(parent, doc, answer_parent=None, answer_doc=None, global_keys=None, scope='', table_cache=None):
    if table_cache is None:table_cache={}
    def render(q):return afm_tables.normalize(gold.reconstruct(q,doc,table_cache),doc)
    lines=parent['lines'];groups=option_groups(lines);starts=[]
    roman=any(ROMAN.match(l['text'])for l in lines) and parent['format']=='MCQ_CASE' and parent['reference']not in ('MCQ',)
    # Case booklets also use MCQ_CASE, with decimal restarted question numbers.
    if scope=='booklet':roman=False
    for g in groups:
        a=g[0][0];floor=starts[-1]['options'][-1][0]+1 if starts else 0
        candidates=[i for i in range(floor,a)if number(lines[i]['text'],roman) and lines[i]['bbox'][0]<=g[0][1]['bbox'][0]+3]
        if not candidates:continue
        at=candidates[-1];ref=number(lines[at]['text'],roman)
        starts.append(dict(at=at,ref=ref,options=g))
    result=[];printed_counts=Counter(x['ref']for x in starts);occurrences=Counter()
    for n,item in enumerate(starts):
        at=item['at'];stop=starts[n+1]['at']if n+1<len(starts)else len(lines)
        occurrences[item['ref']]+=1
        boundaries=[i for i in range(at+1,stop)if CASE.fullmatch(lines[i]['text'])]
        if boundaries:stop=boundaries[0]
        segment=lines[at:stop]
        question=render(dict(lines=lines[at:item['options'][0][0]],start=fr.where(lines[at]),end_exclusive=fr.where(item['options'][0][1])))
        choices=[];issues=[]
        if [m[2]for m in item['options']]!=list('ABCD'):issues.append('ambiguous_duplicate_printed_option_labels_no_relabelling_allowed')
        for k,(oi,marker,label)in enumerate(item['options']):
            end=item['options'][k+1][0]if k<3 else stop
            body=deepcopy(lines[oi:end])
            if re.match(r'^[A-D]\.',body[0]['text'],re.I):
                original=body[0];body[0]['text']=re.sub(r'^[A-D]\.\s*','',original['text'],flags=re.I);joined=''.join(s['text']for s in original.get('spans',[]));remove=re.match(r'^\s*[A-D]\.\s*',joined,re.I);remain=remove.end()if remove else 0;spans=[]
                for span in original.get('spans',[]):
                    ss=deepcopy(span)
                    if remain>=len(ss['text']):remain-=len(ss['text']);continue
                    if remain:ss['text']=ss['text'][remain:];remain=0
                    spans.append(ss)
                body[0]['spans']=spans
            else:body[0]=common.strip_choice(body[0])
            body=[l for l in body if l['text'].strip()]
            if not body:issues.append('incomplete_option_'+label);continue
            endpos=fr.where(lines[end])if end<len(lines)else parent['end_exclusive']
            rich=render(dict(lines=body,start=fr.where(marker),end_exclusive=endpos))
            choices.append(dict(id=label,html=rich['body_html'],source_page=marker['page'],source_bbox=marker['bbox'],checks=rich['fidelity'],structure=rich['blocks']))
            issues+=['option_'+label+'_'+w for w in rich['warnings']]
        previous_cases=[i for i in range(at)if CASE.fullmatch(lines[i]['text'])]
        cstart=previous_cases[-1]if previous_cases else 0
        # Decimal MTP/exam numbering is global; shared facts begin at their
        # case heading. RTP/booklet reference carries the parent case identity.
        firstcase=next((s['at']for s in starts if s['at']>cstart),at)
        facts=lines[cstart:firstcase]
        scenario=None
        if facts and (previous_cases or roman or scope=='booklet'):
            sr=render(dict(lines=facts,start=fr.where(facts[0]),end_exclusive=fr.where(lines[firstcase])))
            scenario=dict(key='AFM-MCQ-CASE-'+gold.sha(scope+'|'+str(pos(facts[0])))[:40],html=sr['body_html'],checks=sr['fidelity'],source_location=dict(start=fr.where(facts[0]),end_exclusive=fr.where(lines[firstcase])))
            issues+=sr['warnings']
        local=keys_in(answer_parent['lines'],answer_doc)if answer_parent and answer_doc else{}
        key=(local if roman or scope=='booklet'else(global_keys or local)).get(item['ref'])
        if printed_counts[item['ref']]>1:
            issues.append('duplicate_printed_question_number_requires_answer_content_review');key=None
        if not key:issues.append('matching_explicit_answer_key_missing')
        if key and key.get('conflict'):issues.append('conflicting_explicit_answer_key_rows')
        if key and key.get('no_correct_option'):issues.append('official_key_reports_no_correct_option')
        if key and len(key['correct_options'])!=1:issues.append('multiple_key_options_requires_owner_decision')
        if len(choices)!=4:issues.append('incomplete_source_options')
        issues+=question['warnings']
        if not question['fidelity']['passed']or any(not o['checks']['passed']for o in choices):issues.append('question_or_option_numerical_integrity_failed')
        ref=parent['reference']+'('+item['ref']+')'if roman else'Case '+parent['reference']+' Q'+item['ref']if scope=='booklet'else item['ref']
        explanation=explanation_for(key,local,answer_parent,answer_doc,{})if scope=='booklet'and key else None
        section=('case_'+parent['reference']+'_mcq')if scope=='booklet'else'rtp_case_'+parent['reference']+'_mcq'if roman else'part_i_mcq'
        if occurrences[item['ref']]>1:section+=':repeat_'+str(occurrences[item['ref']])+'_pdf_'+str(lines[at]['page'])+'_y_'+str(round(lines[at]['bbox'][1]))
        result.append(dict(reference=ref,local_reference=item['ref'],case_reference=parent['reference']if roman or scope=='booklet'else'',question=question,options=choices,scenario=scenario,key=key,explanation=explanation,issues=sorted(set(issues)),region=dict(lines=segment,start=fr.where(lines[at]),end_exclusive=fr.where(lines[stop])if stop<len(lines)else parent['end_exclusive']),source_section=section))
    return result
