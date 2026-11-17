"""Verify prepared limits after a user-managed WSL restart; never restarts WSL."""
import argparse
import json
from .resources import snapshot

def main():
 p=argparse.ArgumentParser();p.add_argument('--require-prepared-limits',action='store_true');args=p.parse_args()
 info=snapshot();ready=info['MemTotal']>=23*2**30 and info['SwapTotal']>=7.5*2**30
 result={k:info[k] for k in ('MemTotal','MemAvailable','SwapTotal','SwapFree','windows_c_free_bytes')}
 result['prepared_limits_active']=ready
 print(json.dumps(result,indent=2))
 if args.require_prepared_limits and not ready:raise SystemExit('Prepared 24GB RAM / 8GB swap limits are not active. Restart WSL outside this running session first.')
 if info['windows_c_free_bytes']<44*2**30:raise SystemExit('Physical Windows disk reserve blocks inference')
if __name__=='__main__':main()
