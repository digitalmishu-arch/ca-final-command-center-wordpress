"""Conservative AFM repair of vertically merged financial table stubs."""
from collections import defaultdict
from copy import deepcopy
import re
import html
import gold_layout as gold

def merged_stub(model):
    return any(c['column']==0 and c['rowspan']>1 and len(c['text'].splitlines())>=3 for c in model['cells'])

def formula_fragments(blocks):
    runs=[];current=[]
    def finish():
        if len(current)>=6 and sum(bool(re.search(r'[A-Za-zΑ-Ωα-ω=+−^√∑*/÷()]',x['text']))for x in current)>=2:runs.append(list(current))
        current.clear()
    for b in blocks:
        text=html.unescape(re.sub('<[^>]+>','',b.get('html',''))).strip()
        if b['type']=='paragraph'and 0<len(text)<=5 and re.fullmatch(r'[\dA-Za-zΑ-Ωα-ω\s=+−–^√∑*/÷().,%\-]+',text):current.append(dict(text=text,page=b.get('page'),bbox=b.get('bbox')))
        else:finish()
    finish();return runs

def repair(model,page):
    if not merged_stub(model):return model,False
    groups=[(c,gold.word_groups(page,c['bbox']))for c in model['cells']]
    monetary=[]
    for c,lines in groups:
        if c['column'] and c['colspan']==1:
            monetary.extend((y,c['column'])for y,text in lines if re.fullmatch(gold.AMOUNT,text))
    bands=[]
    for y,col in sorted(monetary):
        if not bands or y-bands[-1][0]>4:bands.append([y,set()])
        bands[-1][1].add(col)
    anchors=[y for y,cols in bands if len(cols)>=2]
    anchors+=[min(y for y,_ in lines)for c,lines in groups if c['colspan']>1 and lines]
    anchors=sorted(anchors)
    if len(anchors)<3:return model,False
    combined=defaultdict(list);spans={}
    for c,lines in groups:
        for y,text in lines:
            row=max((i for i,a in enumerate(anchors)if a<=y+4),default=0)
            if '₹'in c['text']:text=text.replace('`','₹')
            combined[(row,c['column'])].append((y,text));spans[(row,c['column'])]=c
    cells=[]
    for row,y in enumerate(anchors):
        col=0
        while col<model['columns']:
            source=spans.get((row,col));values=combined.get((row,col),[]);span=source['colspan']if source else 1
            original=source['bbox']if source else model['bbox'];cell=dict(row=row,column=col,rowspan=1,colspan=span,text='\n'.join(t for _,t in sorted(values)),bbox=list(original),original_cell_bbox=list(original))
            cell['bbox'][1]=y-4;cell['bbox'][3]=anchors[row+1]-4 if row+1<len(anchors)else model['bbox'][3]
            cells.append(cell);col+=span
    before=' '.join(c['text']for c in model['cells']);after=' '.join(c['text']for c in cells)
    if gold.tokens(before)!=gold.tokens(after)or gold.numeric(before)!=gold.numeric(after):return model,False
    return {**model,'cells':cells,'rows':len(anchors),'row_method':'AFM merged-stub repair using repeated source monetary baselines','visual_status':'needs_owner_comparison'},True

def normalize(rich,doc):
    out=deepcopy(rich);changed=False;unresolved=False
    for i,block in enumerate(out['blocks']):
        if block['type']!='table'or not merged_stub(block):continue
        model,ok=repair(block,doc[block['page']-1]);out['blocks'][i]=model;changed|=ok;unresolved|=not ok
    if changed:
        out['body_html']='\n'.join(gold.table_html(b)if b['type']=='table'else'<'+('h4'if b['type']=='heading'else'p')+'>'+b['html']+'</'+('h4'if b['type']=='heading'else'p')+'>'for b in out['blocks'])
    if unresolved:out['warnings']=sorted(set(out['warnings']+['merged_financial_stub_geometry_requires_review']))
    fragments=formula_fragments(out['blocks'])
    if fragments:
        out['layout_exceptions']=dict(fragmented_formula_runs=fragments)
        out['warnings']=sorted(set(out['warnings']+['fragmented_formula_requires_source_layout_review']))
        out['fidelity']['numeric_token_conservation_passed']=out['fidelity']['passed'];out['fidelity']['passed']=False
    out['afm_table_geometry_repaired']=changed
    return out
