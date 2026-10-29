<?php
defined('ABSPATH') || exit;

/** One private subject delivery: bounded existing Academic ZIPs plus inert review files. */
final class CAFCC_Collection {
    const FORMAT='CAFCC-ACADEMIC-COLLECTION-1';
    const MAX_ZIP=16000000;
    public static function probe($encoded){
        if(!is_string($encoded)||strlen($encoded)>ceil(self::MAX_ZIP*4/3)+8)return null;
        if(!class_exists('ZipArchive'))return null;$raw=base64_decode($encoded,true);if(!$raw||strlen($raw)>self::MAX_ZIP)return null;
        $f=tmpfile();if(!$f)return null;$z=new ZipArchive();$opened=false;
        try{
            fwrite($f,$raw);if($z->open(stream_get_meta_data($f)['uri'])!==true)return null;$opened=true;
            $st=$z->statName('manifest.json');if(!$st||$st['size']>1000000)return null;
            $m=json_decode($z->getFromName('manifest.json'),true);if(($m['format']??'')!==self::FORMAT)return null;
            return self::decode($z,$m,hash('sha256',$raw));
        }catch(Throwable $e){return CAFCC_Repository::error($e->getMessage());}
        finally{if($opened)$z->close();fclose($f);}
    }
    private static function decode($z,$m,$hash){
        if(array_diff(array_keys($m),array('format','package_key','version','created_at','subject_code','packages','attachments','coverage'))||!preg_match('/^[A-Za-z0-9_.:-]{2,120}$/D',$m['package_key']??'')||!in_array($m['subject_code']??'',array('FR','AFM','AUDIT','DT','IDT','IBS'),true)||!is_array($m['packages']??null)||!array_is_list($m['packages'])||count($m['packages'])<1||count($m['packages'])>100||!is_array($m['attachments']??null)||!array_is_list($m['attachments'])||$z->numFiles>3000)throw new RuntimeException('Invalid single-subject collection manifest.');
        $declared=array_merge($m['packages'],$m['attachments']);if(count($declared)!==$z->numFiles-1)throw new RuntimeException('Every collection member must be declared.');
        $names=array('manifest.json'=>true);$files=array();$total=0;$imports=array_fill_keys(array_column($m['packages'],'path'),true);
        foreach($declared as $entry){
            if(!is_array($entry)||array_diff(array_keys($entry),array('path','bytes','sha256'))||!preg_match('~^[A-Za-z0-9][A-Za-z0-9_/-]*\.(?:json|zip|xlsx|html|csv|txt|png)$~D',$entry['path']??'')||str_contains($entry['path'],'//')||strlen($entry['path'])>240||!is_int($entry['bytes']??null)||!preg_match('/^[a-f0-9]{64}$/D',$entry['sha256']??''))throw new RuntimeException('Invalid collection path or checksum.');
            $name=$entry['path'];$fold=strtolower($name);$st=$z->statName($name);if(isset($names[$fold])||!$st||$st['size']!==$entry['bytes']||$st['size']>8000000||!in_array($st['comp_method'],array(0,8),true)||!empty($st['encryption_method'])||($st['size']>100000&&$st['size']/max(1,$st['comp_size'])>500))throw new RuntimeException('Unsafe or oversized collection member.');
            $total+=$st['size'];if($total>64000000)throw new RuntimeException('Collection expanded size exceeds 64 MB.');$ops=0;$attr=0;if($z->getExternalAttributesName($name,$ops,$attr)&&(($attr>>16)&0170000)===0120000)throw new RuntimeException('Collection symlinks are not accepted.');
            $bytes=$z->getFromName($name,$st['size']+1);if(!is_string($bytes)||strlen($bytes)!==$st['size']||sprintf('%u',crc32($bytes))!==sprintf('%u',$st['crc'])||!hash_equals($entry['sha256'],hash('sha256',$bytes)))throw new RuntimeException('Collection checksum mismatch: '.$name);
            $names[$fold]=true;if(isset($imports[$name]))$files[$name]=$bytes;
        }
        // Duplicate central-directory names are not hidden by getFromName.
        $seen=array();for($i=0;$i<$z->numFiles;$i++){$name=$z->getNameIndex($i);$fold=strtolower($name);if(isset($seen[$fold])||!isset($names[$fold]))throw new RuntimeException('Duplicate or undeclared collection entry.');$seen[$fold]=true;}
        $items=array();$groups=array();$totals=array('subjective'=>0,'mcq'=>0,'question_bodies'=>0,'answer_candidates'=>0,'sources'=>0);$samples=array();$expanded=0;$package_keys=array();
        foreach($m['packages']as $entry){
            if(!str_ends_with($entry['path'],'.zip'))throw new RuntimeException('Collection imports must be existing Academic ZIPs.');
            $child=CAFCC_Package::decode(base64_encode($files[$entry['path']]),false);if(is_wp_error($child))throw new RuntimeException($entry['path'].': '.$child->get_error_message());$cm=$child['manifest'];
            if($cm['scope']['subject_code']!==$m['subject_code']||isset($package_keys[$cm['package_key']]))throw new RuntimeException('Collection subject or child package identity conflicts.');$package_keys[$cm['package_key']]=true;
            $kind='subjective';$count=0;
            foreach($child['items']as $ci){$expanded+=$ci['bytes'];if($expanded>48000000)throw new RuntimeException('Expanded child JSON exceeds 48 MB.');if($ci['kind']==='rights')throw new RuntimeException('Keep owner rights declarations in Settings; this collection imports drafts only.');if(!in_array($ci['kind'],array('questions','mcqs'),true))continue;
                foreach($ci['payload']['records']as $d){$is_mcq=$ci['kind']==='mcqs';$kind=$is_mcq?'mcq':'subjective';$totals[$kind]++;$count++;$totals['question_bodies']+=!empty($is_mcq?$d['question_html']:($d['rich_content']['question']['body_html']??''));$totals['answer_candidates']+=!empty($d['answer']);$totals['sources']+=!empty($d['official_url']);if(count($samples)<3)$samples[]=array('label'=>$d['source_key'].' Q'.$d['reference'],'question'=>CAFCC_Practice::html($is_mcq?$d['question_html']:($d['rich_content']['question']['body_html']??'')),'answer'=>CAFCC_Practice::html($is_mcq?'Answer key retained privately for review':($d['rich_content']['answer']['body_html']??'')));}
            }
            if($count>100)throw new RuntimeException('Use at most 100 records per resumable child package.');
            $groups[]=array('package_key'=>$cm['package_key'],'scope'=>$cm['scope'],'record_kind'=>$kind,'records'=>$count);$items[]=array('path'=>$entry['path'],'kind'=>'collection','bytes'=>$entry['bytes'],'sha256'=>$entry['sha256'],'payload'=>array('archive'=>base64_encode($files[$entry['path']]),'package_key'=>$cm['package_key']));
        }
        if($totals['subjective']+$totals['mcq']>2500)throw new RuntimeException('Use at most 2,500 draft records per subject collection.');
        foreach($m['attachments']as $a)if(str_ends_with($a['path'],'.zip'))throw new RuntimeException('Nested ZIPs must be declared as bounded Academic imports.');
        // Review files are integrity checked but never extracted, executed, put
        // in Media, served as HTML, or imported as academic approval decisions.
        $m['scope']=array('subject_code'=>$m['subject_code'],'exam_attempt'=>'Source-specific attempts; see child manifests','edition_key'=>'');$m['groups']=$groups;$m['items']=array_map(function($i){return array_diff_key($i,array('payload'=>true));},$items);$m['coverage']=array_merge($totals,array('draft_candidates'=>$totals['subjective']+$totals['mcq'],'academic_approvals'=>0,'publications'=>0,'review_attachments'=>count($m['attachments'])));$m['samples']=$samples;
        return array('manifest'=>$m,'items'=>$items,'archive_sha256'=>$hash);
    }
    public static function execute($payload){
        if(!is_array($payload)||array_diff(array_keys($payload),array('archive','package_key')))return CAFCC_Repository::error('Invalid collection checkpoint.');
        $job=CAFCC_Package::upload($payload['archive']);if(is_wp_error($job))return CAFCC_Repository::error($payload['package_key'].': '.$job->get_error_message());if($job['package_key']!==$payload['package_key'])return CAFCC_Repository::error('Child identity changed.');$steps=0;
        while($job['status']!=='completed'){
            if(++$steps>65)return CAFCC_Repository::error('Child checkpoint limit exceeded.');if($job['status']==='blocked')return CAFCC_Repository::error('Child import blocked; retain corrections and inspect '.$job['package_key']);
            $job=CAFCC_Package::step($job['job_key'],array('cursor'=>$job['cursor'],'confirmed'=>true));if(is_wp_error($job))return $job;
        }
        return array('child_package_id'=>$job['id'],'package_key'=>$job['package_key'],'status'=>'completed','publication_actions'=>0);
    }
    public static function preview($id){
        global $wpdb;$row=$wpdb->get_row($wpdb->prepare('SELECT owner_id,manifest FROM '.CAFCC_Package::table().' WHERE id=%d',$id),ARRAY_A);if(!$row||(int)$row['owner_id']!==get_current_user_id())return CAFCC_Repository::error('Private collection not found.',404);$m=json_decode($row['manifest'],true);if(($m['format']??'')!==self::FORMAT)return null;$c=$m['coverage'];return array('record_kind'=>'collection','draft_only'=>true,'count'=>$c['draft_candidates'],'question_bodies'=>$c['question_bodies'],'answer_candidates'=>$c['answer_candidates'],'sources'=>$c['sources'],'samples'=>$m['samples'],'existing_rights_active'=>false,'groups'=>$m['groups'],'validation_scope'=>'structure_and_checksums_verified_records_validated_per_child_before_commit','note'=>'One upload. Structure and checksums verified; each source batch receives full record validation before its draft checkpoint. All new records remain Needs Review. Use Question Library and MCQ Library for later owner publication decisions.');
    }
}
