"""Independently authored source/layout fixtures; no ICAI prose."""
import sys,unittest,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'research'))
import fitz
import archive_catalog as catalog
import archive_profiles as profiles
import gold_layout as gold
from test_gold_layout import q,line
class ArchivePipeline(unittest.TestCase):
 def test_old_audit_title_precedes_incidental_reporting_words(self):
  f={'id':'TEST','title':'misleading-fr.pdf','subject':'AUDIT','folder_path':'AUDIT/RTP'}
  text='PAPER 3: ADVANCED AUDITING AND PROFESSIONAL ETHICS\nMAY 2021 EXAMINATION\nA case mentions financial reporting.'
  d=catalog.identify(f,[dict(text=text,header=text[:100],footer='MAY 2021 EXAMINATION')]);self.assertEqual(d['actual_subject'],'AUDIT');self.assertEqual(d['scheme'],'final_old_eight_paper')
 def test_mtp_issue_date_is_not_promoted_to_exam_target(self):
  f={'id':'TEST','title':'NOV_2026_Questions.pdf','subject':'AFM','folder_path':'AFM/MTP'};t='Mock Test Paper - Series II: September, 2026\nPAPER 2: ADVANCED FINANCIAL MANAGEMENT'
  d=catalog.identify(f,[dict(text=t,header=t,footer='')]);self.assertEqual(d['document_issue_period'],'September 2026');self.assertEqual(d['exam_attempt'],'');self.assertEqual(d['series'],'II')
 def test_cancelled_actual_exam_conflict_is_retained(self):
  f={'id':'TEST','title':'May2020.pdf','subject':'FR','folder_path':'FR/Suggested Answers'};t='FINAL EXAMINATION MAY 2020\nPAPER 1 FINANCIAL REPORTING\nSUGGESTED ANSWERS'
  d=catalog.identify(f,[dict(text=t,header=t,footer='')]);self.assertIn('cancelled_may2020_actual_exam_identity_conflict',d['warnings'])
 def test_lettered_subjective_facts_are_not_mcqs(self):
  lines=[line('1. TEST prepare the statement.',100),line('(a) A recorded asset.',130),line('(b) A recorded obligation.',150)];r=q(lines);r['format']='MCQ';fixed,_=profiles.phases([r],lines,'rtp');self.assertEqual(fixed[0]['format'],'SUBJECTIVE')
 def test_mcq_then_subjective_uses_printed_section_evidence(self):
  lines=[line('PART I: Multiple Choice Questions',70),line('1. TEST which is correct?',100),line('PART II: Descriptive Questions',200),line('1. TEST calculate the result.',230)];a=q([lines[1]]);a['start']={'page':1,'bbox':lines[1]['bbox']};b=q([lines[3]]);b['start']={'page':1,'bbox':lines[3]['bbox']};fixed,_=profiles.phases([a,b],lines,'rtp');self.assertEqual([r['format']for r in fixed],['MCQ','SUBJECTIVE'])
 def test_brown_heading_introduces_following_next_page_question(self):
  a=line('1. TEST original requirement.',100);h={**line('TEST source chapter heading',700),'rgb':[140,65,25],'bold':True,'font':'TEST Bold','column':0};b=line('2. TEST next requirement.',100,page=2);first=q([a,h]);second=q([b]);second.update(reference='2',start={'page':2,'bbox':b['bbox']});fixed,_=profiles.phases([first,second],[a,h,b],'rtp');self.assertNotIn(h,fixed[0]['lines']);self.assertEqual(fixed[1]['heading']['text'],h['text']);self.assertEqual(fixed[0]['end_exclusive']['page'],1)
 def test_mcq_case_heading_does_not_become_a_descriptive_chapter(self):
  intro=line('PART I: Multiple Choice Questions',60);h={**line('CASE SCENARIO I',80),'rgb':[140,65,25],'bold':True,'font':'TEST Bold','column':0};body=line('1. TEST which option is correct?',100);record=q([body]);fixed,_=profiles.phases([record],[intro,h,body],'rtp');self.assertEqual(fixed[0]['format'],'MCQ');self.assertFalse(fixed[0].get('heading'))
 def test_one_heading_cannot_erase_short_following_question(self):
  h={**line('TEST theory group',80),'rgb':[140,65,25],'bold':True,'font':'TEST Bold','column':0};a=line('15. TEST first independent requirement.',100);b=line('16. TEST second independent requirement.',140);first=q([a]);first.update(reference='15',start={'page':1,'bbox':a['bbox']});second=q([b]);second.update(reference='16',start={'page':1,'bbox':b['bbox']});fixed,events=profiles.phases([first,second],[h,a,b],'rtp');self.assertEqual(fixed[0]['lines'],[a]);self.assertEqual(fixed[1]['lines'],[b]);self.assertEqual(fixed[0]['heading']['text'],h['text']);self.assertEqual(len([e for e in events if e['basis']=='forward_brown_heading']),1)
 def test_table_cache_preserves_cell_values_and_html(self):
  with fitz.open()as doc:
   p=doc.new_page();p.insert_text((72,110),'TEST ordinary continuous paragraph, not a table.');p.insert_text((72,135),'TEST same paragraph continues with actual values 120 and (30).')
   import fr_corpus
   lines=fr_corpus.all_lines(doc);region=q(lines);region['start']={'page':1,'bbox':[0,0,595,0]};cache={};a=gold.reconstruct(region,doc);b=gold.reconstruct(region,doc,cache);c=gold.reconstruct(region,doc,cache);self.assertEqual(a,b);self.assertEqual(b,c);self.assertNotIn('<table',a['body_html']);self.assertTrue(a['fidelity']['passed'])

