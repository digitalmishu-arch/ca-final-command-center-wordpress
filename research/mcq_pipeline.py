"""Private MCQ extraction: source-scoped question/case/option/key evidence.

No option or correct answer is inferred. A source key with ambiguous selection
semantics is held for the owner. Source PDFs and derived prose are never fixtures.
"""
from pathlib import Path
from collections import Counter
import argparse,copy,hashlib,html,json,re
import fitz
from fr_corpus import all_lines,where
from gold_layout import discover,reconstruct

VERSION='mcq-layout-4'
CASE=re.compile(r'^Case\s+Scenario\s*[-–:]?\s*(?:[IVX]+|\d+)\s*$',re.I)
CHOICE=re.compile(r'^\(([A-D])\)\s*(.*)$',re.I)


def digest(value):return hashlib.sha256(value if isinstance(value,bytes)else value.encode()).hexdigest()
def position(line):return (line['page'],round(line['bbox'][1],1),line['bbox'][0])


def running_footer(line,document):
    # A bare printed page number in the bottom margin is not an option value.
    page=document[line['page']-1];return bool(re.fullmatch(r'\d{1,3}',line['text'])and line['bbox'][1]>page.rect.height*.84 and line['bbox'][0]>page.rect.width*.70)


def region(lines,start,end,document):
    selected=[copy.deepcopy(l)for l in lines if position(start)<=position(l)<position(end) and not running_footer(l,document)]
    if not selected:return dict(body_html='',plain_text='',blocks=[],fidelity=dict(passed=False),warnings=['empty_region'])
    return reconstruct(dict(lines=selected,start=where(start),end_exclusive=where(end)),document)


def strip_choice(line):
    line=copy.deepcopy(line);m=CHOICE.match(line['text'])
    if not m:return line
    prefix=len(line['text'])-len(m[2]);line['text']=m[2]
    # Span text may include a leading space missing from the stripped line text.
    joined=''.join(s['text']for s in line.get('spans',[]));match=re.match(r'^\s*\([A-Da-d]\)\s*',joined)
    remove=match.end()if match else prefix;spans=[]
    for span in line.get('spans',[]):
        s=copy.deepcopy(span)
        if remove>=len(s['text']):remove-=len(s['text']);continue
        if remove:s['text']=s['text'][remove:];remove=0
        spans.append(s)
    line['spans']=spans
    return line


def key_regions(path,kind):
    """Recognise exact source-key layouts, excluding descriptive answers/workings."""
    doc=fitz.open(path);lines=all_lines(doc);keys={};exceptions=[]
    if kind in ('rtp','mtp'):
        begin=next((i for i,l in enumerate(lines)if re.search(r'Answer\s+to\s+Multiple\s+Choice|ANSWER\s+(?:TO|OF)\s+PART\s*[-–:]?\s*I\b',l['text'],re.I)),None)
        if begin is None:return {},[dict(code='answer_key_section_missing')]
        key_left=next((l['bbox'][0]for l in lines[begin+1:]if re.match(r'^1\.',l['text'])),0)
        end=next((i for i,l in enumerate(lines[begin+1:],begin+1)if re.search(r'Answers?\s+(?:of|to)\s+Part\s*[-–:]?\s*II',l['text'],re.I)),len(lines));area=lines[begin:end]
        for line in area:
            t=line['text'];direct=re.match(r'^(\d{1,2})\.\s*Option\s*\(([A-D])\)',t,re.I);number=re.fullmatch(r'(\d{1,2})\.',t)
            if direct:ref=direct[1];letter=direct[2].upper();evidence=t;box=line['bbox']
            elif number:
                center=(line['bbox'][1]+line['bbox'][3])/2
                paired=[x for x in area if x['page']==line['page']and x['bbox'][0]>line['bbox'][2]and abs((x['bbox'][1]+x['bbox'][3])/2-center)<5 and re.match(r'^Option\s*\(([A-D])\)',x['text'],re.I)]
                if not paired:
                    # The first following descriptive answer ends the RTP key.
                    if keys and int(number[1])>max(map(int,keys))and abs(line['bbox'][0]-key_left)<8:break
                    continue
                if len(paired)!=1:exceptions.append(dict(reference=number[1],code='option_key_row_geometry_ambiguous'));continue
                x=paired[0];ref=number[1];letter=re.match(r'^Option\s*\(([A-D])\)',x['text'],re.I)[1].upper();evidence=t+' '+x['text'];box=[line['bbox'][0],min(line['bbox'][1],x['bbox'][1]),x['bbox'][2],max(line['bbox'][3],x['bbox'][3])]
            else:continue
            value=dict(correct_options=[letter],page=line['page'],bbox=box,source_line=evidence,method='explicit_option_label_with_row_geometry')
            if ref in keys and keys[ref]['correct_options']!=value['correct_options']:exceptions.append(dict(reference=ref,code='conflicting_source_key_rows'))
            keys[ref]=value
    elif kind=='exam':
        begin=next((i for i,l in enumerate(lines)if re.fullmatch(r'Answer\s+Key',l['text'],re.I)),None)
        if begin is None:return {},[dict(code='answer_key_section_missing')]
        end=next((i for i,l in enumerate(lines[begin+1:],begin+1)if re.match(r'^Part\s*[-–:]?\s*II\s*[:–-]',l['text'],re.I)),len(lines));area=lines[begin:end]
        for l in area:
            m=re.fullmatch(r'(\d{1,2})\.',l['text'])
            if not m:continue
            center=(l['bbox'][1]+l['bbox'][3])/2
            candidates=[a for a in area if a['page']==l['page'] and a['bbox'][0]>l['bbox'][2] and abs((a['bbox'][1]+a['bbox'][3])/2-center)<5 and re.fullmatch(r'\([A-D]\)(?:\s+and\s+\([A-D]\))?',a['text'],re.I)]
            if len(candidates)!=1:exceptions.append(dict(reference=m[1],code='answer_key_row_geometry_ambiguous'));continue
            a=candidates[0];keys[m[1]]=dict(correct_options=re.findall(r'\(([A-D])\)',a['text'],re.I),page=l['page'],bbox=[l['bbox'][0],min(l['bbox'][1],a['bbox'][1]),a['bbox'][2],max(l['bbox'][3],a['bbox'][3])],source_line=l['text']+' '+a['text'],method='explicit_key_table_row')
    return keys,exceptions


