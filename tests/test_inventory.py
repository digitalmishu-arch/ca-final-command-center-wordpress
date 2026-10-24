import json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'research'))
import inventory,bridge
ROOT=Path(__file__).resolve().parents[1]
class InventoryTests(unittest.TestCase):
 def setUp(self):
  (ROOT/'work').mkdir(exist_ok=True)
  self.tmp=tempfile.TemporaryDirectory(dir=ROOT/'work');self.p=Path(self.tmp.name)
 def tearDown(self):self.tmp.cleanup()
 def test_reconcile_access_is_not_rights_and_refresh_keeps_decisions(self):
  w=self.p/'book.json';s=self.p/'snap.json';db=self.p/'jobs.sqlite'
  w.write_text(json.dumps(dict(values=[['header'],['FR','RTP','RTP','File','JAN 2026','JAN 2026','New','','https://www.icai.org/post/test','draft','id1']])));s.write_text(json.dumps(dict(folders=[dict(folder=dict(id='folder',path='FR'),result=dict(structuredContent=dict(files=[dict(id='id1',mime_type='application/pdf',can_download=True)])))])))
  r=inventory.reconcile(w,s,db);self.assertEqual(r['availability'],{'listed_downloadable':1});con=inventory.connect(db);self.assertEqual(con.execute('SELECT status FROM jobs').fetchone()[0],'awaiting_rights');con.execute("UPDATE jobs SET rights_state='owner_attested',status='processed'");con.commit();inventory.reconcile(w,s,db);self.assertEqual(con.execute('SELECT rights_state,status FROM jobs').fetchone()[:],('owner_attested','processed'))
 def test_rights_gate_precedes_file_read(self):
  mp=self.p/'manifest.json';mp.write_text(json.dumps(dict(sources=[dict(document_key='no-access',path='file-that-must-not-be-read.pdf')])));r=inventory.process(self.p/'db.sqlite',mp);self.assertEqual(r[0]['status'],'awaiting_rights')
 def test_batch_resume_and_idempotence_include_new_owner_ledger(self):
  mp=self.p/'manifest.json';sources=[]
  for i in range(5):
   f=self.p/f'{i}.pdf';f.write_bytes(b'%PDF-TEST ORIGINAL '+str(i).encode());sources.append(dict(document_key=f'test-{i}',path=f.name,private_extraction_authorised=True,private_copy_basis='Original synthetic fixture',source_type='rtp'))
  mp.write_text(json.dumps(dict(sources=sources)));state=self.p/'db.sqlite'
  def fake_run(manifest,out,**kwargs):out.mkdir(parents=True);(out/'report.json').write_text('{"source_failures":0}');(out/'review.json').write_text('[]')
  with patch('layout_pipeline.run',side_effect=fake_run) as run:
   first=inventory.process(state,mp,limit=2);self.assertEqual(sum(r['status']=='processed' for r in first),2);second=inventory.process(state,mp,limit=2);self.assertEqual(sum(r['status']=='processed' for r in second),2);third=inventory.process(state,mp,limit=2);self.assertEqual(sum(r['status']=='processed' for r in third),1);again=inventory.process(state,mp,limit=2);self.assertTrue(all(r['status']=='skipped_idempotent' for r in again));self.assertEqual(run.call_count,5)
   ledger=self.p/'ledger.json';ledger.write_text('{"version":1,"events":[]}');inventory.process(state,mp,limit=1,ledger=ledger);self.assertEqual(run.call_count,6)
 def test_actual_exam_does_not_assume_rtp_profile(self):
  mp=self.p/'manifest.json';mp.write_text(json.dumps(dict(sources=[dict(document_key='exam',path='unread.pdf',source_type='exam',private_extraction_authorised=True,private_copy_basis='test')])));self.assertEqual(inventory.process(self.p/'db.sqlite',mp)[0]['status'],'awaiting_layout_review')
 def test_packet_omits_pdf_prose_drive_links_and_approvals(self):
  r=dict(question_identity='a'*64,source_sha256='b'*64,classification=dict(concept='TEST',official_nodes=[],editorial_topics=['TEST original topic']),answer_candidates=[],document_key='test-source',subject='FR',source_type='rtp',attempt='TEST',section='mcq',reference='2',subreference='I',source_title='TEST original title',official_url='https://www.icai.org/test.pdf',start=dict(page=1,bbox=[1,2,3,4]),end_exclusive=dict(page=1,bbox=[1,20,30,40]),warnings=[],kind='mcq',question_text='DO NOT COPY TEST prose')
  p=bridge.packet(r);self.assertNotIn('question_text',p);self.assertNotIn('DO NOT COPY',json.dumps(p));self.assertIsNone(p['edition_id']);self.assertEqual(p['classification'],[]);self.assertEqual(p['rights_mode'],'reference_only');self.assertNotIn('publication_status',p)
if __name__=='__main__':unittest.main()
