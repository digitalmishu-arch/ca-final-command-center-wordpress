"""Private layout discovery and conservative geometry reconstruction.

No PDF text, pixels or owner decisions are public fixtures. Automatic checks
never establish academic verification or permission to publish.
"""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import html
import re
import fitz

VERSION = 'gold-layout-2'


def sha(value):
    return hashlib.sha256(value if isinstance(value, bytes) else value.encode()).hexdigest()


def tokens(value):
    return Counter(re.findall(r'\S+', re.sub(r'\s+', ' ', html.unescape(value))))


def numeric(value):
    return Counter(re.findall(r'[−–-]?\(?\d[\d,]*(?:\.\d+)?\)?%?|[₹`%£$]', html.unescape(value)))


AMOUNT=r'[₹`£$]?\s*[−–-]?\(?\d[\d,]*(?:\.\d+)?\)?%?(?:\s+or\s+\d[\d,]*(?:\.\d+)?)?'


def word_groups(page,box):
    # Font-specific currency glyphs can have a different top coordinate while
    # sharing the printed baseline. Group by vertical overlap, not y0 alone.
    words=[w for w in page.get_text('words') if fitz.Rect(box).contains(fitz.Point((w[0]+w[2])/2,(w[1]+w[3])/2))]
    groups=[]
    for w in sorted(words,key=lambda w:((w[1]+w[3])/2,w[0])):
        group=next((g for g in reversed(groups) if min(g['bottom'],w[3])-max(g['top'],w[1])>=.55*min(g['bottom']-g['top'],w[3]-w[1])),None)
        if group is None:group=dict(top=w[1],bottom=w[3],words=[]);groups.append(group)
        group['words'].append(w);group['top']=min(group['top'],w[1]);group['bottom']=max(group['bottom'],w[3])
    return [(g['top'],' '.join(w[4] for w in sorted(g['words'],key=lambda w:w[0]))) for g in sorted(groups,key=lambda g:g['top'])]


def cell_text(page, box):
    text='\n'.join(t for _,t in word_groups(page,box))
    # Clipping by a cell can discard the taller currency glyph even when the
    # word's centre belongs in that cell. Inspect intersecting original spans.
    if any(span.get('font')=='Rupee' and '`' in span['text'] and fitz.Rect(span['bbox']).intersects(fitz.Rect(box)) for block in page.get_text('dict')['blocks'] for line in block.get('lines',[]) for span in line['spans']):text=text.replace('`','₹')
    return text


