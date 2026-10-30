"""Private, checkpointed AFM/SFM reconciliation. Never grants rights or approval.

The original source hash and historical title remain authoritative. MTP issue
periods are separate from target attempts; only an explicit registry backed by
an ICAI announcement may resolve the latter. No other subject is processed.
"""
from collections import Counter, defaultdict
from copy import deepcopy
from pathlib import Path
import argparse, hashlib, html, json, re
import fitz
import archive_catalog as cat
import archive_integrity
import fr_corpus as fr
import gold_layout as gold

VERSION = 'afm-source-reconciliation-2'
CASE = re.compile(r'^(?:CASE\s+(?:SCENARIO|STUDY))\s*[-–:]?\s*(\d+|[IVX]+)\s*$', re.I)
ANSWER_CASE = re.compile(r'^ANSWERS?\s+TO\s+CASE\s+SCENARIO\s*(\d+)\s*$', re.I)
OPTION = re.compile(r'^(?:\(([A-D])\)|([A-D])\.)(?:\s|$)', re.I)
ROMAN = re.compile(r'^(?:\(([ivx]+)\)|([IVX]+)\.)(?:\s|$)')
CHAPTERS = ['Financial Policy and Corporate Strategy', 'Risk Management', 'Advanced Capital Budgeting Decisions',
            'Security Analysis', 'Security Valuation', 'Portfolio Management', 'Securitization', 'Mutual Funds',
            'Derivatives Analysis and Valuation', 'Foreign Exchange Exposure and Risk Management',
            'International Financial Management', 'Interest Rate Risk Management', 'Business Valuation',
            'Mergers, Acquisitions and Corporate Restructuring', 'Startup Finance']
# These are editorial search rules, not asserted official subtopic headings.
CONCEPTS = [
 (5,'Yield to maturity',r'yield\s+to\s+maturity|\bYTM\b'),
 (5,'Bond valuation',r'bond.{0,45}(?:price|valu|yield)|debenture.{0,45}(?:price|yield)'),
 (6,'Capital asset pricing model',r'\bCAPM\b|capital asset pricing|equity beta|portfolio beta'),
 (6,'Portfolio risk and return',r'portfolio|covariance|coefficient of correlation|standard deviation'),
 (7,'Securitisation',r'securiti[sz]|special purpose vehicle|\bNBFC\b.{0,80}receivables'),
 (8,'Net asset value',r'\bNAV\b|mutual fund|net asset value'),
 (9,'Options valuation and strategies',r'call option|put option|black.scholes|binomial|option premium|straddle|strangle'),
 (9,'Futures and arbitrage',r'futures? price|futures? contract|cost of carry'),
 (10,'Foreign exchange hedging',r'forward contract|forward exchange|money market hedge|exchange exposure|NOSTRO|VOSTRO|cross.currency'),
 (11,'International financial management',r'multilateral netting|international capital budgeting|foreign direct investment|political risk|overseas|subsidiar.{0,90}(?:France|Germany|currency)'),
 (12,'Interest rate derivatives',r'interest rate swap|forward rate agreement|\bFRA\b|interest rate cap|interest rate collar|floating rate loan'),
 (3,'Discounted cash flow and investment decisions',r'net present value|\bNPV\b|\bIRR\b|capital budgeting|replacement.{0,30}machine|cost of capital.{0,60}project'),
 (13,'Business valuation',r'free cash flow|\bFCFF\b|\bFCFE\b|economic value added|\bEVA\b|enterprise value|value.{0,25}(?:firm|business)'),
 (14,'Mergers and restructuring',r'merger|acquisition|take.?over|exchange ratio|buy.?back|spin.?off'),
 (15,'Startup funding',r'start.?up|unicorn|venture capital|pitch presentation|angel investor'),
 (2,'Risk management',r'value at risk|\bVaR\b|risk management'),
 (4,'Efficient market hypothesis',r'efficient market|technical analysis|relative strength index|moving average'),
 (1,'Financial policy',r'financial policy|corporate strategy|chief financial officer|\bCFO\b'),
]

