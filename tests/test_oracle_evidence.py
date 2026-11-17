"""Oracle experiment boundaries; tests never load models or open real archives."""
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from experiments.oracle_evidence import client,run,prompts

class OracleBoundaryTests(unittest.TestCase):
 def test_existing_result_is_not_overwritten_or_inference_started(self):
  with tempfile.TemporaryDirectory() as tmp:
   output=Path(tmp)/'preserved.json';output.write_text('Preserved result')
   with patch('sys.argv',['oracle','generate','--output',str(output)]),patch('sys.stderr',io.StringIO()),patch.object(run,'offline') as offline:
    with self.assertRaises(SystemExit) as error:run.main()
    self.assertEqual(error.exception.code,2);offline.assert_not_called()
   self.assertEqual(output.read_text(),'Preserved result')
 def test_model_allowlist_prevents_remote_candidate(self):
  with patch.object(client,'api') as api:
   with self.assertRaises(ValueError):client.request('remote:cloud',[])
   api.assert_not_called()
 def test_nonlocal_url_is_rejected_before_network(self):
  with self.assertRaises(ValueError):client.api('https://example.com/data')
 def response(self):return {'done':True,'done_reason':'stop','message':{'content':'Four.','thinking':'Synthetic hidden reasoning'},'eval_count':9}
 def test_gpt_uses_native_chat_and_named_reasoning(self):
  with patch.object(client,'api',return_value=self.response()) as api:
   result=client.request('gpt-oss:20b',[{'role':'user','content':'2+2?'}])
  self.assertEqual(api.call_args.args[0],'/api/chat');self.assertEqual(api.call_args.args[1]['think'],'low')
  self.assertNotIn('raw',api.call_args.args[1]);self.assertEqual(result['answer'],'Four.')
  self.assertGreater(result['stats']['thinking_chars'],0)
 def test_legacy_complete_thinking_is_removed_from_final_answer(self):
  r=self.response();r['message']['content']='Synthetic analysis</think>\nReady.'
  with patch.object(client,'api',return_value=r):out=client.request('qwen3:4b',[])
  self.assertEqual(out['answer'],'Ready.');self.assertIsNone(out['error'])
  self.assertGreater(out['stats']['stripped_inline_reasoning_chars'],0)
 def test_qwen35_uses_native_thinking_off(self):
  with patch.object(client,'api',return_value=self.response()) as api:client.request('qwen3.5:27b',[])
  self.assertIs(api.call_args.args[1]['think'],False)
 def test_truncation_is_preserved_as_failure(self):
  r=self.response();r['done_reason']='length'
  with patch.object(client,'api',return_value=r):out=client.request('gpt-oss:20b',[])
  self.assertEqual(out['error'],'output_limit')
 def test_reasoning_in_answer_is_not_accepted(self):
  r=self.response();r['message']['content']='Analysis: private reasoning'
  with patch.object(client,'api',return_value=r):out=client.request('gpt-oss:20b',[])
  self.assertEqual(out['error'],'reasoning_in_answer')
 def test_literal_quote_check_does_not_claim_semantic_verification(self):
  notes=[{'id':1,'content':'I think it was 2010.'}]
  plan={'status':'known','facts':[{'source_id':1,'claim':'It was certainly 2010.','supporting_quote':'I think it was 2010.'}],'caveats':[],'excluded_topics':[]}
  self.assertEqual(run.plan_checks(plan,notes),[])
  plan['facts'][0]['source_id']=999;self.assertIn('invalid_source_id',run.plan_checks(plan,notes))
 def test_exact_manual_set_and_oracle_quotes_are_source_valid(self):
  data=json.loads((run.ROOT/'cases.json').read_text())
  manual=json.loads(Path('experiments/model_comparison/manual-confirmed-cases.json').read_text())[0]
  self.assertEqual([t['question'] for t in data['cohorts'][0]['turns']],[t['question'] for t in manual['turns']])
  for cohort in data['cohorts']:
   for turn in cohort['turns']:self.assertEqual(run.plan_checks(turn['validated_plan'],run.source_notes(data,turn)),[])
 def test_gold_plan_only_enters_controlled_condition(self):
  captures=[]
  class DummyMonitor:
   def __enter__(self):self.abort=None;self.samples=[];return self
   def __exit__(self,*args):pass
  def fake_call(model,messages,schema,seed,wire,label,thinking=None):
   captures.append((messages,schema,label))
   answer=json.dumps({'status':'unknown','facts':[],'caveats':[],'excluded_topics':[]}) if schema else 'Synthetic answer.'
   return {'answer':answer,'error':None,'stats':{'wall_s':0}}
  with tempfile.TemporaryDirectory() as tmp,patch.object(run,'Monitor',DummyMonitor),patch.object(run,'unload'),patch.object(run,'api',return_value={'models':[]}),patch.object(run,'call',side_effect=fake_call),patch('builtins.print'):
   report=run.generate(['qwen3:4b'],Path(tmp)/'output.json',17)
  self.assertEqual(len(report['rows']),48)
  for messages,schema,label in captures:
   if label.get('phase')=='warmup':continue
   payload=json.loads(messages[-1]['content'])
   self.assertEqual('source_validated_oracle_plan' in payload,label['strategy']=='validated_plan')
   self.assertFalse(any('Synthetic answer.' in h for h in payload['USER_QUESTION_HISTORY']))

