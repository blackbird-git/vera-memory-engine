"""Run with: python3 -m unittest discover -s tests -v"""
import tempfile
import unittest
from pathlib import Path
from vera.db import connect, insert_memory, list_memories
from vera.retrieval import retrieve, format_context

class TestMemoryEngine(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.con = connect(Path(self.temp.name) / 'vera.sqlite3')
        self.a = insert_memory(self.con, title='Summer at the coast', contributor='Sarah',
                               kind='story', content='We went crabbing near the coast in 1986.')
        self.b = insert_memory(self.con, title='Grandma bread', contributor='Michael',
                               kind='story', content='Grandma baked bread on Sundays.')
    def tearDown(self):
        self.con.close()
        self.temp.cleanup()
    def test_list(self):
        self.assertEqual(len(list_memories(self.con)),2)
    def test_relevant_source(self):
        found = retrieve(self.con,'Where did we go crabbing?')
        self.assertEqual(found[0]['id'],self.a)
    def test_unknown_is_empty(self):
        self.assertEqual(retrieve(self.con,'Did we ever own an ostrich?'),[])
    def test_followup_preserves_source_when_no_match(self):
        found = retrieve(self.con,'What happened next?',previous_ids=[self.a])
        self.assertEqual(found[0]['id'],self.a)
    def test_context_contains_provenance(self):
        context = format_context(retrieve(self.con,'coast'))
        self.assertIn('Contributor: Sarah',context)
    def test_reject_empty_content(self):
        with self.assertRaises(ValueError):
            insert_memory(self.con,title='Hi',contributor='Sam',kind='story',content='  ')

if __name__ == '__main__':
    unittest.main()
