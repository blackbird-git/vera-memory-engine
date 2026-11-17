"""Synthetic-only full-path reproduction against actual local Ollama."""
import argparse
import hashlib
import json
import tempfile
import time
from pathlib import Path
from unittest.mock import patch
from vera.db import connect,insert_memory
from vera.conversation import Conversation
from vera.ollama import generate as live_generate
from vera.retrieval import retrieve
import vera.ollama as client

QUESTIONS=['Did Sarah and Michael play on the beach?',
           'Tell me only about the crabbing trip, not the whole vacation.',
           'Was there anything funny about the crabbing trip?']

def main():
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);args=p.parse_args()
 report={'model':'qwen3:4b','source_sha256':{str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(Path('vera').glob('*.py'))},'sequences':[]}
 for mode,turns in [('isolated '+str(i),[q]) for i,q in enumerate(QUESTIONS,1)]+[('continuous',['Tell me about Oregon.']+QUESTIONS),('topic switch',['Tell me about Grandma bread.','Tell me about Oregon.']+QUESTIONS)]:
  with tempfile.TemporaryDirectory() as tmp:
   con=connect(Path(tmp)/'synthetic.sqlite3')
   for r in json.loads(Path('samples/demo_memories.json').read_text()):insert_memory(con,**r)
   session=Conversation(con);sequence={'mode':mode,'turns':[]}
   for question in turns:
    trace={'question':question,'previous_source_ids':list(session.source_ids),'prior_questions':list(session.questions),'focal_before':list(session.focal),'requests':[]}
    def traced(**kwargs):
     entry={'question':kwargs['question'],'context':kwargs['context'],'history':kwargs.get('history'), 'schema':kwargs.get('response_format')}
     trace['requests'].append(entry)
     result=live_generate(**kwargs);entry['response']=result;return result
    native_open=client.urlopen
    def traced_open(request,timeout):
     wire={'url':request.full_url,'body':json.loads(request.data),'timeout_s':timeout}
     trace.setdefault('http',[]).append(wire)
     original=native_open(request,timeout=timeout)
     class Response:
      headers=original.headers
      def __enter__(self):original.__enter__();return self
      def __exit__(self,*args):return original.__exit__(*args)
      def read(self,*args):
       raw=original.read(*args);wire['response']=json.loads(raw);return raw
     return Response()
    start=time.perf_counter()
    try:
     with patch('vera.conversation.generate',traced),patch('vera.ollama.urlopen',traced_open):trace['answer']=session.respond(question)
    except Exception as exc:trace['error']=str(exc)
    trace.update(metrics=dict(session.metrics),evidence=list(session.evidence),latency_s=time.perf_counter()-start)
    trace['retrieval_if_not_short_circuited']=[dict(r) for r in retrieve(con,question,previous_ids=trace['previous_source_ids'])]
    sequence['turns'].append(trace)
    print(mode,question,'=>',trace.get('answer',trace.get('error')),flush=True)
   con.close()
   report['sequences'].append(sequence)
   Path(args.output).write_text(json.dumps(report,indent=2))
if __name__=='__main__':main()
