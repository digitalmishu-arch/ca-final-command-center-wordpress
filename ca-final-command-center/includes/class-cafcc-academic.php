<?php
defined('ABSPATH') || exit;

/** Connected academic records layered on the schema-1 question IDs. */
final class CAFCC_Academic {
    const REVIEW = array('needs_review', 'verified', 'rejected');
    const TYPES = array('unknown', 'practical', 'theory', 'mcq', 'case_study', 'case_scenario');
    const NODE_TYPES = array('module', 'chapter', 'unit', 'topic', 'subtopic');
    private static $read_cache=array();
    public static function reset_cache() { self::$read_cache=array(); }

    public static function definitions() {
        $review = array('review_status' => 'review', 'publication_status' => 'publication');
        return array(
            'editions' => array_merge(array('edition_key'=>'key', 'subject_id'=>'subjects!', 'title'=>'text!', 'edition_month'=>'month', 'reprint_month'=>'month', 'applicability'=>'long!', 'source_url'=>'url!', 'date_note'=>'long'), $review),
            'taxonomy' => array_merge(array('node_key'=>'key', 'edition_id'=>'editions!', 'subject_id'=>'subjects!', 'parent_id'=>'taxonomy', 'node_type'=>'node_type', 'title'=>'text!', 'position'=>'position', 'heading_origin'=>'origin', 'source_url'=>'url', 'source_location'=>'text'), $review),
            'documents' => array_merge(array('document_key'=>'key', 'document_id'=>'documents', 'edition_id'=>'editions!', 'title'=>'text!', 'source_type'=>'source', 'exam_attempt'=>'text!', 'official_url'=>'url!', 'issue_period'=>'text', 'mtp_series'=>'text','source_sha256'=>'sha256','source_revision'=>'text','scheme'=>'text','law_context'=>'context'), $review),
            'questions' => array_merge(array('stable_key'=>'key', 'question_id'=>'questions', 'edition_id'=>'editions!', 'primary_subject_id'=>'subjects!', 'document_id'=>'documents!', 'chapter_node_id'=>'taxonomy', 'title'=>'text!', 'question_number'=>'text!', 'question_type'=>'question_type', 'family_id'=>'families'), $review),
            'occurrences' => array_merge(array('occurrence_key'=>'key', 'question_id'=>'questions!', 'document_id'=>'documents!', 'edition_id'=>'editions!', 'page_reference'=>'text', 'question_number'=>'text!', 'subquestion_number'=>'text','document_section'=>'text', 'marks'=>'marks', 'marks_verified'=>'bool', 'question_type'=>'question_type'), $review),
            'tags' => array_merge(array('question_id'=>'questions!', 'node_id'=>'taxonomy!'), $review),
            'subject_tags' => array_merge(array('question_id'=>'questions!', 'subject_id'=>'subjects!'), $review),
            'answers' => array_merge(array('answer_key'=>'key', 'question_id'=>'questions!', 'occurrence_id'=>'occurrences', 'answer_mode'=>'answer_mode', 'answer_text'=>'answer', 'rights_basis'=>'rights', 'official_url'=>'url', 'source_location'=>'text'), $review),
            'families' => array_merge(array('family_key'=>'key', 'title'=>'text!'), $review),
            'comparisons' => array_merge(array('left_question_id'=>'questions!', 'right_question_id'=>'questions!', 'relationship'=>'comparison', 'notes'=>'rights'), $review),
            'edition_mappings' => array_merge(array('from_node_id'=>'taxonomy!', 'to_node_id'=>'taxonomy!', 'relationship'=>'mapping', 'notes'=>'rights'), $review)
        );
    }

    public static function table($kind) {
        $map = array('documents'=>'document_meta', 'questions'=>'question_meta', 'tags'=>'question_tags', 'subject_tags'=>'question_subjects');
        if (!isset(self::definitions()[$kind]) && 'import_batches' !== $kind) {
            throw new InvalidArgumentException('Unknown record collection.');
        }
        return CAFCC_DB::table($map[$kind] ?? $kind);
    }