def pos(line): return line['page'], round(line['bbox'][1], 1), line['bbox'][0]
def packed(value): return json.dumps(value, ensure_ascii=False, separators=(',', ':')).encode()
def slug(value): return re.sub('[^a-z0-9]+','-',value.lower()).strip('-')
def refpart(q): return ''.join('('+s+')' for s in q.get('subreference','').split('.') if s)

def identity(record, doc, target_registry):
    d=deepcopy(record['identity']); full='\n'.join(p.get_text() for p in doc)
    front=doc[0].get_text(); d['original_identity']=deepcopy(d); evidence=[]
    correction=record.get('technical_identity_review')
    if correction and correction.get('source_hash')==record['source_hash']:
        allowed={'actual_subject','source_type','role','exam_attempt','scheme'}
        if set(correction.get('fields',{}))-allowed:raise ValueError('Unsupported source identity correction')
        d.update(correction['fields']);evidence.append(correction['evidence'])
    if d.get('actual_subject')=='AFM'and re.search(r'BOOKLET\s+ON\s+CASE\s+SCENARIOS',front,re.I):
        year=re.search(r'RELEVANT\s+FOR\s+\w+[, ]+\s*(20\d{2})',front,re.I)
        d.update(actual_subject='AFM',source_type='other',role='questions_and_answers',exam_attempt=(year[1]+' case-scenario edition')if year else'Case-scenario applicability unconfirmed',series='',scheme='final_six_paper_2023')
        evidence.append('AFM title and numbered case scenarios/answer tables in the actual booklet; the printed applicability year is a collection edition label, not an examination attempt.')
    elif re.search('corrigendum',front,re.I):
        d['document_kind']='corrigendum'; evidence.append(front)
    elif record['folder_path'].lower().endswith('suggested answer') or '/Suggested Answer' in record['folder_path']:
        d['source_type']='exam'; d['role']='questions_and_answers' if re.search(r'(?im)^\s*Question\s+\d+',full) and re.search(r'(?im)^\s*Answer\s*$',full) else 'questions'
        evidence.append('Examination/suggested-answer folder corroborated by explicit Question N / Answer alternation and running attempt headings; initial MCQ cases do not make this a case booklet.')
    d['role']={'questions_role_provisional':'questions','questions_answer_section_unconfirmed':'questions_and_answers'}.get(d['role'],d['role'])
    if d.get('actual_subject')=='AFM':d['scheme']='final_six_paper_2023'
    if d['source_type']=='mtp':
        period=re.search(r'(?:Mock Test Paper\s*[-–:]?\s*(?:Series\s*[-–:]?\s*(?:I{1,3}|IV)\s*[:–-]?)?|Test Series\s*:)\s*('+ '|'.join(cat.MONTHS) +r')\s*,?\s*(20\d{2})',front,re.I)
        if period:d['document_issue_period']=period[1].title()+' '+period[2]
        num=re.search(r'MOCK TEST PAPER\s+([1-4])\b',front,re.I)
        if not d.get('series') and num:d['series']={'1':'I','2':'II','3':'III','4':'IV'}[num[1]];evidence.append('Printed MOCK TEST PAPER '+num[1]+' retained as historical test number; not inferred from filename.')
        key=d['document_issue_period']+'|'+d.get('series','')
        mapping=target_registry.get(key)
        if mapping:d['exam_attempt']=mapping['attempt'];d['target_evidence']=mapping;evidence.append('Target cycle corroborated by ICAI announcement: '+mapping['url'])
        elif not d.get('exam_attempt'):d['exam_attempt']=d['document_issue_period']+' (MTP issue; target pending)';d['target_pending']=True
        if not d.get('series'):d['series']='Unnumbered';d['series_state']='No series number printed; do not infer I or II'
    d['historical_paper_title']='Strategic Financial Management' if d['actual_subject']=='SFM' else 'Advanced Financial Management'
    d['mapping_to_current_afm']='Proposed editorial crosswalk; historical paper identity and applicability retained' if d['actual_subject']=='SFM' else 'Current AFM source'
    d['identity_evidence']=evidence;d['warnings']=[w for w in d.get('warnings',[]) if w not in ('target_attempt_not_established','mtp_series_not_recovered','source_category_not_established_from_content')]
    if d.get('target_pending'):d['warnings'].append('target_attempt_unconfirmed_issue_period_not_exam_attempt')
    if d.get('document_kind')=='corrigendum':d['warnings'].append('corrigendum_retain_original_and_targeted_amendment_separately')
    return d

