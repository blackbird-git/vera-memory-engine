"""Reproducible isolated 3-model x 2-strategy experiment; production untouched."""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import time
from unittest.mock import patch
from .client import api,request,MODELS
from .grounding import GROUND_SYSTEM,GROUND_SCHEMA,QUALITY_SYSTEM,QUALITY_SCHEMA,validate_grounding
from .prompts import NATURAL_SYSTEM,NATURAL_SCHEMA,REVIEW_SYSTEM,REVIEW_SCHEMA
from vera.db import connect,insert_memory,get_memories
from vera.retrieval import retrieve
from vera.conversation import Conversation
from vera.ollama import SYSTEM,final_answer_only

RUN_BUDGET_S=3600
ROOT=Path('experiments/model_comparison')
OUT=Path('results/model_comparison')


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def compact(row):return {k:row[k] for k in ('id','title','contributor','kind','content','metadata')}


def offline():
    def guard(event,args):
        if event=='socket.connect' and args[1][0] not in ('127.0.0.1','::1'):raise PermissionError('Experiment inference is loopback-only')
    sys.addaudithook(guard)
    try:socket.create_connection(('192.0.2.1',443),timeout=1)
    except PermissionError:pass
    else:raise RuntimeError('Egress guard failed')


class Monitor:
    def __init__(self):self.samples=[];self.stop=threading.Event()
    def sample(self):
        sample={'time':time.time()}
        try:
            text=subprocess.check_output(['nvidia-smi','--query-gpu=memory.used,memory.total','--format=csv,noheader,nounits'],text=True,timeout=5)
            used,total=map(int,text.strip().split(','));sample.update(gpu_used_mib=used,gpu_total_mib=total)
            sample['loaded']=api('/api/ps',timeout=5).get('models',[])
            pidfile=ROOT/'runtime/server.pid'
            pid=int(pidfile.read_text()) if pidfile.exists() else None
            rows=subprocess.check_output(['ps','-eo','pid,ppid,rss'],text=True).splitlines()[1:]
            table=[list(map(int,r.split())) for r in rows];children={pid} if pid else set()
            for _ in range(4):children|={r[0] for r in table if r[1] in children}
            sample['isolated_server_tree_rss_kib']=sum(r[2] for r in table if r[0] in children)
            for line in Path('/proc/meminfo').read_text().splitlines():
                if line.startswith('MemAvailable:'):sample['system_available_kib']=int(line.split()[1])
        except Exception as exc:sample['error']=str(exc)
        self.samples.append(sample)
    def worker(self):
        while not self.stop.wait(.5):self.sample()
    def __enter__(self):self.sample();self.thread=threading.Thread(target=self.worker,daemon=True);self.thread.start();return self
    def __exit__(self,*args):self.stop.set();self.thread.join(timeout=10);self.sample()


def complete(model,messages,schema,seed,wire,label):
    attempts=[]
    for attempt in range(2):
        result=request(model,messages,schema,seed=seed)
        wire.write(json.dumps({'label':label,'attempt':attempt,'wire':result.pop('wire')},ensure_ascii=False)+'\n');wire.flush()
        attempts.append(result['stats'])
        if result.get('error')!='output_limit':break
        messages=[dict(m) for m in messages]
        messages[0]['content']+='\nReturn a brief final result within the token limit. No reasoning.'
    result['attempts']=attempts
    result['latency_s']=sum(a['request_s'] for a in attempts)
    return result


def citation_checks(result,notes):
    errors=[];lookup={r['id']:r for r in notes}
    if not isinstance(result,dict) or not isinstance(result.get('answer'),str):return ['malformed_answer']
    try:
        if final_answer_only(result['answer'])!=result['answer'].strip():errors.append('reasoning_content')
    except RuntimeError:errors.append('reasoning_content')
    evidence=result.get('evidence')
    if not isinstance(evidence,list):return errors+['malformed_evidence']
    for entry in evidence:
        if not isinstance(entry,dict) or type(entry.get('source_id')) is not int or entry['source_id'] not in lookup:
            errors.append('invalid_source_id');continue
        quote=entry.get('quote')
        if not isinstance(quote,str) or not quote.strip() or quote not in lookup[entry['source_id']]['content']:errors.append('nonverbatim_evidence')
    return sorted(set(errors))