def qualify_table(rows, box):
    """Prose flowing around a decorative rule is never a financial table."""
    if len(rows)<2 or max(map(len,rows),default=0)<2:return False,'too_few_rows_or_columns'
    numeric_cells=sum(bool(re.search(r'\d',c or '')) for r in rows[1:] for c in r[1:])
    right=[c or '' for r in rows[1:] for c in r[1:] if c]
    def amount_lines(cell):
        lines=[v.strip() for v in cell.splitlines() if v.strip()]
        return bool(lines) and sum(bool(re.fullmatch(AMOUNT+r'|[₹`£$−–-]',v)) for v in lines)/len(lines)>=.75
    prose=sum(len(re.findall(r'\w+',c))>12 and not amount_lines(c) for c in right)
    if not numeric_cells:return False,'no_repeated_financial_values'
    if prose>max(1,len(right)//3):return False,'prose_is_not_a_table'
    if len(right)>3 and numeric_cells/len(right)<.35:return False,'weak_numeric_column_evidence'
    if box[2]-box[0]<80:return False,'implausibly_narrow_table'
    return True,''


def table_model(page, table, region):
    """Use actual cell boxes, not indentation, to associate labels and amounts."""
    box=list(table.bbox)
    if not fitz.Rect(region).contains(fitz.Rect(box)):return None,'table_crosses_question_boundary'
    rows=table.extract();ok,reason=qualify_table(rows,box)
    if not ok:return None,reason
    rects=[list(c) for c in table.cells if c]
    xs=sorted(set(round(x,1) for c in rects for x in (c[0],c[2])))
    ys=sorted(set(round(y,1) for c in rects for y in (c[1],c[3])))
    cells=[];seen=set()
    for c in rects:
        key=tuple(round(x,1) for x in c)
        if key in seen:continue
        seen.add(key)
        near=lambda values,x:min(range(len(values)),key=lambda i:abs(values[i]-x))
        col,endcol=near(xs,c[0]),near(xs,c[2]);row,endrow=near(ys,c[1]),near(ys,c[3])
        cells.append(dict(row=row,column=col,rowspan=max(1,endrow-row),colspan=max(1,endcol-col),text=cell_text(page,c),bbox=c))
    # Every source word in the table must occur once in the reconstructed cells.
    original=cell_text(page,box);rendered=' '.join(c['text'] for c in cells)
    if tokens(original)!=tokens(rendered):return None,'table_word_assignment_not_bijective'
    if numeric(original)!=numeric(rendered):return None,'table_numeric_assignment_failed'
    heading=bool(re.search(r'^(?:TEST|Particulars|Date|Year|Description|Account|Stage)\b',(rows[0][0] or '').strip(),re.I) or not (rows[0][0] or '').strip() and all(len((c or '').split())<12 for c in rows[0][1:]))
    headers=2 if heading and len(rows)>1 and not (rows[1][0] or '').strip() and all(not c or re.fullmatch(r'\s*[₹`£$]\s*',c) for c in rows[1][1:]) else int(heading)
    return dict(type='table',page=page.number+1,bbox=box,cells=cells,rows=len(ys)-1,columns=len(xs)-1,
                numeric_check=True,word_check=True,header_rows=headers,visual_status='needs_owner_comparison'),''


def expand_financial_rows(page,model):
    """A ruled body cell may contain many printed accounting rows.

    Infer rows from repeated monetary baselines across its numeric columns,
    retaining blank cells for interim totals. Never zip unrelated text lines.
    """
    result=[];row_number=0
    for physical in range(model['rows']):
        cells=[c for c in model['cells'] if c['row']==physical];bands={}
        for c in cells:
            bands[c['column']]=word_groups(page,c['bbox'])
        amounts=[y for c in cells if c['column']>0 for y,t in bands[c['column']] if re.fullmatch(AMOUNT+r'(?:\s*(?:lakhs?|crores?|millions?|billions?|thousands?|units?|shares?|paise|kg|MT))?',t,re.I)]
        section_rows=[y for c in cells if c['column']==0 for y,t in bands[c['column']] if re.fullmatch(r'(?:Assets|Liabilities|Equity(?: and Liabilities)?|Other equity|Reserves and surplus|Non.current (?:assets|liabilities)|Current (?:assets|liabilities)|Shareholders?[’\']? equity|Financial (?:assets|liabilities)|Cash flows from[^:]*|Adjustments for[^:]*):?',re.sub(r'^[\s•▪\-–]+','',t),re.I)]
        anchors=[]
        for y in sorted(amounts+section_rows):
            if not anchors or y-anchors[-1]>5:anchors.append(y)
        if physical<model.get('header_rows',1) or len(anchors)<2 or any(c['rowspan']>1 for c in cells):
            result.extend({**c,'row':row_number} for c in cells);row_number+=1;continue
        for n,y in enumerate(anchors):
            # Amounts normally align with the first line of an accounting stub.
            # Midpoints wrongly move a wrapped label/working-note continuation
            # to the next amount. Keep continuation lines until the next start.
            top=y-4 if n else min([c['bbox'][1] for c in cells]+[v[0] for group in bands.values() for v in group])-1
            bottom=anchors[n+1]-4 if n+1<len(anchors) else max(c['bbox'][3] for c in cells)
            for c in cells:
                text='\n'.join(t for baseline,t in bands[c['column']] if top<=baseline<bottom)
                if '₹' in c['text']:text=text.replace('`','₹')
                result.append({**c,'row':row_number,'rowspan':1,'text':text,'bbox':[c['bbox'][0],top,c['bbox'][2],bottom]})
            row_number+=1
    source=' '.join(c['text'] for c in model['cells']);target=' '.join(c['text'] for c in result)
    if tokens(source)!=tokens(target) or numeric(source)!=numeric(target):return model
    return {**model,'cells':result,'rows':row_number,'row_method':'printed_numeric_baselines'}


def table_html(model):
    rows=[]
    for row in range(model['rows']):
        cells=[]
        for c in sorted((c for c in model['cells'] if c['row']==row),key=lambda c:c['column']):
            header=row<model.get('header_rows',1);stub=not header and c['column']==0
            tag='th' if header or stub else 'td';attrs=(' scope="col"' if header else ' scope="row"' if stub else '')
            if c['colspan']>1:attrs+=' colspan="'+str(c['colspan'])+'"'
            if c['rowspan']>1:attrs+=' rowspan="'+str(c['rowspan'])+'"'
            cells.append('<'+tag+attrs+'>'+html.escape(c['text']).replace('\n','<br>')+'</'+tag+'>')
        rows.append('<tr>'+''.join(cells)+'</tr>')
    h=model.get('header_rows',1)
    return '<table>'+('<thead>'+''.join(rows[:h])+'</thead>' if h else '')+'<tbody>'+''.join(rows[h:])+'</tbody></table>'


def borderless_tables(selected,used):
    """Require repeated aligned numeric rows; prose indentation is insufficient."""
    bands=[]
    for i,l in selected:
        if i in used:continue
        if not bands or abs(bands[-1][0]-l['bbox'][1])>4:bands.append([l['bbox'][1],[]])
        bands[-1][1].append((i,l))
    candidates=[]
    for y,rows in bands:
        amounts=[(i,l) for i,l in rows if re.fullmatch(r'[₹`£$]?\s*[−–-]?\(?\d[\d,]*(?:\.\d+)?\)?%?',l['text'])]
        labels=[(i,l) for i,l in rows if (i,l) not in amounts]
        if amounts and labels and max(l['bbox'][0] for _,l in amounts)>min(l['bbox'][0] for _,l in labels)+100 and sum(len(l['text'].split()) for _,l in labels)<=14:
            candidates.append((y,rows,amounts,labels))
    chunks=[]
    for item in candidates:
        if not chunks or item[0]-chunks[-1][-1][0]>34:chunks.append([])
        chunks[-1].append(item)
    models=[]
    for chunk in chunks:
        if len(chunk)<3:continue
        ends=[]
        for _,_,amounts,_ in chunk:
            for _,l in amounts:
                right=l['bbox'][2];group=next((g for g in ends if abs(g[0]-right)<6),None)
                if group:group[1]+=1
                else:ends.append([right,1])
        ends=sorted(g[0] for g in ends if g[1]>=2)
        if not ends or len(ends)>6:continue
        if any(any(min(abs(l['bbox'][2]-x) for x in ends)>=6 for _,l in amounts) for _,_,amounts,_ in chunk):continue
        cells=[];indices=[]
        for row,(_,items,amounts,labels) in enumerate(chunk):
            labels.sort(key=lambda x:x[1]['bbox'][0]);label=' '.join(l['text'] for _,l in labels);lb=[min(l['bbox'][0] for _,l in labels),min(l['bbox'][1] for _,l in labels),max(l['bbox'][2] for _,l in labels),max(l['bbox'][3] for _,l in labels)]
            cells.append(dict(row=row,column=0,rowspan=1,colspan=1,text=label,bbox=lb))
            for col,right in enumerate(ends,1):
                found=[l for _,l in amounts if abs(l['bbox'][2]-right)<6]
                text=' '.join(l['text'] for l in found);box=found[0]['bbox'] if found else [right-40,lb[1],right,lb[3]]
                cells.append(dict(row=row,column=col,rowspan=1,colspan=1,text=text,bbox=box))
            indices.extend(i for i,_ in items)
        source=' '.join(l['text'] for _,items,_,_ in chunk for _,l in items)
        if numeric(source)!=numeric(' '.join(c['text'] for c in cells)):continue
        bbox=[min(c['bbox'][0] for c in cells),min(c['bbox'][1] for c in cells),max(c['bbox'][2] for c in cells),max(c['bbox'][3] for c in cells)]
        models.append((dict(type='table',method='aligned_financial_rows',header_rows=0,page=chunk[0][1][0][1]['page'],bbox=bbox,cells=cells,rows=len(chunk),columns=len(ends)+1,numeric_check=True,visual_status='needs_owner_comparison'),indices))
    return models


def reconstruct(q,document,table_cache=None):
    lines=q['lines'];blocks=[];warnings=[];used=set()
    for pn in sorted({l['page'] for l in lines}):
        selected=[(i,l) for i,l in enumerate(lines) if l['page']==pn];page=document[pn-1]
        start=q.get('start',{});end=q.get('end_exclusive',{});top=start.get('bbox',[0,0,0,0])[1]-2 if start.get('page')==pn else 0;bottom=end.get('bbox',[0,page.rect.height,0,0])[1] if end.get('page')==pn else page.rect.height;region=[0,top,page.rect.width,bottom]
        try:
            if table_cache is not None and pn in table_cache:tables=table_cache[pn]
            else:
                tables=page.find_tables(strategy='lines_strict').tables
                if table_cache is not None:table_cache[pn]=tables
        except Exception:tables=[];warnings.append('table_detection_failed_page_'+str(pn))
        for t in tables:
            if not fitz.Rect(region).intersects(t.bbox):continue
            model,error=table_model(page,t,region)
            if not model:
                if error not in ('no_repeated_financial_values','prose_is_not_a_table','weak_numeric_column_evidence','too_few_rows_or_columns'):warnings.append(error+'_page_'+str(pn))
                continue
            model=expand_financial_rows(page,model)
            inside=[(i,l) for i,l in selected if fitz.Rect(model['bbox']).contains(fitz.Point((l['bbox'][0]+l['bbox'][2])/2,(l['bbox'][1]+l['bbox'][3])/2))]
            if not inside:continue
            used.update(i for i,_ in inside);blocks.append(model)
        for model,indices in borderless_tables(selected,used):
            blocks.append(model);used.update(indices)
    paragraph=None
    for i,l in enumerate(lines):
        if i in used:paragraph=None;continue
        bbox=l['bbox'];text=l['text'];heading=l.get('bold') and bool(re.match(r'Ind AS|Required\b|Scenario\b|Working|Statement|Balance Sheet',text,re.I))
        starts=bool(re.match(r'^(?:\(?[a-zivx]+\)|\d+\.|Required\b)',text))
        join=paragraph and not heading and not starts and paragraph['page']==l['page'] and 0<=bbox[1]-paragraph['bbox'][3]<=max(9,l.get('size',11)*.95) and abs(bbox[0]-paragraph['bbox'][0])<24
        pieces=[]
        for span in l.get('spans',[]):
            part=html.escape(span['text'].replace('`','₹') if span.get('font')=='Rupee' else span['text']);flags=span.get('flags',0)
            if flags&1:part='<sup>'+part+'</sup>'
            if flags&2:part='<em>'+part+'</em>'
            if flags&16:part='<strong>'+part+'</strong>'
            pieces.append(part)
        value=''.join(pieces) or html.escape(text)
        if join:paragraph['html']+=('' if paragraph['html'].endswith('-') else ' ')+value;paragraph['bbox'][2]=max(paragraph['bbox'][2],bbox[2]);paragraph['bbox'][3]=bbox[3]
        else:
            paragraph=dict(type='heading' if heading else 'paragraph',page=l['page'],bbox=list(bbox),html=value);blocks.append(paragraph)
    blocks.sort(key=lambda b:(b['page'],b['bbox'][1],b['bbox'][0]))
    currency_placeholder=any(s.get('font')=='Rupee' and '`' in s.get('text','') for l in lines for s in l.get('spans',[]))
    if currency_placeholder:
        # ICAI's mixed-font tables also use the same currency placeholder in
        # substituted fonts. Preserve the original cell value as evidence.
        for block in blocks:
            if block['type']=='table':
                for cell in block['cells']:
                    if '`' in cell['text']:cell['original_text']=cell['text'];cell['text']=cell['text'].replace('`','₹');cell['symbol_normalization']='ICAI currency placeholder backtick to ₹; original cell retained'
            elif '`' in block['html']:block['html']=block['html'].replace('`','₹')
    body='\n'.join(table_html(b) if b['type']=='table' else '<'+('h4' if b['type']=='heading' else 'p')+'>'+b['html']+'</'+('h4' if b['type']=='heading' else 'p')+'>' for b in blocks)
    raw_plain='\n'.join(l['text'] for l in lines);normalizations=['Rupee font backtick rendered as ₹'] if any(s.get('font')=='Rupee' for l in lines for s in l.get('spans',[])) else [];plain=raw_plain.replace('`','₹') if normalizations else raw_plain;rendered=html.unescape(re.sub('<[^>]*>',' ',body));before,after=numeric(plain),numeric(rendered)
    fidelity=dict(passed=before==after,missing=dict(before-after),added=dict(after-before),numeric_tokens_source=sum(before.values()))
    if not fidelity['passed']:warnings.append('numeric_or_symbol_fidelity_failed')
    number_lines=[l for l in lines if re.fullmatch(r'[₹`(−–-]?\d[\d,.%() −–-]*',l['text']) and l['bbox'][0]>q.get('start',{}).get('bbox',[72])[0]+60]
    if len(number_lines)>=3 and not any(b['type']=='table' for b in blocks):warnings.append('possible_borderless_table_requires_geometry_review')
    return dict(schema='cafcc-rich-v2',body_html=body,plain_text=plain,blocks=blocks,source_text_sha256=sha(raw_plain),symbol_normalizations=normalizations,fidelity=fidelity,warnings=sorted(set(warnings)),transcription_status='needs_review')


def discover(document,metadata):
    import fr_corpus as old
    lines=old.all_lines(document);lefts=Counter(round(l['bbox'][0]) for l in lines if re.match(r'^\d{1,2}\.(?:\s|$)',l['text']));margin=lefts.most_common(1)[0][0] if lefts else 72
    book_style=any(re.fullmatch(r'Questions?\s+\d+',l['text'],re.I) for l in lines) and any(re.fullmatch(r'Answer',l['text'],re.I) for l in lines)
    # A sentence describing Part II in the instructions is not a section start.
    part_heading=re.compile(r'^(?:(?:ANSWERS?)(?:\s+TO|\s+OF)?\s+)?PART\s*[-–—]?\s*(II|I)\b(?=\s*(?:$|[-–—:]|Case\b|Multiple\b|Descriptive\b|Subjective\b))',re.I)
    explicit_parts=any(part_heading.match(l['text']) for l in lines)
    section_started=not (metadata['source_type']=='mtp' and explicit_parts)
    section=[];headings=[];starts=[];answer_at=None;side='answer' if metadata.get('role')=='answers' else 'question';mcq=True if metadata['source_type']=='rtp' else False;question_formats={};current_number=None
    for i,l in enumerate(lines):
        t=l['text']
        if re.match(r'^(?:SUGGESTED ANSWERS|ANSWERS|Answers of Part)',t,re.I):
            if not answer_at:answer_at=dict(index=i,page=l['page'],bbox=l['bbox'])
            side='answer';section.append(dict(kind='answers',index=i,page=l['page'],bbox=l['bbox']))
        part=part_heading.match(t)
        if part:
            mcq=part[1].upper()=='I';section_started=True;section.append(dict(kind='mcq' if mcq else 'subjective',index=i,page=l['page'],bbox=l['bbox']))
        elif not explicit_parts and re.match(r'^(?:DESCRIPTIVE|SUBJECTIVE)',t,re.I):mcq=False
        # Scope a preceding heading forward, never into the preceding question.
        if re.match(r'^Ind\s+AS\s*\d+',t,re.I) and l['bold'] and abs(l['bbox'][0]-margin)<8:headings.append(dict(index=i,page=l['page'],bbox=l['bbox'],text=t,side=side,font=l.get('font',''),size=l.get('size'),rgb=l.get('rgb'),spans=[dict(page=l['page'],bbox=l['bbox'],text=t,font=l.get('font',''),size=l.get('size'),rgb=l.get('rgb'))]))
        elif headings and headings[-1]['side']==side and 0<i-headings[-1]['index']<=3 and l['bold'] and len(t.split())<10 and not re.match(r'\d|Required|SUGGESTED|ANSWERS',t,re.I):
            headings[-1]['text']+=' '+t;headings[-1]['spans'].append(dict(page=l['page'],bbox=l['bbox'],text=t,font=l.get('font',''),size=l.get('size'),rgb=l.get('rgb')))
        explicit=re.fullmatch(r'Questions?\s+(\d+)',t,re.I)
        answer_label=re.fullmatch(r'Answer(?:\s+(\d+))?',t,re.I)
        if explicit:side='question';mcq=False;current_number=explicit[1]
        if answer_label and current_number:side='answer';mcq=False
        if not section_started:continue
        if book_style and not mcq and not explicit and not answer_label:continue
        m=re.match(r'^(?:Question\s*|Q\s*)?(\d{1,2})\.(?:\s|$)',t,re.I)
        if not explicit and not (answer_label and current_number) and (not m or abs(l['bbox'][0]-margin)>5):continue
        n=int(explicit[1] if explicit else answer_label[1] or current_number if answer_label else m[1]);current_number=str(n)
        if side=='answer' and question_formats.get(str(n))=='SUBJECTIVE':mcq=False
        if side=='question':question_formats[str(n)]='MCQ' if mcq else 'SUBJECTIVE'
        prev_heading=next((h for h in reversed(headings) if h['side']==side and h['index']<i and i-h['index']<=4),None)
        if prev_heading:mcq=False
        if side=='question':question_formats[str(n)]='MCQ' if mcq else 'SUBJECTIVE'
        # A small-number restart is meaningful only in its known document section.
        starts.append(dict(index=i,reference=str(n),side=side,format='MCQ' if mcq else 'SUBJECTIVE',heading=prev_heading))
    records=[]
    for n,start in enumerate(starts):
        stop=starts[n+1]['index'] if n+1<len(starts) else len(lines)
        next_start=starts[n+1] if n+1<len(starts) else None
        if next_start and next_start['heading'] and next_start['heading']['index']>start['index']:stop=next_start['heading']['index']
        if answer_at and start['side']=='question' and start['index']<answer_at['index']<stop:stop=answer_at['index']
        for boundary in section:
            if start['index']<boundary['index']<stop:stop=boundary['index']
        rows=lines[start['index']:stop]
        records.append(dict(reference=start['reference'],subreference='',alternative='',side=start['side'],format=start['format'],heading=start['heading'],lines=rows,start=old.where(rows[0]),end_exclusive=old.where(lines[stop]) if stop<len(lines) else dict(page=len(document),bbox=[0,document[-1].rect.height,0,document[-1].rect.height],column=0),warnings=[]))
    profile=dict(engine=VERSION,source_type=metadata['source_type'],role=metadata.get('role'),source_hash=sha(document.tobytes()) if not document.name else sha(open(document.name,'rb').read()),pages=len(document),learned_number_margin=margin,sections=section,answer_start=answer_at,headings=headings,number_starts=[{k:v for k,v in s.items() if k!='heading'} for s in starts],status='needs_owner_review',layout_notes=['Different source types require separately inspected profiles.','Numbers indented inside working notes are not question starts.'])
    return records,profile


REQUIREMENT=re.compile(r'^(?:Required\b|Calculate\b|Determine\b|Prepare\b|Explain\b|Discuss\b|Evaluate\b|How\b|What\b|Advise\b|Show\b|Compute\b|State\b|Examine\b|Assess\b|Analyse\b|Analyze\b|Comment\b|Whether\b|Is\b|Are\b)',re.I)


def reference(text):
    match=re.match(r'^(?:Question\s*|Q\s*)?(\d+)(?:\s*[-—:]?\s*Part\s+([A-Z])|\s+([A-Z])\b|\s*\(([a-z])\)(?:\s*\(([ivx]+)\))?)',text,re.I)
    if not match:return None
    part=(match[2] or match[3] or match[4] or '').lower();nested=(match[5] or '').lower()
    return match[1],'.'.join(p for p in (part,nested) if p)


def operative(line):
    return bool(REQUIREMENT.match(re.sub(r'^\([a-zivx]+\)\s*','',line['text'],flags=re.I)) or re.search(r'\b(?:Is|Are|Should|Would|Can|Does|Do|Will)\b[^?]*\?\s*$',line['text'],re.I))


def split_independent(q):
    """Split explicit requirements, not incidental lettered/roman scenario facts."""
    if q['format']!='SUBJECTIVE':return [q],None
    rows=q['lines'];starts=[]
    # Primary lettered parts share their own left edge. Deeper financial rows
    # and parenthesised facts must not restart an independent practice entry.
    part_left=None
    for i,l in enumerate(rows):
        m=re.match(r'^\(([a-z])\)\s*(.*)',l['text'])
        if m and l['bbox'][0]<=q['start']['bbox'][0]+35:
            if part_left is None:part_left=l['bbox'][0]
            if abs(l['bbox'][0]-part_left)<4:starts.append((m[1],i))
    # Roman requirement lists are scoped beneath their lettered parent.
    if any(re.match(r'^\(ii\)',l['text']) for l in rows):starts=[s for s in starts if s[0] not in ('i','v','x')]
    if len(starts)<2 or len({s[0] for s in starts})!=len(starts):
        ors=[i for i,l in enumerate(rows) if re.fullmatch(r'OR',l['text'],re.I)]
        if len(ors)==1 and any(operative(l) for l in rows[:ors[0]]) and any(operative(l) for l in rows[ors[0]+1:]):return [{**q,'alternative':alt,'lines':part,'shared_lines':[]} for alt,part in [('either',rows[:ors[0]]),('or',rows[ors[0]+1:])]],None
        return [q],None
    if any(not any(operative(l) for l in rows[a:(starts[n+1][1] if n+1<len(starts) else len(rows))]) for n,(_,a) in enumerate(starts)):return [q],dict(code='lettered_facts_or_ambiguous_requirements',reference=q['reference'])
    shared=[l for l in rows[:starts[0][1]] if not re.fullmatch(r'(?:Question\s+)?\d+\.?',l['text'],re.I)];children=[]
    for n,(ref,begin) in enumerate(starts):
        end=starts[n+1][1] if n+1<len(starts) else len(rows);part=rows[begin:end];ors=[i for i,l in enumerate(part) if re.fullmatch(r'OR',l['text'],re.I)]
        alternatives=[('',part)] if not ors else [('either',part[:ors[0]]),('or',part[ors[0]+1:])]
        for alternative,content in alternatives:
            roman=[(re.match(r'^\(([ivx]+)\)',l['text'])[1],i) for i,l in enumerate(content) if re.match(r'^\(([ivx]+)\)',l['text'])]
            nested=[]
            if len(roman)>=2 and all(any(operative(l) for l in content[begin:(roman[k+1][1] if k+1<len(roman) else len(content))]) for k,(_,begin) in enumerate(roman)):
                for k,(r,begin) in enumerate(roman):nested.append((ref+'.'+r,content[begin:(roman[k+1][1] if k+1<len(roman) else len(content))],shared+content[:roman[0][1]]))
            for child_ref,child_rows,common in nested or [(ref,content,shared)]:children.append({**q,'subreference':child_ref,'alternative':alternative,'lines':child_rows,'shared_lines':common,'start':dict(page=child_rows[0]['page'],bbox=child_rows[0]['bbox'],column=0),'parent_reference':q['reference']})
    return children,None


def exact_answer(question,paper,answer_documents):
    matches=[]
    for answer in answer_documents:
        if any(paper.get(k)!=answer.get(k) for k in ('subject_code','exam_attempt','source_type','mtp_series')):continue
        if paper.get('answer_document_hash')!=answer.get('source_hash'):continue
        for a in answer.get('records',[]):
            if a.get('side')!='answer' or a.get('format')!='SUBJECTIVE':continue
            if all((a.get(k) or '')==(question.get(k) or '') for k in ('reference','subreference','alternative')):matches.append(a)
    return matches


def paired_parts(question,answer):
    """Corroborate printed top-level letter parts in both source regions.

    An answer need not contain imperative verbs. Matching sequence, indentation
    and explicit alternative dividers provide structural evidence, not approval.
    Inner financial rows and lettered facts in an unlettered parent stay whole.
    """
    def markers(record):
        found=[];left=None
        for i,line in enumerate(record['lines']):
            m=re.match(r'^\(([a-h])\)(?:\s|$)',line['text'])
            if not m or line['bbox'][0]>record['start']['bbox'][0]+35:continue
            if left is None:
                # A new part begins next to the question/answer label, rather
                # than halfway through an unlettered financial statement.
                if i>3: return []
                left=line['bbox'][0]
            if abs(left-line['bbox'][0])<4:found.append((m[1],i))
        return found
    qm,am=markers(question),markers(answer)
    qrefs=[r for r,_ in qm];arefs=[r for r,_ in am]
    unique=list(dict.fromkeys(qrefs))
    if not qm and not am:
        # Independent roman requirements may share one scenario (for example,
        # journal entries and a consolidated statement). Facts labelled (i)/(ii)
        # cannot qualify unless every question region has an operative request
        # and the answer has the same top-level sequence.
        def romans(record):
            found=[];left=None
            for i,line in enumerate(record['lines']):
                m=re.match(r'^\(([ivx]+)\)(?:\s|$)',line['text'])
                if not m or line['bbox'][0]>record['start']['bbox'][0]+55:continue
                if left is None:left=line['bbox'][0]
                if abs(left-line['bbox'][0])<2:found.append((m[1],i))
            return found
        qr,ar=romans(question),romans(answer)
        expected=['i','ii','iii','iv','v','vi']
        if 2<=len(qr)<=6 and [r for r,_ in qr]==expected[:len(qr)] and [r for r,_ in ar]==expected[:len(qr)]:
            operative_parts=[]
            for n,(_,begin) in enumerate(qr):
                stop=qr[n+1][1] if n+1<len(qr) else len(question['lines'])
                text=' '.join(l['text'] for l in question['lines'][begin:stop]);text=re.sub(r'^\([ivx]+\)\s*','',text)
                operative_parts.append(bool(REQUIREMENT.match(text) or re.match(r'Pass\b|Recommend\b',text,re.I)))
            if all(operative_parts):qm,am=qr,ar
        if not qm:return [question],[answer],[]
    if not qm or not am or (unique!=[chr(97+i) for i in range(len(unique))] and unique!=['i','ii','iii','iv','v','vi'][:len(unique)]) or list(dict.fromkeys(arefs))!=unique:
        return [question],[answer],['printed_part_sequence_not_corroborated']
    def split(record,parts):
        out=[];rows=record['lines'];shared=[l for l in rows[:parts[0][1]] if not re.fullmatch(r'(?:Questions?\s+|Answer\s*)?\d*\.?',l['text'],re.I)]
        for n,(ref,begin) in enumerate(parts):
            stop=parts[n+1][1] if n+1<len(parts) else len(rows);content=rows[begin:stop]
            repeated=n>0 and parts[n-1][0]==ref
            has_next=n+1<len(parts) and parts[n+1][0]==ref
            dividers=[i for i,l in enumerate(content) if re.fullmatch('or',l['text'],re.I)]
            alternatives=[('or' if repeated else 'either' if has_next else '',content)]
            if dividers and not repeated and not has_next:
                if len(dividers)!=1:raise ValueError('Multiple alternative dividers need owner review.')
                at=dividers[0];alternatives=[('either',content[:at]),('or',content[at+1:])]
            for alternative,body in alternatives:
                body=[l for l in body if not re.fullmatch('or',l['text'],re.I)]
                if not body:raise ValueError('Empty alternative region.')
                start=dict(page=body[0]['page'],bbox=body[0]['bbox'],column=0)
                next_line=rows[stop] if stop<len(rows) else None
                # For an Either/Or branch, end before the divider/next branch.
                last_index=rows.index(body[-1]);boundary=rows[last_index+1] if last_index+1<len(rows) else next_line
                end=dict(page=boundary['page'],bbox=boundary['bbox'],column=0) if boundary else record['end_exclusive']
                out.append({**record,'subreference':ref,'alternative':alternative,'lines':body,'shared_lines':shared,'start':start,'end_exclusive':end,'parent_reference':record['reference']})
        return out
    questions,answers=split(question,qm),split(answer,am)
    qi=[(q['subreference'],q['alternative']) for q in questions];ai=[(q['subreference'],q['alternative']) for q in answers]
    if qi!=ai:return questions,answers,['alternative_identity_not_corroborated']
    return questions,answers,[]


def practice_parts(question,answer):
    """Also separate explicitly lettered cases within an Either/Or branch.

    Recursion is bounded and requires corroborating answer labels. Shared
    instructions remain linked common context instead of being discarded.
    """
    questions,answers,warnings=paired_parts(question,answer)
    if warnings:return questions,answers,warnings
    finalq=[];finala=[]
    for q,a in zip(questions,answers):
        if not q['alternative']:
            finalq.append(q);finala.append(a);continue
        nestedq,nesteda,issues=paired_parts(q,a)
        if issues or len(nestedq)==1:
            finalq.append(q);finala.append(a);continue
        for qq,aa in zip(nestedq,nesteda):
            qq={**qq,'subreference':q['subreference']+'.'+qq['subreference'],'alternative':q['alternative'],'shared_lines':q.get('shared_lines',[])+qq.get('shared_lines',[])}
            aa={**aa,'subreference':a['subreference']+'.'+aa['subreference'],'alternative':a['alternative']}
            finalq.append(qq);finala.append(aa)
    return finalq,finala,[]
