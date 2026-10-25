"""Bounded January 2026 FR private pilot; no automatic approvals/publication.

The manifest supplies authorised local originals and verified identities. Missing
files get explicit exceptions. Existing owner work is never overwritten.
"""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import html
import json
from pathlib import Path
import sqlite3
import zipfile
import fitz
import gold_layout as gold
import layout_engine
import fr_package


def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')


def proposed_paths(keys,nodes):
    indexed={n['node_key']:n for n in nodes};paths=[];missing=[]
    for key in keys:
        path=[];seen=set()
        while key:
            if key in seen or key not in indexed:missing.append(key);break
            seen.add(key);node=indexed[key];path.insert(0,dict(node,key=node['node_key']));key=node.get('parent_key')
        if path:paths.append(path)
    unique={}
    for path in paths:
        for node in path:unique.setdefault(node['node_key'],node)
    return list(unique.values()),paths[0] if paths else [],missing


def discover_available(sources):
    available={};failures={}
    for source in sources:
        if source.get('subject_code')!='FR' or source.get('exam_attempt')!='January 2026':raise ValueError('This worker accepts the January 2026 FR pilot only.')
        path=source.get('local_path')
        if not path or not Path(path).is_file():continue
        try:
            if gold.sha(Path(path).read_bytes())!=source.get('source_hash'):raise ValueError('Original bytes differ from the pinned source hash; approve a separate revision.')
            with fitz.open(path) as document:
                observed='\n'.join(page.get_text()[:1000] for page in document)
                if 'FINANCIAL REPORTING' not in observed.upper():raise ValueError('Financial Reporting paper identity not recovered; inspect the original.')
                records,profile=gold.discover(document,source)
                available[source['key']]=dict(source=source,records=records,profile=profile)
        except (ValueError,RuntimeError) as error:failures[source['key']]=str(error)
    return available,failures


def matching_answer(question,paper,pool):
    candidates=gold.exact_answer(question,paper,pool)
    if len(candidates)!=1:return candidates,None,None,None
    answer=candidates[0];source=next(a for a in pool if a['source_hash']==paper['answer_document_hash'] and all(a.get(k)==paper.get(k) for k in ('subject_code','source_type','exam_attempt','mtp_series')))
    with fitz.open(source['local_path']) as document:rich=gold.reconstruct(answer,document)
    return candidates,answer,rich,source


