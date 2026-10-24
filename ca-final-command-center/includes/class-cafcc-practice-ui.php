<?php
defined('ABSPATH') || exit;

/** A small rights editor alongside (not replacing) the academic manager. */
final class CAFCC_Practice_UI {
    public static function init() {
        add_action('admin_menu',function(){
            if(CAFCC_Repository::admin_allowed()){add_submenu_page('cafcc','Practice content & rights','Practice content & rights','manage_options','cafcc-practice',array(__CLASS__,'admin'));}
        });
        add_action('admin_enqueue_scripts',function(){
            if(isset($_GET['page']) && 'cafcc-practice'===sanitize_key(wp_unslash($_GET['page'])) && CAFCC_Repository::admin_allowed()){
                wp_enqueue_style('cafcc-practice-admin',plugins_url('assets/explorer.css',CAFCC_FILE),array(),CAFCC_VERSION);
                wp_enqueue_script('cafcc-practice-admin',plugins_url('assets/practice-admin.js',CAFCC_FILE),array(),CAFCC_VERSION,true);
                wp_localize_script('cafcc-practice-admin','CAFCCPractice',array('url'=>esc_url_raw(rest_url('cafcc/v3/')),'nonce'=>wp_create_nonce('wp_rest')));
            }
        });
    }

    public static function admin() {
        if(!CAFCC_Repository::admin_allowed()){wp_die('Administrator access required.','',array('response'=>403));}
        ?>
        <div class="wrap cafcc-v2" id="cc-practice-admin"><header class="cc-hero"><div><span class="cc-eyebrow">PERMITTED CONTENT</span><h1>Practice content & rights</h1><p>Write original material or record a licence before publishing full text.</p></div></header>
        <p>The connected academic manager still controls the question reference and syllabus. This editor adds permitted text to its existing question ID. Research PDFs are never imported here.</p>
        <p id="pc-feedback" role="status" aria-live="polite"></p><div class="cc-manager-grid"><section><button type="button" id="pc-new">New content</button><div id="pc-records"></div><button type="button" id="pc-prev">Previous</button><button type="button" id="pc-next">Next</button></section>
        <form id="pc-editor"><h2 id="pc-title">New content</h2><label>Existing question ID<input name="question_id" type="number" min="1" required></label>
        <label>Content<select name="content_kind"><option value="question">Question</option><option value="answer">Answer / solution</option></select></label>
        <label>Publication rights<select name="rights_type"><option value="reference_only">Reference only — no copied text</option><option value="original">Independently authored by us</option><option value="licensed">Appropriately licensed material</option></select></label>
        <label>Author / permitted credit<input name="author_name" maxlength="190"></label><label>Source / answer location<input name="source_location" maxlength="190"></label>
        <label>Authorship or licence evidence<textarea name="rights_basis" rows="3" maxlength="2000" placeholder="Record who wrote this or the licence and scope permitting website reproduction."></textarea></label>
        <label>Licence expiry, if any<input name="rights_expires" type="date"></label>
        <label for="pc_body_html">Question text or solution</label>
        <?php wp_editor('', 'pc_body_html',array('textarea_name'=>'body_html','media_buttons'=>false,'textarea_rows'=>14,'quicktags'=>true,'tinymce'=>array('extended_valid_elements'=>'math[display],mi,mn,mo,mrow,mfrac,msqrt,msup,msub,mtable,mtr,mtd,mtext,msubsup,munder,mover'))); ?>
        <button type="button" id="pc-table">Insert table template</button><button type="button" id="pc-calculation">Insert calculation</button>
        <p>Tables, superscripts/subscripts and native MathML are supported. Keep the answer in a separate Answer record. Source availability does not grant reproduction permission.</p>
        <label>Answer choices, for questions only — one per line<textarea name="choice_lines" rows="4" placeholder="A | First choice&#10;B | Second choice"></textarea></label>
        <button type="submit">Save as Draft / Needs Review</button><label><input type="checkbox" id="pc-confirm"> I checked this exact revision, its author/licence, reproduction scope and expiry. I approve this text for student publication.</label><button type="button" id="pc-approve" disabled>Approve this revision</button>
        <p>Every edit withdraws its previous approval and preserves the revision history. The academic question must also be verified and published. Empty or unlicensed reference-only records show only metadata and official links.</p><h3>Saved safe preview</h3><div id="pc-preview" class="cc-rich-content"></div></form></div></div>
        <?php
    }
}
