"""Source-aware synthetic quality benchmark. No external dependencies/services.
Run PYTHONPATH=.:scripts .venv/bin/python scripts/evaluate_quality.py --output PATH
"""
import argparse
import hashlib
import json
import statistics
import re
import tempfile
import time
from pathlib import Path
from vera.db import connect, insert_memory
from vera.conversation import Conversation
from quality_cases import CASES, THRESHOLDS


def score(expected, actual):
    answer=actual.get('answer',''); lower=answer.lower()
    unknown=any(x in lower for x in ("don't have", 'not recorded', 'no source', 'not described', 'not available'))
    clarification='?' in answer and any(x in lower for x in ('which','do you mean'))
    kind=expected['kind']
    behavior=(unknown if kind=='unknown' else clarification if kind=='clarification' else True if kind=='command' else not unknown and not clarification and bool(answer))
    facts=expected['facts']
    retrieved=set(actual.get('retrieved_ids',actual.get('source_ids',[])))
    recall=len(retrieved.intersection(expected['sources']))/len(expected['sources']) if expected['sources'] else None
    complete=sum(any(word.lower() in lower for word in group) for group in facts)/len(facts) if facts else None
    no_forbidden=not any(word.lower() in lower for word in expected['forbidden'])
    return dict(retrieval_recall=recall,answer_completeness=complete,behavior=behavior and no_forbidden and 'error' not in actual)


def audit_evidence(con, passage, answer):
    """Independent archive checks, not the implementation's verified flag.

    This audits provenance/lexical derivation, not universal semantic entailment.
    Human review still checks reference resolution and the quality of narration.
    """
    row=con.execute('SELECT content,contributor FROM memories WHERE id=?',(passage.get('source_id'),)).fetchone()
    if row is None:return False
    spans=passage.get('sentences',[])
    if not spans or any(not isinstance(s,str) or s not in row['content'] for s in spans):return False
    if ' '.join(spans)!=passage.get('quote'):return False
    prose=passage.get('text','')
    if not prose or prose not in answer:return False
    original_words=set(re.findall(r"[a-z0-9]+",row['content'].lower()+' '+row['contributor'].lower()))
    allowed=set("remembers thinks recalls says they them their isn t sure now photo note that s".split())
    if set(re.findall(r"[a-z0-9]+",prose.lower()))-original_words-allowed:return False
    # Changed years, invented places, and dropped uncertainty in selected date
    # clauses are all meaningful failures even if the source ID is correct.
    if set(re.findall(r'\b\d{4}\b',prose))-set(re.findall(r'\b\d{4}\b',passage['quote'])):return False
    if 'possibly' in passage['quote'].lower() and 'possibly' not in prose.lower():return False
    return True


