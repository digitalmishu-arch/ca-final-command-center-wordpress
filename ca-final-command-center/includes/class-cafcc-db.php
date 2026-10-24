<?php
defined('ABSPATH') || exit;

final class CAFCC_DB {
    const VERSION = '4';

    public static function table($entity) {
        global $wpdb;
        if (class_exists('CAFCC_Academic_DB') && in_array($entity, CAFCC_Academic_DB::entities(), true)) {
            return $wpdb->prefix . 'cafcc_' . $entity;
        }
        if (!in_array($entity, array('subjects', 'chapters', 'topics', 'documents', 'questions', 'progress'), true)) {
            throw new InvalidArgumentException('Unknown academic table.');
        }
        // The prototype used cafcc_questions/cafcc_progress with an incompatible
        // schema and no verification metadata. Keep those tables untouched.
        $suffix = array('questions' => 'question_references', 'progress' => 'student_progress');
        return $wpdb->prefix . 'cafcc_' . ($suffix[$entity] ?? $entity);
    }

    public static function legacy_counts() {
        global $wpdb;
        $counts = array();
        foreach (array('questions', 'progress') as $entity) {
            $table = $wpdb->prefix . 'cafcc_' . $entity;
            if ($wpdb->get_var($wpdb->prepare('SHOW TABLES LIKE %s', $wpdb->esc_like($table))) === $table) {
                $counts[$entity] = (int) $wpdb->get_var("SELECT COUNT(*) FROM $table");
            }
        }
        return $counts;
    }

    public static function activate($network_wide = false) {
        if ($network_wide) {
            wp_die('Please activate CA Final Command Center separately on each site. Network activation is not supported.');
        }
        $result = self::migrate();
        if (is_wp_error($result)) {
            wp_die(esc_html($result->get_error_message()));
        }
    }

    public static function migrate() {
        global $wpdb;
        $version = get_option('cafcc_db_version', '0');
        if (self::VERSION === $version) {
            return true;
        }
        // Refuse to run an older plugin against a newer database.
        if ((int) $version > (int) self::VERSION) {
            return new WP_Error('cafcc_schema', 'The academic database requires a newer plugin version.');
        }
        require_once ABSPATH . 'wp-admin/includes/upgrade.php';
        $charset = $wpdb->get_charset_collate();
        $schemas = array(
            'subjects' => "id bigint(20) unsigned NOT NULL AUTO_INCREMENT,
                code varchar(16) NOT NULL,
                name varchar(190) NOT NULL,
                PRIMARY KEY  (id),
                UNIQUE KEY code (code)",
            'chapters' => "id bigint(20) unsigned NOT NULL AUTO_INCREMENT,
                subject_id bigint(20) unsigned NOT NULL,
                title varchar(190) NOT NULL,
                syllabus_version varchar(80) NOT NULL,
                position int unsigned NOT NULL DEFAULT 0,
                PRIMARY KEY  (id),
                KEY subject_id (subject_id)",
            'topics' => "id bigint(20) unsigned NOT NULL AUTO_INCREMENT,
                chapter_id bigint(20) unsigned NOT NULL,
                title varchar(190) NOT NULL,
                PRIMARY KEY  (id),
                KEY chapter_id (chapter_id)",
            'documents' => "id bigint(20) unsigned NOT NULL AUTO_INCREMENT,
                title varchar(190) NOT NULL,
                source_type varchar(32) NOT NULL,
                exam_attempt varchar(80) NOT NULL,
                syllabus_version varchar(80) NOT NULL,
                official_url varchar(2048) NOT NULL DEFAULT '',
                verification_status varchar(16) NOT NULL DEFAULT 'unverified',
                PRIMARY KEY  (id)",
            'questions' => "id bigint(20) unsigned NOT NULL AUTO_INCREMENT,
                document_id bigint(20) unsigned NOT NULL,
                chapter_id bigint(20) unsigned NOT NULL,
                topic_id bigint(20) unsigned DEFAULT NULL,
                question_number varchar(40) NOT NULL,
                title varchar(190) NOT NULL,
                verification_status varchar(16) NOT NULL DEFAULT 'unverified',
                publication_status varchar(16) NOT NULL DEFAULT 'draft',
                PRIMARY KEY  (id),
                KEY document_id (document_id),
                KEY chapter_id (chapter_id),
                KEY topic_id (topic_id)",
            'progress' => "id bigint(20) unsigned NOT NULL AUTO_INCREMENT,
                user_id bigint(20) unsigned NOT NULL,
                question_id bigint(20) unsigned NOT NULL,
                status varchar(24) NOT NULL,
                updated_at datetime NOT NULL,
                PRIMARY KEY  (id),
                UNIQUE KEY student_question (user_id,question_id),
                KEY question_id (question_id)"
        );
        foreach ($schemas as $entity => $columns) {
            $table = self::table($entity);
            dbDelta("CREATE TABLE $table ($columns) $charset;");
            if ($wpdb->get_var($wpdb->prepare('SHOW TABLES LIKE %s', $wpdb->esc_like($table))) !== $table) {
                return new WP_Error('cafcc_schema', 'Academic database setup failed. Check database permissions and retry activation.');
            }
            // Verify columns even on a partial migration before advancing the version.
            $actual = $wpdb->get_col("SHOW COLUMNS FROM $table");
            preg_match_all('/^\s*([a-z_]+) (?:bigint|varchar|int|datetime)/m', $columns, $matches);
            if (array_diff($matches[1], $actual)) {
                return new WP_Error('cafcc_schema', 'Academic database migration is incomplete.');
            }
        }
        $subjects = array('FR' => 'Financial Reporting', 'AFM' => 'Advanced Financial Management',
            'AUDIT' => 'Advanced Audit', 'DT' => 'Direct Tax Laws and International Taxation',
            'IDT' => 'Indirect Tax Laws', 'IBS' => 'Integrated Business Solutions');
        $table = self::table('subjects');
        foreach ($subjects as $code => $name) {
            if (false === $wpdb->query($wpdb->prepare("INSERT IGNORE INTO $table (code,name) VALUES (%s,%s)", $code, $name))) {
                return new WP_Error('cafcc_schema', 'Subject setup failed.');
            }
        }
        $academic = CAFCC_Academic_DB::migrate();
        if (is_wp_error($academic)) { return $academic; }
        $practice=CAFCC_Practice::migrate();
        if (is_wp_error($practice)) {return $practice;}
        $bank=CAFCC_Bank_DB::migrate();
        if (is_wp_error($bank)) {return $bank;}
        update_option('cafcc_db_version', self::VERSION, false);
        return true;
    }
}