class SummaryIntegrityTests(unittest.TestCase):
 def aggregate(self,answer_hash):
  from experiments.oracle_evidence import summarize
  row={'model':'synthetic','strategy':'direct','cohort':'fixture','turn':0,'answer':'A changed answer.','error':None,'latency_s':1,'calls':[]}
  review={**{k:row[k] for k in ('model','strategy','cohort','turn')},'answer_sha256':answer_hash,'grounding':'unsupported','scores':{'completeness':5}}
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);source=root/'input.json';audits=root/'reviews.json';out=root/'summary.json'
   source.write_text(json.dumps({'rows':[row]}));audits.write_text(json.dumps({'rows':[review],'dimensions':['completeness'],'method':'Synthetic test review'}))
   with patch('sys.argv',['summary','--inputs',str(source),'--reviews',str(audits),'--output',str(out)]),patch('builtins.print'):summarize.main()
   return json.loads(out.read_text())
 def test_changed_answer_cannot_inherit_old_source_review(self):
  with self.assertRaisesRegex(ValueError,'does not match'):self.aggregate('stale-answer-hash')
 def test_partial_high_completeness_does_not_become_complete_quality_pass(self):
  import hashlib
  result=self.aggregate(hashlib.sha256(b'A changed answer.').hexdigest())
  cell=result['cells'][0]
  self.assertFalse(cell['complete_for_quality']);self.assertEqual(cell['generation_errors'],0)
  self.assertEqual(cell['grounding_counts'],{'unsupported':1});self.assertEqual(cell['quality_means']['completeness'],5)

class HostGuardTests(unittest.TestCase):
 def test_transient_host_monitor_failure_does_not_silently_disable_guard(self):
  import subprocess
  import signal
  from experiments.oracle_evidence import host_guard as h
  def fake_bytes(path):
   if path.name=='cmdline':return b'/usr/local/bin/ollama\0serve\0'
   if path.name=='environ':return b'OLLAMA_HOST=127.0.0.1:11435\0'
   raise AssertionError(str(path))
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);(root/'server.pid').write_text('999')
   with patch.object(h,'ROOT',root),patch.object(h,'OUT',root/'host.json'),patch.object(h,'workers',return_value=[123]),patch.object(h.subprocess,'check_output',side_effect=subprocess.CalledProcessError(1,['powershell'])),patch.object(h.time,'sleep'),patch.object(h.os,'kill') as kill,patch.object(Path,'read_bytes',fake_bytes):
    with self.assertRaisesRegex(RuntimeError,'failed three consecutive'):h.main()
    kill.assert_called_once_with(999,signal.SIGTERM)
   data=json.loads((root/'host.json').read_text());self.assertTrue(data['aborted'])
   self.assertEqual(sum('monitor_error' in row for row in data['samples']),3)
 def test_single_low_host_sample_does_not_kill_model(self):
  from experiments.oracle_evidence import host_guard as h
  low=json.dumps({'FreePhysicalKiB':1000,'FreeVirtualKiB':1024*1024})
  safe=json.dumps({'FreePhysicalKiB':1024*1024,'FreeVirtualKiB':4*1024*1024})
  with tempfile.TemporaryDirectory() as tmp,patch.object(h,'OUT',Path(tmp)/'host.json'),patch.object(h,'workers',side_effect=[[123],[123],[]]),patch.object(h.subprocess,'check_output',side_effect=[low,safe]),patch.object(h.time,'sleep'),patch.object(h.os,'kill') as kill,patch('builtins.print'):
   h.main();kill.assert_not_called()
 def test_restart_preflight_refuses_to_label_old_limits_as_prepared(self):
  from experiments.oracle_evidence import preflight
  old={'MemTotal':15*2**30,'MemAvailable':10*2**30,'SwapTotal':4*2**30,'SwapFree':2*2**30,'windows_c_free_bytes':60*2**30}
  with patch.object(preflight,'snapshot',return_value=old),patch('sys.argv',['preflight','--require-prepared-limits']),patch('builtins.print'):
   with self.assertRaisesRegex(SystemExit,'not active'):preflight.main()
