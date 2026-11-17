"""Aggregate source-adjudicated reviews; never equate proxies with factual truth."""
import argparse
import collections
import hashlib
import json
import math
from pathlib import Path
import statistics

def median(xs):return statistics.median(xs) if xs else None
def p95(xs):return sorted(xs)[max(0,math.ceil(.95*len(xs))-1)] if xs else None
def key(row):return tuple(row[x] for x in ('model','strategy','cohort','turn'))
def main():
 p=argparse.ArgumentParser();p.add_argument('--inputs',nargs='+',type=Path,required=True);p.add_argument('--reviews',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
 data=[json.loads(path.read_text()) for path in args.inputs];rows={}
 for report in data:
  for row in report['rows']:
   if key(row) in rows:raise ValueError('Duplicate evaluation key across inputs')
   rows[key(row)]=row
 reviews=json.loads(args.reviews.read_text());audits={key(row):row for row in reviews['rows']}
 if len(audits)!=len(reviews['rows']):raise ValueError('Duplicate source-review key')
 for k,review in audits.items():
  if k not in rows or review['answer_sha256']!=hashlib.sha256(rows[k]['answer'].encode()).hexdigest():raise ValueError('Review does not match original answer')
 dimensions=reviews['dimensions'];cells=[]
 for model,strategy in dict.fromkeys((r['model'],r['strategy']) for r in rows.values()):
  selected=[r for r in rows.values() if r['model']==model and r['strategy']==strategy]
  reviewed=[audits[key(r)] for r in selected if key(r) in audits]
  times=[r['latency_s'] for r in selected];success=[r['latency_s'] for r in selected if not r['error']]
  counts=collections.Counter(r['grounding'] for r in reviewed)
  cell={'model':model,'strategy':strategy,'attempted_turns':len(selected),'expected_turns':16,'generation_errors':sum(bool(r['error']) for r in selected),'reviewed_turns':len(reviewed),'complete_for_quality':len(selected)==len(reviewed)==16,'grounding_counts':dict(counts),'quality_means':{d:statistics.mean(r['scores'][d] for r in reviewed) if reviewed else None for d in dimensions},'latency_median_s':median(times),'latency_p95_s':p95(times),'successful_latency_median_s':median(success),'successful_latency_p95_s':p95(success),'mechanical_plan_rejects':sum(bool(r.get('mechanical_plan_errors')) for r in selected),'stripped_inline_reasoning_turns':sum(any(c.get('stats',{}).get('stripped_inline_reasoning_chars',0) for c in r['calls']) for r in selected),'cohorts':{}}
  for cohort in dict.fromkeys(r['cohort'] for r in selected):
   rs=[r for r in selected if r['cohort']==cohort];vs=[audits[key(r)] for r in rs if key(r) in audits]
   cell['cohorts'][cohort]={'turns':len(rs),'reviewed':len(vs),'grounding':dict(collections.Counter(v['grounding'] for v in vs))}
  applicable=[v for v in reviewed if v.get('exclusion_compliant') is not None]
  cell['exclusion_reviews']=len(applicable);cell['exclusion_failures']=sum(v['exclusion_compliant'] is False for v in applicable)
  cell['unknown_calibration']=dict(collections.Counter(v['unknown_calibration'] for v in reviewed if 'unknown_calibration' in v))
  cells.append(cell)
 resources=[]
 for report in data:
  for phase in report.get('resources',[]):
   ss=[s for s in phase['samples'] if 'MemAvailable' in s];model=phase['model'];loaded=[m for s in ss for m in s.get('loaded',[]) if m['name']==model]
   resources.append({'model':model,'sample_count':len(ss),'actual_wsl_memory_bytes':max((s['MemTotal'] for s in ss),default=0),'min_linux_available_bytes':min((s['MemAvailable'] for s in ss),default=0),'max_swap_used_bytes':max((s['SwapTotal']-s['SwapFree'] for s in ss),default=0),'min_windows_disk_free_bytes':min((s['windows_c_free_bytes'] for s in ss),default=0),'max_gpu_total_used_mib':max((s.get('gpu_used_mib',0) for s in ss),default=0),'max_model_vram_bytes':max((m.get('size_vram',0) for m in loaded),default=0),'max_server_tree_rss_bytes':max((s.get('server_tree_rss_bytes',0) for s in ss),default=0),'swap_in_pages_delta':ss[-1]['pswpin_pages']-ss[0]['pswpin_pages'] if ss else 0,'swap_out_pages_delta':ss[-1]['pswpout_pages']-ss[0]['pswpout_pages'] if ss else 0,'max_linux_virtual_disk_busy_percent':max((s.get('linux_virtual_disk_busy_percent',0) for s in ss),default=0)})
 output={'input_sha256':{str(path):hashlib.sha256(path.read_bytes()).hexdigest() for path in args.inputs},'reviews_sha256':hashlib.sha256(args.reviews.read_bytes()).hexdigest(),'quality_review_method':reviews['method'],'attempted_rows':len(rows),'reviewed_rows':len(audits),'cells':cells,'resources':resources,'limitations':['Qwen27 partial low-memory attempts are not a completed quality comparison.','Grounding is source-adjudicated by the development agent, not an independent human study.','Needs-review bindings are separate from clear unsupported examples.','Validated-plan rendering receives an upstream oracle advantage.','Per-model timings use the actual 15.4 GiB/4 GiB environment, not the pending prepared limits.']}
 args.output.write_text(json.dumps(output,indent=2)+'\n');print('Aggregated',len(rows),'attempts and',len(audits),'source-reviewed answers.')
if __name__=='__main__':main()
