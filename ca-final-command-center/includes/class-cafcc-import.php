<?php
defined('ABSPATH') || exit;

/** Append-only CSV batches: transactional preview, revalidation, commit, soft withdrawal. */
final class CAFCC_Import {
    public static function templates() {
        return array(
            'hierarchy'=>array('edition_key','subject_code','node_key','parent_key','node_type','title','position','heading_origin','source_url','source_location'),
            'documents'=>array('document_key','edition_key','title','source_type','exam_attempt','official_url','issue_period','mtp_series'),
            'occurrences'=>array('occurrence_key','question_key','question_title','document_key','edition_key','chapter_key','page_reference','question_number','subquestion_number','marks','marks_verified','question_type'),
            'question_topics'=>array('question_key','node_key'),
            'answers'=>array('answer_key','question_key','occurrence_key','answer_mode','answer_text','rights_basis','official_url','source_location')
        );
    }

    public static function transactional() {
        global $wpdb;
        $tables=array_merge(CAFCC_Academic_DB::entities(),array('questions','documents','chapters'));
        foreach ($tables as $entity) {
            $table=CAFCC_DB::table($entity);
            $engine=$wpdb->get_var($wpdb->prepare('SELECT ENGINE FROM information_schema.TABLES WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME=%s',$table));
            if ('InnoDB'!==$engine) { return CAFCC_Repository::error('Safe imports require InnoDB tables. No tables were converted or imported.',409); }
        }
        return true;
    }

    public static function parse($type,$csv) {
        $headers=self::templates()[$type]??null;
        if (!$headers || !is_string($csv) || strlen($csv)>524288 || wp_check_invalid_utf8($csv)!==$csv) { return CAFCC_Repository::error('Choose a supported CSV type and a valid UTF-8 file smaller than 512 KB.'); }
        $csv=preg_replace('/^\xEF\xBB\xBF/','',$csv);
        $stream=fopen('php://temp','r+'); fwrite($stream,$csv); rewind($stream);
        $actual=fgetcsv($stream,0,',','"','');
        if ($actual!==$headers) { fclose($stream); return CAFCC_Repository::error('CSV headers must exactly match the downloaded template, including order.'); }
        $rows=array();
        while (false!==($row=fgetcsv($stream,0,',','"',''))) {
            if (array(null)===$row || array('')===$row) { continue; }
            if (count($row)!==count($headers) || count($rows)>=200) { fclose($stream); return CAFCC_Repository::error('Each row must match the template; maximum 200 records per batch.'); }
            $rows[]=array_combine($headers,array_map('trim',$row));
        }
        fclose($stream);
        return $rows?:CAFCC_Repository::error('The CSV has no data rows.');
    }

    private static function resolve($kind,$key,$optional=false) {
        if ($optional && ''===$key) { return null; }
        $record=CAFCC_Academic::by_key($kind,$key);
        if (!$record) { throw new InvalidArgumentException('Unknown '.$kind.' key: '.$key); }
        return (int)$record['id'];
    }

    private static function apply($type,$rows,$batch_id) {
        global $wpdb;
        $manifest=array();
        foreach ($rows as $index=>$row) {
            try {
                $kind=$type; $data=$row;
                if ('hierarchy'===$type) {
                    $kind='taxonomy'; $data['edition_id']=self::resolve('editions',$row['edition_key']);
                    $s=CAFCC_DB::table('subjects'); $subject=$wpdb->get_var($wpdb->prepare("SELECT id FROM $s WHERE code=%s",$row['subject_code']));
                    if (!$subject) { throw new InvalidArgumentException('Unknown subject code.'); }
                    $data['subject_id']=(int)$subject; $data['parent_id']=self::resolve('taxonomy',$row['parent_key'],true);
                    $data['position']=$data['position']?:'0';
                    unset($data['edition_key'],$data['subject_code'],$data['parent_key']);
                } elseif ('documents'===$type) {
                    $data['edition_id']=self::resolve('editions',$row['edition_key']); unset($data['edition_key']);
                } elseif ('occurrences'===$type) {
                    $edition_id=self::resolve('editions',$row['edition_key']); $document_id=self::resolve('documents',$row['document_key']);
                    $question=CAFCC_Academic::by_key('questions',$row['question_key']);
                    if (!$question) {
                        $edition=CAFCC_Academic::get('editions',$edition_id);
                        $question=CAFCC_Academic::save('questions',array('stable_key'=>$row['question_key'],'edition_id'=>$edition_id,'primary_subject_id'=>$edition['subject_id'],
                            'document_id'=>$document_id,'chapter_node_id'=>self::resolve('taxonomy',$row['chapter_key'],true), 'title'=>$row['question_title'],
                            'question_number'=>$row['question_number'],'question_type'=>$row['question_type']?:'unknown'),0,$batch_id,true);
                        if (is_wp_error($question)) { return CAFCC_Repository::error('Row '.($index+2).': '.$question->get_error_message()); }
                        $manifest[]=array('kind'=>'questions','id'=>(int)$question['id']);
                    }
                    $data=array_intersect_key($row,CAFCC_Academic::definitions()['occurrences']);
                    $data['question_id']=(int)$question['id']; $data['document_id']=$document_id; $data['edition_id']=$edition_id;
                    $data['marks_verified']=$row['marks_verified']?:'0'; $data['question_type']=$row['question_type']?:'unknown';
                } elseif ('question_topics'===$type) {
                    $kind='tags'; $data=array('question_id'=>self::resolve('questions',$row['question_key']), 'node_id'=>self::resolve('taxonomy',$row['node_key']));
                } elseif ('answers'===$type) {
                    $data['question_id']=self::resolve('questions',$row['question_key']); $data['occurrence_id']=self::resolve('occurrences',$row['occurrence_key'],true);
                    unset($data['question_key'],$data['occurrence_key']);
                }
                $data['review_status']='needs_review'; $data['publication_status']='draft';
                $saved=CAFCC_Academic::save($kind,$data,0,$batch_id,true);
                if (is_wp_error($saved)) { return CAFCC_Repository::error('Row '.($index+2).': '.$saved->get_error_message(),$saved->get_error_data()['status']??400); }
                $manifest[]=array('kind'=>$kind,'id'=>(int)$saved['id']);
            } catch (InvalidArgumentException $e) { return CAFCC_Repository::error('Row '.($index+2).': '.$e->getMessage()); }
        }
        return $manifest;
    }

