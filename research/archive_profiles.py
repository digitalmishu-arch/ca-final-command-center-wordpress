"""Source-evidenced section profiles beyond the FR-only pilot defaults.

A numbered/lettered line is not, by itself, an MCQ. Printed section labels and
operative choice requirements determine the format. Brown headings scope forward.
"""
from collections import Counter
import re
import fr_corpus

def position(line):return line['page'],line['bbox'][1],line['bbox'][0]
def phases(records,lines,source_type):
 events=[];headings=[]
 for i,line in enumerate(lines):
  text=line['text'];joined=text+' '+(lines[i+1]['text']if i+1<len(lines)else'')
  label=bool(re.match(r'^(?:(?:ANSWERS?|SUGGESTED ANSWERS)(?:\s+TO|\s+OF)?\s+)?(?:PART|SECTION)\b|^(?:MCQS|MULTIPLE.CHOICE.QUESTIONS)\b',text,re.I))
  if label:
   fmt='MCQ'if re.search(r'\bMCQS?\b|MULTIPLE.CHOICE|OBJECTIVE',joined,re.I)else'SUBJECTIVE'if re.search(r'DESCRIPTIVE|SUBJECTIVE|PART\s*[-–—:]?\s*II\b',joined,re.I)else None
   if fmt:events.append(dict(position=position(line),format=fmt,text=text,page=line['page'],bbox=line['bbox'],basis='printed_section_label'))
  rgb=line.get('rgb',[0,0,0]);brown=rgb[0]>70 and rgb[0]>rgb[1]*1.15 and rgb[0]>rgb[2]*1.15
  if source_type=='rtp'and line.get('bold')and brown and len(text)<170 and not re.match(r'^[\d(₹`]|Required|Prepare|Calculate|Working|Particulars|Total|Note\b|Amount\b|CASE\b|INTEGRATED CASE|MCQS?\b|MULTIPLE CHOICE|ANSWERS|SUGGESTED',text,re.I):headings.append((i,line))
 starts={position(l):i for i,l in enumerate(lines)};consumed=set()
 for n,q in enumerate(records):
  at=position(q['start']);before=[e for e in events if tuple(e['position'])<at];fmt=before[-1]['format']if before else'SUBJECTIVE';index=starts.get(at)
  # The same page-bottom heading may introduce a next-page question.
  # A short preceding question must not be erased by reusing its heading.
  # Group headings may remain useful evidence, but only the first following
  # question consumes the boundary. Never trim across another question start.
  previous=records[n-1]if n else None
  pending=[(i,l)for i,l in headings if i not in consumed and index is not None and 0<index-i<=4 and 0<=q['start']['page']-l['page']<=1 and (not previous or position(l)>position(previous['start']))]
  if pending and q['side']=='question':
   heading_index,heading=pending[-1];consumed.add(heading_index);fmt='SUBJECTIVE';q['heading']=dict(text=heading['text'],spans=[{k:heading[k]for k in('text','page','bbox','font','size','bold','rgb')}]);events.append(dict(position=position(heading),format=fmt,text=heading['text'],page=heading['page'],bbox=heading['bbox'],basis='forward_brown_heading'));events.sort(key=lambda e:e['position'])
   if n and records[n-1]['side']=='question':previous=records[n-1];previous['lines']=[l for l in previous['lines']if position(l)<position(heading)];previous['end_exclusive']=fr_corpus.where(heading)
  if not before and fmt=='SUBJECTIVE':
   text=' '.join(l['text']for l in q['lines']);options=[l for l in q['lines']if re.match(r'^\([A-Da-d]\)(?:\s|$)',l['text'])]
   letters=[re.match(r'^\(([A-Da-d])\)',l['text'])[1].lower()for l in options]
   if letters==list('abcd')and max(l['bbox'][0]for l in options)-min(l['bbox'][0]for l in options)<8 and re.search(r'which\s+(?:of\s+the\s+following|following)|choose\s+the\s+correct|correct\s+option',text,re.I):fmt='MCQ'
  q['format']=fmt
 return records,events
