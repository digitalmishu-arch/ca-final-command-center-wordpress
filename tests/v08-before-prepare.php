<?php
/** Disposable original package only, for an exact-v0.7 visual baseline. */
require '/var/www/html/wp-load.php';if(DB_NAME!=='cafcc_test'||parse_url(home_url(),PHP_URL_HOST)!=='127.0.0.1')throw new RuntimeException('Disposable loopback database required.');wp_set_current_user(get_user_by('login','test_admin')->ID);
function before_ok($r){if(is_wp_error($r))throw new RuntimeException($r->get_error_message());return $r;}
$p=before_ok(CAFCC_Package::upload(base64_encode(file_get_contents('/tmp/cafcc-owner-browser.zip'))));while($p['status']!=='completed'){$p=before_ok(CAFCC_Package::step($p['job_key'],array('cursor'=>(int)$p['cursor'],'confirmed'=>true,'attest_rights'=>true)));if($p['status']==='blocked')throw new RuntimeException('Original baseline fixture blocked.');}
$j=before_ok(CAFCC_Owner::plan(array('scope'=>'package','package_id'=>$p['id']),'publish'));while($j['phase']!=='completed')$j=before_ok(CAFCC_Owner::step($j['job_key'],array('cursor'=>(int)$j['cursor_position'],'confirmed'=>true,'accept_provisional'=>true)));echo 'Original disposable visual fixtures imported/published for software testing only.';
