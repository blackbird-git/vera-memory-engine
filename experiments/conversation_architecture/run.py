"""New isolated architecture study; evaluation answers never enter model prompts."""
import argparse
from contextlib import closing
import gzip
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import time
from unittest.mock import patch
from experiments.oracle_evidence.client import api,request,unload
from experiments.oracle_evidence.resources import Monitor
from experiments.oracle_evidence.run import offline
from vera.db import connect,insert_memory
from vera.conversation import Conversation
from vera.ollama import SYSTEM
from . import engine

ROOT=Path('experiments/conversation_architecture')
MODEL='gpt-oss:20b'
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('phase',choices=['generate']);p.add_argument('--cases',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--boundary',action='store_true');args=p.parse_args()
    if args.output.exists() or Path(str(args.output)+'.wire.jsonl.gz').exists():p.error('Use a fresh result path')
    offline();args.output.parent.mkdir(parents=True,exist_ok=True)
    cases=json.loads(args.cases.read_text());unload()
    report={'configuration':{'model':MODEL,'engine_revision':engine.REVISION,'seed':17,'case_sha256':digest(args.cases),'engine_sha256':digest(ROOT/'engine.py'),'runner_sha256':digest(__file__),'candidate_evidence':'Fixed cohort-level candidate_source_ids; per-turn oracle/rubric/reference_plan NEVER supplied to inference.','production_sha256':{str(f):digest(f) for f in Path('vera').glob('*.py')},'compiled_guarantee':'Original punctuation-delimited segments with attribution. Semantic selection, qualifiers, exclusions and antecedents remain fallible.','natural_draft':'Research only; never accepted as a released or validated response.','actual_environment':'Recorded by resource samples; no old timing cells rerun.'},'model_manifests':api('/api/tags'),'rows':[]}
    deadline=time.monotonic()+3600
    def save():args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    with gzip.open(str(args.output)+'.wire.jsonl.gz','wt',encoding='utf8') as wire:
        def call(messages,response_schema,label):
            if time.monotonic()>deadline:raise TimeoutError('One-hour architecture phase budget')
            result=request(MODEL,messages,response_schema,seed=17)
            wire.write(json.dumps({'label':label,'wire':result.pop('wire')},ensure_ascii=False)+'\n');wire.flush()
            return result
        with Monitor() as monitor:
            report['warmup']=call([{'role':'user','content':'Say ready.'}],None,{'phase':'warmup'});save()
            if report['warmup']['error']:raise RuntimeError(report['warmup']['error'])
            if args.boundary:
                report['configuration']['evaluation_type']='Independent boundary/context challenge; supplied source collection, source-plan arm only.'
                for case in cases['cases']:
                    if monitor.abort:raise RuntimeError(monitor.abort)
                    session=engine.Session({str(i):cases['records'][str(i)] for i in case['source_ids']})
                    session.history=list(case['history'])[-4:];key={'cohort':case['id'],'turn':0,'strategy':'source_plan'}
                    start=time.perf_counter();planned=call(session.plan_messages(case['question']),engine.schema(session.units),key)
                    plan=None;chosen=[]
                    try:
                        if planned['error']:raise ValueError(planned['error'])
                        plan=json.loads(planned['answer']);chosen=engine.validate(plan,session.units);answer=engine.compose(plan,session.units);error=None
                    except Exception as exc:answer="I couldn't verify an answer from these notes.";error=str(exc)
                    elapsed=time.perf_counter()-start
                    report['rows'].append({**key,'question':case['question'],'answer':answer,'error':error,'plan':plan,'selected_units':chosen,'calls':[planned],'latency_s':elapsed,'inference_s':planned['stats'].get('wall_s',0),'deterministic_s':max(0,elapsed-planned['stats'].get('wall_s',0))});save()
                    print(case['id'],'complete',error,flush=True)
            for cohort in ([] if args.boundary else cases['cohorts']):
                candidates={str(i):cases['records'][str(i)] for i in cohort['candidate_source_ids']}
                with tempfile.TemporaryDirectory() as tmp,closing(connect(Path(tmp)/'synthetic.sqlite3')) as con:
                    mapping={}
                    for source_id,r in candidates.items():mapping[insert_memory(con,**r)]=source_id
                    baseline=Conversation(con,model=MODEL);session=engine.Session(candidates)
                    for index,turn in enumerate(cohort['turns']):
                        if monitor.abort:raise RuntimeError(monitor.abort)
                        question=turn['question'];key={'cohort':cohort['id'],'turn':index};before=con.total_changes;calls=[];start=time.perf_counter()
                        def adapter(**kw):
                            messages=[{'role':'system','content':SYSTEM},{'role':'user','content':json.dumps({'question':kw['question'],'SOURCE_NOTES':kw['context'],'USER_QUESTION_HISTORY':[m['content'] for m in kw.get('history',[]) if m['role']=='user']},ensure_ascii=False)}]
                            out=call(messages,kw.get('response_format'),{**key,'strategy':'current_engine'});calls.append(out)
                            if out['error']:raise RuntimeError(out['error'])
                            return out['answer']
                        try:
                            with patch('vera.conversation.generate',adapter):answer=baseline.respond(question)
                            error=None
                        except Exception as exc:answer='';error=str(exc)
                        assert con.total_changes==before,'Unexpected archive write'
                        evidence=[{**r,'source_id':mapping.get(r['source_id'],str(r['source_id']))} for r in baseline.evidence]
                        report['rows'].append({**key,'strategy':'current_engine','question':question,'answer':answer,'error':error,'calls':calls,'evidence':evidence,'engine_metrics':dict(baseline.metrics),'latency_s':time.perf_counter()-start,'inference_s':sum(c['stats'].get('wall_s',0) for c in calls),'database_changes':con.total_changes-before});save()
                        start=time.perf_counter();planned=call(session.plan_messages(question),engine.schema(session.units),{**key,'strategy':'source_plan','phase':'plan'})
                        plan=None;chosen=[]
                        try:
                            if planned['error']:raise ValueError(planned['error'])
                            plan=json.loads(planned['answer']);chosen=engine.validate(plan,session.units);answer=engine.compose(plan,session.units);error=None
                        except Exception as exc:answer="I couldn't verify an answer from these notes.";error=str(exc)
                        elapsed=time.perf_counter()-start
                        report['rows'].append({**key,'strategy':'source_plan','question':question,'answer':answer,'error':error,'plan':plan,'selected_units':chosen,'calls':[planned],'latency_s':elapsed,'inference_s':planned['stats'].get('wall_s',0),'deterministic_s':max(0,elapsed-planned['stats'].get('wall_s',0))});save()
                        if not error:
                            start=time.perf_counter();draft=call(session.draft_messages(question,plan),None,{**key,'strategy':'natural_draft','phase':'render'})
                            report['rows'].append({**key,'strategy':'natural_draft','question':question,'answer':draft['answer'],'error':draft['error'],'plan':plan,'selected_units':chosen,'calls':[draft],'latency_s':elapsed+time.perf_counter()-start,'inference_s':planned['stats'].get('wall_s',0)+draft['stats'].get('wall_s',0),'released':False});save()
                            session.advance(question,plan)
                        else:session.history=(session.history+[question])[-4:]
                        print(cohort['id'],index+1,'complete',error,flush=True)
            report['resources']={'samples':monitor.samples,'abort':monitor.abort};save()
    unload()
if __name__=='__main__':main()
