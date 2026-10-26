"""Compact delivery uses original synthetic content, never private research data."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'research'))
from academic_package import build


class AcademicPackage(unittest.TestCase):
    def test_manifest_dependency_hashes_and_no_academic_approval(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'taxonomy-imports').mkdir();(root/'TEST/imports').mkdir(parents=True)
            (root/'taxonomy-imports/official-hierarchy-001.json').write_text(json.dumps(dict(batch_key='TEST',nodes=[])))
            original=dict(stable_id='TEST-Q1',quality_checks=dict(owner_approved=True),rights_grant_id=999,rich_content=dict(question=dict(body_html='<p>TEST original question.</p>'),answer=dict(body_html='<p>TEST original solution.</p>')))
            question=root/'TEST/imports/studio-drafts-001.json';question.write_text(json.dumps(dict(batch_key='TEST-Q',records=[original])))
            sources=root/'sources.json';sources.write_text(json.dumps(dict(sources=[dict(technical_state='pdf_checked'),dict(technical_state='retrieval_blocked')])))
            rights=root/'rights.json';rights.write_text(json.dumps(dict(declaration_key='TEST-PHYSICAL',scope=dict(confirmation_method='owner_attestation'))))
            (root/'private.pdf').write_bytes(b'TEST nonpublishable placeholder')
            output=root/'academic.zip';report=build(root,output,'TEST-ACADEMIC',sources,rights)
            self.assertEqual(report['sha256'],hashlib.sha256(output.read_bytes()).hexdigest())
            with zipfile.ZipFile(output) as archive:
                self.assertTrue(all(n.endswith('.json') for n in archive.namelist()))
                manifest=json.loads(archive.read('manifest.json'));self.assertEqual([i['kind'] for i in manifest['items']],['taxonomy','sources','rights','questions'])
                for item in manifest['items']:
                    data=archive.read(item['path']);self.assertEqual(len(data),item['bytes']);self.assertEqual(hashlib.sha256(data).hexdigest(),item['sha256'])
                record=json.loads(archive.read('items/questions_001.json'))['records'][0]
                self.assertEqual(record['stable_id'],original['stable_id']);self.assertEqual(record['rich_content'],original['rich_content']);self.assertFalse(record['quality_checks']);self.assertIsNone(record['rights_grant_id'])
                self.assertEqual(manifest['coverage']['pdfs_read'],1);self.assertEqual(manifest['coverage']['technical_blocks'],1);self.assertEqual(manifest['coverage']['academic_approvals'],0)
            self.assertEqual(json.loads(question.read_text())['records'][0],original)
            with self.assertRaises(ValueError):build(root,output,'TEST-ACADEMIC',sources,rights)


if __name__=='__main__':unittest.main()
