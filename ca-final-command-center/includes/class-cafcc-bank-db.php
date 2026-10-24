<?php
defined('ABSPATH') || exit;

/** Additive schema 4. No existing academic/account row is rewritten. */
final class CAFCC_Bank_DB {
    public static function table($name) {
        if(!in_array($name,array('closure','aliases','reviews','audit','batches','access','access_events','resources'),true)){throw new InvalidArgumentException('Unknown bank table.');}
        global $wpdb;return $wpdb->prefix.'cafcc_bank_'.$name;
    }
    public static function migrate() {
        global $wpdb;
        $schemas=array(
            'closure'=>"ancestor_id bigint(20) unsigned NOT NULL, descendant_id bigint(20) unsigned NOT NULL, depth smallint unsigned NOT NULL, PRIMARY KEY  (ancestor_id,descendant_id), KEY descendant (descendant_id,ancestor_id)",
            'aliases'=>"id bigint(20) unsigned NOT NULL AUTO_INCREMENT, node_id bigint(20) unsigned NOT NULL, alias_text varchar(190) NOT NULL, review_status varchar(20) NOT NULL DEFAULT 'needs_review', PRIMARY KEY  (id), UNIQUE KEY node_alias (node_id,alias_text), KEY alias_text (alias_text)",
            'reviews'=>"id bigint(20) unsigned NOT NULL AUTO_INCREMENT,
                stable_id varchar(120) NOT NULL,
                question_id bigint(20) unsigned DEFAULT NULL,
                occurrence_id bigint(20) unsigned DEFAULT NULL,
                source_hash varchar(64) NOT NULL,
                source_identity varchar(64) NOT NULL,
                source_key varchar(120) NOT NULL,
                subject_code varchar(16) NOT NULL,
                source_type varchar(32) NOT NULL,
                exam_attempt varchar(80) NOT NULL,
                mtp_series varchar(40) NOT NULL DEFAULT '',
                section_label varchar(120) NOT NULL,
                question_number varchar(40) NOT NULL,
                subquestion_number varchar(40) NOT NULL DEFAULT '',
                revision bigint(20) unsigned NOT NULL DEFAULT 1,
                fulltext_allowed tinyint(1) NOT NULL DEFAULT 0,
                question_content_id bigint(20) unsigned NOT NULL DEFAULT 0,
                question_content_revision bigint(20) unsigned NOT NULL DEFAULT 0,
                answer_content_id bigint(20) unsigned NOT NULL DEFAULT 0,
                answer_content_revision bigint(20) unsigned NOT NULL DEFAULT 0,
                status varchar(24) NOT NULL DEFAULT 'needs_review',
                publication_status varchar(16) NOT NULL DEFAULT 'draft',
                payload longtext NOT NULL,
                approvals longtext NOT NULL,
                payload_hash varchar(64) NOT NULL,
                batch_key varchar(120) NOT NULL,
                modified_at datetime NOT NULL,
                PRIMARY KEY  (id), UNIQUE KEY stable_id (stable_id), UNIQUE KEY source_identity (source_identity), UNIQUE KEY occurrence_id (occurrence_id),
                KEY review_queue (status,id), KEY subject_source_attempt (subject_code,source_type,exam_attempt), KEY question_id (question_id), KEY batch_key (batch_key)",
            'audit'=>"id bigint(20) unsigned NOT NULL AUTO_INCREMENT, review_id bigint(20) unsigned NOT NULL, revision bigint(20) unsigned NOT NULL, actor_id bigint(20) unsigned NOT NULL, action varchar(40) NOT NULL, snapshot longtext NOT NULL, created_at datetime NOT NULL, PRIMARY KEY  (id), KEY review_revision (review_id,revision)",
            'batches'=>"id bigint(20) unsigned NOT NULL AUTO_INCREMENT, batch_key varchar(120) NOT NULL, owner_id bigint(20) unsigned NOT NULL, batch_type varchar(32) NOT NULL, status varchar(24) NOT NULL, manifest longtext NOT NULL, created_at datetime NOT NULL, PRIMARY KEY  (id), UNIQUE KEY batch_key (batch_key), KEY owner_status (owner_id,status)",
            'access'=>"user_id bigint(20) unsigned NOT NULL, account_state varchar(24) NOT NULL DEFAULT 'legacy_pending', email_verified tinyint(1) NOT NULL DEFAULT 0, token_hash varchar(64) NOT NULL DEFAULT '', token_expires datetime DEFAULT NULL, plan_key varchar(80) NOT NULL DEFAULT '', entitlement_state varchar(24) NOT NULL DEFAULT 'none', starts_at datetime DEFAULT NULL, expires_at datetime DEFAULT NULL, updated_at datetime NOT NULL, PRIMARY KEY  (user_id), KEY pending (account_state,user_id)",
            'access_events'=>"id bigint(20) unsigned NOT NULL AUTO_INCREMENT, user_id bigint(20) unsigned NOT NULL, actor_id bigint(20) unsigned NOT NULL, event_type varchar(40) NOT NULL, details longtext NOT NULL, created_at datetime NOT NULL, PRIMARY KEY  (id), KEY user_id (user_id,id)",
            'resources'=>"id bigint(20) unsigned NOT NULL AUTO_INCREMENT, subject_code varchar(16) NOT NULL DEFAULT '', title varchar(190) NOT NULL, official_url varchar(2048) NOT NULL, resource_type varchar(32) NOT NULL, applicability varchar(500) NOT NULL DEFAULT '', review_status varchar(20) NOT NULL DEFAULT 'needs_review', publication_status varchar(16) NOT NULL DEFAULT 'draft', PRIMARY KEY  (id), KEY public_subject (publication_status,subject_code)"
        );
        foreach($schemas as $name=>$columns){$columns=preg_replace('/,\s+(?=[A-Za-z_])/',",\n",$columns);$t=self::table($name);dbDelta("CREATE TABLE $t ($columns) ENGINE=InnoDB ".$wpdb->get_charset_collate().';');preg_match_all('/^\s*([a-z_]+) (?:bigint|varchar|smallint|tinyint|datetime|longtext|text)/m',$columns,$matches);$actual=$wpdb->get_col("SHOW COLUMNS FROM $t");if(!$actual||array_diff($matches[1],$actual)){return CAFCC_Repository::error('Schema 4 setup is incomplete; existing records are retained.',503);}}
        // Additional indexes do not change row identities or values.
        foreach(array('taxonomy'=>array('bank_type_title'=>'(node_type,title)','bank_parent_status'=>'(parent_id,review_status,publication_status)'), 'occurrences'=>array('bank_document_question'=>'(document_id,question_id)','bank_public_id'=>'(publication_status,review_status,id)'), 'question_tags'=>array('bank_node_question'=>'(node_id,question_id)'), 'documents'=>array('bank_source_attempt'=>'(source_type,exam_attempt)')) as $name=>$indexes){
            $t=CAFCC_DB::table($name);$known=$wpdb->get_col("SHOW INDEX FROM $t",2);
            foreach($indexes as $key=>$columns){if(!in_array($key,$known,true) && false===$wpdb->query("ALTER TABLE $t ADD KEY $key $columns")){return CAFCC_Repository::error('Question bank index setup is incomplete.',503);}}
        }
        $seed=CAFCC_Academic_DB::seed_catalogue(dirname(__DIR__).'/data/taxonomy-v04-proposals.json');if(is_wp_error($seed))return $seed;
        return self::rebuild_closure();
    }
    public static function private_reference($value){
        if(!is_string($value))return false;for($i=0;$i<6;$i++){if(preg_match('~(?:drive|docs)\.google\.com~i',$value))return true;$next=rawurldecode(html_entity_decode($value,ENT_QUOTES|ENT_HTML5,'UTF-8'));if($next===$value)break;$value=$next;}return (bool)preg_match('~(?:drive|docs)\.google\.com~i',$value);
    }
    public static function transactional(){
        global $wpdb;$tables=array();foreach(array('closure','aliases','reviews','audit','batches','access','access_events','resources') as $kind)$tables[]=self::table($kind);foreach(array_merge(CAFCC_Academic_DB::entities(),array('subjects','chapters','topics','documents','questions','progress')) as $kind)$tables[]=CAFCC_DB::table($kind);foreach(array('content','revisions','notebook') as $kind)$tables[]=CAFCC_Practice::table($kind);
        $placeholders=implode(',',array_fill(0,count($tables),'%s'));$rows=$wpdb->get_results($wpdb->prepare("SHOW TABLE STATUS WHERE Name IN ($placeholders)",$tables),ARRAY_A);if(count($rows)!==count(array_unique($tables)))return CAFCC_Repository::error('Academic transaction tables are incomplete.',503);foreach($rows as $r)if(strtoupper($r['Engine']??'')!=='INNODB')return CAFCC_Repository::error('Review/approval requires InnoDB tables. Existing data is retained; no table engine is automatically converted.',503);return true;
    }
    public static function audit_master($entity,$id,$before,$after){
        if(!CAFCC_Repository::admin_allowed())return false;global $wpdb;return false!==$wpdb->insert(self::table('audit'),array('review_id'=>0,'revision'=>0,'actor_id'=>get_current_user_id(),'action'=>'master_saved','snapshot'=>wp_json_encode(array('entity'=>$entity,'record_id'=>$id,'before'=>$before,'after'=>$after)),'created_at'=>current_time('mysql',true)));
    }
    public static function rebuild_closure() {
        global $wpdb;$n=CAFCC_DB::table('taxonomy');$t=self::table('closure');
        $rows=$wpdb->get_results("SELECT id,parent_id FROM $n",OBJECT_K);
        foreach($rows as $row){$id=(int)$row->id;$parent=$id;$seen=array();$depth=0;
            while($parent && isset($rows[$parent])){if(isset($seen[$parent]) || $depth>12){return CAFCC_Repository::error('Taxonomy cycle/depth requires review.',409);} $seen[$parent]=true;
                if(false===$wpdb->query($wpdb->prepare("INSERT IGNORE INTO $t (ancestor_id,descendant_id,depth) VALUES (%d,%d,%d)",$parent,$id,$depth))){return CAFCC_Repository::error('Cannot index taxonomy.',500);}
                $parent=(int)$rows[$parent]->parent_id;$depth++;
            }
        }return true;
    }
}
