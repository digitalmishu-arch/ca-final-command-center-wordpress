<?php
defined('ABSPATH') || exit;

final class CAFCC_Explorer {
    /** Applied to v1 reads/writes too: withdrawing new sources/batches cannot leak through old routes. */
    public static function visibility_guard() {
        $dm=CAFCC_DB::table('document_meta'); $qm=CAFCC_DB::table('question_meta');
        return " AND NOT EXISTS (SELECT 1 FROM $dm vdm WHERE vdm.document_id=d.id AND NOT (".CAFCC_Academic::published('vdm')."))
            AND NOT EXISTS (SELECT 1 FROM $qm vqm WHERE vqm.question_id=q.id AND NOT (".CAFCC_Academic::active('vqm')."))";
    }

    public static function has_connections($kind,$id) {
        global $wpdb;
        $deps=array('subjects'=>array('taxonomy'=>'subject_id','editions'=>'subject_id','question_subjects'=>'subject_id'),
            'documents'=>array('document_meta'=>'document_id','occurrences'=>'document_id'), 'questions'=>array('question_meta'=>'question_id','occurrences'=>'question_id','answers'=>'question_id','question_tags'=>'question_id'));
        foreach ($deps[$kind]??array() as $entity=>$field) {
            $table=CAFCC_DB::table($entity);
            if ($wpdb->get_var($wpdb->prepare("SELECT id FROM $table WHERE $field=%d LIMIT 1",$id))) { return true; }
        }
        return false;
    }

    public static function validate_v1_change($kind,$id,$input) {
        if (!self::has_connections($kind,$id)) { return true; }
        $old=CAFCC_Repository::get($kind,$id);
        $allowed=array('subjects'=>array('name'),'documents'=>array('title','exam_attempt','verification_status'),
            'questions'=>array('title','verification_status','publication_status'));
        foreach ($input as $field=>$value) {
            if (is_scalar($value) || null===$value) {
                if ((string)($old[$field]??'')===(string)$value) { continue; }
            }
            if (!in_array($field,$allowed[$kind]??array(),true)) { return CAFCC_Repository::error('This connected record must be corrected through the Version 0.2 manager. Its identity and source location cannot be reassigned through the old endpoint.',409); }
        }
        return true;
    }

    public static function filters($request) {
        $f=array();
        foreach (array('subject_id','edition_id','chapter_id','unit_id','topic_id','subtopic_id') as $key) {
            $f[$key]=CAFCC_Repository::id($request->get_param($key),true);
            if (is_wp_error($f[$key])) { return $f[$key]; }
        }
        $page=$request->get_param('page')??'1';
        if (!is_scalar($page) || !preg_match('/^[1-9][0-9]{0,4}$/D',(string)$page)) { return CAFCC_Repository::error('Invalid page.'); }
        $f['page']=(int)$page;
        foreach (array('search','exam_attempt','source_type') as $key) {
            $value=$request->get_param($key)??'';
            if (!is_string($value) || strlen($value)>120) { return CAFCC_Repository::error('Invalid filter text.'); }
            $f[$key]=sanitize_text_field($value);
        }
        if ($f['source_type'] && !in_array($f['source_type'],array('rtp','mtp','exam','study_material','case_study','other'),true)) { return CAFCC_Repository::error('Invalid source filter.'); }
        $selected=array();
        foreach (array('chapter','unit','topic','subtopic') as $type) {
            $node_id=$f[$type.'_id']; if (!$node_id) { continue; }
            $node=CAFCC_Academic::get('taxonomy',$node_id);
            if (!$node || $node['node_type']!==$type || !CAFCC_Academic::path_published($node_id) ||
                ($f['subject_id'] && (int)$node['subject_id']!==$f['subject_id']) || ($f['edition_id'] && (int)$node['edition_id']!==$f['edition_id'])) {
                return CAFCC_Repository::error('The selected hierarchy path is unavailable or inconsistent.');
            }
            $ancestors=self::ancestors($node);
            foreach ($selected as $previous) { if (!in_array($previous,$ancestors,true)) { return CAFCC_Repository::error('Dependent filters must belong to one connected hierarchy path.'); } }
            $selected[]=(int)$node_id;
        }
        if ($f['edition_id']) {
            $ed=CAFCC_Academic::get('editions',$f['edition_id']);
            if (!CAFCC_Academic::row_published($ed) || ($f['subject_id'] && (int)$ed['subject_id']!==$f['subject_id'])) { return CAFCC_Repository::error('Choose an available edition of this subject.'); }
        }
        return $f;
    }

