<?php
defined('ABSPATH') || exit;

final class CAFCC_Academic_UI {
    public static function init() {
        add_action('rest_api_init',array(__CLASS__,'routes'));
        add_action('admin_menu',function(){
            if (CAFCC_Repository::admin_allowed()) {
                add_submenu_page('cafcc','Connected academic manager','Connected academic manager','manage_options','cafcc-connected',array(__CLASS__,'admin'));
            }
        });
        add_action('admin_enqueue_scripts',function($hook){
            if ('ca-final-command-center_page_cafcc-connected'===$hook || (isset($_GET['page']) && 'cafcc-connected'===sanitize_key(wp_unslash($_GET['page'])) && CAFCC_Repository::admin_allowed())) {
                self::assets(true);
            }
        });
    }

    private static function body($r,$limit=65536) {
        if (strlen($r->get_body())>$limit) { return CAFCC_Repository::error('Request exceeds the allowed size.',413); }
        $body=$r->get_json_params();
        return is_array($body) && $body && !array_is_list($body)?$body:CAFCC_Repository::error('Send a JSON record object.');
    }

    public static function routes() {
        $admin=function($r){return CAFCC_REST::permission($r,true);};
        $student=function($r){return CAFCC_REST::permission($r);};
        foreach (array_keys(CAFCC_Academic::definitions()) as $kind) {
            register_rest_route('cafcc/v2','/admin/'.$kind,array(
                array('methods'=>'GET','permission_callback'=>$admin,'callback'=>function($r)use($kind){
                    $page=$r->get_param('page')??1;
                    if (!is_scalar($page) || !preg_match('/^[1-9][0-9]{0,4}$/D',(string)$page)) { return CAFCC_Repository::error('Invalid page.'); }
                    return CAFCC_Academic::listing($kind,(int)$page);
                }),
                array('methods'=>'POST','permission_callback'=>$admin,'callback'=>function($r)use($kind){$body=self::body($r);return is_wp_error($body)?$body:CAFCC_Academic::save($kind,$body);})
            ));
            register_rest_route('cafcc/v2','/admin/'.$kind.'/(?P<id>[1-9][0-9]{0,17})',array('methods'=>'PATCH','permission_callback'=>$admin,'callback'=>function($r)use($kind){$body=self::body($r);return is_wp_error($body)?$body:CAFCC_Academic::save($kind,$body,(int)$r['id']);}));
        }
        foreach (array('catalog','questions','summary') as $method) {
            register_rest_route('cafcc/v2','/'.$method,array('methods'=>'GET','permission_callback'=>$student,'callback'=>function($r)use($method){
                $f=CAFCC_Explorer::filters($r); if (is_wp_error($f)) { return $f; }
                return 'catalog'===$method?CAFCC_Explorer::catalog($f):CAFCC_Explorer::$method($f,get_current_user_id());
            }));
        }
        register_rest_route('cafcc/v2','/answers/(?P<id>[1-9][0-9]{0,17})',array('methods'=>'GET','permission_callback'=>$student,'callback'=>function($r){return CAFCC_Explorer::answers((int)$r['id']);}));
        register_rest_route('cafcc/v2','/admin/import/preview',array('methods'=>'POST','permission_callback'=>$admin,'callback'=>function($r){
            $body=self::body($r,1100000);if(is_wp_error($body)){return $body;}
            if (array_diff(array_keys($body),array('type','csv'))) {return CAFCC_Repository::error('Unexpected import fields.');}
            return CAFCC_Import::preview($body['type']??null,$body['csv']??null);
        }));
        register_rest_route('cafcc/v2','/admin/import/commit',array('methods'=>'POST','permission_callback'=>$admin,'callback'=>function($r){
            $body=self::body($r);return is_wp_error($body)?$body:CAFCC_Import::commit($body['token']??null);
        }));
        register_rest_route('cafcc/v2','/admin/import/batches',array('methods'=>'GET','permission_callback'=>$admin,'callback'=>function(){
            global $wpdb;$t=CAFCC_DB::table('import_batches');return $wpdb->get_results("SELECT id,owner_id,import_type,status,created_at FROM $t ORDER BY id DESC LIMIT 100",ARRAY_A);
        }));
        register_rest_route('cafcc/v2','/admin/import/rollback/(?P<id>[1-9][0-9]{0,17})',array('methods'=>'POST','permission_callback'=>$admin,'callback'=>function($r){return CAFCC_Import::rollback((int)$r['id']);}));
        register_rest_route('cafcc/v2','/admin/review-hierarchy/(?P<id>[1-9][0-9]{0,17})',array('methods'=>'POST','permission_callback'=>$admin,'callback'=>function($r){
            $body=self::body($r);if(is_wp_error($body)){return $body;}
            if (true!==($body['source_reviewed']??false)) { return CAFCC_Repository::error('Confirm review of the source listing first.'); }
            return self::review_hierarchy((int)$r['id']);
        }));
    }

