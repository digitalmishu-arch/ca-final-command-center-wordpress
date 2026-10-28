"""Private, checkpointed six-paper layout discovery. No automatic approvals.

Every actual PDF receives an outcome. Unknown layouts/schemes stay quarantined;
January pilot hashes and content-identical copies are reserved, never reimported.
"""
import argparse
from collections import Counter,defaultdict
from datetime import datetime,timezone
import json,re,sqlite3
from pathlib import Path
import fitz
import gold_layout as gold
import fr_corpus
import archive_catalog as catalog
import archive_profiles
import ibs_layout
VERSION='six-paper-layout-discovery-3'
PILOT={'1QClWQAfewta_6IHTbyH2fmnH2HDTGBNh','1uCRd5DQw0-8SO3rbXy7mdOSzKq8lr-Jy','1umLFhmoTEIWrs23OZKZyhfCub7EmrUqM','1WtEisnU5RDxWcmAarBj3nd_fiQiGqzG4','1xkjsPyAoXW4XQRsAGsg-jM4RYZR-XF6d','1BE7YVGrF0N-iwq4lfKKZW29Pvy8M19-y','1wnwYggQORGWjo_L8n_wpwrfEjX4XJZKv'}
def sequence(records):
 by=defaultdict(list)
 for q in records:by[q['side'],q['format']].append(float(q['reference']))
 return [side+'_'+kind+'_number_sequence_needs_profile_review'for(side,kind),ns in by.items()if len(ns)!=len(set(ns))or any(abs(b-a-1)>0.0001 for a,b in zip(ns,ns[1:]))]
def forward_headings(records):
 for previous,current in zip(records,records[1:]):
  if previous['side']!='question'or current['side']!='question'or current['format']!='SUBJECTIVE':continue
  tail=[]
  for l in reversed(previous['lines'][-4:]):
   rgb=l.get('rgb',[0,0,0]);brown=rgb[0]>70 and rgb[0]>rgb[1]*1.15 and rgb[0]>rgb[2]*1.15
   if l.get('bold')and brown and len(l['text'])<170 and not re.match(r'^[\d(₹`]|Required|Prepare|Calculate|Working',l['text'],re.I):tail.insert(0,l)
   elif tail:break
  if not tail or not 0<=current['start']['page']-tail[-1]['page']<=1:continue
  previous['lines']=[l for l in previous['lines']if l not in tail];previous['end_exclusive']=fr_corpus.where(tail[0]);current['heading']=dict(text=' '.join(l['text']for l in tail),spans=[{k:l[k]for k in('text','page','bbox','font','size','bold','rgb')}for l in tail])
 return records
def discover(r,out):
 ident=r['identity'];kind=ident['source_type'];path=Path(r['local_path'])
 if gold.sha(path.read_bytes())!=r['source_hash']:raise ValueError('Pinned source hash changed')
 if kind not in('rtp','mtp','exam'):return dict(status='held_source_category',reason='Compilation, booklet or unresolved document type requires a separate profile.',records=[])
 role={'questions_role_provisional':'questions','questions_answer_section_unconfirmed':'questions_and_answers'}.get(ident['role'],ident['role'])
 with fitz.open(path)as doc:
  records,profile=(ibs_layout.discover if ident['actual_subject']=='IBS'else gold.discover)(doc,dict(source_type=kind,role=role))
  if kind=='rtp':
   anchor=next((l for l in fr_corpus.all_lines(doc)if re.fullmatch('QUESTIONS',l['text'],re.I)),None)
   if anchor:records=[q for q in records if q['side']=='answer'or fr_corpus.position(q['start'])>fr_corpus.position(anchor)]
  if ident['actual_subject']!='IBS':records,format_events=archive_profiles.phases(records,fr_corpus.all_lines(doc),kind);profile['format_events']=format_events
  profile.update(subject=ident['actual_subject'],source_identity=ident,engine=VERSION,scope='Source-specific discovery, not academic verification');catalog.write(out/'profiles'/(r['file_id']+'.json'),profile)
  cache={};rows=[dict(region=q,rich=gold.reconstruct(q,doc,cache))for q in records if q['lines']]
  return dict(status='layout_candidates_prepared'if rows else'held_no_safe_question_starts',identity=ident,records=rows,warnings=sorted(set(ident['warnings']+(sequence(records)if ident['actual_subject']!='IBS'else[])+(['scanned_or_empty_pages_need_manual_handling']if r['scanned_or_empty_pages']else[]))),parent_subjective_questions=sum(q['side']=='question'and q['format']=='SUBJECTIVE'for q in records),mcq_parent_regions=sum(q['side']=='question'and q['format']=='MCQ'for q in records),pages=len(doc))
