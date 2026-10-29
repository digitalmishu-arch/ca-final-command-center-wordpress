"""Independently authored AFM parser regressions; no ICAI question prose."""
import sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'research'))
import afm_reconcile as afm
import afm_mcq
import afm_bank
import afm_delivery
import afm_tables

def line(text,x=72,y=100,page=1):
    return dict(text=text,bbox=[x,y,x+180,y+12],page=page,column=0,font='Helvetica',size=11,bold=False,rgb=[0,0,0],spans=[dict(text=text,bbox=[x,y,x+180,y+12],font='Helvetica',flags=0)])
def region(lines):return dict(reference='2',subreference='',alternative='',format='SUBJECTIVE',side='question',lines=lines,start=afm.fr.where(lines[0]),end_exclusive=dict(page=1,bbox=[0,700,0,700],column=0))

class AFMReconciliationTests(unittest.TestCase):
    def test_same_baseline_number_precedes_part_label(self):
        labels=[line('(a)',108,304.42),line('6.',72,304.68),line('Original fixture requirement.',140,304.68)]
        with patch.object(afm,'native_lines',return_value=labels):out=afm.cleaned_lines(None)
        self.assertEqual([x['text']for x in out],['6.','(a)','Original fixture requirement.'])
    def test_inline_parent_and_parts_are_separate_practice_records(self):
        q=region([line('2. (a) Explain the original test concept.'),line('(b) Calculate the test amount.',108,150)])
        a=region([line('2. (a) The original test explanation.'),line('(b) The test amount is 37.',108,150)])
        qs,ans,issues=afm.split_question(q,a)
        self.assertEqual([x['subreference']for x in qs],['a','b']);self.assertEqual([x['subreference']for x in ans],['a','b']);self.assertFalse(issues)
        self.assertIn('37',' '.join(l['text']for l in ans[1]['lines']))
    def test_answer_or_methods_do_not_create_question_alternatives(self):
        q=region([line('(a) Explain the original fixture.'),line('(b) Calculate the fixture.',72,200)])
        a=region([line('(a) Method one.'),line('OR',72,130),line('Method two.',72,150),line('(b) Result 37.',72,200)])
        qs,answers,issues=afm.split_question(q,a)
        self.assertFalse(issues);self.assertEqual(len(qs),2);self.assertEqual(len(answers),2)
        self.assertIn('OR',[l['text']for l in answers[0]['lines']])
    def test_key_number_without_dot_uses_same_row_only(self):
        rows=[line('3',72,100),line('Option (c)',120,100),line('Option (b)',120,135)]
        rows[0]['bbox'][2]=80
        keys=afm_mcq.keys_in(rows,None);self.assertEqual(keys['3']['correct_options'],['C'])
    def test_conflicting_key_is_not_verified(self):
        keys=afm_mcq.keys_in([line('1. Option (a)'),line('1. Option (b)',72,150)],None)
        self.assertTrue(keys['1']['conflict'])
    def test_bare_option_key_and_misplaced_number_punctuation(self):
        self.assertEqual(afm_mcq.keys_in([line('9. Option A')],None)['9']['correct_options'],['A'])
        rows=[line('.5'),line('(d)',300,100)];rows[0]['bbox'][2]=90
        self.assertEqual(afm_mcq.keys_in(rows,None)['5']['correct_options'],['D'])
        rows=[line('1.'),line('Option C',300,100)];rows[0]['bbox'][2]=90
        self.assertEqual(afm_mcq.keys_in(rows,None)['1']['correct_options'],['C'])
    def test_explicit_no_correct_option_never_becomes_an_invented_key(self):
        rows=[line('6.'),line('No correct option',300,100)];rows[0]['bbox'][2]=90
        key=afm_mcq.keys_in(rows,None)['6'];self.assertEqual(key['correct_options'],[]);self.assertTrue(key['no_correct_option'])
    def test_duplicate_printed_mcq_numbers_remain_distinct_and_keys_are_held(self):
        rows=[]
        for offset in [0,200]:
            rows.append(line('3.',72,100+offset));rows.append(line('Original independent fixture question.',100,100+offset))
            for n,label in enumerate('ABCD'):rows.append(line('('+label+') Original option '+label,100,130+offset+n*20))
        q=region(rows);q.update(reference='21',format='MCQ_CASE')
        rich=dict(body_html='<p>Original fixture</p>',plain_text='Original fixture',fidelity=dict(passed=True),blocks=[],warnings=[])
        with patch.object(afm_mcq.gold,'reconstruct',return_value=rich):out=afm_mcq.extract(q,None,scope='booklet')
        self.assertEqual(len(out),2);self.assertEqual(out[0]['reference'],out[1]['reference']);self.assertNotEqual(out[0]['source_section'],out[1]['source_section']);self.assertTrue(all(x['key']is None for x in out));self.assertTrue(all('duplicate_printed_question_number_requires_answer_content_review'in x['issues']for x in out))
    def test_bare_question_and_roman_numbers_are_retained(self):
        self.assertEqual(afm_mcq.number('6'),'6');self.assertEqual(afm_mcq.number('III',True),'III');self.assertIsNone(afm_mcq.number('300000'))
    def test_dot_options_are_detected_without_invented_cells(self):
        groups=afm_mcq.option_groups([line('A. 37'),line('B. 51',72,130),line('C. 69',72,160),line('D. 83',72,190)])
        self.assertEqual(len(groups),1);self.assertEqual([r[2]for r in groups[0]],list('ABCD'))
    def test_background_keyword_without_answer_corroboration_is_not_a_tag(self):
        q=region([line('The background mentions a call option.'),line('Explain financial policy.',72,130)])
        a=region([line('Financial policy concerns the selected corporate strategy.')])
        labels=[t['label']for t in afm.tags(q,a)]
        self.assertNotIn('Options valuation and strategies',labels);self.assertIn('Financial policy',labels)
    def test_answer_numerical_corroboration_is_evidence_not_approval(self):
        q=region([line('Original fixture project has cashflows of 370 and 510.')]);a=region([line('The fixture project cashflows include 370 and 510.')])
        evidence=afm.corroboration(q,a);self.assertTrue(evidence['corroborated']);self.assertNotIn('academic_approval',evidence)
    def test_pairing_never_crosses_mtp_series(self):
        def src(fid,series):return dict(file_id=fid,content_fingerprint=fid,identity=dict(actual_subject='AFM',source_type='mtp',exam_attempt='January 2026',document_issue_period='December 2025',series=series,scheme='current'))
        q=src('q','I');a=src('a','II');payloads={'q':dict(records=[]),'a':dict(records=[dict(region=dict(side='answer'))])}
        self.assertEqual(afm_bank.pair_sources(q,[q,a],payloads),[])
    def test_mtp_instructions_are_not_section_headings(self):
        import fitz
        doc=fitz.open();doc.new_page()
        rows=[line('Part I comprises multiple choice questions.'),line('Part II comprises descriptive questions.',72,125),line('PART I - Case Scenarios',72,150),line('1. Original objective fixture.',72,180),line('PART II - Descriptive Questions',72,250),line('1.',93,290),line('(a) Explain an original fixture.',115,290)]
        with patch.object(afm,'cleaned_lines',return_value=rows):records,profile=afm.discover(doc,dict(source_type='mtp',role='questions'))
        self.assertEqual([(q['reference'],q['format'])for q in records],[('1','MCQ'),('1','SUBJECTIVE')])
    def test_rtp_bare_answer_number_is_recovered_only_after_answer_section(self):
        import fitz
        doc=fitz.open();doc.new_page()
        rows=[line('1. Original independently authored question.',108,150),line('SUGGESTED ANSWERS',108,250),line('1 Original independently authored solution.',108,300)]
        with patch.object(afm,'cleaned_lines',return_value=rows):records,profile=afm.discover(doc,dict(source_type='rtp',role='questions_and_answers'))
        self.assertEqual([(q['reference'],q['side'])for q in records],[('1','question'),('1','answer')])
    def test_afm_does_not_crop_real_body_at_top_or_bottom(self):
        import fitz
        doc=fitz.open();doc.new_page();p=doc.new_page()
        p.insert_text((108,60),'14. Original source body at top.')
        p.insert_text((108,p.rect.height*.91),'Original calculation = 371.')
        ls=afm.cleaned_lines(doc);text=' '.join(l['text']for l in ls)
        self.assertIn('14.',text);self.assertIn('371',text)
    def test_offset_printed_folios_are_not_financial_amounts(self):
        import fitz
        doc=fitz.open()
        for pn in range(1,6):
            p=doc.new_page();p.insert_text((108,90),str(pn+4));p.insert_text((108,180),'Original financial amount 371.');p.insert_text((300,180),'37')
        rows=afm.native_lines(doc)
        self.assertFalse(any(l['bbox'][1]<100 and l['text'].isdigit()for l in rows));self.assertEqual(sum(l['text']=='37'for l in rows),5)
    def test_long_taxonomy_keys_fit_existing_schema_without_title_changes(self):
        long='source-backed-historical-context-'+'x'*110
        bank=dict(taxonomies={'edition':dict(editions=[],nodes=[dict(node_key=long,parent_key='',title='Original fixture title')])},subjective=[dict(import_record=dict(ai_proposal=dict(primary_path=[dict(node_key=long)],additional_node_keys=[long])))])
        mapping=afm_delivery.bounded_taxonomy(bank);node=bank['taxonomies']['edition']['nodes'][0]
        self.assertLessEqual(len(node['node_key']),120);self.assertEqual(node['title'],'Original fixture title');self.assertEqual(bank['subjective'][0]['import_record']['ai_proposal']['primary_path'][0]['node_key'],node['node_key']);self.assertIn(long,mapping)
    def test_merged_financial_stub_keeps_each_label_beside_its_values(self):
        import fitz
        doc=fitz.open();p=doc.new_page()
        labels=['Original flow','Original rate','Original total'];a=['37','51','69'];b=['83','97','113']
        for n in range(3):
            for x,text in [(72,labels[n]),(220,a[n]),(320,b[n])]:p.insert_text((x,120+n*20),text)
        model=dict(type='table',rows=3,columns=3,header_rows=0,page=1,bbox=[65,100,380,175],cells=[])
        for col,values,x0,x1,span in [(0,labels,65,190,3),(1,a,200,280,1),(2,b,300,380,1)]:model['cells'].append(dict(row=0,column=col,rowspan=span,colspan=1,text='\n'.join(values),bbox=[x0,100,x1,175]))
        fixed,ok=afm_tables.repair(model,p);self.assertTrue(ok);self.assertEqual(fixed['rows'],3)
        for n in range(3):self.assertEqual([c['text']for c in fixed['cells']if c['row']==n],[labels[n],a[n],b[n]])
    def test_vertical_math_fragments_are_not_declared_readable_by_numeric_checks(self):
        blocks=[dict(type='paragraph',html=x,page=1,bbox=[72,100+i*15,90,112+i*15])for i,x in enumerate(['n','(','1','+','r',')','2'])]
        rich=dict(blocks=blocks,body_html='',warnings=[],fidelity=dict(passed=True))
        fixed=afm_tables.normalize(rich,None);self.assertFalse(fixed['fidelity']['passed']);self.assertTrue(fixed['fidelity']['numeric_token_conservation_passed']);self.assertTrue(fixed['layout_exceptions'])
        self.assertFalse(afm_tables.formula_fragments([dict(type='paragraph',html='An original complete sentence.')]))

if __name__=='__main__':unittest.main()
