"""Live conversational acceptance checks, including negative constraints.

Gold expectations are separate from query parsing and evidence planning. The
reserved questions are not imported by the application or implementation tests.
"""
import argparse
import hashlib
import json
import statistics
import tempfile
import time
from pathlib import Path
from vera.conversation import Conversation
from vera.db import connect,insert_memory
from evaluate_quality import audit_evidence


def expected(required=(),forbidden=(),intent='archive_question',allowed=(),sentence_patterns=()):
    return {'required':list(required),'forbidden':list(forbidden),'intent':intent,'allowed_sources':list(allowed),'sentence_patterns':list(sentence_patterns)}

CRAB=expected(['caught nothing','fisherman','joked','Michael'],['cottage','sandcastle','bread','James'],allowed=[2])
FUNNY=expected(['fisherman','joked','Michael'],['cottage','sandcastle','bread','James'],allowed=[2],sentence_patterns=['crabbing','fisherman'])
BEACH=expected(['sandcastle','Sarah','Helen'],['not implemented','cottage','bread'],allowed=[1,3])
A='Did Sarah and Michael play on the beach?'
B='Tell me only about the crabbing trip, not the whole vacation.'
C='Was there anything funny about the crabbing trip?'
DEVELOPMENT=[[(A,BEACH)],[(B,CRAB)],[(C,FUNNY)],
 [('Tell me about Oregon.',None),(A,BEACH),(B,CRAB),(C,FUNNY)],
 [('Tell me about Grandma bread.',None),('Tell me about Oregon.',None),(A,BEACH),(B,CRAB),(C,FUNNY)],
 [('Tell me about the school concert.',None),('Did Dana play piano?',expected(['Dana','piano'],['not implemented'],allowed=[12])),('Can you play that recording?',expected(['not implemented'],intent='media_action'))],
 [('Tell me about Oregon.',None),('Focus only on crabbing without the cottages.',CRAB),('Anything amusing about that?',FUNNY)],
 [('Tell me about the lake boat ride.',None),('Was anything funny about the boat ride?',expected(['Nina','rowing lesson'],['pudding','sandwich'],allowed=[9]))],
 [('Tell me about the board game afternoon.',None),('Did Lena and Owen play chess?',expected(['Lena','chess'],['not implemented'],allowed=[11]))],
 [('Tell me about Grandma bread.',None),('Was anything humorous recorded about the bread?',expected(["don't have"],['fisherman','joked']))],
]


