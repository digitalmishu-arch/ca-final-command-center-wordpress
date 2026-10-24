"""Private, resumable inventory/worker. No Drive credentials or web worker in WordPress.

Input is a connector-read metadata snapshot plus locally authorised PDF manifests.
A file being listed/downloadable is not a private-copying or publication licence.
"""
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import uuid
import time

ROOT=Path(__file__).resolve().parents[1]

def now():return datetime.now(timezone.utc).isoformat()
def dump(path,obj):Path(path).write_text(json.dumps(obj,indent=2,ensure_ascii=False))
def connect(path):
    path=Path(path).resolve()
    if (ROOT/'work').resolve() not in path.parents:raise ValueError('Inventory state must remain in ignored private work/')
    path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    db=sqlite3.connect(path);db.row_factory=sqlite3.Row
    db.executescript('''CREATE TABLE IF NOT EXISTS jobs (file_id TEXT PRIMARY KEY, metadata TEXT NOT NULL, availability TEXT NOT NULL, rights_state TEXT NOT NULL DEFAULT 'unconfirmed', status TEXT NOT NULL DEFAULT 'awaiting_rights', source_hash TEXT NOT NULL DEFAULT '', run_path TEXT NOT NULL DEFAULT '', last_error TEXT NOT NULL DEFAULT '', modified_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY, file_id TEXT NOT NULL, event TEXT NOT NULL, details TEXT NOT NULL, created_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS leases(file_id TEXT PRIMARY KEY, lease_id TEXT NOT NULL, expires_at INTEGER NOT NULL);
    CREATE TABLE IF NOT EXISTS runs(id TEXT PRIMARY KEY, file_id TEXT NOT NULL, source_hash TEXT NOT NULL, manifest_hash TEXT NOT NULL, engine_hash TEXT NOT NULL, status TEXT NOT NULL, output_path TEXT NOT NULL, created_at TEXT NOT NULL);''')
    return db

def reconcile(workbook,snapshot,db_path):
    db=connect(db_path);values=json.loads(Path(workbook).read_text())['values'];snap=json.loads(Path(snapshot).read_text());files={};partial=[];errors=[]
    for folder in snap['folders']:
        if folder.get('error') or folder.get('result',{}).get('isError'):errors.append(folder['folder'])
        children=folder.get('result',{}).get('structuredContent',{}).get('files',[])
        if len(children)>=100:partial.append(folder['folder'])
        for f in children:
            if f.get('mime_type')=='application/pdf':files[f['id']]=dict(f,folder_path=folder['folder']['path'])
    records=[];seen=Counter()
    for row in values[1:]:
        row=row+['']*(16-len(row));subject,group,kind,name,label,attempt,scheme,private_url,syllabus,review,fid,*_=row
        if not fid:continue
        seen[fid]+=1;actual=files.get(fid);availability='listed_downloadable' if actual and actual.get('can_download') else 'access_denied' if actual else 'not_found_in_scanned_folders'
        metadata=dict(file_id=fid,subject=subject,group=group,document_kind=kind,filename=name,date_label=label,attempt=attempt,scheme=scheme,private_url=private_url,syllabus_url=syllabus,drive=actual,workbook_review=review)
        old=db.execute('SELECT * FROM jobs WHERE file_id=?',(fid,)).fetchone()
        if old:
            # Metadata refresh never erases processing history, rights evidence or owner decisions.
            db.execute('UPDATE jobs SET metadata=?,availability=?,modified_at=? WHERE file_id=?',(json.dumps(metadata),availability,now(),fid))
        else:db.execute('INSERT INTO jobs(file_id,metadata,availability,status,modified_at) VALUES(?,?,?,?,?)',(fid,json.dumps(metadata),availability,'awaiting_rights' if availability=='listed_downloadable' else availability,now()))
        records.append(dict(metadata,availability=availability))
    db.execute('INSERT INTO events(file_id,event,details,created_at) VALUES(?,?,?,?)',('', 'inventory_snapshot',json.dumps(dict(workbook_sha256=hashlib.sha256(Path(workbook).read_bytes()).hexdigest(),snapshot_sha256=hashlib.sha256(Path(snapshot).read_bytes()).hexdigest(),records=len(records))),now()));db.commit()
    pairing=[]
    for record in records:
        kind=record['document_kind'].lower()
        if 'mtp' in kind and ('question' in kind or 'answer' in kind):
            others=[r for r in records if r['subject']==record['subject'] and r['date_label']==record['date_label'] and ('answer' in r['document_kind'].lower())!=('answer' in kind) and 'mtp' in r['document_kind'].lower()]
            pairing.append(dict(file_id=record['file_id'],candidate_ids=[o['file_id'] for o in others],status='candidate_only_verify_visible_attempt_series' if others else 'no_pair_in_inventory'))
        elif 'suggested answer' in kind:pairing.append(dict(file_id=record['file_id'],candidate_ids=[],status='examination_paper_not_in_workbook'))
    return dict(timestamp=now(),catalogued_rows=len(records),unique_catalogued_ids=len(seen),scanned_folders=len(snap['folders']),scanned_pdf_ids=len(files),availability=dict(Counter(r['availability'] for r in records)),subjects=dict(Counter(r['subject'] for r in records)),kinds=dict(Counter(r['document_kind'] for r in records)),duplicate_file_ids=[k for k,v in seen.items() if v>1],byte_duplicate_check='pending download/content hash; filename equality is insufficient',partial_folders=partial,folder_errors=errors,pairing=pairing,records=records,additional_drive_pdf_ids=sorted(set(files)-set(seen)),publication_rights='not established by Drive access')

