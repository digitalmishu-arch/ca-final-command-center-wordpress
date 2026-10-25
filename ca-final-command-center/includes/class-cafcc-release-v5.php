<?php
defined('ABSPATH') || exit;

/** Additive v5 gates and the single owner publication transaction. */
final class CAFCC_Release_V5 {
    public static function migrate(){
        global $wpdb;$t=CAFCC_Studio::table();$columns=$wpdb->get_col("SHOW COLUMNS FROM $t");
        foreach(array('question_format'=>"varchar(16) NOT NULL DEFAULT 'mixed'",'rights_grant_id'=>'bigint(20) unsigned NOT NULL DEFAULT 0','rights_grant_revision'=>'bigint(20) unsigned NOT NULL DEFAULT 0','permission_required'=>'tinyint(1) NOT NULL DEFAULT 0') as $k=>$sql){if(!in_array($k,$columns,true)&&false===$wpdb->query("ALTER TABLE $t ADD COLUMN $k $sql"))return CAFCC_Repository::error('Schema 5 migration incomplete. Existing identities are retained.',503);}
        $keys=$wpdb->get_col("SHOW INDEX FROM $t",2);if(!in_array('subjective_queue',$keys,true)&&false===$wpdb->query("ALTER TABLE $t ADD KEY subjective_queue (question_format,publication_status,status,id)"))return CAFCC_Repository::error('Subjective index migration incomplete.',503);
        if(!in_array('permission_scope',$keys,true)&&false===$wpdb->query("ALTER TABLE $t ADD KEY permission_scope (rights_grant_id,rights_grant_revision,permission_required)"))return CAFCC_Repository::error('Permission scope index incomplete.',503);
        $grant=CAFCC_Rights::migrate();if(is_wp_error($grant))return $grant;
        // Derive a NEW format field only. Do not rewrite academic labels, source
        // identities, prose, notes, accounts, progress or historical decisions.
        $ids=$wpdb->get_col("SELECT id FROM $t WHERE question_format='mixed'");foreach($ids as $id){$r=CAFCC_Studio::get($id);$d=$r['data'];$type=$d['question_type']??'';$section=$d['section']??'';$format=preg_match('/\bmcq\b|multiple.choice|objective/i',$section)||$type==='mcq'?'mcq':(preg_match('/descriptive|subjective/i',$section)||in_array($type,array('theory','practical'),true)?'subjective':'mixed');if($format!=='mixed'){$wpdb->update($t,array('question_format'=>$format),array('id'=>$id));if(!CAFCC_Studio::audit(CAFCC_Studio::get($id),'format_derived_v5'))return CAFCC_Repository::error('Cannot retain format migration audit.',503);}}
        foreach($wpdb->get_col("SELECT id FROM $t") as $id){$r=CAFCC_Studio::get($id);$required=($r['data']['rights_mode']??'')==='licensed_public'?1:0;if((int)($r['permission_required']??0)!==$required&&false===$wpdb->update($t,array('permission_required'=>$required),array('id'=>$id)))return CAFCC_Repository::error('Permission guard migration is incomplete.',503);}
        return true;
    }
    public static function format($data){if(($data['question_type']??'')==='mcq'||preg_match('/\bmcq\b|multiple.choice|objective/i',$data['section']??''))return 'mcq';$value=strtolower($data['question_format']??'');if(in_array($value,array('subjective','mcq','mixed'),true))return $value;$section=$data['section']??'';if(($data['question_type']??'')==='mcq'||preg_match('/\bmcq\b|multiple.choice|objective/i',$section))return 'mcq';return preg_match('/descriptive|subjective/i',$section)||in_array($data['question_type']??'',array('theory','practical'),true)?'subjective':'mixed';}
    public static function guard($alias){return " AND $alias.question_format='subjective' AND ($alias.pilot_gate=0 OR $alias.manual_quality_pass=1)".CAFCC_Rights::public_guard($alias);}
    public static function clean_content($value,$rights_mode,$basis){
        if(!is_array($value)||array_diff(array_keys($value),array('question','answer')))return CAFCC_Repository::error('Use question and answer rich-content fields.');
        if($value&&(!in_array($rights_mode,array('original','licensed_private_review','licensed_public'),true)||!$basis))return CAFCC_Repository::error('Full private content requires an explicit authorised storage basis.');
        $clean=array();foreach($value as $kind=>$body){if(!is_array($body)||array_diff(array_keys($body),array('body_html','author_name','source_location','source_text_sha256','structure','checks')))return CAFCC_Repository::error('Invalid rich '.$kind.' structure.');$v=array();foreach(array('body_html'=>500000,'author_name'=>190,'source_location'=>190,'source_text_sha256'=>64) as $key=>$limit){$s=$body[$key]??'';if(!is_string($s)||strlen($s)>$limit||CAFCC_Bank_DB::private_reference($s))return CAFCC_Repository::error('Invalid/oversize private '.$kind.' '.$key.'; no silent truncation.');$v[$key]=$key==='body_html'?CAFCC_Practice::html($s):sanitize_text_field($s);}if($v['source_text_sha256']&&!preg_match('/^[a-f0-9]{64}$/D',$v['source_text_sha256']))return CAFCC_Repository::error('Invalid transcription source hash.');foreach(array('structure','checks') as $key){$s=$body[$key]??array();if(!is_array($s)||strlen(wp_json_encode($s))>500000||CAFCC_Bank_DB::private_reference(wp_json_encode($s)))return CAFCC_Repository::error('Invalid private structured evidence.');$v[$key]=map_deep($s,'sanitize_text_field');}$clean[$kind]=$v;}
        return $clean;
    }
    public static function blockers($r){
        $d=$r['data'];$errors=array();global $wpdb;$bt=CAFCC_Bank_DB::table('batches');if($wpdb->get_var($wpdb->prepare("SELECT id FROM $bt WHERE batch_key=%s AND status='withdrawn'",$r['batch_key'])))$errors[]='Resume the held import batch as drafts before publication.';if(self::format($d)!=='subjective'||($d['question_type']??'')==='mcq'||preg_match('/\bmcq\b|multiple.choice/i',$d['section']??''))$errors[]='Only confirmed SUBJECTIVE records can enter this publication queue. MCQ/mixed research is retained privately.';
        if(($d['question_type']??'unknown')==='unknown')$errors[]='Review the question type (practical, theory or case) rather than guessing it from its source.';
        foreach(array('source','boundary','classification') as $stage){$e=CAFCC_Studio::stage_valid($r,$stage);if($e)$errors[]=$e;}
        if($d['source_type']==='exam'&&preg_match('/^May\s+2020$/i',$d['exam_attempt']))$errors[]='There was no May 2020 examination paper. Identify the actual source context; cancelled-cycle RTP/MTP materials remain separate.';
        if($d['source_type']==='exam'&&preg_match('/^[A-Za-z]+\s+20\d{2}$/D',$d['exam_attempt'])&&strtotime('1 '.$d['exam_attempt'].' UTC')>time())$errors[]='An actual examination paper cannot be dated in the future.';
        $a=$d['answer'];if(empty($a['question_identity'])||$a['question_identity']!==$d['stable_id']||($a['question_reference']??null)!==$d['reference']||($a['question_subreference']??'')!==$d['subreference']||empty($a['page'])||!preg_match('/^[a-f0-9]{64}$/D',$a['source_hash']??''))$errors[]='Confirm the exact answer document hash, question/subpart identity and answer page.';
        if(($a['question_source_hash']??'')!==$d['source_hash'])$errors[]='Confirm the answer pairing against this exact question-source hash.';
        foreach(array('subject_code','source_type','exam_attempt','mtp_series') as $field){if(($a[$field]??null)!==($d[$field]??''))$errors[]='Answer identity mismatch or unconfirmed '.$field.'. Pair the same subject, source category, attempt and MTP series.';}
        if(!empty($d['blocking_exceptions']))$errors[]='Resolve these blocking exceptions and save corrections: '.implode('; ',$d['blocking_exceptions']);
        foreach(array('question','answer') as $kind){if(empty($d['rich_content'][$kind]['body_html'])||!trim(wp_strip_all_tags($d['rich_content'][$kind]['body_html']??'')))$errors[]='Attach the complete authorised '.$kind.' content; a reference or page candidate is insufficient for full-text publication.';if(empty($d['rich_content'][$kind]['author_name']))$errors[]='Record the '.$kind.' author/source attribution.';}
        if($d['rights_mode']==='original'){$grant=null;}else{$grant=CAFCC_Rights::resolve($d);if(!$grant)$errors[]='Select one active source-wide permission covering the question, suggested answer, electronic storage, intended periods and commercial publication.';}
        $errors=array_merge($errors,CAFCC_Review_Tools::blockers($r));return array_values(array_unique($errors));
    }
    public static function decision($id,$input){
        if(is_wp_error($e=CAFCC_Studio::admin()))return $e;
        if(!is_array($input)||array_diff(array_keys($input),array('expected_revision','action','confirmed'))||true!==($input['confirmed']??false)||!in_array($input['action']??'',array('needs_review','publish','reject'),true))return CAFCC_Repository::error('Choose Needs Review, Publish or Reject for the current saved revision.');
        $result=CAFCC_Academic::transaction(function()use($id,$input){global $wpdb;$r=CAFCC_Studio::get($id,true);if(!$r)return CAFCC_Repository::error('Review not found.',404);if((string)($input['expected_revision']??'')!==(string)$r['revision'])return CAFCC_Repository::error('Stale review decision. Reload before applying it.',409);
            if($input['action']!=='publish'){$changed=CAFCC_Studio::decision($id,array('expected_revision'=>$r['revision'],'confirmed'=>true,'action'=>$input['action']==='reject'?'reject':'hold'));if(!is_wp_error($changed)&&$input['action']==='needs_review'){if(false===$wpdb->update(CAFCC_Studio::table(),array('status'=>'needs_review'),array('id'=>$id))||!CAFCC_Studio::audit(CAFCC_Studio::get($id),'owner_needs_review_v5'))return CAFCC_Repository::error('Cannot retain owner review state.',500);return CAFCC_Studio::get($id);}return $changed;}
            $errors=self::blockers($r);if($errors)return new WP_Error('cafcc_publication_blocked',implode("\n",$errors),array('status'=>409,'blockers'=>$errors,'review_id'=>$id,'publication_status'=>'draft'));
            $d=$r['data'];$grant=$d['rights_mode']==='original'?null:CAFCC_Rights::resolve($d,true);if($d['rights_mode']!=='original'&&!$grant)return new WP_Error('cafcc_publication_blocked','The source-wide permission changed or does not cover this publication.',array('status'=>409));
            if($grant){$d['rights_grant_id']=(int)$grant['id'];$d['rights_mode']='licensed_public';$d['rights_basis']='Private permission #'.$grant['id'].' revision '.$grant['revision'].': '.$grant['scope']['attribution'];}
            // The owner has inspected both full revisions on this page. Internal
            // fingerprints are still retained; no earlier AI/test approval is used.
            $r['data']=$d;CAFCC_Studio::$writing=true;
            try{
                $mapped=CAFCC_Studio::materialize($r,true);if(is_wp_error($mapped))return $mapped;$r=array_merge($r,$mapped);$linked=CAFCC_Review_Tools::link($r);if(is_wp_error($linked))return $linked;
                foreach(array('question','answer') as $kind){$body=$d['rich_content'][$kind];$ct=CAFCC_Practice::table('content');$old=$wpdb->get_row($wpdb->prepare("SELECT * FROM $ct WHERE question_id=%d AND content_kind=%s FOR UPDATE",$r['question_id'],$kind),ARRAY_A);
                    $v=array('question_id'=>$r['question_id'],'content_kind'=>$kind,'body_html'=>$body['body_html'],'author_name'=>$body['author_name'],'source_location'=>$body['source_location'],'rights_type'=>$grant?'licensed':'original','rights_basis'=>$d['rights_basis'],'rights_expires'=>$grant?$grant['expires_on']:'');
                    if($old)$v['expected_revision']=$old['revision'];$pc=CAFCC_Practice::save($v,$old?(int)$old['id']:0);if(is_wp_error($pc))return $pc;$approved=CAFCC_Practice::approve((int)$pc['id'],array('expected_revision'=>$pc['revision'],'rights_confirmed'=>true));if(is_wp_error($approved))return $approved;
                }
                // Source-PDF hash remains in the private mapping, not replaced by
                // a hash of transcribed HTML. This preserves the exact answer source.
                $a=array();foreach(CAFCC_Studio::STAGES as $stage)$a[$stage]=array('fingerprint'=>CAFCC_Studio::fingerprint($r,$stage),'reviewer'=>get_current_user_id(),'timestamp'=>current_time('mysql',true),'reviewed_revision'=>(int)$r['revision'],'workflow'=>'owner_v5');
                $r['approval_state']=$a;$mapped=CAFCC_Studio::materialize($r);if(is_wp_error($mapped))return $mapped;
                $a['publication']=array('reviewer'=>get_current_user_id(),'timestamp'=>current_time('mysql',true),'reviewed_revision'=>(int)$r['revision'],'workflow'=>'owner_v5');
                $values=array_merge($mapped,array('revision'=>(int)$r['revision']+1,'status'=>'approved','publication_status'=>'published','question_format'=>'subjective','fulltext_allowed'=>1,'permission_required'=>$grant?1:0,'payload'=>wp_json_encode($d),'payload_hash'=>hash('sha256',wp_json_encode($d)),'approvals'=>wp_json_encode($a),'rights_grant_id'=>$grant?(int)$grant['id']:0,'rights_grant_revision'=>$grant?(int)$grant['revision']:0,'modified_at'=>current_time('mysql',true)));
                foreach(array('question','answer') as $kind){$cv=CAFCC_Studio::content_version($r,$kind);$values[$kind.'_content_id']=$cv['id'];$values[$kind.'_content_revision']=$cv['revision'];}
                if(false===$wpdb->update(CAFCC_Studio::table(),$values,array('id'=>$id))||!CAFCC_Studio::audit(CAFCC_Studio::get($id),'owner_publish_v5'))return CAFCC_Repository::error('Cannot retain atomic publication audit.',500);
                return CAFCC_Studio::get($id);
            }finally{CAFCC_Studio::$writing=false;}
        });
        // A failed validation must never leave a previous public revision live.
        // Do not act on a stale decision: it may refer to an older owner's view.
        if(is_wp_error($result)&&$result->get_error_code()==='cafcc_publication_blocked'){
            $withdrawn=CAFCC_Academic::transaction(function()use($id,$input){global $wpdb;$r=CAFCC_Studio::get($id,true);if(!$r||(string)$r['revision']!==(string)$input['expected_revision'])return CAFCC_Repository::error('The record changed during validation. Reload it.',409);$a=$r['approval_state'];unset($a['publication']);if(false===$wpdb->update(CAFCC_Studio::table(),array('status'=>'needs_review','publication_status'=>'draft','revision'=>(int)$r['revision']+1,'approvals'=>wp_json_encode($a)),array('id'=>$id))||!CAFCC_Studio::audit(CAFCC_Studio::get($id),'publish_blocked_v5'))return CAFCC_Repository::error('Cannot retain blocked-publication audit.',500);return true;});if(is_wp_error($withdrawn))return $withdrawn;
        }return $result;
    }
    public static function init(){add_action('rest_api_init',function(){register_rest_route('cafcc/v4','/admin/reviews/(?P<id>[1-9][0-9]{0,17})/owner-decision',array('methods'=>'POST','permission_callback'=>function($r){return CAFCC_REST::permission($r,true);},'callback'=>function($r){$v=CAFCC_Studio::body($r);return is_wp_error($v)?$v:self::decision((int)$r['id'],$v);}));});}
}