def job(r,out,engine,held):
 try:payload=held or discover(r,out/'evidence'/engine)
 except Exception as e:payload=dict(status='failed_layout_discovery',error=str(e),records=[])
 payload.update(file_id=r['file_id'],source_hash=r['source_hash']);target=out/'sources'/engine/(r['file_id']+'.json');catalog.write(target,payload);return dict(file_id=r['file_id'],status=payload['status'],payload_path=str(target),source_hash=r['source_hash'],engine_hash=engine,regions=len(payload['records']))
def run(manifest,output,limit=0,workers=4):
 from concurrent.futures import ProcessPoolExecutor,as_completed
 out=catalog.private(output);out.mkdir(parents=True,exist_ok=True);db=sqlite3.connect(out/'worker.sqlite');db.execute('PRAGMA journal_mode=WAL');db.execute('CREATE TABLE IF NOT EXISTS runs(file_id TEXT,source_hash TEXT,engine_hash TEXT,status TEXT,payload_path TEXT,at TEXT,PRIMARY KEY(file_id,source_hash,engine_hash))')
 engine=gold.sha(b''.join(Path(p).read_bytes()for p in(__file__,gold.__file__,fr_corpus.__file__,catalog.__file__,archive_profiles.__file__)));files=json.loads(Path(manifest).read_text())['records'];reserved={r['source_hash']for r in files if r['file_id']in PILOT};fingerprints={r.get('content_fingerprint')for r in files if r['file_id']in PILOT};seen={};summary=[];jobs=[]
 for r in files:
  if r.get('status')!='inventoried_from_pdf_bytes':continue
  context=gold.sha(engine+json.dumps(r['identity'],sort_keys=True)+(gold.sha(Path(ibs_layout.__file__).read_bytes())if r['identity']['actual_subject']=='IBS'else''));key=r['file_id'],r['source_hash'],context;prior=db.execute('SELECT status,payload_path FROM runs WHERE file_id=? AND source_hash=? AND engine_hash=?',key).fetchone();held=None
  if prior:summary.append(dict(file_id=r['file_id'],status=prior[0],payload_path=prior[1]));seen[r.get('content_fingerprint')]=r['file_id'];continue
  if r['source_hash']in reserved or r.get('content_fingerprint')in fingerprints:held=dict(status='retained_existing_january_pilot_no_reimport',records=[],note='Existing pilot identities/corrections reserved, including content-identical copies.')
  elif r.get('content_fingerprint')in seen:held=dict(status='duplicate_source_copy_retained',canonical_file_id=seen[r['content_fingerprint']],records=[])
  seen[r.get('content_fingerprint')]=r['file_id'];jobs.append((r,out,context,held))
  if limit and len(jobs)>=limit:break
 with ProcessPoolExecutor(max_workers=max(1,min(workers,4)))as pool:
  for future in as_completed([pool.submit(job,*args)for args in jobs]):
   result=future.result();db.execute('INSERT INTO runs VALUES(?,?,?,?,?,?)',(result['file_id'],result['source_hash'],result['engine_hash'],result['status'],result['payload_path'],datetime.now(timezone.utc).isoformat()));db.commit();summary.append(result);catalog.write(out/'worker-manifest.json',dict(engine=VERSION,engine_hash=engine,documents=summary,counts=dict(Counter(r['status']for r in summary)),pending=len(jobs)-sum('engine_hash'in r for r in summary),note='Candidate reconstruction only. No academic verification/publication.'));print(json.dumps(result),flush=True)
 return summary
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('manifest');p.add_argument('--output',required=True);p.add_argument('--limit',type=int,default=0);p.add_argument('--workers',type=int,default=4);a=p.parse_args();run(a.manifest,a.output,a.limit,a.workers)
