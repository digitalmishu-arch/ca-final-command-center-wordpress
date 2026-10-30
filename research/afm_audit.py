"""Focused r010 AFM structural reconciliation; private inputs, no bulk extraction.

Source comparison is automated/AI-assisted technical evidence, never owner or
independent human academic approval. Existing integrity holds are not dismissed
by a numbering or answer-boundary correction.
"""
from pathlib import Path
from collections import Counter,defaultdict
from copy import deepcopy
import argparse,json,re,unicodedata,zipfile
import fitz
import afm_structure as structure
import afm_reconcile as afm
import afm_tables
import gold_layout as gold
import archive_release as prior
import archive_integrity
import archive_catalog as cat
import fr_corpus as fr
import layout_engine

ROMANS={'i','ii','iii','iv','v','vi'}
def key(r):return r['reference'],r.get('subreference',''),r.get('practice_structure',{}).get('alternative','')
def rendered_hash(x):return gold.sha(x['body_html'])if x else None

def audit(bank_path,profiles,baseline,decisions,output):
    out=cat.private(output);out.mkdir(parents=True,exist_ok=True);bank=json.loads(Path(bank_path).read_text());old=deepcopy(bank['subjective']);source={s['file_id']:s for s in bank['source_inventory']};profiles=Path(profiles);cache={};keeps=json.loads(Path(decisions).read_text());groups=defaultdict(list);original={}
    with zipfile.ZipFile(baseline)as z:
        m=json.loads(z.read('manifest.json'))
        for entry in m['packages']:
            import io
            with zipfile.ZipFile(io.BytesIO(z.read(entry['path'])))as child:
                cm=json.loads(child.read('manifest.json'))
                for item in cm['items']:
                    if item['kind']=='questions':
                        for r in json.loads(child.read(item['path']))['records']:original[r['stable_id']]=r
    assert len(original)==1255 and set(original)=={x['import_record']['stable_id']for x in old}
    for row in old:groups[(row['source_file_id'],row['import_record']['reference'])].append(row)
    def profile(fid):
        if fid not in cache:cache[fid]=json.loads((profiles/(fid+'.json')).read_text())
        return cache[fid]
    new=[];mapping=[];ledger=[];material=[];parent_audit=[];changed_tables=[];documents={};table_cache={};reconstructed=0
    # Exact source-line hashes allow reuse of already reconstructed r010 HTML.
    rich_index={}
    cached_rows=[]
    if(out/'bank-r011.json').exists():cached_rows=json.loads((out/'bank-r011.json').read_text())['subjective']
    for row in old+cached_rows:
        for side in('question','answer','answer_candidate'):
            if row.get(side):rich_index[(row['source_file_id']if side=='question'else row['answer_file_id'],row[side]['source_text_sha256'])]=row[side]
    def rich(region,fid):
        nonlocal reconstructed
        raw='\n'.join(l['text']for l in region['lines']);h=gold.sha(raw)
        if (fid,h)in rich_index:return deepcopy(rich_index[(fid,h)])
        if fid not in documents:documents[fid]=fitz.open(source[fid]['local_path']);table_cache[fid]={}
        value=gold.reconstruct(region,documents[fid],table_cache[fid]);value=afm_tables.normalize(value,documents[fid]);reconstructed+=1;rich_index[(fid,h)]=value;return deepcopy(value)
    for (fid,ref),previous in groups.items():
        parent=next(x['region']for x in profile(fid)['records']if x['region']['side']=='question'and x['region']['reference']==ref and x['region']['format']=='SUBJECTIVE');parent={**parent,'source_type':source[fid]['identity']['source_type']};afid=previous[0]['answer_file_id'];answers=[x['region']for x in profile(afid)['records']if x['region']['side']=='answer'and x['region']['reference']==ref and x['region']['format']=='SUBJECTIVE']if afid else[];pa=answers[0]if len(answers)==1 else None
        qs,ans,issues=structure.complete_parts(parent,pa)
        keep=keeps.get(fid+'|'+ref,[])
        if keep:
            legacy_q,legacy_a,_=afm.split_question(parent,pa,split_nested_requirements=True)
            for prefix in keep:
                candidates=[q for q in legacy_q if q.get('subreference','').startswith(prefix+'.')if prefix]if prefix else[q for q in legacy_q if q.get('subreference')in ROMANS]
                assert len(candidates)>=2,(fid,ref,prefix)
                qs=[q for q in qs if q.get('subreference','')!=prefix]+candidates
                ans=[a for a in ans if a.get('subreference','')!=prefix]+[a for a in legacy_a if a.get('subreference')in{q['subreference']for q in candidates}]
            qs.sort(key=lambda q:(q['start']['page'],q['start']['bbox'][1],q['start']['bbox'][0]))
        amap={(a.get('subreference',''),a.get('alternative','')):a for a in ans};targets=[]
        for q in qs:
            sub=prior.subref(q);alt=q.get('alternative','');exact=next((x for x in previous if key(x['import_record'])==(ref,sub,alt)),None)
            inputs=[exact]if exact else[x for x in previous if x['import_record']['practice_structure'].get('alternative','')==alt and (not sub or x['import_record']['subreference'].startswith(sub+'('))]
            if not inputs:inputs=previous # retained as uncertain, never mapped to an unrelated source
            template=deepcopy(exact or inputs[0]);r=deepcopy(original[(exact or inputs[0])['import_record']['stable_id']]);old_id=r['stable_id']
            sid=old_id if exact else'R-'+layout_engine.identity(r['source_hash'],'descriptive'+(':'+alt if alt else''),ref,q.get('subreference','')+(':'+alt if alt else''))
            a=amap.get((q.get('subreference',''),alt));answer_region=a
            if a and a.get('shared_lines'):answer_region={**a,'lines':a['shared_lines']+a['lines'],'start':fr.where(a['shared_lines'][0])}
            body=rich(q,fid);answer=rich(answer_region,afid)if answer_region and afid else None
            checkq={**q,'lines':q.get('shared_lines',[])+q['lines']};evidence=afm.corroboration(checkq,answer_region)if answer_region else{};state='A'if answer and evidence['corroborated']else'B'if answer else'C'if afid else'D'
            # Remove ONLY obsolete matching/granularity diagnostics. Formatting,
            # corrigenda, source identity and historical holds survive the merge.
            inherited=[w for x in inputs for w in x['import_record']['blocking_exceptions']]
            warnings=[w for w in inherited if not re.search(r'^answer_mapping_conflict_state_|^answer_parent_part_profile_requires_review$',w)]
            if state=='B':warnings.append('answer_mapping_conflict_limited_content_corroboration_source_part_matches')
            if state in('C','D'):warnings.append('answer_mapping_conflict_'+('exact_parent_part_unresolved'if state=='C'else'source_answer_unavailable'))
            if any(w.startswith('question_boundary')for w in issues):warnings.append('question_integrity_failed_source_part_boundary_requires_review')
            for side,val in [('question',body),('answer',answer)]:
                if not val:continue
                if val.get('layout_exceptions'):warnings.append('question_integrity_failed_fragmented_formula'if side=='question'else'answer_mapping_conflict_fragmented_formula')
                if not val['fidelity']['passed']:warnings.append('question_integrity_failed_retained_transcription_hold'if side=='question'else'answer_formatting_conflict_retained_transcription_hold')
                if any(unicodedata.category(c)in('Co','Cn')or c=='\ufffd'for c in val['plain_text']):val['fidelity']['passed']=False;warnings.append('question_integrity_failed_source_font_glyph'if side=='question'else'answer_formula_conflict_source_font_glyph')
            r.update(stable_id=sid,reference=ref,subreference=sub,question_page=prior.page(q),question_coordinates=dict(start=q['start'],end_exclusive=q['end_exclusive']),blocking_exceptions=sorted(set(warnings)),rich_content=dict(question=prior.content(body)),answer={},extraction_status='needs_review',quality_checks={})
            if not exact:
                r['title']=(source[fid]['identity']['historical_paper_title']+' '+r['exam_attempt']+' Q'+ref+afm.refpart(q)+(' — '+alt if alt else''))[:190];r['previous_corrections']=[];r['engine_revision']={'engine':afm.VERSION,'structural_audit':'r011_complete_problem'};r['practice_structure']=dict(parent_stable_id='P-'+gold.sha(r['source_hash']+'|'+ref)[:48],alternative=alt,quality_required=True)
            r['practice_structure'].pop('scenario_key',None)
            if q.get('shared_lines'):
                common=q['shared_lines'];last=common[-1];sreg={**q,'lines':common,'start':fr.where(common[0]),'end_exclusive':dict(page=last['page'],bbox=[last['bbox'][0],last['bbox'][3]+.1,last['bbox'][2],last['bbox'][3]+.1],column=0)};sr=rich(sreg,fid);sk='SC-'+gold.sha(r['source_hash']+'|'+sr['source_text_sha256'])[:48];bank['scenarios'].setdefault(sk,dict(scenario_key=sk,source_hash=r['source_hash'],body_html=sr['body_html'],rights_basis=r['rights_basis'],evidence=dict(start=sreg['start'],end=sreg['end_exclusive'])));r['practice_structure']['scenario_key']=sk
                if not sr['fidelity']['passed']:r['blocking_exceptions'].append('question_integrity_failed_shared_scenario_format')
            if answer:
                r['rich_content']['answer']=prior.content(answer);r['answer']=dict(source_hash=source[afid]['source_hash'],official_url='https://drive.google.com/file/d/'+afid+'/view',reference=ref,subreference=sub,alternative=alt,question_identity=sid,question_reference=ref,question_subreference=sub,question_source_hash=r['source_hash'],page=str(prior.page(a)),subject_code='AFM',source_type=r['source_type'],exam_attempt=r['exam_attempt'],mtp_series=r['mtp_series'],mode='licensed',notes='r011 '+state+': exact source-context and complete-problem answer region; automated/AI-assisted source comparison, not independent human academic verification.')
            marks=re.findall(r'\((\d{1,2})\s*Marks?\)',body['plain_text'],re.I);r['marks']=int(marks[-1])if len(set(marks))==1 else None;r['marks_verified']=r['marks']is not None
            row=dict(import_record=r,question=body,answer=answer,answer_candidate=deepcopy(template.get('answer_candidate'))if not answer else None,answer_candidate_page=template.get('answer_candidate_page','')if not answer else'',source_file_id=fid,answer_file_id=afid,match_state=state,match_evidence={**evidence,'question_region':structure.span_evidence(q),'answer_region':structure.span_evidence(a),'source_hash':r['source_hash'],'answer_hash':source[afid]['source_hash']if afid else'', 'source_context_fields':{k:r[k]for k in('subject_code','source_type','exam_attempt','mtp_series','issue_period','scheme')},'human_academic_approval':False},proposed_topics=deepcopy(template['proposed_topics']),original_subject=template['original_subject'],source_filename=template['source_filename'],import_eligible=True)
            archive_integrity.hold(row)
            if exact:
                # Preserve exact unchanged import payloads, rather than create
                # gratuitous revision conflicts in otherwise untouched records.
                oldr=original[old_id];same_content=all(oldr.get('rich_content',{}).get(k,{}).get('body_html')==r.get('rich_content',{}).get(k,{}).get('body_html')for k in('question','answer'))and oldr.get('practice_structure',{}).get('scenario_key')==r['practice_structure'].get('scenario_key')
                if same_content and exact['match_state']=='A'and not issues:r=deepcopy(oldr);row['import_record']=r
            row['import_record']['blocking_exceptions']=sorted(set(row['import_record']['blocking_exceptions']))
            new.append(row);targets.append((row,q,a,inputs))
            changed=not exact or original[old_id].get('rich_content')!=r.get('rich_content')
            if changed:
                material.append(dict(new_id=sid,old_ids=[x['import_record']['stable_id']for x in inputs],question_reference=ref,subreference=sub,source_file_id=fid,question_region=structure.span_evidence(q),answer_file_id=afid,answer_region=structure.span_evidence(a),kind='combined_nested_requirements'if not exact else'corrected_answer_boundary_or_payload',owner_approval=False))
                for side,value in [('question',body),('answer',answer)]:
                    if not value:continue
                    old_models=[b for x in inputs for v in [x.get(side),x.get('answer_candidate')if side=='answer'else None]for b in(v or{}).get('blocks',[])if b['type']=='table']
                    def table_signature(b):return gold.sha(json.dumps({k:b.get(k)for k in('rows','columns','header_rows')}|{'cells':[{k:c.get(k)for k in('row','column','rowspan','colspan','text')}for c in b['cells']]},sort_keys=True))
                    old_hashes={table_signature(b)for b in old_models};common_html=' '.join(bank['scenarios'].get(x['import_record'].get('practice_structure',{}).get('scenario_key'),{}).get('body_html','')for x in inputs)if side=='question'else''
                    for model in value['blocks']:
                        if model['type']=='table'and table_signature(model)not in old_hashes and gold.table_html(model)not in common_html:changed_tables.append(dict(question_id=sid,side=side,source_file_id=fid if side=='question'else afid,model=model,status='requires_source_vs_rendered_comparison'))
        for before in previous:
            br=before['import_record'];matches=[(row,q,a,inputs)for row,q,a,inputs in targets if before in inputs];assert len(matches)==1,(br['stable_id'],len(matches));row,q,a,inputs=matches[0];nr=row['import_record'];grouped=br['stable_id']!=nr['stable_id'];action='combined_into_complete_problem_no_activity_transfer'if grouped else'identity_retained';mapping.append(dict(old_id=br['stable_id'],new_id=nr['stable_id'],action=action,old_subreference=br['subreference'],new_subreference=nr['subreference'],old_question_html_sha256=rendered_hash(before['question']),old_answer_html_sha256=rendered_hash(before.get('answer')),new_question_html_sha256=rendered_hash(row['question']),new_answer_html_sha256=rendered_hash(row.get('answer')),student_history='Remain on original IDs; never automatically reassigned',existing_edit_policy='Retain current WordPress edits; show import conflict; owner correction uses current revision'))
            if before['match_state']in('B','C'):
                outcome='parent_requirement_granularity_resolved'if grouped and row['match_state']=='A'else'same_source_answer_warning_reclassified'if not grouped and row['match_state']=='A'else'remains_unresolved'
                ledger.append(dict(old_id=br['stable_id'],new_id=nr['stable_id'],old_state=before['match_state'],new_state=row['match_state'],outcome=outcome,confirmed_wrong_answer=False,source_file_id=fid,answer_file_id=afid,question_region=structure.span_evidence(q),answer_region=structure.span_evidence(a),evidence=row['match_evidence'],question_text_preview=row['question']['plain_text'][:650],answer_text_preview=(row.get('answer')or{}).get('plain_text','')[:650],comparison='Source PDF native lines and layout coordinates compared; not independent human academic approval'))
        parent_audit.append(dict(source_file_id=fid,reference=ref,question_source_hash=source[fid]['source_hash'],old_entries=len(previous),new_entries=len(qs),kept_independent_roman_parts=keep,issues=issues,question_source_pages=sorted({l['page']for l in parent['lines']}),answer_source_pages=sorted({l['page']for l in(pa or{}).get('lines',[])})))
        print(json.dumps(dict(file_id=fid,reference=ref,old=len(previous),new=len(qs),completed_parents=len(parent_audit))),flush=True)
    for d in documents.values():d.close()
    assert len(ledger)==305 and len(mapping)==1255 and len({x['import_record']['stable_id']for x in new})==len(new)
    bank['subjective']=new;bank['r011_reconciliation']=mapping
    # An explicit source key of "No correct option" is a known unscored
    # official outcome, not failed extraction or an invented correct choice.
    nco=[]
    for row in bank['mcqs']:
        r=row['import_record'];r['exceptions']=sorted(set(r['exceptions']));ev=r['answer'].get('key_evidence',{})
        if ev.get('no_correct_option'):
            assert not ev['correct_options']and not r['correct_options'];r['key_policy']='needs_owner_decision';r['key_verified']=False;r['exceptions']=[x for x in r['exceptions']if x not in('official_key_reports_no_correct_option','matching_explicit_answer_key_missing')]+['official_outcome_no_correct_option_unscored'];r['review_notes']='Official source key explicitly states No correct option. Original options retained. This is a known official outcome, not a missing-key extraction failure. Held outside ordinary scored practice until applicable official marking guidance is established.';r['explanation_html']='<p>The official answer key states <strong>No correct option</strong>. No option is designated correct. This question is retained for unscored academic review; ordinary single-correct scoring is withheld.</p>';nco.append(dict(question_id=r['stable_id'],source_file_id=row['source_file_id'],page=ev['page'],source_line=ev['source_line'],bbox=ev['bbox'],outcome='official_no_correct_option',scoring='not_scored',owner_approval=False))
    # Recompute source coverage, preserving all document identity exceptions.
    per=defaultdict(list)
    for row in new:per[row['source_file_id']].append(row)
    for c in bank['coverage']:
        rs=per[c['file_id']];c.update(subjective_parts=len(rs),source_corroborated_answers=sum(x['match_state']=='A'for x in rs),answer_candidates=sum(x['match_state']=='B'for x in rs),answer_pending=sum(x['match_state']in('C','D','E')for x in rs),blocked_questions=sum(any('question_integrity_failed'in w for w in x['import_record']['blocking_exceptions'])for x in rs),import_subjective=len(rs))
    summary=dict(baseline_subjective=1255,revised_subjective=len(new),parents_audited=len(parent_audit),old_warnings_audited=len(ledger),old_warning_outcomes=dict(Counter(x['outcome']for x in ledger)),confirmed_wrong_answer_associations=0,answer_states=dict(Counter(x['match_state']for x in new)),old_entries_combined=sum(x['action'].startswith('combined')for x in mapping),retained_original_ids=sum(x['action']=='identity_retained'for x in mapping),new_complete_problem_ids=len({x['new_id']for x in mapping if x['action'].startswith('combined')}),material_changes=len(material),changed_tables=len(changed_tables),native_regions_reconstructed=reconstructed,official_no_correct_option_mcqs=len(nco),duplicated_r010_no_correct_option_flags=2,question_integrity_holds=sum(any('question_integrity_failed'in w for w in x['import_record']['blocking_exceptions'])for x in new),table_formula_issue_records=sum(any(re.search('table|formula|glyph|numeric|geometry|font',w,re.I)for w in x['import_record']['blocking_exceptions'])for x in new),owner_academic_approvals=0,publications=0)
    for name,obj in [('bank-r011.json',bank),('answer-warning-audit.json',ledger),('old-to-new-identities.json',mapping),('material-changes.json',material),('changed-tables.json',changed_tables),('complete-parent-audit.json',parent_audit),('official-no-correct-option.json',nco),('summary.json',summary)]:
        if name=='bank-r011.json':(out/name).write_text(json.dumps(obj,ensure_ascii=False,separators=(',',':')))
        else:cat.write(out/name,obj)
    print(json.dumps(summary,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--bank',required=True);p.add_argument('--profiles',required=True);p.add_argument('--baseline',required=True);p.add_argument('--decisions',required=True);p.add_argument('--output',required=True);a=p.parse_args();audit(a.bank,a.profiles,a.baseline,a.decisions,a.output)