    public static function active($alias) {
        $b = CAFCC_DB::table('import_batches');
        return "($alias.batch_id IS NULL OR EXISTS (SELECT 1 FROM $b ab WHERE ab.id=$alias.batch_id AND ab.status='committed'))";
    }

    public static function published($alias) {
        return "$alias.review_status='verified' AND $alias.publication_status='published' AND " . self::active($alias);
    }

    public static function get($kind, $id) {
        global $wpdb;
        if ('subjects' === $kind) { return CAFCC_Repository::get('subjects', $id); }
        if ('questions' === $kind) {
            $q = CAFCC_Repository::get('questions', $id);
            if (!$q) { return null; }
            $table = self::table('questions');
            $meta = $wpdb->get_row($wpdb->prepare("SELECT * FROM $table WHERE question_id=%d", $id), ARRAY_A);
            return array_merge($meta ?: array(), $q, array('question_id'=>(int)$id, 'meta_id'=>$meta['id'] ?? null));
        }
        if ('documents' === $kind) {
            $d = CAFCC_Repository::get('documents', $id);
            if (!$d) { return null; }
            $table = self::table('documents');
            $meta = $wpdb->get_row($wpdb->prepare("SELECT * FROM $table WHERE document_id=%d", $id), ARRAY_A);
            return array_merge($d, $meta ?: array(), array('id'=>(int)$id, 'document_id'=>(int)$id, 'meta_id'=>$meta['id'] ?? null));
        }
        $key=$kind.':'.$id;
        if (in_array($kind,array('taxonomy','editions'),true) && array_key_exists($key,self::$read_cache)) { return self::$read_cache[$key]; }
        $table = self::table($kind);
        $row=$wpdb->get_row($wpdb->prepare("SELECT * FROM $table WHERE id=%d", $id), ARRAY_A);
        if (in_array($kind,array('taxonomy','editions'),true)) { self::$read_cache[$key]=$row; }
        return $row;
    }

    public static function by_key($kind, $key) {
        global $wpdb;
        $field = array('editions'=>'edition_key','taxonomy'=>'node_key','documents'=>'document_key','questions'=>'stable_key','occurrences'=>'occurrence_key','answers'=>'answer_key','families'=>'family_key')[$kind] ?? null;
        if (!$field) { return null; }
        $table = self::table($kind);
        $column = array('documents'=>'document_id','questions'=>'question_id')[$kind] ?? 'id';
        $id = $wpdb->get_var($wpdb->prepare("SELECT $column FROM $table WHERE $field=%s", $key));
        return $id ? self::get($kind, $id) : null;
    }

    public static function listing($kind, $page = 1) {
        global $wpdb;
        $table = self::table($kind);
        $column = array('documents'=>'document_id','questions'=>'question_id')[$kind] ?? 'id';
        $ids = $wpdb->get_col($wpdb->prepare("SELECT $column FROM $table ORDER BY id LIMIT %d OFFSET %d", 100, ($page-1)*100));
        $rows = array_map(function ($id) use ($kind) { return self::get($kind, $id); }, $ids);
        if ('questions' === $kind) {
            foreach ($rows as &$r) {
                $r['review_status'] = 'verified' === $r['verification_status'] ? 'verified' : ('rejected' === $r['verification_status'] ? 'rejected' : 'needs_review');
                $r['chapter_node_id'] = null;
            }
            unset($r);
        }
        return array('items'=>$rows, 'total'=>(int)$wpdb->get_var("SELECT COUNT(*) FROM $table"), 'per_page'=>100);
    }

