<?php
defined('ABSPATH') || exit;

/** Rights-reviewed content and per-student notebooks; no research ingestion. */
final class CAFCC_Practice {
    public static function table($kind) {
        global $wpdb;
        if (!in_array($kind,array('content','revisions','notebook'),true)) { throw new InvalidArgumentException('Unknown practice table.'); }
        return $wpdb->prefix.'cafcc_practice_'.$kind;
    }

    public static function migrate() {
        global $wpdb;
        $charset=$wpdb->get_charset_collate();
        $schemas=array(
            'content'=>"id bigint(20) unsigned NOT NULL AUTO_INCREMENT,
                question_id bigint(20) unsigned NOT NULL,
                content_kind varchar(16) NOT NULL,
                body_html longtext NOT NULL,
                search_text longtext NOT NULL,
                options_json longtext NOT NULL,
                author_name varchar(190) NOT NULL DEFAULT '',
                source_location varchar(190) NOT NULL DEFAULT '',
                rights_type varchar(24) NOT NULL DEFAULT 'reference_only',
                rights_basis text NOT NULL,
                rights_expires varchar(10) NOT NULL DEFAULT '',
                revision bigint(20) unsigned NOT NULL DEFAULT 1,
                approved_revision bigint(20) unsigned NOT NULL DEFAULT 0,
                approved_by bigint(20) unsigned NOT NULL DEFAULT 0,
                review_status varchar(20) NOT NULL DEFAULT 'needs_review',
                publication_status varchar(16) NOT NULL DEFAULT 'draft',
                updated_at datetime NOT NULL,
                PRIMARY KEY  (id),
                UNIQUE KEY question_kind (question_id,content_kind)",
            'revisions'=>"id bigint(20) unsigned NOT NULL AUTO_INCREMENT,
                content_id bigint(20) unsigned NOT NULL,
                revision bigint(20) unsigned NOT NULL,
                actor_id bigint(20) unsigned NOT NULL,
                event_type varchar(24) NOT NULL,
                snapshot longtext NOT NULL,
                created_at datetime NOT NULL,
                PRIMARY KEY  (id),
                KEY content_id (content_id)",
            'notebook'=>"id bigint(20) unsigned NOT NULL AUTO_INCREMENT,
                user_id bigint(20) unsigned NOT NULL,
                question_id bigint(20) unsigned NOT NULL,
                note_text longtext NOT NULL,
                bookmarked tinyint(1) NOT NULL DEFAULT 0,
                updated_at datetime NOT NULL,
                PRIMARY KEY  (id),
                UNIQUE KEY student_question (user_id,question_id)"
        );
        foreach($schemas as $kind=>$columns) {
            $t=self::table($kind);dbDelta("CREATE TABLE $t ($columns) ENGINE=InnoDB $charset;");
            $actual=$wpdb->get_col("SHOW COLUMNS FROM $t");
            preg_match_all('/^\s*([a-z_]+) (?:bigint|varchar|longtext|text|tinyint|datetime)/m',$columns,$matches);
            if (!$actual || array_diff($matches[1],$actual)) {return CAFCC_Repository::error('Practice migration is incomplete; all original records are retained.',503);}
        }
        return true;
    }

    public static function html($value) {
        $tags=array_fill_keys(array('p','br','strong','b','em','i','u','h3','h4','h5','ul','ol','li','blockquote','pre','code','sup','sub','var','caption','thead','tbody','tfoot','tr','td','math','mi','mn','mo','mrow','mfrac','msqrt','msup','msub','mtable','mtr','mtd','mtext','msubsup','munder','mover'),array());
        $tags['table']=array();$tags['th']=array('scope'=>true,'colspan'=>true,'rowspan'=>true);$tags['td']=array('colspan'=>true,'rowspan'=>true);$tags['math']=array('display'=>true);
        return wp_kses($value,$tags);
    }

    public static function permitted_sql($alias) {
        global $wpdb;
        if (!preg_match('/^[a-z_]+$/D',$alias)) {throw new InvalidArgumentException('Invalid table alias.');}
        return "$alias.review_status='verified' AND $alias.publication_status='published' AND $alias.approved_by>0 AND $alias.approved_revision=$alias.revision AND $alias.rights_type IN ('original','licensed') AND $alias.rights_basis<>'' AND $alias.author_name<>'' AND $alias.body_html<>'' AND ($alias.rights_expires='' OR $alias.rights_expires>=".$wpdb->prepare('%s',current_time('Y-m-d',true)).')';
    }

