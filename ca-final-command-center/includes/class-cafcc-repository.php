<?php
defined('ABSPATH') || exit;

final class CAFCC_Repository {
    const STATUSES = array('not_started', 'attempted', 'needs_revision', 'completed');
    const VERIFICATION = array('unverified', 'verified', 'rejected');
    const SOURCES = array('exam', 'rtp', 'mtp', 'study_material', 'case_study', 'other');

    public static function entities() {
        return array('subjects', 'chapters', 'topics', 'documents', 'questions');
    }

    public static function admin_allowed() {
        $user = wp_get_current_user();
        return current_user_can('manage_options') &&
            (in_array('administrator', (array) $user->roles, true) || (is_multisite() && is_super_admin()));
    }

    public static function error($message, $status = 400) {
        return new WP_Error('cafcc_request', $message, array('status' => $status));
    }

    public static function id($value, $optional = false) {
        if ($optional && (null === $value || '' === $value || 0 === $value || '0' === $value)) {
            return null;
        }
        if (!is_scalar($value) || !preg_match('/^[1-9][0-9]{0,17}$/D', (string) $value)) {
            return self::error('A valid positive record ID is required.');
        }
        return (int) $value;
    }

    public static function get($entity, $id) {
        global $wpdb;
        $table = CAFCC_DB::table($entity);
        return $wpdb->get_row($wpdb->prepare("SELECT * FROM $table WHERE id = %d", $id), ARRAY_A);
    }

    public static function listing($entity, $page = 1) {
        global $wpdb;
        $table = CAFCC_DB::table($entity);
        return array('items' => $wpdb->get_results($wpdb->prepare("SELECT * FROM $table ORDER BY id ASC LIMIT %d OFFSET %d", 100, ($page - 1) * 100), ARRAY_A),
            'total' => (int) $wpdb->get_var("SELECT COUNT(*) FROM $table"), 'per_page' => 100);
    }

    public static function fields($entity) {
        $fields = array(
            'subjects' => array('code' => 16, 'name' => 190),
            'chapters' => array('subject_id' => 'id', 'title' => 190, 'syllabus_version' => 80, 'position' => 'position'),
            'topics' => array('chapter_id' => 'id', 'title' => 190),
            'documents' => array('title' => 190, 'source_type' => 'source', 'exam_attempt' => 80,
                'syllabus_version' => 80, 'official_url' => 'url', 'verification_status' => 'verification'),
            'questions' => array('document_id' => 'id', 'chapter_id' => 'id', 'topic_id' => 'optional_id',
                'question_number' => 40, 'title' => 190, 'verification_status' => 'verification', 'publication_status' => 'publication')
        );
        return $fields[$entity] ?? array();
    }

    public static function official_url($value) {
        if ('' === $value) {
            return '';
        }
        $parts = wp_parse_url($value);
        $host = strtolower($parts['host'] ?? '');
        $allowed = false;
        foreach (array('icai.org', 'icai.nic.in') as $domain) {
            if ($domain === $host || str_ends_with($host, '.' . $domain)) {
                $allowed = true;
            }
        }
        if (!$allowed || 'https' !== ($parts['scheme'] ?? '') || isset($parts['user']) || isset($parts['pass']) ||
            isset($parts['fragment']) || isset($parts['query']) || isset($parts['port']) || strlen($value) > 2048) {
            return self::error('Use a direct HTTPS ICAI URL without query parameters. Google Drive and other private links are not allowed.');
        }
        $clean = esc_url_raw($value, array('https'));
        return $clean ? $clean : self::error('Invalid official URL.');
    }

