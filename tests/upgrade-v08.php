<?php
/** Fingerprint existing rows without exporting private values. Disposable tests only. */
require '/var/www/html/wp-load.php';
if(DB_NAME!=='cafcc_test')throw new RuntimeException('Disposable test database required.');
global $wpdb;$file='/tmp/cafcc-v08-preservation.json';$mode=getenv('CAFCC_UPGRADE_MODE')?:'verify';
if($mode==='snapshot'){$tables=$wpdb->get_col("SHOW TABLES LIKE '".$wpdb->esc_like($wpdb->prefix.'cafcc_')."%'");$tables[]=$wpdb->users;$tables[]=$wpdb->usermeta;$out=array();foreach($tables as $t){$hashes=array();for($offset=0;;$offset+=250){$rows=$wpdb->get_results("SELECT * FROM `$t` LIMIT 250 OFFSET $offset",ARRAY_A);foreach($rows as $r)$hashes[]=hash('sha256',wp_json_encode($r));if(count($rows)<250)break;}sort($hashes);$out[$t]=$hashes;}file_put_contents($file,wp_json_encode($out));echo count($out).' existing tables fingerprinted; no private rows exported.';exit;}
$old=json_decode(file_get_contents($file),true);foreach($old as $t=>$prior){$hashes=array();for($offset=0;;$offset+=250){$rows=$wpdb->get_results("SELECT * FROM `$t` LIMIT 250 OFFSET $offset",ARRAY_A);foreach($rows as $r)$hashes[]=hash('sha256',wp_json_encode($r));if(count($rows)<250)break;}sort($hashes);if($hashes!==$prior)throw new RuntimeException('Upgrade changed prior rows in '.$t);}
if((int)get_option('cafcc_db_version')!==10)throw new RuntimeException('Schema 10 missing.');echo 'PASS: v0.7 → v0.8 byte fingerprints preserved across '.count($old).' existing academic/student/user tables; schema 10 added separately.'.PHP_EOL;
