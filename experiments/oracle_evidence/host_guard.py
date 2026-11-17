"""Watch Windows host headroom during an owned oracle generation process."""
import json
import os
from pathlib import Path
import signal
import subprocess
import time

ROOT=Path('experiments/oracle_evidence/runtime')
OUT=Path('results/oracle_evidence/host-memory.json')
COMMAND='$ErrorActionPreference="Stop"; $o=Get-CimInstance Win32_OperatingSystem; [pscustomobject]@{FreePhysicalKiB=$o.FreePhysicalMemory;FreeVirtualKiB=$o.FreeVirtualMemory;TotalVirtualKiB=$o.TotalVirtualMemorySize;PageFiles=@(Get-CimInstance Win32_PageFileUsage | Select-Object AllocatedBaseSize,CurrentUsage,PeakUsage)} | ConvertTo-Json -Depth 4 -Compress'

def recognized_worker(argv):
 return 'generate' in argv and any(module in argv for module in ('experiments.oracle_evidence.run','experiments.conversation_architecture.run'))

def workers():
 ids=[]
 for path in Path('/proc').glob('[0-9]*/cmdline'):
  try:
   argv=path.read_bytes().decode(errors='replace').split('\0')
   if recognized_worker(argv) and path.parent.joinpath('cwd').resolve()==Path.cwd():ids.append(int(path.parent.name))
  except (FileNotFoundError,PermissionError,ProcessLookupError):pass
 return ids

def main(output=None):
 output_path=Path(output) if output is not None else OUT
 output_path.parent.mkdir(parents=True,exist_ok=True)
 rows=[];critical=0;failures=0;start=time.monotonic()
 while workers() and time.monotonic()-start<3*3600:
  try:
   text=subprocess.check_output(['powershell.exe','-NoProfile','-NonInteractive','-Command',COMMAND],text=True,timeout=15,stderr=subprocess.PIPE)
   payload=json.loads(text);failures=0
  except (subprocess.SubprocessError,json.JSONDecodeError) as exc:
   failures+=1
   rows.append({'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'monitor_error':type(exc).__name__,'consecutive_failures':failures})
   output_path.write_text(json.dumps({'samples':rows,'aborted':False},indent=2)+'\n')
   if failures<3:time.sleep(5);continue
   payload={'FreePhysicalKiB':0,'FreeVirtualKiB':0};critical=1
  sample={'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),**payload};rows.append(sample)
  output_path.write_text(json.dumps({'samples':rows,'aborted':False},indent=2)+'\n')
  low=int(sample['FreeVirtualKiB'])<512*1024 or int(sample['FreePhysicalKiB'])<256*1024
  critical=critical+1 if low else 0
  if critical>=2:
   pid=int((ROOT/'server.pid').read_text());argv=Path(f'/proc/{pid}/cmdline').read_bytes().split(b'\0');env=dict(x.split(b'=',1) for x in Path(f'/proc/{pid}/environ').read_bytes().split(b'\0') if b'=' in x)
   assert Path(os.fsdecode(argv[0])).name=='ollama' and env.get(b'OLLAMA_HOST')==b'127.0.0.1:11435'
   reason=('Windows host monitor failed three consecutive times' if failures>=3 else 'Windows physical/commit headroom safety floor reached in two consecutive samples')
   (ROOT/'HOST_GUARD_ABORT').write_text(reason);os.kill(pid,signal.SIGTERM)
   output_path.write_text(json.dumps({'samples':rows,'aborted':True,'reason':reason},indent=2)+'\n');raise RuntimeError(reason)
  time.sleep(5)
 print('Windows host memory monitor closed.',flush=True)
if __name__=='__main__':
 import argparse
 parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path)
 main(parser.parse_args().output)