    private static function validate($entity, $input) {
        $fields = self::fields($entity);
        if (array_diff(array_keys($input), array_keys($fields))) {
            return self::error('Unexpected record fields.');
        }
        $data = array();
        foreach ($fields as $key => $type) {
            $value = $input[$key] ?? '';
            if (in_array($type, array('id', 'optional_id'), true)) {
                $value = self::id($value, 'optional_id' === $type);
            } elseif ('position' === $type) {
                $value = '' === $value ? '0' : $value;
                if (!is_scalar($value) || !preg_match('/^[0-9]{1,6}$/D', (string) $value)) {
                    return self::error('Position must be between 0 and 999999.');
                }
                $value = (int) $value;
            } else {
                if (!is_string($value)) {
                    return self::error('Text fields must contain text.');
                }
                $value = trim($value);
                if ('url' === $type) {
                    $value = self::official_url($value);
                } elseif (is_int($type)) {
                    $value = sanitize_text_field($value);
                    if ('' === $value || strlen($value) > $type) {
                        return self::error($key . ' is required and must fit its length limit.');
                    }
                } else {
                    $choices = array('source' => self::SOURCES, 'verification' => self::VERIFICATION,
                        'publication' => array('draft', 'published'));
                    if (!in_array($value, $choices[$type], true)) {
                        return self::error('Invalid ' . $key . '.');
                    }
                }
            }
            if (is_wp_error($value)) {
                return $value;
            }
            $data[$key] = $value;
        }
        if ('subjects' === $entity && !preg_match('/^[A-Z][A-Z0-9_]{1,15}$/D', $data['code'])) {
            return self::error('Subject code must use 2–16 uppercase letters, digits or underscores.');
        }
        $relations = array('subject_id' => 'subjects', 'chapter_id' => 'chapters', 'topic_id' => 'topics', 'document_id' => 'documents');
        foreach ($relations as $key => $table) {
            if (!empty($data[$key]) && !self::get($table, $data[$key])) {
                return self::error('The selected ' . $table . ' record does not exist.');
            }
        }
        if ('documents' === $entity && 'verified' === $data['verification_status'] && !$data['official_url']) {
            return self::error('Verified documents require an official ICAI URL.');
        }
        if ('questions' === $entity) {
            $document = self::get('documents', $data['document_id']);
            $chapter = self::get('chapters', $data['chapter_id']);
            if ($document['syllabus_version'] !== $chapter['syllabus_version']) {
                return self::error('Document and chapter syllabus versions must match exactly.');
            }
            if ($data['topic_id']) {
                $topic = self::get('topics', $data['topic_id']);
                if ((int) $topic['chapter_id'] !== $data['chapter_id']) {
                    return self::error('The topic must belong to the selected chapter.');
                }
            }
            if ('published' === $data['publication_status'] && ('verified' !== $data['verification_status'] ||
                'verified' !== $document['verification_status'] || !$document['official_url'])) {
                return self::error('Only verified references from verified official source documents may be published.');
            }
        }
        return $data;
    }

    public static function save($entity, $input, $id = 0,$inside_transaction=false) {
        if(!$inside_transaction&&class_exists('CAFCC_Bank_DB')){if(is_wp_error($e=CAFCC_Bank_DB::transactional()))return $e;return CAFCC_Academic::transaction(function()use($entity,$input,$id){return self::save($entity,$input,$id,true);});}
        global $wpdb;
        if (!self::admin_allowed()) {
            return self::error('Administrator access is required.', 403);
        }
        if (!in_array($entity, self::entities(), true) || !is_array($input)) {
            return self::error('Invalid master record.');
        }
        $old = $id ? self::get($entity, $id) : null;$audit_before=$old;
        if ($id && !$old) {
            return self::error('Record not found.', 404);
        }
        if ($old) {
            unset($old['id']);
            $input = array_merge($old, $input);
        }
        $data = self::validate($entity, $input);
        if (is_wp_error($data)) {
            return $data;
        }
        // Protect existing question associations when structural metadata changes.
        $structural = array('chapters' => array('subject_id', 'syllabus_version'), 'topics' => array('chapter_id'), 'documents' => array('syllabus_version'));
        foreach ($structural[$entity] ?? array() as $key) {
            if ($old && (string) $old[$key] !== (string) $data[$key] && self::referenced($entity, $id)) {
                return self::error('This record has dependent records. Create a separate record for structural changes.', 409);
            }
        }
        foreach($data as $value)if(is_string($value)&&class_exists('CAFCC_Bank_DB')&&CAFCC_Bank_DB::private_reference($value))return self::error('Private Drive references are not public academic records.');
        $table = CAFCC_DB::table($entity);
        $result = $id ? $wpdb->update($table, $data, array('id' => $id)) : $wpdb->insert($table, $data);
        if (false === $result) {
            return self::error('The record could not be saved. Check for a duplicate subject code.', 409);
        }
        $saved_id=$id?:$wpdb->insert_id;
        if($old && class_exists('CAFCC_Studio'))CAFCC_Studio::invalidate($entity,$saved_id);
        $saved=self::get($entity,$saved_id);if(class_exists('CAFCC_Bank_DB')&&!CAFCC_Bank_DB::audit_master('legacy_'.$entity,$saved_id,$audit_before,$saved))return self::error('Cannot retain master history.',500);
        return $saved;
    }

    private static function referenced($entity, $id) {
        global $wpdb;
        $dependencies = array('subjects' => array('chapters' => 'subject_id'),
            'chapters' => array('topics' => 'chapter_id', 'questions' => 'chapter_id'),
            'topics' => array('questions' => 'topic_id'), 'documents' => array('questions' => 'document_id'),
            'questions' => array('progress' => 'question_id'));
        foreach ($dependencies[$entity] as $child => $field) {
            $table = CAFCC_DB::table($child);
            if ($wpdb->get_var($wpdb->prepare("SELECT id FROM $table WHERE $field = %d LIMIT 1", $id))) {
                return true;
            }
        }
        return false;
    }

