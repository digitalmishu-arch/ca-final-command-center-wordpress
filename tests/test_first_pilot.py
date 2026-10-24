import json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'research'))
import first_pilot
class FirstPilotTests(unittest.TestCase):
 def fixture(self):
  return dict(question_identity='a'*64,source_sha256='b'*64,classification=dict(concept='Original test concept',historical_edition='TEST-ED',method='manual override',reasoning='Original synthetic fixture',taxonomy_match=True,official_nodes=[dict(node_key='TEST-CH',edition_key='TEST-ED',node_type='chapter',title='TEST Chapter',source_url='https://www.icai.org/test')],editorial_topics=['Original test navigation']),answer_candidates=[dict(page=4,bbox=[1,2,3,4],source_sha256='b'*64,official_url='https://www.icai.org/test.pdf')],document_key='TEST-SOURCE',subject='FR',source_type='rtp',attempt='TEST ATTEMPT',section='mcq',reference='6',subreference='',source_title='TEST Source Title',official_url='https://www.icai.org/test.pdf',start=dict(page=1,bbox=[1,2,3,4]),end_exclusive=dict(page=2,bbox=[1,2,3,4]),heading=None,warnings=['Needs review'],kind='mcq',ledger_event=None,engine_revision={},layout_blocked=False)
 def test_exact_source_and_draft_portable_transport(self):
  root=first_pilot.ROOT/'work';root.mkdir(exist_ok=True)
  with tempfile.TemporaryDirectory(dir=root) as tmp:
   p=Path(tmp);r=p/'review.json';r.write_text(json.dumps([self.fixture()]));first_pilot.build(r,'TEST-SOURCE','b'*64,['6'],p/'output');packet=json.loads((p/'output/studio-drafts-001.json').read_text())['records'][0];self.assertIsNone(packet['edition_id']);self.assertEqual(packet['classification'],[]);self.assertEqual(packet['rights_mode'],'reference_only');self.assertNotIn('approval_state',packet);self.assertNotIn('review_question_text',packet);self.assertEqual(packet['ai_proposal']['historical_edition'],'TEST-ED');self.assertTrue(packet['ai_proposal']['editorial_node_keys'])
 def test_number_alone_cannot_apply_to_another_source(self):
  root=first_pilot.ROOT/'work';root.mkdir(exist_ok=True)
  with tempfile.TemporaryDirectory(dir=root) as tmp:
   p=Path(tmp);r=p/'review.json';r.write_text(json.dumps([self.fixture()]));
   with self.assertRaises(ValueError):first_pilot.build(r,'OTHER-SOURCE','b'*64,['6'],p/'output')
 def test_ambiguous_answers_are_held(self):
  root=first_pilot.ROOT/'work';root.mkdir(exist_ok=True)
  with tempfile.TemporaryDirectory(dir=root) as tmp:
   p=Path(tmp);r=p/'review.json';data=self.fixture();data['answer_candidates']*=2;r.write_text(json.dumps([data]));
   with self.assertRaises(ValueError):first_pilot.build(r,'TEST-SOURCE','b'*64,['6'],p/'output')
if __name__=='__main__':unittest.main()
