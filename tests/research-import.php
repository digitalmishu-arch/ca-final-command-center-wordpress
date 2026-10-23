<?php
/** Exercises pipeline-shaped metadata through the unchanged real V0.2 importer. */
wp_set_current_user($admin);
$research_batches=array();
$research_csv=array(
    'documents'=>array(array('document_key'=>'TEST-RESEARCH-DOC','edition_key'=>'fr-may2026','title'=>'TEST ONLY research source','source_type'=>'rtp','exam_attempt'=>'TEST ONLY','official_url'=>'https://www.icai.org/test-only-research.pdf')),
    'occurrences'=>array(array('occurrence_key'=>'TEST-RESEARCH-OCC','question_key'=>'TEST-RESEARCH-Q','question_title'=>'TEST ONLY metadata reference','document_key'=>'TEST-RESEARCH-DOC','edition_key'=>'fr-may2026','chapter_key'=>'fr-may2026-m4-ch11','page_reference'=>'PDF p.1','question_number'=>'1','marks_verified'=>'0','question_type'=>'unknown')),
    'question_topics'=>array(array('question_key'=>'TEST-RESEARCH-Q','node_key'=>'fr-may2026-m4-ch11-u4-derivative-contracts'),array('question_key'=>'TEST-RESEARCH-Q','node_key'=>'fr-may2026-m4-ch11-u4-embedded-features')),
    'answers'=>array(array('answer_key'=>'TEST-RESEARCH-A','question_key'=>'TEST-RESEARCH-Q','occurrence_key'=>'TEST-RESEARCH-OCC','answer_mode'=>'official_link','official_url'=>'https://www.icai.org/test-only-research.pdf','source_location'=>'PDF p.2; Q1'))
);
$research_progress_before=$wpdb->get_results('SELECT * FROM '.CAFCC_DB::table('progress').' ORDER BY id',ARRAY_A);
foreach($research_csv as $kind=>$rows){
    $preview=CAFCC_Import::preview($kind,csv2($kind,$rows));
    check(!is_wp_error($preview),'Research '.$kind.' metadata previews in unchanged V0.2 importer');
    if(is_wp_error($preview)){throw new RuntimeException($preview->get_error_message());}
    $committed=CAFCC_Import::commit($preview['token']);
    check(!is_wp_error($committed),'Research '.$kind.' metadata commits to disposable database only');
    $research_batches[]=$committed['batch_id'];
}
$research_question=CAFCC_Academic::by_key('questions','TEST-RESEARCH-Q');
check($research_question['verification_status']==='unverified' && $research_question['publication_status']==='draft','Research question remains Draft/Needs Review');
check(is_wp_error(CAFCC_Import::preview('occurrences',csv2('occurrences',$research_csv['occurrences']))),'Research duplicate occurrence is rejected on retry');
wp_set_current_user($student_a);
check(v2('GET','questions',null,array('search'=>'TEST-RESEARCH-Q'))->get_data()['total']===0,'Student cannot see unpublished research');
check(is_wp_error(CAFCC_Import::preview('documents',csv2('documents',$research_csv['documents']))),'Student cannot import research directly');
wp_set_current_user($admin);
foreach(array_reverse($research_batches) as $batch){check(!is_wp_error(CAFCC_Import::rollback($batch)),'Research batch can be withdrawn without deletion');}
check($wpdb->get_results('SELECT * FROM '.CAFCC_DB::table('progress').' ORDER BY id',ARRAY_A)===$research_progress_before,'Research preview, import and withdrawal preserve every student progress field');
