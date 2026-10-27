"""Original synthetic geometry fixtures; no real ICAI prose or answer keys."""
from pathlib import Path
import sys,tempfile,unittest,json
import fitz
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'research'))
from mcq_pipeline import key_regions,running_footer,extract_group,digest

class MCQPipeline(unittest.TestCase):
    def pdf(self,path,lines):
        doc=fitz.open();page=doc.new_page(width=612,height=792)
        for x,y,text in lines:page.insert_text((x,y),text,fontsize=11)
        doc.save(path);doc.close()
    def test_separate_key_columns_and_descriptive_stop(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'key.pdf';self.pdf(p,[(108,100,'Answer to Multiple Choice Questions'),(108,130,'1.'),(140,130,'Option (B)'),(108,160,'2.'),(140,160,'Option (D)'),(108,190,'3.'),(140,190,'TEST descriptive working, not an MCQ key'),(108,220,'4.'),(140,220,'Option (A)')]);keys,errors=key_regions(p,'rtp');self.assertEqual(keys['1']['correct_options'],['B']);self.assertEqual(keys['2']['correct_options'],['D']);self.assertNotIn('4',keys);self.assertFalse(errors)
    def test_series_keys_are_read_from_the_supplied_answer_document(self):
        with tempfile.TemporaryDirectory() as d:
            for series,letter in [('I','A'),('II','C')]:
                p=Path(d)/(series+'.pdf');self.pdf(p,[(108,100,'ANSWER TO PART - I CASE SCENARIO BASED MCQS'),(108,130,'1.'),(140,130,'Option ('+letter+')'),(108,180,'Answers to Part - II'),(108,210,'1.'),(140,210,'Option (D)')]);keys,_=key_regions(p,'mtp');self.assertEqual(keys['1']['correct_options'],[letter])
    def test_multiple_printed_exam_keys_remain_multiple(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'exam.pdf';self.pdf(p,[(108,100,'Answer Key'),(108,140,'7.'),(220,140,'(A) and (C)'),(108,200,'Part - II: Descriptive')]);keys,_=key_regions(p,'exam');self.assertEqual(keys['7']['correct_options'],['A','C'])
    def test_running_footer_is_not_a_numeric_option(self):
        d=fitz.open();d.new_page(width=612,height=792)
        self.assertTrue(running_footer({'page':1,'text':'4','bbox':[477,703,487,720]},d));self.assertFalse(running_footer({'page':1,'text':'4','bbox':[165,403,187,420]},d));self.assertFalse(running_footer({'page':1,'text':'400','bbox':[110,703,140,720]},d));d.close()
    def test_case_range_with_and_and_independent_options(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);q=root/'q.pdf';a=root/'a.pdf';self.pdf(q,[(108,80,'Part - I: Case Scenario Based MCQs'),(108,110,'Case Scenario 1'),(108,135,'TEST ORIGINAL common facts for below questions 1 and 2.'),(108,170,'1.'),(136,170,'TEST ORIGINAL choose first labelled item.'),(136,195,'(a) TEST alpha'),(136,215,'(b) TEST beta'),(136,235,'(c) TEST gamma'),(136,255,'(d) TEST delta'),(108,290,'2.'),(136,290,'TEST ORIGINAL choose second labelled item.'),(136,315,'(a) TEST alpha'),(136,335,'(b) TEST beta'),(136,355,'(c) TEST gamma'),(136,375,'(d) TEST delta'),(108,430,'Part - II: Descriptive'),(108,460,'1.'),(136,460,'TEST ORIGINAL subjective (a), not an MCQ.')]);self.pdf(a,[(108,100,'ANSWER TO PART - I CASE SCENARIO BASED MCQS'),(108,130,'1.'),(140,130,'Option (A)'),(108,160,'2.'),(140,160,'Option (B)'),(108,210,'Answers to Part - II')]);g=dict(question_path=str(q),answer_path=str(a),source_type='mtp',subject_code='FR',exam_attempt='January 2026',mtp_series='I',issue_period='TEST issue',edition_key='TEST',question_source_key='TEST-Q',answer_source_key='TEST-A',question_url='https://example.com/TEST-q.pdf',answer_url='https://example.com/TEST-a.pdf',expected_count=2);records,report,cases=extract_group(g);self.assertEqual(len(records),2);self.assertEqual([r['reference']for r in records],['1','2']);self.assertTrue(all(len(r['options'])==4 for r in records));self.assertEqual(records[0]['scenario']['key'],records[1]['scenario']['key']);self.assertEqual(records[0]['scenario']['question_range'],[1,2]);self.assertEqual(records[1]['correct_options'],['B']);again,_,_=extract_group(g);self.assertEqual(records[0]['stable_id'],again[0]['stable_id']);self.assertEqual(records[0]['answer']['question_source_hash'],digest(q.read_bytes()));self.assertNotIn('subjective',records[-1]['options'][-1]['html'])
    def test_unknown_layout_never_invents_keys(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'unknown.pdf';self.pdf(p,[(100,100,'TEST ORIGINAL unrecognised layout')]);keys,errors=key_regions(p,'mtp');self.assertFalse(keys);self.assertEqual(errors[0]['code'],'answer_key_section_missing')
if __name__=='__main__':unittest.main()
