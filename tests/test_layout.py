"""Authored layout fixtures. No private question/answer prose in this repository."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'research'))
import layout_engine as e
import corrections as c
import layout_pipeline as pipeline


def line(text,y,page=1,bold=False,brown=False,x=108):
    return dict(text=text,page=page,bbox=[x,y,x+300,y+14],font='Helvetica-Bold' if bold else 'Helvetica',
                size=11,bold=bold,rgb=[144,87,30] if brown else [0,0,0],column=0)


def heading(text,y,page=1):return line(text,y,page,True,True)


class LayoutTests(unittest.TestCase):
    def test_heading_introduces_next_question(self):
        ls=[heading('QUESTIONS',150),line('1. TEST original requirement',180),heading('Ind AS 21: Foreign exchange',220),line('2. TEST next requirement',250),heading('SUGGESTED ANSWERS',300)]
        qs,*_=e.segment(ls);self.assertEqual(qs[0]['end_exclusive']['bbox'][1],220)
        self.assertIsNone(qs[0]['heading']);self.assertIn('Ind AS 21',qs[1]['heading']['text'])
        self.assertNotIn('Ind AS 21',qs[0]['private_text'])

    def test_heading_at_bottom_of_previous_page(self):
        qs,*_=e.segment([heading('QUESTIONS',150),line('1. TEST',180),heading('Ind AS 102: Share-based Payment',680),line('2. TEST',160,2),heading('SUGGESTED ANSWERS',400,2)])
        self.assertEqual(qs[1]['heading']['spans'][0]['page'],1);self.assertEqual(qs[1]['start']['page'],2)

    def test_mcq_no_heading_and_no_future_heading_leak(self):
        ls=[heading('QUESTIONS',150),line('1. What revenue is recognised for Year 1?',180)]+[line('('+s+') TEST',200+i*20) for i,s in enumerate('abcd')]+[heading('Ind AS 102: Share-based Payment',300),line('2. TEST',330),heading('SUGGESTED ANSWERS',400)]
        qs,*_=e.segment(ls);r=e.classify(qs[0],[],'FR','historical');self.assertEqual(r['concept'],'Ind AS 115');self.assertIsNone(qs[0]['heading'])

    def test_independent_subquestions_exclude_options(self):
        ls=[heading('QUESTIONS',150),line('1. TEST integrated case',180),line('I. What instrument is tested?',200,x=136)]+[line('('+s+') TEST',220+i*20,x=165) for i,s in enumerate('abcd')]+[line('II. Which agent is responsible?',330,x=136),heading('SUGGESTED ANSWERS',400)]
        qs,*_=e.segment(ls);self.assertEqual([p['reference'] for p in qs[0]['subparts']],['I','II'])

    def test_numbering_restarts_separate_sections(self):
        ls=[heading('QUESTIONS',150),line('1. TEST A',180),line('2. TEST A',200),line('PART B: DESCRIPTIVE QUESTIONS',250),line('1. TEST B',280),line('2. TEST B',300),heading('SUGGESTED ANSWERS',400)]
        qs,*_=e.segment(ls);self.assertEqual(len(qs),4);self.assertNotEqual(qs[1]['section'],qs[3]['section'])

    def test_two_q2_corrections_cannot_cross_documents_or_sections(self):
        ledger=c.append({'events':[]},dict(source_sha256='a'*64,section='mcq',reference='2',actor='owner',decision='concept_approved',classification={'concept':'Securitization'}))
        self.assertIsNone(c.applicable(ledger,'b'*64,'mcq','2'));self.assertIsNone(c.applicable(ledger,'a'*64,'descriptive','2'))

    def test_working_notes_not_new_answer(self):
        question={'reference':'3'}
        found=e.answer_candidates(question,[line('3. TEST true answer',160,bold=True),line('3. TEST working note',300,bold=True,x=136),line('3. TEST paragraph',400)])
        self.assertEqual(len(found),1)

    def test_multiple_answers_stay_ambiguous(self):
        found=e.answer_candidates({'reference':'2'},[line('2. TEST',160,bold=True),line('2. TEST',300,2,True)])
        self.assertEqual(len(found),2)

    def test_historical_mismatch_does_not_borrow_latest_edition(self):
        q=dict(heading={'text':'Ind AS 21'},private_text='Determine exchange differences.',kind='unknown')
        t=[dict(title='Unit 2: Ind AS 21',edition_key='may2026',subject_code='FR',node_type='unit',node_key='latest')]
        self.assertEqual(e.classify(q,t,'FR','jan2026')['official_nodes'],[])

    def test_multiple_supported_concepts_remain_separate(self):
        q=dict(heading=None,private_text='Calculate lease liability and deferred tax.',kind='mcq')
        r=e.classify(q,[],'FR','historical');self.assertEqual(len(r['additional_supported_concepts']),2)

    def test_fr_owner_examples_are_context_regressions_not_number_rules(self):
        for ref,std,text in [('6','Ind AS 115','What revenue is recognised for Year 1?'),('7','Ind AS 115','What is the modification in the contract?'),('8','Ind AS 115','What is remaining total revenue?'),('9','Ind AS 115','What revenue is recognised for Year 2?')]:
            q=dict(reference=ref,heading=None,private_text=text,kind='mcq');self.assertEqual(e.classify(q,[],'FR','historical')['concept'],std)
        for std in ['102','21','8','115']:
            q=dict(reference='99',heading={'text':'Ind AS '+std},private_text='TEST independently authored requirement',kind='unknown');self.assertEqual(e.classify(q,[],'FR','historical')['concept'],'Ind AS '+std)
        q=dict(reference='6',heading={'text':'Ind AS 21'},private_text='Determine foreign exchange differences.',kind='unknown');self.assertEqual(e.classify(q,[],'FR','historical')['concept'],'Ind AS 21')

    def test_background_keyword_is_not_operative_requirement(self):
        q=dict(heading=None,private_text='Background: revenue and leases exist.\nCalculate tax liability.',kind='unknown')
        self.assertIsNone(e.classify(q,[],'FR','historical')['concept'])

    def test_wrapped_mcq_requirement_preserves_rou_and_related_party(self):
        for body,expected in [('What depreciation is charged on\nROU asset?\n(a) TEST','Ind AS 116'),('State which statement is correct\nunder Ind AS 24?\n(a) TEST','Ind AS 24')]:
            self.assertEqual(e.classify(dict(heading=None,private_text=body,kind='mcq'),[],'FR','historical')['concept'],expected)

    def test_ledger_append_and_explicit_supersession(self):
        ev=dict(source_sha256='a'*64,section='mcq',reference='1',actor='owner',decision='approved',labels={})
        ledger=c.append({'events':[]},ev)
        with self.assertRaises(ValueError):c.append(ledger,ev)
        newer=c.append(ledger,{**ev,'supersedes':ledger['events'][0]['event_hash']});self.assertEqual(len(newer['events']),2)
        newer['events'][0]['reference']='2'
        with self.assertRaises(ValueError):c.validate(newer)

    def test_separate_metrics_need_owner_labelled_fields(self):
        rows=[dict(source_sha256='a'*64,section='mcq',reference='1',owner_state='needs_review',metric_values={'chapter_key':'A'})]
        m=c.metrics(rows,{'events':[]});self.assertIsNone(m['chapter_agreement']['percentage']);self.assertEqual(m['manual_review']['count'],1)
        ledger=c.append({'events':[]},dict(source_sha256='a'*64,section='mcq',reference='1',actor='owner',decision='approved',labels={'chapter_key':'A'}))
        self.assertEqual(c.metrics(rows,ledger)['chapter_agreement']['agreement'],1)

    def test_pdf_styles_and_scan_gate(self):
        import fitz
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'test.pdf';doc=fitz.open();page=doc.new_page()
            page.insert_text((108,180),'Ind AS 21: TEST heading',fontname='hebo',fontsize=11,color=(144/255,87/255,30/255))
            doc.new_page();doc.save(path);doc.close();lines,pages,issues,profile=e.read_pdf(path)
            self.assertTrue(lines[0]['bold']);self.assertEqual(lines[0]['rgb'],[144,87,30]);self.assertTrue(any(i['page']==2 for i in issues))

    def test_decimal_table_value_is_not_question(self):
        self.assertIsNone(e.question_marker(line('3.103',180),e.PROFILE))

    def test_source_identification_rtp_mtp_exam_and_answer_role(self):
        self.assertEqual(e.document_evidence('REVISION TEST PAPERS JANUARY 2026 EXAMINATION')['observed_type'],'rtp')
        mtp=e.document_evidence('MOCK TEST PAPER Series II MAY 2026 EXAMINATION PAPER - 2 QUESTIONS')
        self.assertEqual((mtp['observed_type'],mtp['series'],mtp['paper']),('mtp',['II'],'2'))
        self.assertEqual(e.document_evidence('FINAL EXAMINATION MAY 2026 EXAMINATION QUESTIONS')['observed_type'],'exam')
        self.assertEqual(e.document_evidence('SUGGESTED ANSWERS JANUARY 2026 EXAMINATION')['role'],'answer_reference')

    def test_owner_reviewed_synthetic_pilot_exports_drafts_only(self):
        import fitz
        (ROOT/'work').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT/'work') as d:
            base=Path(d);doc=fitz.open();page=doc.new_page()
            for text,y,bold in [('PAPER - 1 REVISION TEST PAPERS',60,False),('JANUARY 2026 EXAMINATION',90,False),('QUESTIONS',170,True),('Ind AS 21: TEST heading',200,True),('1. Determine TEST exchange differences.',240,False),('SUGGESTED ANSWERS',400,True),('1. TEST original answer only.',440,True)]:
                page.insert_text((108,y),text,fontname='hebo' if bold else 'helv',fontsize=11,color=(144/255,87/255,30/255) if text in ['QUESTIONS','Ind AS 21: TEST heading','SUGGESTED ANSWERS'] else (0,0,0))
            doc.save(base/'test.pdf');doc.close()
            edition={'edition_key':'TEST-historical','subject_code':'FR'}
            nodes=[dict(node_key='TEST-chapter',edition_key='TEST-historical',subject_code='FR',parent_key='',node_type='chapter',title='TEST chapter',position=0,heading_origin='editorial',source_url='https://www.icai.org/test-only',source_location='TEST ONLY'),dict(node_key='TEST-unit',edition_key='TEST-historical',subject_code='FR',parent_key='TEST-chapter',node_type='unit',title='Unit 2: Ind AS 21',position=0,heading_origin='official',source_url='https://www.icai.org/test-only',source_location='TEST ONLY')]
            (base/'taxonomy.json').write_text(json.dumps({'editions':[edition],'nodes':nodes}))
            source=dict(subject='FR',source_type='rtp',attempt='January 2026',path='test.pdf',document_key='TEST-layout-document',official_url='https://www.icai.org/test-only.pdf',title='TEST ONLY source',historical_edition_key='TEST-historical',access_authorised=True,access_evidence='TEST ONLY synthetic fixture',expected_questions=1)
            (base/'manifest.json').write_text(json.dumps({'historical_taxonomy':'taxonomy.json','sources':[source]}))
            first=pipeline.run(base/'manifest.json',base/'first');self.assertEqual(first['records'],1)
            record=json.loads((base/'first/review.json').read_text())[0]
            ledger=c.append({'events':[]},dict(source_sha256=record['source_sha256'],section=record['section'],reference='1',actor='owner',decision='approved',labels=record['metric_values'],classification=record['classification'],note='TEST ONLY automated fixture; not an actual owner approval'))
            (base/'ledger.json').write_text(json.dumps(ledger))
            pipeline.run(base/'manifest.json',base/'second',base/'ledger.json',export_reviewed=True)
            gate=json.loads((base/'second/pilot-gate.json').read_text());self.assertEqual(gate['exported'],1)
            self.assertIn('TEST-layout-document',(base/'second/pilot-documents.csv').read_text())
            self.assertNotIn('TEST original answer',(base/'second/pilot-answers.csv').read_text())
            review=json.loads((base/'second/review.json').read_text())[0];self.assertEqual(review['publication_status'],'draft')


if __name__=='__main__':unittest.main()
