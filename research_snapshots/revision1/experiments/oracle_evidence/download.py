"""Download only requested public models, preserving a physical Windows disk reserve."""
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time
import urllib.request

ROOT=Path('experiments/oracle_evidence/runtime')
OUT=Path('results/oracle_evidence')
MODELS=('gpt-oss:20b','qwen3.5:27b')
# Keep >=40 GiB physical free plus future 8 GiB swap and 4 GiB safety margin.
STOP_FREE=52*2**30

def sample():
    memory={}
    for line in Path('/proc/meminfo').read_text().splitlines():
        key,value,*_=line.split()
        if key.rstrip(':') in ('MemTotal','MemAvailable','SwapTotal','SwapFree'):
            memory[key.rstrip(':')]=int(value)*1024
    return {'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
            'windows_c_free_bytes':shutil.disk_usage('/mnt/c').free,
            'linux_free_bytes':shutil.disk_usage('.').free,**memory}

def api(path):
    op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with op.open('http://127.0.0.1:11435'+path,timeout=10) as r:return json.load(r)

def main():
    OUT.mkdir(exist_ok=True,parents=True)
    result={'stop_free_bytes':STOP_FREE,'physical_reserve_bytes':40*2**30,'models':[],'samples':[]}
    for model in MODELS:
        before=sample();result['samples'].append(before)
        if before['windows_c_free_bytes']<STOP_FREE:raise RuntimeError('Windows free-space reserve blocks download')
        started=time.monotonic();env=dict(os.environ,OLLAMA_HOST='127.0.0.1:11435')
        with (ROOT/(model.replace(':','_')+'.pull.log')).open('w') as log:
            proc=subprocess.Popen(['ollama','pull',model],env=env,stdout=log,stderr=subprocess.STDOUT)
            try:
                while proc.poll() is None:
                    current=sample();result['samples'].append(current)
                    (OUT/'downloads.json').write_text(json.dumps(result,indent=2)+'\n')
                    if current['windows_c_free_bytes']<STOP_FREE:
                        proc.send_signal(signal.SIGINT)
                        raise RuntimeError('Download stopped before physical Windows reserve is threatened')
                    if time.monotonic()-started>3600:
                        proc.send_signal(signal.SIGINT);raise TimeoutError('One-hour download budget exceeded')
                    time.sleep(5)
                item={'model':model,'exit_code':proc.returncode,'elapsed_s':time.monotonic()-started,'after':sample()}
                if proc.returncode:raise RuntimeError('Model download failed; inspect ignored pull log')
                item['manifest']=next(x for x in api('/api/tags')['models'] if x['name']==model)
                result['models'].append(item)
                (OUT/'downloads.json').write_text(json.dumps(result,indent=2)+'\n')
                print(model,'downloaded',round(item['elapsed_s'],1),'s; C: free GiB',round(item['after']['windows_c_free_bytes']/2**30,1),flush=True)
            finally:
                if proc.poll() is None:
                    proc.terminate()
                    try:proc.wait(timeout=10)
                    except subprocess.TimeoutExpired:proc.kill();proc.wait()
    print('Both downloads complete, existing models preserved.',flush=True)
if __name__=='__main__':main()
