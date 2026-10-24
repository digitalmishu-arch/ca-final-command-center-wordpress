<?php
/** Additional real-WordPress tests. All question/answer/marks fixtures are synthetic TEST ONLY records. */
function v2($method,$path,$data=null,$query=array(),$nonce=true) {
    global $server;
    $r=new WP_REST_Request($method,'/cafcc/v2/'.$path);
    if($nonce){$r->set_header('X-WP-Nonce',wp_create_nonce('wp_rest'));}
    foreach($query as $key=>$value){$r->set_param($key,$value);}
    if(null!==$data){$r->set_header('Content-Type','application/json');$r->set_body(wp_json_encode($data));}
    return $server->dispatch($r);
}
function record2($kind,$data,$id=0) {
    $r=v2($id?'PATCH':'POST','admin/'.$kind.($id?'/'.$id:''),$data);
    if(200!==$r->get_status()){throw new RuntimeException($kind.': '.wp_json_encode($r->get_data()));}
    baseline_after_record($kind,$r->get_data());
    return $r->get_data();
}
function csv2($kind,$rows) {
    $s=fopen('php://temp','r+');$header=CAFCC_Import::templates()[$kind];fputcsv($s,$header,',','"','');
    foreach($rows as $r){fputcsv($s,array_map(function($k)use($r){return $r[$k]??'';},$header),',','"','');}
    rewind($s);$text=stream_get_contents($s);fclose($s);return $text;
}
function snapshot_core() {
    global $wpdb;$result=array();
    foreach(array('subjects','chapters','topics','documents','questions','progress') as $kind){$t=CAFCC_DB::table($kind);$result[$kind]=$wpdb->get_results("SELECT * FROM $t ORDER BY id",ARRAY_A);}
    return $result;
}
wp_set_current_user($admin);
$core_before=snapshot_core();
foreach(CAFCC_Academic_DB::entities() as $entity){$table=CAFCC_DB::table($entity);$wpdb->query("DROP TABLE $table");}
update_option('cafcc_db_version','1');
check(true===CAFCC_DB::migrate(),'Schema 1 upgrades to schema 2 with populated academic and progress tables');
check($core_before===snapshot_core(),'Schema 2 migration preserves every schema-1 field, ID and progress row byte-for-byte');
update_option('cafcc_db_version','1');check(true===CAFCC_DB::migrate() && $core_before===snapshot_core(),'Repeated schema upgrade does not remap or overwrite schema-1 data');
check(CAFCC_Academic::listing('editions')['total']===8,'Six current and two separately sourced historical subject editions are prepared');
check(CAFCC_Academic::listing('taxonomy')['total']===280,'Original 180 hierarchy records plus 100 separately sourced draft historical/editorial proposals are retained');
check(v2('GET','catalog')->get_data()['editions']===array(),'Research editions remain private drafts before explicit review');
$fr=CAFCC_Academic::by_key('editions','fr-may2026');$afm=CAFCC_Academic::by_key('editions','afm-may2026');$ibs=CAFCC_Academic::by_key('editions','ibs-resource-listing');
$fr11=CAFCC_Academic::by_key('taxonomy','fr-may2026-m4-ch11');$u4=CAFCC_Academic::by_key('taxonomy','fr-may2026-m4-ch11-u4');
check($fr11['title']==='Chapter 11: Accounting and Reporting of Financial Instruments','FR chapter 11 matches the sourced ICAI label');
check(str_contains($u4['title'],'Derivatives and Embedded Derivatives') && $u4['heading_origin']==='official','FR unit 4 retains the official heading');
check($fr['edition_month']==='2024-11' && $fr['reprint_month']==='2025-08','Edition month is distinguished from reprint month');
check($ibs['edition_month']==='' && str_contains($ibs['date_note'],'not established'),'Unknown IBS publication date remains explicitly unknown');
foreach(array(0=>'Anonymous',$student_a=>'Student',$editor=>'Editor') as $uid=>$role){
    wp_set_current_user($uid);
    foreach(array_keys(CAFCC_Academic::definitions()) as $kind){
        foreach(array('GET','POST','PATCH') as $method){
            $r=v2($method,'admin/'.$kind.('PATCH'===$method?'/1':''),array('title'=>'attack'));
            check(in_array($r->get_status(),array(401,403),true),"$role cannot $method connected $kind");
        }
    }
    foreach(array('import/preview','import/commit','import/rollback/1','review-hierarchy/1') as $path){check(in_array(v2('POST','admin/'.$path,array('source_reviewed'=>true))->get_status(),array(401,403),true),"$role cannot execute $path");}
    check(is_wp_error(CAFCC_Academic::save('families',array('family_key'=>'attack','title'=>'attack'))),"$role cannot bypass connected repository authorization");
}
wp_set_current_user($admin);
check(v2('POST','admin/families',array('family_key'=>'aa','title'=>'attack'),array(),false)->get_status()===403,'Connected writes require a valid REST nonce');
check(v2('POST','admin/review-hierarchy/'.$fr['id'],array('source_reviewed'=>false))->get_status()===400,'Bulk heading approval requires explicit source-review confirmation');
check(v2('POST','admin/review-hierarchy/'.$fr['id'],array('source_reviewed'=>true))->get_status()===200,'Reviewed official FR hierarchy can be published as one edition');
check(v2('POST','admin/review-hierarchy/'.$afm['id'],array('source_reviewed'=>true))->get_status()===200,'Reviewed AFM hierarchy can be published independently');
$filters=array('subject_id'=>$fr['subject_id'],'edition_id'=>$fr['id'],'chapter_id'=>$fr11['id']);
$catalog=v2('GET','catalog',null,$filters)->get_data();
check(count($catalog['chapters'])===17 && count($catalog['units'])===7,'Chapter and unit options come from the selected FR database path');
check($catalog['topics']===array(),'Editorial topics are not automatically approved with official headings');
$t1=CAFCC_Academic::by_key('taxonomy','fr-may2026-m4-ch11-u4-derivative-contracts');
$t2=CAFCC_Academic::by_key('taxonomy','fr-may2026-m4-ch11-u4-embedded-features');
foreach(array($t1,$t2) as $t){record2('taxonomy',array('review_status'=>'verified','publication_status'=>'published'),$t['id']);}
$sub1=CAFCC_Academic::by_key('taxonomy','fr-may2026-m4-ch11-u4-derivative-contracts-s1');
$sub2=CAFCC_Academic::by_key('taxonomy','fr-may2026-m4-ch11-u4-derivative-contracts-s2');
foreach(array($sub1,$sub2) as $sub){record2('taxonomy',array('review_status'=>'verified','publication_status'=>'published'),$sub['id']);}
$full=array_merge($filters,array('unit_id'=>$u4['id'],'topic_id'=>$t1['id']));
$catalog=v2('GET','catalog',null,$full)->get_data();
check(count($catalog['topics'])===2 && count($catalog['subtopics'])===2,'Topic and subtopic options depend on the selected published parent path');
check($catalog['topics'][0]['heading_origin']==='editorial','Student catalogue labels editorial topics separately');
$other_unit=CAFCC_Academic::by_key('taxonomy','fr-may2026-m4-ch11-u3');
check(v2('GET','questions',null,array_merge($full,array('unit_id'=>$other_unit['id'])))->get_status()===400,'Server rejects independent dropdown combinations from different branches');
check(v2('GET','questions',null,array('edition_id'=>$afm['id'],'subject_id'=>$fr['subject_id']))->get_status()===400,'Server rejects a subject/edition mismatch');
check(v2('GET','questions',null,array('chapter_id'=>'1 OR 1=1'))->get_status()===400,'Connected filter IDs reject SQL injection');
$afm_ch=CAFCC_Academic::by_key('taxonomy','afm-may2026-ch1');
check(v2('GET','catalog',null,array('subject_id'=>$afm['subject_id'],'edition_id'=>$afm['id'],'chapter_id'=>$afm_ch['id']))->get_data()['units']===array(),'AFM chapters do not receive invented ICAI unit headings');
check(v2('PATCH','admin/taxonomy/'.$u4['id'],array('parent_id'=>$afm_ch['id']))->get_status()===400,'Taxonomy cannot be moved to another subject or edition');
$verified=array('review_status'=>'verified','publication_status'=>'published');
$doc2=record2('documents',array_merge(array('document_key'=>'TEST-DOC-RTP','edition_id'=>$fr['id'],'title'=>'TEST ONLY RTP source','source_type'=>'rtp','exam_attempt'=>'TEST ONLY attempt A','official_url'=>'https://www.icai.org/test-only-rtp.pdf','issue_period'=>'TEST ONLY issue A'),$verified));
$question2=record2('questions',array_merge(array('stable_key'=>'TEST-QUESTION-001','edition_id'=>$fr['id'],'primary_subject_id'=>$fr['subject_id'],'document_id'=>$doc2['id'],'chapter_node_id'=>$fr11['id'],'title'=>'TEST ONLY connected question','question_number'=>'TEST-Q1','question_type'=>'practical'),$verified));
check(v2('GET','questions',null,array('search'=>'TEST-QUESTION-001'))->get_data()['total']===0,'A connected question needs a published occurrence before appearing');
$oc2=record2('occurrences',array_merge(array('occurrence_key'=>'TEST-OCC-001','question_id'=>$question2['id'],'document_id'=>$doc2['id'],'edition_id'=>$fr['id'],'page_reference'=>'TEST-P1','question_number'=>'TEST-Q1','marks'=>'6','marks_verified'=>1,'question_type'=>'practical'),$verified));
$tag1=record2('tags',array_merge(array('question_id'=>$question2['id'],'node_id'=>$sub1['id']),$verified));
$tag2=record2('tags',array_merge(array('question_id'=>$question2['id'],'node_id'=>$sub2['id']),$verified));
wp_set_current_user($student_a);
$result=v2('GET','questions',null,$full)->get_data();
check($result['total']===1 && $result['items'][0]['id']==$question2['id'],'Deep dependent filter returns the matching question once across multiple tags');
check(v2('GET','questions',null,array_merge($full,array('subtopic_id'=>$sub1['id'])))->get_data()['total']===1,'Subtopic matching reaches its question relationships');
check(v2('GET','questions',null,array_merge($full,array('source_type'=>'mtp')))->get_data()['total']===0,'Source filter excludes nonmatching occurrences');
check(v2('GET','questions',null,array_merge($full,array('search'=>'TEST ONLY connected')))->get_data()['total']===1,'Search matches reviewed question titles');
check($result['items'][0]['occurrences'][0]['marks']==='6.00','Only explicitly verified occurrence marks are returned');
check(call_api('PUT','progress/'.$question2['id'],array('status'=>'completed'))->get_status()===200,'Connected questions use the existing per-student progress IDs');
wp_set_current_user($student_b);
check(v2('GET','questions',null,$full)->get_data()['items'][0]['progress_status']==='not_started','Connected explorer does not expose another student progress');
wp_set_current_user($admin);
check(v2('POST','admin/occurrences',array_merge(array('occurrence_key'=>'TEST-DUP','question_id'=>$question2['id'],'document_id'=>$doc2['id'],'edition_id'=>$fr['id'],'page_reference'=>'TEST-P1','question_number'=>'TEST-Q1'),$verified))->get_status()===409,'The same source appearance cannot be imported under another occurrence key');
check(v2('POST','admin/occurrences',array('occurrence_key'=>'TEST-MARKS','question_id'=>$question2['id'],'document_id'=>$doc2['id'],'edition_id'=>$fr['id'],'question_number'=>'TEST-Q9','marks'=>'10','marks_verified'=>0))->get_status()===400,'Unverified marks cannot be stored as supplied marks');
$doc3=record2('documents',array_merge(array('document_key'=>'TEST-DOC-MTP','edition_id'=>$fr['id'],'title'=>'TEST ONLY MTP source','source_type'=>'mtp','exam_attempt'=>'TEST ONLY attempt B','official_url'=>'https://www.icai.org/test-only-mtp.pdf','issue_period'=>'TEST ONLY issue B','mtp_series'=>'TEST series II'),$verified));
$oc3=record2('occurrences',array_merge(array('occurrence_key'=>'TEST-OCC-002','question_id'=>$question2['id'],'document_id'=>$doc3['id'],'edition_id'=>$fr['id'],'page_reference'=>'TEST-P9','question_number'=>'TEST-MTP-Q3'),$verified));
check(v2('GET','questions',null,array_merge($full,array('source_type'=>'mtp','exam_attempt'=>'TEST ONLY attempt B')))->get_data()['total']===1,'Attempt and source filters find the same matching occurrence');
check(v2('GET','questions',null,array_merge($full,array('source_type'=>'rtp','exam_attempt'=>'TEST ONLY attempt B')))->get_data()['total']===0,'Source and attempt cannot incorrectly match two different appearances');
check(count(v2('GET','questions',null,$full)->get_data()['items'][0]['occurrences'])===2,'One stable question retains separate source-occurrence records');
check(v2('POST','admin/answers',array('answer_key'=>'TEST-BAD-ANSWER','question_id'=>$question2['id'],'answer_mode'=>'official_link','answer_text'=>'Copied text','official_url'=>'https://www.icai.org/test-answer.pdf','source_location'=>'TEST page 1'))->get_status()===400,'Official-link mode rejects reproduced answer text');
check(v2('POST','admin/answers',array('answer_key'=>'TEST-NO-RIGHTS','question_id'=>$question2['id'],'answer_mode'=>'licensed','answer_text'=>'TEST ONLY solution'))->get_status()===400,'Licensed solutions require reproduction-rights evidence');
$answer=record2('answers',array('answer_key'=>'TEST-ANSWER-DRAFT','question_id'=>$question2['id'],'answer_mode'=>'authored','answer_text'=>'TEST ONLY independently authored solution','rights_basis'=>'Synthetic solution authored for automated testing.'));
check(v2('GET','answers/'.$question2['id'],null,array('occurrence_id'=>$oc2['id']))->get_data()['items']===array(),'Draft answer text is never included in student responses');
record2('answers',$verified,$answer['id']);
check(v2('GET','answers/'.$question2['id'],null,array('occurrence_id'=>$oc2['id']))->get_data()['items'][0]['answer_text']==='TEST ONLY independently authored solution','Reviewed independently authored solutions can be shown');
$official_answer=record2('answers',array_merge(array('answer_key'=>'TEST-OFFICIAL-LINK','question_id'=>$question2['id'],'occurrence_id'=>$oc2['id'],'answer_mode'=>'official_link','official_url'=>'https://www.icai.org/test-answer.pdf','source_location'=>'TEST page 4, answer Q1'),$verified));
$items=v2('GET','answers/'.$question2['id'],null,array('occurrence_id'=>$oc2['id']))->get_data()['items'];
check($items[1]['mode']==='official_link' && !isset($items[1]['answer_text']),'Official answer response exposes only a link and location');
check(v2('POST','admin/answers',array('answer_key'=>'TEST-PRIVATE-ANSWER','question_id'=>$question2['id'],'answer_mode'=>'official_link','official_url'=>'https://drive.google.com/private','source_location'=>'private'))->get_status()===400,'Private Google Drive answer references are rejected');
check(v2('POST','admin/tags',array_merge(array('question_id'=>$question2['id'],'node_id'=>$afm_ch['id']),$verified))->get_status()===400,'Ordinary questions cannot acquire cross-subject classifications');
CAFCC_Academic_UI::review_hierarchy($ibs['id']);
$ibs_ch=CAFCC_Academic::by_key('taxonomy','ibs-editorial-cases');record2('taxonomy',$verified,$ibs_ch['id']);
$ibsdoc=record2('documents',array_merge(array('document_key'=>'TEST-IBS-DOC','edition_id'=>$ibs['id'],'title'=>'TEST ONLY IBS case source','source_type'=>'case_study','exam_attempt'=>'TEST ONLY IBS applicability','official_url'=>'https://www.icai.org/test-ibs.pdf'),$verified));
$ibsq=record2('questions',array_merge(array('stable_key'=>'TEST-IBS-Q','edition_id'=>$ibs['id'],'primary_subject_id'=>$ibs['subject_id'],'document_id'=>$ibsdoc['id'],'chapter_node_id'=>$ibs_ch['id'],'title'=>'TEST ONLY multi-subject case','question_number'=>'TEST-CASE-1','question_type'=>'case_study'),$verified));
record2('occurrences',array_merge(array('occurrence_key'=>'TEST-IBS-OCC','question_id'=>$ibsq['id'],'document_id'=>$ibsdoc['id'],'edition_id'=>$ibs['id'],'question_number'=>'TEST-CASE-1'),$verified));
record2('tags',array_merge(array('question_id'=>$ibsq['id'],'node_id'=>$sub1['id']),$verified));record2('tags',array_merge(array('question_id'=>$ibsq['id'],'node_id'=>$afm_ch['id']),$verified));
record2('subject_tags',array_merge(array('question_id'=>$ibsq['id'],'subject_id'=>$afm['subject_id']),$verified));
check(v2('GET','questions',null,array('subject_id'=>$afm['subject_id'],'edition_id'=>$afm['id'],'chapter_id'=>$afm_ch['id']))->get_data()['total']===1,'IBS cases support cross-subject and topic tags with edition-specific paths');
$history=record2('editions',array('edition_key'=>'TEST-FR-HISTORICAL','subject_id'=>$fr['subject_id'],'title'=>'TEST ONLY historical edition','applicability'=>'TEST ONLY; not a real exam edition','source_url'=>'https://www.icai.org/test-history'));
$hc=record2('taxonomy',array('node_key'=>'TEST-HIST-CH','edition_id'=>$history['id'],'subject_id'=>$fr['subject_id'],'node_type'=>'chapter','title'=>'TEST ONLY historical chapter','heading_origin'=>'editorial'));
$ht=record2('taxonomy',array('node_key'=>'TEST-HIST-TOPIC','edition_id'=>$history['id'],'subject_id'=>$fr['subject_id'],'parent_id'=>$hc['id'],'node_type'=>'topic','title'=>'TEST ONLY historical topic','heading_origin'=>'editorial'));
record2('edition_mappings',array('from_node_id'=>$ht['id'],'to_node_id'=>$t1['id'],'relationship'=>'equivalent'));
check(CAFCC_Repository::get('questions',$question2['id'])['id']===$question2['id'],'Historical mappings do not remap question or progress IDs');
check(v2('POST','admin/edition_mappings',array('from_node_id'=>$ht['id'],'to_node_id'=>$afm_ch['id'],'relationship'=>'equivalent'))->get_status()===400,'Historical mappings cannot cross subjects');
$csv=csv2('hierarchy',array(array('edition_key'=>'fr-may2026','subject_code'=>'FR','node_key'=>'TEST-CSV-SUB','parent_key'=>$t1['node_key'],'node_type'=>'subtopic','title'=>'TEST ONLY imported editorial tag','position'=>'50','heading_origin'=>'editorial')));
$tax_before=CAFCC_Academic::listing('taxonomy')['total'];$core_snap=snapshot_core();
$preview=v2('POST','admin/import/preview',array('type'=>'hierarchy','csv'=>$csv));check($preview->get_status()===200,'Hierarchy CSV preview validates related stable keys');$plan=$preview->get_data();
check(CAFCC_Academic::listing('taxonomy')['total']===$tax_before && $core_snap===snapshot_core(),'CSV preview retains no academic rows or progress changes');
$admin2=wp_create_user('test_admin_second','cafcc-disposable-only','admin2@example.invalid');(new WP_User($admin2))->set_role('administrator');wp_set_current_user($admin2);
check(v2('POST','admin/import/commit',array('token'=>$plan['token']))->get_status()===403,'Preview tokens are bound to their administrator');wp_set_current_user($admin);
$batch=v2('POST','admin/import/commit',array('token'=>$plan['token']))->get_data();
check(isset($batch['batch_id']) && CAFCC_Academic::listing('taxonomy')['total']===$tax_before+1,'Validated hierarchy batch commits once');
$imported=CAFCC_Academic::by_key('taxonomy','TEST-CSV-SUB');check($imported['review_status']==='needs_review' && $imported['publication_status']==='draft','Research CSV records are always Draft/Needs Review');
check(v2('POST','admin/import/commit',array('token'=>$plan['token']))->get_data()['already_committed']===true,'Commit retries cannot duplicate an import batch');
check(v2('POST','admin/import/preview',array('type'=>'hierarchy','csv'=>$csv))->get_status()===409,'CSV duplicate detection checks existing stable keys');
check(v2('POST','admin/import/preview',array('type'=>'hierarchy','csv'=>"bad,headers\na,b\n"))->get_status()===400,'CSV headers are strictly validated');
check(v2('POST','admin/import/preview',array('type'=>'hierarchy','csv'=>csv2('hierarchy',array(array('edition_key'=>'UNKNOWN','subject_code'=>'FR','node_key'=>'TEST-BAD','node_type'=>'chapter','title'=>'TEST')))))->get_status()===400,'CSV cannot reference unknown editions');
$bad_doc=csv2('documents',array(array('document_key'=>'TEST-CSV-PRIVATE','edition_key'=>'fr-may2026','title'=>'TEST','source_type'=>'exam','exam_attempt'=>'TEST','official_url'=>'https://drive.google.com/private')));
check(v2('POST','admin/import/preview',array('type'=>'documents','csv'=>$bad_doc))->get_status()===400,'CSV validation rejects private source URLs');
$docs_csv=csv2('documents',array(array('document_key'=>'TEST-CSV-DOC','edition_key'=>'fr-may2026','title'=>'TEST ONLY CSV source','source_type'=>'exam','exam_attempt'=>'TEST ONLY CSV attempt','official_url'=>'https://www.icai.org/test-csv-source.pdf')));
$dp=v2('POST','admin/import/preview',array('type'=>'documents','csv'=>$docs_csv))->get_data();$dbatch=v2('POST','admin/import/commit',array('token'=>$dp['token']))->get_data();$cdoc=CAFCC_Academic::by_key('documents','TEST-CSV-DOC');
check($cdoc['review_status']==='needs_review' && $cdoc['verification_status']==='unverified','Source-document CSV cannot approve its own academic data');record2('documents',$verified,$cdoc['id']);
$occ_csv=csv2('occurrences',array(array('occurrence_key'=>'TEST-CSV-OCC','question_key'=>'TEST-CSV-Q','question_title'=>'TEST ONLY CSV question','document_key'=>'TEST-CSV-DOC','edition_key'=>'fr-may2026','chapter_key'=>$fr11['node_key'],'question_number'=>'TEST-CSV-Q1','question_type'=>'practical')));
$op=v2('POST','admin/import/preview',array('type'=>'occurrences','csv'=>$occ_csv))->get_data();check(isset($op['token']),'Occurrence CSV validates creation of a stable question and its appearance');check(CAFCC_Academic::by_key('questions','TEST-CSV-Q')===null,'Occurrence preview rolls back nested core-question creation and audit writes');
$obatch=v2('POST','admin/import/commit',array('token'=>$op['token']))->get_data();$cq=CAFCC_Academic::by_key('questions','TEST-CSV-Q');$co=CAFCC_Academic::by_key('occurrences','TEST-CSV-OCC');
check($cq['publication_status']==='draft' && $co['publication_status']==='draft','Imported questions and appearances remain unpublished');
record2('questions',$verified,$cq['id']);record2('occurrences',$verified,$co['id']);
$tag_csv=csv2('question_topics',array(array('question_key'=>'TEST-CSV-Q','node_key'=>$sub1['node_key'])));$tp=v2('POST','admin/import/preview',array('type'=>'question_topics','csv'=>$tag_csv))->get_data();$tbatch=v2('POST','admin/import/commit',array('token'=>$tp['token']))->get_data();
check(isset($tbatch['batch_id']),'Question-topic CSV imports many-to-many classifications');
$ans_csv=csv2('answers',array(array('answer_key'=>'TEST-CSV-ANSWER','question_key'=>'TEST-CSV-Q','occurrence_key'=>'TEST-CSV-OCC','answer_mode'=>'official_link','official_url'=>'https://www.icai.org/test-csv-answer.pdf','source_location'=>'TEST ONLY answer page 2')));
$ap=v2('POST','admin/import/preview',array('type'=>'answers','csv'=>$ans_csv))->get_data();$abatch=v2('POST','admin/import/commit',array('token'=>$ap['token']))->get_data();$ca=CAFCC_Academic::by_key('answers','TEST-CSV-ANSWER');
check($ca['publication_status']==='draft','Answer-reference CSV remains private pending review');record2('answers',$verified,$ca['id']);
check(count(v2('GET','answers/'.$cq['id'])->get_data()['items'])===1,'Reviewed imported answer reference can be linked safely');
wp_set_current_user($student_a);call_api('PUT','progress/'.$cq['id'],array('status'=>'needs_revision'));wp_set_current_user($admin);
$p=CAFCC_DB::table('progress');$saved_progress=$wpdb->get_results($wpdb->prepare("SELECT * FROM $p WHERE question_id=%d",$cq['id']),ARRAY_A);
check(v2('POST','admin/import/rollback/'.$abatch['batch_id'],array('withdraw'=>true))->get_status()===200 && v2('GET','answers/'.$cq['id'])->get_data()['items']===array(),'Withdrawing an answer batch hides approved answers without deleting records');
check(v2('POST','admin/import/rollback/'.$obatch['batch_id'],array('withdraw'=>true))->get_status()===200,'An occurrence/question batch can be withdrawn safely');
check(v2('GET','questions',null,array('search'=>'TEST-CSV-Q'))->get_data()['total']===0,'Withdrawn imported questions disappear from the connected explorer');
check(!is_wp_error(CAFCC_Academic::get('questions',$cq['id'])) && $wpdb->get_results($wpdb->prepare("SELECT * FROM $p WHERE question_id=%d",$cq['id']),ARRAY_A)===$saved_progress,'Batch withdrawal retains question rows and the exact student-progress data');
check(v2('PATCH','admin/questions/'.$cq['id'],$verified)->get_status()===409,'Withdrawn batch records cannot be accidentally republished');
wp_set_current_user($student_a);
check(call_api('PUT','progress/'.$cq['id'],array('status'=>'completed'))->get_status()===404,'Withdrawn batches cannot receive progress through the original v1 API');
$legacy_visible=call_api('GET','questions')->get_data()['items'];check(!in_array($cq['id'],array_column($legacy_visible,'id')),'Withdrawn question batches cannot leak through the original explorer');
check(v2('PUT','progress/'.$question2['id'],array('status'=>'completed','user_id'=>$student_b))->get_status()===404,'No alternate connected endpoint accepts forged progress owners');
wp_set_current_user($admin);
$old_q_before=CAFCC_Repository::get('questions',$q['id']);$old_d_before=CAFCC_Repository::get('documents',$document['id']);
$linked_doc=record2('documents',array('document_key'=>'TEST-LINKED-V1-DOC','document_id'=>$document['id'],'edition_id'=>$fr['id'],'title'=>$old_d_before['title'],'source_type'=>$old_d_before['source_type'],'exam_attempt'=>$old_d_before['exam_attempt'],'official_url'=>$old_d_before['official_url']));
check(CAFCC_Repository::get('documents',$document['id'])===$old_d_before,'Explicitly connecting a v1 source adds only metadata and preserves its old row');
record2('documents',$verified,$linked_doc['id']);
$linked_q=record2('questions',array('stable_key'=>'TEST-LINKED-V1-Q','question_id'=>$q['id'],'edition_id'=>$fr['id'],'primary_subject_id'=>$fr['subject_id'],'document_id'=>$document['id'],'title'=>$old_q_before['title'],'question_number'=>$old_q_before['question_number']));
check(CAFCC_Repository::get('questions',$q['id'])===$old_q_before,'Explicitly classifying a v1 question preserves its ID, source, topic and publication fields');
check($linked_q['id']===$q['id'],'Connected metadata uses the existing question/progress identity');
$cache_response=apply_filters('rest_post_dispatch',v2('GET','catalog'),$server,new WP_REST_Request('GET','/cafcc/v2/catalog'));
check(str_contains($cache_response->get_headers()['Cache-Control'],'no-store'),'Connected REST responses are private and no-store');
check(http_api('GET','questions',null,0,true,'v2')['status']===401,'Actual HTTP connected explorer rejects anonymous visitors');
check(http_api('GET','questions',null,$student_a,false,'v2')['status']===401,'Actual HTTP connected explorer requires cookie and nonce together');
check(http_api('GET','questions',null,$student_a,'invalid','v2')['status']===403,'Actual HTTP connected explorer rejects an invalid nonce');
check(http_api('GET','questions',null,$student_a,true,'v2')['status']===200,'Actual HTTP connected explorer authenticates a student securely');
check(http_api('POST','admin/taxonomy',array('title'=>'attack'),$student_a,true,'v2')['status']===403,'Actual HTTP student cannot alter connected academic classifications');
$secret_answer=record2('answers',array('answer_key'=>'TEST-SECRET-DRAFT','question_id'=>$question2['id'],'answer_mode'=>'authored','answer_text'=>'TEST ONLY PRIVATE DRAFT ANSWER','rights_basis'=>'TEST ONLY authorship evidence'));
$http_answers=http_api('GET','answers/'.$question2['id'].'&occurrence_id='.$oc2['id'],null,$student_a,true,'v2');
check($http_answers['status']===200 && !str_contains(wp_json_encode($http_answers['body']),'PRIVATE DRAFT ANSWER'),'Actual HTTP never exposes unpublished answer text');
$race_rows=array(array('edition_key'=>'fr-may2026','subject_code'=>'FR','node_key'=>'TEST-RACE-FIRST','parent_key'=>$t1['node_key'],'node_type'=>'subtopic','title'=>'TEST ONLY first race row','heading_origin'=>'editorial'),array('edition_key'=>'fr-may2026','subject_code'=>'FR','node_key'=>'TEST-RACE-SECOND','parent_key'=>$t1['node_key'],'node_type'=>'subtopic','title'=>'TEST ONLY second race row','heading_origin'=>'editorial'));
$race_preview=v2('POST','admin/import/preview',array('type'=>'hierarchy','csv'=>csv2('hierarchy',$race_rows)))->get_data();
record2('taxonomy',array('node_key'=>'TEST-RACE-SECOND','edition_id'=>$fr['id'],'subject_id'=>$fr['subject_id'],'parent_id'=>$t1['id'],'node_type'=>'subtopic','title'=>'TEST ONLY concurrent reviewed entry','heading_origin'=>'editorial'));
check(v2('POST','admin/import/commit',array('token'=>$race_preview['token']))->get_status()===409,'Commit revalidates duplicate keys that appeared after preview');
check(null===CAFCC_Academic::by_key('taxonomy','TEST-RACE-FIRST'),'A late import failure rolls back all earlier rows in that batch');
$family=record2('families',array('family_key'=>'TEST-FAMILY','title'=>'TEST ONLY question family'));
record2('questions',array('family_id'=>$family['id']),$question2['id']);
$comparison=record2('comparisons',array('left_question_id'=>min($question2['id'],$ibsq['id']),'right_question_id'=>max($question2['id'],$ibsq['id']),'relationship'=>'possible_repeat','notes'=>'TEST ONLY human-reviewed comparison placeholder; no percentage assigned.'));
check(isset($family['id']) && isset($comparison['id']),'Family and comparison entities support future analysis without fabricated repeat metrics');
check(v2('POST','admin/comparisons',array('left_question_id'=>$question2['id'],'right_question_id'=>$question2['id'],'relationship'=>'possible_repeat'))->get_status()===400,'A question cannot be compared with itself');
check(call_api('DELETE','admin/documents/'.$doc2['id'])->get_status()===409,'Original delete endpoint protects sources used by connected occurrences');
check($wpdb->get_var($wpdb->prepare("SELECT status FROM $p WHERE user_id=%d AND question_id=%d",$student_a,$question2['id']))==='completed','Family/classification edits preserve the existing student completion');
check(call_api('PATCH','admin/documents/'.$doc2['id'],array('official_url'=>'https://www.icai.org/test-changed-location.pdf'))->get_status()===409,'The old master endpoint cannot reassign a connected source URL');
check(call_api('PATCH','admin/questions/'.$question2['id'],array('chapter_id'=>$chapter_b['id']))->get_status()===409,'The old endpoint cannot bypass connected question relationship validation');
check(CAFCC_Academic::get('documents',$doc2['id'])['official_url']==='https://www.icai.org/test-only-rtp.pdf','Rejected old-endpoint changes preserve the official source identity');