def assess(gold, answer, evidence, actual_intent, error=False):
    lower=answer.lower()
    required=gold.get('required',[])
    hits=[word.lower() in lower for word in required]
    forbidden=[word for word in gold.get('forbidden',[]) if word.lower() in lower]
    intent=gold.get('intent','media_action' if required==['not implemented'] else 'archive_question')
    relevant=[]
    for passage in evidence:
        for sentence in passage['sentences']:
            source_ok=not gold.get('allowed_sources') or passage['source_id'] in gold['allowed_sources']
            sentence_ok=not gold.get('sentence_patterns') or any(pattern.lower() in sentence.lower() for pattern in gold['sentence_patterns'])
            relevant.append(source_ok and sentence_ok)
    precision=sum(relevant)/len(relevant) if relevant else (0.0 if gold.get('allowed_sources') else 1.0)
    checks={'intent_correct':actual_intent==intent,'target_detail_complete':all(hits),
            'constraint_compliant':not forbidden,'answer_precision':precision,
            'required_hit_fraction':sum(hits)/len(hits) if hits else 1.0,'forbidden_hits':forbidden}
    checks['passed']=checks['intent_correct'] and checks['target_detail_complete'] and checks['constraint_compliant'] and precision==1 and not error
    return checks


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--heldout',action='store_true');p.add_argument('--questions');p.add_argument('--repeat',type=int,default=1);args=p.parse_args()
    import sys,socket
    def guard(event,values):
        if event=='socket.connect' and values[1][0] not in ('127.0.0.1','::1'):raise PermissionError('Offline acceptance evaluation')
    sys.addaudithook(guard)
    try:socket.create_connection(('192.0.2.1',443),timeout=1)
    except PermissionError:pass
    else:raise RuntimeError('Offline guard did not reject external access')
    cases=json.loads(Path(args.questions).read_text()) if args.questions else (json.loads(Path('samples/acceptance_holdout.json').read_text()) if args.heldout else DEVELOPMENT)
    report={'suite':args.questions or ('reserved_questions' if args.heldout else 'development'),'offline_guard':True,'repeat':args.repeat,'sequences':[],
            'source_sha256':{str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(Path('vera').glob('*.py'))}}
    began=time.monotonic()
    for index,case in enumerate(cases*args.repeat,1):
        if time.monotonic()-began>900:raise RuntimeError('15-minute run budget exceeded')
        with tempfile.TemporaryDirectory() as tmp:
            con=connect(Path(tmp)/'synthetic.sqlite3')
            for file in ('samples/demo_memories.json','samples/acceptance_extra.json'):
                for record in json.loads(Path(file).read_text()):insert_memory(con,**record)
            session=Conversation(con);seq={'id':index,'turns':[]}
            for question,gold in case:
                t=time.perf_counter();before=con.total_changes
                entry={'question':question,'gold':gold,'previous_source_ids':list(session.source_ids)}
                try:entry['answer']=session.respond(question)
                except Exception as exc:entry['error']=str(exc)
                answer=entry.get('answer','');lower=answer.lower()
                entry.update(latency_s=time.perf_counter()-t,metrics=dict(session.metrics),evidence=list(session.evidence),database_changes=con.total_changes-before)
                for passage in entry['evidence']:passage['independently_verified']=audit_evidence(con,passage,answer)
                if gold:
                    actual_intent=session.metrics.get('query',{}).get('intent','archive_question')
                    entry['checks']=assess(gold,answer,entry['evidence'],actual_intent,'error' in entry)
                seq['turns'].append(entry)
            con.close()
        report['sequences'].append(seq);Path(args.output).write_text(json.dumps(report,indent=2))
        print(index,[(t['question'],t.get('answer',t.get('error'))) for t in seq['turns'] if t.get('checks',{}).get('passed') is False],flush=True)
    turns=[t for s in report['sequences'] for t in s['turns']];scored=[t for t in turns if 'checks' in t]
    mean=lambda vals:statistics.mean(vals) if vals else None
    passages=[e for t in turns for e in t['evidence']]
    summary={'sequences':len(report['sequences']),'turns':len(turns),'scored_turns':len(scored),
        'intent_accuracy':mean([t['checks']['intent_correct'] for t in scored]),
        'constraint_compliance':mean([t['checks']['constraint_compliant'] for t in scored]),
        'target_detail_success':mean([t['checks']['target_detail_complete'] for t in scored]),
        'answer_precision':mean([t['checks']['answer_precision'] for t in scored]),
        'turn_pass_rate':mean([t['checks']['passed'] for t in scored]),
        'sequence_pass_rate':mean([all(t.get('checks',{}).get('passed',True) for t in s['turns']) for s in report['sequences']]),
        'grounded_passage_rate':mean([p['independently_verified'] for p in passages]),
        'errors':sum('error'in t for t in turns),'accidental_writes':sum(t['database_changes']!=0 for t in turns),
        'reasoning_leaks':sum(any(x in t.get('answer','').lower() for x in ('<think>','</think>','analysis:','let me think')) for t in turns),
        'output_limit_retries':sum(max(0,t['metrics'].get('attempts',0)-1) for t in turns),'latency':{}}
    for kind in ('model','deterministic'):
        lat=[t['latency_s'] for t in turns if bool(t['metrics'].get('attempts',0))==(kind=='model')]
        summary['latency'][kind]={'turns':len(lat),'median_s':statistics.median(lat) if lat else None,'max_s':max(lat) if lat else None}
    report['summary']=summary;report['elapsed_s']=time.monotonic()-began;Path(args.output).write_text(json.dumps(report,indent=2));print(json.dumps(summary,indent=2))
    if (summary['turn_pass_rate']!=1 or summary['grounded_passage_rate']!=1 or summary['errors'] or summary['accidental_writes'] or summary['reasoning_leaks']):raise SystemExit(1)
if __name__=='__main__':main()