def process(db_path,manifest_path,limit=3,ledger=None,retry_failed=False):
    if not 1<=limit<=6:raise ValueError('Choose a resumable batch of 1–6 PDFs.')
    import layout_pipeline
    db=connect(db_path);mp=Path(manifest_path).resolve();manifest=json.loads(mp.read_text());results=[];attempted=0
    ledger_hash=hashlib.sha256(Path(ledger).read_bytes()).hexdigest() if ledger else ''
    for source in manifest['sources']:
        if attempted>=limit:break
        fid=source.get('file_id',source['document_key'])
        if not db.execute('SELECT 1 FROM jobs WHERE file_id=?',(fid,)).fetchone():
            db.execute('INSERT INTO jobs(file_id,metadata,availability,status,modified_at) VALUES(?,?,?,?,?)',(fid,json.dumps(source),'local_authorised_source','awaiting_rights',now()));db.commit()
        if not source.get('private_extraction_authorised') or not source.get('private_copy_basis'):
            db.execute('UPDATE jobs SET status=?,last_error=?,modified_at=? WHERE file_id=?',('awaiting_rights','Explicit private extraction/storage basis missing',now(),fid));db.commit();results.append(dict(file_id=fid,status='awaiting_rights'));continue
        if source.get('source_type') in ('mtp','exam') and not source.get('layout_profile_reviewed'):
            db.execute('UPDATE jobs SET status=?,last_error=?,modified_at=? WHERE file_id=?',('awaiting_layout_review','No source-specific reviewed layout profile',now(),fid));db.commit();results.append(dict(file_id=fid,status='awaiting_layout_review'));continue
        try:
            raw=(mp.parent/source['path']).resolve().read_bytes()
            if len(raw)>32*1024*1024 or not raw.startswith(b'%PDF-'):raise ValueError('Invalid PDF or 32 MiB limit exceeded')
        except (OSError,ValueError) as exc:
            db.execute('UPDATE jobs SET status=?,last_error=?,modified_at=? WHERE file_id=?',('failed',str(exc),now(),fid));db.commit();results.append(dict(file_id=fid,status='failed',error=str(exc)));attempted+=1;continue
        sha=hashlib.sha256(raw).hexdigest()
        engine_hash=hashlib.sha256(b''.join((ROOT/'research'/f).read_bytes() for f in ('layout_pipeline.py','layout_engine.py','corrections.py','layout-profiles.json'))).hexdigest()
        manifest_hash=hashlib.sha256(json.dumps(dict(source=source,ledger_sha256=ledger_hash),sort_keys=True).encode()).hexdigest()
        prior=db.execute('SELECT * FROM runs WHERE file_id=? AND source_hash=? AND manifest_hash=? AND engine_hash=? ORDER BY created_at DESC LIMIT 1',(fid,sha,manifest_hash,engine_hash)).fetchone()
        if prior and prior['status']=='processed':results.append(dict(file_id=fid,status='skipped_idempotent',output=prior['output_path']));continue
        if prior and prior['status']=='failed' and not retry_failed:results.append(dict(file_id=fid,status='failed_held_use_retry_failed'));continue
        duplicate=db.execute("SELECT file_id,output_path FROM runs WHERE source_hash=? AND file_id<>? AND status='processed'",(sha,fid)).fetchone()
        if duplicate:results.append(dict(file_id=fid,status='duplicate_bytes_needs_review',same_as=duplicate['file_id']));continue
        rid=hashlib.sha256((fid+'|'+sha+'|'+manifest_hash+'|'+engine_hash).encode()).hexdigest()[:16]+'-'+uuid.uuid4().hex[:8];out=ROOT/'work'/'batches'/rid
        db.execute('BEGIN IMMEDIATE');lease=db.execute('SELECT * FROM leases WHERE file_id=?',(fid,)).fetchone()
        if lease and lease['expires_at']>time.time():db.rollback();results.append(dict(file_id=fid,status='busy_in_another_batch'));continue
        db.execute('INSERT OR REPLACE INTO leases VALUES(?,?,?)',(fid,rid,int(time.time())+7200));db.execute('INSERT INTO runs VALUES(?,?,?,?,?,?,?,?)',(rid,fid,sha,manifest_hash,engine_hash,'processing',str(out),now()));db.execute('UPDATE jobs SET status=?,modified_at=? WHERE file_id=?',('processing',now(),fid));db.commit();attempted+=1
        one=dict(manifest,sources=[source]);one_path=mp.parent/('batch-'+rid+'.json');dump(one_path,one)
        previous=db.execute("SELECT output_path FROM runs WHERE file_id=? AND status='processed' ORDER BY created_at DESC LIMIT 1",(fid,)).fetchone()
        previous_path=str(Path(previous['output_path'])/'review.json') if previous else None
        try:
            layout_pipeline.run(one_path,out,ledger_path=ledger,previous_path=previous_path)
            report=json.loads((out/'report.json').read_text())
            if report['source_failures']:raise ValueError('Document identification/segmentation failed; inspect private exception report')
            status='processed';error=''
        except Exception as exc:status='failed';error=str(exc)
        db.execute('UPDATE runs SET status=? WHERE id=?',(status,rid));db.execute('UPDATE jobs SET status=?,source_hash=?,run_path=?,last_error=?,rights_state=?,modified_at=? WHERE file_id=?',(status,sha,str(out),error,'private_extraction_attested',now(),fid));db.execute('INSERT INTO events(file_id,event,details,created_at) VALUES(?,?,?,?)',(fid,status,json.dumps(dict(run=rid,error=error,ledger_sha256=ledger_hash)),now()));db.execute('DELETE FROM leases WHERE file_id=? AND lease_id=?',(fid,rid));db.commit();results.append(dict(file_id=fid,status=status,output=str(out),error=error))
    return results

def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    a=sub.add_parser('reconcile');a.add_argument('--workbook',required=True);a.add_argument('--drive-snapshot',required=True);a.add_argument('--state',required=True);a.add_argument('--report',required=True)
    a=sub.add_parser('batch');a.add_argument('--state',required=True);a.add_argument('--manifest',required=True);a.add_argument('--limit',type=int,default=3);a.add_argument('--ledger');a.add_argument('--retry-failed',action='store_true')
    a=p.parse_args()
    if a.command=='reconcile':r=reconcile(a.workbook,a.drive_snapshot,a.state);dump(a.report,r);print(json.dumps({k:r[k] for k in ('catalogued_rows','scanned_pdf_ids','availability','partial_folders')}))
    else:print(json.dumps(process(a.state,a.manifest,a.limit,a.ledger,a.retry_failed)))
if __name__=='__main__':main()