    public static function visible_question($id) {
        global $wpdb;
        if(!is_user_logged_in() || !current_user_can('read') || CAFCC_DB::VERSION!==get_option('cafcc_db_version')){return false;}
        $filters=array_fill_keys(array('subject_id','edition_id','chapter_id','unit_id','topic_id','subtopic_id','search','source_type','exam_attempt'),null);
        list($from,$where,$args)=CAFCC_Explorer::query_parts($filters,get_current_user_id());$args[]=$id;
        return (bool)$wpdb->get_var($wpdb->prepare("SELECT q.id $from WHERE $where AND q.id=%d",$args));
    }

    public static function public_content($id,$kind) {
        global $wpdb;$t=self::table('content');
        if (!in_array($kind,array('question','answer'),true) || !self::visible_question($id)) {return null;}
        $row=$wpdb->get_row($wpdb->prepare("SELECT pc.* FROM $t pc WHERE pc.question_id=%d AND pc.content_kind=%s AND ".self::permitted_sql('pc'),$id,$kind),ARRAY_A);
        if (!$row || (class_exists('CAFCC_Studio')&&!CAFCC_Studio::content_allowed($id,$kind))) {return null;}
        return array('body_html'=>self::html($row['body_html']),'mcq_options'=>'question'===$kind?json_decode($row['options_json'],true):array(),
            'author_name'=>$row['author_name'],'source_location'=>$row['source_location'],'rights_label'=>'original'===$row['rights_type']?'Independently authored':'Licensed content');
    }

    public static function notebook($id) {
        global $wpdb;
        if (!is_user_logged_in() || !current_user_can('read') || !self::visible_question($id)) {return CAFCC_Repository::error('Published question not found.',404);}
        $t=self::table('notebook');
        $row=$wpdb->get_row($wpdb->prepare("SELECT note_text,bookmarked FROM $t WHERE user_id=%d AND question_id=%d",get_current_user_id(),$id),ARRAY_A);
        return array('note_text'=>$row['note_text']??'','bookmarked'=>(bool)($row['bookmarked']??false));
    }

    public static function save_notebook($id,$data) {
        global $wpdb;$current=self::notebook($id);if(is_wp_error($current)){return $current;}
        if (!is_array($data) || !$data || array_diff(array_keys($data),array('note_text','bookmarked'))) {return CAFCC_Repository::error('Send only your note text and/or bookmark.');}
        if (array_key_exists('note_text',$data) && (!is_string($data['note_text']) || strlen($data['note_text'])>10000)) {return CAFCC_Repository::error('Private note must be text up to 10,000 bytes.');}
        if (array_key_exists('bookmarked',$data) && !is_bool($data['bookmarked'])) {return CAFCC_Repository::error('Bookmark must be true or false.');}
        $value=array('user_id'=>get_current_user_id(),'question_id'=>$id,'note_text'=>isset($data['note_text'])?sanitize_textarea_field($data['note_text']):$current['note_text'],
            'bookmarked'=>array_key_exists('bookmarked',$data)?(int)$data['bookmarked']:(int)$current['bookmarked'],'updated_at'=>current_time('mysql',true));
        if(false===$wpdb->replace(self::table('notebook'),$value)){return CAFCC_Repository::error('Cannot save your notebook.',500);}
        return self::notebook($id);
    }

    private static function audit($row,$event) {
        global $wpdb;
        return false!==$wpdb->insert(self::table('revisions'),array('content_id'=>$row['id'],'revision'=>$row['revision'],
            'actor_id'=>get_current_user_id(),'event_type'=>$event,'snapshot'=>wp_json_encode($row),'created_at'=>current_time('mysql',true)));
    }

