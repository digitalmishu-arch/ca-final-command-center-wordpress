<?php
/** Runs only inside the disposable WordPress container created by run-integration.sh. */
define('WP_INSTALLING', true);
// The first CLI bootstrap precedes installation; keep its cookie hash consistent
// with the installed site used by the separate HTTP requests.
define('COOKIEHASH', md5('http://localhost'));
$_SERVER['HTTP_HOST'] = 'localhost';
$_SERVER['REQUEST_URI'] = '/';
$_SERVER['SERVER_PORT'] = '80';
require '/var/www/html/wp-load.php';
require_once ABSPATH . 'wp-admin/includes/upgrade.php';
require_once ABSPATH . 'wp-admin/includes/plugin.php';
add_filter('pre_http_request', function () { return new WP_Error('test_offline', 'External requests disabled in tests.'); });
wp_install('CAFCC disposable test', 'test_admin', 'admin@example.invalid', false, '', 'cafcc-disposable-only');
wp_installing(false);
update_option('siteurl', 'http://localhost');
update_option('home', 'http://localhost');
$admin = get_user_by('login', 'test_admin')->ID;
$student_a = wp_create_user('student_a', 'cafcc-disposable-only', 'a@example.invalid');
$student_b = wp_create_user('student_b', 'cafcc-disposable-only', 'b@example.invalid');
$editor = wp_create_user('editor_fixture', 'cafcc-disposable-only', 'editor@example.invalid');
(new WP_User($editor))->set_role('editor');
wp_set_current_user($admin);
$plugin = 'ca-final-command-center/ca-final-command-center.php';
$legacy_mode = '1' === getenv('CAFCC_TEST_LEGACY');
if ($legacy_mode) {
    global $wpdb;
    // Reproduce the repository prototype's incompatible tables before upgrade.
    $legacy_q = $wpdb->prefix . 'cafcc_questions';
    $legacy_p = $wpdb->prefix . 'cafcc_progress';
    $wpdb->query("CREATE TABLE $legacy_q (id bigint unsigned NOT NULL AUTO_INCREMENT, subject varchar(16) NOT NULL,
        chapter varchar(190) NOT NULL, topic varchar(190) NOT NULL DEFAULT '', source_type varchar(16) NOT NULL DEFAULT '',
        source_reference varchar(190) NOT NULL DEFAULT '', exam_term varchar(64) NOT NULL DEFAULT '',
        question_text longtext NOT NULL, created_at datetime NOT NULL, PRIMARY KEY (id))");
    $wpdb->query("CREATE TABLE $legacy_p (id bigint unsigned NOT NULL AUTO_INCREMENT, user_id bigint unsigned NOT NULL,
        question_id bigint unsigned NOT NULL, status varchar(20) NOT NULL, notes text NOT NULL, updated_at datetime NOT NULL,
        PRIMARY KEY (id), UNIQUE KEY user_question (user_id,question_id))");
    $wpdb->insert($legacy_q, array('subject' => 'FR', 'chapter' => 'TEST ONLY legacy', 'question_text' => 'TEST ONLY unverified legacy text', 'created_at' => '2026-01-01 00:00:00'));
    $wpdb->insert($legacy_p, array('user_id' => $student_a, 'question_id' => 1, 'status' => 'mastered', 'notes' => 'TEST ONLY private legacy note', 'updated_at' => '2026-01-01 00:00:00'));
    $legacy_questions_before = $wpdb->get_results("SELECT * FROM $legacy_q", ARRAY_A);
    $legacy_progress_before = $wpdb->get_results("SELECT * FROM $legacy_p", ARRAY_A);
}
$result = activate_plugin($plugin);
if (is_wp_error($result)) { throw new RuntimeException($result->get_error_message()); }
CAFCC_REST::init();
CAFCC_Admin::init();
CAFCC_Frontend::init();
CAFCC_Academic_UI::init();
CAFCC_Practice::init();
CAFCC_Facets::init();
CAFCC_Studio::init();
CAFCC_Review_XLSX::init();
CAFCC_Access::init();
CAFCC_Portal::init();
CAFCC_Resources::init();
CAFCC_Diagnostics::init();
CAFCC_Rights::init();
CAFCC_Release_V5::init();
CAFCC_Corpus_Import::init();
CAFCC_Review_V5_XLSX::init();
CAFCC_Study::init();
CAFCC_Review_Tools::init();
CAFCC_Sources::init();
CAFCC_Package::init();
CAFCC_Owner::init();
CAFCC_Owner_UI::init();
CAFCC_Library::init();
CAFCC_Saved::init();
CAFCC_Public_Sources::init();
CAFCC_Standards::init();
CAFCC_MCQ_Admin::init();
CAFCC_MCQ_Student::init();
CAFCC_Notes::init();
CAFCC_Experience::init();
CAFCC_Planner::init();
CAFCC_Resource_Matrix::init();
add_filter('pre_wp_mail',function(){return true;});
foreach(array($student_a,$student_b) as $test_uid){$r=CAFCC_Access::get($test_uid);$grant=CAFCC_Access::decide($test_uid,array('expected_version'=>$r['version'],'action'=>'approve','plan_key'=>'test-original-fixtures','expires_at'=>'','legacy_identity_verified'=>true));if(is_wp_error($grant))throw new RuntimeException($grant->get_error_message());}
require __DIR__ . "/v04-baseline-fixtures.php";
$server = rest_get_server();
$count = 0;
function check($condition, $label) {
    global $count;
    if (!$condition) { fwrite(STDERR, "FAIL: $label\n"); exit(1); }
    echo 'PASS: ' . $label . "\n"; $count++;
}
function call_api($method, $path, $data = null, $nonce = true) {
    global $server;
    $r = new WP_REST_Request($method, '/cafcc/v1/' . $path);
    if ($nonce) $r->set_header('X-WP-Nonce', wp_create_nonce('wp_rest'));
    if ($data !== null) {
        $r->set_header('Content-Type', 'application/json');
        $r->set_body(wp_json_encode($data));
    }
    return $server->dispatch($r);
}
function create_record($entity, $data) {
    $response = call_api('POST', 'admin/' . $entity, $data);
    if ($response->get_status() !== 200) { throw new RuntimeException($entity . ': ' . wp_json_encode($response->get_data())); }
    baseline_after_record($entity,$response->get_data());
    return $response->get_data();
}
function http_api($method, $path, $body = null, $user_id = 0, $nonce = true, $version = "v1") {
    $previous_user = get_current_user_id();
    $previous_cookie = $_COOKIE[LOGGED_IN_COOKIE] ?? null;
    $headers = array('Content-Type: application/json');
    if ($user_id) {
        // A real session token is required for the HTTP nonce/cookie combination.
        $cookie = wp_generate_auth_cookie($user_id, time() + 3600, 'logged_in');
        $_COOKIE[LOGGED_IN_COOKIE] = $cookie;
        wp_set_current_user($user_id);
        $headers[] = 'Cookie: ' . LOGGED_IN_COOKIE . '=' . $cookie;
        if ($nonce) {
            $headers[] = 'X-WP-Nonce: ' . (true === $nonce ? wp_create_nonce('wp_rest') : 'invalid');
        }
    }
    $context = stream_context_create(array('http' => array('method' => $method, 'header' => implode("\r\n", $headers),
        'content' => null === $body ? '' : wp_json_encode($body), 'ignore_errors' => true, 'timeout' => 10, 'follow_location' => 0)));
    $result = file_get_contents('http://localhost/index.php?rest_route=/cafcc/' . $version . '/' . $path, false, $context);
    wp_set_current_user($previous_user);
    if (null === $previous_cookie) { unset($_COOKIE[LOGGED_IN_COOKIE]); } else { $_COOKIE[LOGGED_IN_COOKIE] = $previous_cookie; }
    preg_match('/\s([0-9]{3})\s/', $http_response_header[0] ?? '', $match);
    if (false === $result || !isset($match[1]) || !is_array(json_decode($result, true))) {
        fwrite(STDERR, 'Unexpected HTTP response: ' . ($http_response_header[0] ?? 'no status') . ' ' . substr((string) $result, 0, 400) . "\n");
    }
    return array('status' => (int) ($match[1] ?? 0), 'body' => json_decode($result, true));
}
check(is_plugin_active($plugin), 'Plugin activates through the WordPress plugin API');
check(CAFCC_DB::VERSION === get_option('cafcc_db_version'), 'Migration version recorded after setup');
check(shortcode_exists('cafcc_dashboard'), 'Prototype dashboard shortcode remains supported');
if ($legacy_mode) {
    check(CAFCC_DB::legacy_counts() === array('questions' => 1, 'progress' => 1), 'Prototype tables detected independently of the new schema');
    check($wpdb->get_results("SELECT * FROM $legacy_q", ARRAY_A) === $legacy_questions_before, 'Upgrade preserves every prototype question field');
    check($wpdb->get_results("SELECT * FROM $legacy_p", ARRAY_A) === $legacy_progress_before, 'Upgrade preserves private prototype notes and progress unchanged');
}
check(CAFCC_Repository::listing('subjects')['total'] === 6, 'Exactly six CA Final subjects are seeded');
foreach (array('chapters','topics','documents','questions') as $entity) {
    check(CAFCC_Repository::listing($entity)['total'] === 0, 'No invented ' . $entity . ' seeded');
}
delete_option('cafcc_db_version');
check(CAFCC_DB::migrate() === true && CAFCC_Repository::listing('subjects')['total'] === 6, 'Migration retry is idempotent');
check(call_api('GET', 'summary')->get_data()['total'] === 0, 'Empty summary starts at zero');
$subject = CAFCC_Repository::listing('subjects')['items'][0];
$chapter = create_record('chapters', array('subject_id' => $subject['id'], 'title' => 'TEST ONLY chapter', 'syllabus_version' => 'TEST ONLY syllabus', 'position' => 1));
$chapter_b = create_record('chapters', array('subject_id' => $subject['id'], 'title' => 'TEST ONLY other chapter', 'syllabus_version' => 'TEST ONLY syllabus', 'position' => 2));
$topic = create_record('topics', array('chapter_id' => $chapter['id'], 'title' => 'TEST ONLY topic'));
$document_data = array('title' => 'TEST ONLY source', 'source_type' => 'exam', 'exam_attempt' => 'TEST ONLY attempt',
    'syllabus_version' => 'TEST ONLY syllabus', 'official_url' => 'https://www.icai.org/test-only-not-a-real-document.pdf', 'verification_status' => 'verified');