    public static function validate($kind, $input, $id = 0) {
        $defs = self::definitions()[$kind] ?? null;
        if (!$defs || !is_array($input) || array_diff(array_keys($input), array_keys($defs))) {
            return CAFCC_Repository::error('Unknown record type or unexpected fields.');
        }
        $data = array();
        $choices = array('review'=>self::REVIEW,'publication'=>array('draft','published'), 'node_type'=>self::NODE_TYPES,
            'origin'=>array('official','editorial'), 'source'=>array('exam','rtp','mtp','study_material','case_study','other'),
            'question_type'=>self::TYPES, 'answer_mode'=>array('official_link','authored','licensed'),
            'comparison'=>array('same_concept','adaptation','possible_repeat','unrelated'), 'mapping'=>array('equivalent','renamed','split','merged','removed'));
        $defaults = array('review_status'=>'needs_review','publication_status'=>'draft','node_type'=>'topic','heading_origin'=>'editorial',
            'source_type'=>'exam','question_type'=>'unknown','answer_mode'=>'official_link','position'=>0,'marks_verified'=>0);
        foreach ($defs as $key=>$rule) {
            $required = str_ends_with($rule, '!'); $type = rtrim($rule, '!');
            $value = $input[$key] ?? ($defaults[$key] ?? '');
            if (in_array($type, array('subjects','editions','taxonomy','questions','documents','occurrences','families'), true)) {
                $value = CAFCC_Repository::id($value, !$required);
                if (!is_wp_error($value) && $value && !self::get($type,$value)) {
                    return CAFCC_Repository::error('The selected ' . $key . ' does not exist.');
                }
            } elseif (isset($choices[$type])) {
                if (!is_string($value) || !in_array($value,$choices[$type],true)) { return CAFCC_Repository::error('Invalid '.$key.'.'); }
            } elseif (in_array($type,array('position','bool'),true)) {
                if (!is_scalar($value) || !preg_match('/^[0-9]{1,6}$/D',(string)$value) || ('bool'===$type && !in_array((string)$value,array('0','1'),true))) { return CAFCC_Repository::error('Invalid '.$key.'.'); }
                $value = (int)$value;
            } elseif ('marks' === $type) {
                if ('' === $value || null === $value) { $value = null; }
                elseif (!is_scalar($value) || !preg_match('/^(?:[0-9]{1,3})(?:\.[0-9]{1,2})?$/D',(string)$value) || (float)$value > 100) { return CAFCC_Repository::error('Marks must be verified, between 0 and 100, or blank.'); }
            } else {
                if (!is_string($value)) { return CAFCC_Repository::error($key.' must be text.'); }
                $value = trim($value);
                if ('url' === $type) { $value = in_array($kind,array('documents','answers'),true)?CAFCC_Sources::authorised_url($value):CAFCC_Repository::official_url($value); }
                else { $value = 'answer' === $type ? sanitize_textarea_field($value) : sanitize_text_field($value); }
                if (is_wp_error($value)) { return $value; }
                $limit = array('text'=>190,'long'=>500,'rights'=>1000,'answer'=>30000,'key'=>120,'month'=>7,'url'=>2048,'context'=>2000,'sha256'=>64)[$type] ?? 190;
                if (strlen($value)>$limit || ($required && ''===$value)) { return CAFCC_Repository::error($key.' is required or exceeds its length limit.'); }
                if ('key'===$type && !preg_match('/^[A-Za-z0-9][A-Za-z0-9_.:-]{1,119}$/D',$value)) { return CAFCC_Repository::error('Stable keys must use 2–120 letters, digits, dots, colons, hyphens or underscores.'); }
                if ('month'===$type && ''!==$value && !preg_match('/^[12][0-9]{3}-(0[1-9]|1[0-2])$/D',$value)) { return CAFCC_Repository::error('Edition dates must be YYYY-MM or blank when unknown.'); }
            }
            if (is_wp_error($value)) { return $value; }
            if(is_string($value)&&class_exists('CAFCC_Bank_DB')&&CAFCC_Bank_DB::private_reference($value))return CAFCC_Repository::error('Private Drive references must remain outside public academic records.');
            $data[$key]=$value;
        }
        if (isset($data['publication_status']) && 'published'===$data['publication_status'] && 'verified'!==$data['review_status']) { return CAFCC_Repository::error('Publication requires verification.'); }
        if ('taxonomy'===$kind) {
            $edition=self::get('editions',$data['edition_id']);
            if ((int)$edition['subject_id']!==$data['subject_id']) { return CAFCC_Repository::error('Subject and syllabus edition must match.'); }
            $parent=$data['parent_id']?self::get('taxonomy',$data['parent_id']):null;
            $allowed=array('module'=>array(), 'chapter'=>array('module'), 'unit'=>array('chapter'), 'topic'=>array('unit','chapter'), 'subtopic'=>array('topic','subtopic'));
            if ((!$parent && in_array($data['node_type'],array('unit','topic','subtopic'),true)) ||
                ($parent && (!in_array($parent['node_type'],$allowed[$data['node_type']],true) || (int)$parent['edition_id']!==$data['edition_id'] || (int)$parent['subject_id']!==$data['subject_id'])) || ($id && $data['parent_id']===$id)) {
                return CAFCC_Repository::error('Choose a valid parent in the same subject and edition.');
            }
            if ('official'===$data['heading_origin'] && !$data['source_url']) { return CAFCC_Repository::error('Official headings require a source URL.'); }
            if ('published'===$data['publication_status'] && ('verified'!==$edition['review_status'] || 'published'!==$edition['publication_status'] || ($parent && !self::row_published($parent)))) { return CAFCC_Repository::error('Publish the reviewed edition and parent first.'); }
            if ($id) {
                $old=self::get('taxonomy',$id);
                foreach (array('parent_id','edition_id','subject_id','node_type','node_key') as $key) {
                    if ((string)$old[$key] !== (string)$data[$key]) { return CAFCC_Repository::error('Structural moves require a separate node and an edition mapping. Correct titles/order in place.',409); }
                }
            }
        }
        if ('editions'===$kind && $id) {
            $old=self::get('editions',$id);
            if ($old['edition_key']!==$data['edition_key'] || (int)$old['subject_id']!==$data['subject_id']) { return CAFCC_Repository::error('Edition identity cannot be reassigned. Create a separate edition.',409); }
        }
        if('documents'===$kind&&!empty($data['source_sha256'])&&!preg_match('/^[a-f0-9]{64}$/D',$data['source_sha256']))return CAFCC_Repository::error('Source digest must be a SHA-256 or blank for legacy references.');
        if ('documents'===$kind && 'mtp'!==$data['source_type'] && $data['mtp_series']) { return CAFCC_Repository::error('MTP series applies only to MTP documents.'); }
        if ('questions'===$kind) {
            $doc=self::get('documents',$data['document_id']);
            if (empty($doc['edition_id']) || (int)$doc['edition_id']!==$data['edition_id'] || (int)self::get('editions',$data['edition_id'])['subject_id']!==$data['primary_subject_id']) { return CAFCC_Repository::error('Question, primary subject and source edition must match.'); }
            if ($data['chapter_node_id']) {
                $chapter=self::get('taxonomy',$data['chapter_node_id']);
                if ('chapter'!==$chapter['node_type'] || (int)$chapter['edition_id']!==$data['edition_id']) { return CAFCC_Repository::error('Select a chapter from the question edition.'); }
            }
            if ('published'===$data['publication_status'] && (!self::row_published($doc) || 'verified'!==$doc['verification_status'])) { return CAFCC_Repository::error('Publish and verify the source first.'); }
        }
        if ('occurrences'===$kind) {
            $q=self::get('questions',$data['question_id']); $doc=self::get('documents',$data['document_id']);
            if (empty($q['edition_id']) || empty($doc['edition_id']) || (int)$q['edition_id']!==$data['edition_id'] || (int)$doc['edition_id']!==$data['edition_id']) { return CAFCC_Repository::error('Occurrence, question and document editions must match.'); }
            if (null!==$data['marks'] && !$data['marks_verified']) { return CAFCC_Repository::error('Leave marks blank unless verified against the official source.'); }
            if ('published'===$data['publication_status'] && (!self::row_published($doc) || 'verified'!==$doc['verification_status'])) { return CAFCC_Repository::error('Publish and verify the source first.'); }
        }
        if ('tags'===$kind) {
            $q=self::get('questions',$data['question_id']); $node=self::get('taxonomy',$data['node_id']);
            if (empty($q['edition_id']) || 'module'===$node['node_type']) { return CAFCC_Repository::error('Classify a connected question using a chapter, unit, topic or subtopic.'); }
            $subject=CAFCC_Repository::get('subjects',$q['primary_subject_id']);
            if ('IBS'!==$subject['code'] && (int)$node['edition_id']!==(int)$q['edition_id']) { return CAFCC_Repository::error('Cross-subject/edition classifications are allowed only for IBS cases.'); }
            if ('published'===$data['publication_status'] && !self::path_published($node['id'])) { return CAFCC_Repository::error('Publish the reviewed hierarchy path first.'); }
        }
        if ('subject_tags'===$kind) {
            $q=self::get('questions',$data['question_id']);
            if (empty($q['primary_subject_id'])) { return CAFCC_Repository::error('Connect the question to an edition first.'); }
            $subject=CAFCC_Repository::get('subjects',$q['primary_subject_id']);
            if ('IBS'!==$subject['code'] && $data['subject_id']!==(int)$q['primary_subject_id']) { return CAFCC_Repository::error('Only IBS cases may have additional subject tags.'); }
        }
        if ('answers'===$kind) {
            if (preg_match('~(?:drive|docs)\.google\.com~i',$data['answer_text'])) { return CAFCC_Repository::error('Do not publish private Google Drive links in solutions.'); }
            if ('official_link'===$data['answer_mode'] && ($data['answer_text'] || !$data['official_url'] || !$data['source_location'])) { return CAFCC_Repository::error('Official answers require a link and location; copied answer text is not allowed in link-only mode.'); }
            if ('official_link'!==$data['answer_mode'] && (!$data['answer_text'] || !$data['rights_basis'])) { return CAFCC_Repository::error('Authored/licensed solutions require answer text and a clear authorship or reproduction-rights basis.'); }
            if ($data['occurrence_id'] && (int)self::get('occurrences',$data['occurrence_id'])['question_id']!==$data['question_id']) { return CAFCC_Repository::error('Answer occurrence must belong to the same question.'); }
        }
        if ('edition_mappings'===$kind) {
            $from=self::get('taxonomy',$data['from_node_id']); $to=self::get('taxonomy',$data['to_node_id']);
            if ($data['from_node_id']===$data['to_node_id'] || $from['edition_id']===$to['edition_id'] || $from['subject_id']!==$to['subject_id']) { return CAFCC_Repository::error('Historical mappings require distinct editions of the same subject.'); }
        }
        if ('comparisons'===$kind && $data['left_question_id'] >= $data['right_question_id']) { return CAFCC_Repository::error('Choose two distinct questions, lower ID first. No repeat percentage is inferred.'); }
        return $data;
    }

