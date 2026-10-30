"""Authored-only regression fixtures; no ICAI question prose."""
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'research'))
import afm_reconcile as afm
import afm_structure as structure

def line(text,x=108,y=100):return dict(text=text,page=1,column=0,bbox=[x,y,510,y+12],size=11,spans=[dict(text=text,font='Authored',flags=0,bbox=[x,y,510,y+12])])
def region(lines,side='question'):return dict(reference='3',subreference='',alternative='',side=side,format='SUBJECTIVE',heading=None,lines=lines,start=dict(page=1,bbox=lines[0]['bbox']),end_exclusive=dict(page=1,bbox=[108,700,510,712]),source_type='mtp')
class CompleteProblemTests(unittest.TestCase):
 def test_nested_requirements_share_complete_problem_and_answer(self):
  q=region([line('(a) Authored investment fixture has common facts.'),line('(i) Calculate the original project value.',130,150),line('(ii) Explain the sensitivity of that same project.',130,200),line('(b) Explain a different financing policy.',108,260)])
  a=region([line('(a) Complete authored solution follows.'),line('(i) The original project value calculation.',130,150),line('(ii) Sensitivity of that same project.',130,200),line('(b) Different policy solution.',108,260)],'answer')
  qs,ans,_=structure.complete_parts(q,a);self.assertEqual([x['subreference']for x in qs],['a','b']);self.assertEqual([x['subreference']for x in ans],['a','b']);self.assertTrue(any('(ii)'in l['text']for l in qs[0]['lines']));self.assertTrue(any('(ii)'in l['text']for l in ans[0]['lines']))
 def test_unlettered_roman_requirements_do_not_default_to_standalone_entries(self):
  q=region([line('3. Authored shared cashflows: 37, 51.'),line('(i) Calculate the project value.',130,150),line('(ii) Calculate sensitivity.',130,200)])
  a=region([line('3. Solution for the same authored cashflows.'),line('(i) Value calculation.',130,150),line('(ii) Sensitivity calculation.',130,200)],'answer');qs,ans,_=structure.complete_parts(q,a);self.assertEqual(len(qs),1);self.assertEqual(len(ans),1)
 def test_alternative_workings_do_not_destroy_other_answer_parts(self):
  qs=[dict(subreference=r,alternative=alt)for r,alt in [('a',''),('b',''),('c','either'),('c','or')]]
  a=region([line('(a) First solution.'),line('(b) Second solution.',108,150),line('OR',150,175),line('Another method.',150,195),line('OR',150,215),line('Third method.',150,235),line('(c) Either answer.',108,260),line('(c) OR',108,300),line('Alternative answer.',130,330)],'answer')
  ans,w=structure.answer_parts(qs,a);self.assertEqual(w,[]);self.assertEqual([(x['subreference'],x['alternative'])for x in ans],[('a',''),('b',''),('c','either'),('c','or')]);self.assertEqual(sum(l['text']=='OR'for l in ans[1]['lines']),2)
 def test_inline_parent_number_does_not_shift_answer_part_margin(self):
  qs=[dict(subreference=x,alternative='')for x in 'ab'];a=region([line('3. (a) Original complete solution.',72,100),line('Some workings.',150,130),line('(b) Separate second solution.',108,170)],'answer');ans,w=structure.answer_parts(qs,a);self.assertEqual([x['subreference']for x in ans],['a','b']);self.assertEqual(w,[])
 def test_missing_alternative_does_not_erase_unambiguous_answer_a(self):
  qs=[dict(subreference='a',alternative=''),dict(subreference='b',alternative='either'),dict(subreference='b',alternative='or')];a=region([line('(a) Exact first part.'),line('(b) Ambiguous alternative solution.',108,170)],'answer');ans,w=structure.answer_parts(qs,a);self.assertEqual([x['subreference']for x in ans],['a']);self.assertTrue(w)
 def test_substantive_letter_restart_at_shifted_margin_is_flagged(self):
  q=region([line('(b)',126,100),line('First scenario table continuation.',148,130),line('(b) Original Other Ltd begins a different financing problem.',108,220)]);issues=structure.boundary_conflicts(q);self.assertEqual(len(issues),1);self.assertEqual(issues[0]['printed_part'],'b')
 def test_gdr_requirement_has_its_own_editorial_finance_concept(self):
  q=region([line('Compute the number of GDRs and their financing cost.')]);a=region([line('The GDRs have a fixture financing cost.')],'answer');tags=afm.tags(q,a);self.assertTrue(any(t['chapter']==11 and 'Depository receipts'in t['label']for t in tags));self.assertTrue(all(t['origin']=='editorial'for t in tags))
 def test_out_of_order_working_labels_are_not_silently_assigned(self):
  qs=[dict(subreference=x,alternative='')for x in 'ab'];a=region([line('(a) First part.'),line('(b) Next part.',108,150),line('(a) Unexpected reused main-margin label.',108,200)],'answer');ans,w=structure.answer_parts(qs,a);self.assertEqual(ans,[]);self.assertTrue(w)
if __name__=='__main__':unittest.main()
