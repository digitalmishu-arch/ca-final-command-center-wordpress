<?php
defined('ABSPATH') || exit;

/** Private source-wide permission register. No Media Library or public document URL. */
final class CAFCC_Rights {
    const USES=array('question_reproduction','answer_reproduction','electronic_storage','commercial_publication');
    public static function table(){global $wpdb;return $wpdb->prefix.'cafcc_private_rights';}
    public static function migrate(){
        global $wpdb;$t=self::table();dbDelta("CREATE TABLE $t (
            id bigint(20) unsigned NOT NULL AUTO_INCREMENT,
            revision bigint(20) unsigned NOT NULL DEFAULT 1,
            state varchar(24) NOT NULL DEFAULT 'draft',
            expires_on varchar(10) NOT NULL DEFAULT '',
            payload longtext NOT NULL,
            permission_pdf longblob DEFAULT NULL,
            permission_sha256 varchar(64) NOT NULL DEFAULT '',
            reviewer_id bigint(20) unsigned NOT NULL DEFAULT 0,
            updated_at datetime NOT NULL,
            PRIMARY KEY  (id), KEY state_expiry (state,expires_on)
        ) ENGINE=InnoDB ".$wpdb->get_charset_collate().';');
        $cols=$wpdb->get_col("SHOW COLUMNS FROM $t");return $cols&&in_array('permission_pdf',$cols,true)?true:CAFCC_Repository::error('Private rights register migration is incomplete.',503);
    }
    public static function get($id,$lock=false){global $wpdb;$t=self::table();$r=$wpdb->get_row($wpdb->prepare("SELECT id,revision,state,expires_on,payload,permission_sha256,reviewer_id,updated_at FROM $t WHERE id=%d".($lock?' FOR UPDATE':''),$id),ARRAY_A);if($r){$r['scope']=json_decode($r['payload'],true);unset($r['payload']);}return $r;}
    public static function save($id,$input){
        if(!CAFCC_Repository::admin_allowed())return CAFCC_Repository::error('Administrator access required.',403);
        if(!is_array($input)||array_diff(array_keys($input),array('expected_revision','scope','state','confirmed','permission_pdf_base64')))return CAFCC_Repository::error('Invalid permission register fields.');
        $scope=$input['scope']??null;$fields=array('issuing_authority'=>190,'permission_reference'=>190,'permission_date'=>10,'authorised_publisher'=>190,'covered_material'=>4000,'period_from'=>10,'period_to'=>10,'attribution'=>2000,'restrictions'=>4000,'expires_on'=>10,'duration_note'=>190);
        if(!is_array($scope)||array_diff(array_keys($scope),array_merge(array_keys($fields),self::USES,array('subject_codes','source_types','all_periods'))))return CAFCC_Repository::error('Enter the written permission scope.');
        $v=array();foreach($fields as $k=>$limit){$s=$scope[$k]??'';if(!is_string($s)||strlen($s)>$limit||CAFCC_Bank_DB::private_reference($s))return CAFCC_Repository::error('Invalid private rights field: '.$k);$v[$k]=sanitize_textarea_field($s);}
        foreach(array('permission_date','period_from','period_to','expires_on') as $k){if($v[$k]&&(!preg_match('/^\d{4}-\d{2}-\d{2}$/D',$v[$k])||!checkdate((int)substr($v[$k],5,2),(int)substr($v[$k],8,2),(int)substr($v[$k],0,4))))return CAFCC_Repository::error('Use a valid YYYY-MM-DD date for '.$k);}
        if($v['period_from']&&$v['period_to']&&$v['period_from']>$v['period_to'])return CAFCC_Repository::error('Covered period starts after it ends.');
        foreach(self::USES as $use){if(isset($scope[$use])&&!is_bool($scope[$use]))return CAFCC_Repository::error('Permission uses must be explicit true/false values.');$v[$use]=true===($scope[$use]??false);}
        $v['all_periods']=true===($scope['all_periods']??false);
        foreach(array('subject_codes'=>array('FR','AFM','AUDIT','DT','IDT','IBS'),'source_types'=>array('rtp','mtp','exam','study_material','case_study','other')) as $k=>$allowed){$a=$scope[$k]??array();if(!is_array($a)||!array_is_list($a)||array_diff($a,$allowed))return CAFCC_Repository::error('Invalid permission '.$k);$v[$k]=array_values(array_unique($a));}
        $state=$input['state']??'draft';if(!in_array($state,array('draft','active','suspended'),true))return CAFCC_Repository::error('Choose draft, active or suspended permission.');
        if($state==='active'){
            foreach(array('issuing_authority','permission_reference','permission_date','authorised_publisher','covered_material','attribution') as $k)if(!$v[$k])return CAFCC_Repository::error('Confirm the written permission '.$k.' before activating its scope.');
            if(!$v['subject_codes']||!$v['source_types']||(!$v['all_periods']&&(!$v['period_from']||!$v['period_to'])))return CAFCC_Repository::error('Confirm subjects, source categories and covered periods. Lifetime duration alone does not establish material/period scope.');
            if(true!==($input['confirmed']??false))return CAFCC_Repository::error('Confirm that this scope matches the written permission.');
            if($v['expires_on']&&$v['expires_on']<gmdate('Y-m-d'))return CAFCC_Repository::error('This permission has expired.');
        }
        $pdf=null;if(isset($input['permission_pdf_base64'])&&$input['permission_pdf_base64']!==''){$raw=$input['permission_pdf_base64'];if(!is_string($raw)||strlen($raw)>5600000)return CAFCC_Repository::error('Permission PDF exceeds the private 4 MB limit.');$pdf=base64_decode($raw,true);if(!$pdf||strlen($pdf)>4000000||substr($pdf,0,5)!=='%PDF-')return CAFCC_Repository::error('Upload a valid permission PDF; it is stored privately in the database.');}
        return CAFCC_Academic::transaction(function()use($id,$input,$v,$state,$pdf){global $wpdb;$old=$id?self::get($id,true):null;if($id&&!$old)return CAFCC_Repository::error('Permission not found.',404);if($old&&(string)($input['expected_revision']??'')!==(string)$old['revision'])return CAFCC_Repository::error('Permission changed. Reload the latest revision.',409);
            $row=array('revision'=>$old?(int)$old['revision']+1:1,'state'=>$state,'expires_on'=>$v['expires_on'],'payload'=>wp_json_encode($v),'reviewer_id'=>get_current_user_id(),'updated_at'=>current_time('mysql',true));if($pdf!==null){$row['permission_pdf']=$pdf;$row['permission_sha256']=hash('sha256',$pdf);}
            if(false===($old?$wpdb->update(self::table(),$row,array('id'=>$id)):$wpdb->insert(self::table(),$row)))return CAFCC_Repository::error('Cannot retain private permission.',500);$rid=$old?$id:$wpdb->insert_id;
            // Changing/revoking a grant withdraws linked publication atomically.
            if($old){$rt=CAFCC_Studio::table();$ids=$wpdb->get_col($wpdb->prepare("SELECT id FROM $rt WHERE rights_grant_id=%d",$rid));foreach($ids as $review_id){$before=CAFCC_Studio::get($review_id);$a=$before['approval_state'];unset($a['rights'],$a['publication']);if(false===$wpdb->update($rt,array('status'=>'needs_review','publication_status'=>'draft','revision'=>(int)$before['revision']+1,'approvals'=>wp_json_encode($a)),array('id'=>$review_id))||!CAFCC_Studio::audit(CAFCC_Studio::get($review_id),'permission_changed'))return CAFCC_Repository::error('Cannot retain permission withdrawal audit.',500);}}
            if(!CAFCC_Bank_DB::audit_master('private_rights',$rid,$old,self::get($rid)))return CAFCC_Repository::error('Cannot retain permission history.',500);return self::get($rid);
        });
    }
    public static function covers($id,$data,$kind='question',$lock=false){
        $r=self::get($id,$lock);if(!$r||$r['state']!=='active'||($r['expires_on']&&$r['expires_on']<gmdate('Y-m-d')))return false;$s=$r['scope'];
        foreach(array('electronic_storage','commercial_publication',$kind==='answer'?'answer_reproduction':'question_reproduction') as $use)if(empty($s[$use]))return false;
        if(!in_array($data['subject_code'],$s['subject_codes'],true)||!in_array($data['source_type'],$s['source_types'],true))return false;
        if(empty($s['all_periods'])){$attempt=$data['exam_attempt']??'';if(!preg_match('/^('.implode('|',array('January','February','March','April','May','June','July','August','September','October','November','December')).')\s+(20\d{2})$/i',$attempt))return false;$date=gmdate('Y-m-d',strtotime('1 '.$attempt.' UTC'));if($date<$s['period_from']||$date>$s['period_to'])return false;}
        return $r;
    }
    public static function public_guard($alias){$t=self::table();return " AND (($alias.permission_required=0) OR EXISTS(SELECT 1 FROM $t rg WHERE rg.id=$alias.rights_grant_id AND rg.revision=$alias.rights_grant_revision AND rg.state='active' AND (rg.expires_on='' OR rg.expires_on>='".gmdate('Y-m-d')."')))";}
    public static function init(){
        add_action('admin_menu',function(){if(CAFCC_Repository::admin_allowed())add_submenu_page('cafcc','Private ICAI Permission Register','Publication Rights','manage_options','cafcc-rights',array(__CLASS__,'screen'));});
        add_action('rest_api_init',function(){$p=function($r){return CAFCC_REST::permission($r,true);};
            register_rest_route('cafcc/v5','/admin/rights',array(array('methods'=>'GET','permission_callback'=>$p,'callback'=>function(){global $wpdb;$t=self::table();return array_map(array(__CLASS__,'get'),$wpdb->get_col("SELECT id FROM $t ORDER BY id DESC LIMIT 100"));}),array('methods'=>'POST','permission_callback'=>$p,'callback'=>function($r){$v=CAFCC_Studio::body($r,6000000);return is_wp_error($v)?$v:self::save(0,$v);})));
            register_rest_route('cafcc/v5','/admin/rights/(?P<id>[1-9][0-9]{0,17})',array('methods'=>'PATCH','permission_callback'=>$p,'callback'=>function($r){$v=CAFCC_Studio::body($r,6000000);return is_wp_error($v)?$v:self::save((int)$r['id'],$v);}));
            register_rest_route('cafcc/v5','/admin/rights/(?P<id>[1-9][0-9]{0,17})/document',array('methods'=>'GET','permission_callback'=>$p,'callback'=>function($r){global $wpdb;$t=self::table();$pdf=$wpdb->get_var($wpdb->prepare("SELECT permission_pdf FROM $t WHERE id=%d",(int)$r['id']));if(!$pdf)return CAFCC_Repository::error('No private permission document is stored.',404);return new WP_REST_Response(array('base64'=>base64_encode($pdf),'filename'=>'private-permission-'.(int)$r['id'].'.pdf'),200,array('Cache-Control'=>'private, no-store','X-Content-Type-Options'=>'nosniff'));}));
        });
    }
    public static function screen(){if(!CAFCC_Repository::admin_allowed())wp_die('Administrator access required.');wp_enqueue_script('cafcc-rights',plugins_url('assets/rights.js',CAFCC_FILE),array(),CAFCC_VERSION,true);wp_localize_script('cafcc-rights','CAFCCRights',array('url'=>rest_url('cafcc/v5/admin/rights'),'nonce'=>wp_create_nonce('wp_rest')));echo '<div class="wrap" id="cafcc-rights"><h1>Private publication rights register</h1><p>Record the written permission once for its covered sources. Lifetime means no expiry; it does not establish the covered materials, periods or uses. Documents remain in the private database, outside public uploads. Saving a changed grant withdraws linked questions for review.</p><button type="button" id="rights-new">New permission</button><div id="rights-list"></div><form id="rights-form" hidden></form><p id="rights-feedback" role="status"></p></div>';}
}