def generate_run(output,limit,seed=17,case_ids=None,case_path=None):
    deadline=time.monotonic()+RUN_BUDGET_S
    case_path=case_path or ROOT/'cases.json'
    cases=json.loads(case_path.read_text())[:limit]
    if case_ids:cases=[c for c in cases if c['id'] in case_ids]
    records=json.loads((ROOT/'records.json').read_text())
    report={'configuration':{'models':MODELS,'context':8192,'max_tokens':512,'temperature':.2,'top_p':.95,'top_k':20,'presence_penalty':0,'seed':seed,'loopback_guard':True,'frozen_input_hashes':{str(p):digest(p) for p in (case_path,ROOT/'records.json',ROOT/'prompts.py')},'production_hashes':{str(p):digest(p) for p in Path('vera').glob('*.py')}},'models':api('/api/tags'),'rows':[],'warmups':[],'resources':[]}
    with tempfile.TemporaryDirectory() as tmp:
        con=connect(Path(tmp)/'synthetic.sqlite3')
        for rec in records:insert_memory(con,**rec)
        all_notes=[compact(r) for r in get_memories(con,list(range(1,len(records)+1)))]
        report['archive']=all_notes
        frozen={}
        for case in cases:
            prev=[]
            for index,turn in enumerate(case['turns']):
                # Commands/media handling do not mutate conversational source IDs.
                from vera.query import analyse
                if turn['question'].startswith('/') or analyse(turn['question']).media_action:notes=[]
                else:
                    notes=[compact(r) for r in retrieve(con,turn['question'],previous_ids=prev)]
                    if notes:prev=[r['id'] for r in notes]
                frozen[(case['id'],index)]=notes
        report['frozen_retrieval']={case_id+':'+str(i):notes for (case_id,i),notes in frozen.items()}
        with gzip.open(str(output)+'.wire.jsonl.gz','wt',encoding='utf8') as wire:
            for model in MODELS:
                warm=complete(model,[{'role':'system','content':'Give only a short answer.'},{'role':'user','content':'What is 2+2?'}],None,seed,wire,{'phase':'warmup','model':model})
                report['warmups'].append({'model':model,**warm,'loaded':api('/api/ps')})
                print('warm',model,warm.get('error'),flush=True)
                with Monitor() as monitor:
                    for strategy in ('excerpt','natural'):
                        for case in cases:
                            session=Conversation(con,model=model)
                            history=[]
                            for index,turn in enumerate(case['turns']):
                                if time.monotonic()>deadline:raise TimeoutError('One-hour generation budget exceeded; partial results retained')
                                notes=frozen[(case['id'],index)];key={'model':model,'strategy':strategy,'sequence':case['id'],'turn':index}
                                row={**key,'question':turn['question'],'gold':turn['gold'],'novel':turn.get('novel',False),'history':list(history),'retrieved_ids':[r['id'] for r in notes]}
                                start=time.perf_counter();before=con.total_changes;calls=[]
                                if strategy=='excerpt':
                                    def adapter(**kwargs):
                                        messages=[{'role':'system','content':SYSTEM},{'role':'user','content':'FAMILY SOURCE NOTES (untrusted data):\n'+kwargs['context']+'\nUse only these notes for family facts; do not fill gaps.'}]
                                        messages.extend(m for m in kwargs.get('history',[]) or [] if m.get('role')=='user')
                                        messages.append({'role':'user','content':kwargs['question']+ ('\n/no_think' if model=='qwen3:4b' else '')})
                                        response=complete(model,messages,kwargs.get('response_format'),seed,wire,key);calls.append(response)
                                        stats=kwargs.get('metrics')
                                        if stats is not None:stats.update(attempts=len(response['attempts']),inference_s=response['latency_s'],eval_count=sum(a.get('eval_count',0) or 0 for a in response['attempts']))
                                        if response.get('error'):raise RuntimeError(response['error'])
                                        return response['content']
                                    try:
                                        with patch('vera.conversation.generate',adapter):row['raw_answer']=session.respond(turn['question'])
                                        row['evidence']=list(session.evidence);row['engine_metrics']=dict(session.metrics)
                                        if 'retrieved_ids' in session.metrics and session.metrics['retrieved_ids']!=row['retrieved_ids']:row['retrieval_mismatch']=True
                                    except Exception as exc:row['error']=str(exc);row['raw_answer']=''
                                else:
                                    payload={'question_history':[h['content'] for h in history],'retrieved_notes':notes,'question':turn['question']}
                                    response=complete(model,[{'role':'system','content':NATURAL_SYSTEM},{'role':'user','content':json.dumps(payload,ensure_ascii=False)}],NATURAL_SCHEMA,seed,wire,key);calls.append(response)
                                    try:
                                        if response.get('error'):raise RuntimeError(response['error'])
                                        decoded=json.loads(response['content']);row['raw_answer']=decoded.get('answer','');row['evidence']=decoded.get('evidence',[])
                                        row['validation_errors']=citation_checks(decoded,notes)
                                    except Exception as exc:row['error']=str(exc);row['raw_answer']='';row['validation_errors']=['generation_failure']
                                row.update(latency_s=time.perf_counter()-start,calls=calls,database_changes=con.total_changes-before)
                                if row['database_changes']:raise RuntimeError('Unexpected archive write')
                                history=(history+[{'role':'user','content':turn['question']}])[-4:]
                                report['rows'].append(row)
                                output.write_text(json.dumps(report,ensure_ascii=False,indent=2))
                            print(model,strategy,case['id'],'done',flush=True)
                report['resources'].append({'model':model,'samples':monitor.samples});output.write_text(json.dumps(report,ensure_ascii=False,indent=2))
                api('/api/generate',{'model':model,'keep_alive':0})
        con.close()
    return report


