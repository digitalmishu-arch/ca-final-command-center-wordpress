"""Private all-paper source catalogue. Reads actual PDF bytes; never publishes.

Filename/folder hints are retained separately from visible-document evidence.
Each file commits its own checkpoint. Exact/content duplicates are source-copy
relationships, not claims that examination questions are repeated.
"""
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import unicodedata

import fitz

ROOT=Path(__file__).resolve().parents[1]
VERSION='six-source-catalogue-2'
MONTHS='January February March April May June July August September October November December'.split()
PERIOD=re.compile(r'\b('+'|'.join(MONTHS)+r')\s*[,–-]?\s*(20\d{2})\b',re.I)
SUBJECTS=[('IBS',r'integrated\s+business\s+solutions'),('AFM',r'advanced\s+financial\s+management'),('SFM',r'strategic\s+financial\s+management'),('FR',r'financial\s+reporting'),('AUDIT',r'advanced\s+audit(?:ing)?[^\n]{0,90}(?:assurance|professional\s+ethics)'),('DT',r'direct\s+tax\s+laws'),('IDT',r'indirect\s+tax\s+laws'),('LAW_OLD',r'(?:corporate\s+and\s+economic\s+laws|corporate\s+and\s+allied\s+laws)'),('SCMPE_OLD',r'strategic\s+cost\s+management\s+and\s+performance\s+evaluation'),('MDS_OLD',r'multi[ -]?disciplinary\s+case\s+study')]

def now():return datetime.now(timezone.utc).isoformat()
def sha(b):return hashlib.sha256(b if isinstance(b,bytes)else b.encode()).hexdigest()
def write(p,d):p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def private(path):
 p=Path(path).resolve()
 if (ROOT/'work').resolve() not in p.parents:raise ValueError('Private outputs must remain inside ignored work/.')
 return p
def clean(text):return re.sub(r'\s+',' ',unicodedata.normalize('NFKC',text)).strip()
def periods(text):return [m[1].title()+' '+m[2]for m in PERIOD.finditer(text)]
def database(path):
 path=private(path);path.parent.mkdir(parents=True,exist_ok=True);db=sqlite3.connect(path);db.row_factory=sqlite3.Row
 db.executescript('''CREATE TABLE IF NOT EXISTS files(file_id TEXT PRIMARY KEY, source_hash TEXT NOT NULL, engine_hash TEXT NOT NULL, metadata_json TEXT NOT NULL, status TEXT NOT NULL, updated_at TEXT NOT NULL);
 CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY, file_id TEXT NOT NULL, event TEXT NOT NULL, details_json TEXT NOT NULL, at TEXT NOT NULL);
 CREATE TABLE IF NOT EXISTS outputs(source_hash TEXT NOT NULL, engine_hash TEXT NOT NULL, evidence_path TEXT NOT NULL, PRIMARY KEY(source_hash,engine_hash));''');return db