    public static function delete($entity, $id) {
        global $wpdb;
        if (!self::admin_allowed()) {
            return self::error('Administrator access is required.', 403);
        }
        if (!in_array($entity, self::entities(), true) || !self::get($entity, $id)) {
            return self::error('Record not found.', 404);
        }
        if (class_exists('CAFCC_Explorer') && CAFCC_Explorer::has_connections($entity,$id)) {
            return self::error('This record has connected academic data. Unpublish it instead.',409);
        }
        if (self::referenced($entity, $id)) {
            return self::error('This record is in use. Unpublish questions instead of deleting progress.', 409);
        }
        return false === $wpdb->delete(CAFCC_DB::table($entity), array('id' => $id)) ? self::error('Deletion failed.', 500) : array('deleted' => true);
    }

    public static function visible_from() {
        $q = CAFCC_DB::table('questions');
        $d = CAFCC_DB::table('documents');
        $c = CAFCC_DB::table('chapters');
        $s = CAFCC_DB::table('subjects');
        return "FROM $q q INNER JOIN $d d ON d.id=q.document_id INNER JOIN $c c ON c.id=q.chapter_id
            INNER JOIN $s s ON s.id=c.subject_id";
    }

    public static function visible_where() {
        return "q.publication_status='published' AND q.verification_status='verified' AND d.verification_status='verified'
            AND d.official_url<>'' AND d.syllabus_version=c.syllabus_version" . (class_exists('CAFCC_Explorer') ? CAFCC_Explorer::visibility_guard() : '');
    }

    public static function questions($filters, $user_id) {
        global $wpdb;
        $p = CAFCC_DB::table('progress');
        $from = self::visible_from() . " LEFT JOIN $p p ON p.question_id=q.id AND p.user_id=%d";
        $where = self::visible_where();
        $args = array($user_id);
        foreach (array('subject_id' => 'c.subject_id', 'chapter_id' => 'q.chapter_id') as $key => $column) {
            if (!empty($filters[$key])) {
                $where .= " AND $column=%d";
                $args[] = $filters[$key];
            }
        }
        $total = (int) $wpdb->get_var($wpdb->prepare("SELECT COUNT(*) $from WHERE $where", $args));
        $args[] = 20;
        $args[] = ($filters['page'] - 1) * 20;
        $sql = "SELECT q.id,q.question_number,q.title,q.chapter_id,q.topic_id,c.title AS chapter_title,c.syllabus_version,
            s.code AS subject_code,d.title AS document_title,d.source_type,d.exam_attempt,d.official_url,
            COALESCE(p.status,'not_started') AS progress_status $from WHERE $where ORDER BY c.position,q.id LIMIT %d OFFSET %d";
        return array('items' => $wpdb->get_results($wpdb->prepare($sql, $args), ARRAY_A), 'total' => $total, 'per_page' => 20);
    }

    public static function set_progress($question_id, $status) {
        global $wpdb;
        if (!is_user_logged_in() || !current_user_can('read')) {
            return self::error('Sign in to save progress.', 401);
        }
        if(class_exists('CAFCC_Access')&&!CAFCC_Access::eligible())return self::error('An active approved membership is required.',403);
        if (!in_array($status, self::STATUSES, true)) {
            return self::error('Invalid progress status.');
        }
        $from = self::visible_from();
        $where = self::visible_where();
        // Recheck visibility in the write itself; no client-supplied student ID is accepted.
        $p = CAFCC_DB::table('progress');
        $result = $wpdb->query($wpdb->prepare("INSERT INTO $p (user_id,question_id,status,updated_at)
            SELECT %d,q.id,%s,%s $from WHERE $where AND q.id=%d
            ON DUPLICATE KEY UPDATE status=VALUES(status),updated_at=VALUES(updated_at)",
            get_current_user_id(), $status, current_time('mysql', true), $question_id));
        if (false === $result) {
            return self::error('Progress could not be saved.', 500);
        }
        // MySQL can report zero affected rows when the same status is saved twice.
        if (!$wpdb->get_var($wpdb->prepare("SELECT q.id $from WHERE $where AND q.id=%d", $question_id))) {
            return self::error('Published question not found.', 404);
        }
        return array('question_id' => $question_id, 'status' => $status);
    }

    public static function summary($user_id) {
        global $wpdb;
        $p = CAFCC_DB::table('progress');
        $from = self::visible_from() . " LEFT JOIN $p p ON p.question_id=q.id AND p.user_id=%d";
        $where = self::visible_where();
        $rows = $wpdb->get_results($wpdb->prepare("SELECT COALESCE(p.status,'not_started') AS status,COUNT(*) AS count $from WHERE $where GROUP BY COALESCE(p.status,'not_started')", $user_id), ARRAY_A);
        $counts = array_fill_keys(self::STATUSES, 0);
        foreach ($rows as $row) {
            $counts[$row['status']] = (int) $row['count'];
        }
        return array('counts' => $counts, 'total' => array_sum($counts));
    }
}