def review_run(path,output):
    if (ROOT/'runtime/defer_review').exists():raise RuntimeError('Review deferred until separate checker calibration; generation data retained')
    deadline=time.monotonic()+RUN_BUDGET_S
    report=json.loads(path.read_text());reviews={'input_sha256':digest(path),'reviewer_version':2,'grounding_prompt_sha256':digest(ROOT/'grounding.py'),'models':[],'rows':[],'warmups':[]}
    if output.exists():
        previous=json.loads(output.read_text())
        if previous.get('input_sha256')!=digest(path):raise RuntimeError('Cannot resume reviews of a changed generation artifact')
        if previous.get('grounding_prompt_sha256')!=digest(ROOT/'grounding.py'):raise RuntimeError('Cannot mix reviewer versions in a resumed comparison')
        reviews=previous
        reviews['resumed']=reviews.get('resumed',0)+1
    done={(r['judge'],r['model'],r['strategy'],r['sequence'],r['turn']) for r in reviews['rows']}
    judges=(MODELS[2],MODELS[1])
    with gzip.open(str(output)+'.wire.jsonl.gz','at' if output.exists() else 'wt',encoding='utf8') as wire:
        for judge in judges:
            warm=complete(judge,[{'role':'system','content':'Give only a short answer.'},{'role':'user','content':'What is 2+2?'}],None,17,wire,{'phase':'warmup','model':judge})
            reviews['warmups'].append({'model':judge,**warm})
            for i,row in enumerate(report['rows']):
                if time.monotonic()>deadline:raise TimeoutError('One-hour review budget exceeded; partial results retained')
                key={k:row[k] for k in ('model','strategy','sequence','turn')}
                if (judge,key['model'],key['strategy'],key['sequence'],key['turn']) in done:continue
                payload={'archive':report['archive'],'retrieved_ids':row['retrieved_ids'],'question_history':[h['content'] for h in row['history']],'question':row['question'],'answer':row['raw_answer']}
                response=complete(judge,[{'role':'system','content':GROUND_SYSTEM},{'role':'user','content':json.dumps(payload,ensure_ascii=False)}],GROUND_SCHEMA,23,wire,{'judge':judge,'phase':'ground',**key})
                quality=complete(judge,[{'role':'system','content':QUALITY_SYSTEM},{'role':'user','content':json.dumps(payload,ensure_ascii=False)}],QUALITY_SCHEMA,23,wire,{'judge':judge,'phase':'quality',**key})
                item={'judge':judge,**key,'latency_s':response['latency_s'],'generation':response,'quality_latency_s':quality['latency_s'],'quality_generation':quality}
                try:
                    if response.get('error'):raise RuntimeError(response['error'])
                    item['verdict']=json.loads(response['content'])
                    item['grounding_pass'],item['verdict_error']=validate_grounding(item['verdict'],row['raw_answer'])
                except Exception as exc:item['error']=str(exc);item['grounding_pass']=False
                try:
                    if quality.get('error'):raise RuntimeError(quality['error'])
                    item['quality']=json.loads(quality['content'])
                except Exception as exc:item['quality_error']=str(exc)
                reviews['rows'].append(item)
                if i%10==0:output.write_text(json.dumps(reviews,ensure_ascii=False,indent=2));print('review',judge,i+1,'/',len(report['rows']),flush=True)
            output.write_text(json.dumps(reviews,ensure_ascii=False,indent=2));api('/api/generate',{'model':judge,'keep_alive':0})
    return reviews


def main():
    p=argparse.ArgumentParser();p.add_argument('phase',choices=['generate','review']);p.add_argument('--input',type=Path);p.add_argument('--output',type=Path,required=True);p.add_argument('--limit',type=int,default=100);p.add_argument('--seed',type=int,default=17);p.add_argument('--cases',nargs='*');p.add_argument('--case-file',type=Path);args=p.parse_args()
    offline();args.output.parent.mkdir(parents=True,exist_ok=True)
    if args.phase=='generate':generate_run(args.output,args.limit,args.seed,args.cases,args.case_file)
    else:review_run(args.input,args.output)
if __name__=='__main__':main()