def native_lines(doc):
    """AFM body extraction: no FR-specific font/height crop of real text."""
    lines=[]
    for p in doc:
        for b in p.get_text('dict')['blocks']:
            for l in b.get('lines',[]):
                spans=l['spans'];text=''.join(s['text']for s in spans).strip()
                if not text:continue
                main=max(spans,key=lambda s:len(s['text']));c=main['color'];box=[round(float(v),2)for v in l['bbox']]
                if box[1]>p.rect.height*.88 and re.match(r'^©|^The Institute of Chartered Accountants',text,re.I):continue
                if text==str(p.number+1)and box[1]>p.rect.height*.82 and (main['color']!=0 or abs((box[0]+box[2])/2-p.rect.width/2)<45):continue
                if p.number and box[1]<115 and re.match(r'^(?:SUGGESTED ANSWERS|ADVANCED FINANCIAL|STRATEGIC FINANCIAL|REVISION TEST|FINAL EXAMINATION|PAPER\s*[–-])',text,re.I):continue
                row=dict(page=p.number+1,bbox=box,text=text,font=main['font'],size=main['size'],bold=bool(main['flags']&16 or re.search('bold|black',main['font'],re.I)),rgb=[(c>>16)&255,(c>>8)&255,c&255],column=0,spans=[dict(text=s['text'],bbox=list(s['bbox']),flags=s['flags'],font=s['font'])for s in spans])
                if any(x['page']==row['page']and x['text']==text and abs(x['bbox'][0]-box[0])<1 and abs(x['bbox'][1]-box[1])<2 for x in lines[-10:]):continue
                lines.append(row)
    # Printed folios need not equal PDF page indices (front matter creates an
    # offset). Learn repeated numeric running furniture from geometry, font,
    # colour and a constant page offset, never from a fixed body-height crop.
    folios=defaultdict(list)
    for i,l in enumerate(lines):
        p=doc[l['page']-1];x,y,x1,_=l['bbox']
        if not re.fullmatch(r'\d{1,3}',l['text'])or not(y<140 or y>p.rect.height*.82)or not(x<150 or abs((x+x1)/2-p.rect.width/2)<45):continue
        key=(round(x/8),round(y/8),l['font'],round(l['size'],1),tuple(l['rgb']),int(l['text'])-l['page']);folios[key].append(i)
    omit={i for indexes in folios.values()if len({lines[j]['page']for j in indexes})>=3 for i in indexes}
    return [l for i,l in enumerate(lines)if i not in omit]

def cleaned_lines(doc):
    lines=native_lines(doc)
    # Fixed rounded y buckets can put an (a) label before its same-baseline
    # parent number when their fonts differ by a fraction of a point. Cluster
    # actual vertical centres first, then read each row from left to right.
    ordered=[]
    for pn in sorted({l['page']for l in lines}):
        pending=[];anchor=None
        for line in sorted((l for l in lines if l['page']==pn),key=lambda l:((l['bbox'][1]+l['bbox'][3])/2,l['bbox'][0])):
            cy=(line['bbox'][1]+line['bbox'][3])/2
            if pending and cy-anchor>2.5:ordered.extend(sorted(pending,key=lambda l:l['bbox'][0]));pending=[];anchor=None
            if anchor is None:anchor=cy
            pending.append(line)
        ordered.extend(sorted(pending,key=lambda l:l['bbox'][0]))
    return ordered

def make_region(lines, begin, end, doc, **fields):
    body=lines[begin:end]
    if not body:return None
    endwhere=fr.where(lines[end]) if end<len(lines) else dict(page=len(doc),bbox=[0,doc[-1].rect.height,0,doc[-1].rect.height],column=0)
    return dict(reference='',subreference='',alternative='',side='question',format='SUBJECTIVE',heading=None,lines=body,start=fr.where(body[0]),end_exclusive=endwhere,warnings=[],**fields)

