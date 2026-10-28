"""Source-specific IBS case / decimal-reference discovery, with shared facts.

Case 1's 1.6 is distinct from Case 2's 2.6 and from working-note decimals.
Questions and answers have separate sides; repeated references alone never create
an independently verified mapping. The case's first-question boundary owns facts.
"""
import re
from collections import Counter
import fr_corpus
CASE=re.compile(r'^(?:(ANSWERS?\s+TO\s+(?:THE\s+)?)?CASE\s+STUDY)\s*[-–—:]?\s*(\d+|VI|IV|V|III|II|I)\b',re.I)
SIMPLE=re.compile(r'^([1-9][0-9]?)\.(?=\s|$)')
REF=re.compile(r'^([1-9][0-9]?)\.([1-9][0-9]?)(?=[\s.():-]|$)')
def discover(doc,metadata):
 lines=fr_corpus.all_lines(doc);possible=[l for l in lines if (REF.match(l['text'])or SIMPLE.match(l['text']))and 55<=l['bbox'][0]<=150];margin=Counter(round(l['bbox'][0])for l in possible).most_common(1)[0][0]if possible else 108
 contains_questions=any(re.fullmatch(r'(?:Multiple.Choice.Questions?|Descriptive.Questions?)',l['text'],re.I)for l in lines)
 side='answer'if metadata.get('role')=='answers'and not contains_questions else'question';fmt=None;case=None;case_begin={};case_first={};question_formats={};seen=set();last_numbers={};starts=[];boundaries=[];events=[]
 for i,l in enumerate(lines):
  text=l['text'];cm=CASE.match(text)
  if cm:
   raw=cm[2].upper();case={'I':'1','II':'2','III':'3','IV':'4','V':'5','VI':'6'}.get(raw,raw);side='answer'if cm[1]or(metadata.get('role')=='answers'and not contains_questions)else'question';fmt=None;boundaries.append(i);events.append(dict(kind='case',case=case,side=side,page=l['page'],bbox=l['bbox'],text=text))
   if side=='question':case_begin[case]=i
   continue
  is_label=bool(re.match(r'^(?:ANSWERS?\s+TO\s+(?:THE\s+)?)?(?:MULTIPLE.CHOICE.QUESTIONS?|DESCRIPTIVE.QUESTIONS?)\b',text,re.I))
  if is_label:
   if re.match(r'ANSWERS?\s+TO',text,re.I):side='answer'
   fmt='MCQ'if re.search('MULTIPLE.CHOICE',text,re.I)else'SUBJECTIVE';boundaries.append(i);events.append(dict(kind='section',format=fmt,side=side,page=l['page'],bbox=l['bbox'],text=text));continue
  if re.fullmatch(r'(?:SUGGESTED\s+)?ANSWERS?',text,re.I):side='answer';boundaries.append(i);events.append(dict(kind='answers',page=l['page'],bbox=l['bbox']));continue
  m=REF.match(text);simple=SIMPLE.match(text)if not m else None
  if not(m or simple)or abs(l['bbox'][0]-margin)>6:continue
  number_case=m[1]if m else case;number_sub=m[2]if m else simple[1]
  if not number_case:continue
  full=number_case+'.'+number_sub;printed=full if m else number_sub
  if side=='question'and(case!=number_case or fmt is None):continue
  # Suggested-answer books may move from requirements to compact option rows
  # without repeating a large ANSWERS title. Require an actual key label too.
  if side=='question'and full in seen:
   if re.search(r'\bOption\s*\([A-J]\)',text,re.I):side='answer'
   else:continue
  if side=='answer':case=number_case
  if int(number_sub)<=last_numbers.get((case,side),0):continue
  last_numbers[(case,side)]=int(number_sub)
  mode=question_formats.get(full,fmt)if side=='answer'else fmt
  if mode not in('MCQ','SUBJECTIVE'):continue
  if side=='question':seen.add(full);question_formats[full]=mode;case_first.setdefault(case,i)
  starts.append(dict(index=i,reference=printed,identity_reference=full,side=side,format=mode,case=case))
 records=[]
 for n,s in enumerate(starts):
  stop=starts[n+1]['index']if n+1<len(starts)else len(lines);stop=min([stop]+[b for b in boundaries if s['index']<b<stop]);rows=lines[s['index']:stop]
  if not rows:continue
  shared=lines[case_begin[s['case']]:case_first[s['case']]]if s['side']=='question'and s['case']in case_begin and s['case']in case_first else[]
  # Only facts preceding the first question belong to the common scenario.
  shared=[l for l in shared if not re.match(r'^(?:Multiple.Choice|Descriptive).Questions?',l['text'],re.I)]
  records.append(dict(reference=s['reference'],identity_reference=s['identity_reference'],case_reference=s['case'],subreference='',alternative='',side=s['side'],format=s['format'],heading=None,lines=rows,start=fr_corpus.where(rows[0]),end_exclusive=fr_corpus.where(lines[stop])if stop<len(lines)else dict(page=len(doc),bbox=[0,doc[-1].rect.height,0,doc[-1].rect.height],column=0),shared_lines=shared,parent_reference=s['case'],warnings=[]))
 profile=dict(engine='ibs-decimal-case-1',source_type=metadata['source_type'],role=metadata.get('role'),pages=len(doc),learned_number_margin=margin,events=events,number_starts=starts,common_fact_cases=list(case_first),status='needs_review',note='Printed decimal case references and section labels only; no answer approval or assumed MCQ count.')
 return records,profile
