<?php
defined('ABSPATH') || exit;

final class CAFCC_Frontend {
    public static function init() {
        add_shortcode('ca_final_command_center', array(__CLASS__, 'render'));
        add_shortcode('cafcc_dashboard', array(__CLASS__, 'render'));
        add_action('template_redirect', function () {
            $post = get_queried_object();
            if ($post instanceof WP_Post && (has_shortcode($post->post_content, 'ca_final_command_center') || has_shortcode($post->post_content, 'cafcc_dashboard'))) {
                self::no_cache();
            }
        });
    }

    private static function no_cache() {
        if (!defined('DONOTCACHEPAGE')) {
            define('DONOTCACHEPAGE', true);
        }
        if (!headers_sent()) {
            nocache_headers();
        }
    }

    public static function render() {
        self::no_cache();
        if (!is_user_logged_in() || !current_user_can('read')) {
            return '<div class="cafcc"><p>Please <a href="' . esc_url(wp_login_url(get_permalink())) . '">sign in</a> to access your CA Final dashboard.</p></div>';
        }
        wp_enqueue_style('cafcc', plugins_url('assets/app.css', CAFCC_FILE), array(), CAFCC_VERSION);
        wp_enqueue_script('cafcc-student', plugins_url('assets/student.js', CAFCC_FILE), array(), CAFCC_VERSION, true);
        wp_localize_script('cafcc-student', 'CAFCCStudent', array('url' => esc_url_raw(rest_url('cafcc/v1/')), 'nonce' => wp_create_nonce('wp_rest')));
        ob_start();
        ?>
        <section class="cafcc cafcc-student" aria-label="CA Final Command Center">
            <h2>CA Final Command Center</h2>
            <p>Your practice progress, saved to your account.</p>
            <p class="cafcc-message" role="status" aria-live="polite">Loading your dashboard…</p>
            <div class="cafcc-summary" aria-label="Your progress"></div>
            <h3>Chapter-wise question explorer</h3>
            <div class="cafcc-filters">
                <label>Subject<select class="cafcc-subject"><option value="">All subjects</option></select></label>
                <label>Chapter<select class="cafcc-chapter"><option value="">All chapters</option></select></label>
            </div>
            <div class="cafcc-questions"></div>
            <div class="cafcc-pages"></div>
            <p class="cafcc-muted">Advanced analytics are unavailable in version 0.1.0. Only verified, published question references appear here.</p>
        </section>
        <?php
        return ob_get_clean();
    }
}