def identify(file,pages):
 first='\n'.join(p['text']for p in pages[:3]);front=first[:14000];headers='\n'.join(p['header']+'\n'+p['footer']for p in pages);evidence=front+'\n'+headers
 matches=[(m.start(),s) for s,rx in SUBJECTS if (m:=re.search(rx.replace('[^\\n]{0,90}','[\\s\\S]{0,160}'),front[:3500],re.I))];actual=min(matches)[1] if matches else None
 paper=re.search(r'PAPER\s*[-–:]?\s*([1-8])\b',front,re.I);paper=int(paper[1])if paper else None
 type_='rtp'if re.search(r'REVISION\s+TEST\s+PAPERS?',evidence,re.I)else'mtp'if re.search(r'MOCK\s+TEST\s+PAPERS?',front,re.I)else'case_booklet'if re.search(r'CASE\s+SCENARIO|CASE\s+STUD(?:Y|IES)\s+BOOK|CASE\s+SCENARIOS',front,re.I)else'exam'if re.search(r'(?:FINAL|INTERMEDIATE|FOUNDATION).*EXAMINATION|SUGGESTED\s+ANSWERS?',front,re.I)else'unknown'
 if file.get('inventory_group')=='subject_supporting':type_='compilation'
 text='\n'.join(p['text']for p in pages)
 if file.get('folder_path','').upper().endswith('RTP') and type_ in ('unknown','exam','case_booklet'):type_='rtp'
 q_starts=len(re.findall(r'(?im)^\s*QUESTION\s+[1-9][0-9]?\b',text));a_starts=len(re.findall(r'(?im)^\s*ANSWERS?\s*(?:[1-9][0-9]?)?\s*$',text))
 answers_title=bool(re.search(r'ANSWERS?\s*(?:AND|&)\s*HINTS|SUGGESTED\s+ANSWERS?|^\s*ANSWERS?\s*$',front[:2200],re.I|re.M))
 answer_section=bool(re.search(r'(?im)^\s*(?:SUGGESTED\s+ANSWERS?|ANSWERS?\s+(?:TO|OF)\s+PART|ANSWERS?)\s*$',text))
 if type_=='rtp':role='questions_and_answers'if answer_section else'questions_answer_section_unconfirmed'
 elif q_starts>=1 and a_starts>=1:role='questions_and_answers'
 elif answers_title or re.search(r'ANSWER\s+TO\s+PART|ANSWERS\s+TO\s+PART',front[:2200],re.I):role='answers'
 elif type_=='case_booklet':role='case_booklet'
 else:role='questions_role_provisional'
 title_lines=[l.strip()for l in pages[0]['text'].splitlines()if l.strip()][:24];title='\n'.join(title_lines)
 labels=[]
 for line in (headers+'\n'+title).splitlines():
  if re.search(r'EXAMINATION|EXAM\b|REVISION\s+TEST|MOCK\s+TEST|^\s*(?:'+'|'.join(MONTHS)+r')',line,re.I):labels+=periods(line)
 observed=Counter(labels).most_common(1)[0][0]if labels else''
 target_re=re.compile(r'(?:FOR|TARGET|APPLICABLE\s+FOR)\s+(?:THE\s+)?('+'|'.join(MONTHS)+r')\s*,?\s*(20\d{2})\s*(?:EXAM|ATTEMPT)',re.I)
 targets=target_re.findall(front);target=(targets[0][0].title()+' '+targets[0][1])if targets else''
 series=re.search(r'(?:MOCK\s+TEST\s+PAPERS?\s*[-–:]?\s*)?SERIES\s*[-–:]?\s*(III|II|IV|I|[1-4])\b',title,re.I)
 series=series[1].upper()if series else'';series={'1':'I','2':'II','3':'III','4':'IV'}.get(series,series)
 attempt=target if type_=='mtp'else observed
 issue=observed if type_=='mtp'else''
 # These seven source copies and target-cycle selections were expressly confirmed
 # by the owner. Preserve that prior selection; issue-period evidence stays separate.
 pilot={'1QClWQAfewta_6IHTbyH2fmnH2HDTGBNh':('rtp','questions_and_answers',''), '1uCRd5DQw0-8SO3rbXy7mdOSzKq8lr-Jy':('mtp','questions','I'),'1umLFhmoTEIWrs23OZKZyhfCub7EmrUqM':('mtp','answers','I'),'1WtEisnU5RDxWcmAarBj3nd_fiQiGqzG4':('mtp','questions','II'),'1xkjsPyAoXW4XQRsAGsg-jM4RYZR-XF6d':('mtp','answers','II'),'1BE7YVGrF0N-iwq4lfKKZW29Pvy8M19-y':('exam','questions_and_answers',''),'1wnwYggQORGWjo_L8n_wpwrfEjX4XJZKv':('exam','questions_and_answers','')}
 owner=pilot.get(file['id']);selection='source_evidence_provisional'
 if owner:type_,role,series=owner;attempt='January 2026';selection='owner_confirmed_existing_pilot'
 year=int((attempt or observed)[-4:])if attempt or observed else None
 scheme='final_old_eight_paper'if actual in ('SFM','LAW_OLD','SCMPE_OLD','MDS_OLD')or paper in (7,8)or(year and year<2024)else'final_six_paper_2023'if year and year>=2024 and actual in ('FR','AFM','AUDIT','DT','IDT','IBS')else'unresolved'
 warnings=[]
 if type_=='rtp' and not re.search(r'REVISION\s+TEST\s+PAPERS?',evidence,re.I):warnings.append('rtp_folder_and_integrated_structure_requires_profile_confirmation')
 if not actual:warnings.append('subject_not_established_from_visible_front_matter')
 if actual and file['subject']not in ('CASE',actual)and not(file['subject']=='AFM'and actual=='SFM'):warnings.append('collection_subject_differs_from_visible_subject')
 if type_=='unknown':warnings.append('source_category_not_established_from_content')
 if not attempt and type_ not in ('case_booklet','compilation'):warnings.append('target_attempt_not_established'if type_=='mtp'else'attempt_not_established')
 if type_=='mtp'and not series:warnings.append('mtp_series_not_recovered')
 if type_=='exam'and attempt=='May 2020':warnings.append('cancelled_may2020_actual_exam_identity_conflict')
 if type_=='exam'and attempt:
  m,y=attempt.rsplit(' ',1)
  if (int(y),MONTHS.index(m)+1)>(datetime.now(timezone.utc).year,datetime.now(timezone.utc).month):warnings.append('future_actual_examination_document_not_verifiable')
 if scheme!='final_six_paper_2023':warnings.append('historical_scheme_requires_separate_applicability_and_subject_mapping')
 if type_=='compilation':warnings.append('compilation_authorship_and_reproduction_scope_not_assumed')
 assessment=sorted(set(re.findall(r'(?i)(?:assessment\s+year|A\.?\s*Y\.?)\s*[:–-]?\s*(20\d{2}\s*[-–/]\s*(?:20)?\d{2})',text)))if actual in ('DT','IDT')else[]
 return dict(actual_subject=actual,paper_number=paper,source_type=type_,role=role,exam_attempt=attempt,document_issue_period=issue,series=series,scheme=scheme,title=title,selection=selection,printed_question_headings=q_starts,printed_answer_headings=a_starts,assessment_year_evidence=assessment,warnings=warnings,filename_hint=file['title'],folder_hint=file.get('folder_path',''),attribution='ICAI attribution requires source verification; file accessibility is not permission evidence')