    public static function save($input,$id=0) {
        if(!CAFCC_Repository::admin_allowed()){return CAFCC_Repository::error('Administrator access is required.',403);}
        $allowed=array('question_id','content_kind','body_html','mcq_options','author_name','source_location','rights_type','rights_basis','rights_expires','expected_revision');
        if(!is_array($input) || !$input || array_diff(array_keys($input),$allowed)){return CAFCC_Repository::error('Unexpected practice content fields.');}
        return CAFCC_Academic::transaction(function()use($input,$id){
            global $wpdb;$t=self::table('content');$old=$id?$wpdb->get_row($wpdb->prepare("SELECT * FROM $t WHERE id=%d FOR UPDATE",$id),ARRAY_A):null;
            if($id && !$old){return CAFCC_Repository::error('Content not found.',404);}
            if($old && (!isset($input['expected_revision']) || !is_scalar($input['expected_revision']) || (string)$old['revision']!==(string)$input['expected_revision'])){return CAFCC_Repository::error('Content changed. Reload before editing.',409);}
            $qid=CAFCC_Repository::id($input['question_id']??($old['question_id']??null));
            if(is_wp_error($qid) || !CAFCC_Repository::get('questions',$qid)){return CAFCC_Repository::error('Choose an existing question ID.');}
            $kind=$input['content_kind']??($old['content_kind']??'question');
            if(!in_array($kind,array('question','answer'),true)){return CAFCC_Repository::error('Choose question or answer content.');}
            if($old && ((int)$old['question_id']!==$qid || $old['content_kind']!==$kind)){return CAFCC_Repository::error('Content identity cannot be reassigned.',409);}
            $row=array('question_id'=>$qid,'content_kind'=>$kind);
            foreach(array('body_html'=>60000,'author_name'=>190,'source_location'=>190,'rights_type'=>24,'rights_basis'=>2000,'rights_expires'=>10) as $field=>$limit){
                $v=$input[$field]??($old[$field]??('rights_type'===$field?'reference_only':''));
                if(!is_string($v) || strlen($v)>$limit || preg_match('~(?:drive|docs)\.google\.com~i',html_entity_decode($v,ENT_QUOTES|ENT_HTML5,'UTF-8'))){return CAFCC_Repository::error('Invalid '.$field.' or private Drive link.');}
                $row[$field]='body_html'===$field?self::html($v):sanitize_text_field($v);
            }
            if(!in_array($row['rights_type'],array('reference_only','original','licensed'),true)){return CAFCC_Repository::error('Select an explicit rights basis.');}
            $expires=$row['rights_expires'];
            if($expires && (!preg_match('/^\d{4}-\d{2}-\d{2}$/D',$expires) || !checkdate((int)substr($expires,5,2),(int)substr($expires,8,2),(int)substr($expires,0,4)))){return CAFCC_Repository::error('Rights expiry must be a real YYYY-MM-DD date or blank.');}
            $options=$input['mcq_options']??($old?json_decode($old['options_json'],true):array());
            if(!is_array($options) || !array_is_list($options) || count($options)>8){return CAFCC_Repository::error('MCQ options must be a list of at most eight choices.');}
            $clean=array();$keys=array();
            foreach($options as $option){
                if(!is_array($option) || array_diff(array_keys($option),array('key','text')) || !isset($option['key'],$option['text']) || !is_string($option['key']) || !preg_match('/^[A-H]$/D',$option['key']) || in_array($option['key'],$keys,true) || !is_string($option['text']) || strlen($option['text'])>2000 || preg_match('~(?:drive|docs)\.google\.com~i',html_entity_decode($option['text'],ENT_QUOTES|ENT_HTML5,'UTF-8'))){return CAFCC_Repository::error('Each option needs a unique A–H key and plain text; answer keys are not question fields.');}
                $keys[]=$option['key'];$clean[]=array('key'=>$option['key'],'text'=>sanitize_text_field($option['text']));
            }
            if('answer'===$kind && $clean){return CAFCC_Repository::error('Keep correct choices in the reviewed solution, not question options.');}
            if('reference_only'===$row['rights_type'] && ($row['body_html'] || $clean)){return CAFCC_Repository::error('Reference-only records cannot store extracted source text in WordPress. Keep research private and use the official link.');}
            $row['options_json']=wp_json_encode($clean);$row['search_text']=wp_strip_all_tags($row['body_html']).' '.implode(' ',array_column($clean,'text'));
            $row=array_merge($row,array('revision'=>$old?(int)$old['revision']+1:1,'approved_revision'=>0,'approved_by'=>0,'review_status'=>'needs_review','publication_status'=>'draft','updated_at'=>current_time('mysql',true)));
            if($old && !self::audit($old,'before_edit')){return CAFCC_Repository::error('Cannot retain content history.',500);}
            $suppressed=$wpdb->suppress_errors(true);
            try{$ok=$id?$wpdb->update($t,$row,array('id'=>$id)):$wpdb->insert($t,$row);}finally{$wpdb->suppress_errors($suppressed);}
            if(false===$ok){return CAFCC_Repository::error('Question/kind already exists or content could not be saved.',409);}
            $saved=$wpdb->get_row($wpdb->prepare("SELECT * FROM $t WHERE id=%d",$id?:$wpdb->insert_id),ARRAY_A);
            return self::audit($saved,'saved_draft')?$saved:CAFCC_Repository::error('Cannot retain content history.',500);
        });
    }

