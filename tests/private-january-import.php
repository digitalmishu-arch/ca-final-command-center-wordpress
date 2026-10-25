<?php
/** Opt-in local evidence only; no private source text in public CI or code. */
if(getenv('CAFCC_PRIVATE_JAN')!=='1')exit("Set CAFCC_PRIVATE_JAN=1 only in the disposable local worker.\n");
require '/var/www/html/wp-load.php';
if(DB_NAME!=='cafcc_test'||!in_array(parse_url(home_url(),PHP_URL_HOST),array('127.0.0.1','localhost'),true))exit("Disposable local WordPress required.\n");
$admin=get_user_by('login','test_admin');wp_set_current_user($admin->ID);$root=getenv('CAFCC_PRIVATE_PACKAGE');if(!$root||!is_dir($root))exit("Private package directory required.\n");
$report=array('scope'=>'Private disposable WordPress only; no Hostinger access or owner academic approval.','taxonomy_batches'=>0,'question_batches'=>0,'drafts_added'=>0,'retry_inserts'=>0,'real_publications'=>0);
global $wpdb;$existing=(int)$wpdb->get_var("SELECT COUNT(*) FROM ".CAFCC_Studio::table()." WHERE source_hash='8bdb55ac0ffd3f01a96c5caac07326d4529d30acf8963094828a348e9b22c737' AND stable_id LIKE 'R-%'");$report['existing_real_drafts']=$existing;
function private_jan_ok($r){if(is_wp_error($r))throw new RuntimeException($r->get_error_message());return $r;}
foreach(glob($root.'/taxonomy-imports/*.json') as $file){$p=private_jan_ok(CAFCC_Corpus_Import::preview(json_decode(file_get_contents($file),true)));private_jan_ok(CAFCC_Corpus_Import::apply($p['token']));$report['taxonomy_batches']++;}
foreach(glob($root.'/*/imports/*.json') as $file){$payload=json_decode(file_get_contents($file),true);$p=private_jan_ok(CAFCC_Studio::import_preview($payload));if(!$p['can_apply'])throw new RuntimeException('Private import preview contains conflicts: '.$file);$a=private_jan_ok(CAFCC_Studio::import_apply($p['token']));$report['drafts_added']+=$a['added'];$p=private_jan_ok(CAFCC_Studio::import_preview($payload));$a=private_jan_ok(CAFCC_Studio::import_apply($p['token']));$report['retry_inserts']+=$a['added'];$report['question_batches']++;}
foreach(glob($root.'/*.xlsx') as $file){$x=private_jan_ok(CAFCC_Review_V5_XLSX::preview(base64_encode(file_get_contents($file))));if($x['conflicts'])throw new RuntimeException('Workbook has revision/hash conflicts.');$report['workbook_validated']=basename($file);}
global $wpdb;$table=CAFCC_Studio::table();$hash='8bdb55ac0ffd3f01a96c5caac07326d4529d30acf8963094828a348e9b22c737';$report['real_rtp_rows_still_needs_review']=(int)$wpdb->get_var($wpdb->prepare("SELECT COUNT(*) FROM $table WHERE source_hash=%s AND stable_id LIKE 'R-%%' AND status='needs_review' AND publication_status='draft'",$hash));
if($report['drafts_added']!==max(0,10-$existing)||$report['real_rtp_rows_still_needs_review']!==10||$report['retry_inserts']!==0)throw new RuntimeException('Unexpected real draft count or non-idempotent retry.');
echo wp_json_encode($report,JSON_PRETTY_PRINT),PHP_EOL;
