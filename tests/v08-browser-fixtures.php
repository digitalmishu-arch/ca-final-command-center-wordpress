<?php
/** Independent authored fixtures and explicitly disposable plan selection only. */
require __DIR__.'/v07-browser-fixtures.php';
wp_set_current_user(get_user_by('login','student_a')->ID);
global $wpdb;$final=(int)$wpdb->get_var($wpdb->prepare('SELECT id FROM '.CAFCC_Planner::table('plans')." WHERE user_id=%d AND course='final' ORDER BY id DESC LIMIT 1",get_current_user_id()));
if($final){$r=CAFCC_Planner::activate($final,array('request_key'=>str_replace('-','',wp_generate_uuid4())));if(is_wp_error($r))throw new RuntimeException($r->get_error_message());}
