"""Original layout fixtures for the seven-document private collection worker."""
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'research'))
import fitz
import gold_layout as g


def line(t,y,x=72):return dict(text=t,page=1,bbox=[x,y,x+180,y+12],size=11,bold=False,spans=[])
def region(rows,side='question'):return dict(lines=rows,reference='2',subreference='',alternative='',side=side,format='SUBJECTIVE',start=dict(page=1,bbox=[72,80,250,92],column=0),end_exclusive=dict(page=1,bbox=[72,700,250,712],column=0),heading=None,warnings=[])


class JanuaryCollection(unittest.TestCase):
    def test_wrapped_stub_and_working_note_stay_with_their_amount(self):
        with fitz.open() as d:
            p=d.new_page()
            for x in [72,280,400]:p.draw_line((x,80),(x,215))
            for y in [80,110,215]:p.draw_line((72,y),(400,y))
            p.insert_text((80,100),'Description');p.insert_text((290,100),'TEST value')
            for y,text in [(130,'TEST long liability'),(150,'(deferred consideration)'),(170,'(TEST working note)'),(195,'TEST trade payables')]:p.insert_text((80,y),text)
            p.insert_text((290,130),'4.95');p.insert_text((290,195),'13.50')
            m,error=g.table_model(p,p.find_tables(strategy='lines_strict').tables[0],[0,0,595,842]);self.assertFalse(error);m=g.expand_financial_rows(p,m);grid={(c['row'],c['column']):c['text'] for c in m['cells']}
            self.assertIn('(TEST working note)',grid[(1,0)]);self.assertEqual(grid[(1,1)],'4.95');self.assertEqual(grid[(2,0)],'TEST trade payables');self.assertEqual(grid[(2,1)],'13.50')

    def test_unit_amount_and_financial_section_rows_keep_their_own_values(self):
        with fitz.open() as d:
            p=d.new_page()
            for x in [72,250,360]:p.draw_line((x,80),(x,240))
            for y in [80,110,240]:p.draw_line((72,y),(360,y))
            for x,t in [(80,'Description'),(260,'TEST value')]:p.insert_text((x,100),t)
            for y,label,value in [(130,'TEST land','60 Lakhs'),(150,'TEST calves','2,000'),(170,'- Financial assets',''),(190,'TEST receivables','4.50'),(210,'Other equity',''),(230,'TEST earnings','15.00')]:
                p.insert_text((80,y),label)
                if value:p.insert_text((260,y),value)
            m,error=g.table_model(p,p.find_tables(strategy='lines_strict').tables[0],[0,0,595,842]);self.assertFalse(error);m=g.expand_financial_rows(p,m);grid={(c['row'],c['column']):c['text'] for c in m['cells']}
            self.assertEqual(m['rows'],7);self.assertEqual(grid[(1,0)],'TEST land');self.assertEqual(grid[(1,1)],'60 Lakhs');self.assertEqual(grid[(3,0)],'- Financial assets');self.assertEqual(grid[(3,1)],'');self.assertEqual(grid[(4,1)],'4.50');self.assertEqual(grid[(5,1)],'');self.assertEqual(grid[(6,1)],'15.00')

    def test_instructions_cannot_open_subjective_section(self):
        with fitz.open() as d:
            p=d.new_page()
            for y,t in [(80,'Part I comprises Case Scenario based MCQs'),(100,'Part II comprises descriptive questions'),(130,'PART I - Case Scenario based MCQs'),(160,'1. TEST original choice.'),(230,'Part II - Descriptive Questions'),(260,'1. TEST original requirement.')]:p.insert_text((72,y),t)
            rows,_=g.discover(d,dict(source_type='mtp',role='questions'))
            self.assertEqual([(r['reference'],r['format']) for r in rows],[('1','MCQ'),('1','SUBJECTIVE')]);self.assertLess(rows[0]['end_exclusive']['bbox'][1],rows[1]['start']['bbox'][1])

    def test_plural_question_labels_and_answer_working_notes(self):
        with fitz.open() as d:
            p=d.new_page()
            for y,t in [(80,'Question 1'),(110,'TEST original requirement.'),(150,'Answer'),(180,'1. TEST working note.'),(240,'Questions 2'),(270,'TEST second requirement.'),(310,'Answer'),(340,'2. TEST working note.')]:p.insert_text((72,y),t)
            rows,_=g.discover(d,dict(source_type='exam',role='questions_and_answers'))
            self.assertEqual([(r['reference'],r['side']) for r in rows],[('1','question'),('1','answer'),('2','question'),('2','answer')])

    def test_lettered_answers_need_not_contain_imperative_verbs(self):
        q=region([line('2.',80),line('(a) TEST first independent scenario.',100),line('Calculate TEST value.',120),line('(b) TEST second independent scenario.',180),line('Explain TEST treatment.',200)])
        a=region([line('2.',80),line('(a) TEST value equals 120.',100),line('(b) TEST treatment is recognised.',180)],'answer')
        qs,ans,w=g.paired_parts(q,a);self.assertFalse(w);self.assertEqual([r['subreference'] for r in qs],['a','b']);self.assertEqual([r['subreference'] for r in ans],['a','b']);self.assertEqual(qs[0]['end_exclusive']['bbox'][1],180)

    def test_or_branches_with_repeated_answer_subpart(self):
        q=region([line('2.',80),line('(a) TEST first.',100),line('OR',140),line('TEST alternate.',160)])
        a=region([line('2.',80),line('(a) TEST solution first.',100),line('(a)',160),line('Or',160,160),line('TEST alternate solution.',190)],'answer')
        qs,ans,w=g.paired_parts(q,a);self.assertFalse(w);self.assertEqual([(r['subreference'],r['alternative']) for r in qs],[('a','either'),('a','or')]);self.assertEqual([r['alternative'] for r in ans],['either','or'])

    def test_lettered_financial_rows_do_not_split_unlettered_parent(self):
        rows=[line('2.',80)]+[line('TEST original shared facts.',100+i*15) for i in range(5)]+[line('(a) TEST equipment',200),line('(b) TEST inventory',220)]
        qs,ans,w=g.paired_parts(region(rows),region(rows,'answer'));self.assertEqual(len(qs),1);self.assertFalse(w)

    def test_answer_sequence_conflict_remains_private(self):
        q=region([line('2.',80),line('(a) TEST one',100),line('(b) TEST two',180)])
        a=region([line('2.',80),line('(a) TEST answer',100),line('(c) TEST conflict',180)],'answer')
        qs,ans,w=g.paired_parts(q,a);self.assertTrue(w);self.assertEqual(len(qs),1)


if __name__=='__main__':unittest.main()
