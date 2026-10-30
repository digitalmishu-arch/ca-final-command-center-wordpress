<?php
/** Authored diagnostics regressions, never an approval of real academic data. */
wp_set_current_user($admin);
CAFCC_Publication_Diagnostics::init();
$diagnostic_id=(int)$wpdb->get_var("SELECT id FROM ".CAFCC_Studio::table()." WHERE stable_id='TEST-V082-COLLECTION-QUESTION'");
$diagnostic_job=mcq_ok(CAFCC_Owner::plan(array('scope'=>'all','ids'=>array($diagnostic_id)),'publish'));
$before_reviews=all_row_digest(CAFCC_Studio::table());$before_rights=all_row_digest(CAFCC_Rights::table());
$diagnostic=mcq_ok(CAFCC_Publication_Diagnostics::page($diagnostic_job['job_key']));
check($diagnostic['selected']===1&&$diagnostic['records'][0]['stable_id']==='TEST-V082-COLLECTION-QUESTION','Diagnostic describes the exact saved selection and stable identity');
check(!isset($diagnostic['records'][0]['question_html'])&&!isset($diagnostic['records'][0]['notes'])&&!isset($diagnostic['records'][0]['rights_scope']),'Diagnostic excludes question prose, student notes and permission details');
check(all_row_digest(CAFCC_Studio::table())===$before_reviews&&all_row_digest(CAFCC_Rights::table())===$before_rights,'Diagnostic does not edit reviews, rights or publication decisions');
check(is_wp_error(CAFCC_Publication_Diagnostics::page($diagnostic_job['job_key'],2)),'Out-of-range diagnostic pages are rejected');
wp_set_current_user($student_a);check(is_wp_error(CAFCC_Publication_Diagnostics::page($diagnostic_job['job_key'])),'Student cannot export publication diagnostics');
$diagnostic_admin=wp_create_user('diagnostic_other_admin','cafcc-disposable-only','other-admin@example.invalid');(new WP_User($diagnostic_admin))->set_role('administrator');wp_set_current_user($diagnostic_admin);check(is_wp_error(CAFCC_Publication_Diagnostics::page($diagnostic_job['job_key'])),'Another administrator cannot export a different owner saved preview');wp_set_current_user($admin);
$empty_review=CAFCC_Studio::get($diagnostic_id);$empty_review['data']['rich_content']=array();$empty_quality=CAFCC_Owner::quality($empty_review);
check(in_array('Complete question text is missing.',$empty_quality['blocks'],true),'Empty question still blocks publication');
check(!in_array('Question HTML contains an invalid table structure.',$empty_quality['blocks'],true)&&!in_array('Question contains a restricted private reference.',$empty_quality['blocks'],true),'Missing content does not fabricate table corruption or private-link diagnoses');
$private_review=$empty_review;$private_review['data']['rich_content']['question']=array('body_html'=>'<p>Private https://drive.google.com/file/d/restricted/view</p>','author_name'=>'Original authored fixture');check(in_array('Question contains a restricted private reference.',CAFCC_Owner::quality($private_review)['blocks'],true),'Actual private references remain blocked');

$current_diagnostic_job=mcq_ok(CAFCC_Owner::plan(array('scope'=>'current'),'publish'));check($current_diagnostic_job['selection']['resolved_package_id']===(int)get_option('cafcc_current_package',0),'Current dataset preview freezes its resolved package identity for diagnostics');
