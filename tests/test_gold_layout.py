"""Original synthetic layout fixtures, never copied ICAI question prose."""
import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'research'))
import fitz
import gold_layout as g


def line(text,y,x=72,page=1):return dict(text=text,bbox=[x,y,x+200,y+12],page=page,size=11,bold=False,spans=[])
def q(lines):return dict(reference='1',subreference='',alternative='',side='question',format='SUBJECTIVE',lines=lines,start=dict(page=1,bbox=[72,100,300,112]),end_exclusive=dict(page=1,bbox=[72,700,300,712]),warnings=[],heading=None)


class GoldLayout(unittest.TestCase):
    def test_printed_financial_rows_inside_one_ruled_body_cell(self):
        with fitz.open() as d:
            p=d.new_page()
            for x in (72,230,350,470):p.draw_line((x,90),(x,210))
            for y in (90,120,210):p.draw_line((72,y),(470,y))
            for x,t in [(80,'TEST asset'),(240,'TEST A'),(360,'TEST B')]:p.insert_text((x,110),t)
            for y,label,a,b in [(145,'TEST first','120','240'),(170,'TEST second','(30)','(60)'),(195,'TEST total','90','180')]:
                p.insert_text((80,y),label);p.insert_text((240,y),a);p.insert_text((360,y),b)
            table=p.find_tables(strategy='lines_strict').tables[0];m,error=g.table_model(p,table,[0,0,595,842]);self.assertEqual(error,'');self.assertIsNotNone(m)
            rows=g.expand_financial_rows(p,m);self.assertEqual(rows['rows'],4)
            grid={(c['row'],c['column']):c['text'] for c in rows['cells']}
            self.assertEqual(grid[(1,0)],'TEST first');self.assertEqual(grid[(1,1)],'120');self.assertEqual(grid[(2,1)],'(30)');self.assertEqual(grid[(3,2)],'180')

    def test_alternating_answer_book_ignores_same_margin_working_numbers(self):
        with fitz.open() as d:
            p=d.new_page()
            for y,t in [(100,'Question 1'),(130,'(a) Prepare TEST one.'),(160,'(b) Calculate TEST two.'),(230,'Answer'),(270,'1. TEST working note.'),(330,'2. TEST working note.'),(400,'Question 2'),(430,'Explain TEST three.'),(500,'Answer'),(530,'TEST complete solution.')]:p.insert_text((72,y),t)
            rows,_=g.discover(d,dict(source_type='exam',role='questions_and_answers'))
            self.assertEqual([(r['side'],r['reference']) for r in rows],[('question','1'),('answer','1'),('question','2'),('answer','2')])

    def test_indentation_does_not_turn_prose_into_table(self):
        rows=[['TEST original paragraph continues into the next part of the sentence.','TEST further ordinary prose with many words and no accounting values.'],['TEST another paragraph about the requirement.','TEST ordinary continuation of the same paragraph.']]
        self.assertFalse(g.qualify_table(rows,[72,100,520,300])[0])

    def test_true_financial_grid_has_values_and_labels(self):
        self.assertTrue(g.qualify_table([['TEST asset','TEST A','TEST B'],['Land','120','240'],['Plant','30','60']],[72,100,520,300])[0])

    def test_decorative_two_column_prose_is_rejected_even_with_year(self):
        rows=[['TEST instructions','TEST notes'],['TEST paragraph','During 2026 this original paragraph continues with many words about an accounting scenario and its background facts.'],['TEST second paragraph','During 2025 this original paragraph continues with many words about a scenario and its background facts.']]
        self.assertFalse(g.qualify_table(rows,[72,100,520,300])[0])

    def test_independent_lettered_parts_keep_shared_context(self):
        children,error=g.split_independent(q([line('TEST common facts.',100),line('(a) Prepare an original account.',130),line('(b) Calculate an original value.',170)]))
        self.assertIsNone(error);self.assertEqual([x['subreference'] for x in children],['a','b']);self.assertEqual(children[0]['shared_lines'][0]['text'],'TEST common facts.')

    def test_lettered_assets_are_not_independent_requirements(self):
        children,error=g.split_independent(q([line('TEST original asset facts',100),line('(a) Land is held.',130),line('(b) Plant is held.',170)]))
        self.assertEqual(len(children),1);self.assertIsNotNone(error)

    def test_either_or_keeps_distinct_identity(self):
        children,_=g.split_independent(q([line('Prepare TEST original statement.',100),line('OR',140),line('Explain TEST original alternative.',170)]))
        self.assertEqual([c['alternative'] for c in children],['either','or'])

    def test_roman_requirements_beneath_letter_parent(self):
        children,_=g.split_independent(q([line('(a) TEST scenario',100),line('(i) Calculate TEST one.',130,x=90),line('(ii) Prepare TEST two.',160,x=90),line('(b) Explain TEST three.',200)]))
        self.assertEqual([c['subreference'] for c in children],['a.i','a.ii','b'])

    def test_reference_formats(self):
        for text,expected in [('Q1(a)(i)',('1','a.i')),('Question 1 A',('1','a')),('Question 2 — Part B',('2','b')),('Q1(b)',('1','b'))]:self.assertEqual(g.reference(text),expected)

    def test_exact_answer_requires_series_hash_and_alternative(self):
        paper=dict(subject_code='FR',exam_attempt='January 2026',source_type='mtp',mtp_series='I',answer_document_hash='answer-I');question=dict(reference='2',subreference='b',alternative='or')
        other={**paper,'mtp_series':'II','source_hash':'answer-II','records':[dict(side='answer',format='SUBJECTIVE',**question)]}
        self.assertEqual(g.exact_answer(question,paper,[other]),[])
        own={**paper,'source_hash':'answer-I','records':[dict(side='answer',format='SUBJECTIVE',reference='2',subreference='b',alternative='either')]}
        self.assertEqual(g.exact_answer(question,paper,[own]),[])

    def test_span_grid_retains_semantic_headers(self):
        model=dict(rows=2,cells=[dict(row=0,column=0,rowspan=1,colspan=2,text='TEST header'),dict(row=1,column=0,rowspan=1,colspan=1,text='TEST label'),dict(row=1,column=1,rowspan=1,colspan=1,text='(120)')])
        body=g.table_html(model);self.assertIn('colspan="2"',body);self.assertIn('scope="col"',body);self.assertIn('scope="row"',body);self.assertIn('(120)',body)

    def test_prose_continuity_despite_small_x_change(self):
        with fitz.open() as d:
            d.new_page();record=q([line('TEST continuous paragraph begins',100),line('and continues without an invented column.',116,x=75)])
            body=g.reconstruct(record,d);self.assertEqual(body['body_html'].count('<p>'),1);self.assertNotIn('<table>',body['body_html'])

    def test_questions_first_answers_later_and_notes_not_questions(self):
        with fitz.open() as d:
            p=d.new_page();p.insert_text((72,100),'1. TEST calculate first.');p.insert_text((72,170),'Ind AS 115',fontname='hebo');p.insert_text((72,200),'2. TEST calculate second.');p.insert_text((72,300),'SUGGESTED ANSWERS',fontname='hebo');p.insert_text((72,330),'1. TEST solution first.');p.insert_text((95,360),'1. TEST working note.');p.insert_text((72,430),'2. TEST solution second.')
            records,profile=g.discover(d,dict(source_type='rtp',role='questions_and_answers'))
            self.assertIsNotNone(profile['answer_start']);self.assertEqual([(x['side'],x['reference']) for x in records],[('question','1'),('question','2'),('answer','1'),('answer','2')]);self.assertLess(records[0]['end_exclusive']['bbox'][1],records[1]['start']['bbox'][1])

    def test_long_numeric_body_is_financial_not_prose(self):
        amounts='\n'.join(str(1000+n) for n in range(20))
        self.assertEqual(g.qualify_table([['Description','Year A','Year B'],['','`','`'],['TEST financial rows',amounts,amounts]],[0,0,400,600]),(True,''))
        self.assertFalse(g.qualify_table([['Description','Note'],['TEST','This is a long ordinary paragraph with background facts and explanatory prose rather than financial amounts.']],[0,0,400,600])[0])

    def test_currency_font_height_does_not_move_symbol_to_another_line(self):
        class Page:
            def get_text(self,mode):return [(10,100,40,114,'TEST',0,0,0),(45,104,50,112,'CURRENCY',0,0,1),(55,100,75,114,'120',0,0,2),(10,120,50,134,'NEXT',0,1,0)]
        self.assertEqual([text for _,text in g.word_groups(Page(),[0,90,100,140])],['TEST CURRENCY 120','NEXT'])

    def test_proposed_paths_retain_historical_parent_context(self):
        from january_pilot import proposed_paths
        nodes=[dict(node_key='old-chapter',parent_key=None,node_type='chapter',title='TEST historic chapter'),dict(node_key='old-topic',parent_key='old-chapter',node_type='topic',title='TEST historic topic')]
        selected,primary,missing=proposed_paths(['old-topic'],nodes)
        self.assertEqual([n['key'] for n in primary],['old-chapter','old-topic']);self.assertFalse(missing)
        self.assertEqual(proposed_paths(['new-topic'],nodes)[2],['new-topic'])

if __name__=='__main__':unittest.main()
