<?php
defined('ABSPATH') || exit;

final class CAFCC_REST {
    public static function init() {
        add_action('rest_api_init', array(__CLASS__, 'routes'));
    }

    public static function permission($request, $admin = false) {
        if (CAFCC_DB::VERSION !== get_option('cafcc_db_version')) {
            return CAFCC_Repository::error('Academic database setup is incomplete.', 503);
        }
        if (!is_user_logged_in() || !current_user_can('read')) {
            return CAFCC_Repository::error('Please sign in.', 401);
        }
        // Require a REST nonce for reads and writes, even with application passwords.
        if (!wp_verify_nonce($request->get_header('X-WP-Nonce'), 'wp_rest')) {
            return CAFCC_Repository::error('Your session expired. Reload this page.', 403);
        }
        if ($admin && !CAFCC_Repository::admin_allowed()) {
            return CAFCC_Repository::error('Administrator access is required.', 403);
        }
        if(!$admin && class_exists('CAFCC_Access')&&!CAFCC_Access::eligible())return CAFCC_Repository::error('Verified email, administrator approval and an active membership entitlement are required.',403);
        return true;
    }

    public static function routes() {
        $student = function ($request) { return self::permission($request); };
        $admin = function ($request) { return self::permission($request, true); };
        foreach (CAFCC_Repository::entities() as $entity) {
            register_rest_route('cafcc/v1', '/admin/' . $entity, array(
                array('methods' => 'GET', 'permission_callback' => $admin, 'callback' => function ($r) use ($entity) {
                    $page = self::page($r);
                    return is_wp_error($page) ? $page : CAFCC_Repository::listing($entity, $page);
                }),
                array('methods' => 'POST', 'permission_callback' => $admin, 'callback' => function ($r) use ($entity) {
                    $data = self::body($r);
                    return is_wp_error($data) ? $data : CAFCC_Repository::save($entity, $data);
                })
            ));
            register_rest_route('cafcc/v1', '/admin/' . $entity . '/(?P<id>[1-9][0-9]{0,17})', array(
                array('methods' => 'PATCH', 'permission_callback' => $admin, 'callback' => function ($r) use ($entity) {
                    $data = self::body($r);
                    if (!is_wp_error($data) && class_exists('CAFCC_Explorer')) {
                        $valid=CAFCC_Explorer::validate_v1_change($entity,(int)$r['id'],$data);
                        if (is_wp_error($valid)) { return $valid; }
                    }
                    return is_wp_error($data) ? $data : CAFCC_Repository::save($entity, $data, (int) $r['id']);
                }),
                array('methods' => 'DELETE', 'permission_callback' => $admin, 'callback' => function ($r) use ($entity) {
                    return CAFCC_Repository::delete($entity, (int) $r['id']);
                })
            ));
        }
        register_rest_route('cafcc/v1', '/catalog', array('methods' => 'GET', 'permission_callback' => $student,
            'callback' => array(__CLASS__, 'catalog')));
        register_rest_route('cafcc/v1', '/questions', array('methods' => 'GET', 'permission_callback' => $student,
            'callback' => function ($r) {
                $filters = array('page' => self::page($r));
                if (is_wp_error($filters['page'])) {
                    return $filters['page'];
                }
                foreach (array('subject_id', 'chapter_id') as $key) {
                    $filters[$key] = CAFCC_Repository::id($r->get_param($key), true);
                    if (is_wp_error($filters[$key])) {
                        return $filters[$key];
                    }
                }
                return CAFCC_Repository::questions($filters, get_current_user_id());
            }));
        register_rest_route('cafcc/v1', '/summary', array('methods' => 'GET', 'permission_callback' => $student,
            'callback' => function () { return CAFCC_Repository::summary(get_current_user_id()); }));
        register_rest_route('cafcc/v1', '/progress/(?P<id>[1-9][0-9]{0,17})', array('methods' => 'PUT', 'permission_callback' => $student,
            'callback' => function ($r) {
                $data = self::body($r);
                if (is_wp_error($data)) {
                    return $data;
                }
                if (array_keys($data) !== array('status') || !is_string($data['status'])) {
                    return CAFCC_Repository::error('Send only a progress status.');
                }
                return CAFCC_Repository::set_progress((int) $r['id'], $data['status']);
            }));
        add_filter('rest_post_dispatch', array(__CLASS__, 'private_response'), 10, 3);
    }

    public static function private_response($response, $server, $request) {
        if ((str_starts_with($request->get_route(), '/cafcc/v1/') || str_starts_with($request->get_route(), '/cafcc/v2/') || str_starts_with($request->get_route(), '/cafcc/v3/') || str_starts_with($request->get_route(), '/cafcc/v4/') || str_starts_with($request->get_route(), '/cafcc/v5/'))) {
            $response->header('Cache-Control', 'private, no-store, max-age=0');
            $response->header('Vary', 'Cookie, X-WP-Nonce');
        }
        return $response;
    }

    private static function page($request) {
        $page = $request->get_param('page') ?? 1;
        if (!is_scalar($page) || !preg_match('/^[1-9][0-9]{0,4}$/D', (string) $page)) {
            return CAFCC_Repository::error('Page must be between 1 and 99999.');
        }
        return (int) $page;
    }

    private static function body($request) {
        if (strlen($request->get_body()) > 16384) {
            return CAFCC_Repository::error('Record requests must be smaller than 16 KB.', 413);
        }
        $data = $request->get_json_params();
        if (!is_array($data) || !$data || array_is_list($data)) {
            return CAFCC_Repository::error('Send one JSON record object.');
        }
        return $data;
    }

    public static function catalog() {
        global $wpdb;
        $s = CAFCC_DB::table('subjects');
        $c = CAFCC_DB::table('chapters');
        // Expose chapter labels only when a verified published reference exists.
        $from = CAFCC_Repository::visible_from();
        $where = CAFCC_Repository::visible_where();
        return array('subjects' => $wpdb->get_results("SELECT id,code,name FROM $s ORDER BY id", ARRAY_A),
            'chapters' => $wpdb->get_results("SELECT id,subject_id,title,syllabus_version,position FROM $c WHERE id IN (SELECT q.chapter_id $from WHERE $where) ORDER BY position,id", ARRAY_A));
    }
}
