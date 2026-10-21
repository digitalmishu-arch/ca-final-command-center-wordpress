<?php
/**
 * Plugin Name: CA Final Command Center
 * Description: Academic question references and private student progress for CA Final.
 * Version: 0.1.0
 * Requires at least: 6.6
 * Requires PHP: 8.1
 * Author: CA Final Command Center
 * License: GPL-2.0-or-later
 * Text Domain: ca-final-command-center
 */

defined('ABSPATH') || exit;
define('CAFCC_VERSION', '0.1.0');
define('CAFCC_FILE', __FILE__);
foreach (array('db', 'repository', 'rest', 'admin', 'frontend') as $cafcc_component) {
    require_once __DIR__ . '/includes/class-cafcc-' . $cafcc_component . '.php';
}
register_activation_hook(__FILE__, array('CAFCC_DB', 'activate'));
add_action('plugins_loaded', function () {
    if (CAFCC_DB::VERSION !== get_option('cafcc_db_version')) {
        CAFCC_DB::migrate();
    }
    CAFCC_REST::init();
    CAFCC_Admin::init();
    CAFCC_Frontend::init();
});
// Intentionally no destructive deactivation or uninstall hook.