def discover(doc, d):
    lines=cleaned_lines(doc); index={pos(l):i for i,l in enumerate(lines)}
    if d.get('document_kind')=='corrigendum':return [],dict(profile='corrigendum',text='\n'.join(l['text'] for l in lines),status='targeted-amendment-review')
    if d['source_type']=='other':
        starts=[]
        for i,l in enumerate(lines):
            c=CASE.fullmatch(l['text']);a=ANSWER_CASE.fullmatch(l['text'])
            if c or a:starts.append((i,'question' if c else 'answer',(c or a)[1]))
        records=[]
        for n,(i,side,ref) in enumerate(starts):
            q=make_region(lines,i,starts[n+1][0]if n+1<len(starts)else len(lines),doc)
            q.update(reference=ref,side=side,format='MCQ_CASE');records.append(q)
        return records,dict(profile='afm-case-booklet',starts=[dict(index=i,side=s,reference=r,page=lines[i]['page'])for i,s,r in starts])
    raw,profile=gold.discover(doc,dict(source_type=d['source_type'],role=d['role']),source_lines=lines)
    if d['source_type']=='exam':
        # Discover labelled books independently of repeated SUGGESTED ANSWERS furniture.
        explicit=[];current=None
        for i,l in enumerate(lines):
            m=re.fullmatch(r'Questions?\s+(?:No\.?\s*)?(\d+)',l['text'],re.I)
            a=re.fullmatch(r'Answer(?:\s+(\d+))?',l['text'],re.I)
            if m:current=m[1];explicit.append((i,'question',current))
            elif a and current:explicit.append((i,'answer',a[1]or current))
        if explicit:
            records=[]
            # MCQs precede the separately labelled descriptive section.
            cutoff=next((i for i,l in enumerate(lines)if re.match(r'^Answer\s+Key$',l['text'],re.I)),explicit[0][0])
            choices_before=[i for i,l in enumerate(lines[:cutoff])if OPTION.match(l['text'])]
            if choices_before:
                q=make_region(lines,0,cutoff,doc);q.update(reference='MCQ',format='MCQ_CASE');records.append(q)
            for n,(i,side,ref) in enumerate(explicit):
                q=make_region(lines,i,explicit[n+1][0]if n+1<len(explicit)else len(lines),doc);q.update(reference=ref,side=side);records.append(q)
            profile.update(profile='afm-labelled-suggested-answer-book',number_starts=[dict(side=s,reference=r,page=lines[i]['page'])for i,s,r in explicit]);return records,profile
    # Rebuild from accepted starts so rejected working notes do not cut content.
    starts=[];seen=set()
    anchor=next((i for i,l in enumerate(lines)if re.match(r'^ANSWERS?\s+(?:OF|TO)\s+PART\s*[–-]?\s*II',l['text'],re.I)),None)
    if d['source_type']=='mtp':
        # Parent indentation varies within one file. Learn starts from the
        # first part beside the number, not one global x-coordinate.
        subjective=next((i for i,l in enumerate(lines)if re.match(r'^(?:ANSWERS?\s+(?:OF|TO)\s+)?PART\s*[–-]?\s*II\b(?=\s*(?:$|[-–—:]|Descriptive\b|Subjective\b))',l['text'],re.I)),0)
        pool=defaultdict(list)
        for i,l in enumerate(lines):
            m=re.match(r'^([1-6])\.(?:\s|$)',l['text'])
            if i<subjective or not m or l['bbox'][0]>115:continue
            cy=sum(l['bbox'][1::2])/2
            part=bool(re.match(r'^\d+\.\s*\(a\)',l['text'],re.I))or any(re.match(r'^\(a\)',x['text'],re.I)and x['page']==l['page']and 0<x['bbox'][0]-l['bbox'][0]<75 and abs(sum(x['bbox'][1::2])/2-cy)<7 for x in lines[max(0,i-1):i+5])
            pool[m[1]].append((i,part))
        replacements=[]
        for ref,candidates in pool.items():
            preferred=[i for i,part in candidates if part]
            accepted=preferred if preferred else[i for i,_ in candidates]if len(candidates)==1 else[]
            if len(accepted)==1:
                i=accepted[0];q=make_region(lines,i,len(lines),doc);q.update(reference=ref,side='answer'if d['role']=='answers'else'question',format='SUBJECTIVE');replacements.append(q)
        raw=[q for q in raw if q['format']!='SUBJECTIVE']+replacements
        raw.sort(key=lambda q:index[pos(q['start'])])
    if d['source_type']=='rtp':
        aa=profile.get('answer_start');ai=aa.get('index')if aa else None
        margin=profile['learned_number_margin'];known={q['reference']for q in raw if q['side']=='answer'and re.match(r'^\d+\.',q['lines'][0]['text'])}
        if ai is not None:
            for i,l in enumerate(lines):
                m=re.match(r'^(\d{1,2})(?:\s|$)',l['text'])
                if i<=ai or not m or m[1]in known or abs(l['bbox'][0]-margin)>2:continue
                # A missing full stop is supported only by the corresponding
                # question sequence and a unique bare answer label.
                if not any(q['side']=='question'and q['reference']==m[1]for q in raw):continue
                hits=[x for x in lines[ai:]if re.match(r'^'+m[1]+r'(?:\s|$)',x['text'])and abs(x['bbox'][0]-margin)<2]
                if len(hits)!=1:continue
                q=make_region(lines,i,len(lines),doc);q.update(reference=m[1],side='answer',format='SUBJECTIVE');raw.append(q);known.add(m[1])
            raw.sort(key=lambda q:index[pos(q['start'])])
    for q in raw:
        at=index.get(pos(q['start']))
        if at is None:continue
        t=lines[at]['text'];ref=q['reference']
        if d['source_type']=='rtp' and not re.match(r'^'+re.escape(ref)+(r'(?:\.|\s|$)'if q['side']=='answer'else r'\.(?:\s|$)'),t):continue
        if d['source_type']=='mtp':
            if q['format']=='SUBJECTIVE' and int(ref)>6:continue
            if d['role']=='answers' and q['format']=='SUBJECTIVE' and anchor is not None and at<anchor:continue
            if q['format']=='SUBJECTIVE' and q not in replacements:
                # MTP parent labels are printed beside their first (a) part.
                # Numbered working notes can share the left margin but do not
                # carry that parent/part geometry. Never keep the first "2."
                # merely because it precedes the actual Answer 2(a).
                cy=sum(lines[at]['bbox'][1::2])/2
                inline=bool(re.match(r'^\d+\.\s*\([a-h]\)',t,re.I))
                beside=any(re.match(r'^\([a-h]\)',x['text'],re.I) and x['page']==lines[at]['page'] and 0<x['bbox'][0]-lines[at]['bbox'][0]<75 and abs(sum(x['bbox'][1::2])/2-cy)<7 for x in lines[max(0,at-1):at+5])
                if not (inline or beside):continue
        key=(q['side'],q['format'],ref)
        if key in seen:
            # Subsequent repeated working-note numbers remain inside their parent.
            continue
        seen.add(key);starts.append((at,q))
    records=[]
    for n,(at,old) in enumerate(starts):
        stop=starts[n+1][0]if n+1<len(starts)else len(lines)
        for b in profile.get('sections',[]):
            bi=index.get(pos(dict(page=b['page'],bbox=b['bbox'])))
            if bi is not None and at<bi<stop:stop=bi
        # A standalone brown RTP topic heading belongs to the following record.
        heading=old.get('heading');next_heading=None
        if n+1<len(starts) and d['source_type']=='rtp':
            ni=starts[n+1][0]
            for k in range(max(at+1,ni-4),ni):
                l=lines[k];rgb=l.get('rgb',[0,0,0]);brown=rgb[0]>70 and rgb[0]>rgb[1]*1.15 and rgb[0]>rgb[2]*1.15
                if l.get('bold') and brown and not re.match(r'^[\d(₹`]|Required|Prepare|Calculate|Working|ANSWERS|SUGGESTED|PARTICULARS',l['text'],re.I):next_heading=k;break
            if next_heading is not None and next_heading<stop:stop=next_heading
        q=make_region(lines,at,stop,doc)
        if not q:continue
        q.update(reference=old['reference'],side=old['side'],format=old['format'],heading=heading)
        if d['source_type']=='rtp':
            if at:
                before=[l for l in lines[max(0,at-4):at]if l.get('bold')and l['bbox'][0]<180 and len(l['text'])<150 and not re.match(r'^\d|QUESTIONS|ANSWERS|SUGGESTED|Particulars',l['text'],re.I)]
                if before:q['heading']=dict(text=before[-1]['text'],spans=[before[-1]])
            body=' '.join(l['text']for l in q['lines']);letters=[(OPTION.match(l['text'])[1]or OPTION.match(l['text'])[2]).upper()for l in q['lines']if OPTION.match(l['text'])]
            complete=sum(letters[k:k+4]==list('ABCD')for k in range(max(0,len(letters)-3)))
            q['format']='MCQ_CASE'if q['side']=='question'and complete and re.search(r'choose|correct answer|following questions',body,re.I)else'SUBJECTIVE'
        records.append(q)
    profile.update(profile='afm-'+d['source_type']+'-source-aware',accepted_starts=[dict(side=q['side'],format=q['format'],reference=q['reference'],page=q['start']['page'])for q in records])
    return records,profile