    public static function ancestors($node) {
        $ids=array((int)$node['id']);
        for ($i=0;!empty($node['parent_id']) && $i<6;$i++) {
            $node=CAFCC_Academic::get('taxonomy',$node['parent_id']); if (!$node) { break; }
            $ids[]=(int)$node['id'];
        }
        return $ids;
    }

    public static function public_nodes($edition_id=null,$subject_id=null) {
        global $wpdb;
        $n=CAFCC_DB::table('taxonomy'); $where=CAFCC_Academic::published('n'); $args=array();
        if ($edition_id) { $where.=' AND n.edition_id=%d'; $args[]=$edition_id; }
        if ($subject_id) { $where.=' AND n.subject_id=%d'; $args[]=$subject_id; }
        $sql="SELECT n.* FROM $n n WHERE $where ORDER BY n.position,n.id LIMIT 10000";
        $rows=$wpdb->get_results($args?$wpdb->prepare($sql,$args):$sql,ARRAY_A);
        return array_values(array_filter($rows,function($row){return CAFCC_Academic::path_published($row['id']);}));
    }

    private static function descendant_ids($id) {
        $node=CAFCC_Academic::get('taxonomy',$id); if (!$node) { return array(); }
        $rows=self::public_nodes($node['edition_id'],$node['subject_id']);
        return array_values(array_map(function($n){return (int)$n['id'];},array_filter($rows,function($n)use($id){return in_array((int)$id,self::ancestors($n),true);} )));
    }

    private static function occurrence_where($o='o',$d='od',$dm='odm') {
        $e=CAFCC_DB::table('editions');
        return CAFCC_Academic::published($o)." AND $d.verification_status='verified' AND $d.official_url<>'' AND ".CAFCC_Academic::published($dm).
            " AND EXISTS (SELECT 1 FROM $e oe WHERE oe.id=$o.edition_id AND ".CAFCC_Academic::published('oe').")";
    }

    public static function query_parts($f,$user_id) {
        global $wpdb;
        $qm=CAFCC_DB::table('question_meta'); $p=CAFCC_DB::table('progress'); $tag=CAFCC_DB::table('question_tags'); $n=CAFCC_DB::table('taxonomy');
        $st=CAFCC_DB::table('question_subjects'); $oc=CAFCC_DB::table('occurrences'); $docs=CAFCC_DB::table('documents'); $dm=CAFCC_DB::table('document_meta'); $ed=CAFCC_DB::table('editions');
        $from=CAFCC_Repository::visible_from()." LEFT JOIN $qm qm ON qm.question_id=q.id LEFT JOIN $p p ON p.question_id=q.id AND p.user_id=%d";
        $where=CAFCC_Repository::visible_where(); $args=array($user_id);
        $tagpub=CAFCC_Academic::published('ft'). ' AND '.CAFCC_Academic::published('fn');
        $where.=" AND (qm.id IS NULL OR (EXISTS (SELECT 1 FROM $ed qe WHERE qe.id=qm.edition_id AND ".CAFCC_Academic::published('qe').") AND EXISTS (SELECT 1 FROM $oc o JOIN $docs od ON od.id=o.document_id JOIN $dm odm ON odm.document_id=od.id WHERE o.question_id=q.id AND ".self::occurrence_where().")))";
        if (!empty($f['subject_id'])) {
            $where.=" AND (COALESCE(qm.primary_subject_id,c.subject_id)=%d OR EXISTS (SELECT 1 FROM $st fs WHERE fs.question_id=q.id AND fs.subject_id=%d AND ".CAFCC_Academic::published('fs').") OR EXISTS (SELECT 1 FROM $tag ft JOIN $n fn ON fn.id=ft.node_id WHERE ft.question_id=q.id AND fn.subject_id=%d AND $tagpub))";
            array_push($args,$f['subject_id'],$f['subject_id'],$f['subject_id']);
        }
        if (!empty($f['edition_id'])) {
            $where.=" AND (qm.edition_id=%d OR EXISTS (SELECT 1 FROM $tag ft JOIN $n fn ON fn.id=ft.node_id WHERE ft.question_id=q.id AND fn.edition_id=%d AND $tagpub))";
            array_push($args,$f['edition_id'],$f['edition_id']);
        }
        $deepest=null;
        foreach (array('chapter_id','unit_id','topic_id','subtopic_id') as $key) { if (!empty($f[$key])) { $deepest=$f[$key]; } }
        if ($deepest) {
            $ids=self::descendant_ids($deepest);
            if (!$ids) { $where.=' AND 1=0'; }
            else {
                $placeholders=implode(',',array_fill(0,count($ids),'%d'));
                $where.=" AND EXISTS (SELECT 1 FROM $tag ft WHERE ft.question_id=q.id AND ft.node_id IN ($placeholders) AND ".CAFCC_Academic::published('ft').")";
                array_push($args,...$ids);
            }
        }
        if (!empty($f['search'])) {
            $like='%'.$wpdb->esc_like($f['search']).'%'; $where.=" AND (q.title LIKE %s OR q.question_number LIKE %s OR qm.stable_key LIKE %s)"; array_push($args,$like,$like,$like);
        }
        if (!empty($f['source_type']) || !empty($f['exam_attempt'])) {
            $occ=''; $old=''; $oa=array(); $la=array();
            foreach (array('source_type','exam_attempt') as $key) {
                if (!empty($f[$key])) { $occ.=" AND od.$key=%s"; $old.=" AND d.$key=%s"; $oa[]=$f[$key]; $la[]=$f[$key]; }
            }
            $where.=" AND ((qm.id IS NULL $old) OR EXISTS (SELECT 1 FROM $oc o JOIN $docs od ON od.id=o.document_id JOIN $dm odm ON odm.document_id=od.id WHERE o.question_id=q.id AND ".self::occurrence_where()." $occ))";
            array_push($args,...$la,...$oa);
        }
        return array($from,$where,$args);
    }

