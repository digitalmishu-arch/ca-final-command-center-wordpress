<?php
defined('ABSPATH') || exit;
/** Bounded, previewed draft loading; never changes an existing owner taxonomy row. */
final class CAFCC_Topic_Proposals {
    public static function init(){
        add_action('admin_menu',function(){add_submenu_page('cafcc','Editorial topic proposals','Topic proposals','manage_options','cafcc-proposals',array(__CLASS__,'screen'));});
        add_action('admin_post_cafcc_proposals',function(){if(!CAFCC_Repository::admin_allowed()||!isset($_POST['_wpnonce'])||!is_string($_POST['_wpnonce'])||!wp_verify_nonce(wp_unslash($_POST['_wpnonce']),'cafcc_proposals'))wp_die('Secure administrator request required.','',array('response'=>403));$token=$_POST['token']??null;$r=$token?CAFCC_Import::commit(is_string($token)?$token:''):self::preview();if(is_wp_error($r))wp_die(esc_html($r->get_error_message()));set_transient('cafcc_proposal_panel_'.get_current_user_id(),$token?array('applied'=>$r):$r,1800);wp_safe_redirect(admin_url('admin.php?page=cafcc-proposals'));exit;});
    }
    public static function bundle(){return json_decode(file_get_contents(dirname(__DIR__).'/data/editorial-navigation-proposals.json'),true);}
    public static function preview(){
        if(!CAFCC_Repository::admin_allowed())return CAFCC_Repository::error('Administrator access required.',403);$bundle=self::bundle();$pending=array();$known=array();
        foreach($bundle['nodes'] as $n){if(CAFCC_Academic::by_key('taxonomy',$n['node_key']))continue;if(!isset($known[$n['parent_key']])&&!CAFCC_Academic::by_key('taxonomy',$n['parent_key']))continue;$pending[]=$n;$known[$n['node_key']]=true;if(count($pending)===100)break;}
        if(!$pending)return array('remaining'=>0,'message'=>'No remaining loadable proposals. Existing rows and owner corrections are retained. Review unresolved unit/edition entries separately.');
        $stream=fopen('php://temp','r+');$headers=CAFCC_Import::templates()['hierarchy'];fputcsv($stream,$headers,',','"','');foreach($pending as $n)fputcsv($stream,array_map(function($k)use($n){return $n[$k];},$headers),',','"','');rewind($stream);$csv=stream_get_contents($stream);fclose($stream);$r=CAFCC_Import::preview('hierarchy',$csv);if(!is_wp_error($r))$r['proposal_count']=count($pending);return $r;
    }
    public static function screen(){
        if(!CAFCC_Repository::admin_allowed())wp_die('Administrator access required.');$b=self::bundle();echo '<div class="wrap"><h1>Editorial topic proposals</h1><p>'.esc_html(count($b['nodes'])).' source-derived navigation proposals. These are Editorial, Needs Review and Draft. They supplement the retained official chapter/unit catalogue. They do not classify or publish questions. Historical editions are separate; current proposals must not be applied to old papers.</p><p>Load at most 100 missing entries per reviewed batch. Existing keys and corrections are never overwritten. Some official unit parents and wrapped headings remain unresolved; the exception list is available in the private delivery package.</p><form method="post" action="'.esc_url(admin_url('admin-post.php')).'">'.wp_nonce_field('cafcc_proposals','_wpnonce',true,false).'<input type="hidden" name="action" value="cafcc_proposals"><button class="button">Preview next draft batch</button></form>';
        $r=get_transient('cafcc_proposal_panel_'.get_current_user_id());if($r){echo '<pre style="white-space:pre-wrap;max-width:900px">'.esc_html(wp_json_encode($r,JSON_PRETTY_PRINT)).'</pre>';if(isset($r['token']))echo '<form method="post" action="'.esc_url(admin_url('admin-post.php')).'">'.wp_nonce_field('cafcc_proposals','_wpnonce',true,false).'<input type="hidden" name="action" value="cafcc_proposals"><input type="hidden" name="token" value="'.esc_attr($r['token']).'"><button class="button button-primary">Apply previewed entries as Draft</button></form>';}
        echo '<p>Use the connected Academic Manager to inspect source evidence and approve each proposed path. Student topic suggestions require eligible published questions.</p></div>';
    }
}
