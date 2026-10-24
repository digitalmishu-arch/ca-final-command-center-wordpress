<?php
defined('ABSPATH') || exit;

/** Independent facets; SQL closure joins never load the question corpus into PHP. */
final class CAFCC_Facets {
    public static function init(){add_action('rest_api_init',array(__CLASS__,'routes'));}
    public static function filters($r){
        // Reuse text/id validation, but never demand ancestors before a child.
        $f=CAFCC_Explorer::filters($r);if(is_wp_error($f)){return $f;}
        $f['node_ids']=array();foreach(array('chapter_id','unit_id','topic_id','subtopic_id') as $k){if($f[$k])$f['node_ids'][]=(int)$f[$k];}
        return $f;
    }
    public static function parts($f,$uid){
        global $wpdb;
        $base=$f;foreach(array('chapter_id','unit_id','topic_id','subtopic_id') as $k)$base[$k]=null;$base['search']='';
        list($from,$where,$args)=CAFCC_Explorer::query_parts($base,$uid);
        $t=CAFCC_DB::table('question_tags');$n=CAFCC_DB::table('taxonomy');$cl=CAFCC_Bank_DB::table('closure');$aliases=CAFCC_Bank_DB::table('aliases');
        foreach($f['node_ids']??array() as $id){$where.=" AND EXISTS (SELECT 1 FROM $t bt JOIN $cl bc ON bc.descendant_id=bt.node_id JOIN $n bn ON bn.id=bt.node_id WHERE bt.question_id=q.id AND bc.ancestor_id=%d AND ".CAFCC_Academic::published('bt')." AND ".CAFCC_Academic::published('bn').")";$args[]=$id;}
        if(!empty($f['search'])){$like='%'.$wpdb->esc_like($f['search']).'%';$content=CAFCC_Practice::table('content');
            $where.=" AND (q.title LIKE %s OR q.question_number LIKE %s OR qm.stable_key LIKE %s OR EXISTS (SELECT 1 FROM $content pc WHERE pc.question_id=q.id AND pc.content_kind='question' AND ".CAFCC_Practice::permitted_sql('pc')." AND pc.search_text LIKE %s) OR EXISTS (SELECT 1 FROM $t st JOIN $cl sc ON sc.descendant_id=st.node_id JOIN $n sn ON sn.id=sc.ancestor_id WHERE st.question_id=q.id AND ".CAFCC_Academic::published('st')." AND ".CAFCC_Academic::published('sn')." AND (sn.title LIKE %s OR EXISTS(SELECT 1 FROM $aliases sa WHERE sa.node_id=sn.id AND sa.review_status='verified' AND sa.alias_text LIKE %s))))";
            array_push($args,$like,$like,$like,$like,$like,$like);
        }return array($from,$where,$args);
    }
    public static function node_search($r){
        global $wpdb;$f=self::filters($r);if(is_wp_error($f))return $f;
        $term=$r->get_param('term')??'';$type=$r->get_param('type')??'';
        if(!is_string($term)||strlen($term)>120 || !is_string($type)||($type&&!in_array($type,CAFCC_Academic::NODE_TYPES,true)))return CAFCC_Repository::error('Invalid concept search.');
        $f['search']='';$f['node_ids']=array();foreach(array('chapter_id','unit_id','topic_id','subtopic_id') as $k)$f[$k]=null;
        list($from,$where,$args)=self::parts($f,get_current_user_id());
        $n=CAFCC_DB::table('taxonomy');$e=CAFCC_DB::table('editions');$s=CAFCC_DB::table('subjects');$t=CAFCC_DB::table('question_tags');$cl=CAFCC_Bank_DB::table('closure');$a=CAFCC_Bank_DB::table('aliases');
        $sql="SELECT n.id,n.title,n.node_type,n.edition_id,n.subject_id,n.parent_id,n.heading_origin,e.title AS edition_title,s.code AS subject_code FROM $n n JOIN $e e ON e.id=n.edition_id JOIN $s s ON s.id=n.subject_id WHERE ".CAFCC_Academic::published('n')." AND ".CAFCC_Academic::published('e');$na=array();
        if($term){$sql.=" AND (n.title LIKE %s OR EXISTS(SELECT 1 FROM $a a WHERE a.node_id=n.id AND a.review_status='verified' AND a.alias_text LIKE %s))";$like='%'.$wpdb->esc_like($term).'%';array_push($na,$like,$like);}
        if($type){$sql.=' AND n.node_type=%s';$na[]=$type;}
        if($f['subject_id']){$sql.=' AND n.subject_id=%d';$na[]=$f['subject_id'];}if($f['edition_id']){$sql.=' AND n.edition_id=%d';$na[]=$f['edition_id'];}
        // A published heading is offered only when an eligible published question is tagged beneath it.
        $sql.=" AND EXISTS(SELECT 1 $from JOIN $t nt ON nt.question_id=q.id JOIN $cl nc ON nc.descendant_id=nt.node_id WHERE $where AND nc.ancestor_id=n.id AND ".CAFCC_Academic::published('nt').") ORDER BY n.position,n.id LIMIT 31";array_push($na,...$args);
        $rows=$wpdb->get_results($wpdb->prepare($sql,$na),ARRAY_A);$more=count($rows)>30;$rows=array_slice($rows,0,30);
        $rows=array_values(array_filter($rows,function($r){return CAFCC_Academic::path_published($r['id']);}));
        foreach($rows as &$node){$node['ancestors']=self::context((int)$node['id']);}
        return array('items'=>$rows,'more'=>$more,'availability'=>'Only reviewed paths with eligible question records.');
    }
    public static function context($id){$node=CAFCC_Academic::get('taxonomy',$id);$path=array();if(!$node)return $path;foreach(array_reverse(CAFCC_Explorer::ancestors($node)) as $nid){$r=CAFCC_Academic::get('taxonomy',$nid);$path[]=array('id'=>(int)$nid,'type'=>$r['node_type'],'title'=>$r['title']);}return $path;}
    public static function questions($r){
        global $wpdb;$f=self::filters($r);if(is_wp_error($f))return $f;
        list($from,$where,$args)=self::parts($f,get_current_user_id());$o=CAFCC_DB::table('occurrences');$od=CAFCC_DB::table('documents');$dm=CAFCC_DB::table('document_meta');
        $from.=" JOIN $o bo ON bo.question_id=q.id JOIN $od bd ON bd.id=bo.document_id JOIN $dm bm ON bm.document_id=bd.id";
        $where.=' AND '.CAFCC_Academic::published('bo').' AND '.CAFCC_Academic::published('bm')." AND bd.verification_status='verified'";
        if(class_exists('CAFCC_Studio'))$where.=CAFCC_Studio::occurrence_guard('bo');
        foreach(array('source_type','exam_attempt') as $key){if(!empty($f[$key])){$where.=" AND bd.$key=%s";$args[]=$f[$key];}}
        $total=(int)$wpdb->get_var($wpdb->prepare("SELECT COUNT(*) $from WHERE $where",$args));$qa=$args;array_push($qa,20,($f['page']-1)*20);
        $rows=$wpdb->get_results($wpdb->prepare("SELECT q.id,q.title,q.question_number,c.title AS chapter_title,c.syllabus_version,s.code AS subject_code,qm.edition_id,qm.stable_key,qm.question_type,bo.id AS occurrence_id,COALESCE(p.status,'not_started') AS progress_status $from WHERE $where ORDER BY bo.id DESC LIMIT %d OFFSET %d",$qa),ARRAY_A);
        foreach($rows as &$q){$q['occurrences']=array_values(array_filter(CAFCC_Explorer::occurrences($q['id']),function($o)use($q){return (int)$o['id']===(int)$q['occurrence_id'];}));$q['classifications']=CAFCC_Explorer::tags($q['id']);$q['practice_content']=CAFCC_Practice::public_content((int)$q['id'],'question');$q['notebook']=CAFCC_Practice::notebook((int)$q['id']);$q['legacy_reference']=false;}
        return array('items'=>$rows,'total'=>$total,'per_page'=>20,'page'=>$f['page']);
    }
    public static function summary($r){
        global $wpdb;$f=self::filters($r);if(is_wp_error($f))return $f;list($from,$where,$args)=self::parts($f,get_current_user_id());
        $rows=$wpdb->get_results($wpdb->prepare("SELECT COALESCE(p.status,'not_started') AS status,COUNT(*) AS count $from WHERE $where GROUP BY COALESCE(p.status,'not_started')",$args),ARRAY_A);
        $counts=array_fill_keys(CAFCC_Repository::STATUSES,0);foreach($rows as $row)$counts[$row['status']]=(int)$row['count'];return array('counts'=>$counts,'total'=>array_sum($counts));
    }
    public static function catalog($r){
        global $wpdb;$f=self::filters($r);if(is_wp_error($f))return $f;
        $s=CAFCC_DB::table('subjects');$e=CAFCC_DB::table('editions');$d=CAFCC_DB::table('documents');
        $ed=$wpdb->get_results("SELECT id,title,subject_id,applicability FROM $e e WHERE ".CAFCC_Academic::published('e')." ORDER BY id",ARRAY_A);
        $bf=$f;$bf['source_type']='';$bf['exam_attempt']='';$bf['search']='';$bf['node_ids']=array();
        list($from,$where,$args)=self::parts($bf,get_current_user_id());$o=CAFCC_DB::table('occurrences');$dm=CAFCC_DB::table('document_meta');
        $choices=$wpdb->get_results($wpdb->prepare("SELECT DISTINCT fd.source_type,fd.exam_attempt $from JOIN $o fo ON fo.question_id=q.id JOIN $d fd ON fd.id=fo.document_id JOIN $dm fm ON fm.document_id=fd.id WHERE $where AND ".CAFCC_Academic::published('fo')." AND ".CAFCC_Academic::published('fm')." AND fd.verification_status='verified' ORDER BY fd.exam_attempt DESC",$args),ARRAY_A);
        return array('subjects'=>$wpdb->get_results("SELECT id,code,name FROM $s ORDER BY id",ARRAY_A),'editions'=>$ed,'source_types'=>array_values(array_unique(array_column($choices,'source_type'))),'exam_attempts'=>array_values(array_unique(array_column($choices,'exam_attempt'))));
    }
    public static function alias($data){
        if(!CAFCC_Repository::admin_allowed())return CAFCC_Repository::error('Administrator access required.',403);
        $id=CAFCC_Repository::id($data['node_id']??null);$text=$data['alias_text']??'';
        if(is_wp_error($id)||!CAFCC_Academic::get('taxonomy',$id)||!is_string($text)||!trim($text)||strlen($text)>190)return CAFCC_Repository::error('Choose an existing node and a short alias.');
        global $wpdb;$row=array('node_id'=>$id,'alias_text'=>sanitize_text_field($text),'review_status'=>true===($data['reviewed']??false)?'verified':'needs_review');
        if(false===$wpdb->replace(CAFCC_Bank_DB::table('aliases'),$row))return CAFCC_Repository::error('Cannot save alias.',500);return $row;
    }
    public static function routes(){
        register_rest_route('cafcc/v4','/answers/(?P<id>[1-9][0-9]{0,17})',array('methods'=>'GET','permission_callback'=>function($r){return CAFCC_REST::permission($r);},'callback'=>function($r){return class_exists('CAFCC_Studio')?CAFCC_Studio::answers((int)$r['id'],(int)$r->get_param('occurrence_id')):CAFCC_Explorer::answers((int)$r['id']);}));
        $student=function($r){return CAFCC_REST::permission($r);};$admin=function($r){return CAFCC_REST::permission($r,true);};
        foreach(array('questions','catalog','node_search','summary') as $method)register_rest_route('cafcc/v4','/'.('node_search'===$method?'concepts':$method),array('methods'=>'GET','permission_callback'=>$student,'callback'=>array(__CLASS__,$method)));
        register_rest_route('cafcc/v4','/admin/aliases',array('methods'=>'POST','permission_callback'=>$admin,'callback'=>function($r){return self::alias($r->get_json_params()??array());}));
    }
}
