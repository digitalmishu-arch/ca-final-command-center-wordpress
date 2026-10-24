<?php
/** Independently authored synthetic content; never seed real installations. */
function v3($method,$path,$body=null,$nonce=true){
    global $server;$parts=explode('?',$path,2);$r=new WP_REST_Request($method,'/cafcc/v3/'.$parts[0]);
    if(isset($parts[1])){parse_str($parts[1],$query);$r->set_query_params($query);}
    if($nonce){$r->set_header('X-WP-Nonce',wp_create_nonce('wp_rest'));}
    if(null!==$body){$r->set_header('Content-Type','application/json');$r->set_body(wp_json_encode($body));}
    return $server->dispatch($r);
}
function practice_save_test($data,$id=0){
    $r=v3($id?'PATCH':'POST','admin/practice'.($id?'/'.$id:''),$data);
    if(200!==$r->get_status()){throw new RuntimeException('Practice save failed: '.wp_json_encode($r->get_data()));}
    baseline_review_fixture((int)$r->get_data()['question_id']);return $r->get_data();
}
function practice_approve_test($row){
    $r=v3('POST','admin/practice/'.$row['id'].'/approve',array('expected_revision'=>$row['revision'],'rights_confirmed'=>true));
    if(200!==$r->get_status()){throw new RuntimeException('Practice approval failed: '.wp_json_encode($r->get_data()));}
    baseline_review_fixture((int)$r->get_data()['question_id']);return $r->get_data();
}
wp_set_current_user($admin);$pub=array('review_status'=>'verified','publication_status'=>'published');
$v3doc=record2('documents',array_merge(array('document_key'=>'TEST-V03-DOC','edition_id'=>$fr['id'],'title'=>'TEST ONLY original practice fixture — not an ICAI question','source_type'=>'other','exam_attempt'=>'TEST ONLY authored demo, no exam attempt','official_url'=>'https://www.icai.org/test-only-v03.pdf'),$pub));
$v3q=record2('questions',array_merge(array('stable_key'=>'TEST-V03-Q','edition_id'=>$fr['id'],'primary_subject_id'=>$fr['subject_id'],'document_id'=>$v3doc['id'],'chapter_node_id'=>$fr11['id'],'title'=>'TEST ONLY independently authored example','question_number'=>'TEST-P3','question_type'=>'mcq'),$pub));
record2('occurrences',array_merge(array('occurrence_key'=>'TEST-V03-OCC','question_id'=>$v3q['id'],'document_id'=>$v3doc['id'],'edition_id'=>$fr['id'],'question_number'=>'TEST-P3','page_reference'=>'TEST authored fixture, no source PDF','question_type'=>'mcq'),$pub));
$question_body='<h3>TEST ORIGINAL PRACTICE</h3><p>TEST-QUESTION-SEARCH-NEEDLE. Calculate the balance after 20 units plus 5 units.</p><table><caption>TEST original inputs</caption><thead><tr><th scope="col">Opening</th><th scope="col">Added</th></tr></thead><tbody><tr><td>20</td><td>5</td></tr></tbody></table><math display="block"><mrow><mn>20</mn><mo>+</mo><mn>5</mn></mrow></math><script>alert(1)</script><img src=x onerror=alert(1)>';
$v3data=array('question_id'=>$v3q['id'],'content_kind'=>'question','rights_type'=>'original','rights_basis'=>'TEST ONLY independently authored by the project for automated tests; no copied ICAI text.','author_name'=>'TEST Author','body_html'=>$question_body,'mcq_options'=>array(array('key'=>'A','text'=>'24 units'),array('key'=>'B','text'=>'25 units')));
foreach(array(0=>'Anonymous',$student_a=>'Student',$editor=>'Editor') as $uid=>$role){
    wp_set_current_user($uid);
    foreach(array('GET','POST') as $method){check(in_array(v3($method,'admin/practice',$v3data)->get_status(),array(401,403),true),"$role cannot $method rights-controlled master content");}
    check(is_wp_error(CAFCC_Practice::save($v3data)),"$role cannot bypass content repository permissions");
    check(in_array(v3('POST','admin/practice/1/approve',array('expected_revision'=>1,'rights_confirmed'=>true))->get_status(),array(401,403),true),"$role cannot approve publication rights");
}
wp_set_current_user($admin);
check(v3('POST','admin/practice',$v3data,false)->get_status()===403,'Practice master writes require a REST nonce');
check(v3('POST','admin/practice',array_merge($v3data,array('rights_type'=>'reference_only')))->get_status()===400,'Reference-only sources cannot store copied question text in WordPress');
check(v3('POST','admin/practice',array_merge($v3data,array('body_html'=>'<p>https://drive&#46;google&#46;com/private</p>')))->get_status()===400,'Encoded private Drive links cannot enter practice content');
check(v3('POST','admin/practice',array_merge($v3data,array('mcq_options'=>array(array('key'=>'A','text'=>'TEST','correct'=>true)))))->get_status()===400,'Question options reject answer-key fields');
$v3content=practice_save_test($v3data);
check(v3('POST','admin/practice',array_merge($v3data,array('publication_status'=>'published')))->get_status()===400,'Content save cannot bypass the separate rights approval step');
check($v3content['review_status']==='needs_review' && $v3content['publication_status']==='draft','New original content always begins as Draft/Needs Review');
check(!str_contains($v3content['body_html'],'<script') && !str_contains($v3content['body_html'],'onerror') && str_contains($v3content['body_html'],'<math'),'Rich content sanitisation retains formulas and tables while removing executable markup');
wp_set_current_user($student_a);
check(v3('GET','admin/practice/'.$v3content['id'].'/history')->get_status()===403,'Student cannot read private content revision history');
check(null===CAFCC_Practice::public_content($v3q['id'],'question'),'Unapproved question text is unavailable to a student');
check(v2('GET','questions',null,array('search'=>'TEST-QUESTION-SEARCH-NEEDLE'))->get_data()['total']===0,'Search cannot reveal draft full text');
wp_set_current_user($admin);
check(v3('GET','admin/practice/'.$v3content['id'].'/history')->get_status()===200,'Administrator can inspect retained revision evidence');
check(v3('POST','admin/practice/'.$v3content['id'].'/approve',array('expected_revision'=>1,'rights_confirmed'=>false))->get_status()===400,'Publication requires explicit rights review');
check(v3('POST','admin/practice/'.$v3content['id'].'/approve',array('expected_revision'=>99,'rights_confirmed'=>true))->get_status()===409,'Stale revision cannot be approved');
$v3content=practice_approve_test($v3content);
$answer=practice_save_test(array('question_id'=>$v3q['id'],'content_kind'=>'answer','rights_type'=>'original','rights_basis'=>'TEST ONLY independently authored solution by project.','author_name'=>'TEST Solution Author','source_location'=>'TEST original solution, step 1','body_html'=>'<h3>TEST-ANSWER-PRIVATE-NEEDLE</h3><p>20 + 5 = 25 units.</p><table><tr><th scope="col">Result</th><td>25</td></tr></table>'));
$answer=practice_approve_test($answer);
wp_set_current_user($student_a);
$visible=v2('GET','questions',null,array('search'=>'TEST-QUESTION-SEARCH-NEEDLE'))->get_data();
check($visible['total']===1 && str_contains($visible['items'][0]['practice_content']['body_html'],'TEST-QUESTION-SEARCH-NEEDLE'),'Reviewed permitted full text is selectable/searchable question content');
check(!str_contains(wp_json_encode($visible),'TEST-ANSWER-PRIVATE-NEEDLE'),'Initial question response never includes solution text');
check(v2('GET','questions',null,array('search'=>'TEST-ANSWER-PRIVATE-NEEDLE'))->get_data()['total']===0,'Question search never indexes answer-only text');
$solution=v2('GET','answers/'.$v3q['id'])->get_data();check(str_contains(wp_json_encode($solution),'TEST-ANSWER-PRIVATE-NEEDLE'),'Explicit answer request receives reviewed formatted solution with credit');
$notebook=v3('PUT','notebook/'.$v3q['id'],array('note_text'=>'TEST private student A note','bookmarked'=>true));check($notebook->get_status()===200,'Student A saves a private note and bookmark');
check(v2('GET','questions',null,array('search'=>'TEST-V03-Q','bookmarked'=>'1'))->get_data()['total']===1,'Student A bookmark filter uses only A records');
check(v3('PUT','notebook/'.$v3q['id'],array('user_id'=>$student_b,'note_text'=>'attack'))->get_status()===400,'A student cannot select another notebook owner');
check(v3('GET','notebook/'.$v3q['id'].'?user_id='.$student_b)->get_status()!==200,'A direct URL cannot select another notebook owner');
check(call_api('PUT','progress/'.$v3q['id'],array('status'=>'completed'))->get_status()===200,'Student A practice status remains supported');
wp_set_current_user($student_b);
$b=v3('GET','notebook/'.$v3q['id'])->get_data();check($b['note_text']==='' && !$b['bookmarked'],'Student B does not receive A notes or bookmark');
check(v2('GET','questions',null,array('search'=>'TEST-V03-Q','bookmarked'=>'1'))->get_data()['total']===0,'Student B cannot use A bookmarks to filter questions');
check(v3('PUT','notebook/'.$v3q['id'],array('note_text'=>'TEST private student B note'))->get_status()===200,'Student B saves separate notes');
check(call_api('PUT','progress/'.$v3q['id'],array('status'=>'attempted'))->get_status()===200,'Student B saves a separate progress status');
wp_set_current_user($student_a);check(v3('GET','notebook/'.$v3q['id'])->get_data()['note_text']==='TEST private student A note','B changes preserve A private note');
$a_questions=v2('GET','questions',null,array('search'=>'TEST-V03-Q'))->get_data();check($a_questions['items'][0]['progress_status']==='completed','A completion remains independent from B attempt');
check(!str_contains(wp_json_encode($a_questions),'TEST private student B note'),'Question cards never leak another student private note');
check(v2('GET','questions',null,array('search'=>'TEST private student A note'))->get_data()['total']===0,'Private notes are excluded from academic text search');
$http=http_api('GET','notebook/'.$v3q['id'],null,$student_b,true,'v3');check($http['status']===200 && $http['body']['note_text']==='TEST private student B note','Actual HTTP notebook access enforces B cookie identity');
check(in_array(http_api('PUT','notebook/'.$v3q['id'],array('bookmarked'=>true),$student_b,false,'v3')['status'],array(401,403),true),'Actual HTTP notebook writes reject missing nonce');
wp_set_current_user($admin);
$edited=practice_save_test(array('body_html'=>'<p>TEST revised question text</p>','expected_revision'=>$v3content['revision']),$v3content['id']);
check($edited['revision']==2 && $edited['publication_status']==='draft' && !$edited['approved_by'],'Editing reviewed content revokes its approval and increments revision');
check(v3('PATCH','admin/practice/'.$edited['id'],array('body_html'=>'attack','expected_revision'=>1))->get_status()===409,'Stale content edit is rejected');
$revisions=CAFCC_Practice::table('revisions');check((int)$wpdb->get_var($wpdb->prepare("SELECT COUNT(*) FROM $revisions WHERE content_id=%d AND event_type='before_edit'",$edited['id']))===1,'Previously approved content snapshot remains in revision history');
wp_set_current_user($student_a);check(null===CAFCC_Practice::public_content($v3q['id'],'question'),'Edited content is immediately withheld pending new rights review');
check(v3('GET','notebook/'.$v3q['id'])->get_data()['note_text']==='TEST private student A note','Content withdrawal preserves student notes');
wp_set_current_user($admin);$edited=practice_approve_test($edited);
$licensed=practice_save_test(array('rights_type'=>'licensed','rights_basis'=>'TEST licence: web display permitted until specified date.','rights_expires'=>gmdate('Y-m-d',time()-86400),'expected_revision'=>$edited['revision']),$edited['id']);
check(v3('POST','admin/practice/'.$licensed['id'].'/approve',array('expected_revision'=>$licensed['revision'],'rights_confirmed'=>true))->get_status()===400,'Expired licensed content cannot be approved');
$licensed=practice_save_test(array('rights_expires'=>'','expected_revision'=>$licensed['revision']),$licensed['id']);$licensed=practice_approve_test($licensed);
check(CAFCC_Practice::public_content($v3q['id'],'question')['rights_label']==='Licensed content','Current licensed content supports reviewed display');
$content_table=CAFCC_Practice::table('content');$wpdb->update($content_table,array('rights_expires'=>gmdate('Y-m-d',time()-86400)),array('id'=>$licensed['id']));
check(null===CAFCC_Practice::public_content($v3q['id'],'question'),'Rights expiry hides previously approved content at read time');
record2('questions',array('publication_status'=>'draft'),$v3q['id']);
wp_set_current_user($student_a);check(v2('GET','answers/'.$v3q['id'])->get_status()===404,'Unpublished academic question hides all answers');
check(v3('GET','notebook/'.$v3q['id'])->get_status()===404,'Unpublished question cannot be used to access student notebook routes');
wp_set_current_user($admin);
$snapshot=array();foreach(array('content','revisions','notebook') as $kind){$t=CAFCC_Practice::table($kind);$snapshot[$kind]=$wpdb->get_results("SELECT * FROM $t ORDER BY id",ARRAY_A);}
// An original Version 0.1 question with new practice content is also protected.
$legacy_practice_q=create_record('questions',array_merge($qdata,array('question_number'=>'TEST-V03-V1','title'=>'TEST ONLY legacy reference with permitted-content metadata')));
$legacy_practice=practice_save_test(array('question_id'=>$legacy_practice_q['id'],'content_kind'=>'question','rights_type'=>'reference_only','body_html'=>''));
check(call_api('DELETE','admin/questions/'.$legacy_practice_q['id'])->get_status()===409,'Old delete route protects Version 0.1 references with new practice content');
$snapshot=array();foreach(array('content','revisions','notebook') as $kind){$t=CAFCC_Practice::table($kind);$snapshot[$kind]=$wpdb->get_results("SELECT * FROM $t ORDER BY id",ARRAY_A);}
$old_core=snapshot_core();$academic_snapshot=array();foreach(CAFCC_Academic_DB::entities() as $kind){$t=CAFCC_DB::table($kind);$academic_snapshot[$kind]=$wpdb->get_results("SELECT * FROM $t ORDER BY id",ARRAY_A);}
$accounts=$wpdb->get_results("SELECT * FROM $wpdb->users ORDER BY ID",ARRAY_A);
update_option('cafcc_db_version','2');check(true===CAFCC_DB::migrate(),'Schema 2 upgrades additively to schema 3');
check($old_core===snapshot_core(),'Upgrade preserves every original academic/progress field and ID');
foreach($academic_snapshot as $kind=>$expected){$t=CAFCC_DB::table($kind);check($expected===$wpdb->get_results("SELECT * FROM $t ORDER BY id",ARRAY_A),'Upgrade preserves connected '.$kind.' records');}
foreach($snapshot as $kind=>$expected){$t=CAFCC_Practice::table($kind);check($expected===$wpdb->get_results("SELECT * FROM $t ORDER BY id",ARRAY_A),'Upgrade retry preserves practice '.$kind.' rows');}
check($accounts===$wpdb->get_results("SELECT * FROM $wpdb->users ORDER BY ID",ARRAY_A),'Migration preserves every student/admin account field');
deactivate_plugins($plugin);activate_plugin($plugin);
foreach($snapshot as $kind=>$expected){$t=CAFCC_Practice::table($kind);check($expected===$wpdb->get_results("SELECT * FROM $t ORDER BY id",ARRAY_A),'Deactivation/reactivation retains practice '.$kind);}
update_option('cafcc_db_version','999');check(v3('GET','admin/practice')->get_status()===503,'New API refuses incompatible database versions');update_option('cafcc_db_version',CAFCC_DB::VERSION);
