<?php
defined('ABSPATH') || exit;

final class CAFCC_Frontend {
    public static function init() {
        add_shortcode('ca_final_command_center', array(__CLASS__, 'render'));
        add_shortcode('cafcc_dashboard', array(__CLASS__, 'render'));
        add_action('wp_enqueue_scripts',function(){wp_enqueue_style('cafcc-v2',plugins_url('assets/explorer.css',CAFCC_FILE),array(),CAFCC_VERSION);});
        add_action('template_redirect', function () {
            $post = get_queried_object();
            if ($post instanceof WP_Post && (has_shortcode($post->post_content, 'ca_final_command_center') || has_shortcode($post->post_content, 'cafcc_dashboard') || has_shortcode($post->post_content, 'cafcc_portal'))) {
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
        return CAFCC_Portal::render();
    }
}
