<?php
defined('ABSPATH') || exit;

/** One private JSON-only ZIP; dependency preview and transactional item checkpoints. */
final class CAFCC_Package {
    const FORMAT='CAFCC-ACADEMIC-PACKAGE-1';
    const MAX_ZIP=8000000;
    public static function table(){global $wpdb;return $wpdb->prefix.'cafcc_academic_packages';}
    public static function items_table(){global $wpdb;return $wpdb->prefix.'cafcc_academic_package_items';}
    public static function migrate(){
        global $wpdb;$jobs=self::table();$items=self::items_table();$collate=$wpdb->get_charset_collate();
        dbDelta("CREATE TABLE $jobs (
            id bigint(20) unsigned NOT NULL AUTO_INCREMENT,
            owner_id bigint(20) unsigned NOT NULL,
            job_key varchar(40) NOT NULL,
            package_key varchar(120) NOT NULL,
            archive_sha256 varchar(64) NOT NULL,
            status varchar(24) NOT NULL DEFAULT 'preview',
            cursor_position int(10) unsigned NOT NULL DEFAULT 0,
            manifest longtext NOT NULL,
            report longtext NOT NULL,
            confirmed_at datetime DEFAULT NULL,
            created_at datetime NOT NULL,
            updated_at datetime NOT NULL,
            PRIMARY KEY  (id),
            UNIQUE KEY job_key (job_key),
            UNIQUE KEY owner_package (owner_id,package_key),
            KEY owner_status (owner_id,status)
        ) ENGINE=InnoDB $collate;");
        dbDelta("CREATE TABLE $items (
            id bigint(20) unsigned NOT NULL AUTO_INCREMENT,
            package_id bigint(20) unsigned NOT NULL,
            ordinal int(10) unsigned NOT NULL,
            kind varchar(24) NOT NULL,
            file_sha256 varchar(64) NOT NULL,
            payload longtext NOT NULL,
            status varchar(24) NOT NULL DEFAULT 'pending',
            result longtext NOT NULL,
            PRIMARY KEY  (id),
            UNIQUE KEY package_ordinal (package_id,ordinal)
        ) ENGINE=InnoDB $collate;");
        return $wpdb->get_var("SHOW TABLES LIKE '$jobs'")&&$wpdb->get_var("SHOW TABLES LIKE '$items'")?true:CAFCC_Repository::error('Academic package setup incomplete.',503);
    }
    public static function decode($encoded,$collections=true){
        if($collections){$collection=CAFCC_Collection::probe($encoded);if($collection!==null)return $collection;}
        if(!is_string($encoded)||strlen($encoded)>ceil(self::MAX_ZIP*4/3)+8)return CAFCC_Repository::error('Use an academic import ZIP under 8 MB.');
        if(!class_exists('ZipArchive'))return CAFCC_Repository::error('PHP ZIP is unavailable. Use the included numbered JSON fallback; no data was changed.',503);
        $bytes=base64_decode($encoded,true);if(!$bytes||strlen($bytes)>self::MAX_ZIP||substr($bytes,0,2)!=='PK')return CAFCC_Repository::error('Choose the Academic Import ZIP, separate from the plugin/research archive.');
        // System temporary file only: never extract into uploads, Media or a web directory.
        $file=tmpfile();if(!$file)return CAFCC_Repository::error('Private system temporary storage unavailable.',503);$zip=new ZipArchive();$opened=false;
        try{
            fwrite($file,$bytes);$path=stream_get_meta_data($file)['uri'];if($zip->open($path)!==true)throw new RuntimeException('Invalid academic ZIP.');$opened=true;
            if($zip->numFiles<2||$zip->numFiles>65)throw new RuntimeException('Use 1–64 JSON items plus manifest.json.');$files=array();$seen=array();$total=0;
            for($i=0;$i<$zip->numFiles;$i++){
                $st=$zip->statIndex($i);$name=$st['name'];$total+=$st['size'];$fold=strtolower($name);
                if(!preg_match('~^[A-Za-z0-9][A-Za-z0-9_/-]*\.json$~D',$name)||str_contains($name,'//')||isset($seen[$fold])||$st['size']>2000000||$total>24000000||!in_array($st['comp_method'],array(0,8),true)||!empty($st['encryption_method'])||($st['size']>100000&&$st['size']/max(1,$st['comp_size'])>500))throw new RuntimeException('Unsafe, duplicate, encrypted or oversized item. Choose the JSON-only Academic Import ZIP.');
                $ops=0;$attr=0;if($zip->getExternalAttributesIndex($i,$ops,$attr)&&(($attr>>16)&0170000)===0120000)throw new RuntimeException('Symlinks are not accepted.');
                $raw=$zip->getFromIndex($i,$st['size']+1);if(!is_string($raw)||strlen($raw)!==$st['size']||sprintf('%u',crc32($raw))!==sprintf('%u',$st['crc']))throw new RuntimeException('ZIP byte/CRC integrity check failed.');$files[$name]=$raw;$seen[$fold]=true;
            }
            if(empty($files['manifest.json'])||strlen($files['manifest.json'])>128000)throw new RuntimeException('Missing/big manifest.json.');$m=json_decode($files['manifest.json'],true,32,JSON_THROW_ON_ERROR);
            if(!is_array($m)||array_diff(array_keys($m),array('format','package_key','version','created_at','scope','coverage','items'))||($m['format']??'')!==self::FORMAT||!preg_match('/^[A-Za-z0-9_.:-]{2,120}$/D',$m['package_key']??'')||!is_array($m['items']??null)||!array_is_list($m['items'])||count($m['items'])!==count($files)-1)throw new RuntimeException('Invalid academic manifest or undeclared files.');
            if(!is_array($m['scope']??null)||array_diff(array_keys($m['scope']),array('subject_code','exam_attempt','edition_key'))||!in_array($m['scope']['subject_code']??'',array('FR','AFM','AUDIT','DT','IDT','IBS'),true)||!is_string($m['scope']['exam_attempt']??null)||!$m['scope']['exam_attempt'])throw new RuntimeException('Identify one package subject and examination cycle.');
            $rank=array('taxonomy'=>0,'sources'=>1,'rights'=>2,'scenarios'=>3,'questions'=>4,'mcqs'=>4);$last=-1;$ordered=array();$used=array('manifest.json'=>true);$totals=array('taxonomy'=>0,'questions'=>0,'rights'=>0);
            foreach($m['items'] as $item){
                if(!is_array($item)||array_diff(array_keys($item),array('path','kind','bytes','sha256'))||!isset($rank[$item['kind']??''])||$rank[$item['kind']]<$last||isset($used[$item['path']??''])||!isset($files[$item['path']??''])||!is_int($item['bytes']??null)||!preg_match('/^[a-f0-9]{64}$/D',$item['sha256']??''))throw new RuntimeException('Invalid dependency order, repeated path or item identity.');
                $raw=$files[$item['path']];if(strlen($raw)!==$item['bytes']||!hash_equals($item['sha256'],hash('sha256',$raw)))throw new RuntimeException('Manifest checksum mismatch: '.$item['path']);$payload=json_decode($raw,true,64,JSON_THROW_ON_ERROR);if(!is_array($payload)||array_is_list($payload))throw new RuntimeException('Each JSON item must be an object.');
                foreach((in_array($item['kind'],array('questions','mcqs'),true)?($payload['records']??array()):($item['kind']==='sources'?($payload['sources']??array()):array())) as $academic){if(!is_array($academic)||($academic['subject_code']??null)!==$m['scope']['subject_code']||($academic['exam_attempt']??null)!==$m['scope']['exam_attempt'])throw new RuntimeException('An item falls outside the declared subject/attempt.');}
                if($item['kind']==='taxonomy')$totals['taxonomy']+=count($payload['nodes']??array());if(in_array($item['kind'],array('questions','mcqs'),true))$totals['questions']+=count($payload['records']??array());if($item['kind']==='rights')$totals['rights']++;
                $last=$rank[$item['kind']];$used[$item['path']]=true;$ordered[]=array_merge($item,array('payload'=>$payload));
            }
            if($totals['taxonomy']>2000||$totals['questions']>500||$totals['rights']>1)throw new RuntimeException('Split into versioned packages of at most 2,000 headings, 500 records and one source-wide declaration.');
            if(count(array_unique(array_intersect(array_column($m['items'],'kind'),array('questions','mcqs'))))>1)throw new RuntimeException('Keep MCQ and subjective academic packages separate.');
            return array('manifest'=>$m,'items'=>$ordered,'archive_sha256'=>hash('sha256',$bytes));
        }catch(Throwable $error){return CAFCC_Repository::error($error->getMessage());}
        finally{if($opened)$zip->close();fclose($file);}
    }
    private static function proposed_taxonomy($d){
        if(!is_array($d))return $d;if(!empty($d['edition_id'])||!empty($d['classification']))return $d;$proposal=$d['ai_proposal']??array();$ed=CAFCC_Academic::by_key('editions',$proposal['historical_edition']??'');if(!$ed)return $d;
        $path=$proposal['primary_path']??array();$last=$path?end($path):null;$keys=array_merge($last?array($last['node_key']??$last['key']??''):array(),$proposal['additional_node_keys']??array());$ids=array();foreach(array_filter($keys) as $key){$n=CAFCC_Academic::by_key('taxonomy',$key);if(!$n||(int)$n['edition_id']!==(int)$ed['id'])return $d;$ids[]=(int)$n['id'];}
        if($ids){$d['edition_id']=(int)$ed['id'];$d['classification']=array_values(array_unique($ids));}return $d;
    }
    private static function declaration($p){
        if(!is_array($p)||array_diff(array_keys($p),array('declaration_key','scope'))||!preg_match('/^[A-Za-z0-9_.:-]{2,120}$/D',$p['declaration_key']??'')||!is_array($p['scope']??null))return CAFCC_Repository::error('Invalid source-wide owner declaration.');global $wpdb;$t=CAFCC_Rights::table();$id=$wpdb->get_var($wpdb->prepare("SELECT id FROM $t WHERE JSON_UNQUOTE(JSON_EXTRACT(payload,'$.declaration_key'))=%s",$p['declaration_key']));
        if($id){$g=CAFCC_Rights::get($id);if($g['state']==='active')CAFCC_Sources::associate($g);return array('created'=>0,'retained'=>1,'grant_id'=>(int)$id,'note'=>'Existing owner declaration retained. Scope corrections are made in Publication Rights, not overwritten by a package.','state'=>$g['state']);}
        $scope=$p['scope'];$scope['declaration_key']=$p['declaration_key'];$g=CAFCC_Rights::save(0,array('scope'=>$scope,'state'=>'active','confirmed'=>true));if(is_wp_error($g))return $g;return array('created'=>1,'retained'=>0,'grant_id'=>(int)$g['id'],'note'=>'Confirmed source-wide owner attestation; academic records remain unapproved.');
    }
    public static function execute_item($kind,$p){
        if($kind==='collection')return CAFCC_Collection::execute($p);
        if($kind==='mcqs')return CAFCC_MCQ::import($p);
        if($kind==='taxonomy')return CAFCC_Corpus_Import::taxonomy_execute($p);
        if($kind==='sources'){if(array_diff(array_keys($p),array('sources')))return CAFCC_Repository::error('Invalid source item.');return CAFCC_Sources::import($p['sources']??null);}
        if($kind==='rights')return self::declaration($p);
        if($kind==='scenarios'){$preview=CAFCC_Review_Tools::scenario_batch('preview',$p);if(is_wp_error($preview))return $preview;if(!$preview['can_apply'])return array('retained'=>count($p['scenarios']),'conflicts'=>$preview['conflicts'],'note'=>'Existing common-fact corrections retained.');return CAFCC_Review_Tools::scenario_batch('apply',array('token'=>$preview['token']));}
        if($kind==='questions'){
            if(array_diff(array_keys($p),array('batch_key','records'))||!is_array($p['records']??null))return CAFCC_Repository::error('Invalid question batch.');$p['records']=array_map(array(__CLASS__,'proposed_taxonomy'),$p['records']);$p['skip_existing']=true;$preview=CAFCC_Studio::import_preview($p);if(is_wp_error($preview))return $preview;if(!$preview['can_apply'])return CAFCC_Repository::error('Question batch validation: '.wp_json_encode($preview['errors']));$result=CAFCC_Studio::import_apply($preview['token']);if(is_wp_error($result))return $result;
            $result['retained_corrections']=count($preview['retained_existing']);$result['conflicts']=array_map(function($r){return array('review_id'=>$r['id'],'stable_id'=>$r['record']['stable_id'],'message'=>'Existing correction retained; use Studio comparison if reconstruction is needed.');},$preview['conflict_records']);return $result;
        }
        return CAFCC_Repository::error('Unsupported package item.');
    }
    public static function upload($encoded){
        if(is_wp_error($e=CAFCC_Studio::admin()))return $e;if(is_wp_error($e=CAFCC_Bank_DB::transactional()))return $e;$decoded=self::decode($encoded);if(is_wp_error($decoded))return $decoded;global $wpdb;$t=self::table();$owner=get_current_user_id();$m=$decoded['manifest'];$old=$wpdb->get_row($wpdb->prepare("SELECT * FROM $t WHERE owner_id=%d AND package_key=%s",$owner,$m['package_key']),ARRAY_A);
        if($old){if(!hash_equals($old['archive_sha256'],$decoded['archive_sha256']))return CAFCC_Repository::error('This package key already has different bytes. Use a new revision; prior jobs and corrections remain.',409);CAFCC_Owner::sync_package((int)$old['id']);return self::view($old);}
        $reports=array();
        if(($m['format']??'')===CAFCC_Collection::FORMAT){
            // Do not run a whole subject's SQL dry-run inside one web request.
            // Every child still uses the unchanged complete dependency/data
            // preview before its bounded draft transaction can commit.
            foreach($decoded['items']as $item)$reports[]=array('path'=>$item['path'],'kind'=>'collection','result'=>array('structure_checksums'=>'passed','record_validation'=>'pending_bounded_child_preview','publication_actions'=>0));
        }else{
            $probe=CAFCC_Academic::transaction(function()use($decoded,&$reports){foreach($decoded['items'] as $item){$r=self::execute_item($item['kind'],$item['payload']);if(is_wp_error($r))return $r;$reports[]=array('path'=>$item['path'],'kind'=>$item['kind'],'result'=>$r);}return new WP_Error('cafcc_package_preview_rollback','Validated preview; no records committed.');});
            if($probe->get_error_code()!=='cafcc_package_preview_rollback')return $probe;
        }
        return CAFCC_Academic::transaction(function()use($decoded,$m,$reports,$owner){global $wpdb;$job=array('owner_id'=>$owner,'job_key'=>wp_generate_password(40,false,false),'package_key'=>$m['package_key'],'archive_sha256'=>$decoded['archive_sha256'],'status'=>'preview','cursor_position'=>0,'manifest'=>wp_json_encode($m),'report'=>wp_json_encode(array('preview'=>$reports,'applied'=>array(),'blocking_issue'=>null)),'created_at'=>current_time('mysql',true),'updated_at'=>current_time('mysql',true));if(false===$wpdb->insert(self::table(),$job))return CAFCC_Repository::error('Could not retain import preview.',500);$id=$wpdb->insert_id;
            foreach($decoded['items'] as $i=>$item)if(false===$wpdb->insert(self::items_table(),array('package_id'=>$id,'ordinal'=>$i,'kind'=>$item['kind'],'file_sha256'=>$item['sha256'],'payload'=>wp_json_encode($item['payload']),'status'=>'pending','result'=>'{}')))return CAFCC_Repository::error('Cannot retain private import checkpoint.',500);
            if(!CAFCC_Bank_DB::audit_master('academic_package',$id,null,array('package_key'=>$m['package_key'],'archive_sha256'=>$job['archive_sha256'],'phase'=>'preview')))return CAFCC_Repository::error('Cannot retain import audit.',500);return self::view(array_merge($job,array('id'=>$id)));});
    }
    public static function view($row){global $wpdb;$m=json_decode($row['manifest'],true);$rights=$wpdb->get_var($wpdb->prepare('SELECT payload FROM '.self::items_table()." WHERE package_id=%d AND kind='rights' LIMIT 1",$row['id']));$declaration=$rights?json_decode($rights,true):null;return array('record_kind'=>($m['format']??'')===CAFCC_Collection::FORMAT?'collection':(array_filter($m['items'],function($i){return $i['kind']==='mcqs';})?'mcq':'subjective'),'id'=>(int)$row['id'],'rights_declaration'=>$declaration,'job_key'=>$row['job_key'],'package_key'=>$row['package_key'],'archive_sha256'=>$row['archive_sha256'],'status'=>$row['status'],'cursor'=>(int)$row['cursor_position'],'items'=>count($m['items']),'scope'=>$m['scope']??array(),'coverage'=>$m['coverage']??array(),'contains_rights_declaration'=>(bool)array_filter($m['items'],function($i){return $i['kind']==='rights';}),'report'=>json_decode($row['report'],true),'confirmed_at'=>$row['confirmed_at']??null,'academic_publication'=>'Needs Review only; no question approval is supplied.');}
    public static function read($key){if(is_wp_error($e=CAFCC_Studio::admin()))return $e;global $wpdb;$r=$wpdb->get_row($wpdb->prepare('SELECT * FROM '.self::table().' WHERE job_key=%s AND owner_id=%d',$key,get_current_user_id()),ARRAY_A);return $r?self::view($r):CAFCC_Repository::error('Private import not found.',404);}
    public static function step($key,$input){
        if(is_wp_error($e=CAFCC_Studio::admin()))return $e;if(!is_string($key)||!preg_match('/^[A-Za-z0-9]{40}$/D',$key)||!is_array($input)||array_diff(array_keys($input),array('cursor','confirmed','attest_rights'))||!is_int($input['cursor']??null))return CAFCC_Repository::error('Invalid import checkpoint.');
        return CAFCC_Academic::transaction(function()use($key,$input){global $wpdb;$t=self::table();$r=$wpdb->get_row($wpdb->prepare("SELECT * FROM $t WHERE job_key=%s AND owner_id=%d FOR UPDATE",$key,get_current_user_id()),ARRAY_A);if(!$r)return CAFCC_Repository::error('Private import not found.',404);$m=json_decode($r['manifest'],true);$report=json_decode($r['report'],true);$cursor=(int)$r['cursor_position'];
            if($input['cursor']<$cursor||$r['status']==='completed')return self::view($r);if($input['cursor']!==$cursor)return CAFCC_Repository::error('Import cursor changed; resume the saved checkpoint.',409);
            if($r['status']==='preview'){if(true!==($input['confirmed']??false))return CAFCC_Repository::error('Confirm the preview before applying academic drafts.');if(array_filter($m['items'],function($i){return $i['kind']==='rights';})&&true!==($input['attest_rights']??false))return CAFCC_Repository::error('Confirm the included source-wide owner attestation once, or import a package without a declaration.');$r['status']='importing';$r['confirmed_at']=current_time('mysql',true);}
            elseif($r['status']!=='importing')return CAFCC_Repository::error('This import is blocked. Retain corrections and prepare a corrected new package revision.',409);
            $it=self::items_table();$item=$wpdb->get_row($wpdb->prepare("SELECT * FROM $it WHERE package_id=%d AND ordinal=%d FOR UPDATE",$r['id'],$cursor),ARRAY_A);if(!$item)return CAFCC_Repository::error('Import checkpoint item missing.',500);
            // The item and cursor commit together. A retry never replays prior writes.
            $done=CAFCC_Academic::transaction(function()use($item){return self::execute_item($item['kind'],json_decode($item['payload'],true));});
            if(is_wp_error($done)){$r['status']='blocked';$report['blocking_issue']=array('item'=>$m['items'][$cursor]['path'],'message'=>$done->get_error_message(),'action'=>'Correct the source data or existing conflict; use a new versioned package. No student data was reset.');}
            else{$report['applied'][]=array('path'=>$m['items'][$cursor]['path'],'kind'=>$item['kind'],'result'=>$done);if(false===$wpdb->update($it,array('status'=>'applied','result'=>wp_json_encode($done)),array('id'=>$item['id'])))return CAFCC_Repository::error('Cannot save item checkpoint.',500);$r['cursor_position']=++$cursor;if($cursor===count($m['items']))$r['status']='completed';}
            $r['report']=wp_json_encode($report);$r['updated_at']=current_time('mysql',true);if(false===$wpdb->update($t,array_intersect_key($r,array_flip(array('status','cursor_position','report','confirmed_at','updated_at'))),array('id'=>$r['id'])))return CAFCC_Repository::error('Cannot save import checkpoint.',500);
            if(!CAFCC_Bank_DB::audit_master('academic_package_step',$r['id'],null,array('cursor'=>$cursor,'status'=>$r['status'])))return CAFCC_Repository::error('Cannot retain import-step audit.',500);if($r['status']==='completed'){$sync=CAFCC_Owner::sync_package((int)$r['id']);if(is_wp_error($sync))return $sync;}return self::view($r);
        });
    }
    public static function screen(){if(!CAFCC_Repository::admin_allowed())wp_die('Administrator required.');wp_enqueue_script('cafcc-package',plugins_url('assets/package.js',CAFCC_FILE),array(),CAFCC_VERSION,true);wp_localize_script('cafcc-package','CAFCCPackage',array('url'=>rest_url('cafcc/v7/admin/'),'nonce'=>wp_create_nonce('wp_rest')));echo '<div class="wrap" id="cafcc-academic-package"><h1>Import Academic Package</h1><p>Choose the compact Academic Import ZIP. It contains private JSON only. The plugin ZIP and research archive are separate. Source PDFs, permission evidence and images never go into Media.</p><label>Academic Import ZIP <input type="file" id="academic-zip" accept=".zip,application/zip"></label><div id="package-preview"></div><label style="display:block;min-height:44px"><input type="checkbox" id="package-confirm"> I reviewed this package and confirm any included source-wide rights attestation. Import all academic records as Needs Review.</label><button type="button" class="button button-primary" id="package-apply" disabled>Confirm and import academic drafts</button><button type="button" class="button" id="package-resume">Resume saved import</button><p role="status" id="package-feedback"></p><h2>Private Source Register</h2><p>Owner selection, PDF integrity, academic review and publication rights are separate. Your private Drive file references are visible only here.</p><div id="package-sources"></div></div>';}
    public static function init(){
        add_action('admin_menu',function(){if(CAFCC_Repository::admin_allowed())add_submenu_page('cafcc','Import Academic Package','Import Academic Package','manage_options','cafcc-package',array(__CLASS__,'screen'));});
        add_action('rest_api_init',function(){$p=function($r){return CAFCC_REST::permission($r,true);};register_rest_route('cafcc/v7','/admin/packages',array('methods'=>'POST','permission_callback'=>$p,'callback'=>function($r){$v=CAFCC_Studio::body($r,22000000);return is_wp_error($v)?$v:self::upload($v['base64']??null);}));register_rest_route('cafcc/v7','/admin/packages/(?P<key>[A-Za-z0-9]{40})',array(array('methods'=>'GET','permission_callback'=>$p,'callback'=>function($r){return self::read($r['key']);}),array('methods'=>'POST','permission_callback'=>$p,'callback'=>function($r){$v=CAFCC_Studio::body($r);return is_wp_error($v)?$v:self::step($r['key'],$v);})));});
        add_filter('rest_post_dispatch',function($response,$server,$request){if(str_starts_with($request->get_route(),'/cafcc/v7/')){$response->header('Cache-Control','private, no-store');$response->header('Vary','Cookie');}return $response;},10,3);
    }
}
