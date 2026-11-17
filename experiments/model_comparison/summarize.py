"""Aggregate raw drafts, critic uncertainty and conservative delivered fallbacks."""
import argparse
import json
import math
import re
import statistics
from pathlib import Path

DIMS=('directness','relevance','instruction_following','context_retention','completeness','naturalness')
NEUTRAL="I can't verify that from the available notes. Could you clarify which person or event you mean?"


def normalized(text):return text.lower().replace('’',"'").replace('‘',"'")
def mean(values):return statistics.mean(values) if values else None
def wilson(hits,total):
    if not total:return None
    z=1.96;p=hits/total;denom=1+z*z/total
    center=(p+z*z/(2*total))/denom
    half=z*((p*(1-p)+z*z/(4*total))/total)**.5/denom
    return [max(0,center-half),min(1,center+half)]

def p95(values):return sorted(values)[max(0,math.ceil(.95*len(values))-1)] if values else None


def gold_score(answer,gold):
    lower=normalized(answer);groups=gold['facts']
    hits=[any(normalized(word) in lower for word in group) for group in groups]
    forbidden=[word for word in gold['exclude'] if normalized(word) in lower]
    unknown=any(word in lower for word in ("don't have",'do not have',"can't verify",'cannot verify','not recorded','does not record','not in','no record','no information','not know',"don't know",'do not know',"can't tell",'cannot tell','do not establish','not establish',"doesn't say",'does not say',"don't tell",'do not tell','not specified','not documented','not described','no detail','no evidence',"can't say",'cannot say','unclear','not enough'))
    kind=gold['kind']
    if kind=='unknown':behavior=unknown
    elif kind=='action':behavior=any(word in lower for word in ('not implemented','unavailable',"can't send",'cannot send',"can't play",'cannot play','not able','unable'))
    elif kind=='save_request':behavior=not bool(re.search(r"\b(?:i have|i've|successfully)\s+(?:saved|added|recorded)\b",lower))
    elif kind=='uncertain':behavior=any(word in lower for word in ('uncertain','conflict','different','cannot',"can't",'not establish','recollection'))
    else:behavior=bool(answer) and not unknown
    count=len(re.findall(r'[.!?](?:\s|$)',answer))
    return {'fact_coverage':sum(hits)/len(hits) if hits else None,'scope_pass':not forbidden,'forbidden_hits':forbidden,
            'behavior_pass':behavior,'brief_pass':not gold['max_sentences'] or count<=gold['max_sentences'],
            'word_count':len(answer.split()),'fact_hits':hits}


def choose_final(raw,baseline,judgments,baseline_judgments,policy='strict'):
    if policy not in ('strict','validated_excerpt'):
        raise ValueError('Unknown fallback policy')
    valid=not raw.get('error') and not raw.get('validation_errors')
    approved=valid and len(judgments)==2 and len({j.get('judge') for j in judgments})==2 and all(j.get('grounding_pass') is True for j in judgments)
    if approved:return raw['raw_answer'],'natural',judgments
    baseline_ok=not baseline.get('error') and bool(baseline.get('raw_answer')) and (
        policy=='validated_excerpt' or (
            len(baseline_judgments)==2 and len({j.get('judge') for j in baseline_judgments})==2
            and all(j.get('grounding_pass') is True for j in baseline_judgments)))
    if baseline_ok:return baseline['raw_answer'],'excerpt_fallback',baseline_judgments
    return NEUTRAL,'neutral_fallback',[]


