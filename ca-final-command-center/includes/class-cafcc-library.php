<?php
defined('ABSPATH') || exit;

/** Private, paginated revision metadata. Question and answer bodies have separate gates. */
final class CAFCC_Library {
    const MODES=array('all','important','bookmarks','notes','needs_revision','timed','attempt_history','attempted','completed','solved_independently','read','highlighted','difficult');
    public static function allowed(){return CAFCC_Access::eligible() ? true : CAFCC_Repository::error('Current student access is required.',403);}
    public static function filters($request){
        $f=array();
        foreach(array('tab'=>'all','search'=>'','subject'=>'','source'=>'','attempt'=>'','series'=>'','date'=>'','session_status'=>'','topic_id'=>'','sort'=>'recent','direction'=>'desc','archive'=>'all') as $key=>$default){
            $v=$request->get_param($key)??$default;
            if(!is_string($v)||strlen($v)>190)return CAFCC_Repository::error('Invalid practice filter.');
            $f[$key]=sanitize_text_field($v);
        }
        if(!in_array($f['tab'],self::MODES,true)||!in_array($f['sort'],array('recent','source','attempt','question','duration','count','first','latest','best'),true)||!in_array($f['direction'],array('asc','desc'),true))return CAFCC_Repository::error('Choose an available practice view.');
        if(!in_array($f['archive'],array('active','all','archived'),true))return CAFCC_Repository::error('Choose an available archive view.');
        if($f['subject']&&!in_array($f['subject'],array('FR','AFM','AUDIT','DT','IDT','IBS'),true))return CAFCC_Repository::error('Choose an available subject.');
        if($f['source']&&!in_array($f['source'],CAFCC_Repository::SOURCES,true))return CAFCC_Repository::error('Choose an available source.');
        if($f['series']&&!in_array($f['series'],array('I','II'),true))return CAFCC_Repository::error('Choose an MTP series.');
        if(!in_array($f['session_status'],array('','running','paused','finished'),true))return CAFCC_Repository::error('Invalid session status.');
        if($f['date']&&$f['date']!=='today'&&!preg_match('/^\d{4}-\d{2}-\d{2}$/D',$f['date']))return CAFCC_Repository::error('Use a date in YYYY-MM-DD format.');
        if($f['topic_id']&&(!preg_match('/^[1-9][0-9]{0,17}$/D',$f['topic_id'])||!CAFCC_Academic::path_published((int)$f['topic_id'])))return CAFCC_Repository::error('This topic is unavailable.');
        $page=$request->get_param('page')??1;if(!is_scalar($page)||!preg_match('/^[1-9][0-9]{0,5}$/D',(string)$page))return CAFCC_Repository::error('Invalid page.');$f['page']=(int)$page;
        return $f;
    }
    private static function date_bounds($date){
        if(!$date)return null;
        $day=$date==='today'?current_datetime()->setTime(0,0):DateTimeImmutable::createFromFormat('!Y-m-d',$date,wp_timezone());
        if(!$day||($date!=='today'&&$day->format('Y-m-d')!==$date))return false;
        return array($day->getTimestamp(),$day->modify('+1 day')->getTimestamp());
    }
    /** Every personal join is scoped to the authenticated user, never a request user ID. */
    public static function query($f){
        global $wpdb;$uid=(int)get_current_user_id();$q=CAFCC_DB::table('questions');$qm=CAFCC_DB::table('question_meta');$o=CAFCC_DB::table('occurrences');$d=CAFCC_DB::table('documents');$dm=CAFCC_DB::table('document_meta');$sub=CAFCC_DB::table('subjects');$ch=CAFCC_DB::table('chapters');$p=CAFCC_DB::table('progress');$np=CAFCC_Practice::table('notebook');$sp=CAFCC_Study::table('personal');$ss=CAFCC_Study::table('sessions');$hi=CAFCC_Study::table('highlights');
        $timed=$f['tab']==='timed';
        $from="FROM $q q LEFT JOIN $qm qm ON qm.question_id=q.id JOIN $ch chapter ON chapter.id=q.chapter_id JOIN $sub subject ON subject.id=chapter.subject_id LEFT JOIN $o occ ON occ.question_id=q.id LEFT JOIN $d doc ON doc.id=occ.document_id LEFT JOIN $dm meta ON meta.document_id=doc.id LEFT JOIN $p progress ON progress.question_id=q.id AND progress.user_id=$uid LEFT JOIN $np notebook ON notebook.question_id=q.id AND notebook.user_id=$uid LEFT JOIN $sp personal ON personal.occurrence_id=occ.id AND personal.user_id=$uid";
        $from.=$timed?" JOIN $ss session ON session.occurrence_id=occ.id AND session.user_id=$uid":" LEFT JOIN $ss session ON session.id=(SELECT latest.id FROM $ss latest WHERE latest.occurrence_id=occ.id AND latest.user_id=$uid ORDER BY latest.attempt_number DESC LIMIT 1)";
        $outcome="COALESCE(personal.outcome,progress.status,'not_started')";
        $saved="(personal.id IS NOT NULL OR progress.question_id IS NOT NULL OR notebook.bookmarked=1 OR notebook.note_text<>'' OR session.id IS NOT NULL OR EXISTS(SELECT 1 FROM $hi h WHERE h.user_id=$uid AND h.occurrence_id=occ.id))";
        $where=$saved;$args=array();
        if(in_array($f['tab'],array('timed','all'),true)&&($f['archive']??'active')!=='all'){$hidden=CAFCC_Saved::hidden_sql($timed?'session':'saved',$timed?'session.id':'q.id');$where.=' AND '.(($f['archive']??'active')==='archived'?$hidden:'NOT '.$hidden);}
        $tag=function($label)use($wpdb,$sp,$uid){return $wpdb->prepare("EXISTS(SELECT 1 FROM $sp tagged WHERE tagged.user_id=%d AND tagged.occurrence_id=occ.id AND JSON_CONTAINS(tagged.tags_json,JSON_QUOTE(%s)))",$uid,$label);};
        switch($f['tab']){
            case 'important':$where.=' AND '.$tag('Important');break;
            case 'difficult':$where.=' AND '.$tag('Difficult');break;
            case 'bookmarks':$where.=' AND notebook.bookmarked=1';break;
            case 'notes':$where.=" AND notebook.note_text<>''";break;
            case 'needs_revision':$where.=" AND $outcome='needs_revision'";break;
            case 'attempted':$where.=" AND ($outcome IN ('attempted','needs_revision','completed','solved_independently') OR session.id IS NOT NULL)";break;
            case 'completed':$where.=" AND $outcome IN ('completed','solved_independently')";break;
            case 'solved_independently':$where.=" AND $outcome='solved_independently'";break;
            case 'read':$where.=" AND (personal.read_at IS NOT NULL OR $outcome='read')";break;
            case 'highlighted':$where.=" AND EXISTS(SELECT 1 FROM $hi h WHERE h.user_id=$uid AND h.occurrence_id=occ.id)";break;
        }
        foreach(array('subject'=>'subject.code','source'=>'doc.source_type','attempt'=>'doc.exam_attempt','series'=>'meta.mtp_series') as $filter=>$col)if($f[$filter]){$where.=" AND $col=%s";$args[]=$f[$filter];}
        if($f['topic_id']){$where.=' AND EXISTS(SELECT 1 FROM '.CAFCC_DB::table('question_tags').' tmap JOIN '.CAFCC_Bank_DB::table('closure').' tpath ON tpath.descendant_id=tmap.node_id WHERE tmap.question_id=q.id AND tpath.ancestor_id=%d)';$args[]=(int)$f['topic_id'];}
        if($f['search']){$term='%'.$wpdb->esc_like($f['search']).'%';$where.=" AND (qm.stable_key LIKE %s OR q.question_number LIKE %s OR notebook.note_text LIKE %s OR personal.tags_json LIKE %s OR q.title LIKE %s OR EXISTS(SELECT 1 FROM ".CAFCC_Studio::table()." saved_identity WHERE saved_identity.question_id=q.id AND saved_identity.occurrence_id=occ.id AND saved_identity.stable_id LIKE %s))";array_push($args,$term,$term,$term,$term,$term,$term);}
        if($f['session_status']){$where.=' AND session.status=%s';$args[]=$f['session_status'];}
        $bounds=self::date_bounds($f['date']);if($bounds===false)return CAFCC_Repository::error('Invalid calendar date.');if($bounds){$where.=' AND session.started_at>=%d AND session.started_at<%d';array_push($args,...$bounds);}
        return array($from,$where,$args,$outcome);
    }
    private static function prepare($sql,$args){global $wpdb;return $args?$wpdb->prepare($sql,$args):$sql;}
    public static function list($request){
        if(is_wp_error($e=self::allowed()))return $e;$f=self::filters($request);if(is_wp_error($f))return $f;if($request->get_param('archive')===null)$f['archive']='active';if($f['tab']==='attempt_history')return self::attempt_history($f);$query=self::query($f);if(is_wp_error($query))return $query;[$from,$where,$args,$outcome]=$query;global $wpdb;
        $total=(int)$wpdb->get_var(self::prepare("SELECT COUNT(*) $from WHERE $where",$args));$unique=(int)$wpdb->get_var(self::prepare("SELECT COUNT(DISTINCT q.id) $from WHERE $where",$args));
        $order=array('recent'=>'COALESCE(session.started_at,UNIX_TIMESTAMP(personal.modified_at),UNIX_TIMESTAMP(notebook.updated_at),0)','source'=>'doc.source_type','attempt'=>'doc.exam_attempt','question'=>'q.question_number','duration'=>'session.active_seconds')[$f['sort']]??'q.id';$dir=strtoupper($f['direction']);$limit=$args;array_push($limit,20,($f['page']-1)*20);
        $cols="q.id AS question_id,COALESCE(occ.id,0) AS occurrence_id,qm.stable_key,subject.code AS subject,doc.source_type AS source,doc.exam_attempt AS attempt,meta.mtp_series AS series,COALESCE(occ.question_number,q.question_number) AS reference,COALESCE(occ.subquestion_number,'') AS subpart,occ.document_section,$outcome AS outcome,COALESCE(notebook.note_text,'') AS note,COALESCE(notebook.bookmarked,0) AS bookmarked,COALESCE(personal.tags_json,'[]') AS tags_json,personal.read_at,session.id AS session_id,session.attempt_number,session.status AS session_status,session.outcome AS session_outcome,session.started_at,session.ended_at,session.active_seconds,session.last_tick";
        $rows=$wpdb->get_results(self::prepare("SELECT $cols $from WHERE $where ORDER BY $order $dir,q.id DESC LIMIT %d OFFSET %d",$limit),ARRAY_A);
        foreach($rows as &$row){
            $row['question_id']=(int)$row['question_id'];$row['occurrence_id']=(int)$row['occurrence_id'];$row['tags']=json_decode($row['tags_json'],true);unset($row['tags_json']);$row['bookmarked']=(bool)$row['bookmarked'];$row['note_hash']=hash('sha256',$row['note']);$row['available']=$row['occurrence_id']&&CAFCC_Study::eligible($row['question_id'],$row['occurrence_id']);$row['snippet']='Question currently unavailable; your private activity is retained.';
            if($row['available']){$pc=CAFCC_Practice::table('content');$row['snippet']=$wpdb->get_var($wpdb->prepare("SELECT SUBSTRING_INDEX(TRIM(REPLACE(REPLACE(search_text,CHAR(10),' '),CHAR(13),' ')),' ',15) FROM $pc pc WHERE pc.question_id=%d AND content_kind='question' AND ".CAFCC_Practice::permitted_sql('pc')." LIMIT 1",$row['question_id']))?:'Published question reference';}
            $row['active_seconds']=(int)$row['active_seconds']+($row['session_status']==='running'?max(0,time()-(int)$row['last_tick']):0);$row['source_label']=self::source_label($row['source'],$row['series']);$row['question_label']=CAFCC_Experience::reference_label($row['reference'],$row['subpart'],$row['document_section']);unset($row['last_tick']);CAFCC_Saved::decorate($row);
        }
        $sum=$wpdb->get_row(self::prepare("SELECT COALESCE(SUM(session.active_seconds+CASE WHEN session.status='running' THEN GREATEST(0,".(int)time()."-session.last_tick) ELSE 0 END),0) AS active_seconds $from WHERE $where",$args),ARRAY_A);
        return array('items'=>$rows,'total'=>$total,'unique_questions'=>$unique,'per_page'=>20,'page'=>$f['page'],'tab'=>$f['tab'],'active_seconds'=>(int)$sum['active_seconds'],'count_basis'=>$f['tab']==='timed'?'Timer sessions; unique question count is separate.':'Saved source-occurrence records; retained unavailable records contain no academic prose.');
    }
    public static function attempt_history($f){
        global $wpdb;$f['archive']='all';[$from,$where,$args]=self::query($f);$sessions=CAFCC_Study::table('sessions');$uid=(int)get_current_user_id();
        $from.=" JOIN (SELECT question_id,occurrence_id,COUNT(*) AS completed,MIN(active_seconds) AS best_seconds,AVG(active_seconds) AS average_seconds,SUBSTRING_INDEX(GROUP_CONCAT(active_seconds ORDER BY attempt_number ASC),',',1) AS first_seconds,SUBSTRING_INDEX(GROUP_CONCAT(active_seconds ORDER BY attempt_number DESC),',',1) AS latest_seconds,MAX(started_at) AS latest_at FROM $sessions WHERE user_id=$uid AND status='finished' GROUP BY question_id,occurrence_id) history ON history.question_id=q.id AND history.occurrence_id=occ.id";
        $prep=function($sql,$a)use($wpdb){return $a?$wpdb->prepare($sql,$a):$sql;};$total=(int)$wpdb->get_var($prep("SELECT COUNT(*) $from WHERE $where",$args));
        $order=array('recent'=>'history.latest_at','source'=>'doc.source_type','attempt'=>'doc.exam_attempt','question'=>'q.question_number','duration'=>'history.average_seconds','count'=>'history.completed','first'=>'history.first_seconds+0','latest'=>'history.latest_seconds+0','best'=>'history.best_seconds')[$f['sort']];$direction=strtoupper($f['direction']);$params=$args;array_push($params,20,($f['page']-1)*20);
        $rows=$wpdb->get_results($prep("SELECT q.id AS question_id,occ.id AS occurrence_id,subject.code AS subject,doc.source_type AS source,doc.exam_attempt AS attempt,meta.mtp_series AS series,COALESCE(occ.question_number,q.question_number) AS reference,occ.subquestion_number AS subpart,occ.document_section,history.* $from WHERE $where ORDER BY $order $direction,occ.id ASC LIMIT %d OFFSET %d",$params),ARRAY_A);
        foreach($rows as &$row){$row['available']=CAFCC_Study::eligible($row['question_id'],$row['occurrence_id']);$row['source_label']=self::source_label($row['source'],$row['series']);$row['question_label']=CAFCC_Experience::reference_label($row['reference'],$row['subpart'],$row['document_section']);$row['snippet']='Question currently unavailable; your private history is retained.';if($row['available']){$pc=CAFCC_Practice::table('content');$row['snippet']=$wpdb->get_var($wpdb->prepare("SELECT SUBSTRING_INDEX(TRIM(REPLACE(REPLACE(search_text,CHAR(10),' '),CHAR(13),' ')),' ',15) FROM $pc pc WHERE question_id=%d AND content_kind='question' AND ".CAFCC_Practice::permitted_sql('pc')." LIMIT 1",$row['question_id']))?:'Published question reference';}}
        return array('items'=>$rows,'total'=>$total,'unique_questions'=>$total,'per_page'=>20,'page'=>$f['page'],'tab'=>'attempt_history','note'=>'All completed sessions, including archived sessions. A faster time is not proof of correctness or mastery.');
    }
    public static function source_label($source,$series){return $source==='mtp'?'MTP'.($series?' Series '.$series:''):($source==='exam'?'Examination':strtoupper($source?:'Source'));}
    public static function question($request){
        if(is_wp_error($e=self::allowed()))return $e;$qid=CAFCC_Repository::id($request['id']);$oid=CAFCC_Repository::id($request->get_param('occurrence_id'));if(is_wp_error($qid)||is_wp_error($oid))return CAFCC_Repository::error('Select an exact question and source occurrence.');
        global $wpdb;$r=new WP_REST_Request('GET');$f=CAFCC_Facets::filters($r);[$from,$where,$args]=CAFCC_Facets::occurrence_parts($f,get_current_user_id());$args[]=$qid;$args[]=$oid;
        $row=$wpdb->get_row(self::prepare("SELECT q.id,q.title,q.question_number,c.title AS chapter_title,c.syllabus_version,s.code AS subject_code,qm.edition_id,qm.stable_key,qm.question_type,bo.id AS occurrence_id,COALESCE(p.status,'not_started') AS progress_status $from WHERE $where AND q.id=%d AND bo.id=%d",$args),ARRAY_A);
        if(!$row)return CAFCC_Repository::error('This question is unavailable; your saved history remains.',404);$cards=CAFCC_Facets::hydrate(array($row));return $cards[0];
    }
    public static function save_note($request){
        if(is_wp_error($e=self::allowed()))return $e;$d=CAFCC_Studio::body($request,16000);if(is_wp_error($d))return $d;
        if(array_diff(array_keys($d),array('note','expected_hash'))||!is_string($d['note']??null)||strlen($d['note'])>10000||!preg_match('/^[a-f0-9]{64}$/D',$d['expected_hash']??''))return CAFCC_Repository::error('Use a bounded private note and its current revision.');
        $qid=CAFCC_Repository::id($request['id']);if(is_wp_error($qid))return $qid;
        return CAFCC_Academic::transaction(function()use($qid,$d){global $wpdb;$t=CAFCC_Practice::table('notebook');$uid=get_current_user_id();$row=$wpdb->get_row($wpdb->prepare("SELECT * FROM $t WHERE user_id=%d AND question_id=%d FOR UPDATE",$uid,$qid),ARRAY_A);
            if(!$row)return CAFCC_Repository::error('Saved private note not found.',404);if(!hash_equals(hash('sha256',$row['note_text']),$d['expected_hash']))return CAFCC_Repository::error('Your note changed in another tab. Reload before saving.',409);
            $note=sanitize_textarea_field($d['note']);if(false===$wpdb->update($t,array('note_text'=>$note,'updated_at'=>current_time('mysql',true)),array('user_id'=>$uid,'question_id'=>$qid)))return CAFCC_Repository::error('Cannot save your note.',500);return array('note'=>$note,'note_hash'=>hash('sha256',$note));
        });
    }
    public static function history($request){
        if(is_wp_error($e=self::allowed()))return $e;$qid=CAFCC_Repository::id($request['id']);$oid=CAFCC_Repository::id($request->get_param('occurrence_id'));if(is_wp_error($qid)||is_wp_error($oid))return CAFCC_Repository::error('Select the exact occurrence.');global $wpdb;$t=CAFCC_Study::table('sessions');$uid=get_current_user_id();$page=max(1,(int)($request->get_param('page')??1));if($page>10000)return CAFCC_Repository::error('Invalid history page.');
        $only=$request->get_param('completed_only')==='1'?" AND status='finished'":'';
        $rows=$wpdb->get_results($wpdb->prepare("SELECT id,attempt_number,status,outcome,started_at,ended_at,active_seconds,paused_seconds,last_tick FROM $t WHERE user_id=%d AND question_id=%d AND occurrence_id=%d $only ORDER BY attempt_number ASC LIMIT 50 OFFSET %d",$uid,$qid,$oid,($page-1)*50),ARRAY_A);
        $stats=$wpdb->get_row($wpdb->prepare("SELECT COUNT(*) AS completed,MIN(active_seconds) AS best_seconds,AVG(active_seconds) AS average_seconds FROM $t WHERE user_id=%d AND question_id=%d AND occurrence_id=%d AND status='finished'",$uid,$qid,$oid),ARRAY_A);
        $times=$wpdb->get_col($wpdb->prepare("(SELECT active_seconds FROM $t WHERE user_id=%d AND question_id=%d AND occurrence_id=%d AND status='finished' ORDER BY attempt_number ASC LIMIT 1) UNION ALL (SELECT active_seconds FROM $t WHERE user_id=%d AND question_id=%d AND occurrence_id=%d AND status='finished' ORDER BY attempt_number DESC LIMIT 1)",$uid,$qid,$oid,$uid,$qid,$oid));
        $stats['first_seconds']=isset($times[0])?(int)$times[0]:null;$stats['latest_seconds']=isset($times[1])?(int)$times[1]:null;$stats['difference_seconds']=count($times)===2?(int)$times[1]-(int)$times[0]:null;
        foreach($rows as &$row){$row['active_seconds']=(int)$row['active_seconds']+($row['status']==='running'?max(0,time()-(int)$row['last_tick']):0);$row['archived']=(bool)$wpdb->get_var("SELECT ".CAFCC_Saved::hidden_sql('session',(int)$row['id']));unset($row['last_tick']);}
        return array('items'=>$rows,'page'=>$page,'per_page'=>50,'comparison'=>$stats,'note'=>'Finished sessions only are compared. Less time does not establish correctness or mastery.');
    }
    public static function dashboard($request){
        if(is_wp_error($e=self::allowed()))return $e;$cards=array();
        $definitions=array('all'=>'Saved Practice Records','read'=>'Questions Viewed','attempted'=>'Questions Attempted','completed'=>'Completed Questions','solved_independently'=>'Solved Independently','needs_revision'=>'Needs Revision','important'=>'Important','bookmarks'=>'Bookmarks','notes'=>'Private Notes');
        foreach($definitions as $tab=>$title){$r=clone $request;$r->set_param('tab',$tab);if($tab==='all')$r->set_param('archive','active');$f=self::filters($r);if(is_wp_error($f))return $f;$query=self::query($f);if(is_wp_error($query))return $query;[$from,$where,$args]=$query;global $wpdb;$value=(int)$wpdb->get_var(self::prepare("SELECT COUNT(*) $from WHERE $where",$args));$cards[]=array('key'=>$tab,'label'=>$title,'value'=>$value,'url'=>self::practice_url($f));}
        foreach(array('today','all_time','finished') as $mode){$r=clone $request;$r->set_param('tab','timed');$r->set_param('archive','all');if($mode==='today')$r->set_param('date','today');if($mode==='finished')$r->set_param('session_status','finished');$r->set_param('archive','all');$f=self::filters($r);if(is_wp_error($f))return $f;[$from,$where,$args]=self::query($f);$stats=$wpdb->get_row(self::prepare("SELECT COUNT(*) AS sessions,COUNT(DISTINCT q.id) AS questions,COALESCE(SUM(session.active_seconds+CASE WHEN session.status='running' THEN GREATEST(0,".(int)time()."-session.last_tick) ELSE 0 END),0) AS seconds,COALESCE(AVG(session.active_seconds),0) AS average_seconds $from WHERE $where",$args),ARRAY_A);
            if($mode==='today')$cards[]=array('key'=>'practised_today','label'=>'Questions Practised Today','value'=>(int)$stats['questions'],'detail'=>(int)$stats['sessions'].' sessions','url'=>self::practice_url($f));
            if($mode==='all_time')$cards[]=array('key'=>'practice_time','label'=>'Total Active Practice Time','value'=>(int)$stats['seconds'],'format'=>'duration','url'=>self::practice_url($f));
            if($mode==='finished'){$cards[]=array('key'=>'finished_sessions','label'=>'Finished Timer Sessions','value'=>(int)$stats['sessions'],'url'=>self::practice_url($f));$cards[]=array('key'=>'average_time','label'=>'Average Finished Session Time','value'=>(int)round($stats['average_seconds']),'format'=>'duration','url'=>self::practice_url($f));}
        }
        $recent_request=clone $request;$recent_request->set_param('tab','timed');$recent=self::list($recent_request);
        $_activity=self::activity($request);return array('preparation'=>CAFCC_Planner::preparation(),'activity'=>$_activity,'cards'=>$cards,'recent_sessions'=>is_wp_error($recent)?array():array_slice($recent['items'],0,5),'mcq'=>class_exists('CAFCC_MCQ_Student')?CAFCC_MCQ_Student::metrics():null,'note'=>'Subjective results are your own assessment. MCQ correctness is scored separately. Lifetime time metrics include archived timer sessions. Hidden saved-list entries remain in their other collections. Withdrawn academic text is never returned.');
    }
    public static function activity($request){
        global $wpdb;$r=clone $request;$r->set_param('tab','timed');$r->set_param('session_status','finished');$f=self::filters($r);if(is_wp_error($f))return array();[$from,$w,$a]=self::query($f);$sources=$wpdb->get_results(self::prepare("SELECT doc.source_type,meta.mtp_series,COUNT(session.id) AS sessions,COUNT(DISTINCT q.id) AS questions,SUM(session.active_seconds) AS seconds $from WHERE $w GROUP BY doc.source_type,meta.mtp_series",$a),ARRAY_A);foreach($sources as &$source){$sf=$f;$sf['source']=$source['source_type'];$sf['series']=$source['mtp_series'];$source['url']=self::practice_url($sf);$source['label']=self::source_label($source['source_type'],$source['mtp_series']);}unset($source);$tags=CAFCC_DB::table('question_tags');$tax=CAFCC_DB::table('taxonomy');$topics=$wpdb->get_results(self::prepare("SELECT topic.id,topic.title,COUNT(DISTINCT session.id) AS sessions,COUNT(DISTINCT q.id) AS questions,SUM(session.active_seconds) AS seconds $from JOIN $tags activity_tag ON activity_tag.question_id=q.id JOIN $tax topic ON topic.id=activity_tag.node_id WHERE $w AND topic.node_type IN ('topic','subtopic') GROUP BY topic.id,topic.title ORDER BY seconds DESC LIMIT 30",$a),ARRAY_A);$public=array();foreach($topics as $topic)if(CAFCC_Academic::path_published($topic['id'])){$tf=$f;$tf['topic_id']=(string)$topic['id'];$topic['url']=self::practice_url($tf);$public[]=$topic;}return array('sources'=>$sources,'topics'=>$public,'note'=>'Finished sessions only. Multiple topic tags can describe the same session; topic rows are not additive and do not measure mastery.');
    }
    public static function practice_url($f){$args=array('cafcc_view'=>'practice');foreach(array('tab','subject','source','attempt','series','date','session_status','topic_id','archive') as $k)if(!empty($f[$k]))$args[$k]=$f[$k];return add_query_arg($args,home_url('/'));}
    public static function assets(){
        wp_enqueue_style('cafcc-library',plugins_url('assets/library.css',CAFCC_FILE),array('cafcc-study'),CAFCC_VERSION);
        wp_enqueue_script('cafcc-library',plugins_url('assets/library.js',CAFCC_FILE),array('cafcc-study'),CAFCC_VERSION,true);
        wp_localize_script('cafcc-library','CAFCCLibrary',array('url'=>rest_url('cafcc/v9/'),'nonce'=>wp_create_nonce('wp_rest'),'mcq_url'=>CAFCC_Portal::url('mcq'),'practice_url'=>CAFCC_Portal::url('practice'),'saved_url'=>rest_url('cafcc/v11/')));
    }
    public static function screen(){
        $reader=CAFCC_Academic_UI::student('reader');self::assets();
        return '<section data-cafcc-library><header class="cc-library-heading"><span class="cc-eyebrow">YOUR PRIVATE REVISION LIBRARY</span><h1>My Practice</h1><p>Compact records. Open one question when you are ready.</p></header><nav class="cc-practice-tabs" aria-label="Personal revision views"></nav><form class="cc-library-filters"><label>Search saved records<input type="search" name="search" placeholder="Question ID, my note or tag"></label><label>Subject<select name="subject"><option value="">All subjects</option><option>FR</option><option>AFM</option><option value="AUDIT">Audit</option><option>DT</option><option>IDT</option><option>IBS</option></select></label><label>Source<select name="source"><option value="">All sources</option><option value="rtp">RTP</option><option value="mtp">MTP</option><option value="exam">Examination</option></select></label><label>MTP series<select name="series"><option value="">All series</option><option>I</option><option>II</option></select></label><label>Attempt<input name="attempt" type="search" placeholder="All attempts"></label><label>Sort<select name="sort"><option value="recent">Most recent</option><option value="source">Source</option><option value="attempt">Examination attempt</option><option value="question">Question</option><option value="duration">Practice duration</option><option value="count">Completed attempts</option><option value="first">First completed time</option><option value="latest">Latest completed time</option><option value="best">Best completed time</option></select></label><label>Direction<select name="direction"><option value="desc">Descending</option><option value="asc">Ascending</option></select></label><label data-library-archive-label>Visibility<select name="archive"><option value="active">Current list</option><option value="archived">Archived / hidden only</option><option value="all">Include archived / hidden</option></select></label><button type="submit">Apply filters</button><button type="button" data-library-clear>Clear All</button></form><p data-library-feedback role="status"></p><p data-library-count></p><p data-library-retention></p><section data-library-comparison hidden></section><div class="cc-library-scroll"><table class="cc-library-table"><thead></thead><tbody></tbody></table></div><nav data-library-pagination aria-label="Saved practice pages"></nav><section class="cc-library-detail" data-library-detail hidden><header><h2>Selected question</h2><button type="button" data-library-collapse>Close question</button></header>'.$reader.'</section></section>';
    }
    public static function dashboard_screen(){CAFCC_Study::assets();self::assets();return '<section class="cc-dashboard" data-cafcc-dashboard><h1>My Dashboard</h1><p>Your real study activity. Every card opens its underlying records.</p><div data-study-dashboard data-student-dashboard><p>Loading your private activity…</p></div></section>';}
    public static function init(){add_action('rest_api_init',function(){
        $permission=function($r){return CAFCC_REST::permission($r);};
        foreach(array('practice'=>'list','student-dashboard'=>'dashboard') as $route=>$method)register_rest_route('cafcc/v9','/'.$route,array('methods'=>'GET','permission_callback'=>$permission,'callback'=>array(__CLASS__,$method)));
        register_rest_route('cafcc/v9','/practice-note/(?P<id>[1-9][0-9]{0,17})',array('methods'=>'PUT','permission_callback'=>$permission,'callback'=>array(__CLASS__,'save_note')));
        register_rest_route('cafcc/v9','/question/(?P<id>[1-9][0-9]{0,17})',array('methods'=>'GET','permission_callback'=>$permission,'callback'=>array(__CLASS__,'question')));
        register_rest_route('cafcc/v9','/question/(?P<id>[1-9][0-9]{0,17})/history',array('methods'=>'GET','permission_callback'=>$permission,'callback'=>array(__CLASS__,'history')));
    });add_filter('rest_post_dispatch',function($response,$server,$request){if(str_starts_with($request->get_route(),'/cafcc/v9/')){$response->header('Cache-Control','private, no-store');$response->header('Vary','Cookie');}return $response;},10,3);}
}
