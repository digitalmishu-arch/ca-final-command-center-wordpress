"""Build a compact, private JSON-only WordPress Academic Import ZIP.

The research evidence archive remains separate. This never carries academic
approvals, raw PDFs, executable files, accounts or student activity.
"""
import argparse
from datetime import datetime,timezone
import hashlib,json
from io import BytesIO
from pathlib import Path
import zipfile


def build(review,output,package_key,sources,rights=None):
    review=Path(review);output=Path(output)
    if output.exists():raise ValueError('Choose a new package revision; do not overwrite a delivered ZIP.')
    members={};items=[]
    def add(kind,name,payload):
        raw=json.dumps(payload,ensure_ascii=False,indent=2).encode()+b'\n'
        if len(raw)>2000000:raise ValueError('Split oversize data into smaller numbered batches: '+name)
        members[name]=raw;items.append(dict(path=name,kind=kind,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
    for i,path in enumerate(sorted((review/'taxonomy-imports').glob('*.json')),1):add('taxonomy',f'items/taxonomy_{i:03d}.json',json.loads(path.read_text()))
    source_rows=json.loads(Path(sources).read_text())
    if isinstance(source_rows,dict):source_rows=source_rows['sources']
    add('sources','items/sources.json',dict(sources=source_rows))
    if rights:add('rights','items/rights.json',json.loads(Path(rights).read_text()))
    for i,path in enumerate(sorted(review.glob('shared-scenarios-*.json')),1):add('scenarios',f'items/scenarios_{i:03d}.json',json.loads(path.read_text()))
    count=0
    for i,path in enumerate(sorted(review.glob('*/imports/studio-drafts-*.json')),1):
        payload=json.loads(path.read_text());count+=len(payload['records'])
        for r in payload['records']:
            # Permission exists by owner attestation; it is linked on the server,
            # separately from the still-pending academic review of this candidate.
            r['rights_basis']='Owner attests signed physical ICAI authorisation retained physically; match the recorded source-wide declaration. Academic correctness remains Needs Review.'
            r['rights_grant_id']=None;r['quality_checks']={}
        add('questions',f'items/questions_{i:03d}.json',payload)
    manifest=dict(format='CAFCC-ACADEMIC-PACKAGE-1',package_key=package_key,version='0.5.2',created_at=datetime.now(timezone.utc).isoformat(),scope=dict(subject_code='FR',exam_attempt='January 2026',edition_key='fr-may2025-jan2026'),coverage=dict(source_documents=len(source_rows),pdfs_read=sum(bool(s.get('source_hash')) or s['technical_state']=='pdf_checked' for s in source_rows),technical_blocks=sum(s['technical_state']=='retrieval_blocked' for s in source_rows),source_context_needs_review=sum(s['technical_state']=='needs_layout_review' for s in source_rows),subjective_candidates=count,academic_approvals=0,publications=0),items=items)
    members['manifest.json']=json.dumps(manifest,ensure_ascii=False,indent=2).encode()+b'\n';stream=BytesIO()
    with zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED) as archive:
        for name,data in members.items():archive.writestr(name,data)
    if stream.tell()>8000000:raise ValueError('Academic import ZIP exceeds 8 MB; split into versioned packages.')
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('xb') as file:file.write(stream.getvalue())
    return dict(filename=output.name,bytes=output.stat().st_size,sha256=hashlib.sha256(output.read_bytes()).hexdigest(),items=len(items),coverage=manifest['coverage'])


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('review_directory');p.add_argument('output_zip');p.add_argument('--package-key',required=True);p.add_argument('--sources',required=True);p.add_argument('--rights');a=p.parse_args();print(json.dumps(build(a.review_directory,a.output_zip,a.package_key,a.sources,a.rights)))
