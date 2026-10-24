<?php
// Disposable local preview only. Never execute against an existing WordPress installation.
require '/var/www/html/wp-load.php';
if ('cafcc_test'!==DB_NAME) { throw new RuntimeException('Preview requires the disposable test database.'); }
update_option('siteurl','http://127.0.0.1:8092');update_option('home','http://127.0.0.1:8092');
wp_set_current_user(get_user_by('login','test_admin')->ID);
update_user_meta(get_user_by('login','student_a')->ID,'show_admin_bar_front','false');
global $wpdb;
$q=CAFCC_DB::table('questions');$wpdb->query("UPDATE $q SET publication_status='draft'");
foreach(CAFCC_Academic::listing('editions')['items'] as $ed){ if (!str_starts_with($ed['edition_key'],'TEST-')) { CAFCC_Academic_UI::review_hierarchy($ed['id']); } }
$page=wp_insert_post(array('post_type'=>'page','post_title'=>'CA Final Command Center','post_content'=>'[ca_final_command_center]','post_status'=>'publish'));
// A dedicated preview template uses the actual shortcode/assets and actual REST API.
file_put_contents(ABSPATH.'wp-content/themes/twentytwentyfive/cafcc-preview.php',"<?php /* Template Name: CAFCC local preview */ ?><!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><?php wp_head(); ?></head><body style=\"margin:0;background:#eef2f8\"><?php echo do_shortcode('[ca_final_command_center]'); wp_footer(); ?></body></html>");
update_post_meta($page,'_wp_page_template','cafcc-preview.php');
echo 'Local preview page: http://127.0.0.1:8092/?page_id='.$page."\n";

$mu=ABSPATH.'wp-content/mu-plugins';wp_mkdir_p($mu);file_put_contents($mu.'/cafcc-disposable-mail.php','<?php if(defined("DB_NAME")&&DB_NAME==="cafcc_test"){add_filter("pre_wp_mail",function($pre,$atts){update_option("cafcc_test_last_mail",$atts,false);return true;},10,2);}');