def extract_group(group):
    qpath=Path(group['question_path']);apath=Path(group['answer_path']);qhash=digest(qpath.read_bytes());ahash=digest(apath.read_bytes());doc=fitz.open(qpath);lines=all_lines(doc);raw,profile=discover(doc,dict(source_type=group['source_type'],role='questions_and_answers'if group['source_type']in('rtp','exam')else'questions'));
    if group.get('layout_profile')in ('six-paper-layout-discovery-2','six-paper-layout-discovery-3'):
        import archive_profiles
        raw,_events=archive_profiles.phases(raw,lines,group['source_type'])
    questions=[q for q in raw if q['format']=='MCQ'and q['side']=='question'];
    first=questions[0]['start']if questions else None
    if not first:return [],dict(code='mcq_starts_missing'),[]
    last_end=max((q['end_exclusive']for q in questions),key=position)
    # An answer-key table is never the continuation of the last MCQ.
    key_start=next((l for l in lines if re.fullmatch(r'Answer\s+Key',l['text'],re.I)and position(l)>position(first)),None)
    if key_start and position(key_start)<position(last_end):last_end=key_start
    questions=[q for q in questions if position(q['start'])<position(last_end)]
    cases=[l for l in lines if CASE.match(l['text'])and position(l)<position(last_end)];case_data=[]
    for n,start in enumerate(cases):
        end=cases[n+1]if n+1<len(cases)else last_end;members=[q for q in questions if position(start)<position(q['start'])<position(end)]
        if not members:continue
        end=members[0]['start'];model=region(lines,start,end,doc);ranges=re.findall(r'Questions?\s*(?:Nos?\.?\s*)?(\d+)\s*(?:to|and|[-–])\s*(\d+)',model['plain_text'],re.I);limits=tuple(map(int,ranges[-1]))if ranges else None
        case_data.append(dict(key='MCQ-CASE-'+digest(qhash+'|'+str(position(start)))[:32],start=where(start),end_exclusive=end,range=limits,content=model))
    keys,key_errors=key_regions(apath,group['source_type']);records=[]
    for index,q in enumerate(questions):
        start=q['start'];end=questions[index+1]['start']if index+1<len(questions)else last_end
        boundaries=[c['start']for c in case_data if position(start)<position(c['start'])<position(end)]
        if boundaries:end=min(boundaries,key=position)
        if position(last_end)<position(end):end=last_end
        body=[copy.deepcopy(l)for l in lines if position(start)<=position(l)<position(end) and not running_footer(l,doc)]
        markers=[(i,l,CHOICE.match(l['text']))for i,l in enumerate(body)if CHOICE.match(l['text'])]
        sequence=None
        for k in range(max(0,len(markers)-3)):
            group_markers=markers[k:k+4]
            if [x[2][1].upper()for x in group_markers]==list('ABCD')and max(x[1]['bbox'][0]for x in group_markers)-min(x[1]['bbox'][0]for x in group_markers)<16:sequence=group_markers
        warnings=[];options=[];stem=None
        if not sequence:warnings.append('four_complete_source_options_not_identified');stem=region(lines,start,end,doc)
        else:
            stem=region(lines,start,sequence[0][1],doc)
            for n,(at,marker,m)in enumerate(sequence):
                stop=sequence[n+1][0]if n+1<len(sequence)else len(body);option_lines=body[at:stop];option_lines[0]=strip_choice(option_lines[0]);option_lines=[l for l in option_lines if l['text'].strip()]
                if not option_lines:model=dict(body_html='',plain_text='',fidelity=dict(passed=False),warnings=['empty_option'])
                else:model=reconstruct(dict(lines=option_lines,start=where(marker),end_exclusive=where(sequence[n+1][1])if n+1<len(sequence)else end),doc)
                options.append(dict(id=m[1].upper(),html=model['body_html'],source_label=m[1],source_page=marker['page'],source_bbox=marker['bbox'],checks=model['fidelity'],structure=model.get('blocks',[])))
                warnings+=['option_'+m[1].upper()+':'+w for w in model['warnings']]
        scenario=next((c for c in case_data if c['range']and c['range'][0]<=int(q['reference'])<=c['range'][1]),None)
        # A case is linked only when its source says which question range it covers.
        if not scenario and any(position(c['start'])<position(start)and not c['range']for c in case_data):warnings.append('common_facts_question_range_requires_review')
        warnings += [e['code']for e in key_errors if e.get('reference')==q['reference']]
        key=keys.get(q['reference']);key_policy='single'if key and len(key['correct_options'])==1 else'needs_owner_decision'
        if not key:warnings.append('matching_explicit_answer_key_missing')
        elif key_policy!='single':warnings.append('multiple_key_options_selection_policy_requires_owner_decision')
        if any(not o['checks']['passed']for o in options)or not stem['fidelity']['passed']:warnings.append('question_or_option_numeric_integrity_failed')
        if scenario and not scenario['content']['fidelity']['passed']:warnings.append('shared_scenario_numeric_integrity_failed')
        for m in [stem]+([scenario['content']]if scenario else[]):warnings+=m['warnings']
        stable='MCQ-'+digest(qhash+'|part_i_mcq|'+q['reference'])[:48]
        record=dict(stable_id=stable,source_occurrence_id='MCO-'+digest(qhash+'|part_i_mcq|'+q['reference'])[:48],subject_code=group['subject_code'],source_type=group['source_type'],exam_attempt=group['exam_attempt'],mtp_series=group.get('mtp_series',''),issue_period=group.get('issue_period',''),edition_key=group['edition_key'],scheme='new_scheme',section='part_i_mcq',reference=q['reference'],source_key=group['question_source_key'],source_hash=qhash,official_url=group['question_url'],question_page=start['page'],question_location=dict(start=start,end_exclusive=end),question_html=stem['body_html'],question_checks=stem['fidelity'],question_structure=stem['blocks'],options=options,scenario=dict(key=scenario['key'],source_hash=qhash,html=scenario['content']['body_html'],checks=scenario['content']['fidelity'],structure=scenario['content']['blocks'],question_range=list(scenario['range']),source_location=dict(start=scenario['start'],end_exclusive=scenario['end_exclusive']))if scenario else None,answer=dict(source_key=group['answer_source_key'],source_hash=ahash,official_url=group['answer_url'],page=key['page']if key else'',key_evidence=key,question_source_hash=qhash,question_reference=q['reference'],subject_code=group['subject_code'],source_type=group['source_type'],exam_attempt=group['exam_attempt'],mtp_series=group.get('mtp_series','')),correct_options=key['correct_options']if key else[],key_policy=key_policy,key_verified=bool(key),explanation_html='',academic_review_status='needs_review',publication_status='draft',classification_origin='provisional',tags=[],exceptions=sorted(set(warnings)),rights_mode='licensed_public',attribution='The Institute of Chartered Accountants of India (ICAI). Source: the exact owner-selected PDF and its corresponding answer key.',record_revision=1,extractor=VERSION)
        records.append(record)
    # No source-numeric key may be silently reused across sections or series.
    report=dict(source_key=group['question_source_key'],source_hash=qhash,answer_hash=ahash,candidates=len(records),explicit_keys=len(keys),options_complete=sum(len(r['options'])==4 for r in records),case_scenarios=len(case_data),key_errors=key_errors,missing_references=sorted(set(str(n)for n in range(1,group['expected_count']+1))-set(r['reference']for r in records)),exceptions=[dict(stable_id=r['stable_id'],reference=r['reference'],exceptions=r['exceptions'])for r in records if r['exceptions']],question_profile=profile,answer_key_profile='explicit_option_labels'if group['source_type']!='exam'else'key_table_geometry')
    return records,report,case_data


def run(manifest_path,output):
    manifest=json.loads(Path(manifest_path).read_text());out=Path(output);out.mkdir(parents=True,exist_ok=True);all_records=[];reports=[]
    for group in manifest['groups']:
        records,report,cases=extract_group(group);all_records+=records;reports.append(report);target=out/group['question_source_key'];target.mkdir(exist_ok=True);(target/'candidates.json').write_text(json.dumps(records,indent=2));(target/'layout-profile.json').write_text(json.dumps(report,indent=2));(target/'case-scenarios.json').write_text(json.dumps(cases,indent=2))
    (out/'all-candidates.json').write_text(json.dumps(all_records,indent=2));(out/'coverage.json').write_text(json.dumps(dict(engine=VERSION,groups=reports,total=len(all_records),academic_approval=False),indent=2));return all_records,reports

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('manifest');p.add_argument('output');a=p.parse_args();records,reports=run(a.manifest,a.output);print(json.dumps([dict(source=r['source_key'],candidates=r['candidates'],options_complete=r['options_complete'],explicit_keys=r['explicit_keys'],exceptions=len(r['exceptions']))for r in reports]))