    public static function preview($type,$csv) {
        global $wpdb;
        if (!CAFCC_Repository::admin_allowed()) { return CAFCC_Repository::error('Administrator access is required.',403); }
        $rows=self::parse($type,$csv); if (is_wp_error($rows)) { return $rows; }
        $safe=self::transactional(); if (is_wp_error($safe)) { return $safe; }
        $probe=CAFCC_Academic::transaction(function()use($type,$rows){$m=self::apply($type,$rows,null);return is_wp_error($m)?$m:new WP_Error('cafcc_import_preview_rollback','Validated without committing',array('manifest'=>$m));});
        if($probe->get_error_code()!=='cafcc_import_preview_rollback')return $probe;
        $manifest=$probe->get_error_data()['manifest'];
        $token=wp_generate_uuid4();
        set_transient('cafcc_import_'.$token,array('owner_id'=>get_current_user_id(),'type'=>$type,'csv'=>$csv,'hash'=>hash('sha256',$csv),'batch_id'=>null),HOUR_IN_SECONDS);
        return array('token'=>$token,'type'=>$type,'row_count'=>count($rows),'record_count'=>count($manifest),'review_status'=>'needs_review',
            'publication_status'=>'draft','preview'=>array_slice($rows,0,20),'message'=>'Validation passed. No academic rows committed. Preview expires in one hour. All imported records require review.');
    }

    public static function commit($token) {
        global $wpdb;
        if (!CAFCC_Repository::admin_allowed()) { return CAFCC_Repository::error('Administrator access is required.',403); }
        if (!is_string($token) || !wp_is_uuid($token)) { return CAFCC_Repository::error('Invalid preview token.'); }
        $lock='cafcc-import-'.md5($wpdb->prefix);
        if ('1'!==(string)$wpdb->get_var($wpdb->prepare('SELECT GET_LOCK(%s,5)',$lock))) { return CAFCC_Repository::error('Another import is running. Retry shortly.',409); }
        try {
            $plan=get_transient('cafcc_import_'.$token);
            if (!$plan || (int)$plan['owner_id']!==get_current_user_id()) { return CAFCC_Repository::error('Preview expired or belongs to a different administrator.',403); }
            if ($plan['batch_id']) { return array('batch_id'=>$plan['batch_id'],'already_committed'=>true); }
            $safe=self::transactional(); if (is_wp_error($safe)) { return $safe; }
            $rows=self::parse($plan['type'],$plan['csv']); if (is_wp_error($rows)) { return $rows; }
            $result=CAFCC_Academic::transaction(function () use ($plan,$rows) {
                global $wpdb; $b=CAFCC_DB::table('import_batches');
                if (false===$wpdb->insert($b,array('owner_id'=>get_current_user_id(),'import_type'=>$plan['type'],'status'=>'committed','manifest'=>'[]','created_at'=>current_time('mysql',true)))) { return CAFCC_Repository::error('Cannot create an import batch.',500); }
                $batch=(int)$wpdb->insert_id; $manifest=self::apply($plan['type'],$rows,$batch);
                if (is_wp_error($manifest)) { return $manifest; }
                if (false===$wpdb->update($b,array('manifest'=>wp_json_encode($manifest)),array('id'=>$batch))) { return CAFCC_Repository::error('Cannot save import manifest.',500); }
                return array('batch_id'=>$batch,'record_count'=>count($manifest),'status'=>'committed','review_status'=>'needs_review');
            });
            if (!is_wp_error($result)) { $plan['batch_id']=$result['batch_id']; set_transient('cafcc_import_'.$token,$plan,HOUR_IN_SECONDS); }
            return $result;
        } finally { $wpdb->get_var($wpdb->prepare('SELECT RELEASE_LOCK(%s)',$lock)); }
    }

    public static function rollback($id) {
        global $wpdb;
        if (!CAFCC_Repository::admin_allowed()) { return CAFCC_Repository::error('Administrator access is required.',403); }
        $id=CAFCC_Repository::id($id); if (is_wp_error($id)) { return $id; }
        $table=CAFCC_DB::table('import_batches');
        $batch=$wpdb->get_row($wpdb->prepare("SELECT * FROM $table WHERE id=%d",$id),ARRAY_A);
        if (!$batch) { return CAFCC_Repository::error('Batch not found.',404); }
        if (false===$wpdb->update($table,array('status'=>'rolled_back'),array('id'=>$id))) { return CAFCC_Repository::error('Batch withdrawal failed.',500); }
        CAFCC_Academic::reset_cache();
        return array('batch_id'=>$id,'status'=>'rolled_back','records_retained'=>count(json_decode($batch['manifest'],true)?:array()),'message'=>'Batch withdrawn from student access. All records, notes and student progress are retained. Dependent records remain stored and are hidden where their source/path is withdrawn.');
    }
}
