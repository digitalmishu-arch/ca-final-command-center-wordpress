<?php
/**
 * Plugin Name: CA Final Command Center
 * Description: CA Final question bank and per-student practice tracking.
 * Version: 0.1.0
 * Requires PHP: 7.4
 */
if (!defined('ABSPATH')) exit;
final class CAFCC {
 const CAP='manage_cafcc_academics';
 const SUBJECTS=['FR'=>'Financial Reporting','AFM'=>'Advanced Financial Management','AUDIT'=>'Advanced Auditing, Assurance and Professional Ethics','DT'=>'Direct Tax Laws and International Taxation','IDT'=>'Indirect Tax Laws','IBS'=>'Integrated Business Solutions'];
 static function table($name){global $wpdb;return $wpdb->prefix.'cafcc_'.$name;}
 static function activate(){
  global $wpdb;require_once ABSPATH.'wp-admin/includes/upgrade.php';$collate=$wpdb->get_charset_collate();
  $q=self::table('questions');$p=self::table('progress');
  dbDelta("CREATE TABLE $q (
   id bigint(20) unsigned NOT NULL AUTO_INCREMENT,
   subject varchar(16) NOT NULL,
   chapter varchar(190) NOT NULL,
   topic varchar(190) NOT NULL DEFAULT '',
   source_type varchar(16) NOT NULL DEFAULT '',
   source_reference varchar(190) NOT NULL DEFAULT '',
   exam_term varchar(64) NOT NULL DEFAULT '',
   question_text longtext NOT NULL,
   created_at datetime NOT NULL,
   PRIMARY KEY  (id),
   KEY subject (subject),
   KEY chapter (chapter)
  ) $collate;");
  dbDelta("CREATE TABLE $p (
   id bigint(20) unsigned NOT NULL AUTO_INCREMENT,
   user_id bigint(20) unsigned NOT NULL,
   question_id bigint(20) unsigned NOT NULL,
   status varchar(20) NOT NULL DEFAULT 'not_started',
   notes text NOT NULL,
   updated_at datetime NOT NULL,
   PRIMARY KEY  (id),
   UNIQUE KEY user_question (user_id,question_id)
  ) $collate;");
  if($role=get_role('administrator')) $role->add_cap(self::CAP);
 }
 static function init(){
  add_action('admin_menu',[__CLASS__,'menu']);
  add_action('admin_post_cafcc_add_question',[__CLASS__,'save']);
  add_action('rest_api_init',[__CLASS__,'routes']);
  add_shortcode('cafcc_dashboard',[__CLASS__,'dashboard']);
 }
 static function menu(){add_menu_page('CA Final Command Center','CA Final CC',self::CAP,'cafcc',[__CLASS__,'admin'],'dashicons-welcome-learn-more');}
 static function admin(){
  if(!current_user_can(self::CAP)) wp_die('Forbidden');
  echo '<div class="wrap"><h1>CA Final Question Bank</h1>';
  if(isset($_GET['added'])) echo '<div class="notice notice-success"><p>Question saved.</p></div>';
  echo '<form method="post" action="'.esc_url(admin_url('admin-post.php')).'">';
  wp_nonce_field('cafcc_add_question');echo '<input type="hidden" name="action" value="cafcc_add_question">';
  echo '<p><label>Subject <select name="subject">';
  foreach(self::SUBJECTS as $k=>$v) echo '<option value="'.esc_attr($k).'">'.esc_html($v).'</option>';
  echo '</select></label></p>';
  foreach(['chapter'=>'Chapter','topic'=>'Topic','source_reference'=>'Source reference','exam_term'=>'Exam term'] as $k=>$v)
   echo '<p><label>'.esc_html($v).' <input name="'.esc_attr($k).'" class="regular-text" '.($k==='chapter'?'required':'').'></label></p>';
  echo '<p><label>Source <select name="source_type"><option value="exam">Exam</option><option value="rtp">RTP</option><option value="mtp">MTP</option><option value="other">Other</option></select></label></p>';
  echo '<p><label>Question<br><textarea name="question_text" class="large-text" rows="6" required></textarea></label></p>';
  submit_button('Add Question');echo '</form><p>Embed <code>[cafcc_dashboard]</code> on a student page.</p></div>';
 }
 static function save(){
  if(!current_user_can(self::CAP)) wp_die('Forbidden', '', ['response'=>403]);
  check_admin_referer('cafcc_add_question');
  $subject=isset($_POST['subject'])?sanitize_key(wp_unslash($_POST['subject'])):'';
  $chapter=isset($_POST['chapter'])?sanitize_text_field(wp_unslash($_POST['chapter'])):'';
  $question=isset($_POST['question_text'])?sanitize_textarea_field(wp_unslash($_POST['question_text'])):'';
  if(!isset(self::SUBJECTS[$subject])||$chapter===''||$question==='') wp_die('Missing required fields', '', ['response'=>400]);
  $source=isset($_POST['source_type'])?sanitize_key(wp_unslash($_POST['source_type'])):'other';
  if(!in_array($source,['exam','rtp','mtp','other'],true)) $source='other';
  $row=['subject'=>$subject,'chapter'=>$chapter,'question_text'=>$question,'source_type'=>$source,'created_at'=>current_time('mysql',true)];
  foreach(['topic','source_reference','exam_term'] as $k) $row[$k]=isset($_POST[$k])?sanitize_text_field(wp_unslash($_POST[$k])):'';
  global $wpdb;
  if(false===$wpdb->insert(self::table('questions'),$row)) wp_die('Database error','',['response'=>500]);
  wp_safe_redirect(add_query_arg('added','1',admin_url('admin.php?page=cafcc')));exit;
 }
 static function dashboard(){
  if(!is_user_logged_in()) return '<p>Please log in to access your CA Final dashboard.</p>';
  wp_enqueue_style('cafcc',plugins_url('assets/style.css',__FILE__),[], '0.1.0');
  wp_enqueue_script('cafcc',plugins_url('assets/app.js',__FILE__),[], '0.1.0',true);
  wp_localize_script('cafcc','CAFCC_CONFIG',['url'=>esc_url_raw(rest_url('cafcc/v1/')),'nonce'=>wp_create_nonce('wp_rest')]);
  $out='<div class="cafcc-app"><h2>CA Final Command Center</h2><p>Build consistency, one question at a time.</p><label for="cafcc-subject">Subject</label><select id="cafcc-subject"><option value="">All subjects</option>';
  foreach(self::SUBJECTS as $k=>$v) $out.='<option value="'.esc_attr($k).'">'.esc_html($v).'</option>';
  return $out.'</select><p id="cafcc-feedback" role="status"></p><div id="cafcc-list">Loading…</div></div>';
 }
 static function routes(){
  register_rest_route('cafcc/v1','/questions',['methods'=>'GET','callback'=>[__CLASS__,'questions'],'permission_callback'=>function(){return is_user_logged_in();}]);
  register_rest_route('cafcc/v1','/progress/(?P<id>\\d+)',['methods'=>'POST','callback'=>[__CLASS__,'progress'],'permission_callback'=>function(){return is_user_logged_in();}]);
 }
 static function questions($req){
  global $wpdb;$q=self::table('questions');$p=self::table('progress');$user=get_current_user_id();
  $subject=sanitize_key((string)$req->get_param('subject'));
  if($subject && !isset(self::SUBJECTS[$subject])) return new WP_Error('bad_subject','Invalid subject',['status'=>400]);
  $sql="SELECT q.*,COALESCE(p.status,'not_started') AS status,COALESCE(p.notes,'') AS notes FROM $q q LEFT JOIN $p p ON p.question_id=q.id AND p.user_id=%d";
  $args=[$user];if($subject){$sql.=' WHERE q.subject=%s';$args[]=$subject;}
  $sql.=' ORDER BY q.id DESC LIMIT 200';
  return rest_ensure_response($wpdb->get_results($wpdb->prepare($sql,$args),ARRAY_A));
 }
 static function progress($req){
  global $wpdb;$id=absint($req['id']);$q=self::table('questions');
  if(!$id || !$wpdb->get_var($wpdb->prepare("SELECT id FROM $q WHERE id=%d",$id))) return new WP_Error('not_found','Question not found',['status'=>404]);
  $status=sanitize_key((string)$req->get_param('status'));
  if(!in_array($status,['not_started','attempted','revision','mastered'],true)) return new WP_Error('bad_status','Invalid status',['status'=>400]);
  $notes=sanitize_textarea_field((string)$req->get_param('notes'));
  $result=$wpdb->replace(self::table('progress'),['user_id'=>get_current_user_id(),'question_id'=>$id,'status'=>$status,'notes'=>$notes,'updated_at'=>current_time('mysql',true)],['%d','%d','%s','%s','%s']);
  if($result===false) return new WP_Error('db_error','Could not save progress',['status'=>500]);
  return rest_ensure_response(['id'=>$id,'status'=>$status,'notes'=>$notes]);
 }
}
register_activation_hook(__FILE__,['CAFCC','activate']);
add_action('plugins_loaded',['CAFCC','init']);
