"""Regressions for observed semantic failures and conservative narration."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from vera.db import connect,insert_memory
from vera.conversation import Conversation
from vera.retrieval import retrieve
from vera.evidence import narrate,plan


class RelevanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.con=connect(Path(self.tmp.name)/'synthetic.sqlite3')
        for file in ('samples/demo_memories.json','samples/relevance_extra.json'):
            for r in json.loads(Path(file).read_text()):insert_memory(self.con,**r)
        self.session=Conversation(self.con)
    def tearDown(self):
        self.con.close();self.tmp.cleanup()
    def respond(self, question):
        with patch('vera.conversation.generate', return_value='{"source_ids":[]}'):
            return self.session.respond(question)
    def test_accommodation_synonym_retains_subject(self):
        self.respond('Tell me about Washington.')
        self.assertIn('tent',self.respond('What type of accommodation was mentioned?'))
        self.assertEqual(self.session.metrics['retrieved_ids'],[6])
    def test_denver_does_not_merge_different_events(self):
        self.assertEqual([r['id'] for r in retrieve(self.con,'train to Denver')],[8])
        self.assertEqual([r['id'] for r in retrieve(self.con,'birthday picnic')],[11])
    def test_longer_story_and_people_coverage(self):
        self.respond('Tell me about Oregon.')
        answer=self.respond('Tell me a longer version of that story.')
        for word in ('Newport','Sarah','Michael','Lisa','1986','1987','fisherman'):self.assertIn(word,answer)
    def test_person_dossier_across_events(self):
        answer=self.respond('Tell me about Sarah.')
        self.assertIn('birthday',answer);self.assertIn('coast',answer)
    def test_legacy_missing_person_link_uses_original_words(self):
        self.assertTrue({3,10,12} <= {r['id'] for r in retrieve(self.con,'Tell me about Lisa.')})
    def test_true_unknown_description_not_clock_mention(self):
        self.respond('Tell me about the train.')
        self.assertIn("don't have",self.respond('What did the clock look like?'))
        self.assertEqual(self.session.metrics['unknown_reason'],'requested_detail_not_in_sources')
    def test_no_silent_unknown_if_model_omits_sources(self):
        answer=self.respond('Tell me about Oregon.')
        self.assertIn('fisherman',answer);self.assertIn('Lisa',answer)
        self.assertEqual(self.session.metrics['coverage_recovered'],6)
    def test_focal_speaker_is_preserved_separately_from_event_dossier(self):
        self.respond('Tell me about Oregon.')
        self.respond('What happened after crabbing?')
        self.assertIn('Michael',self.respond('Who remembers that?'))
        self.assertIn('Sarah',self.respond('Who remembers the cottage?'))
    def test_every_passage_traces_to_original_sentences(self):
        self.respond('Tell me about Oregon.')
        for p in self.session.evidence:
            original=self.con.execute('SELECT content FROM memories WHERE id=?',(p['source_id'],)).fetchone()[0]
            for sentence in p['sentences']:self.assertIn(sentence,original)
            self.assertTrue(p['verified'])
    def test_unknown_never_reuses_previous_evidence(self):
        self.respond('Tell me about Oregon.')
        self.respond('Was Grandpa an astronaut?')
        self.assertEqual(self.session.evidence,[])
    def test_correction_included_without_overwriting_original(self):
        original=self.con.execute('SELECT content FROM memories WHERE id=1').fetchone()[0]
        self.session.respond('/correct 1 '+json.dumps({'title':'Corrected coast','contributor':'Sarah','content':'I now think it was 1987.','metadata':{'events':['oregon-coast']}}))
        self.session.respond('/confirm')
        self.assertIn('Sarah now thinks',self.respond('Tell me about Oregon.'))
        self.assertEqual(self.con.execute('SELECT content FROM memories WHERE id=1').fetchone()[0],original)
    def test_temporal_uncertainty_and_original_dialogue(self):
        text=narrate('I think it was 1986. Dad joked, “We caught it ourselves.”','Sarah','story')
        self.assertIn('Sarah thinks',text)
        self.assertIn('“We caught it ourselves.”',text)
    def test_narration_does_not_make_listener_participate(self):
        text=narrate('I remember when we were little. Dad took us crabbing.','Michael','story')
        self.assertIn('Michael remembers',text);self.assertNotIn(' us ',text);self.assertNotIn(' we ',text)
    def test_new_subject_not_lost_to_followup_state(self):
        self.respond('Tell me about the train.')
        self.assertIn('birthday',self.respond('Tell me about the birthday picnic.'))
        self.assertEqual(self.session.metrics['retrieved_ids'],[11])
    def test_story_does_not_write(self):
        before=self.con.total_changes
        self.respond('Tell me about Oregon.')
        self.assertEqual(before,self.con.total_changes)
    def test_description_is_known_when_a_related_source_actually_describes_it(self):
        insert_memory(self.con,title='Clock description',contributor='Synthetic Lee',kind='story',content='The station clock was round and blue.',metadata={'events':['train-denver']})
        self.respond('Tell me about the train.')
        self.assertIn('round and blue',self.respond('What did the clock look like?'))
    def test_model_latency_telemetry_is_distinct_from_turn_latency(self):
        from test_ollama_output import FakeResponse
        from vera.ollama import generate
        metrics={}
        with patch('vera.ollama.urlopen',return_value=FakeResponse({'response':'answer','done_reason':'stop','eval_duration':200_000_000,'prompt_eval_duration':100_000_000,'load_duration':50_000_000})):
            generate(question='Synthetic',context='Synthetic',model='qwen3:4b',url='http://localhost:11434',metrics=metrics)
        self.assertEqual(metrics['eval_s'],.2)
        self.assertEqual(metrics['prompt_eval_s'],.1)
        self.assertEqual(metrics['load_s'],.05)
        self.assertIn('inference_s',metrics)
    def test_singular_first_person_does_not_become_veras_family(self):
        text=narrate('I remember my father taking me fishing. I was unsure of the year.','Synthetic Sam','story')
        self.assertIn("Synthetic Sam's father",text)
        self.assertNotIn(' my ',text);self.assertNotIn(' me ',text)
        self.assertIn('says they were unsure',text)
    def test_receipt_question_does_not_dump_the_entire_event(self):
        answer=self.respond('Tell me about the rental receipt.')
        self.assertIn('Newport',answer);self.assertNotIn('crabbing',answer)
        self.assertEqual([p['source_id'] for p in self.session.evidence],[9])
    def test_first_person_possessive_still_attributes_the_fact(self):
        text=narrate('My birthday picnic was in 1990.','Sarah','story')
        self.assertIn('Sarah remembers',text);self.assertIn('1990',text)
