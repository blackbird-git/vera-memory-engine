"""Physical Windows disk, Linux memory/swap, GPU and own-service monitoring."""
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import threading
import time
from .client import api

ROOT=Path('experiments/oracle_evidence/runtime')

def snapshot():
 result={'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'monotonic':time.monotonic(),'windows_c_free_bytes':shutil.disk_usage('/mnt/c').free}
 for line in Path('/proc/meminfo').read_text().splitlines():
  k,v,*_=line.split()
  if k.rstrip(':') in ('MemTotal','MemAvailable','SwapTotal','SwapFree'):result[k.rstrip(':')]=int(v)*1024
 vm=dict(line.split() for line in Path('/proc/vmstat').read_text().splitlines())
 result.update(pswpin_pages=int(vm['pswpin']),pswpout_pages=int(vm['pswpout']))
 major,minor=os.major(os.stat('.').st_dev),os.minor(os.stat('.').st_dev)
 for line in Path('/proc/diskstats').read_text().splitlines():
  fields=line.split()
  if int(fields[0])==major and int(fields[1])==minor:
   result.update(disk_read_sectors=int(fields[5]),disk_write_sectors=int(fields[9]),disk_io_ms=int(fields[12]));break
 try:
  out=subprocess.check_output(['nvidia-smi','--query-gpu=memory.used,memory.total,utilization.gpu,utilization.memory','--format=csv,noheader,nounits'],text=True,timeout=5)
  v=[int(x.strip()) for x in out.strip().split(',')];result.update(gpu_used_mib=v[0],gpu_total_mib=v[1],gpu_util_percent=v[2],gpu_memory_util_percent=v[3])
 except Exception as exc:result['gpu_error']=type(exc).__name__
 try:result['loaded']=api('/api/ps',timeout=5).get('models',[])
 except Exception as exc:result['loaded_error']=type(exc).__name__
 try:
  pid=int((ROOT/'server.pid').read_text());rows=[list(map(int,line.split())) for line in subprocess.check_output(['ps','-eo','pid,ppid,rss'],text=True).splitlines()[1:]];children={pid}
  for _ in range(5):children|={r[0] for r in rows if r[1] in children}
  result['server_tree_rss_bytes']=sum(r[2]*1024 for r in rows if r[0] in children)
 except Exception as exc:result['rss_error']=type(exc).__name__
 return result

class Monitor:
 def __init__(self):self.samples=[];self.stop=threading.Event();self.abort=None
 def collect(self):
  current=snapshot()
  if self.samples and 'disk_io_ms' in current and 'disk_io_ms' in self.samples[-1]:
   previous=self.samples[-1];elapsed=current['monotonic']-previous['monotonic']
   current['linux_virtual_disk_busy_percent']=min(100,max(0,(current['disk_io_ms']-previous['disk_io_ms'])/(elapsed*10)))
  self.samples.append(current)
  # Preserve samples even if a long request is interrupted before a model completes.
  with (ROOT/'resource-timeline.jsonl').open('a') as log:log.write(json.dumps(current)+'\n')
  low=(current['windows_c_free_bytes']<44*2**30 or (current['MemAvailable']<384*2**20 and current['SwapFree']<256*2**20))
  if low and self.abort is None:
   self.abort='Physical disk or memory/swap safety reserve reached'
   pid=int((ROOT/'server.pid').read_text())
   cmd=Path(f'/proc/{pid}/cmdline').read_bytes().split(b'\0')
   env=dict(v.split(b'=',1) for v in Path(f'/proc/{pid}/environ').read_bytes().split(b'\0') if b'=' in v)
   if Path(os.fsdecode(cmd[0])).name=='ollama' and env.get(b'OLLAMA_HOST')==b'127.0.0.1:11435':os.kill(pid,signal.SIGTERM)
 def worker(self):
  while not self.stop.wait(1):
   try:self.collect()
   except Exception as exc:self.samples.append({'monitor_error':str(exc)})
 def __enter__(self):self.collect();self.thread=threading.Thread(target=self.worker,daemon=True);self.thread.start();return self
 def __exit__(self,*args):self.stop.set();self.thread.join(timeout=15);self.collect()
