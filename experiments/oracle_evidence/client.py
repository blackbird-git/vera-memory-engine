"""Native, loopback-only inference for the oracle capability experiment."""
import json
import time
from urllib.request import Request,build_opener,ProxyHandler,HTTPRedirectHandler

ENDPOINT='http://127.0.0.1:11435'
MODELS=('qwen3:4b','qwen3.5:4b','ministral-3:3b-instruct-2512-q4_K_M','gpt-oss:20b','qwen3.5:27b','qwen3.5:27b-text-oracle')
class NoRedirect(HTTPRedirectHandler):
 def redirect_request(self,*args,**kwargs):raise RuntimeError('Redirects are forbidden')
OPENER=build_opener(ProxyHandler({}),NoRedirect())
def api(path,body=None,timeout=15):
 if not path.startswith('/api/'):raise ValueError('Loopback API paths only')
 req=Request(ENDPOINT+path,data=json.dumps(body).encode() if body is not None else None,headers={'Content-Type':'application/json'})
 with OPENER.open(req,timeout=timeout) as r:raw=r.read(4_000_001)
 if len(raw)>4_000_000:raise RuntimeError('Response-size budget exceeded')
 data=json.loads(raw)
 if not isinstance(data,dict) or data.get('error'):raise RuntimeError(str(data.get('error','Bad response')))
 return data

def request(model,messages,schema=None,seed=17,thinking=None,max_tokens=1024):
 if model not in MODELS:raise ValueError('Model is not in frozen candidate set')
 if sum(len(m['content']) for m in messages)>14000:raise ValueError('Prompt exceeds oracle experiment input budget')
 body={'model':model,'messages':messages,'stream':False,'keep_alive':'2m',
       'options':{'num_ctx':4096,'num_predict':max_tokens,'temperature':.2,'seed':seed,'top_p':.95,'top_k':20,'repeat_penalty':1.0,'presence_penalty':0.0}}
 path='/api/chat'
 if model=='qwen3:4b':
  def escape(s):return s.replace('<|','< |').replace('|>','| >')
  body.pop('messages');body['raw']=True;body['think']=False
  body['prompt']=''.join('<|im_start|>'+m['role']+'\n'+escape(m['content'])+'<|im_end|>\n' for m in messages)+'<|im_start|>assistant\n<think>\n\n</think>\n\n';path='/api/generate'
 elif model.startswith('gpt-oss:'):body['think']=thinking or 'low'
 elif model.startswith('qwen3.5:'):body['think']=False if thinking is None else thinking
 if schema is not None:body['format']=schema
 start=time.perf_counter()
 try:
  data=api(path,body,timeout=300)
  message=data.get('message',{});answer=data.get('response',message.get('content',''))
  if not isinstance(answer,str):raise ValueError('Answer is not text')
  if data.get('done') is not True:raise ValueError('Incomplete server response')
  stats={k:data.get(k) for k in ('done_reason','eval_count','prompt_eval_count','prompt_eval_cached_count')}
  for k in ('total_duration','load_duration','prompt_eval_duration','eval_duration'):stats[k.replace('_duration','_s')]=data.get(k,0)/1e9
  stats['wall_s']=time.perf_counter()-start
  stats['thinking_chars']=len(message.get('thinking',data.get('thinking','')))
  # Some legacy Qwen outputs repeat a closing thinking marker even with the
  # closed-thinking prefix. Preserve only the explicitly delimited final part.
  stats['stripped_inline_reasoning_chars']=0
  if '</think>' in answer:
   raw_length=len(answer);answer=answer.rsplit('</think>',1)[-1].strip()
   stats['stripped_inline_reasoning_chars']=raw_length-len(answer)
  error='output_limit' if data.get('done_reason')=='length' else None
  if not answer.strip() and not error:error='empty_answer'
  if any(s in answer.lower() for s in ('<think>','</think>','<analysis>','analysis:')):error='reasoning_in_answer'
  return {'answer':answer,'stats':stats,'error':error,'wire':{'path':path,'request':body,'response':data}}
 except Exception as exc:
  return {'answer':'','stats':{'wall_s':time.perf_counter()-start},'error':str(exc),'wire':{'path':path,'request':body}}

def unload():
 for loaded in api('/api/ps').get('models',[]):api('/api/generate',{'model':loaded['name'],'keep_alive':0})
 if api('/api/ps').get('models'):raise RuntimeError('Experimental model did not unload')