    public static function row_published($row) {
        if (!$row || 'verified'!==($row['review_status']??'') || 'published'!==($row['publication_status']??'')) { return false; }
        if (!empty($row['batch_id'])) {
            global $wpdb; $table=CAFCC_DB::table('import_batches');
            return 'committed'===$wpdb->get_var($wpdb->prepare("SELECT status FROM $table WHERE id=%d",$row['batch_id']));
        }
        return true;
    }

    public static function path_published($node_id) {
        for ($depth=0;$node_id && $depth<12;$depth++) {
            $node=self::get('taxonomy',$node_id);
            if (!self::row_published($node) || !self::row_published(self::get('editions',$node['edition_id']))) { return false; }
            $node_id=$node['parent_id'];
        }
        return !$node_id;
    }

    private static $transaction_depth=0;
    public static function transaction($callback) {
        global $wpdb;$depth=self::$transaction_depth++;$savepoint='cafcc_nested_'.$depth;
        $begun=$wpdb->query($depth?'SAVEPOINT '.$savepoint:'START TRANSACTION');
        try {
            if(false===$begun)return CAFCC_Repository::error('Cannot start academic transaction.',500);
            $result=$callback();
            if(is_wp_error($result)){$wpdb->query($depth?'ROLLBACK TO SAVEPOINT '.$savepoint:'ROLLBACK');self::reset_cache();return $result;}
            if(false===$wpdb->query($depth?'RELEASE SAVEPOINT '.$savepoint:'COMMIT')){$wpdb->query($depth?'ROLLBACK TO SAVEPOINT '.$savepoint:'ROLLBACK');self::reset_cache();return CAFCC_Repository::error('The database transaction failed.',500);}
            return $result;
        }catch(Throwable $e){$wpdb->query($depth?'ROLLBACK TO SAVEPOINT '.$savepoint:'ROLLBACK');self::reset_cache();return CAFCC_Repository::error('The academic operation failed; no batch was committed.',500);}
        finally{self::$transaction_depth--;}
    }

