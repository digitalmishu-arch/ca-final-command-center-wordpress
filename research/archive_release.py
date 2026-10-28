"""Private six-subject draft bundles from checkpointed, source-specific regions.

No rights grant, publication or academic approval is supplied. Unknown source
attempts and historical subjects are held outside importable children. Source
context editions are explicitly provisional, never invented official headings.
"""
import argparse
from collections import Counter,defaultdict
from copy import deepcopy
from datetime import datetime,timezone
import gzip,html,json,re,zipfile
from pathlib import Path
import fitz
import archive_catalog as cat
import gold_layout as gold
import layout_engine
import fr_package
import mcq_pipeline
import ibs_mcq
ROOT=Path(__file__).resolve().parents[1]
SUBJECTS=('FR','AFM','AUDIT','DT','IDT','IBS')
PRIOR_LEDGER_PATH=ROOT/'work/january-complete/extraction-r016/prior-owner-corrections.json'
PRIOR_LEDGER=json.loads(PRIOR_LEDGER_PATH.read_text())if PRIOR_LEDGER_PATH.exists()else[]
CANONICAL=json.loads((ROOT/'ca-final-command-center/data/syllabus-catalogue.json').read_text())
_REGION_CACHE={};_SOURCE_HASHES={};_CACHE_DIR=None
def rich_region(q,doc,cache=None):
 path=doc.name
 if path not in _SOURCE_HASHES:_SOURCE_HASHES[path]=gold.sha(Path(path).read_bytes())
 signature=gold.sha(json.dumps({k:q[k]for k in ('lines','start','end_exclusive')},sort_keys=True));key=(_SOURCE_HASHES[path],signature)
 if key in _REGION_CACHE:return _REGION_CACHE[key]
 disk=_CACHE_DIR/key[0]/(signature+'.json')
 if disk.exists():return json.loads(disk.read_text())
 value=gold.reconstruct(q,doc,cache);cat.write(disk,value);return value
BASIS='Owner-authorised private extraction and electronic storage for this six-subject project. No publication grant or academic approval is supplied; WordPress must match the actual existing source-wide rights scope.'
def plain(value):return html.unescape(re.sub('<[^>]+>',' ',value))
def subref(q):
 parts=q.get('subreference','').split('.');return parts[0]+''.join('('+p+')'for p in parts[1:])
def page(q):return str(q['start']['page'])+'-'+str(max(l['page']for l in q['lines']))
def content(rich):return dict(body_html=rich['body_html'],author_name='The Institute of Chartered Accountants of India (ICAI)',source_text_sha256=rich['source_text_sha256'],source_location='See exact PDF coordinates in research record',structure=dict(blocks=rich['blocks']),checks=rich['fidelity'])
def source_url(r):return 'https://drive.google.com/file/d/'+r['file_id']+'/view'
def source_key(r):return 'SRC-'+r['source_hash'][:40]
def edition(r):
 d=r['identity']
 if d['exam_attempt']=='May 2026':
  e=next((e for e in CANONICAL['editions']if e['subject_code']==d['actual_subject']),None)
  if e:return e['edition_key']
 return 'context-'+(d['actual_subject']or r['collection_subject']).lower()+'-'+re.sub('[^a-z0-9]+','-',(d['scheme']+'-'+d['exam_attempt']).lower()).strip('-')
def source(r,role=None):
 d=r['identity'];return dict(source_key=source_key(r),title=(d['title'].splitlines()[0]if d['title']else r['filename'])+' — '+r['filename'],subject_code=d['actual_subject'],source_type=d['source_type'],role=role or r.get('layout_role') or ('questions'if d['role']=='questions_role_provisional'else'questions_and_answers'if d['role']=='questions_answer_section_unconfirmed'else d['role']),exam_attempt=d['exam_attempt'],mtp_series=d['series'],issue_period=d['document_issue_period'],source_hash=r['source_hash'],source_url=source_url(r),icai_url='',hosting='owner_verified_icai_mirror',content_origin='icai',selection_state='owner_verified',selection_evidence='Owner selected the authorised public source collection for this task. PDF bytes, hash and visible identity were read. This is not academic verification.',technical_state='pdf_checked',technical_notes='Original source file retained. Target attempt comes from source evidence; MTP issue period remains separate. Layout/academic exceptions are retained with each draft.',drive_file_id=r['file_id'],edition_key=edition(r),public_copy_confirmation='owner-authorised-source-collection')
