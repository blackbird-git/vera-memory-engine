import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from vera.conversation import Conversation
from vera.db import connect,insert_memory
from vera.query import analyse
from vera.retrieval import retrieve


class IntentTests(unittest.TestCase):
    def test_historical_verbs_are_not_action_requests(self):
        for q in ['Did Sarah and Michael play on the beach?', 'Did Dad send postcards?', 'How did they share the bread?', 'Could Dana play piano?', 'Can you share a memory about the beach?']:
            with self.subTest(q=q):self.assertFalse(analyse(q).media_action)
    def test_direct_media_requests(self):
        for q in ['Can you play that recording?', 'Please play the audio.', 'Would you send me the photograph?', 'Share that photo.', 'Can you play it?']:
            with self.subTest(q=q):self.assertTrue(analyse(q).media_action)
    def test_scope_keeps_positive_topic_separate(self):
        for q in ['Tell me only about crabbing, not the whole vacation.', 'Focus on crabbing without the cottages.', 'Just crabbing; leave out bread.', 'Focus on crabbing; omit bread.', 'Crabbing except for the cottages.']:
            with self.subTest(q=q):
                spec=analyse(q);self.assertTrue(spec.narrow);self.assertTrue(spec.excluded)
                self.assertIn('crabbing',spec.positive.lower())
                self.assertNotIn('bread',spec.positive)
        self.assertFalse(analyse('Was Michael not sure of the year?').excluded)


class ContinuousAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.con=connect(Path(self.tmp.name)/'synthetic.sqlite3')
        for file in ('samples/demo_memories.json','samples/acceptance_extra.json'):
            for r in json.loads(Path(file).read_text()):insert_memory(self.con,**r)
        self.session=Conversation(self.con)
    def tearDown(self):self.con.close();self.tmp.cleanup()
    def answer(self,q):
        # A deliberately poor model selection must not omit required detail
        # coverage or widen the user's explicit scope.
        with patch('vera.conversation.generate',return_value='{"source_ids":[],"sentence_ids":[0]}'):
            return self.session.respond(q)
    def test_play_means_childhood_activity_after_unrelated_topic(self):
        self.answer('Tell me about Grandma bread.')
        answer=self.answer('Did Sarah and Michael play on the beach?')
        self.assertIn('sandcastle',answer);self.assertIn('Helen',answer)
        self.assertNotIn('not implemented',answer);self.assertNotIn('bread',answer);self.assertNotIn('cottage',answer)
    def test_scoped_crabbing_then_funny_detail(self):
        self.answer('Tell me about Grandma bread.');self.answer('Tell me about Oregon.')
        for q in ['Tell me only about the crabbing trip, not the whole vacation.', 'Was there anything funny about the crabbing trip?', 'Anything amusing about that?']:
            answer=self.answer(q)
            for term in ('Michael','fisherman','joked'):self.assertIn(term,answer)
            for term in ('sandcastle','cottage','bread','James'):self.assertNotIn(term,answer)
            self.assertEqual([p['source_id'] for p in self.session.evidence],[2])
    def test_negative_activity_mention_does_not_create_false_ambiguity(self):
        answer=self.answer('Tell me just about crabbing, not the vacation.')
        self.assertNotIn('Which event',answer)
        self.assertNotIn(6,self.session.metrics['planned_source_ids'])
    def test_bare_negation_does_not_retrieve_a_bread_account(self):
        found=retrieve(self.con,'Tell me only about crabbing, not the whole vacation.')
        self.assertFalse({4,5}&{r['id'] for r in found})
    def test_exclusion_filters_sentences_not_whole_mixed_memory(self):
        insert_memory(self.con,title='Mixed account',contributor='Synthetic Test',kind='story',content='We stayed in a cabin. We fished from the pier. We released the trout.',metadata={'events':['pier-day']})
        answer=self.answer('Tell me only about fishing, without the cabin.')
        self.assertIn('fished',answer);self.assertIn('trout',answer);self.assertNotIn('cabin',answer)
    def test_detail_coverage_is_general_not_a_family_answer_template(self):
        self.answer('Tell me about the lake boat ride.')
        answer=self.answer('Was anything funny about the boat ride?')
        self.assertIn('Nina',answer);self.assertIn('rowing lesson',answer)
        self.assertNotIn('pudding',answer);self.assertNotIn('sandwich',answer)
    def test_sentence_id_validation_rejects_out_of_bounds(self):
        with patch('vera.conversation.generate',return_value='{"source_ids":[2],"sentence_ids":[999]}'):
            self.assertIn("couldn't verify",self.session.respond('Was anything funny about crabbing?'))
        self.assertEqual(self.session.evidence,[])
    def test_no_accidental_write_during_scoped_conversation(self):
        before=self.con.total_changes
        self.answer('Tell me about Oregon.');self.answer('Tell me only about crabbing, not bread.')
        self.assertEqual(before,self.con.total_changes)
    def test_false_person_assumption_does_not_switch_away_from_current_subject(self):
        self.answer('Tell me about the garden.')
        answer=self.answer('Was Alex Reed the gardener?')
        self.assertIn('Alex Morgan',answer);self.assertIn('sunflowers',answer)
        self.assertNotIn('Washington',answer)
    def test_general_event_frame_words_do_not_change_subject(self):
        self.answer('Tell me about the lake boat ride.')
        answer=self.answer('Was there a funny incident in the boat account?')
        self.assertIn('rowing lesson',answer);self.assertNotIn('pudding',answer)
    def test_date_preamble_does_not_override_actual_question(self):
        self.answer('Tell me about crabbing.')
        answer=self.answer("I am unsure of the year, perhaps 1987. Was that an enjoyable activity for us?")
        self.assertIn("don't have",answer)
        self.assertNotIn('Sarah thinks it was summer',answer)
    def test_media_verb_in_preamble_does_not_override_historical_question(self):
        answer=self.answer('I can play a recording later. Did Sarah play on the beach?')
        self.assertIn('sandcastle',answer);self.assertNotIn('not implemented',answer)