    public static function review_hierarchy($edition_id) {
        if (!CAFCC_Repository::admin_allowed()) {return CAFCC_Repository::error('Administrator access is required.',403);}
        $safe=CAFCC_Import::transactional(); if(is_wp_error($safe)){return $safe;}
        return CAFCC_Academic::transaction(function()use($edition_id){
            $ed=CAFCC_Academic::save('editions',array('review_status'=>'verified','publication_status'=>'published'),$edition_id,null,true);
            if (is_wp_error($ed)) {return $ed;}
            global $wpdb;$t=CAFCC_DB::table('taxonomy');
            $nodes=$wpdb->get_results($wpdb->prepare("SELECT * FROM $t WHERE edition_id=%d AND heading_origin='official' AND batch_id IS NULL ORDER BY FIELD(node_type,'module','chapter','unit','topic','subtopic'),id",$edition_id),ARRAY_A);
            $count=0;
            foreach($nodes as $node){
                $saved=CAFCC_Academic::save('taxonomy',array('review_status'=>'verified','publication_status'=>'published'),(int)$node['id'],null,true);
                if(is_wp_error($saved)){return $saved;} $count++;
            }
            return array('published_official_headings'=>$count,'editorial_tags'=>'Remain Draft/Needs Review until individually reviewed.');
        });
    }

    private static function assets($admin=false) {
        wp_enqueue_style('cafcc-v2',plugins_url('assets/explorer.css',CAFCC_FILE),array(),CAFCC_VERSION);
        $handle=$admin?'cafcc-manager':'cafcc-explorer';
        wp_enqueue_script($handle,plugins_url('assets/'.($admin?'manager.js':'explorer.js'),CAFCC_FILE),array(),CAFCC_VERSION,true);
        $config=array('url'=>esc_url_raw(rest_url('cafcc/v2/')),'v1'=>esc_url_raw(rest_url('cafcc/v1/')),'practice'=>esc_url_raw(rest_url('cafcc/v3/')),'nonce'=>wp_create_nonce('wp_rest'));
        if($admin){$config['definitions']=CAFCC_Academic::definitions();$config['templates']=CAFCC_Import::templates();}
        wp_localize_script($handle,$admin?'CAFCCManager':'CAFCCExplorer',$config);
    }

    public static function student() {
        if (!is_user_logged_in() || !current_user_can('read')) {return '<div class="cafcc"><p>Please <a href="'.esc_url(wp_login_url(get_permalink())).'">sign in</a> to access your CA Final dashboard.</p></div>';}
        self::assets();ob_start(); ?>
        <section class="cafcc-v2" data-cafcc-explorer aria-label="CA Final Command Center">
            <header class="cc-hero"><div><span class="cc-eyebrow">CA FINAL · YOUR STUDY WORKSPACE</span><h2>Build clarity.<br>Practise with purpose.</h2><p>Follow your syllabus. Work through reviewed questions. Make the next step yours.</p></div><span class="cc-version">Version 0.3</span></header>
            <div class="cc-summary" aria-label="Your practice progress"></div>
            <div class="cc-workspace"><aside class="cc-filters"><div class="cc-section-title"><h3>Your study path</h3><button type="button" class="cc-reset cc-quiet">Reset</button></div>
                <?php foreach(array('subject_id'=>'Subject','edition_id'=>'Syllabus edition','chapter_id'=>'Chapter','unit_id'=>'ICAI unit','topic_id'=>'Topic','subtopic_id'=>'Subtopic') as $key=>$label): ?>
                    <label><?php echo esc_html($label); ?><select data-filter="<?php echo esc_attr($key); ?>" aria-label="<?php echo esc_attr($label); ?>"><option value="">All <?php echo esc_html(strtolower($label)); ?></option></select></label>
                <?php endforeach; ?>
                <p class="cc-edition-note"></p><p class="cc-note">Official headings and editorial tags are labelled separately. Some chapters have no separately listed ICAI units.</p>
            </aside><main class="cc-results"><div class="cc-section-title"><div><span class="cc-eyebrow">QUESTION LIBRARY</span><h3>Chapter-wise question explorer</h3></div><span class="cc-result-count"></span></div>
                <p class="cc-selected-path" aria-live="polite"></p><form class="cc-search"><label class="cc-search-label">Search questions<input type="search" data-filter="search" placeholder="Permitted question text, title or number"></label><button type="submit">Search</button></form>
                <div class="cc-source-filters"><label>Exam attempt<select data-filter="exam_attempt"><option value="">All available attempts</option></select></label><label>Source<select data-filter="source_type"><option value="">All available sources</option></select></label></div>
                <label class="cc-checkbox"><input type="checkbox" data-filter="bookmarked" value="1"> My bookmarks only</label>
                <p class="cc-feedback" role="status" aria-live="polite">Loading your workspace…</p><div class="cc-question-list"></div><nav class="cc-pagination" aria-label="Question pages"></nav>
                <p class="cc-note">No repetition percentages or advanced analytics are inferred. Question text and solutions appear only when publication and rights requirements are met.</p>
            </main></div>
        </section><?php return ob_get_clean();
    }