    public static function approve($id,$input) {
        if(!CAFCC_Repository::admin_allowed()){return CAFCC_Repository::error('Administrator access is required.',403);}
        if(!is_array($input) || array_diff(array_keys($input),array('expected_revision','rights_confirmed')) || true!==($input['rights_confirmed']??false)){return CAFCC_Repository::error('Explicit review of publication rights is required.');}
        return CAFCC_Academic::transaction(function()use($id,$input){
            global $wpdb;$t=self::table('content');$row=$wpdb->get_row($wpdb->prepare("SELECT * FROM $t WHERE id=%d FOR UPDATE",$id),ARRAY_A);
            if(!$row){return CAFCC_Repository::error('Content not found.',404);}
            if(!isset($input['expected_revision']) || !is_scalar($input['expected_revision']) || (string)$row['revision']!==(string)$input['expected_revision']){return CAFCC_Repository::error('Review the current content revision first.',409);}
            if(!in_array($row['rights_type'],array('original','licensed'),true) || !$row['rights_basis'] || !$row['author_name'] || !trim(wp_strip_all_tags($row['body_html'])) || ($row['rights_expires'] && $row['rights_expires']<current_time('Y-m-d',true))){return CAFCC_Repository::error('Publication requires reviewed original/licensed text, author, rights details and current permission.');}
            $row['review_status']='verified';$row['publication_status']='published';$row['approved_revision']=$row['revision'];$row['approved_by']=get_current_user_id();
            if(false===$wpdb->update($t,array_intersect_key($row,array_flip(array('review_status','publication_status','approved_revision','approved_by'))),array('id'=>$id)) || !self::audit($row,'rights_approved')){return CAFCC_Repository::error('Cannot save rights approval.',500);}
            return $row;
        });
    }

    private static function body($r) {
        if(strlen($r->get_body())>100000){return CAFCC_Repository::error('Request too large.',413);}
        $v=$r->get_json_params();return is_array($v) && $v && !array_is_list($v)?$v:CAFCC_Repository::error('Send a JSON object.');
    }

    public static function init() {
        add_action('rest_api_init',function(){
            $admin=function($r){return CAFCC_REST::permission($r,true);};$student=function($r){return CAFCC_REST::permission($r);};
            register_rest_route('cafcc/v3','/admin/practice',array(
                array('methods'=>'GET','permission_callback'=>$admin,'callback'=>function($r){global $wpdb;$page=$r->get_param('page')??'1';if(!is_scalar($page)||!preg_match('/^[1-9][0-9]{0,4}$/D',(string)$page)){return CAFCC_Repository::error('Invalid page.');}$t=self::table('content');return $wpdb->get_results($wpdb->prepare("SELECT * FROM $t ORDER BY id DESC LIMIT 50 OFFSET %d",((int)$page-1)*50),ARRAY_A);}),
                array('methods'=>'POST','permission_callback'=>$admin,'callback'=>function($r){$b=self::body($r);return is_wp_error($b)?$b:self::save($b);})
            ));
            register_rest_route('cafcc/v3','/admin/practice/(?P<id>[1-9][0-9]{0,17})',array('methods'=>'PATCH','permission_callback'=>$admin,'callback'=>function($r){$b=self::body($r);return is_wp_error($b)?$b:self::save($b,(int)$r['id']);}));
            register_rest_route('cafcc/v3','/admin/practice/(?P<id>[1-9][0-9]{0,17})/approve',array('methods'=>'POST','permission_callback'=>$admin,'callback'=>function($r){$b=self::body($r);return is_wp_error($b)?$b:self::approve((int)$r['id'],$b);}));
            register_rest_route('cafcc/v3','/admin/practice/(?P<id>[1-9][0-9]{0,17})/history',array('methods'=>'GET','permission_callback'=>$admin,'callback'=>function($r){global $wpdb;$t=self::table('revisions');return $wpdb->get_results($wpdb->prepare("SELECT * FROM $t WHERE content_id=%d ORDER BY id DESC LIMIT 50",(int)$r['id']),ARRAY_A);}));
            register_rest_route('cafcc/v3','/notebook/(?P<id>[1-9][0-9]{0,17})',array(
                array('methods'=>'GET','permission_callback'=>$student,'callback'=>function($r){if(null!==$r->get_param('user_id')){return CAFCC_Repository::error('User selection is not supported.');}return self::notebook((int)$r['id']);}),
                array('methods'=>'PUT','permission_callback'=>$student,'callback'=>function($r){$b=self::body($r);return is_wp_error($b)?$b:self::save_notebook((int)$r['id'],$b);})
            ));
        });
        CAFCC_Practice_UI::init();
    }
}