class IBSProfiles(unittest.TestCase):
 def test_integer_restarts_belong_to_distinct_cases(self):
  import ibs_layout
  with fitz.open()as d:
   p=d.new_page()
   for y,t in [(50,'CASE STUDY - 1'),(80,'TEST common case one.'),(110,'Descriptive Questions'),(140,'6. TEST requirement one.'),(190,'CASE STUDY - 2'),(220,'TEST common case two.'),(250,'Descriptive Questions'),(280,'6. TEST requirement two.')]:p.insert_text((72,y),t)
   records,_=ibs_layout.discover(d,{'source_type':'rtp','role':'questions_and_answers'});self.assertEqual([r['reference']for r in records],['6','6']);self.assertEqual([r['identity_reference']for r in records],['1.6','2.6']);self.assertIn('one.',' '.join(l['text']for l in records[0]['shared_lines']));self.assertNotIn('one.',' '.join(l['text']for l in records[1]['shared_lines']))
 def test_decimal_case_references_and_common_facts(self):
  import ibs_layout
  with fitz.open()as d:
   p=d.new_page()
   for y,t in [(80,'CASE STUDY - 1'),(110,'TEST common facts belonging to this independently authored case.'),(160,'Multiple Choice Questions'),(190,'1.1 TEST choose one option.'),(220,'(a) TEST first'),(245,'(b) TEST second'),(270,'(c) TEST third'),(295,'(d) TEST fourth'),(330,'Descriptive Questions'),(360,'1.6 TEST calculate the required amount.'),(410,'ANSWERS'),(440,'1.1 Option (B): TEST key'),(480,'1.6 TEST complete working and explanation.')]:p.insert_text((72,y),t)
   records,profile=ibs_layout.discover(d,{'source_type':'exam','role':'questions_and_answers'});self.assertEqual([(q['side'],q['reference'],q['format'])for q in records],[('question','1.1','MCQ'),('question','1.6','SUBJECTIVE'),('answer','1.1','MCQ'),('answer','1.6','SUBJECTIVE')]);self.assertIn('TEST common facts',' '.join(l['text']for l in records[1]['shared_lines']));self.assertEqual(records[1]['parent_reference'],'1')


class StructuralIntegrity(unittest.TestCase):
 def model(self,cells):return {'blocks':[{'type':'table','page':2,'bbox':[1,2,300,200],'cells':cells}]}
 def test_placeholder_cannot_move_into_label(self):
  import archive_integrity as a
  rich=self.model([dict(row=0,column=0,text='TEST liability -'),dict(row=0,column=1,text='40'),dict(row=0,column=2,text='')]);self.assertEqual(a.inspect(rich)[0]['code'],'amount_placeholder_column_assignment_requires_review')
 def test_formula_font_glyph_requires_correction(self):
  import archive_integrity as a
  self.assertEqual(a.inspect(self.model([dict(row=0,column=0,text='TEST formula \ue010 12')]))[0]['code'],'unsupported_pdf_formula_or_font_glyph')
 def test_tokens_do_not_prove_multiline_row_association(self):
  import archive_integrity as a
  rich=self.model([dict(row=0,column=0,text='TEST labels'),dict(row=0,column=1,text='100\n200\n300')]);self.assertEqual(a.inspect(rich)[0]['code'],'multi_amount_cell_row_associations_require_review');rich['blocks'][0]['row_method']='printed_numeric_baselines';self.assertEqual(a.inspect(rich),[])

if __name__=='__main__':unittest.main()