def main():
    p=argparse.ArgumentParser();p.add_argument('--generations',type=Path,required=True);p.add_argument('--reviews',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--fallback-policy',choices=('strict','validated_excerpt'),default='strict');args=p.parse_args()
    data=json.loads(args.generations.read_text());review=json.loads(args.reviews.read_text())
    def key(row):return tuple(row[k] for k in ('model','strategy','sequence','turn'))
    indexed={key(row):row for row in data['rows']};by_key={}
    for row in review['rows']:by_key.setdefault(key(row),[]).append(row)
    expected_keys={key(r) for r in data['rows']}
    if set(by_key)!=expected_keys or any(len(by_key[k])!=2 or len({j.get('judge') for j in by_key[k]})!=2 for k in expected_keys):
        raise RuntimeError('Incomplete or duplicate paired reviews; preserve partial data and finish reviewing before summary')
    processed=[]
    for row in data['rows']:
        judges=by_key.get(key(row),[])
        item={k:row[k] for k in ('model','strategy','sequence','turn','question','gold','novel')}
        item.update(raw_answer=row['raw_answer'],raw_score=gold_score(row['raw_answer'],row['gold']),raw_generation_s=row['latency_s'],model_called=bool(row.get('calls')),
                    raw_guard_errors=row.get('validation_errors',[]),generation_error=row.get('error'),
                    raw_critic_rejected=not(len(judges)==2 and all(j.get('grounding_pass') is True for j in judges)),
                    critic_disagreement=len(judges)==2 and judges[0].get('grounding_pass')!=judges[1].get('grounding_pass'),
                    critic_invalid=sum(bool(j.get('error') or j.get('verdict_error')) for j in judges),
                    quality_valid_count=sum(all(d in j.get('quality',{}) for d in DIMS) for j in judges),
                    raw_quality={d:mean([j['quality'][d] for j in judges if d in j.get('quality',{})]) for d in DIMS},
                    unsupported_claims=[{'judge':j['judge'],'claims':j.get('verdict',{}).get('unsupported_claims',[]),'verdict_error':j.get('verdict_error')} for j in judges],
                    grounding_verification_s=sum(j['latency_s'] for j in judges))
        if row['strategy']=='natural':
            base_key=(row['model'],'excerpt',row['sequence'],row['turn']);baseline=indexed[base_key]
            answer,route,final_judges=choose_final(row,baseline,judges,by_key.get(base_key,[]),args.fallback_policy)
            item.update(final_answer=answer,route=route,final_score=gold_score(answer,row['gold']),
                        final_quality={d:mean([j['quality'][d] for j in final_judges if d in j.get('quality',{})]) if final_judges else 1.0 for d in DIMS},
                        estimated_warm_pipeline_s=row['latency_s']+item['grounding_verification_s']+(baseline['latency_s'] if route=='excerpt_fallback' else 0))
        else:
            item.update(final_answer=row['raw_answer'],route='excerpt',final_score=item['raw_score'],final_quality=item['raw_quality'],estimated_warm_pipeline_s=row['latency_s'])
        processed.append(item)
    summary=[]
    for model in data['configuration']['models']:
        for strategy in ('excerpt','natural'):
            rows=[r for r in processed if r['model']==model and r['strategy']==strategy]
            lat=[r['raw_generation_s'] for r in rows];warm=[r['estimated_warm_pipeline_s'] for r in rows]
            cell={'model':model,'strategy':strategy,'turns':len(rows),'raw_quality':{},'delivered_quality':{}}
            for d in DIMS:
                cell['raw_quality'][d]=mean([r['raw_quality'][d] for r in rows if r['raw_quality'][d] is not None])
                cell['delivered_quality'][d]=mean([r['final_quality'][d] for r in rows if r['final_quality'][d] is not None])
            for prefix,field in (('raw','raw_score'),('delivered','final_score')):
                cell[prefix+'_fact_coverage']=mean([r[field]['fact_coverage'] for r in rows if r[field]['fact_coverage'] is not None])
                for name in ('scope_pass','behavior_pass','brief_pass'):cell[prefix+'_'+name]=mean([r[field][name] for r in rows])
            model_lat=[r['raw_generation_s'] for r in rows if r['model_called']]
            deterministic_lat=[r['raw_generation_s'] for r in rows if not r['model_called']]
            cell.update(model_turns=len(model_lat),deterministic_turns=len(deterministic_lat),model_generation_median_s=mean([]) if not model_lat else statistics.median(model_lat),model_generation_p95_s=p95(model_lat),deterministic_median_s=statistics.median(deterministic_lat) if deterministic_lat else None,
                        raw_generation_median_s=statistics.median(lat),raw_generation_p95_s=p95(lat),
                        estimated_warm_pipeline_median_s=statistics.median(warm),estimated_warm_pipeline_p95_s=p95(warm),
                        critic_rejected_rate=mean([r['raw_critic_rejected'] for r in rows]),critic_rejected_wilson95=wilson(sum(r['raw_critic_rejected'] for r in rows),len(rows)),critic_disagreement_rate=mean([r['critic_disagreement'] for r in rows]),
                        invalid_critic_verdicts=sum(r['critic_invalid'] for r in rows),valid_quality_reviews=sum(r['quality_valid_count'] for r in rows),expected_quality_reviews=2*len(rows),citation_rejections=sum(bool(r['raw_guard_errors']) for r in rows),
                        generation_errors=sum(bool(r['generation_error']) for r in rows),fallback_rate=mean([r['route'].endswith('fallback') for r in rows]),
                        neutral_fallbacks=sum(r['route']=='neutral_fallback' for r in rows))
            summary.append(cell)
    resources=[]
    for phase in data['resources']:
        samples=phase['samples'];loaded=[m for s in samples for m in s.get('loaded',[]) if m['name']==phase['model']]
        resources.append({'model':phase['model'],'model_vram_bytes_max':max((m['size_vram'] for m in loaded),default=0),
                          'model_resident_size_bytes_max':max((m['size'] for m in loaded),default=0),
                          'gpu_total_used_mib_max':max((s['gpu_used_mib'] for s in samples if 'gpu_used_mib' in s),default=0),
                          'isolated_tree_rss_kib_max':max((s['isolated_server_tree_rss_kib'] for s in samples if 'isolated_server_tree_rss_kib' in s),default=0)})
    args.output.write_text(json.dumps({'fallback_policy':args.fallback_policy,'cells':summary,'resources':resources,'rows':processed,
        'limitations':['Critic flags are model judgments, not measured hallucination truth.','Estimated warm pipeline sums sequential warm timings; it excludes model reload costs. See live pipeline probes.','Neutral fallback quality uses a conservative floor of 1, not a purported reviewer rating.','Question provenance is recorded in the frozen case fixture; historical provisional runs remain provisional.']},indent=2,ensure_ascii=False))
    print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
