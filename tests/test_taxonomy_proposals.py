import unittest
from research.taxonomy_proposals import propose
class ProposalTests(unittest.TestCase):
 def fixture(self,units=False):
  nodes=[dict(node_key='ch1',node_type='chapter',title='Chapter 1: Original test chapter',subject_code='FR',edition_key='fr-may2026',parent_key='m1',position=100),dict(node_key='ch2',node_type='chapter',title='Chapter 2: Another test chapter',subject_code='FR',edition_key='fr-may2026',parent_key='m1',position=200)]
  if units:nodes.append(dict(node_key='u1',node_type='unit',parent_key='ch1'))
  source=dict(subject='FR',module=1,url='https://www.icai.org/test-metadata',lines={'1':dict(line=1,page=2,text='1. Original test concept ........... 1.3'),'2':dict(line=2,page=2,text='1.1 Original test detail ........... 1.4'),'3':dict(line=3,page=3,text='2. Another tested concept ........... 2.5')})
  return [source],dict(nodes=nodes)
 def test_printed_chapter_not_preceding_heading(self):
  s,c=self.fixture();r=propose(s,c);self.assertEqual(r['nodes'][-1]['parent_key'],'ch2')
 def test_missing_unit_never_guessed(self):
  s,c=self.fixture(True);r=propose(s,c);self.assertTrue(r['exceptions']);self.assertFalse(any(n['parent_key']=='ch1' for n in r['nodes']))
 def test_subtopics_draft_editorial(self):
  s,c=self.fixture();r=propose(s,c);self.assertEqual(r['nodes'][1]['node_type'],'subtopic');self.assertTrue(all(n['heading_origin']=='editorial' and n['publication_status']=='draft' for n in r['nodes']))
 def test_source_budget_and_edition(self):
  s,c=self.fixture();r=propose(s,c,3);self.assertLessEqual(r['sources'][0]['derived_label_words'],3);self.assertTrue(all(n['edition_key']=='fr-may2026' for n in r['nodes']))
if __name__=='__main__':unittest.main()
