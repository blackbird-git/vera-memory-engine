"""Experiment invariants; these tests make no inference calls."""
import unittest
from experiments.model_comparison.client import request,api
from experiments.model_comparison.run import citation_checks


class ComparisonGuards(unittest.TestCase):
    def test_candidate_allowlist_before_any_network_call(self):
        with self.assertRaises(ValueError):request('remote:cloud',[])
    def test_api_path_rejects_external_url(self):
        with self.assertRaises(ValueError):api('https://example.com/collect')
    def test_citation_is_checked_against_real_note_text(self):
        notes=[{'id':1,'content':'I think it was 1986.'}]
        response={'answer':'Sarah thinks it was 1986.','evidence':[{'source_id':1,'quote':'It was definitely 1986.'}]}
        self.assertIn('nonverbatim_evidence',citation_checks(response,notes))
        response['evidence'][0]['quote']='I think it was 1986.'
        self.assertEqual(citation_checks(response,notes),[])
    def test_valid_quote_does_not_assert_semantic_grounding(self):
        # A true quote can accompany a false claim. Independent critics must
        # inspect the answer, not accept the citation validation as entailment.
        response={'answer':'It was definitely 1986.','evidence':[{'source_id':1,'quote':'I think it was 1986.'}]}
        self.assertEqual(citation_checks(response,[{'id':1,'content':'I think it was 1986.'}]),[])
    def test_unknown_needs_no_fabricated_citation(self):
        self.assertEqual(citation_checks({'answer':"I don't have that detail.",'evidence':[]},[]),[])
    def test_source_boolean_is_not_an_id(self):
        self.assertIn('invalid_source_id',citation_checks({'answer':'a','evidence':[{'source_id':True,'quote':'a'}]},[{'id':1,'content':'a'}]))
    def test_reasoning_inside_answer_is_rejected(self):
        self.assertIn('reasoning_content',citation_checks({'answer':'<think>secret</think>Answer.','evidence':[]},[]))
    def test_inconsistent_critic_cannot_approve(self):
        from experiments.model_comparison.grounding import validate_grounding
        self.assertEqual(validate_grounding({'supported':True,'unsupported_claims':['false']},'false'),(False,'critic_inconsistent'))
    def test_nonliteral_critic_claim_is_invalid(self):
        from experiments.model_comparison.grounding import validate_grounding
        self.assertEqual(validate_grounding({'supported':False,'unsupported_claims':['invented accusation']},'a real answer'),(False,'critic_nonliteral_claim'))
    def test_fallback_requires_two_valid_independent_checks(self):
        from experiments.model_comparison.summarize import choose_final
        natural={'raw_answer':'draft'};base={'raw_answer':'source excerpt'}
        approved=[{'grounding_pass':True,'judge':'reviewer_a'},{'grounding_pass':True,'judge':'reviewer_b'}]
        self.assertEqual(choose_final(natural,base,approved,approved)[1],'natural')
        self.assertEqual(choose_final(natural,base,[{'grounding_pass':False}],approved)[1],'excerpt_fallback')
        self.assertEqual(choose_final(natural,base,[],[])[1],'neutral_fallback')
    def test_invalid_citation_forces_fallback_even_if_critics_approve(self):
        from experiments.model_comparison.summarize import choose_final
        approved=[{'grounding_pass':True,'judge':'reviewer_a'},{'grounding_pass':True,'judge':'reviewer_b'}]
        result=choose_final({'raw_answer':'draft','validation_errors':['invented']},{'raw_answer':'excerpt'},approved,approved)
        self.assertEqual(result[1],'excerpt_fallback')
    def test_validated_excerpt_policy_preserves_existing_engine_fallback(self):
        from experiments.model_comparison.summarize import choose_final
        result=choose_final({'raw_answer':'draft'},{'raw_answer':'validated excerpt'},[],[],policy='validated_excerpt')
        self.assertEqual(result[:2],('validated excerpt','excerpt_fallback'))
        result=choose_final({'raw_answer':'draft'},{'raw_answer':'failed','error':'transport'},[],[],policy='validated_excerpt')
        self.assertEqual(result[1],'neutral_fallback')
    def test_validated_excerpt_policy_still_requires_independent_natural_checks(self):
        from experiments.model_comparison.summarize import choose_final
        duplicate=[{'grounding_pass':True,'judge':'same'}]*2
        self.assertEqual(choose_final({'raw_answer':'draft'},{'raw_answer':'excerpt'},duplicate,[],policy='validated_excerpt')[1],'excerpt_fallback')
    def test_incomplete_reviews_cannot_be_reported_as_completed_comparison(self):
        import json,tempfile
        from pathlib import Path
        from unittest.mock import patch
        from experiments.model_comparison.summarize import main
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);generations=root/'generations.json';reviews=root/'reviews.json';output=root/'summary.json'
            generations.write_text(json.dumps({'rows':[{'model':'qwen3:4b','strategy':'excerpt','sequence':'s','turn':0}]}))
            reviews.write_text('{"rows":[]}')
            with patch('sys.argv',['summarize','--generations',str(generations),'--reviews',str(reviews),'--output',str(output)]):
                with self.assertRaisesRegex(RuntimeError,'Incomplete'):main()
            self.assertFalse(output.exists())
    def test_duplicate_reviewer_is_not_independent_consensus(self):
        from experiments.model_comparison.summarize import choose_final
        duplicate=[{'grounding_pass':True,'judge':'same'}]*2
        self.assertEqual(choose_final({'raw_answer':'draft'},{'raw_answer':'excerpt'},duplicate,duplicate)[1],'neutral_fallback')
    def test_complete_comparison_reports_review_coverage(self):
        import json,tempfile
        from pathlib import Path
        from unittest.mock import patch
        from experiments.model_comparison.summarize import main,DIMS
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);g=root/'g.json';r=root/'r.json';out=root/'out.json'
            rows=[{'model':'qwen3:4b','strategy':strategy,'sequence':'s','turn':0,'question':'Unknown?','gold':{'facts':[],'exclude':[],'kind':'unknown','max_sentences':0},'novel':False,'raw_answer':"I don't know.",'latency_s':.1,'calls':[]} for strategy in ('excerpt','natural')]
            reviews=[{'model':row['model'],'strategy':row['strategy'],'sequence':'s','turn':0,'judge':judge,'grounding_pass':True,'latency_s':.1,'quality':{d:4 for d in DIMS}} for row in rows for judge in ('a','b')]
            g.write_text(json.dumps({'rows':rows,'configuration':{'models':['qwen3:4b']},'resources':[]}));r.write_text(json.dumps({'rows':reviews}))
            with patch('sys.argv',['summarize','--generations',str(g),'--reviews',str(r),'--output',str(out)]),patch('builtins.print'):main()
            for cell in json.loads(out.read_text())['cells']:
                self.assertEqual(cell['valid_quality_reviews'],2)
                self.assertEqual(cell['expected_quality_reviews'],2)