def split_question(q, a, split_nested_requirements=False):
    def inline_part(record):
        if not record:return record
        record=deepcopy(record)
        if not record['lines']:return record
        line=record['lines'][0];m=re.match(r'^\d+\.\s*(?=\([a-zivx]+\))',line['text'],re.I)
        if not m:return record
        line['original_parent_label_text']=line['text'];line['original_parent_label_bbox']=list(line['bbox']);line['text']=line['text'][m.end():]
        # Some PDFs put "1. (a)" in one text span. The later printed (b)/(c)
        # labels establish the part indentation; the number's x-coordinate
        # must not make (a) look like a different hierarchy level.
        following=[l['bbox'][0]for l in record['lines'][1:]if re.match(r'^\([b-h]\)',l['text'])and 0<=l['bbox'][0]-line['bbox'][0]<=65]
        if following:line['bbox']=list(line['bbox']);line['bbox'][0]=min(following);record['start']=fr.where(line)
        joined=''.join(s['text']for s in line.get('spans',[]));prefix=re.match(r'^\s*\d+\.\s*(?=\([a-zivx]+\))',joined,re.I);left=prefix.end()if prefix else 0;spans=[]
        for span in line.get('spans',[]):
            ss=deepcopy(span)
            if left>=len(ss['text']):left-=len(ss['text']);continue
            if left:ss['text']=ss['text'][left:];left=0
            spans.append(ss)
        line['spans']=spans;return record
    q=inline_part(q);a=inline_part(a)
    warnings=[]
    if a:
        # Alternative solution methods inside an answer are not alternative
        # question occurrences. Keep them inside that part unless the question
        # itself prints an Either/Or divider.
        answer_for_split=deepcopy(a)
        if not any(re.fullmatch('OR',l['text'],re.I)for l in q['lines']):
            answer_for_split['lines']=[{**l,'text':'Alternative solution method','spans':[dict(text='Alternative solution method',font=l.get('font',''),flags=0,bbox=l['bbox'])]}if re.fullmatch('OR',l['text'],re.I)else l for l in a['lines']]
        try:qs,ans,warnings=gold.practice_parts(q,answer_for_split,allow_roman_parts=split_nested_requirements)
        except ValueError as error:
            qs,issue=gold.split_independent(q);ans=[];warnings=['answer_alternative_boundary_conflict: '+str(error)]
        # Splitting decisions may use a neutral marker, but retained answer
        # prose must always be the exact original source line, including OR.
        originals={pos(l):l for l in a['lines']}
        for aa in ans:aa['lines']=[originals.get(pos(l),l)for l in aa['lines']]
        if warnings:
            qs,issue=gold.split_independent(q);ans=[]
            # Recover uniquely printed parts even when another answer part is
            # missing/reordered. Never substitute a neighbouring whole answer.
            if q.get('source_type')in('mtp','exam'):
                try:
                    source_q,_,qw=gold.paired_parts(q,q,allow_roman_parts=split_nested_requirements)
                    if not qw and any(x.get('subreference')for x in source_q):qs=source_q;issue=None
                except ValueError:pass
            try:
                source_a,_,aw=gold.paired_parts(answer_for_split,answer_for_split,allow_roman_parts=split_nested_requirements)
                if not aw:ans=source_a
            except ValueError:pass
            for aa in ans:aa['lines']=[originals.get(pos(l),l)for l in aa['lines']]
            warnings=['question_boundary_'+issue['code']]if issue else['answer_parent_part_profile_requires_review']
    else:qs,issue=gold.split_independent(q);ans=[];warnings=[issue['code']]if issue else[]
    # A single printed (a) is still a subpart, not an unnumbered parent.
    if len(qs)==1 and not qs[0].get('subreference'):
        for l in qs[0]['lines'][:4]:
            m=re.match(r'^\(([a-h])\)',l['text'])
            if m:qs[0]={**qs[0],'subreference':m[1]};break
    if len(ans)==1 and len(qs)==1 and qs[0].get('subreference')and not ans[0].get('subreference'):
        m=next((re.match(r'^\(([a-h])\)',l['text'])for l in ans[0]['lines'][:4]if re.match(r'^\(([a-h])\)',l['text'])),None)
        if m and m[1]==qs[0]['subreference']:ans[0]={**ans[0],'subreference':m[1]}
    # Roman numerals and operative verbs do not establish independent problems.
    # A source-specific decision may opt in only after distinct problem/marks
    # and corresponding solution boundaries have been compared.
    if not split_nested_requirements:return qs,ans,list(dict.fromkeys(warnings))
    # Independently operative roman requirements retain linked shared facts.
    def romans(record):
        hits=[];left=None
        for i,l in enumerate(record['lines']):
            m=re.match(r'^\(([ivx]+)\)(?:\s|$)',l['text'])
            if not m:continue
            if left is None:left=l['bbox'][0]
            if abs(l['bbox'][0]-left)<3:hits.append((m[1],i))
        seq=['i','ii','iii','iv','v','vi']
        return hits if 2<=len(hits)<=6 and [s for s,_ in hits]==seq[:len(hits)]else[]
    expanded=[];expanded_answers=[];amap={(x.get('subreference',''),x.get('alternative','')):x for x in ans}
    for child in qs:
        matched=amap.get((child.get('subreference',''),child.get('alternative','')));qm=romans(child)
        independent=qm and all(any(gold.operative(l)for l in child['lines'][start:(qm[n+1][1]if n+1<len(qm)else len(child['lines']))])for n,(_,start)in enumerate(qm))
        if not independent:expanded.append(child);expanded_answers+=([matched]if matched else[]);continue
        am=romans(matched)if matched else[];same=bool(am and [s for s,_ in am]==[s for s,_ in qm])
        for n,(ref,at)in enumerate(qm):
            stop=qm[n+1][1]if n+1<len(qm)else len(child['lines']);body=child['lines'][at:stop];newref=(child.get('subreference','')+'.'if child.get('subreference')else'')+ref
            expanded.append({**child,'subreference':newref,'lines':body,'shared_lines':child.get('shared_lines',[])+child['lines'][:qm[0][1]],'start':fr.where(body[0]),'end_exclusive':fr.where(child['lines'][stop])if stop<len(child['lines'])else child['end_exclusive']})
            if same:
                aa=am[n][1];ae=am[n+1][1]if n+1<len(am)else len(matched['lines']);ab=matched['lines'][aa:ae];expanded_answers.append({**matched,'subreference':newref,'lines':ab,'start':fr.where(ab[0]),'end_exclusive':fr.where(matched['lines'][ae])if ae<len(matched['lines'])else matched['end_exclusive']})
    return expanded,expanded_answers,list(dict.fromkeys(warnings))

