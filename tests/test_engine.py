import json
import sqlite3
import tempfile
from contextlib import closing
import unittest
from pathlib import Path
from unittest.mock import patch
from vera.db import connect, insert_memory, get_memories, delete_memory
from vera.conversation import Conversation
from vera.retrieval import retrieve
from vera.ollama import generate, final_answer_only


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / 'archive.sqlite3'
        self.con = connect(self.path)
        self.records = json.loads(Path('samples/demo_memories.json').read_text())
        for r in self.records: insert_memory(self.con, **r)
        self.session = Conversation(self.con)
    def tearDown(self):
        self.con.close()
        self.temp.cleanup()
    def test_integrity_and_fts_delete(self):
        self.assertEqual(self.con.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
        delete_memory(self.con,8)
        self.assertEqual(retrieve(self.con,'station'),[])
    def test_explicit_place_excludes_similar_event(self):
        rows=retrieve(self.con,'Oregon coast')
        self.assertEqual({r['id'] for r in rows},{1,2,3})
    def test_conflicting_accounts_stay_together(self):
        rows=retrieve(self.con,'crabbing')
        self.assertTrue({1,2,3}.issubset({r['id'] for r in rows}))
    def test_followup_keeps_event_and_photo(self):
        rows=retrieve(self.con,'Who remembers that?',previous_ids=[2,1,3])
        self.assertEqual({r['id'] for r in rows},{1,2,3})
    def test_unrelated_unknown_drops_previous(self):
        self.assertEqual(retrieve(self.con,'Did anyone own an ostrich?',previous_ids=[1,2,3]),[])
    def test_same_name_asks_clarification(self):
        self.assertIn('Which event',self.session.respond('Tell me about Alex'))
    def test_no_implicit_save(self):
        with patch('vera.conversation.generate', return_value=json.dumps({'excerpts':[]})):
            before=self.con.total_changes
            self.session.respond('Remember that Sarah owned a spaceship on the Oregon trip')
            self.assertEqual(before,self.con.total_changes)
    def test_explicit_confirmation(self):
        r={'title':'New note','contributor':'Synthetic Sam','content':'  Original wording.  '}
        before=self.con.total_changes
        self.session.respond('/remember '+json.dumps(r))
        self.assertEqual(before,self.con.total_changes)
        self.assertIn('Saved', self.session.respond('/confirm'))
        row=self.con.execute('SELECT content FROM memories WHERE title=?',('New note',)).fetchone()
        self.assertEqual(row[0],r['content'])
        self.assertIn('no pending',self.session.respond('/confirm'))
    def test_cancel_and_intervening_turn(self):
        r={'title':'No save','contributor':'Synthetic','content':'No save'}
        self.session.propose(r)
        self.session.respond('/cancel')
        self.assertIn('no pending',self.session.respond('/confirm'))
        self.session.propose(r)
        self.session.respond('Unknown ostrich')
        self.assertIn('no pending',self.session.respond('/confirm'))
    def test_correction_preserves_original(self):
        original=self.con.execute('SELECT content FROM memories WHERE id=1').fetchone()[0]
        self.session.respond('/correct 1 '+json.dumps(dict(title='Corrected coast',contributor='Sarah',content='It may have been 1987.')))
        self.session.respond('/confirm')
        self.assertEqual(self.con.execute('SELECT content FROM memories WHERE id=1').fetchone()[0], original)
        self.assertEqual(get_memories(self.con,[1]),[])
    def test_confirm_delete(self):
        self.session.respond('/delete 8')
        self.assertTrue(get_memories(self.con,[8]))
        self.session.respond('/confirm')
        self.assertEqual(get_memories(self.con,[8]),[])
    def test_reject_fake_citations_and_malformed_json(self):
        for reply in ['not JSON','{"answer":"Invented","source_ids":[999]}']:
            with self.subTest(reply=reply),patch('vera.conversation.generate',return_value=reply):
                self.assertIn("couldn't verify",self.session.respond('Oregon'))
                self.assertTrue(self.session.metrics['validation_rejected'])
    def test_migration_backup_verified(self):
        p=Path(self.temp.name)/'legacy.sqlite3'
        c=sqlite3.connect(p);c.execute('CREATE TABLE sentinel(value TEXT)');c.execute("INSERT INTO sentinel VALUES('synthetic')");c.commit();c.close()
        c=connect(p);c.close()
        copies=list((p.parent/'backups').glob('legacy*'))
        self.assertEqual(len(copies),1)
        with closing(sqlite3.connect(copies[0])) as backup:
            self.assertEqual(backup.execute('PRAGMA integrity_check').fetchone()[0],'ok')
            self.assertEqual(backup.execute('SELECT value FROM sentinel').fetchone()[0],'synthetic')
    def test_loopback_only(self):
        with self.assertRaises(ValueError): generate(question='x',context='x',model='qwen3:4b',url='https://example.com')
    def test_double_limit_is_safe(self):
        from test_ollama_output import FakeResponse
        with patch('vera.ollama.urlopen',return_value=FakeResponse({'done_reason':'length','response':'<think>secret'})) as call:
            with self.assertRaises(RuntimeError): generate(question='x',context='x',model='qwen3:4b',url='http://localhost:11434')
            self.assertEqual(call.call_count,2)
    def test_transport_failure(self):
        with patch('vera.ollama.urlopen',side_effect=TimeoutError):
            with self.assertRaises(RuntimeError): generate(question='x',context='x',model='qwen3:4b',url='http://localhost:11434')
    def test_reasoning_variants(self):
        for answer in ['<THINK>secret','Analysis: secret','Let me think about the user']:
            with self.subTest(answer=answer),self.assertRaises(RuntimeError): final_answer_only(answer)

class ImportTests(unittest.TestCase):
    def test_import_rolls_back_on_invalid_record(self):
        from vera.__main__ import load_json
        with tempfile.TemporaryDirectory() as tmp:
            con=connect(Path(tmp)/'test.sqlite3')
            path=Path(tmp)/'import.json'
            path.write_text(json.dumps([dict(title='Synthetic',contributor='Test',content='Valid'),dict(title='Invalid')]))
            with self.assertRaises(KeyError): load_json(con,path)
            self.assertEqual(con.execute('SELECT count(*) FROM memories').fetchone()[0],0)
            con.close()
    def test_valid_excerpt_and_date_conflicts(self):
        with tempfile.TemporaryDirectory() as tmp:
            con=connect(Path(tmp)/'test.sqlite3')
            for record in json.loads(Path('samples/demo_memories.json').read_text()): insert_memory(con,**record)
            session=Conversation(con)
            with patch('vera.conversation.generate', return_value='{"excerpts":[]}'):
                reply=session.respond('Was the Oregon trip definitely in 1986?')
            self.assertIn('1986',reply);self.assertIn('1987',reply);self.assertIn('Sarah',reply);self.assertIn('Michael',reply)
            con.close()

class ClientDefenseTests(unittest.TestCase):
    def test_assistant_history_is_not_evidence(self):
        from test_ollama_output import FakeResponse
        with patch('vera.ollama.urlopen',return_value=FakeResponse({'response':'A clean answer.','done_reason':'stop'})) as call:
            generate(question='Who remembers that?',context='Synthetic archive note',model='qwen3:4b',url='http://localhost:11434',history=[{'role':'assistant','content':'invented spaceship'},{'role':'user','content':'Oregon'}])
            body=json.loads(call.call_args.args[0].data)
            self.assertNotIn('invented spaceship',body['prompt'])
            self.assertIn('Oregon',body['prompt'])
            self.assertEqual(body['options']['num_ctx'],8192)
    def test_redirects_are_blocked(self):
        from vera.ollama import NoRedirect
        with self.assertRaises(RuntimeError): NoRedirect().redirect_request(None,None,None,None,None,None)
    def test_malformed_and_unfinished_response(self):
        from test_ollama_output import FakeResponse
        for payload in [{'done':False,'response':'partial'},{'message':{'content':None}},{'response':'ok','eval_count':'invalid'}]:
            with self.subTest(payload=payload),patch('vera.ollama.urlopen',return_value=FakeResponse(payload)):
                with self.assertRaises(RuntimeError): generate(question='x',context='x',model='qwen3:4b',url='http://localhost:11434')

class FollowupRegressionTests(unittest.TestCase):
    def test_continuation_and_explicit_attribution(self):
        with tempfile.TemporaryDirectory() as tmp:
            con=connect(Path(tmp)/'test.sqlite3')
            for record in json.loads(Path('samples/demo_memories.json').read_text()): insert_memory(con,**record)
            session=Conversation(con,source_ids=[1,2,3])
            with patch('vera.conversation.generate',return_value=json.dumps({'excerpts':[{'source_id':2,'quote':'Dad took us crabbing but we caught nothing.'}]})):
                self.assertIn('fisherman', session.respond('What happened after crabbing?'))
                reply=session.respond('Who remembers the cottage?')
                self.assertIn('Sarah',reply)
                self.assertNotIn('Michael (synthetic example) recalls:',reply)
            con.close()