def inspect(file,db,output):
 material=file.get('materialized',{});material=json.loads(material)if isinstance(material,str)else material
 path=Path(material.get('path',''))
 if not path.is_file():return dict(file_id=file['id'],filename=file['title'],subject=file['subject'],status='download_failed',error=file.get('transfer_error',file.get('download_error','Local PDF missing')))
 raw=path.read_bytes();digest=sha(raw);engine=sha(Path(__file__).read_bytes())
 prior=db.execute('SELECT * FROM files WHERE file_id=? AND source_hash=? AND engine_hash=?',(file['id'],digest,engine)).fetchone()
 if prior:return json.loads(prior['metadata_json'])
 result=dict(file_id=file['id'],filename=file['title'],collection_subject=file['subject'],inventory_group=file.get('inventory_group'),folder_path=file.get('folder_path'),drive_url=file['url'],source_hash=digest,bytes=len(raw),listed_bytes=int(file.get('size')or 0),local_path=str(path),modified_time=file.get('modified_time'),engine=VERSION)
 try:
  if not raw.startswith(b'%PDF-'):raise ValueError('Not a PDF signature')
  document=fitz.open(stream=raw,filetype='pdf')
  if document.needs_pass:raise ValueError('Encrypted PDF needs an authorised password')
  pages=[];scanned=[];table_candidates=[];header_count=Counter()
  for p in document:
   text=p.get_text('text',sort=True);head=p.get_text(clip=fitz.Rect(0,0,p.rect.width,min(150,p.rect.height*.24)),sort=True);foot=p.get_text(clip=fitz.Rect(0,p.rect.height*.86,p.rect.width,p.rect.height),sort=True)
   if len(re.sub(r'\s','',text))<40:scanned.append(p.number+1)
   drawings=p.get_drawings();vertical=0;horizontal=0
   for d in drawings:
    for item in d['items']:
     if item[0]=='l':
      a,b=item[1:3];vertical+=abs(a.x-b.x)<1 and abs(a.y-b.y)>12;horizontal+=abs(a.y-b.y)<1 and abs(a.x-b.x)>30
     elif item[0]=='re':vertical+=2;horizontal+=2
   if vertical>=2 and horizontal>=3:table_candidates.append(p.number+1)
   pages.append(dict(page=p.number+1,width=p.rect.width,height=p.rect.height,text=text,header=head,footer=foot,vertical_rules=vertical,horizontal_rules=horizontal))
  if not pages:raise ValueError('PDF has no pages')
  text='\n'.join(p['text']for p in pages);identity=identify(file,pages)
  result.update(status='inventoried_from_pdf_bytes',page_count=len(pages),identity=identity,scanned_or_empty_pages=scanned,table_candidate_pages=table_candidates,text_sha256=sha(clean(text)),content_fingerprint=sha(' '.join(re.findall(r'\w+',clean(text).casefold()))),private_extraction_basis='Owner explicitly authorised this six-subject research task',publication_rights='Apply only an existing matching administrator rights declaration; no scope expansion assumed',answer_availability='pending_structural_pair_reconciliation')
  evidence=output/'evidence'/digest/'pages.json.gz';evidence.parent.mkdir(parents=True,exist_ok=True)
  with gzip.open(evidence,'wt',encoding='utf-8')as f:json.dump(pages,f,ensure_ascii=False)
  result['evidence_path']=str(evidence)
 except Exception as exc:result.update(status='unreadable_pdf',error=str(exc))
 db.execute('INSERT OR REPLACE INTO files VALUES(?,?,?,?,?,?)',(file['id'],digest,engine,json.dumps(result,ensure_ascii=False),result['status'],now()));db.execute('INSERT INTO events(file_id,event,details_json,at)VALUES(?,?,?,?)',(file['id'],result['status'],json.dumps(dict(source_hash=digest,engine=engine)),now()));db.commit();return result

