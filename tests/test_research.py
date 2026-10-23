"""Synthetic metadata tests only; no real ICAI content or private Drive IDs."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('pipeline', ROOT/'research/rtp_pipeline.py')
p = importlib.util.module_from_spec(spec); spec.loader.exec_module(p)


def fixture():
    edition = {'edition_key':'fr-may2026', 'subject_code':'FR'}
    tables = {kind:[] for kind in ('hierarchy','documents','occurrences','question_topics','answers')}
    tables['documents'] = [p.ordered('documents', dict(document_key='TEST-RESEARCH-DOC',edition_key='fr-may2026', title='TEST ONLY source',source_type='rtp',exam_attempt='TEST ONLY',official_url='https://www.icai.org/test-only-research.pdf'))]
    tables['occurrences'] = [p.ordered('occurrences', dict(occurrence_key='TEST-RESEARCH-OCC',question_key='TEST-RESEARCH-Q',question_title='TEST ONLY reference',document_key='TEST-RESEARCH-DOC',edition_key='fr-may2026',chapter_key='fr-may2026-m4-ch11',page_reference='PDF p.1',question_number='1',marks_verified='0',question_type='unknown'))]
    tables['question_topics'] = [p.ordered('question_topics', dict(question_key='TEST-RESEARCH-Q',node_key=k)) for k in ['fr-may2026-m4-ch11-u4-derivative-contracts','fr-may2026-m4-ch11-u4-embedded-features']]
    tables['answers'] = [p.ordered('answers',dict(answer_key='TEST-RESEARCH-A',question_key='TEST-RESEARCH-Q',occurrence_key='TEST-RESEARCH-OCC',answer_mode='official_link',official_url='https://www.icai.org/test-only-research.pdf',source_location='PDF p.2; Q1'))]
    return tables, {'fr-may2026':edition}, json.loads(p.CATALOGUE.read_text())


class ResearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Fresh GitHub checkouts intentionally contain no ignored private work/.
        (ROOT/'work').mkdir(mode=0o700, exist_ok=True)

    def test_official_urls(self):
        for url in ['http://icai.org/a','https://icai.org.evil.test/a','https://drive.google.com/a','https://www.icai.org/a?token=secret','https://a@icai.org/a','https://icai.org:443/a']:
            self.assertFalse(p.official_url(url))
        self.assertTrue(p.official_url('https://resource.cdn.icai.org/a.pdf'))

    def test_numbering_ignores_update_and_answer_sections(self):
        text='PART I UPDATE\n1. update\nQUESTIONS\n1. TEST FIRST\n2. TEST SECOND\fSUGGESTED ANSWERS\n1. answer\n2. answer\n'
        rows, errors=p.extract(text,'AUDIT')
        self.assertEqual([r['reference'] for r in rows],['1','2']);self.assertFalse(errors)
        self.assertEqual(rows[0]['answer_pages'],[2])

    def test_numbered_facts_before_mcqs(self):
        text='QUESTIONS\n1. fact\n2. fact\n1. TEST MCQ\n2. TEST MCQ\n3. TEST MCQ\nSUGGESTED ANSWERS\n'
        rows,_=p.extract(text,'IDT');self.assertIn('TEST MCQ',rows[0]['_private_chunk'])

    def test_ibs_decimal_case_references(self):
        text='QUESTIONS\n1.1 TEST\n1.2 TEST\n2.1 TEST\nSUGGESTED ANSWERS\n1.1 TEST\n'
        rows,_=p.extract(text,'IBS');self.assertEqual([r['reference'] for r in rows],['1.1','1.2','2.1'])

    def test_missing_boundaries(self):
        self.assertEqual(p.extract('scan only','FR'),([],['section_boundaries_missing']))

    def test_clean_package_and_multiple_tags(self):
        self.assertEqual(p.validate_package(*fixture()),[])

    def test_unverified_marks_and_private_url(self):
        t,e,c=fixture();t['occurrences'][0]['marks']='6';t['documents'][0]['official_url']='https://drive.google.com/private'
        errors=p.validate_package(t,e,c);self.assertTrue(any('Marks' in x['error'] for x in errors));self.assertTrue(any('URL' in x['error'] for x in errors))

    def test_duplicate_occurrence_distinct_key(self):
        t,e,c=fixture();r=copy.deepcopy(t['occurrences'][0]);r['occurrence_key']='TEST-DUPLICATE';t['occurrences'].append(r)
        self.assertTrue(any('Duplicate source occurrence' in x['error'] for x in p.validate_package(t,e,c)))

    def test_relationships_and_answer_rights(self):
        for field,value in [('question_key','missing'),('answer_text','TEST copyrighted payload'),('answer_mode','authored')]:
            t,e,c=fixture();t['answers'][0][field]=value;self.assertTrue(p.validate_package(t,e,c))
        t,e,c=fixture();t['occurrences'][0]['edition_key']='missing';self.assertTrue(p.validate_package(t,e,c))

    def test_cross_edition_tag_withheld(self):
        t,e,c=fixture();t['occurrences'][0]['edition_key']='historical';t['documents'][0]['edition_key']='historical';t['occurrences'][0]['chapter_key']='';e['historical']={'subject_code':'FR'}
        self.assertTrue(any('topic relationship' in x['error'] for x in p.validate_package(t,e,c)))

    def test_csv_formula_rejected(self):
        t,e,c=fixture();t['documents'][0]['title']='=HYPERLINK("x")';self.assertTrue(p.validate_package(t,e,c))

    def test_source_access_is_required(self):
        source=json.loads((ROOT/'research/manifest.example.json').read_text())['sources'][0]
        with self.assertRaisesRegex(ValueError,'Authorised'):p.check_manifest(source)

    def test_output_must_be_private_and_new(self):
        with self.assertRaises(ValueError):p.run('missing','research/public-export')
        with tempfile.TemporaryDirectory(dir=ROOT/'work') as existing:
            with self.assertRaises(ValueError):p.run('missing',existing)

    def test_prose_is_not_serialized_by_extractor(self):
        rows,_=p.extract('QUESTIONS\n1. SECRET TEST PROSE\nSUGGESTED ANSWERS\n1. SECRET SOLUTION\n','FR')
        rows[0].pop('_private_chunk');self.assertNotIn('SECRET',json.dumps(rows))

    def test_suggestions_use_existing_labels_only(self):
        c=json.loads(p.CATALOGUE.read_text());tags=p.suggest('Ind AS 116 and Ind AS 12','FR',c)
        self.assertGreaterEqual(len(tags),2);self.assertTrue(all(t['status']=='suggested_cross_edition_not_applied' for t in tags))

    def run_fixture(self, change=None):
        """Exercise the full private exporter with synthetic PDF text, no PDFs in Git."""
        with tempfile.TemporaryDirectory(dir=ROOT/'work') as temp:
            temp=Path(temp);pdf=temp/'test.pdf';pdf.write_bytes(b'%PDF-1.7 SYNTHETIC TEST ONLY')
            source=json.loads((ROOT/'research/manifest.example.json').read_text())['sources'][0]
            source.update(path='test.pdf',access_authorised=True,access_evidence='TEST ONLY attachment',expected_questions=2,annotations={})
            edition=json.loads((ROOT/'research/manifest.example.json').read_text())['edition_setup'][0]
            manifest={'sources':[source],'edition_setup':[edition]}
            if change:change(manifest)
            (temp/'manifest.json').write_text(json.dumps(manifest))
            text='FINANCIAL REPORTING\nREVISION TEST PAPERS\nJANUARY 2026 EXAMINATION\nQUESTIONS\n1. PRIVATE TEST QUESTION\n2. PRIVATE TEST QUESTION\n\fSUGGESTED ANSWERS\n1. PRIVATE TEST ANSWER\n2. PRIVATE TEST ANSWER\n\f'
            with mock.patch.object(p.subprocess,'run',return_value=SimpleNamespace(stdout=text.encode())):
                report=p.run(temp/'manifest.json',temp/'output')
            combined=''.join(f.read_text() for f in (temp/'output').iterdir())
            return report,combined

    def test_full_export_contains_metadata_without_prose(self):
        report,combined=self.run_fixture();self.assertEqual(report['counts']['occurrences'],2)
        self.assertEqual(report['validation'],'passed');self.assertNotIn('PRIVATE TEST QUESTION',combined);self.assertNotIn('PRIVATE TEST ANSWER',combined)

    def test_duplicate_source_does_not_discard_first_source(self):
        report,_=self.run_fixture(lambda m:m['sources'].append(copy.deepcopy(m['sources'][0])))
        self.assertEqual(len(report['sources']),1);self.assertEqual(report['counts']['occurrences'],2);self.assertTrue(report['errors'])

    def test_failed_count_withholds_source_atomically(self):
        report,_=self.run_fixture(lambda m:m['sources'][0].update(expected_questions=99))
        self.assertEqual(report['counts']['occurrences'],0);self.assertTrue(report['errors'])

    def test_unapproved_parts_and_marks_do_not_escape(self):
        report,combined=self.run_fixture(lambda m:m['sources'][0].update(annotations={'1':{'parts':['I','II'],'marks':'6'}}))
        self.assertEqual(report['counts']['occurrences'],2);self.assertEqual(report['review_gaps']['verified_marks'],0);self.assertEqual(len(report['errors']),2)


if __name__ == '__main__':
    (ROOT/'work').mkdir(exist_ok=True)
    unittest.main()
