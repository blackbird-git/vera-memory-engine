"""Start only the dedicated local daemon, with an optional bounded RAM prompt cache."""
import argparse
import os
from pathlib import Path
import socket

def main():
 p=argparse.ArgumentParser();p.add_argument('--cache-mib',type=int);args=p.parse_args()
 if args.cache_mib is not None and not 0<=args.cache_mib<=8192:raise ValueError('Cache budget outside experiment bounds')
 with socket.socket() as probe:
  if probe.connect_ex(('127.0.0.1',11435))==0:raise RuntimeError('Dedicated port already in use; do not replace an unknown service')
 root=Path('experiments/oracle_evidence/runtime');root.mkdir(parents=True,exist_ok=True)
 os.environ.update(OLLAMA_HOST='127.0.0.1:11435',OLLAMA_MODELS=str(Path('.local_models').resolve()),OLLAMA_NO_CLOUD='1',OLLAMA_NOPRUNE='1',OLLAMA_MAX_LOADED_MODELS='1',OLLAMA_NUM_PARALLEL='1',OLLAMA_KEEP_ALIVE='2m')
 os.environ.pop('LLAMA_ARG_CACHE_RAM',None)
 if args.cache_mib is not None:os.environ['LLAMA_ARG_CACHE_RAM']=str(args.cache_mib)
 (root/'server.pid').write_text(str(os.getpid()))
 os.execvp('ollama',['ollama','serve'])
if __name__=='__main__':main()
