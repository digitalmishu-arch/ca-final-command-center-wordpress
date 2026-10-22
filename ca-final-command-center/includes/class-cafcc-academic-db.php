<?php
defined('ABSPATH') || exit;

/** Schema 2 is additive: no schema-1 or prototype table/row is changed. */
final class CAFCC_Academic_DB {
    public static function entities() {
        return array('editions', 'taxonomy', 'document_meta', 'question_meta', 'occurrences', 'question_tags',
            'question_subjects', 'answers', 'families', 'comparisons', 'edition_mappings', 'import_batches');
    }

    public static function migrate() {
        global $wpdb;
        $review = "review_status varchar(20) NOT NULL DEFAULT 'needs_review',
            publication_status varchar(16) NOT NULL DEFAULT 'draft',
            batch_id bigint(20) unsigned DEFAULT NULL";
        $schemas = array(
            'editions' => "id bigint(20) unsigned NOT NULL AUTO_INCREMENT,
                edition_key varchar(80) NOT NULL,
                subject_id bigint(20) unsigned NOT NULL,
                title varchar(190) NOT NULL,
                edition_month varchar(7) NOT NULL DEFAULT '',
                reprint_month varchar(7) NOT NULL DEFAULT '',
                applicability varchar(500) NOT NULL,
                source_url varchar(2048) NOT NULL,
                date_note varchar(500) NOT NULL DEFAULT '',
                $review,
                PRIMARY KEY  (id),
                UNIQUE KEY edition_key (edition_key)",
            'taxonomy' => "id bigint(20) unsigned NOT NULL AUTO_INCREMENT,
                node_key varchar(120) NOT NULL,
                edition_id bigint(20) unsigned NOT NULL,
                subject_id bigint(20) unsigned NOT NULL,
                parent_id bigint(20) unsigned DEFAULT NULL,
                node_type varchar(16) NOT NULL,
                title varchar(190) NOT NULL,
                position int unsigned NOT NULL DEFAULT 0,
                heading_origin varchar(16) NOT NULL DEFAULT 'editorial',
                source_url varchar(2048) NOT NULL DEFAULT '',
                source_location varchar(190) NOT NULL DEFAULT '',
                $review,
                PRIMARY KEY  (id),
                UNIQUE KEY node_key (node_key),
                KEY parent_id (parent_id),
                KEY edition_subject (edition_id,subject_id)",
            'document_meta' => "id bigint(20) unsigned NOT NULL AUTO_INCREMENT,
                document_id bigint(20) unsigned NOT NULL,
                document_key varchar(120) NOT NULL,
                edition_id bigint(20) unsigned NOT NULL,
                issue_period varchar(80) NOT NULL DEFAULT '',
                mtp_series varchar(40) NOT NULL DEFAULT '',
                $review,
                PRIMARY KEY  (id),
                UNIQUE KEY document_id (document_id),
                UNIQUE KEY document_key (document_key)",
            'question_meta' => "id bigint(20) unsigned NOT NULL AUTO_INCREMENT,
                question_id bigint(20) unsigned NOT NULL,
                stable_key varchar(120) NOT NULL,
                edition_id bigint(20) unsigned NOT NULL,
                primary_subject_id bigint(20) unsigned NOT NULL,
                question_type varchar(24) NOT NULL DEFAULT 'unknown',
                family_id bigint(20) unsigned DEFAULT NULL,
                batch_id bigint(20) unsigned DEFAULT NULL,
                PRIMARY KEY  (id),
                UNIQUE KEY question_id (question_id),
                UNIQUE KEY stable_key (stable_key)",
            'occurrences' => "id bigint(20) unsigned NOT NULL AUTO_INCREMENT,
                occurrence_key varchar(120) NOT NULL,
                location_hash varchar(64) NOT NULL,
                question_id bigint(20) unsigned NOT NULL,
                document_id bigint(20) unsigned NOT NULL,
                edition_id bigint(20) unsigned NOT NULL,
                page_reference varchar(80) NOT NULL DEFAULT '',
                question_number varchar(40) NOT NULL,
                subquestion_number varchar(40) NOT NULL DEFAULT '',
                marks decimal(6,2) DEFAULT NULL,
                marks_verified tinyint(1) NOT NULL DEFAULT 0,
                question_type varchar(24) NOT NULL DEFAULT 'unknown',
                $review,
                PRIMARY KEY  (id),
                UNIQUE KEY occurrence_key (occurrence_key),
                UNIQUE KEY location_hash (location_hash),
                KEY question_id (question_id)",
            'question_tags' => "id bigint(20) unsigned NOT NULL AUTO_INCREMENT,
                question_id bigint(20) unsigned NOT NULL,
                node_id bigint(20) unsigned NOT NULL,
                $review,
                PRIMARY KEY  (id),
                UNIQUE KEY question_node (question_id,node_id),
                KEY node_id (node_id)",
            'question_subjects' => "id bigint(20) unsigned NOT NULL AUTO_INCREMENT,
                question_id bigint(20) unsigned NOT NULL,
                subject_id bigint(20) unsigned NOT NULL,
                $review,
                PRIMARY KEY  (id),
                UNIQUE KEY question_subject (question_id,subject_id)",
            'answers' => "id bigint(20) unsigned NOT NULL AUTO_INCREMENT,
                answer_key varchar(120) NOT NULL,
                question_id bigint(20) unsigned NOT NULL,
                occurrence_id bigint(20) unsigned DEFAULT NULL,
                answer_mode varchar(24) NOT NULL DEFAULT 'official_link',
                answer_text longtext NOT NULL,
                rights_basis varchar(1000) NOT NULL DEFAULT '',
                official_url varchar(2048) NOT NULL DEFAULT '',
                source_location varchar(190) NOT NULL DEFAULT '',
                $review,
                PRIMARY KEY  (id),
                UNIQUE KEY answer_key (answer_key),
                KEY question_id (question_id)",
            'families' => "id bigint(20) unsigned NOT NULL AUTO_INCREMENT,
                family_key varchar(120) NOT NULL,
                title varchar(190) NOT NULL,
                $review,
                PRIMARY KEY  (id),
                UNIQUE KEY family_key (family_key)",
            'comparisons' => "id bigint(20) unsigned NOT NULL AUTO_INCREMENT,
                left_question_id bigint(20) unsigned NOT NULL,
                right_question_id bigint(20) unsigned NOT NULL,
                relationship varchar(24) NOT NULL,
                notes varchar(1000) NOT NULL DEFAULT '',
                $review,
                PRIMARY KEY  (id),
                UNIQUE KEY question_pair (left_question_id,right_question_id)",
            'edition_mappings' => "id bigint(20) unsigned NOT NULL AUTO_INCREMENT,
                from_node_id bigint(20) unsigned NOT NULL,
                to_node_id bigint(20) unsigned NOT NULL,
                relationship varchar(24) NOT NULL,
                notes varchar(1000) NOT NULL DEFAULT '',
                $review,
                PRIMARY KEY  (id),
                UNIQUE KEY node_pair (from_node_id,to_node_id)",
            'import_batches' => "id bigint(20) unsigned NOT NULL AUTO_INCREMENT,
                owner_id bigint(20) unsigned NOT NULL,
                import_type varchar(24) NOT NULL,
                status varchar(24) NOT NULL DEFAULT 'committed',
                manifest longtext NOT NULL,
                created_at datetime NOT NULL,
                PRIMARY KEY  (id)"
        );
        foreach ($schemas as $entity => $columns) {
            $table = CAFCC_DB::table($entity);
            dbDelta("CREATE TABLE $table ($columns) " . $wpdb->get_charset_collate() . ';');
            $actual = $wpdb->get_col("SHOW COLUMNS FROM $table");
            preg_match_all('/^\s*([a-z_]+) (?:bigint|varchar|int|datetime|longtext|decimal|tinyint)/m', $columns, $matches);
            if (array_diff($matches[1], $actual)) {
                return new WP_Error('cafcc_schema', 'Schema 2 setup is incomplete. Existing academic records have not been migrated or deleted.');
            }
        }
        return self::seed_catalogue();
    }