    public static function questions($f,$user_id) {
        global $wpdb;
        list($from,$where,$args)=self::query_parts($f,$user_id);
        $total=(int)$wpdb->get_var($wpdb->prepare("SELECT COUNT(*) $from WHERE $where",$args));
        $sql="SELECT q.id,q.title,q.question_number,c.title AS chapter_title,c.syllabus_version,s.code AS subject_code,
            COALESCE(qm.stable_key,CONCAT('V1-',q.id)) AS stable_key,qm.edition_id,qm.question_type,
            COALESCE(p.status,'not_started') AS progress_status,d.title AS document_title,d.official_url,d.source_type,d.exam_attempt $from WHERE $where ORDER BY q.id DESC LIMIT %d OFFSET %d";
        $args[]=20; $args[]=($f['page']-1)*20;
        $items=$wpdb->get_results($wpdb->prepare($sql,$args),ARRAY_A);
        foreach ($items as &$item) {
            $item['occurrences']=self::occurrences($item['id']);
            $item['legacy_reference']=empty($item['edition_id']);
            $item['classifications']=self::tags($item['id']);
        }
        return array('items'=>$items,'total'=>$total,'per_page'=>20);
    }

    public static function occurrences($id) {
        global $wpdb;
        $o=CAFCC_DB::table('occurrences'); $d=CAFCC_DB::table('documents'); $dm=CAFCC_DB::table('document_meta');
        $where=self::occurrence_where();
        return $wpdb->get_results($wpdb->prepare("SELECT o.id,o.occurrence_key,o.page_reference,o.question_number,o.subquestion_number,
            CASE WHEN o.marks_verified=1 THEN o.marks ELSE NULL END AS marks,o.question_type,od.title,od.official_url,od.exam_attempt,od.source_type,odm.issue_period,odm.mtp_series
            FROM $o o JOIN $d od ON od.id=o.document_id JOIN $dm odm ON odm.document_id=od.id WHERE o.question_id=%d AND $where ORDER BY o.id",$id),ARRAY_A);
    }

    public static function tags($id) {
        global $wpdb; $t=CAFCC_DB::table('question_tags'); $n=CAFCC_DB::table('taxonomy');
        $rows=$wpdb->get_results($wpdb->prepare("SELECT n.id,n.title,n.node_type,n.heading_origin,n.source_url FROM $t t JOIN $n n ON n.id=t.node_id WHERE t.question_id=%d AND ".CAFCC_Academic::published('t')." AND ".CAFCC_Academic::published('n'),$id),ARRAY_A);
        return array_values(array_filter($rows,function($n){return CAFCC_Academic::path_published($n['id']);}));
    }

    public static function summary($f,$user_id) {
        global $wpdb; list($from,$where,$args)=self::query_parts($f,$user_id);
        $rows=$wpdb->get_results($wpdb->prepare("SELECT COALESCE(p.status,'not_started') AS status,COUNT(*) AS count $from WHERE $where GROUP BY COALESCE(p.status,'not_started')",$args),ARRAY_A);
        $counts=array_fill_keys(CAFCC_Repository::STATUSES,0);
        foreach ($rows as $r) { $counts[$r['status']]=(int)$r['count']; }
        return array('counts'=>$counts,'total'=>array_sum($counts));
    }

    public static function catalog($f) {
        global $wpdb; $s=CAFCC_DB::table('subjects'); $e=CAFCC_DB::table('editions');
        $where=CAFCC_Academic::published('e'); $args=array();
        if ($f['subject_id']) { $where.=' AND e.subject_id=%d'; $args[]=$f['subject_id']; }
        $sql="SELECT e.id,e.subject_id,e.title,e.edition_key,e.edition_month,e.reprint_month,e.applicability,e.date_note,e.source_url FROM $e e WHERE $where ORDER BY e.id";
        $editions=$wpdb->get_results($args?$wpdb->prepare($sql,$args):$sql,ARRAY_A);
        $nodes=($f['subject_id'] && $f['edition_id'])?self::public_nodes($f['edition_id'],$f['subject_id']):array();
        $groups=array('chapters'=>array(),'units'=>array(),'topics'=>array(),'subtopics'=>array());
        foreach ($nodes as $node) {
            $anc=self::ancestors($node);
            if ('chapter'===$node['node_type']) { $groups['chapters'][]=$node; }
            elseif ('unit'===$node['node_type'] && $f['chapter_id'] && in_array($f['chapter_id'],$anc,true)) { $groups['units'][]=$node; }
            elseif ('topic'===$node['node_type'] && $f['chapter_id'] && in_array($f['chapter_id'],$anc,true) && (!$f['unit_id'] || in_array($f['unit_id'],$anc,true))) { $groups['topics'][]=$node; }
            elseif ('subtopic'===$node['node_type'] && $f['topic_id'] && in_array($f['topic_id'],$anc,true)) { $groups['subtopics'][]=$node; }
        }
        // Attempt/source choices come from the visible database, never fabricated lists.
        $base=$f; $base['source_type']=''; $base['exam_attempt']=''; list($from,$qwhere,$qa)=self::query_parts($base,get_current_user_id());
        $o=CAFCC_DB::table('occurrences'); $d=CAFCC_DB::table('documents'); $dm=CAFCC_DB::table('document_meta');
        $choices=$wpdb->get_results($wpdb->prepare("SELECT DISTINCT od.source_type,od.exam_attempt $from JOIN $o o ON o.question_id=q.id JOIN $d od ON od.id=o.document_id JOIN $dm odm ON odm.document_id=od.id WHERE $qwhere AND ".self::occurrence_where(),$qa),ARRAY_A);
        $legacy=$wpdb->get_results($wpdb->prepare("SELECT DISTINCT d.source_type,d.exam_attempt $from WHERE $qwhere AND qm.id IS NULL",$qa),ARRAY_A);
        $choices=array_merge($choices,$legacy);
        return array_merge(array('subjects'=>$wpdb->get_results("SELECT id,code,name FROM $s ORDER BY id",ARRAY_A),'editions'=>$editions,
            'exam_attempts'=>array_values(array_unique(array_column($choices,'exam_attempt'))),'source_types'=>array_values(array_unique(array_column($choices,'source_type')))), $groups);
    }

    public static function answers($id) {
        global $wpdb;
        $q=CAFCC_DB::table('questions'); $from=CAFCC_Repository::visible_from(); $where=CAFCC_Repository::visible_where();
        if (!$wpdb->get_var($wpdb->prepare("SELECT q.id $from WHERE $where AND q.id=%d",$id))) { return CAFCC_Repository::error('Published question not found.',404); }
        $a=CAFCC_DB::table('answers');
        $rows=$wpdb->get_results($wpdb->prepare("SELECT a.* FROM $a a WHERE a.question_id=%d AND ".CAFCC_Academic::published('a')." ORDER BY a.id",$id),ARRAY_A);
        $result=array(); $visible_occ=array_map('intval',array_column(self::occurrences($id),'id'));
        foreach ($rows as $row) {
            if ($row['occurrence_id'] && !in_array((int)$row['occurrence_id'],$visible_occ,true)) { continue; }
            if ('official_link'===$row['answer_mode']) {
                $result[]=array('mode'=>'official_link','official_url'=>$row['official_url'],'source_location'=>$row['source_location']);
            } elseif ($row['rights_basis'] && $row['answer_text']) {
                $result[]=array('mode'=>$row['answer_mode'],'answer_text'=>$row['answer_text'],'rights_label'=>'authored'===$row['answer_mode']?'Independently authored solution':'Licensed solution');
            }
        }
        return array('items'=>$result,'empty_message'=>'No reviewed solution is available yet.');
    }
}
