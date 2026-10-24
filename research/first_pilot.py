"""Build a private, reference-only review pilot from existing corrected output.

No approvals or database-specific numeric IDs are transferred. This is not a
question classifier; caller selects an exact authorised source and references.
"""
import argparse,csv,hashlib,json,re
from pathlib import Path
from bridge import packet
ROOT=Path(__file__).resolve().parents[1]
def build(review,source_key,source_hash,references,output):
 out=Path(output).resolve()
 if (ROOT/'work').resolve() not in out.parents or out.exists():raise ValueError('Use a new private directory under ignored work/.')
 if not re.fullmatch('[a-f0-9]{64}',source_hash) or not 1<=len(references)<=5:raise ValueError('Provide exact source SHA-256 and 1–5 references.')
 rows=json.loads(Path(review).read_text());chosen=[]
 for ref in references:
  matches=[r for r in rows if r['document_key']==source_key and r['source_sha256']==source_hash and r['reference']==ref and not r['subreference']]
  if len(matches)!=1:raise ValueError('Missing or ambiguous exact source/reference: '+ref)
  r=matches[0]
  if r['subject']!='FR' or r.get('layout_blocked') or not r.get('start') or len(r['answer_candidates'])!=1:raise ValueError('Use a clear FR reference with boundary evidence and one answer candidate; this is not answer approval.')
  if not r['classification'].get('taxonomy_match'):raise ValueError('Historical official chapter proposal must be source-supported.')
  chosen.append(r)
 out.mkdir(parents=True,mode=0o700);packets=[];topics={};headers=['edition_key','subject_code','node_key','parent_key','node_type','title','position','heading_origin','source_url','source_location']
 for r in chosen:
  p=packet(r);p['question_coordinates']['shared_scenario']=r.get('scenario');p['scheme']='CA Final; source-linked May/September 2025 and January 2026 syllabus edition (owner confirmation required)';nodes=r['classification']['official_nodes'];chapter=next(n for n in nodes if n['node_type']=='chapter');edition=chapter['edition_key'];keys=[]
  for title in r['classification'].get('editorial_topics',[]):
   key=edition+'-pilot-'+hashlib.sha256((chapter['node_key']+'|'+title).encode()).hexdigest()[:16];keys.append(key)
   topics[key]=[edition,'FR',key,chapter['node_key'],'topic',title,100,'editorial',r['official_url'],'Editorial proposal: '+r['document_key']+' Q'+r['reference']+', PDF p.'+str(r['start']['page'])+'. Historical parent: '+edition+'. Owner review required.']
  p['ai_proposal']['editorial_node_keys']=keys;p['exceptions']=list(p['exceptions'])+['Source identity/hash and location evidence checked; detailed topic, exact answer match, historical applicability and all WordPress approval stages still require owner review.'];p['review_notes']='Private pilot: use the supplied historical hierarchy CSV as drafts. No academic or publication approval is conveyed. Source references only; no copied question or answer prose.';packets.append(p)
 batch={'batch_key':'FR-PILOT-'+hashlib.sha256((source_hash+'|'+','.join(references)).encode()).hexdigest()[:20],'records':packets};(out/'studio-drafts-001.json').write_text(json.dumps(batch,indent=2,ensure_ascii=False)+'\n')
 with (out/'pilot-hierarchy.csv').open('w',newline='') as f:w=csv.writer(f);w.writerow(headers);w.writerows(topics.values())
 evidence=[{k:r[k] for k in ['question_identity','source_sha256','document_key','source_type','source_title','attempt','section','reference','subreference','start','end_exclusive','heading','answer_candidates','classification','warnings','ledger_event','engine_revision']} for r in chosen];(out/'pilot-evidence.json').write_text(json.dumps(evidence,indent=2,ensure_ascii=False))
 report=dict(source_key=source_key,source_sha256=source_hash,references=references,records=len(packets),editorial_topic_proposals=len(topics),review_status='needs_review',publication_status='draft',owner_approvals=0,contains_source_prose=False,database_ids_transferred=False)
 (out/'pilot-manifest.json').write_text(json.dumps(report,indent=2));return report
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--review',required=True);p.add_argument('--source-key',required=True);p.add_argument('--source-sha256',required=True);p.add_argument('--references',required=True);p.add_argument('--output',required=True);a=p.parse_args();print(json.dumps(build(a.review,a.source_key,a.source_sha256,a.references.split(','),a.output)))