    public static function seed_catalogue() {
        global $wpdb;
        $bundle=json_decode(file_get_contents(dirname(__DIR__) . "/data/syllabus-catalogue.json"),true);
        if (!$bundle || empty($bundle["editions"]) || empty($bundle["nodes"])) { return new WP_Error("cafcc_catalogue", "The bundled source catalogue is unavailable."); }
        $subjects=CAFCC_DB::table("subjects"); $editions=CAFCC_DB::table("editions"); $nodes=CAFCC_DB::table("taxonomy");
        foreach ($bundle["editions"] as $row) {
            $row["subject_id"]=(int)$wpdb->get_var($wpdb->prepare("SELECT id FROM $subjects WHERE code=%s",$row["subject_code"])); unset($row["subject_code"]);
            if (!$wpdb->get_var($wpdb->prepare("SELECT id FROM $editions WHERE edition_key=%s",$row["edition_key"])) && false===$wpdb->insert($editions,$row)) { return new WP_Error("cafcc_catalogue", "Could not prepare sourced editions."); }
        }
        foreach ($bundle["nodes"] as $row) {
            if ($wpdb->get_var($wpdb->prepare("SELECT id FROM $nodes WHERE node_key=%s",$row["node_key"]))) { continue; }
            $row["subject_id"]=(int)$wpdb->get_var($wpdb->prepare("SELECT id FROM $subjects WHERE code=%s",$row["subject_code"]));
            $row["edition_id"]=(int)$wpdb->get_var($wpdb->prepare("SELECT id FROM $editions WHERE edition_key=%s",$row["edition_key"]));
            $row["parent_id"]=$row["parent_key"]?(int)$wpdb->get_var($wpdb->prepare("SELECT id FROM $nodes WHERE node_key=%s",$row["parent_key"])):null;
            unset($row["subject_code"],$row["edition_key"],$row["parent_key"]);
            if (false===$wpdb->insert($nodes,$row)) { return new WP_Error("cafcc_catalogue", "Could not prepare sourced hierarchy."); }
        }
        return true;
    }
}