def tags(q,a=None):
    heading=(q.get('heading')or{}).get('text','');text=' '.join(l['text']for l in q['lines'])
    requirement=' '.join(l['text']for l in q['lines']if gold.operative(l))
    answer=' '.join(l['text']for l in (a or{}).get('lines',[]))
    found=[]
    for chapter,label,rx in CONCEPTS:
        m=re.search(rx,requirement+' '+heading,re.I);basis='heading/operative requirement'
        if not m:
            m=re.search(rx,text,re.I);basis='question and answer corroboration'
            if m and not re.search(rx,answer,re.I) and not re.search(rx,heading,re.I):m=None
        if m:found.append(dict(chapter=chapter,chapter_title=CHAPTERS[chapter-1],label=label,origin='editorial',evidence=m[0],basis=basis))
    exact=[i+1 for i,t in enumerate(CHAPTERS)if re.sub('[^a-z]','',t.lower())==re.sub('[^a-z]','',heading.lower())]
    if exact and not any(x['chapter']==exact[0]for x in found):found.insert(0,dict(chapter=exact[0],chapter_title=CHAPTERS[exact[0]-1],label=CHAPTERS[exact[0]-1],origin='source_heading',evidence=heading,basis='exact printed heading'))
    return found

def corroboration(q,a):
    def numbers(rows):return set(re.findall(r'\d[\d,]*(?:\.\d+)?', ' '.join(l['text']for l in rows))) - {'1','2','3','4','5','6','7','8','9','10','100'}
    def words(rows):return set(re.findall(r'\b[a-z]{5,}\b',' '.join(l['text']for l in rows).lower()))-{'which','their','there','given','following','company','limited','question','answer','calculate','amount','value','years','therefore','would','should','total'}
    ns=sorted(numbers(q['lines'])&numbers(a['lines']));ws=sorted(words(q['lines'])&words(a['lines']))
    return dict(common_numeric_references=ns[:30],common_content_terms=ws[:30],corroborated=bool(ns and ws or len(ws)>=3),method='Exact source context, printed parent/part identity plus internal numerical/terminology overlap; not independent academic verification')

