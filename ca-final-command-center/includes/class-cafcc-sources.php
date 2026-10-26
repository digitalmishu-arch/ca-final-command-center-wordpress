<?php
defined('ABSPATH') || exit;

/** Private owner-verified source selection, separate from extraction/academic approval. */
final class CAFCC_Sources {
    public static function table(){global $wpdb;return $wpdb->prefix.'cafcc_source_register';}
    public static function migrate(){
        global $wpdb;$t=self::table();dbDelta("CREATE TABLE $t (
            id bigint(20) unsigned NOT NULL AUTO_INCREMENT,
            source_key varchar(120) NOT NULL,
            source_hash varchar(64) NOT NULL DEFAULT '',
            revision bigint(20) unsigned NOT NULL DEFAULT 1,
            rights_grant_id bigint(20) unsigned NOT NULL DEFAULT 0,
            payload longtext NOT NULL,
            reviewer_id bigint(20) unsigned NOT NULL,
            updated_at datetime NOT NULL,
            PRIMARY KEY  (id),
            UNIQUE KEY source_key (source_key),
            KEY source_hash (source_hash),
            KEY rights_grant_id (rights_grant_id)
        ) ENGINE=InnoDB ".$wpdb->get_charset_collate().';');return $wpdb->get_var("SHOW TABLES LIKE '$t'")?true:CAFCC_Repository::error('Private source register setup failed.',503);
    }
    public static function get($key,$lock=false){global $wpdb;$t=self::table();$r=$wpdb->get_row($wpdb->prepare("SELECT * FROM $t WHERE source_key=%s".($lock?' FOR UPDATE':''),$key),ARRAY_A);if($r){$r['data']=json_decode($r['payload'],true);unset($r['payload']);}return $r;}
    public static function public_url($url){
        if(!is_string($url)||strlen($url)>2048||CAFCC_Bank_DB::private_reference($url))return false;$p=wp_parse_url($url);
        if(!$p||($p['scheme']??'')!=='https'||empty($p['host'])||isset($p['user'])||isset($p['pass'])||isset($p['port'])||isset($p['query'])||isset($p['fragment'])||!preg_match('/\.pdf$/i',$p['path']??''))return false;
        $host=strtolower($p['host']);if(!str_contains($host,'.')||filter_var($host,FILTER_VALIDATE_IP)||preg_match('/(?:^|\.)(?:localhost|local|internal|test|invalid)$/i',$host))return false;return esc_url_raw($url,array('https'));
    }
    public static function clean($v){
        $allowed=array('source_key','title','subject_code','source_type','role','exam_attempt','mtp_series','issue_period','source_hash','source_url','icai_url','hosting','content_origin','selection_state','selection_evidence','technical_state','technical_notes','drive_file_id','edition_key');
        if(!is_array($v)||array_diff(array_keys($v),$allowed))return CAFCC_Repository::error('Invalid source-register fields.');$out=array();
        foreach($allowed as $k){$s=$v[$k]??'';if(!is_string($s)||strlen($s)>(in_array($k,array('selection_evidence','technical_notes'),true)?4000:2048))return CAFCC_Repository::error('Invalid source field: '.$k);$out[$k]=sanitize_textarea_field($s);}
        if(!preg_match('/^[A-Za-z0-9_.:-]{2,120}$/D',$out['source_key'])||!$out['title']||!in_array($out['subject_code'],array('FR','AFM','AUDIT','DT','IDT','IBS'),true)||!in_array($out['source_type'],CAFCC_Repository::SOURCES,true)||!in_array($out['role'],array('questions','answers','questions_and_answers','corrigendum','study_material'),true)||!$out['exam_attempt'])return CAFCC_Repository::error('Identify subject, category, attempt and source role.');
        if(!in_array($out['selection_state'],array('owner_verified','needs_review'),true)||!in_array($out['technical_state'],array('pdf_checked','retrieval_blocked','needs_layout_review'),true)||!in_array($out['hosting'],array('icai_hosted','owner_verified_icai_mirror','other'),true)||!in_array($out['content_origin'],array('icai','other'),true))return CAFCC_Repository::error('Distinguish owner selection, hosting and technical checks.');
        if(!self::public_url($out['source_url']))return CAFCC_Repository::error('Source URL needs a direct public HTTPS PDF; private Drive references belong in the private field.');
        if($out['icai_url']&&is_wp_error(CAFCC_Repository::official_url($out['icai_url'])))return CAFCC_Repository::error('The optional exact ICAI URL must be ICAI-hosted.');
        $official=!is_wp_error(CAFCC_Repository::official_url($out['source_url']));if(($out['hosting']==='icai_hosted'&&!$official)||($out['hosting']==='owner_verified_icai_mirror'&&($official||$out['selection_state']!=='owner_verified'||$out['content_origin']!=='icai')))return CAFCC_Repository::error('Source hosting declaration conflicts with its URL or owner selection.');
        if($out['source_hash']&&!preg_match('/^[a-f0-9]{64}$/D',$out['source_hash']))return CAFCC_Repository::error('Invalid source SHA-256.');if($out['technical_state']==='pdf_checked'&&!$out['source_hash'])return CAFCC_Repository::error('A processed PDF requires its actual hash.');
        if($out['drive_file_id']){if(preg_match('~https://drive\.google\.com/file/d/([A-Za-z0-9_-]+)~',$out['drive_file_id'],$m))$out['drive_file_id']=$m[1];if(!preg_match('/^[A-Za-z0-9_-]{10,120}$/D',$out['drive_file_id']))return CAFCC_Repository::error('Use the private source file ID or its individual Drive file link.');}
        return $out;
    }
    public static function save($v,$expected=null){
        if(is_wp_error($e=CAFCC_Studio::admin()))return $e;$v=self::clean($v);if(is_wp_error($v))return $v;
        return CAFCC_Academic::transaction(function()use($v,$expected){global $wpdb;$old=self::get($v['source_key'],true);if($old&&((string)$old['revision']!==(string)$expected))return CAFCC_Repository::error('Source changed; reload its current revision.',409);if($old&&$old['source_hash']&&$old['source_hash']!==$v['source_hash'])return CAFCC_Repository::error('Retain the original hash; add a separate source-revision key.',409);
            $row=array('source_key'=>$v['source_key'],'source_hash'=>$v['source_hash'],'revision'=>$old?(int)$old['revision']+1:1,'payload'=>wp_json_encode($v),'reviewer_id'=>get_current_user_id(),'updated_at'=>current_time('mysql',true));if(false===($old?$wpdb->update(self::table(),$row,array('id'=>$old['id'])):$wpdb->insert(self::table(),$row)))return CAFCC_Repository::error('Cannot save private source.',500);$id=$old?$old['id']:$wpdb->insert_id;
            if($old){$rt=CAFCC_Studio::table();$ids=$wpdb->get_col($wpdb->prepare("SELECT id FROM $rt WHERE source_key=%s OR (source_hash=%s AND source_hash<>'') OR (JSON_UNQUOTE(JSON_EXTRACT(payload,'$.answer.source_hash'))=%s AND %s<>'')",$v['source_key'],$v['source_hash'],$v['source_hash'],$v['source_hash']));foreach($ids as $rid){$r=CAFCC_Studio::get($rid,true);if(false===$wpdb->update($rt,array('publication_status'=>'draft','status'=>'needs_review','revision'=>(int)$r['revision']+1,'modified_at'=>current_time('mysql',true)),array('id'=>$rid)))return CAFCC_Repository::error('Cannot withdraw the changed source safely.',500);if(!CAFCC_Studio::audit(CAFCC_Studio::get($rid),'source_register_changed'))return CAFCC_Repository::error('Cannot retain source correction audit.',500);}}
            if(!CAFCC_Bank_DB::audit_master('source_register',$id,$old,self::get($v['source_key'])))return CAFCC_Repository::error('Cannot retain source declaration audit.',500);return self::get($v['source_key']);});
    }
    public static function import($rows){if(!is_array($rows)||!array_is_list($rows)||count($rows)>100)return CAFCC_Repository::error('Use at most 100 source declarations.');$out=array('added'=>0,'retained'=>0,'conflicts'=>array());foreach($rows as $v){$v=self::clean($v);if(is_wp_error($v))return $v;$old=self::get($v['source_key']);if($old){$out['retained']++;if($old['data']!==$v)$out['conflicts'][]=array('source_key'=>$v['source_key'],'message'=>'Existing source correction retained; edit the Source Register explicitly.');continue;}$r=self::save($v);if(is_wp_error($r))return $r;$out['added']++;}return $out;}
    public static function find_url($url,$hash='',$lock=false){
        global $wpdb;$t=self::table();$rows=$wpdb->get_results("SELECT * FROM $t ORDER BY id LIMIT 1000",ARRAY_A);foreach($rows as $r){$d=json_decode($r['payload'],true);if(($d['source_url']===$url||($d['icai_url']&&$d['icai_url']===$url))&&(!$hash||!$r['source_hash']||$r['source_hash']===$hash)){if($lock){$r=$wpdb->get_row($wpdb->prepare("SELECT * FROM $t WHERE id=%d FOR UPDATE",$r['id']),ARRAY_A);$d=json_decode($r['payload'],true);if(!($d['source_url']===$url||($d['icai_url']&&$d['icai_url']===$url))||($hash&&$r['source_hash']&&$r['source_hash']!==$hash))continue;}$r['data']=$d;unset($r['payload']);return $r;}}return null;
    }
    public static function authorised_url($url,$context=array()){
        $official=CAFCC_Repository::official_url($url);if(!is_wp_error($official))return $official;$r=self::find_url($url,$context['source_hash']??'');if(!$r||$r['data']['selection_state']!=='owner_verified'||$r['data']['hosting']!=='owner_verified_icai_mirror')return $official;
        foreach(array('subject_code','source_type','exam_attempt','mtp_series') as $k)if(isset($context[$k])&&$context[$k]!==$r['data'][$k])return CAFCC_Repository::error('Mirror source context does not match the verified register.');return self::public_url($url)?:$official;
    }
    public static function icai_material($data,$kind='question'){
        $a=$kind==='answer'?($data['answer']??array()):$data;$url=$a['official_url']??'';$hash=$a['source_hash']??'';
        $known=self::find_url($url);if($known&&$known['data']['content_origin']!=='icai')return false;
        if(!is_wp_error(CAFCC_Repository::official_url($url)))return (bool)$url;
        $r=self::find_url($url,$hash);if(!$r)return false;$d=$r['data'];if($d['content_origin']!=='icai'||$d['selection_state']!=='owner_verified'||$d['hosting']!=='owner_verified_icai_mirror'||$d['technical_state']!=='pdf_checked'||!$hash||$r['source_hash']!==$hash)return false;
        foreach(array('subject_code','source_type','exam_attempt','mtp_series') as $key)if(($data[$key]??'')!==$d[$key])return false;return true;
    }
    public static function publication_issues($data,$lock=false){
        $errors=array();foreach(array('question','answer') as $kind){$a=$kind==='answer'?($data['answer']??array()):$data;$url=$a['official_url']??'';$r=self::find_url($url,'',$lock);if(!$r)continue;$s=$r['data'];$valid=$s['selection_state']==='owner_verified'&&$s['technical_state']==='pdf_checked'&&$r['source_hash']===($a['source_hash']??'')&&in_array($s['role'],array($kind==='answer'?'answers':'questions','questions_and_answers'),true);foreach(array('subject_code','source_type','exam_attempt','mtp_series') as $key)if(($data[$key]??'')!==$s[$key])$valid=false;if(!$valid)$errors[]=ucfirst($kind).' source — retrieve/check the registered PDF and exact hash, role and attempt/series.';}return $errors;
    }
    public static function hosting($url){return !is_wp_error(CAFCC_Repository::official_url($url))?'ICAI-hosted PDF':'Owner-verified ICAI mirror';}
    public static function associate($grant){global $wpdb;$t=self::table();$rows=$wpdb->get_results("SELECT source_key FROM $t",ARRAY_A);foreach($rows as $row){$s=self::get($row['source_key']);$d=$s['data'];$probe=array_merge($d,array('official_url'=>$d['source_url'],'answer'=>array('official_url'=>$d['source_url'],'source_hash'=>$d['source_hash'])));if(CAFCC_Rights::covers($grant['id'],$probe))$wpdb->update($t,array('rights_grant_id'=>$grant['id']),array('id'=>$s['id']));}}
    public static function init(){add_action('rest_api_init',function(){$permission=function($r){return CAFCC_REST::permission($r,true);};register_rest_route('cafcc/v7','/admin/sources',array(array('methods'=>'GET','permission_callback'=>$permission,'callback'=>function(){global $wpdb;$t=self::table();return array_map(array(__CLASS__,'get'),$wpdb->get_col("SELECT source_key FROM $t ORDER BY id LIMIT 1000"));}),array('methods'=>'POST','permission_callback'=>$permission,'callback'=>function($r){$v=CAFCC_Studio::body($r);if(is_wp_error($v))return $v;return self::save($v['source']??array(),$v['expected_revision']??null);})));});}
}
