<?php
function v4($method,$path,$data=null,$query=array(),$nonce=true){global $server;$r=new WP_REST_Request($method,'/cafcc/v4/'.$path);if($nonce)$r->set_header('X-WP-Nonce',wp_create_nonce('wp_rest'));foreach($query as $k=>$v)$r->set_param($k,$v);if(null!==$data){$r->set_header('Content-Type','application/json');$r->set_body(wp_json_encode($data));}return $server->dispatch($r);}
wp_set_current_user($admin);
$facetdoc=record2('documents',array_merge(array('document_key'=>'TEST-V04-FACET-DOC','edition_id'=>$fr['id'],'title'=>'TEST original facet fixture','source_type'=>'mtp','mtp_series'=>'2','exam_attempt'=>'TEST January 2026','official_url'=>'https://www.icai.org/test-v04-facets.pdf'),$verified));
$facetq=record2('questions',array_merge(array('stable_key'=>'TEST-V04-FACET-Q','edition_id'=>$fr['id'],'primary_subject_id'=>$fr['subject_id'],'document_id'=>$facetdoc['id'],'chapter_node_id'=>$fr11['id'],'title'=>'TEST original concept search fixture','question_number'=>'FACET-1'),$verified));
$facetocc=record2('occurrences',array_merge(array('occurrence_key'=>'TEST-V04-FACET-O','question_id'=>$facetq['id'],'document_id'=>$facetdoc['id'],'edition_id'=>$fr['id'],'question_number'=>'FACET-1','page_reference'=>'TEST authored'),$verified));
foreach(array($t1,$t2) as $tag)record2('tags',array_merge(array('question_id'=>$facetq['id'],'node_id'=>$tag['id']),$verified));
check(v4('POST','admin/aliases',array('node_id'=>$t2['id'],'alias_text'=>'TEST Embedded Derivative Alias','reviewed'=>true))->get_status()===200,'Administrator adds an independently reviewed concept alias');
wp_set_current_user($student_a);
$direct=v4('GET','concepts',null,array('term'=>'TEST Embedded'))->get_data();
check(count($direct['items'])===1 && (int)$direct['items'][0]['id']===(int)$t2['id'],'Student can find an alias globally without selecting subject or edition');
$ancestor_ids=array_column($direct['items'][0]['ancestors'],'id');check(in_array((int)$fr11['id'],$ancestor_ids,true)&&in_array((int)$u4['id'],$ancestor_ids,true),'Direct topic resolves exact chapter and ICAI unit ancestors');
check(v4('GET','questions',null,array('topic_id'=>$t2['id']))->get_data()['total']>=1,'Direct topic selection needs no preceding subject, edition, chapter or unit');
$found=v4('GET','questions',null,array('search'=>'TEST Embedded'))->get_data();check(in_array((int)$facetq['id'],array_map('intval',array_column($found['items'],'id')),true),'Free concept search includes taxonomy aliases instead of incidental case words');
check(v4('GET','questions',null,array('source_type'=>'mtp','exam_attempt'=>'TEST January 2026','topic_id'=>$t2['id']))->get_data()['total']===1,'Attempt and source facets can be combined with a direct topic');
check(v4('GET','questions',null,array('topic_id'=>$t2['id'],'edition_id'=>$afm['id']))->get_status()===400,'Conflicting historical edition cannot silently remap a selected topic');
check(v4('GET','questions',null,array('topic_id'=>'1 OR 1=1'))->get_status()===400,'Facet identifiers reject SQL injection');
check(v4('GET','questions',null,array('search'=>'TEST Embedded'))->get_data()['per_page']===20,'Question occurrence results are server-paginated');
check(v4('POST','admin/aliases',array('node_id'=>$t2['id'],'alias_text'=>'attack'))->get_status()===403,'Student cannot add or approve search aliases');
wp_set_current_user($admin);