def summarize(rows):
    scored=[t for t in rows if t['expected']['kind']!='command']
    mean=lambda xs: statistics.mean(xs) if xs else None
    metric=lambda key:mean([t['score'][key] for t in scored if t['score'][key] is not None])
    answer_turns=[t for t in scored if t['expected']['kind']=='answer']
    # Proxies only: attribution/narrative do not constitute a human quality rating.
    attribution=mean([any(name in t.get('answer','') for name in ('Sarah','Michael','Helen','Lisa','Margaret','James','Alex')) for t in answer_turns])
    narrative=mean(['recalls: “' not in t.get('answer','') and bool(t.get('answer')) and not t.get('answer','').startswith("I don't") for t in answer_turns])
    passages=[p for t in scored for p in t.get('evidence',[])]
    grounding=mean([p.get('independently_verified',False) for p in passages])
    lat={}
    for category in ('model','deterministic'):
        selected=[t for t in rows if bool(t['metrics'].get('attempts',0))==(category=='model')]
        values=[t['latency_s'] for t in selected]
        lat[category]={'turns':len(values),'median_s':statistics.median(values) if values else None,'p95_s':sorted(values)[max(0,int(.95*len(values))-1)] if values else None,'max_s':max(values) if values else None}
    inference=[t['metrics']['inference_s'] for t in rows if t['metrics'].get('attempts',0) and 'inference_s' in t['metrics']]
    lat['inference_only_median_s']=statistics.median(inference) if inference else None
    metrics=dict(retrieval_recall=metric('retrieval_recall'),answer_completeness=metric('answer_completeness'),behavior_accuracy=mean([t['score']['behavior'] for t in scored]),grounded_passage_rate=grounding,attribution_rate=attribution,natural_story_rate=narrative)
    return dict(metrics=metrics,criteria={key:metrics[key] is not None and metrics[key]>=threshold for key,threshold in THRESHOLDS.items()},latency=lat,errors=sum('error' in t for t in rows),reasoning_leaks=sum(any(x in t.get('answer','').lower() for x in ('<think>','</think>','analysis:','let me think')) for t in rows),turns=len(rows),model_calls=sum(t['metrics'].get('attempts',0) for t in rows))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);parser.add_argument('--repeat',type=int,default=1);parser.add_argument('--limit',type=int,default=30);args=parser.parse_args()
    import sys,socket
    def guard(event,values):
        if event=='socket.connect' and values[1][0] not in ('127.0.0.1','::1'):raise PermissionError('Offline benchmark')
    sys.addaudithook(guard)
    try:socket.create_connection(('192.0.2.1',443),timeout=1)
    except PermissionError:pass
    else:raise RuntimeError('External-network guard failed')
    fingerprints={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(Path('vera').glob('*.py'))}
    report={'source_sha256':fingerprints,'thresholds':THRESHOLDS,'offline_guard':True,'sequences':[],'notes':'Gold facts and surface quality proxies require manual review; recall targets minimally necessary sources.'}
    start=time.monotonic()
    for i,case in enumerate(CASES[:args.limit]*args.repeat,1):
        if time.monotonic()-start>900:raise RuntimeError('15-minute evaluation budget exceeded')
        with tempfile.TemporaryDirectory() as tmp:
            con=connect(Path(tmp)/'synthetic.sqlite3')
            for file in ('samples/demo_memories.json','samples/relevance_extra.json'):
                for r in json.loads(Path(file).read_text()):insert_memory(con,**r)
            session=Conversation(con);seq={'id':i,'turns':[]}
            for expected in case:
                t=time.perf_counter();entry={'expected':expected}
                before=con.total_changes
                try:entry['answer']=session.respond(expected['question'])
                except Exception as exc:entry['error']=str(exc)
                entry.update(latency_s=time.perf_counter()-t,source_ids=list(session.source_ids),retrieved_ids=list(session.metrics.get('retrieved_ids',session.source_ids)),metrics=dict(session.metrics),evidence=list(getattr(session,'evidence',[])),database_changes=con.total_changes-before)
                if expected['kind']!='command' and entry['database_changes']:entry['error']='Accidental archive write'
                for passage in entry['evidence']:
                    passage['independently_verified']=audit_evidence(con,passage,entry.get('answer',''))
                entry['score']=score(expected,entry);seq['turns'].append(entry)
            con.close()
        report['sequences'].append(seq)
        Path(args.output).write_text(json.dumps(report,indent=2))
        print(f"sequence {i}: "+str([t['expected']['question'] for t in seq['turns'] if not t['score']['behavior'] or t['score']['answer_completeness'] not in (None,1.0)]),flush=True)
    report['summary']=summarize([t for s in report['sequences'] for t in s['turns']]);report['elapsed_s']=time.monotonic()-start
    Path(args.output).write_text(json.dumps(report,indent=2));print(json.dumps(report['summary'],indent=2))
    if not all(report['summary']['criteria'].values()) or report['summary']['errors'] or report['summary']['reasoning_leaks']:raise SystemExit(1)
if __name__=='__main__':main()
