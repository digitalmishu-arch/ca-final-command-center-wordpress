<?php
defined('ABSPATH') || exit;

/** Existing notebook rows, lazy reads and compare-and-swap writes; no data migration. */
final class CAFCC_Notes {
    public static function diagnostic($code,$route='notes',$status=503){
        $event=array('code'=>$code,'route'=>$route,'status'=>(int)$status,'request_id'=>wp_generate_uuid4(),'at'=>gmdate('c'));
        // Query text, connection details and note content are intentionally never logged.
        error_log('CAFCC_SERVICE '.wp_json_encode($event));
        global $wpdb;if(!$wpdb->last_error){$events=get_option('cafcc_service_diagnostics',array());$events[]=$event;update_option('cafcc_service_diagnostics',array_slice($events,-40),false);}
        return $event['request_id'];
    }
    public static function unavailable(){self::diagnostic('database_query_failed');return new WP_Error('cafcc_service','The study service is temporarily unavailable. Your saved work is unchanged. Please retry.',array('status'=>503));}
    public static function guard($callback){
        global $wpdb;$old=$wpdb->suppress_errors(true);$wpdb->last_error='';
        try{$result=$callback();if($wpdb->last_error)return self::unavailable();return $result;}
        catch(Throwable $e){return self::unavailable();}finally{$wpdb->suppress_errors($old);}
    }
    public static function load($id){return self::guard(function()use($id){
        if(is_wp_error($e=CAFCC_Library::allowed()))return $e;
        if(!CAFCC_Practice::visible_question($id))return CAFCC_Repository::error('Published question not found.',404);
        global $wpdb;$t=CAFCC_Practice::table('notebook');$r=$wpdb->get_row($wpdb->prepare("SELECT note_text,bookmarked FROM $t WHERE user_id=%d AND question_id=%d",get_current_user_id(),$id),ARRAY_A);
        if($wpdb->last_error)return self::unavailable();$note=$r['note_text']??'';
        return array('note_text'=>$note,'bookmarked'=>(bool)($r['bookmarked']??false),'note_hash'=>hash('sha256',$note));
    });}
    public static function save($id,$data){return self::guard(function()use($id,$data){
        $current=self::load($id);if(is_wp_error($current))return $current;
        if(!is_array($data)||array_diff(array_keys($data),array('note_text','expected_hash'))||!is_string($data['note_text']??null)||strlen($data['note_text'])>10000||!is_string($data['expected_hash']??null)||!preg_match('/^[a-f0-9]{64}$/D',$data['expected_hash']))return CAFCC_Repository::error('Send a bounded private note and its saved revision.');
        $text=sanitize_textarea_field($data['note_text']);
        return CAFCC_Academic::transaction(function()use($id,$data,$text){
            global $wpdb;$t=CAFCC_Practice::table('notebook');$uid=get_current_user_id();
            if(false===$wpdb->query($wpdb->prepare("INSERT IGNORE INTO $t (user_id,question_id,note_text,bookmarked,updated_at) VALUES (%d,%d,'',0,%s)",$uid,$id,current_time('mysql',true))))return self::unavailable();
            $row=$wpdb->get_row($wpdb->prepare("SELECT note_text FROM $t WHERE user_id=%d AND question_id=%d FOR UPDATE",$uid,$id),ARRAY_A);if(!$row)return self::unavailable();
            // A replay after a lost successful response is harmless; a stale different edit is rejected.
            if($row['note_text']!==$text&&!hash_equals(hash('sha256',$row['note_text']),$data['expected_hash']))return CAFCC_Repository::error('Your note changed in another tab. Reload the saved version before editing.',409);
            if($row['note_text']!==$text&&false===$wpdb->update($t,array('note_text'=>$text,'updated_at'=>current_time('mysql',true)),array('user_id'=>$uid,'question_id'=>$id)))return self::unavailable();
            return array('note_text'=>$text,'note_hash'=>hash('sha256',$text),'saved'=>true);
        });
    });}
    public static function init(){add_action('rest_api_init',function(){
        $p=function($r){return CAFCC_REST::permission($r);};
        register_rest_route('cafcc/v10','/notebook/(?P<id>[1-9][0-9]{0,17})',array(
            array('methods'=>'GET','permission_callback'=>$p,'callback'=>function($r){if(array_diff(array_keys($r->get_query_params()),array('_locale','rest_route')))return CAFCC_Repository::error('Owner selection is not supported.');return self::load((int)$r['id']);}),
            array('methods'=>'PUT','permission_callback'=>$p,'callback'=>function($r){$d=CAFCC_Studio::body($r,16000);return is_wp_error($d)?$d:self::save((int)$r['id'],$d);})
        ));
        register_rest_route('cafcc/v10','/admin/service-diagnostics',array('methods'=>'GET','permission_callback'=>function($r){return CAFCC_REST::permission($r,true);},'callback'=>function(){return array('events'=>get_option('cafcc_service_diagnostics',array()),'note'=>'Bounded service codes only. Bootstrap/database failures before plugin loading require the hosting PHP/database logs. No credentials, SQL or private note content are collected.');}));
    });add_filter('rest_post_dispatch',function($response,$server,$r){if(str_starts_with($r->get_route(),'/cafcc/v10/')){$response->header('Cache-Control','private, no-store');$response->header('Vary','Cookie');}return $response;},10,3);}
}