def run(downloads,output):
 output=private(output);output.mkdir(parents=True,exist_ok=True);db=database(output/'catalog.sqlite');files={}
 for name in sorted(Path(downloads).glob('downloads-*.json')):
  for row in json.loads(name.read_text()):files[row['id']]=row
 records=[inspect(f,db,output)for f in files.values()];groups=defaultdict(list)
 for r in records:
  if r.get('content_fingerprint'):groups[r['content_fingerprint']].append(r['file_id'])
 duplicates=[ids for ids in groups.values()if len(ids)>1]
 pair_groups=defaultdict(list)
 for r in records:
  d=r.get('identity',{});key=(d.get('actual_subject'),d.get('source_type'),d.get('exam_attempt'),d.get('document_issue_period'),d.get('series'),d.get('scheme'))
  if key[0]and(d.get('exam_attempt')or d.get('document_issue_period')):pair_groups[key].append(r)
 for r in records:
  d=r.get('identity',{});key=(d.get('actual_subject'),d.get('source_type'),d.get('exam_attempt'),d.get('document_issue_period'),d.get('series'),d.get('scheme'));pool=pair_groups[key]
  r['counterpart_candidates']=[x['file_id']for x in pool if x['file_id']!=r['file_id']and ((x.get('identity',{}).get('role')=='answers')!=(d.get('role')=='answers'))]
  r['answer_availability']='integrated_answer_section_detected'if d.get('role')=='questions_and_answers'else'candidate_counterpart_requires_exact_subpart_validation'if r['counterpart_candidates']else'no_counterpart_established'
  r['duplicate_source_copy_ids']=next((g for g in duplicates if r['file_id']in g),[])
 summary=dict(at=now(),files=len(records),states=dict(Counter(r['status']for r in records)),subjects=dict(Counter(r.get('collection_subject',r.get('subject','unknown'))for r in records)),duplicate_content_groups=len(duplicates),duplicate_file_count=sum(len(g)-1 for g in duplicates),records=records)
 write(output/'master-source-manifest.json',summary);write(output/'source-exceptions.json',[dict(file_id=r['file_id'],filename=r['filename'],subject=r.get('collection_subject',r.get('subject')),status=r['status'],warnings=r.get('identity',{}).get('warnings',[]),scanned_pages=r.get('scanned_or_empty_pages',[]),error=r.get('error',''))for r in records if r['status']!='inventoried_from_pdf_bytes'or r.get('identity',{}).get('warnings')or r.get('scanned_or_empty_pages')]);return summary

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--downloads',required=True);p.add_argument('--output',required=True);a=p.parse_args();r=run(a.downloads,a.output);print(json.dumps({k:r[k]for k in ('files','states','subjects','duplicate_content_groups','duplicate_file_count')}))