def context_taxonomy(r):
 d=r['identity'];key=edition(r);url='https://www.icai.org/post/bos-knowledge-portal';subject=d['actual_subject']or r['collection_subject'];title=subject+' — '+d['exam_attempt']+' source context (historical syllabus mapping provisional)'
 ed=dict(edition_key=key,subject_code=subject,title=title,applicability=d['exam_attempt']+' only; source-context record, official historical syllabus edition requires reconciliation',source_url=url)
 nodes=[]
 for kind,name,parent in [('chapter',subject+' — Classification to be refined (Editorial)',''),('topic',subject+' — Topic to be refined (Editorial)',key+'-chapter')]:nodes.append(dict(node_key=key+'-'+kind,edition_key=key,subject_code=subject,parent_key=parent,node_type=kind,title=name,heading_origin='editorial',source_url=url,source_location='Provisional navigation context for the exact source attempt; not quoted ICAI study-material taxonomy.'))
 canonical=next((e for e in CANONICAL['editions']if e['edition_key']==key),None)
 if canonical:
  ed={k:canonical[k]for k in ('edition_key','subject_code','title','applicability','source_url')};allowed=('node_key','edition_key','subject_code','parent_key','node_type','title','heading_number','printed_page','position','heading_origin','source_url','source_location');nodes=[{k:v for k,v in n.items()if k in allowed}for n in CANONICAL['nodes']if n['edition_key']==key]+nodes
 return dict(batch_key='TAX-'+key,editions=[ed],nodes=nodes)
def eligible_source(r):
 d=r['identity'];return d['actual_subject']in SUBJECTS and d['actual_subject']==r['collection_subject'] and d['source_type']in('rtp','mtp','exam')and bool(d['exam_attempt'])and(d['source_type']!='mtp'or bool(d['series']))and not any(x in d['warnings']for x in('cancelled_may2020_actual_exam_identity_conflict','future_actual_examination_document_not_verifiable'))
def counterpart(r,manifest,payloads):
 d=r['identity'];own=payloads[r['file_id']]
 if any(q['region']['side']=='answer'for q in own['records']):return [r]
 candidates=[]
 for a in manifest:
  ad=a['identity'];p=payloads.get(a['file_id'],{})
  if a['file_id']==r['file_id']or not p.get('records'):continue
  if any(ad.get(k)!=d.get(k)for k in('actual_subject','source_type','exam_attempt','document_issue_period','series','scheme')):continue
  if not(d['exam_attempt']or d['document_issue_period'])or(d['source_type']=='mtp'and not d['series']):continue
  if any(x['region']['side']=='answer'for x in p['records']):candidates.append(a)
 unique={a['content_fingerprint']:a for a in candidates};return list(unique.values())
