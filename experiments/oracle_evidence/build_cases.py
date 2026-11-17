"""Create the frozen oracle-only synthetic cohort; never imported by production."""
import json
from pathlib import Path

ROOT=Path('experiments/oracle_evidence')
base=json.loads(Path('experiments/model_comparison/records.json').read_text())[:5]
records={str(i+1):r for i,r in enumerate(base)}
new=[
 ('Canal bicycle afternoon','Iris','I remember cycling beside the canal in 2009. Leo got a puncture near the lock. We walked the bicycles to a repair shop. Leo called it our slowest cycling race.', 'canal-ride'),
 ('Canal photograph','Nora','My photograph shows two bicycles beside a canal lock. The envelope is labeled May 2010. I cannot identify the riders, and the photograph itself has no date.','canal-ride'),
 ('Canal ride recollection','Leo','I think the canal ride was in 2010, though I am not certain. My bicycle got a puncture. Iris and I walked to the repair shop. I joked that we were in the slowest cycling race.','canal-ride'),
 ('Market cake stall','Tessa','At the town market I sold lemon cake with Priya. We sold every slice. The receipt says September 2016. I do not remember the price per slice.','market-cake'),
 ('Market stall recollection','Priya','I remember selling lemon cake with Tessa at the town market, possibly in 2017. Tessa forgot the napkins, so we used spare paper plates.','market-cake'),
 ('Kitchen herbs','Uncle Martin','I grew basil and mint on the kitchen windowsill in 2015.','kitchen-herbs')]
for i,(title,contributor,content,event) in enumerate(new,101):
 records[str(i)]={'title':title,'contributor':contributor+' (synthetic)','kind':'photo_note' if 'photograph' in title.lower() else 'story','content':content,'metadata':{'events':[event],'uncertainty':'attributed synthetic source, not independent historical proof'}}

def fact(source_id,claim,quote=None):
 source=records[str(source_id)]
 if quote is None:quote=source['content']
 assert quote in source['content']
 return {'source_id':source_id,'claim':claim,'supporting_quote':quote}

def turn(q,ids,claims,status='known',exclude=(),required=(),caveats=(),max_sentences=4):
 return {'question':q,'oracle_source_ids':ids,'validated_plan':{'status':status,'facts':claims,'caveats':list(caveats),'excluded_topics':list(exclude)},'rubric':{'required_fact_groups':[list(x) for x in required],'excluded_topics':list(exclude),'max_sentences_proxy':max_sentences,'status':status,'source_review_required':True}}

manual_q=[t['question'] for t in json.loads(Path('experiments/model_comparison/manual-confirmed-cases.json').read_text())[0]['turns']]
crab=[fact(2,'Michael recalls that Dad took them crabbing and they caught nothing.','Dad took us crabbing but we caught nothing.'),fact(2,'Michael recalls Dad buying crab from a fisherman at the dock and joking that he had caught it himself.','He bought crab from a fisherman at the dock and joked that he had caught it himself.')]
beach=[fact(1,'Sarah remembers building sandcastles together.','My strongest memory is building sandcastles together.'),fact(3,"Helen's photograph description shows children building a sandcastle; Helen tentatively identifies Sarah, Michael and cousin Lisa.","A faded photograph shows three children building a sandcastle on the Oregon coast. The back of the photograph is handwritten 'Summer 1986'. The children appear to be Sarah, Michael, and their cousin Lisa, based on Helen's identification.")]
manual=[
 turn(manual_q[0],[1,3],beach,required=[('sandcastle','sand castle'),('Sarah',),('Michael',)],caveats=['Photo identity is tentative, based on Helen; do not infer emotions.']),
 turn(manual_q[1],[2],crab,exclude=['cottage','sandcastles','general vacation','bread'],required=[('caught nothing','no crab','empty-handed'),('bought','purchased'),('fisherman',),('joke','joked','pretend','claimed')]),
 turn(manual_q[2],[2],crab[1:],exclude=['cottage','sandcastles','bread'],required=[('bought','purchased'),('joke','joked','pretend','claimed')]),
 turn(manual_q[3],[1,3],beach,required=[('sandcastle','sand castle')],caveats=['Do not overstate Helen\'s tentative identity assessment.']),
 turn(manual_q[4],[2],crab,exclude=['cottage','dates','sandcastles','bread'],required=[('bought','purchased'),('joke','joked','pretend','claimed')],max_sentences=3),
 turn(manual_q[5],[2],[fact(2,'Michael was not certain of the year; he suggested possibly 1987.',"I'm not sure of the year, possibly 1987.")],status='uncertain',required=[('Michael',),('1987',),('uncertain','not sure','not certain','possibly','unsure')],max_sentences=2),
 turn(manual_q[6],[1,2,3],[fact(1,'Sarah remembers a tiny cottage near the Oregon coast beach and building sandcastles.','We rented a tiny cottage near the beach. My strongest memory is building sandcastles together.'),*crab],required=[('sandcastle','sand castle'),('bought','purchased'),('joke','joked','pretend','claimed')],caveats=['Do not invent reactions, dialogue, relationships or details. No need to give a year; accounts do not establish one certain outing.'],max_sentences=4),
 turn(manual_q[7],[2,5],[],status='unknown',required=[],caveats=['The supplied notes do not establish whether Uncle James attended the crabbing trip. Absence of evidence is not proof he did not attend. A bread account does not establish crabbing attendance.'],max_sentences=2)]