    public static function admin() {
        if(!CAFCC_Repository::admin_allowed()){wp_die('Administrator access required.','',array('response'=>403));}
        ?>
        <div class="wrap cafcc-v2 cc-manager" id="cafcc-manager"><header class="cc-hero"><div><span class="cc-eyebrow">ACADEMIC OPERATIONS</span><h1>Connected academic manager</h1><p>Review sources, connect the syllabus and publish with confidence.</p></div></header>
            <p class="cc-admin-feedback" role="status" aria-live="polite"></p>
            <div class="cc-admin-tabs"><button type="button" data-panel="records">Taxonomy & resources</button><button type="button" data-panel="imports">CSV imports</button></div>
            <section data-pane="records"><div class="cc-toolbar"><label>Record collection<select id="cc-kind"></select></label><button type="button" id="cc-new">New record</button></div>
                <div class="cc-manager-grid"><section><div class="cc-record-search"><label>Find a record<input type="search" id="cc-record-search" placeholder="Title or stable key"></label></div><div id="cc-records"></div><div id="cc-record-pages"></div></section>
                    <form id="cc-editor"><h2 id="cc-edit-title">New record</h2><div id="cc-editor-fields"></div><button type="submit">Save record</button><p class="cc-note">Set Verified and Published only after source review. Unpublish to correct material without deleting progress. Stable identity and edition cannot be reassigned.</p></form></div>
                <section class="cc-review-box"><h2>Review bundled ICAI hierarchy</h2><p>The source catalogue arrives as Draft/Needs Review. Review the official listing and its applicability, then publish its official headings together. Editorial topics remain separate drafts.</p><label>Edition<select id="cc-review-edition"></select></label><label class="cc-checkbox"><input type="checkbox" id="cc-source-reviewed"> I checked the source listing, edition dates and applicability.</label><button type="button" id="cc-review-publish">Publish reviewed official headings</button></section>
            </section>
            <section data-pane="imports" hidden><h2>Preview → Validate → Import → Review</h2><p>Append-only UTF-8 CSV, up to 200 rows and 512 KB. Existing research always enters as Draft/Needs Review. Preview uses a rolled-back transaction and does not retain academic rows; ID gaps are normal.</p>
                <label>Import type<select id="cc-import-type"></select></label><button type="button" id="cc-template">Download CSV template</button><label>CSV file<input type="file" id="cc-csv" accept=".csv,text/csv"></label>
                <button type="button" id="cc-preview">Validate & preview</button><div id="cc-import-preview"></div><button type="button" id="cc-commit" disabled>Import validated draft batch</button>
                <h3>Recent import batches</h3><p>Withdraw a batch to remove it from student access. Rows and progress are retained. Withdrawal also hides dependent resources when their source or taxonomy path becomes unavailable.</p><div id="cc-batches"></div>
            </section>
            <p><a href="<?php echo esc_url(admin_url('admin.php?page=cafcc')); ?>">Version 0.1 records and existing data</a> remain available. Explicitly connect existing documents/questions by ID; no classifications are guessed or progress remapped.</p>
        </div><?php
    }
}
