"""AFM complete-problem boundary evidence, without re-extracting source PDFs.

Numbered requirements and alternative solution methods are not automatically
standalone practice occurrences. All decisions remain provisional source audits.
"""
from collections import Counter
from copy import deepcopy
import re
import afm_reconcile as afm
import fr_corpus as fr

PART=re.compile(r'^(?:\d+\.\s*)?\(([a-h])\)(?:\s|$)',re.I)

def answer_parts(questions,answer):
    """Use printed answer-part margins, scoped to question alternatives.

    An OR in workings for part (b) cannot invalidate the answer to (a), or be
    mistaken for the question's separate Either/Or in part (c).
    """
    if not answer:return [],['answer_source_parent_missing']
    refs=[q.get('subreference','')for q in questions]
    if len(questions)==1 and not refs[0]:return [answer],[]
    expected=set(refs);hits=[];left=None
    for i,l in enumerate(answer['lines']):
        m=PART.match(l['text'])
        if not m or m[1].lower()not in expected:continue
        if left is None:
            if i>5:break
            left=l['bbox'][0]
            # Some first labels share a span with '1. (a)' at the
            # parent margin; later (b)/(c) establish the actual part margin.
            if re.match(r'^\d+\.\s*\(',l['text']):
                later=[x['bbox'][0]for x in answer['lines'][i+1:]if PART.match(x['text'])and PART.match(x['text'])[1].lower()in expected and l['bbox'][0]<=x['bbox'][0]<=l['bbox'][0]+65]
                if later:left=min(later)
                hits.append((m[1].lower(),i));continue
        if abs(l['bbox'][0]-left)<4:hits.append((m[1].lower(),i))
    if not hits:
        if len(questions)==1:
            return [{**answer,'subreference':refs[0],'alternative':questions[0].get('alternative','')}],[]
        return [],['answer_lettered_part_locations_unresolved']
    # Working-note labels cannot restart the sequence of main answer parts.
    if [r for r,_ in hits]!=sorted([r for r,_ in hits]):return [],['answer_lettered_part_order_requires_source_review']
    shared=answer['lines'][:hits[0][1]];shared=[l for l in shared if not re.fullmatch(r'Answer(?:\s+\d+)?|\d+\.?',l['text'],re.I)]
    out=[];issues=[];counts=Counter(r for r,_ in hits)
    for n,(ref,at)in enumerate(hits):
        stop=hits[n+1][1]if n+1<len(hits)else len(answer['lines']);body=answer['lines'][at:stop];qs=[q for q in questions if q.get('subreference','')==ref];alternatives=[q.get('alternative','')for q in qs]
        if counts[ref]>1:
            if counts[ref]!=len(qs)or set(alternatives)!={'either','or'}:
                issues.append('answer_repeated_part_'+ref+'_requires_review');continue
            alt='either'if n==0 or hits[n-1][0]!=ref else'or';branches=[(alt,body)]
        elif len(qs)==1:branches=[(alternatives[0],body)]
        elif set(alternatives)=={'either','or'}:
            dividers=[i for i,l in enumerate(body)if re.fullmatch('OR',l['text'],re.I)]
            if len(dividers)!=1:issues.append('answer_alternative_'+ref+'_boundary_unresolved');continue
            k=dividers[0];branches=[('either',body[:k]),('or',body[k+1:])]
        else:issues.append('answer_part_'+ref+'_question_identity_ambiguous');continue
        for alt,rows in branches:
            if not rows:issues.append('answer_empty_part_'+ref);continue
            last=answer['lines'].index(rows[-1]);end=fr.where(answer['lines'][last+1])if last+1<len(answer['lines'])else answer['end_exclusive']
            out.append({**answer,'subreference':ref,'alternative':alt,'lines':rows,'start':fr.where(rows[0]),'end_exclusive':end,'shared_lines':shared})
    return out,sorted(set(issues))

def complete_parts(question,answer):
    # Use only source question structure to select student-facing problems.
    qs,_,warnings=afm.split_question(question,answer)
    ans,issues=answer_parts(qs,answer)
    return qs,ans,sorted(set(warnings+issues))

def span_evidence(region):
    if not region:return None
    return dict(reference=region['reference'],subreference=region.get('subreference',''),alternative=region.get('alternative',''),start=region['start'],end_exclusive=region['end_exclusive'],lines=len(region['lines']),printed_requirement_labels=[l['text'][:150]for l in region['lines']if re.match(r'^\([ivx]+\)',l['text'],re.I)],marks=[l['text']for l in region['lines']if re.search(r'\bMarks?\b',l['text'],re.I)])