def build_zip(path,key,subject,attempt,edkey,tax,sources,rows,scenarios,kind='questions'):
 members={};items=[]
 def add(k,name,obj):
  raw=(json.dumps(obj,ensure_ascii=False,indent=2)+'\n').encode();assert len(raw)<=2000000,(name,len(raw));members[name]=raw;items.append(dict(path=name,kind=k,bytes=len(raw),sha256=gold.sha(raw)))
 for i in range(0,len(tax['nodes']),100):add('taxonomy','items/taxonomy_'+str(i//100+1)+'.json',dict(batch_key=tax['batch_key']+'-'+str(i//100+1),editions=tax['editions'],nodes=tax['nodes'][i:i+100]))
 add('sources','items/sources.json',dict(sources=list(sources.values())))
 if scenarios:add('scenarios','items/scenarios.json',dict(batch_key=key+'-SC',scenarios=list(scenarios.values())))
 for i in range(0,len(rows),10):add(kind,'items/records_'+str(i//10+1).zfill(3)+'.json',dict(format='CAFCC-MCQ-DRAFTS-1',records=rows[i:i+10])if kind=='mcqs'else dict(batch_key=key+'-'+str(i//10+1),records=rows[i:i+10]))
 assert len(items)<=64
 manifest=dict(format='CAFCC-ACADEMIC-PACKAGE-1',package_key=key,version='0.8.1',created_at=datetime.now(timezone.utc).isoformat(),scope=dict(subject_code=subject,exam_attempt=attempt,edition_key=edkey),coverage=dict(draft_candidates=len(rows),academic_approvals=0,publications=0,classification='Provisional editorial/source-context mapping; independent academic verification not asserted'),items=items)
 members['manifest.json']=(json.dumps(manifest,indent=2)+'\n').encode();path.parent.mkdir(parents=True,exist_ok=True)
 with zipfile.ZipFile(path,'x',zipfile.ZIP_DEFLATED)as z:
  for name,raw in members.items():z.writestr(name,raw)
 if path.stat().st_size>8000000:raise ValueError('Split oversized academic package')
 return dict(filename=path.name,bytes=path.stat().st_size,sha256=gold.sha(path.read_bytes()),records=len(rows),kind=kind)
def build(manifest_path,worker_path,out,revision):
 global _CACHE_DIR
 _CACHE_DIR=cat.private(Path(out).parent/'rich-cache'/gold.sha(Path(gold.__file__).read_bytes()));_CACHE_DIR.mkdir(parents=True,exist_ok=True)
 out=cat.private(out);out.mkdir(parents=True,exist_ok=False);manifest=json.loads(Path(manifest_path).read_text())['records'];index={r['file_id']:r for r in manifest};worker=json.loads(Path(worker_path).read_text());payloads={r['file_id']:json.loads(Path(r['payload_path']).read_text())for r in worker['documents']};totals={};all_packages=[]
 for r in manifest:
  sides={x['region']['side']for x in payloads.get(r['file_id'],{}).get('records',[])}
  r['layout_role']='questions_and_answers'if sides=={'question','answer'}else'answers'if sides=={'answer'}else'questions'if sides=={'question'}else None
  for x in payloads.get(r['file_id'],{}).get('records',[]):
   q=x['region'];signature=gold.sha(json.dumps({k:q[k]for k in ('lines','start','end_exclusive')},sort_keys=True));_REGION_CACHE[(r['source_hash'],signature)]=x['rich']
 for subject in SUBJECTS:
  base=out/subject;base.mkdir();rows=[];exceptions=[];inventory=[];mcqs=[];table_report=[];scenarios={};source_rows={};source_counts=[]
  for r in [r for r in manifest if r['collection_subject']==subject]:
   p=payloads.get(r['file_id'],{});d=r['identity'];inventory.append(dict(file_id=r['file_id'],filename=r['filename'],source_kind=d['role'],attempt=d['exam_attempt'],issue_period=d['document_issue_period'],series=d['series'],sha256=r['source_hash'],pages=r['page_count'],outcome=p.get('status','not_yet_extracted'),warnings=p.get('warnings',[]),source_url=source_url(r)))
   raw_qs=[x for x in p.get('records',[])if x['region']['side']=='question'and x['region']['format']=='SUBJECTIVE'];answers=counterpart(r,manifest,payloads)if raw_qs else[];answer_source=answers[0]if len(answers)==1 else None;answer_regions=[x['region']for x in payloads[answer_source['file_id']]['records']if x['region']['side']=='answer'and x['region']['format']=='SUBJECTIVE']if answer_source else[]
   eligible=eligible_source(r);source_counts.append(dict(file_id=r['file_id'],filename=r['filename'],status=p.get('status','not_yet_extracted'),subjective_parents=len(raw_qs),mcq_regions=sum(x['region']['side']=='question'and x['region']['format']=='MCQ'for x in p.get('records',[])),answer_source_candidates=[a['file_id']for a in answers],import_identity_eligible=eligible))
   if p.get('status')!='layout_candidates_prepared':exceptions.append(dict(file_id=r['file_id'],code=p.get('status','not_yet_extracted'),required_action=p.get('reason',p.get('error','Retained source outcome; no duplicate import.'))));continue
   if not eligible:exceptions.append(dict(file_id=r['file_id'],code='source_identity_or_target_attempt_held',required_action='Resolve exact target attempt/series/historical subject from authoritative evidence; issue date is not the exam target.'))
   with fitz.open(r['local_path'])as doc:
    cache={}
    for parent in raw_qs:
     q=parent['region'];matches=[a for a in answer_regions if a['reference']==q['reference']and(subject!='IBS'or a.get('parent_reference')==q.get('parent_reference'))];a=matches[0]if len(matches)==1 and not any(w.startswith('answer_')and 'number_sequence'in w for w in p.get('warnings',[]))else None
     try:
      if a:parts,aps,split_warnings=gold.practice_parts(q,a)
      else:
       parts,ambiguous=gold.split_independent(q);aps=[];split_warnings=[ambiguous['code']]if ambiguous else[]
     except ValueError as error:parts=[q];aps=[];split_warnings=['question_integrity_failed_independent_part_or_alternative_boundary: '+str(error)]
     amap={(x.get('subreference',''),x.get('alternative','')):x for x in aps};parent_key='P-'+gold.sha(r['source_hash']+'|'+q.get('identity_reference',q['reference']))[:48]
     for child in parts:
      shared=[];seen_shared=set()
      for l in q.get('shared_lines',[])+child.get('shared_lines',[]):
       key=(l['page'],tuple(l['bbox']),l['text'])
       if key not in seen_shared:shared.append(l);seen_shared.add(key)
      child={**child,'shared_lines':shared}
      source_section='case_'+q['parent_reference']+'_descriptive'if subject=='IBS'and q.get('parent_reference')else'descriptive'
      stable='R-'+layout_engine.identity(r['source_hash'],source_section,child['reference'],child['subreference']+(':'+child.get('alternative','')if child.get('alternative')else''));rich=rich_region(child,doc,cache);matched=amap.get((child['subreference'],child.get('alternative','')));arich=None
      if matched and answer_source:
       with fitz.open(answer_source['local_path'])as adoc:arich=rich_region(matched,adoc,{})
      warnings=list(dict.fromkeys(p.get('warnings',[])+split_warnings+rich['warnings']+(arich['warnings']if arich else['answer_pending_no_unique_exact_part_match'])+['historical_official_taxonomy_mapping_provisional','publication_rights_scope_must_match_existing_declaration']))
      if not eligible:warnings.append('question_integrity_failed_unresolved_source_identity')
      if any(w.startswith('question_SUBJECTIVE')and 'number_sequence' in w for w in warnings)or split_warnings:warnings.append('question_integrity_failed_question_boundary_profile_requires_review')
      if any('table'in w or 'fidelity_failed'in w for w in rich['warnings']):warnings.append('question_integrity_failed_table_or_numeric_geometry')
      if any(child['start']['page']<=pn<=child['end_exclusive']['page']for pn in r['scanned_or_empty_pages']):warnings.append('question_integrity_failed_scanned_source_region')
      text=rich['plain_text'];practical=any(b['type']=='table'for b in rich['blocks'])or bool(re.search(r'\bcalculate|\bcompute|\bprepare|\bdetermine.{0,30}(?:amount|value)|\bjournal entr',text,re.I));case=bool(re.search(r'\b(?:Ltd\.?|Limited|Company|firm|client)\b',text,re.I));qt='practical'if practical else'case_study'if case else'theory';bundle='SUBJECTIVE-THEORY'if qt=='theory'else'SUBJECTIVE-PRACTICAL'
      record=dict(stable_id=stable,source_hash=r['source_hash'],source_key=source_key(r),subject_code=d['actual_subject']if d['actual_subject']in SUBJECTS else subject,source_type=d['source_type'],exam_attempt=d['exam_attempt'],mtp_series=d['series'],issue_period=d['document_issue_period'],scheme=d['scheme'],section=source_section+(':'+child.get('alternative','')if child.get('alternative')else''),reference=child['reference'],subreference=subref(child),title=(subject+' '+d['source_type']+' '+d['exam_attempt']+' Q'+child['reference'])[:190],official_url=source_url(r),edition_id=None,classification=[],question_page=page(child),question_coordinates=dict(start=child['start'],end_exclusive=child['end_exclusive']),heading_evidence=child.get('heading')or{},question_type=qt,question_format='subjective',rights_mode='licensed_private_review',rights_basis=BASIS,reasoning='Provisional classification from detected source heading and operative requirement. Historical official topic reconciliation is not asserted.',confidence='Provisional; source and structural exceptions retained',blocking_exceptions=warnings,extraction_status='needs_review',source_revision=r['source_hash'],engine_revision=dict(engine=worker['engine'],engine_hash=worker['engine_hash']),law_context='Original historical source retained; assessment-year evidence: '+', '.join(d['assessment_year_evidence']),ai_proposal=dict(historical_edition=edition(r),official_nodes=[],primary_path=[dict(node_key=edition(r)+'-topic',node_type='topic',title=subject+' — Topic to be refined (Editorial)')],additional_node_keys=[]),rich_content=dict(question=content(rich)),answer={},marks=None,marks_verified=False,practice_structure=dict(parent_stable_id=parent_key,alternative=child.get('alternative',''),quality_required=True),quality_checks={},source_provenance=dict(drive_file_id=r['file_id']))
      common=child.get('shared_lines',[])
      if subject=='IBS'and q.get('shared_lines'):
       base_keys={(l['page'],tuple(l['bbox']),l['text'])for l in q['shared_lines']};extra=[l for l in common if(l['page'],tuple(l['bbox']),l['text'])not in base_keys]
       if extra:
        combined={**child,'lines':extra+child['lines'],'start':fr_package.fr_corpus.where(extra[0])};rich=rich_region(combined,doc,cache);record['rich_content']['question']=content(rich)
       common=q['shared_lines']
      if common:
       last=common[-1];shared={**child,'lines':common,'start':fr_package.fr_corpus.where(common[0]),'end_exclusive':dict(page=last['page'],bbox=[last['bbox'][0],last['bbox'][3]+.1,last['bbox'][2],last['bbox'][3]+.1],column=0)};sr=rich_region(shared,doc,cache);sk='SC-'+gold.sha(r['source_hash']+'|'+json.dumps(shared['start'],sort_keys=True)+'|'+sr['source_text_sha256'])[:48];scenarios[sk]=dict(scenario_key=sk,source_hash=r['source_hash'],body_html=sr['body_html'],rights_basis=BASIS,evidence=dict(start=shared['start'],end=shared['end_exclusive']));record['practice_structure']['scenario_key']=sk
       if not sr['fidelity']['passed']or sr['warnings']:record['blocking_exceptions'].append('question_integrity_failed_shared_scenario_geometry_requires_review')
      if arich:
       record['rich_content']['answer']=content(arich);record['answer']=dict(source_hash=answer_source['source_hash'],official_url=source_url(answer_source),reference=child['reference'],subreference=subref(child),alternative=child.get('alternative',''),question_identity=stable,question_reference=child['reference'],question_subreference=subref(child),question_source_hash=r['source_hash'],page=page(matched),subject_code=d['actual_subject'],source_type=d['source_type'],exam_attempt=d['exam_attempt'],mtp_series=d['series'],mode='licensed',notes='Unique structural source/hash/role/attempt/series/part candidate. Not independent academic verification.');record['source_provenance']['answer_drive_file_id']=answer_source['file_id']
      review_rich=deepcopy(rich)
      if common:review_rich['plain_text']=sr['plain_text']+'\n\n'+rich['plain_text']
      heading=(child.get('heading')or{}).get('text','');prior_events=[e for e in PRIOR_LEDGER if e.get('source_sha256')==r['source_hash']and str(e.get('reference'))==child['reference']and(e.get('subreference')or'')==child['subreference']];record['previous_corrections']=prior_events;proposed=[heading]if heading else[]
      for event in prior_events:
       if event.get('section')=='descriptive'and event.get('decision')in ('approved','concept_approved')and event.get('classification',{}).get('concept'):proposed.append(event['classification']['concept'])
       elif event.get('section')!='descriptive':record['blocking_exceptions'].append('prior_owner_numbering_context_conflict_needs_owner_review_no_override_applied')
      record['ai_proposal']['proposed_search_tags']=list(dict.fromkeys(proposed));normal=lambda t:re.sub('[^a-z0-9]+','',t.lower());available=[n for n in context_taxonomy(r)['nodes']if n['heading_origin']=='official'and n['node_type']in('chapter','unit','topic','subtopic')];exact=[n for n in available if normal(n['title'])==normal(heading)]if heading else[]
      if len(exact)==1:record['ai_proposal']['primary_path']=[exact[0]];record['ai_proposal']['official_nodes']=[exact[0]]
      if any(x['import_record']['stable_id']==stable for x in rows):
       exceptions.append(dict(file_id=r['file_id'],code='duplicate_boundary_candidate_identity',required_action='Q'+child['reference']+' '+subref(child)+' PDF '+page(child)+' has another detected boundary with the same identity; inspect the saved layout profile.'));continue
      row=dict(import_record=record,question=review_rich,answer=arich,import_eligible=eligible,bundle=bundle,source_file_id=r['file_id']);rows.append(row)
      detail=base/'details'/(stable+'.html');detail.parent.mkdir(exist_ok=True);detail.write_text('<!doctype html><meta charset="utf-8"><title>Private Needs Review</title><style>body{font:17px system-ui;max-width:1100px;margin:24px auto}table{border-collapse:collapse}td,th{border:1px solid #889;padding:8px}</style><h1>Needs Review — '+stable+'</h1><p>'+html.escape(r['filename']+' · '+d['exam_attempt']+' · Q'+child['reference']+subref(child)+' · PDF '+page(child))+'</p><h2>Shared facts</h2>'+(scenarios.get(record['practice_structure'].get('scenario_key'),{}).get('body_html',''))+'<h2>Question</h2>'+rich['body_html']+'<h2>Provisional answer candidate</h2>'+(arich['body_html']if arich else'<p>Answer Pending</p>')+'<pre>'+html.escape(json.dumps(warnings,indent=2))+'</pre>')
      for kind,body in [('question',rich),('answer',arich)]:
       if body:
        for b in body['blocks']:
         if b['type']=='table':table_report.append(dict(stable_id=stable,kind=kind,page=b['page'],rows=b['rows'],columns=b['columns'],numeric_check=b['numeric_check'],bbox=b['bbox'],method=b.get('method','ruled_geometry'),visual_review='not_independently_checked',detail='details/'+stable+'.html'))
      if eligible:
       source_rows[source_key(r)]=source(r)
       if answer_source:source_rows[source_key(answer_source)]=source(answer_source)
   # MCQ extraction remains separately keyed and never enters subjective packages.
   if any(x['region']['format']=='MCQ'and x['region']['side']=='question'for x in p.get('records',[])):
    pools=counterpart(r,manifest,payloads);a=pools[0]if len(pools)==1 else r if d['role']=='questions_and_answers'else None
    if a:
     group=dict(subject_code=subject,source_type=d['source_type'],exam_attempt=d['exam_attempt'],mtp_series=d['series'],issue_period=d['document_issue_period'],edition_key=edition(r),question_path=r['local_path'],answer_path=a['local_path'],question_source_key=source_key(r),answer_source_key=source_key(a),question_url=source_url(r),answer_url=source_url(a),layout_profile='six-paper-layout-discovery-3',expected_count=sum(x['region']['side']=='question'and x['region']['format']=='MCQ'for x in p['records']))
     try:
      candidates,report,cases=(ibs_mcq.extract_group if subject=='IBS'else mcq_pipeline.extract_group)(group)
      for c in candidates:c['import_eligible']=eligible;c['source_file_id']=r['file_id']
      mcqs+=candidates;cat.write(base/'mcq-reports'/(r['file_id']+'.json'),report)
      if eligible:source_rows[source_key(r)]=source(r);source_rows[source_key(a)]=source(a)
     except Exception as e:exceptions.append(dict(file_id=r['file_id'],code='mcq_extraction_held',required_action=str(e)))
    else:exceptions.append(dict(file_id=r['file_id'],code='mcq_key_source_unresolved',required_action='Identify the exact matching key source; options/keys were not invented.'))
  cat.write(base/'source-inventory.json',[r for r in manifest if r['collection_subject']==subject]);cat.write(base/'source-pairing-report.json',source_counts);cat.write(base/'exceptions.json',exceptions);cat.write(base/'table-report.json',table_report);cat.write(base/'subjective-candidates.json',rows);cat.write(base/'mcq-candidates.json',mcqs)
  books=fr_package.workbook(rows,[],{'nodes':[]},exceptions,base,1,inventory);(base/books).rename(base/(subject+'-Owner-Review-'+revision+'.xlsx'))
  groups=defaultdict(list)
  for row in rows:
   if row['import_eligible']:groups[(row['import_record']['exam_attempt'],edition(index[row['source_file_id']]),row['bundle'])].append(row)
  packages=[]
  for(attempt,ek,kind),items in groups.items():
   for n in range(0,len(items),100):
    batch=items[n:n+100];rs=[x['import_record']for x in batch];file=index[batch[0]['source_file_id']];needed={d['source_key']for d in rs}|{source_key(index[x['import_record']['source_provenance']['answer_drive_file_id']])for x in batch if x['import_record']['answer']};sc={d['practice_structure']['scenario_key']:scenarios[d['practice_structure']['scenario_key']]for d in rs if d['practice_structure'].get('scenario_key')};key=subject+'-'+re.sub('[^A-Za-z0-9]+','-',attempt)+'-'+kind+'-'+revision+'-'+str(n//100+1).zfill(3);packages.append(build_zip(base/'imports'/(key+'.zip'),key,subject,attempt,ek,context_taxonomy(file),{k:v for k,v in source_rows.items()if k in needed},rs,sc))
  mg=defaultdict(list)
  for c in mcqs:
   if c['import_eligible']:mg[c['exam_attempt'],c['edition_key']].append(c)
  for(attempt,ek),items in mg.items():
   for n in range(0,len(items),100):
    batch=items[n:n+100];file=index[batch[0]['source_file_id']];needed={c['source_key']for c in batch}|{c['answer']['source_key']for c in batch};extra={'import_eligible','source_file_id','academic_review_status','publication_status','classification_origin','rights_mode','attribution','record_revision','extractor'};clean=[{k:v for k,v in c.items()if k not in extra}for c in batch]
    for c in clean:
     # An incomplete candidate stays private. Never invent an absent option to
     # accommodate a key detected elsewhere in the source.
     if set(c['correct_options'])-{o['id']for o in c['options']}:
      c['exceptions'].append('missing_option_for_detected_key');c['correct_options']=[];c['key_verified']=False;c['key_policy']='needs_owner_decision'
    key=subject+'-'+re.sub('[^A-Za-z0-9]+','-',attempt)+'-MCQ-'+revision+'-'+str(n//100+1).zfill(3);packages.append(build_zip(base/'imports'/(key+'.zip'),key,subject,attempt,ek,context_taxonomy(file),{k:v for k,v in source_rows.items()if k in needed},clean,{},'mcqs'))
  summary=dict(subject=subject,pdfs_inventoried=len(inventory),document_outcomes=dict(Counter(x['outcome']for x in inventory)),subjective_parent_regions=sum(x['subjective_parents']for x in source_counts),subjective_subpart_drafts=len(rows),theory=sum(x['bundle']=='SUBJECTIVE-THEORY'for x in rows),practical_case=sum(x['bundle']=='SUBJECTIVE-PRACTICAL'for x in rows),structural_answer_candidates=sum(bool(x['answer'])for x in rows),answer_pending=sum(not x['answer']for x in rows),independently_verified_pairs=0,table_models=len(table_report),tables_independently_visually_checked=0,mcq_candidates=len(mcqs),mcq_explicit_keys=sum(c['key_verified']for c in mcqs),mcq_without_keys=sum(not c['key_verified']for c in mcqs),importable_subjective_drafts=sum(p['records']for p in packages if p['kind']=='questions'),importable_mcq_drafts=sum(p['records']for p in packages if p['kind']=='mcqs'),packages=packages,owner_approvals=0,automatic_publications=0,coverage='INCOMPLETE: source identity, historical applicability, table/segmentation exceptions and owner publication decisions remain distinct from automated parsing.')
  cat.write(base/'processing-summary.json',summary);cat.write(base/'import-order.json',dict(revision=revision,instructions='Extract the outer private delivery bundle. Upload each imports/*.zip in this order. Each child uses Upload ZIP → Preview → Save as Drafts. Publish All remains an owner decision and enforces actual rights/integrity. Do not upload the outer research bundle as a plugin or Academic ZIP.',packages=packages));totals[subject]=summary;print(json.dumps(dict(subject=subject,records=len(rows),packages=len(packages))),flush=True)
 cat.write(out/'processing-summary.json',totals);return totals
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('manifest');p.add_argument('worker_manifest');p.add_argument('output');p.add_argument('--revision',required=True);a=p.parse_args();build(a.manifest,a.worker_manifest,a.output,a.revision)
