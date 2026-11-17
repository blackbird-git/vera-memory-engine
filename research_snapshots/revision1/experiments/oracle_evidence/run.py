"""Controlled oracle-only capability study. Never imports Vera production modules."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import socket
import sys
import time
from .client import MODELS,api,request,unload
from .resources import Monitor,snapshot
from .prompts import DIRECT,PLANNER,RENDER,CONTROLLED,PLAN_SCHEMA

ROOT=Path('experiments/oracle_evidence')
OUT=Path('results/oracle_evidence')
STRATEGIES=('direct','generated_plan','validated_plan')
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def offline():
 def guard(event,args):
  if event=='socket.connect' and args[1][0] not in ('127.0.0.1','::1'):raise PermissionError('Oracle inference is loopback-only')
 sys.addaudithook(guard)
 try:socket.create_connection(('192.0.2.1',443),timeout=1)
 except PermissionError:pass
 else:raise RuntimeError('Offline guard failed')

def source_notes(data,turn):
 return [{'id':i,**data['records'][str(i)]} for i in turn['oracle_source_ids']]

def plan_checks(plan,notes):
 if not isinstance(plan,dict) or plan.get('status') not in ('known','unknown','uncertain'):return ['invalid_status_or_plan']
 if not isinstance(plan.get('facts'),list) or not isinstance(plan.get('caveats'),list) or not isinstance(plan.get('excluded_topics'),list):return ['invalid_plan_shape']
 sources={r['id']:r for r in notes};errors=[]
 for f in plan['facts']:
  if not isinstance(f,dict) or type(f.get('source_id')) is not int or f['source_id'] not in sources:errors.append('invalid_source_id');continue
  if not isinstance(f.get('claim'),str) or not f['claim'].strip():errors.append('empty_claim')
  quote=f.get('supporting_quote')
  if not isinstance(quote,str) or not quote.strip() or quote not in sources[f['source_id']]['content']:errors.append('invalid_quote')
 return sorted(set(errors))

def call(model,messages,schema,seed,wire,label,thinking=None):
 out=request(model,messages,schema,seed=seed,thinking=thinking)
 wire.write(json.dumps({'label':label,'wire':out.pop('wire')},ensure_ascii=False)+'\n');wire.flush()
 return out

def pilot(models,output):
 data={'models':[],'configuration':{'context':4096,'max_tokens':1024,'inference_local':True},'started_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())}
 with gzip.open(str(output)+'.wire.jsonl.gz','wt',encoding='utf8') as wire:
  for model in models:
   unload();info=api('/api/show',{'model':model});before=snapshot()
   with Monitor() as monitor:
    a=call(model,[{'role':'system','content':'Answer directly without exposing analysis.'},{'role':'user','content':'What is two plus two?'}],None,17,wire,{'pilot':model,'phase':'text'})
    b=call(model,[{'role':'system','content':'Return JSON only.'},{'role':'user','content':'Return {"answer":"four"}.'}],{'type':'object','properties':{'answer':{'type':'string'}},'required':['answer'],'additionalProperties':False},17,wire,{'pilot':model,'phase':'structured'}) if not a.get('error') else None
   item={'model':model,'metadata':info,'before':before,'text':a,'structured':b,'resources':monitor.samples,'resource_abort':monitor.abort}
   data['models'].append(item);output.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')
   print('pilot',model,'text',a.get('error'),'structured',b.get('error') if b else 'skipped','RAM GiB',round(before['MemTotal']/2**30,2),flush=True)
   if monitor.abort:raise RuntimeError(monitor.abort)
   unload()
 return data

def generate(models,output,seed,cohort_ids=None,thinking=None):
 data=json.loads((ROOT/'cases.json').read_text())
 for cohort in data['cohorts']:
  for turn in cohort['turns']:
   errors=plan_checks(turn['validated_plan'],source_notes(data,turn))
   if errors:raise ValueError('Frozen oracle plan is not mechanically source-valid: '+str(errors))
 cache_mib=None
 try:
  service_pid=int((ROOT/'runtime/server.pid').read_text())
  for value in Path(f'/proc/{service_pid}/environ').read_bytes().split(b'\0'):
   if value.startswith(b'LLAMA_ARG_CACHE_RAM='):cache_mib=int(value.split(b'=',1)[1])
 except (OSError,ValueError):pass
 report={'configuration':{'prompt_cache_mib':cache_mib,'models':models,'strategies':STRATEGIES,'seed':seed,'num_ctx':4096,'num_predict':1024,'temperature':.2,'thinking_override':thinking,'case_sha256':digest(ROOT/'cases.json'),'prompt_sha256':digest(ROOT/'prompts.py'),'client_sha256':digest(ROOT/'client.py'),'production_sha256':{str(p):digest(p) for p in Path('vera').glob('*.py')},'oracle_plan':'Source-adjudicated gold plan is supplied only to controlled-rendering arm; it is an upstream oracle advantage, not a deployable automatic verifier.','history':'Last four user questions only; no prior assistant prose is evidence.'},'model_manifests':api('/api/tags'),'rows':[],'warmups':[],'resources':[]}
 deadline=time.monotonic()+3*3600
 with gzip.open(str(output)+'.wire.jsonl.gz','wt',encoding='utf8') as wire:
  for model in models:
   unload()
   warm=call(model,[{'role':'system','content':'Answer briefly.'},{'role':'user','content':'Say ready.'}],None,seed,wire,{'model':model,'phase':'warmup'},thinking=thinking)
   report['warmups'].append({'model':model,**warm})
   if warm.get('error'):
    report.setdefault('blocked_models',[]).append({'model':model,'reason':warm['error']});output.write_text(json.dumps(report,indent=2));unload();continue
   with Monitor() as monitor:
    for strategy in STRATEGIES:
     for cohort in data['cohorts']:
      if cohort_ids and cohort['id'] not in cohort_ids:continue
      history=[]
      for index,turn in enumerate(cohort['turns']):
       if time.monotonic()>deadline:raise TimeoutError('Three-hour evaluation phase budget exhausted; partial artifact preserved')
       if monitor.abort:raise RuntimeError(monitor.abort)
       key={'model':model,'strategy':strategy,'cohort':cohort['id'],'turn':index}
       row={**key,'question':turn['question'],'oracle_source_ids':turn['oracle_source_ids'],'rubric':turn['rubric'],'history':list(history),'calls':[]}
       start=time.perf_counter();notes=source_notes(data,turn)
       payload={'USER_QUESTION_HISTORY':history,'ORACLE_SOURCE_NOTES':notes,'question':turn['question']}
       if strategy=='direct':
        reply=call(model,[{'role':'system','content':DIRECT},{'role':'user','content':json.dumps(payload,ensure_ascii=False)}],None,seed,wire,key,thinking=thinking);row['calls'].append(reply)
       elif strategy=='generated_plan':
        planned=call(model,[{'role':'system','content':PLANNER},{'role':'user','content':json.dumps(payload,ensure_ascii=False)}],PLAN_SCHEMA,seed,wire,{**key,'phase':'plan'},thinking=thinking);row['calls'].append(planned)
        try:
         if planned.get('error'):raise ValueError(planned['error'])
         plan=json.loads(planned['answer']);row['generated_plan']=plan;row['mechanical_plan_errors']=plan_checks(plan,notes)
         # Mechanical quote checks are diagnostic, not semantic proof. This arm
         # tests the model-generated plan without silently replacing it with gold.
         payload['model_generated_plan']=plan
         reply=call(model,[{'role':'system','content':RENDER},{'role':'user','content':json.dumps(payload,ensure_ascii=False)}],None,seed,wire,{**key,'phase':'render'},thinking=thinking);row['calls'].append(reply)
        except Exception as exc:reply={'answer':'','error':'plan_failure: '+str(exc)}
       else:
        controlled_payload={'USER_QUESTION_HISTORY':history,'question':turn['question'],'source_validated_oracle_plan':turn['validated_plan']}
        reply=call(model,[{'role':'system','content':CONTROLLED},{'role':'user','content':json.dumps(controlled_payload,ensure_ascii=False)}],None,seed,wire,key,thinking=thinking);row['calls'].append(reply)
       row.update(answer=reply['answer'],error=reply.get('error'),latency_s=time.perf_counter()-start)
       history=(history+[turn['question']])[-4:]
       report['rows'].append(row);output.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
       print(model,strategy,cohort['id'],index+1,round(row['latency_s'],2),row['error'],flush=True)
   report['resources'].append({'model':model,'samples':monitor.samples,'abort':monitor.abort});output.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
   unload()
 return report

def main():
 p=argparse.ArgumentParser();p.add_argument('phase',choices=('pilot','generate'));p.add_argument('--models',nargs='+',choices=MODELS,default=[m for m in MODELS if not m.endswith('-text-oracle')]);p.add_argument('--output',type=Path,required=True);p.add_argument('--seed',type=int,default=17);p.add_argument('--cohorts',nargs='*');p.add_argument('--thinking',choices=('true','false','low','medium'));args=p.parse_args()
 if args.output.exists() or Path(str(args.output)+'.wire.jsonl.gz').exists():p.error('Refusing to overwrite an existing experiment artifact; use a fresh output path')
 offline();args.output.parent.mkdir(parents=True,exist_ok=True)
 thinking={'true':True,'false':False}.get(args.thinking,args.thinking)
 if args.phase=='pilot':pilot(args.models,args.output)
 else:generate(args.models,args.output,args.seed,args.cohorts,thinking)
if __name__=='__main__':main()