# Separately authored before candidate output; not an independent human study.
holdout=[
 turn('Tell me about Iris and Leo cycling along the canal.',[101,103],[fact(101,'Iris remembers cycling beside the canal; Leo got a puncture and they walked to a repair shop.'),fact(103,'Leo also recalls the puncture and walking with Iris to the repair shop.')],required=[('puncture','flat'),('walk','walked'),('repair',)],caveats=['Iris recalls 2009; Leo tentatively recalls 2010. Do not merge dates into certainty.']),
 turn('Leave out the years and the photograph. What happened after the puncture?',[101,103],[fact(101,'Iris says they walked the bicycles to a repair shop.','We walked the bicycles to a repair shop.'),fact(103,'Leo recalls walking with Iris to the repair shop.','Iris and I walked to the repair shop.')],exclude=['dates','photograph'],required=[('walk','walked'),('repair',)],max_sentences=2),
 turn('What was the joke, and who made it?',[101,103],[fact(101,'Iris recalls Leo calling it their slowest cycling race.','Leo called it our slowest cycling race.'),fact(103,'Leo remembers joking they were in the slowest cycling race.','I joked that we were in the slowest cycling race.')],required=[('Leo',),('slowest',),('race',)],max_sentences=2),
 turn('Does the photograph prove the riders were Iris and Leo in May 2010?',[102],[fact(102,'Nora cannot identify the riders and the photograph itself has no date.','I cannot identify the riders, and the photograph itself has no date.'),fact(102,'May 2010 is an envelope label, not an established date or identity for the photograph.','The envelope is labeled May 2010.')],status='uncertain',required=[('envelope',),('2010',),('not','cannot',"can't",'uncertain')],max_sentences=3),
 turn('Switch to the market stall. What did Tessa and Priya sell?',[104,105],[fact(104,'Tessa remembers selling lemon cake with Priya.','At the town market I sold lemon cake with Priya.'),fact(105,'Priya also recalls selling lemon cake with Tessa.','I remember selling lemon cake with Tessa at the town market, possibly in 2017.')],required=[('lemon',),('cake',)],exclude=['canal','bicycles'],max_sentences=2),
 turn('Tell me just how they handled the missing napkins; skip the sales totals and dates.',[105],[fact(105,'Priya recalls that Tessa forgot the napkins, so they used spare paper plates.','Tessa forgot the napkins, so we used spare paper plates.')],required=[('Tessa',),('napkin','napkins'),('paper plates',)],exclude=['dates','sales totals'],max_sentences=2),
 turn('Can we honestly give one certain year for that stall?',[104,105],[fact(104,'Tessa\'s receipt is dated September 2016.','The receipt says September 2016.'),fact(105,'Priya recalls possibly 2017.','I remember selling lemon cake with Tessa at the town market, possibly in 2017.')],status='uncertain',required=[('2016',),('2017',),('uncertain','not certain','conflict','differ','cannot',"can't",'not establish')],caveats=['Receipt date and recollection do not establish one certain year or prove they describe the identical stall.']),
 turn('Did Uncle Martin sell the cake with them, and what did each slice cost?',[104,105,106],[],status='unknown',caveats=['These notes do not establish Martin\'s attendance. Tessa does not remember the price per slice; no price is recorded. Do not assert Martin did not attend or invent a price.'],max_sentences=3)]
report={'design':'Oracle evidence bypasses production retrieval, routing and SQLite. Controlled-plan facts are human/source-adjudicated evaluation inputs, not a deployable automatic verifier. Holdout is separately authored and frozen before outputs, not an independent human evaluation.','records':records,'cohorts':[{'id':'manual_exact','turns':manual},{'id':'independent_holdout','turns':holdout}]}
p=ROOT/'cases.json'
if p.exists():raise RuntimeError('Do not overwrite a frozen case fixture')
p.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
print('Frozen 8 exact manual + 8 separate holdout turns with oracle sources and validated plans.')
if __name__=='__main__':pass
