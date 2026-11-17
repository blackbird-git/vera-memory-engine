"""Isolated, loopback-only native-template client. Does not modify Vera's client."""
import json
import time
from urllib.request import Request, build_opener, ProxyHandler
from vera.ollama import NoRedirect, final_answer_only

ENDPOINT='http://127.0.0.1:11435'
MODELS=('qwen3:4b','qwen3.5:4b','ministral-3:3b-instruct-2512-q4_K_M')
OPENER=build_opener(ProxyHandler({}),NoRedirect())


def api(path, body=None, timeout=90):
    if not path.startswith('/api/'):raise ValueError('Only local Ollama API paths are permitted')
    request=Request(ENDPOINT+path,data=json.dumps(body).encode() if body is not None else None,headers={'Content-Type':'application/json'})
    with OPENER.open(request,timeout=timeout) as response:
        raw=response.read(2_000_001)
    if len(raw)>2_000_000:raise RuntimeError('Response exceeds experiment budget')
    result=json.loads(raw)
    if not isinstance(result,dict) or result.get('error'):raise RuntimeError(str(result.get('error','Invalid response')))
    return result


def request(model, messages, schema=None, seed=17, max_tokens=512):
    if model not in MODELS:raise ValueError('Candidate not in frozen model list')
    body={'model':model,'messages':messages,'stream':False,'keep_alive':'2m',
          'options':{'num_ctx':8192,'num_predict':max_tokens,'temperature':.2,'seed':seed,'top_p':.95,'top_k':20,'repeat_penalty':1.0,'presence_penalty':0.0}}
    path='/api/chat'
    if model=='qwen3:4b':
        def escape(text):return text.replace('<|','< |').replace('|>','| >')
        body.pop('messages');body['raw']=True;body['think']=False
        body['prompt']=''.join('<|im_start|>'+m['role']+'\n'+escape(m['content'])+'<|im_end|>\n' for m in messages)+'<|im_start|>assistant\n<think>\n\n</think>\n\n'
        path='/api/generate'
    elif model=='qwen3.5:4b':body['think']=False
    if schema is not None:body['format']=schema
    started=time.perf_counter()
    try:
        result=api(path,body)
        content=result.get('response',result.get('message',{}).get('content',''))
        clean=final_answer_only(content)
        stats={'request_s':time.perf_counter()-started,'done_reason':result.get('done_reason'),
               'eval_count':result.get('eval_count'), 'prompt_eval_count':result.get('prompt_eval_count'),
               'thinking_chars':len(result.get('message',{}).get('thinking',''))}
        for key in ('total_duration','load_duration','prompt_eval_duration','eval_duration'):
            stats[key.replace('_duration','_s')]=result.get(key,0)/1e9
        return {'content':clean,'stats':stats,'wire':{'path':path,'body':body,'response':result},
                'error':'output_limit' if result.get('done_reason')=='length' else None}
    except Exception as exc:
        return {'content':'','stats':{'request_s':time.perf_counter()-started},'error':str(exc),'wire':{'path':path,'body':body}}
