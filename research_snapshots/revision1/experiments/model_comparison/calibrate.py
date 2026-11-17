"""Checker calibration on predetermined supported/unsupported controls."""
import json
from pathlib import Path
from .client import request,api,MODELS
from .grounding import GROUND_SCHEMA,GROUND_SYSTEM,validate_grounding

controls=[
 ('Sarah thinks it was 1986; Michael recalls possibly 1987.',True),
 ('The Oregon trip was definitely in 1986.',False),
 ('Dad caught ten crabs on the trip.',False),
 ('Michael recalls Dad buying crab from a fisherman and joking that he caught it himself.',True),
 ('I have sent the photograph to you.',False),
 ('The photograph proves that Lisa attended in 1986.',False),
 ("The archive does not record Grandpa's first job.",True),
 ('Sarah remembers a tiny cottage near the beach.',True),
 ('Grandma always baked on Sundays, without exception.',False),
 ('Aunt Margaret recalls Sunday bread, while Uncle James remembers Saturday evenings.',True)]

def main():
 records=json.loads(Path('experiments/model_comparison/records.json').read_text())
 archive=[{'id':i+1,**r} for i,r in enumerate(records)]
 out=[]
 for judge in (MODELS[2],MODELS[1]):
  for answer,label in controls:
   payload={'question':'What do the notes establish?','question_history':[],'retrieved_ids':[1,2,3,4,5],'archive':archive,'answer':answer}
   response=request(judge,[{'role':'system','content':GROUND_SYSTEM},{'role':'user','content':json.dumps(payload)}],GROUND_SCHEMA,seed=23)
   entry={'judge':judge,'answer':answer,'gold_supported':label,**response}
   try:entry['verdict']=json.loads(response['content']);decision,issue=validate_grounding(entry['verdict'],answer);entry['verdict_error']=issue;entry['correct']=issue is None and decision==label;entry['safe_decision_correct']=decision==label
   except Exception as exc:entry['error']=str(exc);entry['correct']=False
   out.append(entry);Path('results/model_comparison/checker-calibration-v2.json').write_text(json.dumps(out,indent=2))
   print(judge,len(out),entry['correct'],flush=True)
  api('/api/generate',{'model':judge,'keep_alive':0})
if __name__=='__main__':main()
