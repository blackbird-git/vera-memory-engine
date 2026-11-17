"""Post-hoc role/date/uncertainty stress controls; judge prompts stay unchanged.
The main run exposed a binding error missed by both critics. These controls measure
that failure class; they are not used to add family-specific production rules.
"""
import json
from pathlib import Path
from .client import request,api,MODELS
from .grounding import GROUND_SYSTEM,GROUND_SCHEMA,validate_grounding
from .run import offline

CONTROLS=[
 ('Michael remembers the Oregon trip as summer 1986.',False),
 ('Sarah remembers possibly 1987.',False),
 ('Jun made the emergency power supply joke.',False),
 ('Ben fetched spare batteries during the orchard evening.',False),
 ('The orchard photograph envelope is labeled October 2011.',True),
 ('The orchard photograph was taken in October 2011.',False),
 ('Michael is Sarah\'s brother.',False),
 ('Alex Reed recalls that no one went crabbing on the Washington outing.',True),
 ('Michael recalls Dad buying crab from a fisherman.',True),
 ('Uncle James remembers bread baking on Saturday evenings.',True),
 ('Theo recalls 2011 while Jun thinks the lantern evening was in 2012.',True),
 ('Helen identifies the children tentatively; the note does not independently prove their identity.',True)]


def main():
 offline();archive=[{'id':i+1,**r} for i,r in enumerate(json.loads(Path('experiments/model_comparison/records.json').read_text()))]
 output=Path('results/model_comparison/grounding-stress.json');rows=[]
 for judge in (MODELS[2],MODELS[1]):
  for answer,label in CONTROLS:
   payload={'archive':archive,'retrieved_ids':list(range(1,len(archive)+1)),'question':'Is every factual assertion in this answer supported by the retrieved records?','answer':answer,'question_history':[]}
   response=request(judge,[{'role':'system','content':GROUND_SYSTEM},{'role':'user','content':json.dumps(payload,ensure_ascii=False)}],GROUND_SCHEMA,seed=23)
   entry={'judge':judge,'answer':answer,'gold_supported':label,**response}
   try:
    verdict=json.loads(response['content']);decision,issue=validate_grounding(verdict,answer)
    entry.update(verdict=verdict,verdict_error=issue,decision=decision,correct=issue is None and decision==label,safe_decision_correct=decision==label)
   except Exception as exc:entry.update(error=str(exc),decision=False,correct=False,safe_decision_correct=not label)
   rows.append(entry);output.write_text(json.dumps(rows,indent=2,ensure_ascii=False));print(judge,len(rows),entry['correct'],flush=True)
  api('/api/generate',{'model':judge,'keep_alive':0})
if __name__=='__main__':main()
