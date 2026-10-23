<?php
/** Optional PRIVATE local run: validate actual metadata in disposable WordPress.
 * No PDF text is read, no source/title is printed, no publishing is performed.
 */
$private_package=getenv('CAFCC_RESEARCH_PACKAGE');
if($private_package){
    $private_root=realpath('/repo/work');$private_path=realpath($private_package);
    if(!$private_path || !str_starts_with($private_path,$private_root.'/')){throw new RuntimeException('Research package must be under private /repo/work.');}
    wp_set_current_user($admin);
    $private_progress=$wpdb->get_results('SELECT * FROM '.CAFCC_DB::table('progress').' ORDER BY id',ARRAY_A);
    $private_questions=$wpdb->get_results('SELECT * FROM '.CAFCC_DB::table('questions').' ORDER BY id',ARRAY_A);
    $private_report=json_decode(file_get_contents($private_path.'/report.json'),true,512,JSON_THROW_ON_ERROR);
    $private_editions=json_decode(file_get_contents($private_path.'/edition-setup.json'),true,512,JSON_THROW_ON_ERROR);
    foreach($private_editions as $edition){
        $subjects=CAFCC_DB::table('subjects');
        $edition['subject_id']=(int)$wpdb->get_var($wpdb->prepare("SELECT id FROM $subjects WHERE code=%s",$edition['subject_code']));
        unset($edition['subject_code']);$edition['review_status']='needs_review';$edition['publication_status']='draft';
        $saved=CAFCC_Academic::save('editions',$edition);
        check(!is_wp_error($saved),'Historical research context can be prepared as a separate draft edition');
        if(is_wp_error($saved)){throw new RuntimeException($saved->get_error_message());}
    }
    $private_batches=array();$private_total=0;
    foreach($private_report['csv_files'] as $file){
        if(!$file['importable']){continue;}
        if(basename($file['file'])!==$file['file']){throw new RuntimeException('Invalid package filename.');}
        $csv=file_get_contents($private_path.'/'.$file['file']);
        check(hash('sha256',$csv)===$file['sha256'],'Private research CSV checksum matches validated run');
        $preview=CAFCC_Import::preview($file['type'],$csv);
        check(!is_wp_error($preview),'Private research CSV passes unchanged V0.2 preview');
        if(is_wp_error($preview)){throw new RuntimeException($preview->get_error_message());}
        check($preview['row_count']===$file['rows'],'Private research preview has the expected row count');
        $result=CAFCC_Import::commit($preview['token']);
        check(!is_wp_error($result),'Private research CSV imports in disposable database only');
        if(is_wp_error($result)){throw new RuntimeException($result->get_error_message());}
        $private_batches[]=$result['batch_id'];$private_total+=$file['rows'];
    }
    $question_table=CAFCC_DB::table('questions');$document_table=CAFCC_DB::table('documents');
    foreach($private_questions as $q){check($q===$wpdb->get_row($wpdb->prepare("SELECT * FROM $question_table WHERE id=%d",$q['id']),ARRAY_A),'Original question record unchanged by research import');}
    $occurrence_table=CAFCC_DB::table('occurrences');$answer_table=CAFCC_DB::table('answers');
    foreach(array($occurrence_table,$answer_table) as $table){
        $ids=implode(',',array_map('intval',$private_batches));
        check((int)$wpdb->get_var("SELECT COUNT(*) FROM $table WHERE batch_id IN ($ids) AND (review_status<>'needs_review' OR publication_status<>'draft')")===0,'Every private research occurrence/answer remains Draft/Needs Review');
    }
    foreach(array_reverse($private_batches) as $batch){check(!is_wp_error(CAFCC_Import::rollback($batch)),'Private research batch withdraws while retaining records');}
    check($private_progress===$wpdb->get_results('SELECT * FROM '.CAFCC_DB::table('progress').' ORDER BY id',ARRAY_A),'Private six-PDF metadata test preserves every student-progress field');
    echo 'Private research metadata rows validated: '.(int)$private_total."; all drafts; no hosting connection.\n";
}