    public static function save($kind,$input,$id=0,$batch_id=null,$inside_transaction=false) {
        global $wpdb;
        if (!CAFCC_Repository::admin_allowed()) { return CAFCC_Repository::error('Administrator access is required.',403); }
        $defs=self::definitions()[$kind]??null;
        if (!$defs || !is_array($input) || array_diff(array_keys($input),array_keys($defs))) { return CAFCC_Repository::error('Unexpected academic fields.'); }
        $old=$id?self::get($kind,$id):null;
        if ($id && !$old) { return CAFCC_Repository::error('Academic record not found.',404); }
        if ($old) {
            if (!empty($old['batch_id'])) {
                $b=CAFCC_DB::table('import_batches');
                if ('committed'!==$wpdb->get_var($wpdb->prepare("SELECT status FROM $b WHERE id=%d",$old['batch_id']))) { return CAFCC_Repository::error('This import batch was withdrawn. Create a new reviewed record.',409); }
            }
            if ('questions'===$kind) { $old['review_status']='verified'===$old['verification_status']?'verified':('rejected'===$old['verification_status']?'rejected':'needs_review'); }
            $input=array_merge(array_intersect_key($old,$defs),$input);
        }
        $data=self::validate($kind,$input,$id);
        if (is_wp_error($data)) { return $data; }
        if (!$inside_transaction) { $safe=CAFCC_Import::transactional(); if (is_wp_error($safe)) { return $safe; } }
        $write=function () use ($kind,$data,$id,$batch_id,$old) {
            global $wpdb;
            $table=self::table($kind); $row=$data; $where=array('id'=>$id);
            if ('documents'===$kind) {
                if ($old && ((int)$old['edition_id']!==$data['edition_id'] || $old['document_key']!==$data['document_key'])) { return CAFCC_Repository::error('Document edition and stable key cannot be reassigned.',409); }
                if ($old && $old['official_url']!==$data['official_url']) {
                    $ot=CAFCC_DB::table('occurrences');
                    if ($wpdb->get_var($wpdb->prepare("SELECT id FROM $ot WHERE document_id=%d LIMIT 1",$id))) { return CAFCC_Repository::error('This source has recorded appearances. Add a corrected source/occurrence and unpublish the incorrect one; its progress is retained.',409); }
                }
                $base=array_intersect_key($data,array_flip(array('title','source_type','exam_attempt','official_url')));
                $base['syllabus_version']=$old['syllabus_version']??self::get('editions',$data['edition_id'])['edition_key'];
                $base['verification_status']='verified'===$data['review_status']?'verified':('rejected'===$data['review_status']?'rejected':'unverified');
                if (!$old && !empty($data['document_id'])) {
                    $existing=self::get('documents',$data['document_id']);
                    if (!empty($existing['meta_id'])) { return CAFCC_Repository::error('This document is already connected.',409); }
                    $saved=$existing; // Add explicit edition metadata without rewriting the old document.
                } else { $saved=CAFCC_Repository::save('documents',$base,$id); }
                if (is_wp_error($saved)) { return $saved; }
                $id=(int)$saved['id'];
                $row=array_intersect_key($data,array_flip(array('document_key','edition_id','issue_period','mtp_series','source_sha256','source_revision','scheme','law_context','review_status','publication_status')));if($old&&!empty($old['source_sha256'])&&$old['source_sha256']!==$data['source_sha256'])return CAFCC_Repository::error('Source bytes are immutable. Create a separate source revision and retain the old occurrence IDs.',409);
                $row['document_id']=$id; $where=array('document_id'=>$id);
            } elseif ('questions'===$kind) {
                if ($old && ($old['stable_key']!==$data['stable_key'] || (int)$old['edition_id']!==$data['edition_id'] || (int)$old['primary_subject_id']!==$data['primary_subject_id'] || (int)$old['question_id']!==(int)$data['question_id'])) { return CAFCC_Repository::error('Stable question identity and edition cannot be reassigned.',409); }
                $linked=$data['question_id']?CAFCC_Repository::get('questions',$data['question_id']):null;
                if (!$old && $linked) {
                    $meta=self::get('questions',$linked['id']);
                    if (!empty($meta['meta_id']) || (int)$linked['document_id']!==$data['document_id']) { return CAFCC_Repository::error('The selected question is already connected or has a different primary document.',409); }
                    // Explicit classification adds metadata only; no existing record is rewritten.
                    $id=(int)$linked['id'];
                } else {
                    $chapter_id=$old['chapter_id']??null;
                    if (!$chapter_id) {
                        $node=$data['chapter_node_id']?self::get('taxonomy',$data['chapter_node_id']):null;
                        $chapter=CAFCC_Repository::save('chapters',array('subject_id'=>$data['primary_subject_id'],'title'=>$node?$node['title']:'Case references (editorial collection)',
                            'syllabus_version'=>self::get('editions',$data['edition_id'])['edition_key'],'position'=>0));
                        if (is_wp_error($chapter)) { return $chapter; }
                        $chapter_id=(int)$chapter['id'];
                    }
                    $base=array('document_id'=>$data['document_id'],'chapter_id'=>$chapter_id,'topic_id'=>$old['topic_id']??null,'title'=>$data['title'],
                        'question_number'=>$data['question_number'],'verification_status'=>'verified'===$data['review_status']?'verified':('rejected'===$data['review_status']?'rejected':'unverified'), 'publication_status'=>$data['publication_status']);
                    $saved=CAFCC_Repository::save('questions',$base,$id);
                    if (is_wp_error($saved)) { return $saved; }
                    $id=(int)$saved['id'];
                }
                $row=array_intersect_key($data,array_flip(array('stable_key','edition_id','primary_subject_id','question_type','family_id')));
                $row['question_id']=$id; $where=array('question_id'=>$id);
            } elseif ('occurrences'===$kind) {
                $doc=self::get('documents',$data['document_id']);
                $identity=array($doc['official_url'],$data['edition_id'],strtolower(trim($data['page_reference'])),strtolower(trim($data['question_number'])),strtolower(trim($data['subquestion_number'])));if(!empty($doc['source_sha256']))$identity[]='sha256:'.$doc['source_sha256'];if(!empty($data['document_section']))$identity[]='section:'.$data['document_section'];$row['location_hash']=hash('sha256',implode('|',$identity));
            }
            if (!$old) { $row['batch_id']=$batch_id; }
            $suppressed=$wpdb->suppress_errors(true);
            try { $result=$old?$wpdb->update($table,$row,$where):$wpdb->insert($table,$row); }
            finally { $wpdb->suppress_errors($suppressed); }
            if (false===$result) { return CAFCC_Repository::error('Duplicate key, duplicate source occurrence or invalid academic record.',409); }
            self::reset_cache();
            $record_id=in_array($kind,array('documents','questions'),true)?$id:($id?:$wpdb->insert_id);
            if ('taxonomy'===$kind && class_exists('CAFCC_Bank_DB')) { $indexed=$old?CAFCC_Bank_DB::rebuild_closure():CAFCC_Bank_DB::index_node($record_id); if(is_wp_error($indexed))return $indexed; }
            if(($old||$kind!=='taxonomy')&&class_exists('CAFCC_Studio'))CAFCC_Studio::invalidate($kind,$record_id);
            $saved=self::get($kind,$record_id);if(class_exists('CAFCC_Bank_DB')&&!CAFCC_Bank_DB::audit_master($kind,$record_id,$old,$saved))return CAFCC_Repository::error('Cannot retain academic master history.',500);
            return $saved;
        };
        return $inside_transaction?$write():self::transaction($write);
    }
}
