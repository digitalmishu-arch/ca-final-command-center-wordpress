<?php
defined('ABSPATH') || exit;

/** Query-backed standard and concept facets, independent of hierarchy dropdown order. */
final class CAFCC_Standards {
    public static function catalog(){return CAFCC_Search_Tags::catalog()['entries'];}
    public static function entry($term){$n=CAFCC_Search_Tags::normalise($term);foreach(self::catalog() as $e)if(CAFCC_Search_Tags::normalise($e['code'])===$n)return $e;return null;}
    public static function filters($request){
        $code=$request->get_param('standard')??'';$concept=$request->get_param('concept')??'';
        if(!is_string($code)||strlen($code)>40||!is_string($concept)||strlen($concept)>220)return CAFCC_Repository::error('Invalid standard/concept filter.');
        $entry=$code?self::entry($code):null;if($code&&!$entry)return CAFCC_Repository::error('Choose a supported Ind AS or SA from the reference catalogue.');
        if($concept&&!preg_match('/^(?:node:[1-9][0-9]{0,17}|tag:[a-z0-9 ][a-z0-9 -]{0,190})$/D',$concept))return CAFCC_Repository::error('Choose an indexed concept.');
        if(str_starts_with($concept,'node:')){$id=(int)substr($concept,5);$n=CAFCC_Academic::get('taxonomy',$id);if(!$n||!in_array($n['node_type'],array('topic','subtopic'),true)||!CAFCC_Academic::path_published($id))return CAFCC_Repository::error('This edition-specific concept is unavailable.');}
        return array('standard'=>$entry?$entry['code']:'','concept'=>$concept);
    }
    public static function condition($question_alias,$f,&$args){
        $sql='';if(!empty($f['standard']))$sql.=' AND '.CAFCC_Search_Tags::search_sql($question_alias.'.id',$f['standard'],$args);
        if(!empty($f['concept'])){
            if(str_starts_with($f['concept'],'tag:')){$sql.=' AND EXISTS(SELECT 1 FROM '.CAFCC_Search_Tags::table()." concept_tag WHERE concept_tag.question_id=$question_alias.id AND concept_tag.normalised=%s)";$args[]=substr($f['concept'],4);}
            else{$qt=CAFCC_DB::table('question_tags');$cl=CAFCC_Bank_DB::table('closure');$sql.=" AND EXISTS(SELECT 1 FROM $qt concept_node JOIN $cl ancestor ON ancestor.descendant_id=concept_node.node_id WHERE concept_node.question_id=$question_alias.id AND ancestor.ancestor_id=%d AND ".CAFCC_Academic::published('concept_node').')';$args[]=(int)substr($f['concept'],5);}
        }return $sql;
    }
    private static function query($request,$clear_standard=false){$r=clone $request;$r->set_param('concept','');if($clear_standard)$r->set_param('standard','');$r->set_param('search','');$f=CAFCC_Facets::filters($r);if(is_wp_error($f))return $f;return CAFCC_Facets::occurrence_parts($f,get_current_user_id());}
    public static function options($request){
        if(is_wp_error($e=CAFCC_Library::allowed()))return $e;$query=self::query($request,true);if(is_wp_error($query))return $query;[$from,$where,$args]=$query;$term=$request->get_param('term')??'';if(!is_string($term)||strlen($term)>120)return CAFCC_Repository::error('Use a shorter standard search.');global $wpdb;$tags=CAFCC_Search_Tags::table();
        $code="CASE WHEN standard_tag.normalised REGEXP '^ind as [0-9]+' THEN SUBSTRING_INDEX(standard_tag.normalised,' ',3) WHEN standard_tag.normalised REGEXP '^sa [0-9]+' THEN SUBSTRING_INDEX(standard_tag.normalised,' ',2) ELSE '' END";
        $rows=$wpdb->get_results($wpdb->prepare("SELECT $code AS standard_code,COUNT(DISTINCT bo.id) AS questions $from JOIN $tags standard_tag ON standard_tag.question_id=q.id AND standard_tag.kind IN ('standard','owner_tag') WHERE $where GROUP BY standard_code",$args),ARRAY_A);$counts=array();foreach($rows as $row)$counts[$row['standard_code']]=(int)$row['questions'];$items=array();$normal=CAFCC_Search_Tags::normalise($term);if($normal==='revenue recognition')$normal='revenue from contracts';$selected=$request->get_param('standard')??'';
        foreach(self::catalog() as $e){$key=CAFCC_Search_Tags::normalise($e['code']);$count=$counts[$key]??0;if(!$count&&self::entry($selected)!==$e)continue;$label=$e['code'].' — '.$e['title'];
            if($normal){if(CAFCC_Search_Tags::standard_query($term)){if(!($key===$normal||(!preg_match('/\d/',$normal)&&str_starts_with($key,$normal.' '))))continue;}elseif(!str_contains(CAFCC_Search_Tags::normalise($label),$normal))continue;}
            $items[]=array('id'=>$e['code'],'code'=>$e['code'],'title'=>$e['title'],'label'=>$label,'subject_code'=>$e['subject'],'questions'=>$count,'origin'=>'ICAI standard naming reference; question association may be provisional');
        }return array('items'=>$items,'count_basis'=>'Eligible published source occurrences with an assigned standard tag.');
    }
    public static function concepts($request){
        if(is_wp_error($e=CAFCC_Library::allowed()))return $e;$query=self::query($request);if(is_wp_error($query))return $query;[$from,$where,$args]=$query;global $wpdb;$tags=CAFCC_Search_Tags::table();$tx=CAFCC_DB::table('taxonomy');$qt=CAFCC_DB::table('question_tags');$cl=CAFCC_Bank_DB::table('closure');$ed=CAFCC_DB::table('editions');
        $rows=$wpdb->get_results($wpdb->prepare("SELECT tag.label,tag.normalised,COUNT(DISTINCT bo.id) AS questions $from JOIN $tags tag ON tag.question_id=q.id AND tag.kind IN ('concept','owner_tag') WHERE $where GROUP BY tag.label,tag.normalised ORDER BY questions DESC,tag.label LIMIT 80",$args),ARRAY_A);$items=array();foreach($rows as $r){if(preg_match('/^(ind as|sa) [0-9]/',$r['normalised']))continue;$items[]=array('id'=>'tag:'.$r['normalised'],'label'=>$r['label'],'questions'=>(int)$r['questions'],'origin'=>'Editorial / provisional search tag');}
        $nodes=$wpdb->get_results($wpdb->prepare("SELECT node.id,node.title,node.heading_origin,edition.title AS edition_title,COUNT(DISTINCT bo.id) AS questions $from JOIN $qt mapping ON mapping.question_id=q.id JOIN $cl path ON path.descendant_id=mapping.node_id JOIN $tx node ON node.id=path.ancestor_id JOIN $ed edition ON edition.id=node.edition_id WHERE $where AND node.node_type IN ('topic','subtopic') AND ".CAFCC_Academic::published('mapping').' AND '.CAFCC_Owner::usable_sql('node')." GROUP BY node.id,node.title,node.heading_origin,edition.title ORDER BY questions DESC,node.title LIMIT 100",$args),ARRAY_A);
        foreach($nodes as $n)if(CAFCC_Academic::path_published($n['id']))$items[]=array('id'=>'node:'.$n['id'],'label'=>$n['title'].' · '.$n['edition_title'],'questions'=>(int)$n['questions'],'origin'=>$n['heading_origin']==='official'?'Source-backed ICAI heading':'Editorial taxonomy heading');
        return array('items'=>$items,'note'=>'Only concepts actually associated with eligible matching questions are offered. Official headings and inferred search tags remain distinct.');
    }
    public static function init(){add_action('rest_api_init',function(){$p=function($r){return CAFCC_REST::permission($r);};foreach(array('standards'=>'options','standard-concepts'=>'concepts') as $route=>$method)register_rest_route('cafcc/v9','/'.$route,array('methods'=>'GET','permission_callback'=>$p,'callback'=>array(__CLASS__,$method)));});}
}