def process_source(r, targets, out, profiles_only=False):
    target=out/(r['file_id']+'.json')
    fingerprint=gold.sha(Path(__file__).read_bytes()+packed(targets)+r['source_hash'].encode()+str(profiles_only).encode())
    if target.exists():
        prior=json.loads(target.read_text())
        if prior.get('engine_hash')==fingerprint:return dict(file_id=r['file_id'],status=prior['status'],checkpoint='retained',path=str(target))
    assert gold.sha(Path(r['local_path']).read_bytes())==r['source_hash']
    with fitz.open(r['local_path'])as doc:
        ident=identity(r,doc,targets)
        if len(r['scanned_or_empty_pages'])>=len(doc)*.8:
            result=dict(status='ocr_source_requires_manual_transcription_review',identity=ident,records=[],pages=len(doc),warnings=['No native reconstruction asserted for image-only PDF; prior OCR retained separately.'])
        else:
            records,profile=discover(doc,ident);cache={};rows=[]
            for q in records:
                rich=None
                if not profiles_only:
                    rich=gold.reconstruct(q,doc,cache);rich['integrity_issues']=archive_integrity.inspect(rich)
                rows.append(dict(region=q,rich=rich))
            result=dict(status='source_regions_prepared',identity=ident,records=rows,profile=profile,pages=len(doc))
    result.update(file_id=r['file_id'],source_hash=r['source_hash'],engine=VERSION,engine_hash=fingerprint)
    cat.write(target,result);return dict(file_id=r['file_id'],status=result['status'],regions=len(result['records']),path=str(target))

def run(manifest, targets, output, profiles_only=False):
    from concurrent.futures import ProcessPoolExecutor,as_completed
    out=cat.private(output);out.mkdir(parents=True,exist_ok=True)
    files=json.loads(Path(manifest).read_text())['records'];assert all(r['collection_subject']in('AFM','CASE')for r in files)
    registry=json.loads(Path(targets).read_text());summary=[]
    with ProcessPoolExecutor(max_workers=3)as pool:
        for f in as_completed([pool.submit(process_source,r,registry,out/'documents',profiles_only)for r in files]):
            result=f.result();summary.append(result);cat.write(out/'checkpoint.json',dict(engine=VERSION,documents=summary,pending=len(files)-len(summary)));print(json.dumps(result),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('manifest');p.add_argument('--targets',required=True);p.add_argument('--output',required=True);p.add_argument('--profiles-only',action='store_true');a=p.parse_args();run(a.manifest,a.targets,a.output,a.profiles_only)
