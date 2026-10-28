<?php
defined('ABSPATH') || exit;

/** Private presentation choices. Original sessions and academic records are never deleted. */
final class CAFCC_Saved {
    const ACTIONS=array('important','bookmark','revision','note','session','saved');
    public static function table($kind){if(!in_array($kind,array('visibility','events','locks'),true))throw new InvalidArgumentException('Unknown saved storage.');global $wpdb;return $wpdb->prefix.'cafcc_saved_'.$kind;}
    public static function migrate(){
        global $wpdb;require_once ABSPATH.'wp-admin/includes/upgrade.php';
        $schemas=array('visibility'=>"user_id bigint(20) unsigned NOT NULL,
            kind varchar(16) NOT NULL,
            target_id bigint(20) unsigned NOT NULL,
            hidden tinyint(1) NOT NULL DEFAULT 0,
            modified_at datetime NOT NULL,
            PRIMARY KEY  (user_id,kind,target_id)",
            'locks'=>"user_id bigint(20) unsigned NOT NULL,
            PRIMARY KEY  (user_id)",
            'events'=>"id bigint(20) unsigned NOT NULL AUTO_INCREMENT,
            user_id bigint(20) unsigned NOT NULL,
            request_key varchar(80) NOT NULL,
            request_hash varchar(64) NOT NULL,
            action varchar(16) NOT NULL,
            question_id bigint(20) unsigned NOT NULL,
            occurrence_id bigint(20) unsigned NOT NULL,
            session_id bigint(20) unsigned NOT NULL DEFAULT 0,
            before_json longtext NOT NULL,
            after_json longtext NOT NULL,
            response_json text NOT NULL,
            undone tinyint(1) NOT NULL DEFAULT 0,
            created_at bigint(20) unsigned NOT NULL,
            PRIMARY KEY  (id),
            UNIQUE KEY owner_request (user_id,request_key),
            KEY owner_history (user_id,question_id,id)");
        foreach($schemas as $k=>$sql){$t=self::table($k);dbDelta("CREATE TABLE $t ($sql) ENGINE=InnoDB ".$wpdb->get_charset_collate().';');if(!$wpdb->get_var("SHOW TABLES LIKE '$t'"))return CAFCC_Repository::error('Saved-list migration incomplete. Existing activity is retained.',503);}return true;
    }
    public static function hidden_sql($kind,$target){$t=self::table('visibility');$uid=(int)get_current_user_id();if(!in_array($kind,array('saved','session'),true))throw new InvalidArgumentException('Invalid visibility.');return "EXISTS(SELECT 1 FROM $t hidden WHERE hidden.user_id=$uid AND hidden.kind='$kind' AND hidden.target_id=$target AND hidden.hidden=1)";}
    private static function state($action,$qid,$oid,$sid,$lock=false){
        global $wpdb;$uid=get_current_user_id();$suffix=$lock?' FOR UPDATE':'';
        if(in_array($action,array('saved','session'),true)){
            if($action==='session'){$s=CAFCC_Study::table('sessions');$row=$wpdb->get_row($wpdb->prepare("SELECT id,status FROM $s WHERE id=%d AND user_id=%d AND question_id=%d AND occurrence_id=%d".$suffix,$sid,$uid,$qid,$oid),ARRAY_A);if(!$row)return CAFCC_Repository::error('Your timer session was not found.',404);if($row['status']!=='finished')return CAFCC_Repository::error('Finish the active session before archiving it.',409);}
            $t=self::table('visibility');return array('hidden'=>(bool)$wpdb->get_var($wpdb->prepare("SELECT hidden FROM $t WHERE user_id=%d AND kind=%s AND target_id=%d".$suffix,$uid,$action,$action==='session'?$sid:$qid)));
        }
        if(in_array($action,array('note','bookmark'),true)){$t=CAFCC_Practice::table('notebook');$r=$wpdb->get_row($wpdb->prepare("SELECT note_text,bookmarked FROM $t WHERE user_id=%d AND question_id=%d".$suffix,$uid,$qid),ARRAY_A);if(!$r)return CAFCC_Repository::error('Your saved record was not found.',404);return $action==='note'?array('note'=>$r['note_text']):array('bookmarked'=>(bool)$r['bookmarked']);}
        $t=CAFCC_Study::table('personal');$p=CAFCC_DB::table('progress');$r=$wpdb->get_row($wpdb->prepare("SELECT tags_json,outcome FROM $t WHERE user_id=%d AND question_id=%d AND occurrence_id=%d".$suffix,$uid,$qid,$oid),ARRAY_A);
        if($action==='important'){if(!$r)return CAFCC_Repository::error('Your Important marker was not found.',404);return array('tags'=>json_decode($r['tags_json'],true));}
        $prior=$wpdb->get_var($wpdb->prepare("SELECT status FROM $p WHERE user_id=%d AND question_id=%d".$suffix,$uid,$qid));return array('outcome'=>$r['outcome']??null,'progress'=>$prior);
    }
    private static function fingerprint($v){return hash('sha256',wp_json_encode($v));}
    public static function decorate(&$row){
        $map=array('important'=>'important','bookmarks'=>'bookmark','notes'=>'note','needs_revision'=>'revision','timed'=>'session','all'=>'saved');$row['actions']=array();
        foreach($map as $tab=>$action){$s=self::state($action,$row['question_id'],$row['occurrence_id'],(int)($row['session_id']??0));if(!is_wp_error($s))$row['actions'][$tab]=array('action'=>$action,'expected_hash'=>self::fingerprint($s),'hidden'=>$s['hidden']??false);}
    }
    private static function apply_state($action,$qid,$oid,$sid,$v){
        global $wpdb;$uid=get_current_user_id();$at=current_time('mysql',true);$result=true;
        if(in_array($action,array('saved','session'),true)){$t=self::table('visibility');$result=$wpdb->replace($t,array('user_id'=>$uid,'kind'=>$action,'target_id'=>$action==='session'?$sid:$qid,'hidden'=>$v['hidden']?1:0,'modified_at'=>$at));}
        elseif(in_array($action,array('note','bookmark'),true)){$t=CAFCC_Practice::table('notebook');$result=$wpdb->update($t,array_merge(array('updated_at'=>$at),$action==='note'?array('note_text'=>$v['note']):array('bookmarked'=>$v['bookmarked']?1:0)),array('user_id'=>$uid,'question_id'=>$qid));}
        else{$t=CAFCC_Study::table('personal');if($action==='important')$result=$wpdb->query($wpdb->prepare("UPDATE $t SET tags_json=%s,revision=revision+1,modified_at=%s WHERE user_id=%d AND question_id=%d AND occurrence_id=%d",wp_json_encode($v['tags']),$at,$uid,$qid,$oid));else{
            if($v['outcome']!==null)$result=$wpdb->query($wpdb->prepare("UPDATE $t SET outcome=%s,revision=revision+1,modified_at=%s WHERE user_id=%d AND question_id=%d AND occurrence_id=%d",$v['outcome'],$at,$uid,$qid,$oid));
            if($result!==false&&$v['progress']!==null)$result=$wpdb->update(CAFCC_DB::table('progress'),array('status'=>$v['progress'],'updated_at'=>$at),array('user_id'=>$uid,'question_id'=>$qid));
        }}return $result===false?CAFCC_Repository::error('Your change could not be saved. Please retry.',503):true;
    }
    public static function change($request){
        if(is_wp_error($e=CAFCC_Library::allowed()))return $e;$d=CAFCC_Studio::body($request,3000);if(is_wp_error($d))return $d;
        if(array_diff(array_keys($d),array('action','question_id','occurrence_id','session_id','expected_hash','request_key','undo_id','restore'))||!is_string($d['request_key']??null)||!preg_match('/^[A-Za-z0-9_-]{16,80}$/D',$d['request_key']))return CAFCC_Repository::error('Use a valid private-list request.');
        if(isset($d['restore'])&&!is_bool($d['restore']))return CAFCC_Repository::error('Use an explicit restore choice.');if(isset($d['session_id'])&&(!is_scalar($d['session_id'])||!preg_match('/^[0-9]{1,18}$/D',(string)$d['session_id'])))return CAFCC_Repository::error('Invalid session identity.');
        if(is_wp_error($e=CAFCC_Bank_DB::transactional()))return $e;
        return CAFCC_Notes::guard(function()use($d){return CAFCC_Academic::transaction(function()use($d){
            global $wpdb;$uid=get_current_user_id();$locks=self::table('locks');$events=self::table('events');
            if(false===$wpdb->query($wpdb->prepare("INSERT IGNORE INTO $locks (user_id) VALUES (%d)",$uid)))return CAFCC_Notes::unavailable();$wpdb->get_var($wpdb->prepare("SELECT user_id FROM $locks WHERE user_id=%d FOR UPDATE",$uid));
            $hash=self::fingerprint($d);$prior=$wpdb->get_row($wpdb->prepare("SELECT * FROM $events WHERE user_id=%d AND request_key=%s",$uid,$d['request_key']),ARRAY_A);if($prior)return hash_equals($prior['request_hash'],$hash)?json_decode($prior['response_json'],true):CAFCC_Repository::error('Request key already used.',409);
            $undo=null;
            if(isset($d['undo_id'])){$id=CAFCC_Repository::id($d['undo_id']);if(is_wp_error($id))return $id;$undo=$wpdb->get_row($wpdb->prepare("SELECT * FROM $events WHERE id=%d AND user_id=%d FOR UPDATE",$id,$uid),ARRAY_A);if(!$undo||$undo['undone']||time()-(int)$undo['created_at']>600)return CAFCC_Repository::error('Undo expired or is unavailable. Use the list controls to restore archived items.',409);$action=$undo['action'];$qid=(int)$undo['question_id'];$oid=(int)$undo['occurrence_id'];$sid=(int)$undo['session_id'];$expected=self::fingerprint(json_decode($undo['after_json'],true));}
            else{$action=$d['action']??'';$qid=CAFCC_Repository::id($d['question_id']??null);$oid=CAFCC_Repository::id($d['occurrence_id']??null);$sid=(int)($d['session_id']??0);$expected=$d['expected_hash']??'';if(is_wp_error($qid)||is_wp_error($oid)||!in_array($action,self::ACTIONS,true)||!is_string($expected)||!preg_match('/^[a-f0-9]{64}$/D',$expected))return CAFCC_Repository::error('Reload the current saved record.');}
            $before=self::state($action,$qid,$oid,$sid,true);if(is_wp_error($before))return $before;if(!hash_equals(self::fingerprint($before),$expected))return CAFCC_Repository::error('This private record changed. Reload before changing it.',409);
            $after=$before;
            if($undo)$after=json_decode($undo['before_json'],true);
            elseif(in_array($action,array('saved','session'),true))$after['hidden']=!($d['restore']??false);
            elseif($action==='important')$after['tags']=array_values(array_filter($before['tags'],function($t){return $t!=='Important';}));
            elseif($action==='bookmark')$after['bookmarked']=false;
            elseif($action==='note')$after['note']='';
            elseif($action==='revision'){foreach(array('outcome','progress')as $field)if($after[$field]==='needs_revision')$after[$field]='attempted';}
            if(is_wp_error($e=self::apply_state($action,$qid,$oid,$sid,$after)))return $e;
            if($undo&&false===$wpdb->update($events,array('undone'=>1),array('id'=>$undo['id'],'user_id'=>$uid)))return CAFCC_Notes::unavailable();
            $response=array('saved'=>true,'message'=>$undo?'Your previous private-list value was restored.':'Updated only your personal list. The question and other study activity are retained.','undo_seconds'=>600);
            if(false===$wpdb->insert($events,array('user_id'=>$uid,'request_key'=>$d['request_key'],'request_hash'=>$hash,'action'=>$action,'question_id'=>$qid,'occurrence_id'=>$oid,'session_id'=>$sid,'before_json'=>wp_json_encode($before),'after_json'=>wp_json_encode($after),'response_json'=>'{}','created_at'=>time())))return CAFCC_Notes::unavailable();$response['undo_id']=(int)$wpdb->insert_id;
            if(false===$wpdb->update($events,array('response_json'=>wp_json_encode($response)),array('id'=>$response['undo_id'])))return CAFCC_Notes::unavailable();return $response;
        });});
    }
    public static function init(){add_action('rest_api_init',function(){register_rest_route('cafcc/v11','/saved-action',array('methods'=>'POST','permission_callback'=>function($r){return CAFCC_REST::permission($r);},'callback'=>array(__CLASS__,'change')));});add_filter('rest_post_dispatch',function($res,$server,$r){if(str_starts_with($r->get_route(),'/cafcc/v11/')){$res->header('Cache-Control','private, no-store');$res->header('Vary','Cookie');}return $res;},10,3);}
}
