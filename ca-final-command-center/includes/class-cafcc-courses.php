<?php
defined('ABSPATH') || exit;

/** Paper-name reference metadata; no question bank or chapter tree is invented. */
final class CAFCC_Courses {
    public static function all(){
        $make=function($code,$title,$source,$papers,$from){$subjects=array();foreach($papers as $i=>$p)$subjects[]=array('key'=>$p[0],'title'=>$p[1],'short'=>$p[2],'group'=>$code==='foundation'?0:($i<3?1:2));return array('code'=>$code,'title'=>$title,'scheme'=>'new_scheme_2024','from'=>$from,'source_url'=>$source,'subjects'=>$subjects,'chapter_note'=>'Paper-name reference only. Chapter templates require an indexed source-backed edition; otherwise add your own clearly labelled plan entries.');};
        return array(
            'final'=>$make('final','CA Final','https://www.icai.org/post/bos-knowledge-portal',array(array('FR','Financial Reporting','FR'),array('AFM','Advanced Financial Management','AFM'),array('AUDIT','Advanced Auditing, Assurance and Professional Ethics','Audit'),array('DT','Direct Tax Laws and International Taxation','DT'),array('IDT','Indirect Tax Laws','IDT'),array('IBS','Integrated Business Solutions','IBS')),'2024-05'),
            'intermediate'=>$make('intermediate','CA Intermediate','https://www.icai.org/post/suggested-answer-intermediate',array(array('INT-AA','Advanced Accounting','Adv. Accounting'),array('INT-LAW','Corporate and Other Laws','Law'),array('INT-TAX','Taxation','Taxation'),array('INT-COST','Cost and Management Accounting','Costing'),array('INT-AUDIT','Auditing and Ethics','Audit'),array('INT-FMSM','Financial Management and Strategic Management','FM / SM')),'2024-05'),
            'foundation'=>$make('foundation','CA Foundation','https://www.icai.org/post/suggested-answer-foundation-course',array(array('FND-ACC','Accounting','Accounting'),array('FND-LAW','Business Laws','Business Laws'),array('FND-QA','Quantitative Aptitude','Quantitative Aptitude'),array('FND-ECO','Business Economics','Economics')),'2024-06')
        );
    }
    public static function subjects($course,$group='both'){$c=self::all()[$course]??null;if(!$c)return array();return array_values(array_filter($c['subjects'],function($s)use($course,$group){return $course==='foundation'||$group==='both'||(string)$s['group']===$group;}));}
    public static function month($month,$year){return is_int($month)&&is_int($year)&&$month>=1&&$month<=12&&$year>=2000&&$year<=2100;}
    public static function period($month,$year){return gmdate('F',gmmktime(0,0,0,$month,1,2000)).' '.$year;}
}