$document = create_record('documents', $document_data);
$qdata = array('document_id' => $document['id'], 'chapter_id' => $chapter['id'], 'topic_id' => $topic['id'],
    'question_number' => 'TEST-1', 'title' => 'TEST ONLY question reference', 'verification_status' => 'verified', 'publication_status' => 'published');
$q = create_record('questions', $qdata);
$draft = create_record('questions', array_merge($qdata, array('question_number' => 'TEST-DRAFT', 'publication_status' => 'draft')));
check(call_api('POST', 'admin/questions', array_merge($qdata, array('chapter_id' => $chapter_b['id'])))->get_status() === 400, 'Question topic must belong to the selected chapter');
$other_syllabus = create_record('chapters', array('subject_id' => $subject['id'], 'title' => 'TEST ONLY mismatched syllabus', 'syllabus_version' => 'OTHER TEST syllabus', 'position' => 0));
check(call_api('POST', 'admin/questions', array_merge($qdata, array('chapter_id' => $other_syllabus['id'], 'topic_id' => null)))->get_status() === 400, 'Question source and chapter syllabus must match');
check(call_api('POST', 'admin/questions', array_merge($qdata, array('verification_status' => 'unverified')))->get_status() === 400, 'Unverified questions cannot be published');
foreach (array('https://drive.google.com/file/d/private', 'https://icai.org.evil.example/file', 'javascript:alert(1)', 'http://www.icai.org/file', 'https://www.icai.org/file?private_token=secret', 'https://evil.example@icai.org/file') as $url) {
    check(call_api('POST', 'admin/documents', array_merge($document_data, array('official_url' => $url)))->get_status() === 400, 'Unsafe/nonofficial URL rejected: ' . $url);
}
check(call_api('POST', 'admin/documents', array_merge($document_data, array('official_url' => '')))->get_status() === 400, 'Verified source requires an official URL');
check(call_api('POST', 'admin/chapters', array('subject_id' => '1 OR 1=1', 'title' => 'TEST', 'syllabus_version' => 'TEST'))->get_status() === 400, 'SQL injection in relation ID is rejected');
check(call_api('POST', 'admin/subjects', array('code' => 'TEST', 'name' => array('array injection')))->get_status() === 400, 'Array injection in text field rejected');
$sanitized = create_record('topics', array('chapter_id' => $chapter_b['id'], 'title' => '<b>TEST ONLY safe text</b>'));
check($sanitized['title'] === 'TEST ONLY safe text', 'HTML is stripped from master text');
check(call_api('PATCH', 'admin/chapters/' . $chapter['id'], array('syllabus_version' => 'CHANGED'))->get_status() === 409, 'Referenced chapter structural metadata is protected');
check(call_api('DELETE', 'admin/chapters/' . $chapter['id'])->get_status() === 409, 'Referenced chapter cannot be deleted');
check(call_api('PATCH', 'admin/topics/' . $topic['id'], array('chapter_id' => $chapter_b['id']))->get_status() === 409, 'Referenced topic cannot be moved to another chapter');
check(call_api('PATCH', 'admin/documents/' . $document['id'], array('syllabus_version' => 'CHANGED'))->get_status() === 409, 'Referenced source syllabus cannot be changed');
check(call_api('GET', 'summary', null, false)->get_status() === 403, 'Signed-in REST requests require a valid nonce');
$r = new WP_REST_Request('POST', '/cafcc/v1/admin/subjects'); $r->set_header('X-WP-Nonce', 'invalid');
check($server->dispatch($r)->get_status() === 403, 'Invalid nonce is rejected');
foreach (array(0 => 'Anonymous', $student_a => 'Student', $editor => 'Editor') as $id => $role) {
    wp_set_current_user($id);
    foreach (CAFCC_Repository::entities() as $entity) {
        foreach (array('GET', 'POST', 'PATCH', 'DELETE') as $method) {
            $path = 'admin/' . $entity . (in_array($method, array('PATCH','DELETE'), true) ? '/1' : '');
            check(in_array(call_api($method, $path, array('title' => 'attack'))->get_status(), array(401,403), true), "$role cannot $method master $entity");
        }
    }
    check(is_wp_error(CAFCC_Repository::save('subjects', array('code' => 'ATTACK', 'name' => 'Attack'))), "$role cannot bypass REST permissions through repository");
}
wp_set_current_user($editor);
$editor_user = new WP_User($editor); $editor_user->add_cap('manage_options');
check(call_api('POST', 'admin/subjects', array('code' => 'XX', 'name' => 'Attack'))->get_status() === 403, 'Nonadministrator with manage_options still cannot edit master data');
wp_set_current_user(0);
check(call_api('GET', 'questions')->get_status() === 401, 'Anonymous visitors cannot read student questions');
check(call_api('PUT', 'progress/' . $q['id'], array('status' => 'completed'))->get_status() === 401, 'Anonymous visitors cannot save progress');
check(str_contains(CAFCC_Frontend::render(), 'Sign in'), 'Public dashboard shows sign-in state');
wp_set_current_user($student_a);
check(call_api('GET', 'questions')->get_data()['total'] === 1, 'Students see only the verified published question');
check(count(call_api('GET', 'catalog')->get_data()['chapters']) === 1, 'Catalog hides chapters without published verified questions');
check(call_api('GET', 'questions?ignored=1')->get_status() === 404, 'Unknown route does not expose records');
$r = new WP_REST_Request('GET', '/cafcc/v1/questions'); $r->set_header('X-WP-Nonce', wp_create_nonce('wp_rest')); $r->set_param('chapter_id', '1 OR 1=1');
check($server->dispatch($r)->get_status() === 400, 'Student filter rejects SQL injection');
check(call_api('PUT', 'progress/' . $draft['id'], array('status' => 'completed'))->get_status() === 404, 'Students cannot track draft questions');
check(call_api('PUT', 'progress/' . $q['id'], array('status' => 'invalid'))->get_status() === 400, 'Unknown progress status rejected');
check(call_api('PUT', 'progress/' . $q['id'], array('status' => 'completed', 'user_id' => $student_b))->get_status() === 400, 'Client-supplied student ID is rejected');
foreach (CAFCC_Repository::STATUSES as $status) {
    check(call_api('PUT', 'progress/' . $q['id'], array('status' => $status))->get_status() === 200, 'Student can save ' . $status);
}
check(call_api('PUT', 'progress/' . $q['id'], array('status' => 'completed'))->get_status() === 200, 'Repeated identical progress write is safe');
check(call_api('GET', 'summary')->get_data()['counts']['completed'] === 1, 'Student A sees their own completion');
wp_set_current_user($student_b);
check(call_api('GET', 'questions')->get_data()['items'][0]['progress_status'] === 'not_started', 'Student B cannot see student A progress');
check(call_api('GET', 'summary')->get_data()['counts']['completed'] === 0, 'Student B summary excludes student A');
check(call_api('PUT', 'progress/' . $q['id'], array('status' => 'needs_revision'))->get_status() === 200, 'Student B can save separate progress');
wp_set_current_user($student_a);
check(call_api('GET', 'questions')->get_data()['items'][0]['progress_status'] === 'completed', 'Student B write leaves student A unchanged');
$anonymous_http = http_api('GET', 'questions');
if (401 !== $anonymous_http['status']) { fwrite(STDERR, wp_json_encode($anonymous_http) . "\n"); }
check($anonymous_http['status'] === 401, 'Actual HTTP rejects anonymous access');
check(http_api('GET', 'questions', null, $student_a, false)['status'] === 401, 'Actual HTTP cookie without nonce does not authenticate');
check(http_api('GET', 'questions', null, $student_a, 'invalid')['status'] === 403, 'Actual HTTP invalid nonce is rejected by WordPress');
$http_a = http_api('GET', 'questions', null, $student_a);
if (200 !== $http_a['status']) { fwrite(STDERR, wp_json_encode($http_a) . "\n"); }
check($http_a['status'] === 200 && $http_a['body']['items'][0]['progress_status'] === 'completed', 'Actual HTTP authenticates student A with matching cookie and nonce');
$http_b = http_api('GET', 'questions', null, $student_b);
check($http_b['status'] === 200 && $http_b['body']['items'][0]['progress_status'] === 'needs_revision', 'Actual HTTP keeps student B progress separate');
check(http_api('POST', 'admin/subjects', array('code' => 'NO', 'name' => 'attack'), $student_a)['status'] === 403, 'Actual HTTP blocks student master writes');
check(http_api('PUT', 'progress/' . $q['id'], array('status' => 'attempted', 'user_id' => $student_b), $student_a)['status'] === 400, 'Actual HTTP rejects forged progress owner');
check(http_api('GET', 'admin/subjects', null, $admin)['status'] === 200, 'Actual HTTP allows authenticated administrator master access');
check(str_contains(CAFCC_Frontend::render(), 'Question Explorer'), 'Signed-in dashboard renders the explorer');
wp_set_current_user($admin);
check(call_api('DELETE', 'admin/questions/' . $q['id'])->get_status() === 409, 'Question deletion cannot destroy existing student progress');
check(call_api('PATCH', 'admin/documents/' . $document['id'], array('verification_status' => 'rejected'))->get_status() === 200, 'Administrator can revoke source verification');
wp_set_current_user($student_a);
check(call_api('GET', 'questions')->get_data()['total'] === 0, 'Revoking source verification hides published references');
check(call_api('GET', 'summary')->get_data()['total'] === 0, 'Summary excludes references after verification revoked');
check(call_api('PUT', 'progress/' . $q['id'], array('status' => 'attempted'))->get_status() === 404, 'Hidden reference cannot receive progress writes');
wp_set_current_user($admin);
call_api('PATCH', 'admin/documents/' . $document['id'], array('verification_status' => 'verified'));
$before = CAFCC_Repository::listing('questions')['total'];
deactivate_plugins($plugin);
check(CAFCC_Repository::listing('questions')['total'] === $before, 'Deactivation preserves academic records');
global $wpdb;
check((int) $wpdb->get_var('SELECT COUNT(*) FROM ' . CAFCC_DB::table('progress')) === 2, 'Deactivation preserves separate student progress');
activate_plugin($plugin);
check(CAFCC_Repository::listing('questions')['total'] === $before, 'Reactivation preserves records without duplication');
if ($legacy_mode) {
    check($wpdb->get_results("SELECT * FROM $legacy_q", ARRAY_A) === $legacy_questions_before &&
        $wpdb->get_results("SELECT * FROM $legacy_p", ARRAY_A) === $legacy_progress_before, 'Reactivation leaves all prototype data untouched');
}
$response = apply_filters('rest_post_dispatch', call_api('GET', 'summary'), $server, new WP_REST_Request('GET', '/cafcc/v1/summary'));
check(str_contains($response->get_headers()['Cache-Control'], 'no-store'), 'REST student data is marked private and no-store');
update_option('cafcc_db_version', '999');
check(call_api('GET', 'summary')->get_status() === 503, 'Incompatible database version blocks API access');
check(is_wp_error(CAFCC_DB::migrate()), 'Database downgrade is refused');
update_option('cafcc_db_version', CAFCC_DB::VERSION);
require __DIR__ . "/v02.php";
require __DIR__ . "/v03.php";
require __DIR__ . "/v04-facets.php";
require __DIR__ . "/v04-studio.php";
require __DIR__ . "/v04-access.php";
require __DIR__ . "/v04-performance.php";
require __DIR__ . "/v041.php";
require __DIR__ . "/v05.php";
require __DIR__ . "/v051.php";
require __DIR__ . "/v052.php";
require __DIR__ . "/v06.php";
require __DIR__ . "/v07.php";
require __DIR__ . "/v08.php";
require __DIR__ . "/v081.php";
require __DIR__ . "/v082.php";
echo "\n$count integration assertions passed on WordPress " . get_bloginfo('version') . ', PHP ' . PHP_VERSION . ".\n";
