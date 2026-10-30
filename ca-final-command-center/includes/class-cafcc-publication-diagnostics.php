<?php
defined('ABSPATH') || exit;

/** Read-only, owner-admin diagnostics. Never publishes, repairs or exports student data. */
final class CAFCC_Publication_Diagnostics {
    public static function package($id,$selected){
        global $wpdb;
        $p=$wpdb->get_row($wpdb->prepare('SELECT id,owner_id,package_key,status,cursor_position,manifest,report FROM '.CAFCC_Package::table().' WHERE id=%d',$id),ARRAY_A);
        if(!$p||(int)$p['owner_id']!==get_current_user_id())return CAFCC_Repository::error('Private import not found.',404);
        $manifest=json_decode($p['manifest'],true);$members=$wpdb->get_results($wpdb->prepare('SELECT m.candidate_id,m.review_id,m.imported_revision,r.stable_id,r.revision,r.archived,r.publication_status FROM '.CAFCC_Owner::table('membership').' m JOIN '.CAFCC_Studio::table().' r ON r.id=m.review_id WHERE m.package_id=%d ORDER BY m.review_id',$id),ARRAY_A);
        $selected=array_fill_keys(array_map('intval',$selected),true);$excluded=array();$aliases=array();
        foreach($members as $m){if(!isset($selected[(int)$m['review_id']]))$excluded[]=$m;if($m['candidate_id']!==$m['stable_id'])$aliases[]=$m;}
        $states=$wpdb->get_results($wpdb->prepare('SELECT ordinal,kind,status FROM '.CAFCC_Package::items_table().' WHERE package_id=%d ORDER BY ordinal',$id),ARRAY_A);
        $expected=(int)($manifest['coverage']['subjective']??$manifest['coverage']['draft_candidates']??0);
        $out=array('id'=>(int)$id,'package_key'=>$p['package_key'],'status'=>$p['status'],'cursor'=>(int)$p['cursor_position'],'checkpoints'=>$states,'expected_subjective'=>$expected,'linked_subjective'=>count(array_unique(array_column($members,'review_id'))),'excluded_by_saved_selection'=>$excluded,'identity_aliases'=>$aliases);
        if(($manifest['format']??'')===CAFCC_Collection::FORMAT){$report=CAFCC_Collection::result_summary($id);if(!is_wp_error($report))$out['import_conflicts']=$report;}
        return $out;
    }
    public static function page($key,$page=1){
        if(is_wp_error($e=CAFCC_Studio::admin()))return $e;
        if(!is_int($page)||$page<1||$page>100)return CAFCC_Repository::error('Choose a valid diagnostic page.');
        $job=CAFCC_Owner::job($key);if(is_wp_error($job))return $job;
        $records=$job['records'];$out=array('format'=>'CAFCC-PUBLICATION-DIAGNOSTICS-1','application_version'=>CAFCC_VERSION,'generated_at'=>current_time('mysql',true),'job_key'=>$key,'phase'=>$job['phase'],'action'=>$job['action_name'],'selection'=>$job['selection'],'selected'=>count($records),'page'=>$page,'per_page'=>100,'pages'=>max(1,(int)ceil(count($records)/100)),'preview_summary'=>array_intersect_key($job['report'],array_flip(array('selected','eligible','warnings','preview_answer_pending','exception_counts'))),'records'=>array(),'academic_approval_created'=>false,'publication_actions'=>0);
        if($page>$out['pages'])return CAFCC_Repository::error('Diagnostic page is outside the selected snapshot.');
        if($page===1){
            $pid=($job['selection']['scope']??'current')==='current'?(int)get_option('cafcc_current_package',0):(int)($job['selection']['package_id']??0);
            if($pid){$package=self::package($pid,array_column($records,'id'));if(is_wp_error($package))return $package;$out['package']=$package;}
            global $wpdb;$out['available_collections']=$wpdb->get_results($wpdb->prepare('SELECT p.id,p.package_key,p.status,COUNT(DISTINCT m.review_id) linked_subjective FROM '.CAFCC_Package::table().' p LEFT JOIN '.CAFCC_Owner::table('membership').' m ON m.package_id=p.id WHERE p.owner_id=%d AND p.package_key LIKE %s GROUP BY p.id ORDER BY p.id DESC LIMIT 20',get_current_user_id(),'AFM-PAPER2-ALL-ATTEMPTS-%'),ARRAY_A);
        }
        foreach(array_slice($records,($page-1)*100,100)as $selected){
            $r=CAFCC_Studio::get((int)$selected['id']);if(!$r){$out['records'][]=array('id'=>(int)$selected['id'],'missing'=>true);continue;}
            $d=$r['data'];$q=CAFCC_Owner::preview_quality($r);$source=CAFCC_Sources::find_url($d['official_url'],$d['source_hash']);
            $out['records'][]=array('id'=>(int)$r['id'],'stable_id'=>$r['stable_id'],'selected_revision'=>(int)$selected['revision'],'current_revision'=>(int)$r['revision'],'changed_since_preview'=>(int)$selected['revision']!==(int)$r['revision'],'archived'=>(bool)$r['archived'],'publication_status'=>$r['publication_status'],'source_key'=>$d['source_key'],'source_hash'=>$d['source_hash'],'source_type'=>$d['source_type'],'attempt'=>$d['exam_attempt'],'series'=>$d['mtp_series'],'reference'=>$d['reference'],'subreference'=>$d['subreference'],'question_page'=>$d['question_page'],'section_label'=>$d['section'],'question_type'=>$d['question_type'],'question_format'=>CAFCC_Release_V5::format($d),'has_question_html'=>!!trim(wp_strip_all_tags($d['rich_content']['question']['body_html']??'')),'has_question_attribution'=>!empty($d['rich_content']['question']['author_name']),'question_html_sha256'=>hash('sha256',$d['rich_content']['question']['body_html']??''),'exact_source_registered'=>$source&&$source['source_hash']===$d['source_hash'],'source_role'=>$source['data']['role']??'','source_selection'=>$source['data']['selection_state']??'','rights_matched'=>(bool)CAFCC_Owner::grant($d),'blocks'=>$q['blocks'],'warnings'=>$q['warnings'],'answer_state'=>$q['answer_state'],'has_answer_html'=>!!trim(wp_strip_all_tags($d['rich_content']['answer']['body_html']??'')),'answer_html_integrity'=>CAFCC_Owner::html_integrity($d['rich_content']['answer']['body_html']??''),'saved_preview_block'=>$job['report']['blocked'][(string)$r['id']]['message']??'');
        }
        return $out;
    }
    public static function init(){
        add_action('rest_api_init',function(){register_rest_route('cafcc/v8','/admin/publication-diagnostics/(?P<key>[a-f0-9-]{36})',array('methods'=>'GET','permission_callback'=>function($r){return CAFCC_REST::permission($r,true);},'callback'=>function($r){$page=filter_var($r->get_param('page')??1,FILTER_VALIDATE_INT);return $page===false?CAFCC_Repository::error('Invalid diagnostic page.'):self::page($r['key'],$page);}));});
    }
}