def run(manifest_path,output,previous=None,taxonomy=None):
    manifest=json.loads(Path(manifest_path).read_text());out=Path(output)
    if out.exists():raise ValueError('Use a new output revision. Existing review decisions/evidence must be retained.')
    out.mkdir(parents=True);db=sqlite3.connect(out.parent/'january-checkpoints.sqlite')
    db.execute('CREATE TABLE IF NOT EXISTS source_runs (source_hash TEXT,engine_hash TEXT,payload TEXT,created_at TEXT,PRIMARY KEY(source_hash,engine_hash))')
    engine=gold.sha(b''.join(Path(path).read_bytes() for path in (gold.__file__,__file__,fr_package.__file__,layout_engine.__file__)));old=json.loads(Path(previous).read_text()) if previous else []
    prior={(r['import_record']['source_hash'],r['import_record']['reference'],r['import_record']['subreference']):r for r in old}
    taxonomy=json.loads(Path(taxonomy).read_text()) if taxonomy else {'nodes':[],'editions':[]};edition=manifest['edition_key'];taxonomy['nodes']=[n for n in taxonomy['nodes'] if n['edition_key']==edition];taxonomy['editions']=[n for n in taxonomy['editions'] if n['edition_key']==edition]
    rows=[];exceptions=[];inventory=[];table_report=[];reconciliation=[];profiles=[];scenarios={}
    discovered,failures=discover_available(manifest['sources']);pool=[];seen_answers=set()
    for found in discovered.values():
        source=found['source'];identity=tuple(source.get(k) for k in ('source_hash','subject_code','source_type','exam_attempt','mtp_series'))
        if source.get('role') in ('answers','questions_and_answers') and identity not in seen_answers:pool.append({**source,'records':found['records']});seen_answers.add(identity)
    for source in manifest['sources']:
        if source.get('subject_code')!='FR' or source.get('exam_attempt')!='January 2026':raise ValueError('This worker accepts the January 2026 FR pilot only.')
        src=deepcopy(source);local=src.pop('local_path',None)
        if not local or not Path(local).is_file():
            src.update(outcome='blocked_missing_original',questions=None,verified_answer_relationships=0)
            inventory.append(src);exceptions.append({'source':src['key'],'code':'original_pdf_not_available','required_action':src.get('required_action','Supply the authorised original privately; no other attempt is substituted.')});continue
        if src['key'] in failures:
            src.update(outcome='blocked_original_validation',questions=None,verified_answer_relationships=0);inventory.append(src);exceptions.append(dict(source=src['key'],code='original_validation_failed',required_action=failures[src['key']]));continue
        digest=src['source_hash']
        with fitz.open(local) as document:
            records=discovered[src['key']]['records'];profile=deepcopy(discovered[src['key']]['profile']);profile['source']=src;profiles.append(profile);write(out/'layout-profiles'/f"{src['key']}.json",profile)
            db.execute('INSERT OR IGNORE INTO source_runs VALUES (?,?,?,?)',(digest,engine,json.dumps(profile),datetime.now(timezone.utc).isoformat()));db.commit()
            paper={**src,'answer_document_hash':src.get('answer_document_hash',digest if src.get('role')=='questions_and_answers' else None)}
            qs=[r for r in records if r['side']=='question' and r['format']=='SUBJECTIVE'];mcqs=[r for r in records if r['side']=='question' and r['format']=='MCQ'];source_rows=[]
            write(out/src['key']/'preserved-mcqs.json',[{k:v for k,v in r.items()} for r in mcqs])
            for parent in qs:
                children,ambiguity=gold.split_independent(parent)
                if ambiguity:exceptions.append({'source':src['key'],**ambiguity,'required_action':'Owner to distinguish background facts from independent requirements.'})
                for q in children:
                    key=(digest,q['reference'],q['subreference']);prev=prior.get(key);old_record=deepcopy(prev['import_record']) if prev else None
                    stable=old_record['stable_id'] if old_record and not q['alternative'] else 'R-'+layout_engine.identity(digest,'descriptive',q['reference'],q['subreference']+(':'+q['alternative'] if q['alternative'] else ''))
                    qrich=gold.reconstruct(q,document);candidates,answer,arich,answer_source=matching_answer(q,paper,pool)
                    d=old_record or dict(stable_id=stable,source_hash=digest,source_key=src['key'],subject_code='FR',source_type=src['source_type'],exam_attempt='January 2026',mtp_series=src.get('mtp_series',''),section='descriptive',reference=q['reference'],subreference=q['subreference'],edition_id=None,classification=[],scheme='New Scheme',rights_mode='licensed_private_review',rights_basis='Owner-authorised private academic research. Publication scope and academic decisions must be confirmed in WordPress.',review_notes='',confidence='Provisional; owner comparison required',marks=None,marks_verified=False)
                    d.update(stable_id=stable,title=src['title'],official_url=src.get('official_url',''),question_page=str(q['start']['page'])+'-'+str(max(l['page'] for l in q['lines'])),question_coordinates={'start':q['start'],'end_exclusive':q['end_exclusive']},heading_evidence=q['heading'] or {},source_revision=digest,engine_revision={'engine':gold.VERSION,'engine_hash':engine},question_format='subjective',question_type=src.get('question_types',{}).get(q['reference'],'unknown'),extraction_status='needs_review',source_provenance={'drive_file_id':src['drive_file_id']} if src.get('drive_file_id') else {},practice_structure={'parent_stable_id':old_record['stable_id'] if len(children)>1 and old_record else '', 'alternative':q['alternative'],'layout_profile':src['key'],'boundary_signature':gold.sha(json.dumps([q['start'],q['end_exclusive']],sort_keys=True)),'quality_required':True},quality_checks={})
                    if answer_source and answer_source.get('drive_file_id'):d['source_provenance']['answer_drive_file_id']=answer_source['drive_file_id']
                    if q.get('shared_lines'):
                        shared=q['shared_lines'];common={**q,'lines':shared,'start':dict(page=shared[0]['page'],bbox=shared[0]['bbox'],column=0),'end_exclusive':q['start']};body=gold.reconstruct(common,document)
                        group=q['subreference'].split('.')[0] if '.' in q['subreference'] else 'root';scenario_key='SC-'+digest[:16]+'-Q'+q['reference']+'-'+group;d['practice_structure']['scenario_key']=scenario_key
                        scenarios[scenario_key]=dict(source_hash=digest,scenario_key=scenario_key,body_html=body['body_html'],rights_basis=d['rights_basis'],evidence=dict(start=common['start'],end=common['end_exclusive']))
                    d['blocking_exceptions']=list(dict.fromkeys(qrich['warnings']+(arich['warnings'] if arich else ['exact_answer_not_established'])+['owner_visual_comparison_required']))
                    # The earlier source-specific unresolved Q19/corrigendum is retained.
                    if digest in manifest.get('held_answer_references',{}) and q['reference'] in manifest['held_answer_references'][digest]:d['blocking_exceptions'].append('prior_answer_conflict_or_corrigendum_requires_owner_decision')
                    tags=manifest.get('classification_proposals',{}).get(src['key'],{}).get(q['reference'],{})
                    selected,primary_path,missing_nodes=proposed_paths(tags.get('node_keys',[]),taxonomy['nodes'])
                    if missing_nodes:d['blocking_exceptions'].append('historical_topic_key_not_found')
                    # Exact official node keys are proposed, never approved or remapped.
                    d['ai_proposal']={'historical_edition':edition,'official_nodes':selected,'primary_path':primary_path,'additional_node_keys':tags.get('node_keys',[])[1:],'method':'mixed','reasoning':tags.get('reasoning','Read the operative requirement and verify its exact historical topic.'),'owner_state':'needs_review'}
                    d['reasoning']=tags.get('reasoning',d.get('reasoning',''))
                    def content(rich):return dict(body_html=rich['body_html'],author_name='The Institute of Chartered Accountants of India',source_location='PDF page(s) '+d['question_page'],source_text_sha256=rich['source_text_sha256'],structure={'blocks':rich['blocks']},checks=rich['fidelity'])
                    d['rich_content']={'question':content(qrich)}
                    if arich:
                        d['rich_content']['answer']=content(arich);d['rich_content']['answer']['source_location']='PDF page(s) '+str(answer['start']['page'])+'-'+str(max(l['page'] for l in answer['lines']))
                        d['answer']=dict(source_hash=answer_source['source_hash'],official_url=answer_source.get('official_url',''),reference=q['reference'],subreference=q['subreference'],alternative=q['alternative'],question_identity=stable,question_reference=q['reference'],question_subreference=q['subreference'],question_source_hash=digest,page=d['rich_content']['answer']['source_location'],mode='licensed',subject_code='FR',source_type=src['source_type'],exam_attempt='January 2026',mtp_series=src.get('mtp_series',''),notes='Provisional exact structural candidate, not owner verification.')
                    else:d['answer']={}
                    for kind,rich in [('question',qrich),('answer',arich)]:
                        if not rich:continue
                        for n,model in enumerate(b for b in rich['blocks'] if b['type']=='table'):
                            name=src['key']+'-Q'+q['reference']+q['subreference']+'-'+kind+'-T'+str(n+1);box=fitz.Rect(model['bbox']);box+=(-8,-8,8,8);image=out/'private-source-evidence'/(name+'.png');image.parent.mkdir(exist_ok=True)
                            if kind=='answer' and answer_source['local_path']!=local:
                                with fitz.open(answer_source['local_path']) as answer_pdf:answer_pdf[model['page']-1].get_pixmap(clip=box,matrix=fitz.Matrix(1.5,1.5)).save(image)
                            else:document[model['page']-1].get_pixmap(clip=box,matrix=fitz.Matrix(1.5,1.5)).save(image)
                            comp=out/'table-comparisons'/(name+'.html');comp.parent.mkdir(exist_ok=True);comp.write_text('<!doctype html><meta charset="utf-8"><title>PRIVATE source comparison</title><style>body{font:16px system-ui;color:#152b4b}main{display:grid;grid-template-columns:1fr 1fr;gap:20px}img{width:100%}table{border-collapse:collapse;width:100%}th,td{border:1px solid #8799af;padding:8px;text-align:left;vertical-align:top}</style><h1>PRIVATE — '+html.escape(name)+'</h1><p>PDF page '+str(model['page'])+' · Needs Review. Numeric checks are not visual or academic verification.</p><main><section><h2>Original PDF region</h2><img src="../private-source-evidence/'+image.name+'"></section><section><h2>Reconstructed selectable HTML</h2>'+gold.table_html(model)+'</section></main>')
                            table_report.append(dict(stable_id=stable,kind=kind,source_page=model['page'],rows=model['rows'],columns=model['columns'],numeric_check=model['numeric_check'],comparison_file=str(comp.relative_to(out)),visual_status='needs_owner_comparison',method=model.get('method','ruled_geometry')))
                    detail=out/'details'/(stable+'.html');detail.parent.mkdir(exist_ok=True);before=prev['question']['body_html'] if prev else '<p>No earlier candidate.</p>'
                    detail.write_text('<!doctype html><meta charset="utf-8"><title>PRIVATE FR review</title><style>body{font:17px system-ui;max-width:1100px;margin:30px auto;color:#152b4b}table{border-collapse:collapse;width:100%}td,th{border:1px solid #899cb2;padding:8px}section{padding:15px;border:1px solid #ccd6e2;margin:15px 0}pre{white-space:pre-wrap}</style><h1>PRIVATE — '+stable+' — Q'+q['reference']+'</h1><p>Needs Review. '+html.escape(d['question_page'])+'</p><section><h2>Reconstructed question</h2>'+qrich['body_html']+'</section><section><h2>Provisional answer candidate</h2>'+(arich['body_html'] if arich else 'Not established')+'</section><details><summary>Earlier v0.5 question for comparison</summary>'+before+'</details><pre>'+html.escape(json.dumps(d['blocking_exceptions'],indent=2))+'</pre>')
                    row=dict(import_record=d,question=qrich,answer=arich,answer_candidates=[{'page':answer['start']['page'],'source_hash':answer_source['source_hash']}] if answer else [],source=src);rows.append(row);source_rows.append(row);reconciliation.append(dict(old_stable_id=old_record['stable_id'] if old_record else None,new_stable_id=stable,action='retain_identity' if old_record else 'new_child_or_unseen_identity',reference=q['reference'],subreference=q['subreference'],alternative=q['alternative'],old_records_deleted=False))
                    for issue in d['blocking_exceptions']:exceptions.append({'source':src['key'],'stable_id':stable,'code':issue,'required_action':'Compare the private PDF and corrected HTML; retain Needs Review until resolved.'})
            src.update(outcome='processed_needs_review',pages=len(document),subjective_parent_questions=len(qs),subjective_records=len(source_rows),mcqs_separated=len(mcqs),answer_candidates=sum(bool(r['answer']) for r in source_rows),verified_answer_relationships=0);inventory.append(src)
            fr_package.batches([r['import_record'] for r in source_rows],out/src['key']/'imports','studio-drafts')
    previous_ledger=Path(previous).parent/'prior-owner-corrections.json' if previous else None
    if previous_ledger and previous_ledger.is_file():(out/'prior-owner-corrections.json').write_bytes(previous_ledger.read_bytes())
    write(out/'previous-record-snapshots.json',[prior[k] for k in prior if k[0] in {s.get('source_hash') for s in manifest['sources']}]);write(out/'source-inventory.json',inventory);write(out/'layout-profiles.json',profiles);write(out/'exceptions.json',exceptions);write(out/'table-reconstruction-report.json',table_report);write(out/'old-to-new-reconciliation.json',reconciliation);write(out/'private-candidates.json',rows);write(out/'owner-decisions-ledger.json',dict(format='source-hash/section/reference/subpart/alternative',decisions=[],previous_decisions_retained=True))
    # Keep each official edition distinct; do not substitute the May 2026 tree.
    fr_package.batches(taxonomy['nodes'],out/'taxonomy-imports','official-hierarchy',max_rows=100,key='nodes',extra={'editions':taxonomy['editions']})
    workbook=fr_package.workbook(rows,[],taxonomy,exceptions,out,1,inventory)
    coverage=dict(sources=inventory,subjective_records=len(rows),academic_approvals=0,publications=0,table_regions=len(table_report),table_regions_owner_verified=0,missing_sources=sum(s['outcome']=='blocked_missing_original' for s in inventory),failed_sources=sum(s['outcome']=='blocked_original_validation' for s in inventory),acceptance='INCOMPLETE until missing originals, visual reconstruction and owner decisions are resolved')
    if scenarios:write(out/'shared-scenarios-001.json',dict(scenarios=list(scenarios.values())))
    write(out/'coverage.json',coverage);write(out/'import-order.json',dict(first='taxonomy-imports in numeric order; all draft',shared_facts='Import shared-scenarios-001.json first when present; private only',second='source-specific imports in numeric order; all Needs Review',workbook=workbook,existing_records='Preview and compare corrected private reconstruction. Preserve IDs, owner classifications, notes and progress. Do not delete/reimport.',publication='No approval is supplied. Owner-only publication after complete checks.'))
    (out/'READ-FIRST.txt').write_text('PRIVATE JANUARY 2026 FR — VERSION 0.5.1\n\nThis is an incomplete owner-review candidate package. Read coverage.json, source-inventory.json and exceptions.json. Sources without original bytes are explicitly blocked; no other attempt was substituted. Table geometry and numeric agreement are not independent visual/academic verification. Every question remains Needs Review. No real question has been approved or published. Open details/*.html and table-comparisons/*.html privately. Preserve source-specific corrections and earlier IDs. Never upload this package to public Git, CI or WordPress Media. Import only the numbered JSON files through the administrator-only Studio importer.\n')
    checks={str(p.relative_to(out)):gold.sha(p.read_bytes()) for p in sorted(out.rglob('*')) if p.is_file()};write(out/'manifest.json',dict(version='0.5.1',status='needs_review',files=checks))
    archive=out.with_suffix('.zip')
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(out.rglob('*')):
            if p.is_file():z.write(p,'JAN2026-FR-V051-PRIVATE/'+str(p.relative_to(out)))
    print(json.dumps({'output':str(out),'zip':str(archive),'sha256':gold.sha(archive.read_bytes()),'subjective_records':len(rows),'missing_source_documents':coverage['missing_sources'],'table_regions':len(table_report),'owner_approvals':0}))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('manifest');p.add_argument('output');p.add_argument('--previous');p.add_argument('--taxonomy');a=p.parse_args();run(a.manifest,a.output,a.previous,a.taxonomy)
