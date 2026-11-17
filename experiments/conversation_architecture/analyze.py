"""Hash-bound semantic review plus timing; provenance never becomes accuracy."""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import statistics

def key(row):return tuple(row[k] for k in ('strategy','cohort','turn'))
def median(xs):return statistics.median(xs) if xs else None
def p95(xs):return sorted(xs)[max(0,math.ceil(.95*len(xs))-1)] if xs else None
def main():
 p=argparse.ArgumentParser();p.add_argument('--generations',type=Path,required=True);p.add_argument('--reviews',type=Path,required=True);p.add_argument('--cases',type=Path,required=True);p.add_argument('--expected-turns',type=int,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
 report=json.loads(args.generations.read_text());reviews=json.loads(args.reviews.read_text());rows={key(r):r for r in report['rows']};audits={key(r):r for r in reviews['rows']}
 if len(rows)!=len(report['rows']) or len(audits)!=len(reviews['rows']):raise ValueError('Duplicate row/review')
 if hashlib.sha256(args.cases.read_bytes()).hexdigest()!=report['configuration']['case_sha256']:raise ValueError('Fixture does not match run')
 for k,review in audits.items():
  if k not in rows or review['answer_sha256']!=hashlib.sha256(rows[k]['answer'].encode()).hexdigest():raise ValueError('Stale or unmatched source review')
 cells=[]
 for strategy in dict.fromkeys(r['strategy'] for r in rows.values()):
  rr=[r for r in rows.values() if r['strategy']==strategy];aa=[audits[key(r)] for r in rr if key(r) in audits];times=[r['latency_s'] for r in rr];inference=[r.get('inference_s',0) for r in rr]
  deterministic=[max(0,r['latency_s']-r.get('inference_s',0)) for r in rr]
  no_model=[r['latency_s'] for r in rr if not r.get('calls')]
  dims=list(dict.fromkeys(d for a in aa for d in a.get('scores',{})))
  cells.append({'strategy':strategy,'attempted':len(rr),'expected':args.expected_turns,'reviewed':len(aa),'complete':len(rr)==len(aa)==args.expected_turns,'runtime_errors':sum(bool(r['error']) for r in rr),'grounding':dict(Counter(a['grounding'] for a in aa)),'semantic_coverage':dict(Counter(a.get('semantic_coverage','not_reviewed') for a in aa)),'exclusion_reviews':sum(a.get('exclusion_compliant') is not None for a in aa),'exclusion_failures':sum(a.get('exclusion_compliant') is False for a in aa),'scope_contamination_rows':sum(bool(a.get('scope_contamination')) for a in aa),'unknown_calibration':dict(Counter(a['unknown_calibration'] for a in aa if a.get('unknown_calibration'))),'quality_means':{d:statistics.mean(a['scores'][d] for a in aa if d in a.get('scores',{})) for d in dims},'latency_median_s':median(times),'latency_p95_s':p95(times),'inference_median_s':median(inference),'inference_p95_s':p95(inference),'deterministic_processing_median_s':median(deterministic),'no_model_turns':len(no_model),'no_model_latency_median_s':median(no_model),'no_model_latency_p95_s':p95(no_model)})
 samples=report.get('resources',{}).get('samples',[])
 out={'generation_sha256':hashlib.sha256(args.generations.read_bytes()).hexdigest(),'review_sha256':hashlib.sha256(args.reviews.read_bytes()).hexdigest(),'case_sha256':report['configuration']['case_sha256'],'cells':cells,'resource_summary':{'sample_count':len(samples),'actual_memory_bytes':max((s.get('MemTotal',0) for s in samples),default=0),'actual_swap_bytes':max((s.get('SwapTotal',0) for s in samples),default=0),'minimum_windows_free_bytes':min((s['windows_c_free_bytes'] for s in samples if 'windows_c_free_bytes' in s),default=0),'max_gpu_total_used_mib':max((s.get('gpu_used_mib',0) for s in samples),default=0)},'limits':['Independent development-agent reviews, not a blind human study.','Literal source fidelity is not semantic grounding; missing context and scope remain separate defects.','Different fresh cohorts prevent a paired causal before/after quality claim.','Natural drafts are research-only and unreleased.','Small correlated samples do not establish production service levels or universal accuracy.']}
 args.output.write_text(json.dumps(out,indent=2)+'\n')
 print('Analyzed',len(rows),'answers with',len(audits),'hash-matched reviews.')
if __name__=='__main__':main()
