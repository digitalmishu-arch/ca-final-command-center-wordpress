<?php
defined('ABSPATH') || exit;

/** Display-only public source copies; canonical hashes, rights and revisions remain intact. */
final class CAFCC_Public_Sources {
    public static function table(){global $wpdb;return $wpdb->prefix.'cafcc_public_source_links';}
    public static function migrate(){
        global $wpdb;$t=self::table();dbDelta("CREATE TABLE $t (
            id bigint unsigned NOT NULL AUTO_INCREMENT,
            source_hash varchar(64) NOT NULL,
            source_role varchar(32) NOT NULL,
            drive_file_id varchar(120) NOT NULL,
            title varchar(250) NOT NULL,
            state varchar(16) NOT NULL DEFAULT 'active',
            evidence_json longtext NOT NULL,
            reviewer_id bigint unsigned NOT NULL DEFAULT 0,
            checked_at datetime NOT NULL,
            PRIMARY KEY  (id),
            UNIQUE KEY exact_source_role (source_hash,source_role),
            KEY active_hash (source_hash,state)
        ) ENGINE=InnoDB ".$wpdb->get_charset_collate().';');
        $file=dirname(__DIR__).'/data/january2026-public-sources.json';$rows=json_decode(file_get_contents($file),true);
        foreach($rows['sources'] as $row){$old=$wpdb->get_var($wpdb->prepare("SELECT id FROM $t WHERE source_hash=%s AND source_role=%s",$row['sha256'],$row['role']));if($old)continue;
            $ok=$wpdb->insert($t,array('source_hash'=>$row['sha256'],'source_role'=>$row['role'],'drive_file_id'=>$row['drive_file_id'],'title'=>$row['title'],'state'=>'active','evidence_json'=>wp_json_encode(array('owner_authorised_public_source_copy'=>true,'public_reader_metadata_checked'=>true,'actual_pdf_bytes_checked'=>true,'checked_on'=>$rows['checked_on'],'original_exam_paper_claim'=>false,'page_jump_supported'=>false)),'reviewer_id'=>get_current_user_id(),'checked_at'=>current_time('mysql',true)));if(false===$ok)return CAFCC_Repository::error('Public source-link migration incomplete.',503);
        }return true;
    }
    public static function find($hash,$kind){
        if(!preg_match('/^[a-f0-9]{64}$/D',$hash)||!in_array($kind,array('question','answer'),true))return null;global $wpdb;$t=self::table();$role=$kind==='question'?'questions':'answers';$row=$wpdb->get_row($wpdb->prepare("SELECT * FROM $t WHERE source_hash=%s AND state='active' AND source_role IN (%s,'questions_and_answers') ORDER BY id LIMIT 1",$hash,$role),ARRAY_A);if(!$row)return null;
        $registered=$wpdb->get_results($wpdb->prepare('SELECT payload FROM '.CAFCC_Sources::table().' WHERE source_hash=%s',$hash),ARRAY_A);$valid=false;foreach($registered as $r){$d=json_decode($r['payload'],true);if(($d['technical_state']??'')==='pdf_checked'&&($d['selection_state']??'')==='owner_verified'&&($d['content_origin']??'')==='icai')$valid=true;}
        if(!$valid)return null;return array('url'=>'https://drive.google.com/file/d/'.$row['drive_file_id'].'/view','drive_file_id'=>$row['drive_file_id'],'hosting_label'=>'Owner-public Google Drive PDF','source_document_title'=>$row['title'],'owner_public_copy'=>true,'page_jump_supported'=>false);
    }
    public static function question($card,$source_hash){
        $copy=self::find($source_hash,'question');if(!$copy)return $card;
        foreach($card['source_citations'] as &$citation){$citation=array_merge($citation,$copy);$citation['label']=implode(' · ',array_filter(array(strtoupper($card['occurrences'][0]['source_type']),$card['occurrences'][0]['mtp_series']?:null,$card['subject_code'],$card['occurrences'][0]['exam_attempt'],'Q'.$card['occurrences'][0]['question_number'].($card['occurrences'][0]['subquestion_number']?'('.$card['occurrences'][0]['subquestion_number'].')':''))));}unset($citation);
        foreach($card['occurrences'] as &$occurrence){$occurrence['official_url']=$copy['url'];$occurrence['owner_public_copy']=true;$occurrence['hosting_label']=$copy['hosting_label'];$occurrence['page_jump_supported']=false;}unset($occurrence);return $card;
    }
    public static function answer($item,$answer){$copy=self::find($answer['source_hash']??'','answer');if($copy){$item=array_merge($item,$copy);$item['official_url']=$copy['url'];$item['verified_page']=$answer['page']??'';}return $item;}
    public static function init(){
        add_action('rest_api_init',function(){register_rest_route('cafcc/v9','/admin/public-source-links',array(
            array('methods'=>'GET','permission_callback'=>function($r){return CAFCC_REST::permission($r,true);},'callback'=>function(){global $wpdb;return $wpdb->get_results('SELECT id,source_hash,source_role,drive_file_id,title,state,checked_at FROM '.self::table().' ORDER BY id',ARRAY_A);}),
            array('methods'=>'POST','permission_callback'=>function($r){return CAFCC_REST::permission($r,true);},'callback'=>function($r){$d=CAFCC_Studio::body($r,4000);if(is_wp_error($d))return $d;if(array_diff(array_keys($d),array('id','state'))||!in_array($d['state']??'',array('active','disabled'),true))return CAFCC_Repository::error('Choose an existing public-copy link and its state.');$id=CAFCC_Repository::id($d['id']??null);if(is_wp_error($id))return $id;global $wpdb;$t=self::table();$old=$wpdb->get_row($wpdb->prepare("SELECT * FROM $t WHERE id=%d",$id),ARRAY_A);if(!$old)return CAFCC_Repository::error('Public source copy not found.',404);if(false===$wpdb->update($t,array('state'=>$d['state']),array('id'=>$id)))return CAFCC_Repository::error('Cannot save source-copy preference.',500);CAFCC_Bank_DB::audit_master('public_source_link_preference',$id,$old,$d);return array('saved'=>true);})
        ));});
    }
}
