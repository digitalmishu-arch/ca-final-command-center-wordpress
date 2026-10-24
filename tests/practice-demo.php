<?php
/** Authored examples for a disposable preview only; never installed with plugin. */
require '/var/www/html/wp-load.php';
if('cafcc_test'!==DB_NAME || '1'!==getenv('CAFCC_PRACTICE_DEMO')){throw new RuntimeException('Synthetic preview requires the disposable test database and explicit test flag.');}
wp_set_current_user(get_user_by('login','test_admin')->ID);
function demo_record($kind,$data){if($kind==='tags'){global $wpdb;$t=CAFCC_DB::table('question_tags');$id=$wpdb->get_var($wpdb->prepare("SELECT id FROM $t WHERE question_id=%d AND node_id=%d",$data['question_id'],$data['node_id']));if($id)return CAFCC_Academic::get('tags',$id);}$keys=array('taxonomy'=>'node_key','documents'=>'document_key','questions'=>'stable_key','occurrences'=>'occurrence_key');if(isset($keys[$kind])&&isset($data[$keys[$kind]])){$old=CAFCC_Academic::by_key($kind,$data[$keys[$kind]]);if($old)return $old;}$r=CAFCC_Academic::save($kind,$data);if(is_wp_error($r)){throw new RuntimeException($r->get_error_message());}return $r;}
function demo_content($qid,$kind,$html,$options=array()){
    $ct=CAFCC_Practice::table('content');global $wpdb;$old=$wpdb->get_row($wpdb->prepare("SELECT id,revision FROM $ct WHERE question_id=%d AND content_kind=%s",$qid,$kind),ARRAY_A);
    $r=CAFCC_Practice::save(array('expected_revision'=>$old['revision']??0,'question_id'=>$qid,'content_kind'=>$kind,'body_html'=>$html,'mcq_options'=>$options,'rights_type'=>'original',
        'rights_basis'=>'Independently authored synthetic demonstration fixture for this project. No ICAI question or answer text is reproduced.',
        'author_name'=>'CA Final Command Center — authored demo','source_location'=>'Original demonstration; no examination attempt'),$old?(int)$old['id']:0);
    if(is_wp_error($r)){throw new RuntimeException($r->get_error_message());}
    $r=CAFCC_Practice::approve($r['id'],array('expected_revision'=>$r['revision'],'rights_confirmed'=>true));
    if(is_wp_error($r)){throw new RuntimeException($r->get_error_message());}
}
$pub=array('review_status'=>'verified','publication_status'=>'published');
$examples=array(
    array('subject'=>'FR','edition'=>'fr-may2026','chapter'=>'fr-may2026-m2-ch5','unit'=>'fr-may2026-m2-ch5-u2','topic'=>'Straight-line depreciation — authored demo','title'=>'Original demo · Find the annual depreciation charge',
        'question'=>'<p><strong>Independently authored synthetic practice. This is not an ICAI examination question.</strong></p><p>A machine has the following assumed inputs. Using the straight-line method, calculate its annual depreciation charge.</p><table><caption>Given inputs</caption><thead><tr><th scope="col">Input</th><th scope="col">Amount</th></tr></thead><tbody><tr><td>Cost</td><td>₹1,000</td></tr><tr><td>Residual value</td><td>₹100</td></tr><tr><td>Useful life</td><td>3 years</td></tr></tbody></table><p>Select an option, then open the answer when you are ready.</p>',
        'answer'=>'<h3>Work through the calculation</h3><p>Depreciable amount = cost − residual value.</p><table><tr><th scope="row">Depreciable amount</th><td>₹1,000 − ₹100 = ₹900</td></tr><tr><th scope="row">Annual charge</th><td>₹900 ÷ 3 = ₹300</td></tr></table><math display="block"><mrow><mfrac><mrow><mn>1000</mn><mo>−</mo><mn>100</mn></mrow><mn>3</mn></mfrac><mo>=</mo><mn>300</mn></mrow></math><p>Option B. Independently authored solution, not an official answer.</p>',
        'options'=>array(array('key'=>'A','text'=>'₹250'),array('key'=>'B','text'=>'₹300'),array('key'=>'C','text'=>'₹350'))),
    array('subject'=>'AFM','edition'=>'afm-may2026','chapter'=>'afm-may2026-ch3','unit'=>'','topic'=>'Time value of money — authored demo','title'=>'Original demo · Compare a one-period future value',
        'question'=>'<p><strong>Independently authored synthetic practice. No examination attempt.</strong></p><p>Assume a principal of ₹2,000 earns a stated return of 5% for one period, with no fees or taxes. Calculate its future value.</p><pre>Future value = principal × (1 + rate)</pre>',
        'answer'=>'<h3>One-period calculation</h3><p>₹2,000 × 1.05 = ₹2,100.</p><p>The increase is ₹100. These assumptions belong to this authored arithmetic demonstration.</p>','options'=>array())
);
foreach($examples as $i=>$e){
    $edition=CAFCC_Academic::by_key('editions',$e['edition']);$chapter=CAFCC_Academic::by_key('taxonomy',$e['chapter']);$parent=$e['unit']?CAFCC_Academic::by_key('taxonomy',$e['unit']):$chapter;
    $topic=demo_record('taxonomy',array_merge(array('node_key'=>'ORIGINAL-DEMO-TOPIC-'.$i,'edition_id'=>$edition['id'],'subject_id'=>$edition['subject_id'],'parent_id'=>$parent['id'],'node_type'=>'topic','title'=>$e['topic'],'heading_origin'=>'editorial'),$pub));
    $sub=demo_record('taxonomy',array_merge(array('node_key'=>'ORIGINAL-DEMO-SUB-'.$i,'edition_id'=>$edition['id'],'subject_id'=>$edition['subject_id'],'parent_id'=>$topic['id'],'node_type'=>'subtopic','title'=>'Calculate the stated example','heading_origin'=>'editorial'),$pub));
    $doc=demo_record('documents',array_merge(array('document_key'=>'ORIGINAL-DEMO-DOC-'.$i,'edition_id'=>$edition['id'],'title'=>'Authored demo — ICAI link is syllabus background only','source_type'=>'other','exam_attempt'=>'Original demonstration — no examination attempt','official_url'=>'https://www.icai.org/post/bos-knowledge-portal'),$pub));
    $q=demo_record('questions',array_merge(array('stable_key'=>'ORIGINAL-DEMO-QUESTION-'.$i,'edition_id'=>$edition['id'],'primary_subject_id'=>$edition['subject_id'],'document_id'=>$doc['id'],'chapter_node_id'=>$chapter['id'],'title'=>$e['title'],'question_number'=>'DEMO-'.($i+1),'question_type'=>'practical'),$pub));
    $occ=demo_record('occurrences',array_merge(array('occurrence_key'=>'ORIGINAL-DEMO-OCC-'.$i,'question_id'=>$q['id'],'document_id'=>$doc['id'],'edition_id'=>$edition['id'],'question_number'=>'DEMO-'.($i+1),'page_reference'=>'Original web demonstration, no PDF'),$pub));
    demo_record('tags',array_merge(array('question_id'=>$q['id'],'node_id'=>$sub['id']),$pub));
    demo_content($q['id'],'question',$e['question'],array());demo_content($q['id'],'answer',$e['answer']);
    if(class_exists('CAFCC_Studio')){
        $rt=CAFCC_Studio::table();$rid=$wpdb->get_var($wpdb->prepare("SELECT id FROM $rt WHERE occurrence_id=%d",$occ['id']));$r=$rid?CAFCC_Studio::get($rid):CAFCC_Studio::adopt($occ['id'],array('source_hash'=>hash('sha256',$e['question']),'section'=>'authored_demo'));if(is_wp_error($r))throw new RuntimeException($r->get_error_message());$d=$r['data'];$d['question_page']=$occ['page_reference'];$d['scheme']='Independently authored synthetic demonstration';$d['reasoning']='This authored arithmetic fixture is intentionally placed by the test author; it is not an ICAI classification.';$d['rights_mode']='original';$d['rights_basis']='Independently authored by this project; no copied ICAI prose.';$d['question_coordinates']=array('format'=>'original_web_fixture','location'=>'Question card body');$ct=CAFCC_Practice::table('content');$body=$wpdb->get_var($wpdb->prepare("SELECT body_html FROM $ct WHERE question_id=%d AND content_kind='answer'",$q['id']));$d['answer']=array('mode'=>'original','source_hash'=>hash('sha256',$body),'reference'=>$d['reference'],'subreference'=>'','page'=>'Original authored solution panel','question_identity'=>$d['stable_id'],'question_reference'=>$d['reference'],'question_subreference'=>'');
        $r=CAFCC_Studio::save($r['id'],array('expected_revision'=>$r['revision'],'data'=>$d));if(is_wp_error($r))throw new RuntimeException($r->get_error_message());foreach(array_merge(CAFCC_Studio::STAGES,array('publish')) as $action){$r=CAFCC_Studio::decision($r['id'],array('expected_revision'=>$r['revision'],'action'=>$action,'confirmed'=>true));if(is_wp_error($r))throw new RuntimeException($action.': '.$r->get_error_message());}
    }

}
echo "Two independently authored local examples ready. No ICAI prose or fabricated examination data.\n";
