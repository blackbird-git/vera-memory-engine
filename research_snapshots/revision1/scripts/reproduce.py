import json, time
from pathlib import Path
from unittest.mock import patch
from urllib.request import urlopen
from vera.ollama import generate
records=json.loads(Path('samples/demo_memories.json').read_text())
context='\n\n'.join(f"Contributor: {r['contributor']}\n{r['content']}" for r in records[:3])
observed=[]
def traced(request, timeout):
    start=time.perf_counter()
    with urlopen(request, timeout=timeout) as response:
        raw=response.read()
    payload=json.loads(raw)
    observed.append({'request':json.loads(request.data), 'response':payload,'latency_s':time.perf_counter()-start})
    class Response:
        def __enter__(self): return self
        def __exit__(self,*args): return False
        def read(self): return raw
    return Response()
history=[]
for question in ['Tell me about the Oregon coast trip.','What happened after they went crabbing?']:
    try:
        with patch('vera.ollama.urlopen',traced):
            answer=generate(question=question,context=context,model='qwen3:4b',url='http://127.0.0.1:11434',history=history)
        history.extend([{'role':'user','content':question},{'role':'assistant','content':answer}])
        print(question,repr(answer),flush=True)
    except Exception as exc: print(type(exc).__name__,str(exc),flush=True)
Path('evaluations/reproduction-current.json').write_text(json.dumps(observed,indent=2))
print([(r['response'].get('done_reason'),r['response'].get('eval_count'),round(r['latency_s'],3)) for r in observed])
