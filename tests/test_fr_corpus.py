"""Only independently authored test text; no copyrighted source prose."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'research'))
import fr_corpus as f
import fr_taxonomy as taxonomy
from test_layout import line, heading


class FRCorpusTests(unittest.TestCase):
    def identity(self,kind='rtp',role='questions_and_answers'):
        return dict(source_type=kind,role=role)

    def test_brown_heading_introduces_following_question(self):
        rows=[heading('QUESTIONS',150),line('1. TEST calculate an original amount.',180),heading('Ind AS 115',220),line('2. TEST next requirement.',250),heading('ANSWERS',300),line('1. TEST solution',350),line('2. TEST solution',400)]
        qs,_=f.boundaries(rows,self.identity());qs=[q for q in qs if q['side']=='question']
        self.assertEqual(qs[0]['end_exclusive']['bbox'][1],220);self.assertEqual(qs[1]['heading']['text'],'Ind AS 115')

    def test_cross_page_black_standard_heading(self):
        rows=[heading('QUESTIONS',150),line('1. TEST calculate.',180),line('Ind AS 21',680,bold=True),line('2. TEST calculate.',160,page=2)]
        qs,_=f.boundaries(rows,self.identity());self.assertEqual(qs[1]['heading']['spans'][0]['page'],1);self.assertEqual(qs[1]['start']['page'],2)

    def test_old_mtp_does_not_require_part_ii_heading(self):
        qs,_=f.boundaries([line('1. TEST prepare an account.',180,x=72),line('2. TEST compute a value.',250,x=72),line('3. TEST explain.',350,x=72)],self.identity('mtp','questions'))
        self.assertEqual([q['reference'] for q in qs],['1','2','3']);self.assertTrue(all(q['format']=='SUBJECTIVE' for q in qs))

    def test_answer_books_alternate_question_and_answer(self):
        qs,_=f.boundaries([line('Question 1',150),line('TEST scenario',180),line('Answer',220),line('TEST solution',240),line('Question 2',300),line('TEST scenario',330),line('Answer',370),line('TEST solution',390)],self.identity('exam'))
        self.assertEqual([(q['side'],q['reference']) for q in qs],[('question','1'),('answer','1'),('question','2'),('answer','2')])

    def test_lettered_requirements_are_not_automatically_mcqs(self):
        rows=[line('1. TEST common facts',150),line('(a) Prepare an original statement',180),line('(b) Calculate an original amount',220),line('(c) Explain an original treatment',260),line('(d) Discuss the original result',300)]
        q={'format':'SUBJECTIVE','lines':rows,'end_exclusive':{'page':1,'bbox':[108,350,400,365],'column':0},'warnings':[]}
        parts=f.split_parts(q);self.assertEqual([p['subreference'] for p in parts],list('abcd'));self.assertTrue(all(p['lines'][0]['text']=='1. TEST common facts' for p in parts))

    def test_answer_number_restarts_keep_mcq_keys_out_of_descriptive_mapping(self):
        rows=[heading('ANSWERS OF PART I: MCQs',150),line('1. TEST option B',180),heading('ANSWERS OF PART II: DESCRIPTIVE QUESTIONS',240),line('1. TEST worked solution',280)]
        records,_=f.boundaries(rows,self.identity('mtp','answers'))
        self.assertEqual([(r['section'],r['format']) for r in records],[('mcq','MCQ'),('descriptive','SUBJECTIVE')])
        import fr_package
        ident=dict(source_type='mtp',role='answers',subject_confirmed=True,issue_period='July 2025',series='I')
        doc=dict(identity=ident,records=records);paper=dict(identity={**ident,'role':'questions'})
        matches=fr_package.match_answers(paper,dict(reference='1',subreference='',format='SUBJECTIVE'),[doc])
        self.assertEqual(len(matches),1);self.assertEqual(matches[0]['record']['section'],'descriptive')

    def test_number_and_negative_sign_fidelity(self):
        self.assertTrue(f.fidelity('₹120 (40) −8 31/03/2026 5%','₹120 (40) −8 31/03/2026 5%')['passed'])
        self.assertFalse(f.fidelity('₹120 −8 5%','₹120 8 5')['passed'])

    def test_exact_answer_identity_uses_whole_source_context(self):
        import fr_package
        q={'reference':'2','subreference':'a'};ident=dict(source_type='mtp',role='questions',subject_confirmed=True,issue_period='July 2025',series='I')
        paper={'identity':ident};answers=[dict(identity={**ident,'role':'answers','series':'II'},records=[dict(side='answer',reference='2',subreference='a')]),dict(identity={**ident,'role':'answers'},records=[dict(side='answer',reference='2',subreference='b')])]
        self.assertEqual(fr_package.match_answers(paper,q,answers),[])

    def test_toc_ignores_general_outline_and_retains_numeric_hierarchy(self):
        body=''' (https://resource.cdn.icai.org/test-original-contents.pdf)
Total lines: 9
L0@P0: CONTENTS
L1@P0: Chapter 17: TEST overview, not detailed scope
L2@P1: DETAILED CONTENTS: MODULE – 1
L3@P1: CHAPTER-3: TEST ORIGINAL CHAPTER
L4@P1: Unit 1: TEST ORIGINAL UNIT
L5@P1: 1.1 TEST original topic ........................................ 3.10
L6@P1: 1.1.1 TEST original subtopic ................................ 3.11
L7@P1: 1.1.1.1 TEST deeper heading ................................ 3.12
L8@P1: END'''
        result=taxonomy.parse({'initial':[dict(year='2026',module=1,text=body)]});nodes=result['nodes'];self.assertFalse(any('ch17' in n['node_key'] for n in nodes));self.assertEqual([n['node_type'] for n in nodes],['module','chapter','unit','topic','subtopic','subtopic']);self.assertEqual(nodes[-1]['printed_page'],'3.12');self.assertEqual(nodes[-1]['parent_key'],nodes[-2]['node_key'])

    def test_blank_or_wrong_paper_has_no_verified_metadata(self):
        import fitz
        with fitz.open() as doc:
            doc.new_page().insert_text((72,72),'TEST scenario: a transaction in March 2025.');meta=f.identify({'source_kind':'RTP'},doc)
            self.assertFalse(meta['subject_confirmed']);self.assertEqual(meta['attempt'],'')


if __name__=='__main__':unittest.main()
