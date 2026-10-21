<?php
defined('ABSPATH') || exit;

final class CAFCC_Admin {
    public static function init() {
        add_action('admin_menu', function () {
            if (CAFCC_Repository::admin_allowed()) {
                add_menu_page('CA Final Command Center', 'CA Final Command Center', 'manage_options', 'cafcc',
                    array(__CLASS__, 'render'), 'dashicons-welcome-learn-more', 30);
            }
        });
        add_action('admin_enqueue_scripts', function ($hook) {
            if ('toplevel_page_cafcc' === $hook && CAFCC_Repository::admin_allowed()) {
                wp_enqueue_style('cafcc', plugins_url('assets/app.css', CAFCC_FILE), array(), CAFCC_VERSION);
                wp_enqueue_script('cafcc-admin', plugins_url('assets/admin.js', CAFCC_FILE), array(), CAFCC_VERSION, true);
                wp_localize_script('cafcc-admin', 'CAFCCAdmin', array('url' => esc_url_raw(rest_url('cafcc/v1/')),
                    'nonce' => wp_create_nonce('wp_rest'), 'fields' => array_combine(CAFCC_Repository::entities(), array_map(array('CAFCC_Repository', 'fields'), CAFCC_Repository::entities())),
                    'verification' => CAFCC_Repository::VERIFICATION, 'sources' => CAFCC_Repository::SOURCES));
            }
        });
    }

    public static function render() {
        if (!CAFCC_Repository::admin_allowed()) {
            wp_die('Administrator access is required.', '', array('response' => 403));
        }
        ?>
        <div class="wrap cafcc" id="cafcc-admin">
            <h1>CA Final Command Center</h1>
            <?php if (CAFCC_DB::legacy_counts()) : ?>
                <div class="notice notice-warning inline"><p>Prototype question/progress tables were found and preserved without changes. They are separate from this verified academic database. Existing question text and student notes need a reviewed migration; they are not automatically published or mapped to new references.</p></div>
            <?php endif; ?>
            <p>Add subjects, chapters, topics, source documents, then question references. Verify the official source before publishing a question.</p>
            <p>Only direct HTTPS ICAI resource links are accepted. No private Google Drive links. Removing verification immediately hides associated references from students.</p>
            <p id="cafcc-message" role="status" aria-live="polite"></p>
            <label for="cafcc-entity">Record type</label>
            <select id="cafcc-entity">
                <?php foreach (CAFCC_Repository::entities() as $entity) : ?>
                    <option value="<?php echo esc_attr($entity); ?>"><?php echo esc_html(ucfirst($entity)); ?></option>
                <?php endforeach; ?>
            </select>
            <button type="button" class="button" id="cafcc-new">New record</button>
            <div class="cafcc-admin-columns">
                <section aria-label="Academic records"><div id="cafcc-records"></div><div id="cafcc-pages" class="cafcc-pages"></div></section>
                <form id="cafcc-form"><h2 id="cafcc-form-title">New record</h2><div id="cafcc-fields"></div>
                    <button class="button button-primary" type="submit">Save record</button>
                </form>
            </div>
            <p>Student dashboard shortcode: <code>[ca_final_command_center]</code>. Put this on a private development page. Configure student accounts through WordPress; this plugin does not enable public registration.</p>
        </div>
        <?php
    }
}
