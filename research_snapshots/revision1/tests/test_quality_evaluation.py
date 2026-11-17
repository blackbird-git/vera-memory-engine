"""Benchmark assertions should reject plausible but incorrect results."""
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from vera.db import connect,insert_memory

# The scripts are runnable directly without installing an application package.
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from evaluate_quality import score,audit_evidence
from quality_cases import turn


class QualityEvaluationTests(unittest.TestCase):
    def test_surface_facts_do_not_hide_wrong_unknown_behavior(self):
        expected=turn('What accommodation?',sources=[1],facts=['tent'])
        wrong=score(expected,{'answer':"I don't have that detail about the tent.",'retrieved_ids':[]})
        self.assertEqual(wrong['retrieval_recall'],0)
        self.assertFalse(wrong['behavior'])
        self.assertEqual(wrong['answer_completeness'],1)
    def test_fabricated_wording_fails_independent_archive_audit(self):
        with tempfile.TemporaryDirectory() as tmp:
            con=connect(Path(tmp)/'synthetic.sqlite3')
            i=insert_memory(con,title='Date',contributor='Synthetic Sam',kind='story',content='I think it was possibly 1986.')
            p={'source_id':i,'quote':'I think it was possibly 1986.','sentences':['I think it was possibly 1986.'],'text':'Synthetic Sam thinks it was possibly 1987.','verified':True}
            self.assertFalse(audit_evidence(con,p,p['text']))
            p['text']='Synthetic Sam thinks it was possibly 1986.'
            self.assertTrue(audit_evidence(con,p,p['text']))
            p['text']='Synthetic Sam thinks it was 1986.'
            self.assertFalse(audit_evidence(con,p,p['text']))
            con.close()
    def test_false_claim_blacklist_is_separate_from_positive_facts(self):
        result=score(turn('Did he win?',kind='unknown',forbidden=['won a medal']),{'answer':"I don't have records, but he won a medal.",'source_ids':[]})
        self.assertFalse(result['behavior'])
    def test_acceptance_metric_penalizes_dumping_unrelated_but_grounded_material(self):
        from evaluate_acceptance import assess
        result=assess({'required':['fisherman'],'forbidden':['bread']},'Michael remembers a fisherman. James remembers bread.',[], 'archive_question')
        self.assertTrue(result['target_detail_complete'])
        self.assertFalse(result['constraint_compliant']);self.assertFalse(result['passed'])
    def test_correct_source_is_insufficient_when_the_requested_detail_is_missing(self):
        from evaluate_acceptance import assess
        result=assess({'required':['joked'],'allowed_sources':[2],'sentence_patterns':['joked']},'Michael remembers crabbing.',[{'source_id':2,'sentences':['Dad took us crabbing but we caught nothing.']}], 'archive_question')
        self.assertEqual(result['answer_precision'],0)
        self.assertFalse(result['target_detail_complete']);self.assertFalse(result['passed'])
    def test_media_action_gold_does_not_default_to_historical_intent(self):
        from evaluate_acceptance import assess
        result=assess({'required':['not implemented']},'Media playback is not implemented.',[],'media_action')
        self.assertTrue(result['passed'])
