"""Versioned, conservative PDF layout segmentation. Private evidence only.

PyMuPDF exposes spans, coordinates, font size/weight and RGB colour. No online
model, keyword-frequency score, reproduction licence, or academic approval is
inferred. Unknown layouts are review exceptions, not successful extractions.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

PROFILE = {'id':'icai-bos-single-column', 'version':2, 'body_left':108,
           'left_tolerance':9, 'header_y':140, 'footer_fraction':0.84,
           'heading_rgb':[144,87,30], 'colour_tolerance':45}


def norm(text):
    return re.sub(r'[^a-z0-9]+',' ',text.lower()).strip()


def location(line):
    return {k:line[k] for k in ('page','bbox','column')}


def document_evidence(text):
    kind='rtp' if re.search('REVISION TEST PAPER',text,re.I) else 'mtp' if re.search('MOCK TEST PAPER',text,re.I) else 'exam' if re.search('EXAMINATION',text,re.I) else 'unknown'
    paper=re.search(r'PAPER\s*[–:-]\s*(\d)',text,re.I)
    answers=bool(re.search('SUGGESTED ANSWERS?|ANSWER KEY',text,re.I))
    questions=bool(re.search(r'\bQUESTIONS\b',text,re.I))
    months='January|February|March|April|May|June|July|August|September|October|November|December'
    return dict(observed_type=kind,attempts=sorted(set(re.findall(r'((?:'+months+r')\s*,?\s*20\d{2})\s+EXAMINATION',text,re.I))),
                series=re.findall(r'Series\s*[–:-]?\s*([IVX]+|\d+)',text,re.I),paper=paper[1] if paper else '',
                role='questions_and_answers' if answers and questions else 'answer_reference' if answers else 'question_paper')


def styled_heading(line, profile):
    t=line['text'];rgb=line['rgb'];target=profile['heading_rgb']
    colour=sum(abs(a-b) for a,b in zip(rgb,target))<profile['colour_tolerance']
    return (line['bold'] and (colour or line['size']>=13) and len(t)<180 and
            not t.endswith('?') and not re.match(r'^(?:\d|\(|[IVX]+\.)',t) and
            not re.search(r'\b(?:choose|following questions|calculate its|do you|explain why)\b',t,re.I))


def read_pdf(path, profile=None):
    import fitz
    profile={**PROFILE,**(profile or {})}
    with fitz.open(path) as document:
        lines=[];page_info=[]
        for page in document:
            page_lines=[]
            for block in page.get_text('dict')['blocks']:
                for line in block.get('lines',[]):
                    spans=line['spans'];text=''.join(s['text'] for s in spans).strip()
                    if not text:continue
                    main=max(spans,key=lambda s:len(s['text']))
                    c=main['color'];box=[round(float(x),2) for x in line['bbox']]
                    page_lines.append(dict(page=page.number+1,text=text,bbox=box,
                        font=main['font'],size=round(main['size'],2),
                        bold=bool(main['flags']&16 or re.search(r'bold|black',main['font'],re.I)),
                        rgb=[(c>>16)&255,(c>>8)&255,c&255],column=0))
            page_lines.sort(key=lambda l:(round(l['bbox'][1]/3),l['bbox'][0]))
            page_info.append(dict(page=page.number+1,width=page.rect.width,height=page.rect.height,
                                  text_characters=sum(len(l['text']) for l in page_lines)))
            lines.extend(page_lines)
    # Identify genuinely separated columns by overlapping y ranges at distinct
    # left margins. Tables also trigger this: ambiguity is safer than false order.
    exceptions=[]
    for info in page_info:
        if info['text_characters']<80:
            exceptions.append(dict(code='scan_or_sparse_page',page=info['page'],blocking=True))
        candidates=[l for l in lines if l['page']==info['page'] and len(l['text'])>35 and 140<l['bbox'][1]<info['height']*.84]
        for right in candidates:
            if right['bbox'][0]<info['width']*.5:continue
            if any(left['bbox'][0]<info['width']*.4 and left['bbox'][2]<=right['bbox'][0]+5 and abs(left['bbox'][1]-right['bbox'][1])<8 for left in candidates):
                exceptions.append(dict(code='possible_multiple_columns',page=info['page'],blocking=True));break
    full='\n'.join(l['text'] for l in lines)
    meta=document_evidence(full)
    for info in page_info:info['document_evidence']=meta
    body=[l for l in lines if profile['header_y']<l['bbox'][1]<page_info[l['page']-1]['height']*profile['footer_fraction']]
    for index,l in enumerate(body):l['index']=index
    return body,page_info,exceptions,profile


def question_marker(line, profile):
    if abs(line['bbox'][0]-profile['body_left'])>profile['left_tolerance']:return None
    m=re.match(r'^(\d{1,2}(?:\.\d{1,2})?)[.)]?(?=\s|$)\s*(.*)$',line['text'])
    if not m:return None
    # A bare integer without a dot/closing bracket is normally a table value.
    if '.' not in line['text'][:len(m[1])+1] and ')' not in line['text'][:len(m[1])+1]:return None
    return m[1]


def segment(lines, profile=None):
    profile={**PROFILE,**(profile or {})};questions=[];exceptions=[]
    active=False;answers=False;section='questions';section_counter=0
    pending=[];current=None;context=None;previous_heading=None;scenario_wait=False
    all_answer_lines=[];seen=Counter();answer_sections=[]

    def end(at):
        nonlocal current
        if current:
            current['end_exclusive']=location(at)
            current['private_text']='\n'.join(l['text'] for l in current.pop('_lines'))
            questions.append(current);current=None

    for l in lines:
        text=l['text'];upper=text.upper()
        if re.match(r'^SUGGESTED\s+ANSWERS?|^ANSWER\s+KEY|^SUGGESTED\s+HINTS',upper):
            end(pending[0] if pending else l);pending=[];answers=True;active=False
            answer_sections.append(location(l));continue
        if answers:
            all_answer_lines.append(l);continue
        if re.match(r'^(?:PART\s*[–-]?\s*I\s*:\s*ACADEMIC UPDATE)',upper):
            active=False;continue
        if (upper=='QUESTIONS' or re.match(r'^PART\s*II\s*:\s*QUESTIONS',upper) or
                re.match(r'^PART\s*[AB12].*(?:MULTIPLE|DESCRIPTIVE|SUBJECTIVE)',upper)):
            if current:end(l)
            active=True;pending=[];context=None
            section_counter+=1
            section='mcq' if 'MULTIPLE' in upper else 'descriptive' if re.search('DESCRIPTIVE|SUBJECTIVE',upper) else 'questions'
            if section_counter>1 and section=='questions':section='questions-'+str(section_counter)
            continue
        if not active:continue
        if re.match(r'^Case\s+(?:Scenario|Study)\b',text,re.I):
            end(pending[0] if pending else l);pending=[];context={'label':text,'start':location(l)}
            previous_heading=None
            scenario_wait=True
            continue
        if re.search(r'Based on.*facts|On the basis.*facts|From the information|Multiple Choice Questions',text,re.I):
            scenario_wait=False
        heading=styled_heading(l,profile)
        if heading:
            # Consecutive styled lines form one heading. Keep exact span evidence.
            if not pending:end(l)
            pending.append(l);continue
        ref=question_marker(l,profile)
        if scenario_wait and ref and '.' not in ref and not pending:continue
        if ref:
            if context and 'end_exclusive' not in context:context['end_exclusive']=location(l)
            key=(section,ref)
            # A restart at 1 creates a separate context, never merges another Q1.
            if seen[key] and ref in ('1','1.1'):
                section_counter+=1;section='restart-'+str(section_counter);key=(section,ref)
            if seen[key]:
                exceptions.append(dict(code='duplicate_question_number',section=section,reference=ref,page=l['page'],blocking=True))
                continue
            end(pending[0] if pending else l)
            if pending:
                scenario_wait=False
                previous_heading={'text':' '.join(h['text'] for h in pending),
                    'spans':[{k:h[k] for k in ('text','font','size','bold','rgb','page','bbox','column')} for h in pending]}
                pending=[]
            seen[key]+=1
            current=dict(section=section,reference=ref,subreference='',start=location(l),
                heading=previous_heading,scenario=context,kind='unknown',_lines=[l],warnings=[])
        elif current:
            current['_lines'].append(l)
        elif pending:
            # A nonstyled continuation before a new question is ambiguous. Keep
            # the evidence, never append this heading to the previous question.
            if not exceptions or exceptions[-1].get('code')!='heading_without_question' or exceptions[-1].get('page')!=l['page']:
                exceptions.append(dict(code='heading_without_question',page=l['page'],blocking=False))
    if current:
        last=lines[-1];end(last)
    # Detect options inside the bounded question, not the next question's heading.
    for q in questions:
        if q['scenario'] and q['scenario'].get('end_exclusive'):
            a=q['scenario']['start'];b=q['scenario']['end_exclusive']
            q['private_scenario_text']='\n'.join(l['text'] for l in lines if (l['page'],l['bbox'][1])>=(a['page'],a['bbox'][1]) and (l['page'],l['bbox'][1])<(b['page'],b['bbox'][1]))
        options=re.findall(r'^\s*\(([a-d])\)\s*(.*)',q['private_text'],re.M)
        q['kind']='mcq' if set(k for k,_ in options)>={'a','b','c','d'} else 'unknown'
        if q['heading'] and re.search(r'descriptive|subjective',q['heading']['text'],re.I):q['kind']='unknown'
        if q['kind']=='mcq' and q['section'].startswith('questions'):
            q['section']='mcq'
        elif q['kind']!='mcq' and q['heading'] and q['section'].startswith('questions'):
            q['section']='descriptive'
        q['private_options']=[dict(key=k,text=t) for k,t in options]
        q['subparts']=subparts(q,lines)
    return questions,all_answer_lines,exceptions,answer_sections


def subparts(question, lines):
    """Return separately bounded requirements. MCQ options are excluded.

    Uppercase Roman I–V introduce AFM case MCQs; lowercase/parenthesised
    markers in prose are only candidates and require operative language.
    """
    start=question['start'];end=question['end_exclusive']
    selected=[l for l in lines if (l['page'],l['bbox'][1])>=(start['page'],start['bbox'][1]) and
              (l['page'],l['bbox'][1])<(end['page'],end['bbox'][1])]
    out=[]
    for i,l in enumerate(selected):
        m=re.match(r'^([IVX]{1,5})\.\s*(.*)',l['text'])
        if not m and question['kind']!='mcq':
            m=re.match(r'^\(([a-zivx]{1,5})\)\s*(.*)',l['text'])
            if m and not re.search(r'calculate|determine|explain|discuss|analyse|analyze|state|compute|advise|evaluate|identify',
                                   ' '.join(x['text'] for x in selected[i:i+3]),re.I):m=None
        if m:
            out.append(dict(reference=m[1],start=location(l),candidate=True))
    # Duplicate markers in facts/requirements are not silently combined.
    counts=Counter(p['reference'] for p in out)
    for n,p in enumerate(out):
        p['end_exclusive']=out[n+1]['start'] if n+1<len(out) else end
        p['ambiguous']=counts[p['reference']]>1
    return out


def answer_candidates(question, lines, profile=None):
    """Left-margin, styled answer starts, separated from nested working notes."""
    profile={**PROFILE,**(profile or {})};found=[]
    for l in lines:
        if question_marker(l,profile)!=question['reference']:continue
        if not l['bold']:continue
        found.append({**location(l),'evidence':'left-margin bold answer marker'})
    return found


def identify(lines, declared):
    text='\n'.join(l['text'] for l in lines);kind=declared.get('source_type')
    # Body lines exclude running headers; validate full document metadata in runner.
    return dict(source_type=kind,subject=declared['subject'],attempt=declared['attempt'],
                mtp_series=declared.get('mtp_series',''),paper=declared.get('paper',''),
                profile=PROFILE['id']+'@'+str(PROFILE['version']),
                review_required=kind not in ('rtp','mtp','exam') or (kind=='mtp' and not declared.get('mtp_series')))


def standard(text):
    m=re.search(r'\bInd\s*AS\s*(\d+)\b',text,re.I)
    return 'Ind AS '+m[1] if m else None


def operative_requirement(body):
    """Keep wrapped requirement lines together, excluding options/background."""
    lines=body.splitlines();chunks=[]
    for i,text in enumerate(lines):
        if not re.search(r'\b(?:what|which|calculate|determine|analy[sz]e|state|examine|compute|advise|explain|discuss|required)\b',text,re.I):continue
        chunk=[]
        for next_line in lines[i:i+12]:
            if re.match(r'^\s*\([a-d]\)',next_line):break
            chunk.append(next_line)
            if '?' in next_line:break
        chunks.append(' '.join(chunk))
    return ' '.join(chunks)


def classify(question, taxonomy, subject, edition_key):
    heading=question.get('heading');body=question['private_text']
    requirement=operative_requirement(body)
    concept=None;method='semantic analysis';reason=[]
    if heading and not re.search(r'^(?:Multiple Choice|Descriptive|Theoretical|Integrated Case|Independent MCQ)',heading['text'],re.I):
        concept=standard(heading['text']) or heading['text']
        method='heading-supported';reason.append('Preceding styled heading introduces this bounded question/group.')
    # MCQ requirements take precedence over inherited scenario/group headings.
    # These are transparent concept rules, not an academic inference/approval model.
    rules=[(r'\brevenue\b|contract extended|modification in the contract','Ind AS 115','Revenue recognition'),
           (r'lease term|lease liability|right of use|ROU asset','Ind AS 116','Lease accounting'),
           (r'defer(?:red)? tax|tax rate','Ind AS 12','Deferred tax measurement'),
           (r'related part|under Ind AS 24','Ind AS 24','Related-party identification and disclosure'),
           (r'yield to maturity|\bYTM\b','Security Valuation','Yield to maturity')]
    topics=[];additional=[]
    if question['kind']=='mcq' or not concept:
        matches=[(c,t) for pattern,c,t in rules if re.search(pattern,requirement,re.I)]
        if len({c for c,t in matches})==1:
            concept=matches[0][0];topics=[matches[0][1]];method='mixed' if heading else 'semantic analysis'
            reason.append('Operative requirement supports the proposed concept; options/background alone do not establish a tag.')
        elif len(matches)>1:
            additional=[{'concept':c,'editorial_topic':t} for c,t in matches]
            reason.append('Several operative concepts detected; primary classification needs owner review.')
    if heading and not topics:
        detail=[(r'modification|extended','Contract modification'),(r'upfront payment|payment to a customer','Consideration payable to a customer'),
                (r'ESOP|share.based','Group share-based payment arrangements'),(r'exchange difference|foreign operations','Foreign-operation exchange differences'),
                (r'error|restat','Correction of prior-period errors'),(r'netting','Multilateral netting'),(r'yield|YTM','Yield to maturity')]
        topics=[name for pattern,name in detail if re.search(pattern,body,re.I)]
    if concept=='Ind AS 115':
        if re.search(r'modification|extended',requirement,re.I):topics=['Contract modifications']
        elif re.search(r'remaining total revenue',requirement,re.I):topics=['Remaining consideration after contract modification']
        elif re.search(r'Year\s*[12]',requirement,re.I):topics=['Period-specific revenue recognition']
    if concept and norm(concept)=='securitization' and re.search(r'instrument|originator|special purpose|obligor|agent|trust',requirement,re.I):
        topics=['Securitisation theory — instruments and participants']
    nodes=[]
    for n in taxonomy:
        if n['edition_key']!=edition_key or (subject!='IBS' and n['subject_code']!=subject):continue
        if not concept:continue
        match=standard(n['title'])==concept if concept.startswith('Ind AS') else norm(re.sub(r'^Chapter\s+\d+\s*:\s*','',n['title'],flags=re.I))==norm(concept)
        if match and n['node_type'] in ('chapter','unit'):nodes.append(n)
    # Enrich selected units with their exact edition-specific parent chapter.
    index={n['node_key']:n for n in taxonomy}
    for n in list(nodes):
        parent=index.get(n.get('parent_key'))
        if parent and parent['node_type']=='chapter' and parent not in nodes:nodes.append(parent)
    return dict(concept=concept,method=method,reasoning=' '.join(reason) or 'No reliable heading or operative concept rule; owner semantic classification required.',
                official_nodes=nodes,editorial_topics=topics,editorial_subtopics=[],confidence='provisional',
                primary_chapter=next((n['node_key'] for n in nodes if n['node_type']=='chapter'),None),
                primary_unit=next((n['node_key'] for n in nodes if n['node_type']=='unit'),None),
                primary_topic={'label':topics[0],'origin':'editorial','status':'needs_review'} if topics else None,
                primary_subtopic=None,
                historical_edition=edition_key,taxonomy_match=bool(nodes),owner_state='needs_review',additional_supported_concepts=additional)


def identity(source_hash, section, reference, subreference=''):
    return hashlib.sha256('|'.join([source_hash,section,reference,subreference]).encode()).hexdigest()
