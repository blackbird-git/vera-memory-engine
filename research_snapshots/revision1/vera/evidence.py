"""Question-focused evidence plans and conservative natural narration.

Models may order source passages. Factual prose is derived from original wording,
not accepted as an unchecked model paraphrase. Every passage retains its source.
"""
import json
import re
from .retrieval import expanded_terms, tokens
from .ollama import final_answer_only
from .query import analyse, stems, HUMOR, GENERIC


def name(row):
    return re.sub(r'\s*\(synthetic[^)]*\)', '', row['contributor']).strip()


def sentences(content):
    return [s for s in re.split(r'(?<=[.!?])\s+',content.strip()) if s]


def safe(text):
    return (not re.search(r'<\s*/?\s*(think|analysis)\b',text,re.I)
            and final_answer_only(text)==text.strip())


def narrate(quote, contributor, kind):
    """Only grammatical person/attribution changes; quoted dialogue is untouched.

    Avoid assumed genders, listener participation, and invented emotional bridges.
    First-person groups remain explicitly the contributor's group.
    """
    output=[]
    for index,sentence in enumerate(sentences(quote)):
        # Keep literal quotations and contractions intact by treating only the
        # opening grammatical subject as a transformation boundary.
        if sentence.startswith('I remember '):
            text=contributor+' remembers '+sentence[len('I remember '):]
        elif sentence.startswith('I think '):
            text=contributor+' thinks '+sentence[len('I think '):]
        elif sentence.startswith('I now think '):
            text=contributor+' now thinks '+sentence[len('I now think '):]
        elif sentence.startswith("I'm not sure"):
            text=contributor+" isn't sure"+sentence[len("I'm not sure"):]
        elif sentence.startswith('My '):
            text=(contributor+' remembers that their '+sentence[3:] if index==0 else contributor+"'s "+sentence[3:])
        elif sentence.startswith('I am '):
            text=contributor+' says they are '+sentence[len('I am '):]
        elif sentence.startswith('I was '):
            text=contributor+' says they were '+sentence[len('I was '):]
        elif sentence.startswith('I '):
            text=contributor+' says they '+sentence[2:]
        elif sentence.startswith('We '):
            # Retain the exact participant group rather than guess its members.
            text=contributor+' says, “'+sentence+'”'
        elif index==0:
            if kind=='photo_note':
                text=contributor+"'s photo note says: “"+sentence+'”'
            else:
                text=contributor+' remembers: “'+sentence+'”'
        else:
            text=sentence
        # Change group pronouns only outside literal quotations. An unquoted
        # 'us' must not make Vera or the listener a participant in the event.
        parts=re.split(r'("[^"]*"|“[^”]*”)',text)
        for n in range(0,len(parts),2):
            parts[n]=re.sub(r"\bmy\b",contributor+"'s",parts[n],flags=re.I)
            parts[n]=re.sub(r"\bme\b",contributor,parts[n],flags=re.I)
            for original,replacement in ((r'\bwe\b','they'),(r'\bus\b','them'),(r'\bour\b','their')):
                parts[n]=re.sub(original,replacement,parts[n],flags=re.I)
        output.append(''.join(parts))
    return ' '.join(output)


def plan(question, sources, focal=()):
    question=analyse(question).positive
    q=question.lower();qt=tokens(question);terms=expanded_terms(question)
    story=bool(re.search(r'\b(tell me|what do we know|longer|stories)\b',q))
    story = story or (bool(re.match(r'^(the |alex )',q)) and not q.endswith('?'))
    date=bool(qt & {'year','date','dates'}) or (bool(re.search(r'\b\d{4}\b',q)) and not qt&HUMOR)
    photo=bool(qt & {'photo','photograph','picture','image'})
    artifact=qt & {'receipt','letter','transcript'}
    relationship=bool(qt & {'related','relationship','relationships'})
    who=bool(re.match(r'who\b',q))
    places=bool(qt & {'place','places','locations','location'})
    compare=bool(qt & {'same','separate','both','different','recollections'})
    chronological=bool(qt & {'after','next'})
    appearance=bool(re.search(r'\b(look like|appearance)\b',q))
    descriptive=[]
    if appearance:
        subject=terms-{'look','like','appearance'}
        descriptive=[s for r in sources for s in sentences(r['content']) if subject & tokens(s) and re.search(r'\b(was|is|looked|looks|had|has)\b',s.lower())]
    missing_detail=bool(re.search(r'\b(look like|appearance|street address|exact street|first job)\b',q))
    # These specific details need explicit evidence, not a source merely mentioning
    # the entity. Do not infer a clock description from the word 'clock'.
    detail_words={'address','street','job','appearance','looked','colour','color','shape'} & qt
    if missing_detail and not descriptive and not any(detail_words & tokens(r['content']) for r in sources):return [],''
    if re.search(r'\b(ignore|system:)\b',q):return [],''
    if qt & {'audio','recording'} and qt & {'original','have'}:
        # A recording note is not evidence that the original file is available.
        available=[r for r in sources if r['media_path']]
        if not available:return [],''
    focused=(who and bool(qt & {'that','it'})) or 'what evidence supports that' in q
    chosen=[]
    for row in sources:
        ss=sentences(row['content'])
        if not all(safe(s) for s in ss):continue
        meta=json.loads(row['metadata'])
        matched=[s for s in ss if expanded_terms(s) & terms]
        if appearance:
            matched=[s for s in ss if s in descriptive]
        elif focused and focal:
            matched=[p['quote'] for p in focal if p['source_id']==row['id']]
        elif tokens(question)&{'play','played','playing','plays'}:
            matched=[s for s in ss if tokens(s)&{'play','played','playing','plays','game','games','sandcastle','sandcastles'}]
            if row['kind']=='photo_note' and matched:
                matched += [s for s in ss if 'identif' in s.lower()]
        elif (photo and not date and not compare):
            matched=ss if row['kind']=='photo_note' else []
        elif artifact and not date and not compare:
            matched=ss if tokens(row['title']+' '+row['content']) & artifact else []
        elif compare and qt & {'same','separate'}:
            matched=[s for s in ss if re.search(r'\b(?:18|19|20)\d{2}\b',s)]
        elif story or compare:
            matched=ss
        elif date:
            matched=[s for s in ss if re.search(r'\b(?:18|19|20)\d{2}\b',s)]
        elif photo:
            matched=ss if row['kind']=='photo_note' else []
        elif places:
            place=meta.get('place','')
            matched=[s for s in ss if place and place.lower() in s.lower()]
        elif relationship:
            matched=[s for s in ss if tokens(s)&{'cousin','sister','brother','parent','mother','father','sibling','related'}]
        elif qt & {'mentioned'} and qt & {'who','people'}:
            matched=ss
        elif who and terms:
            # Attribution questions require the requested object in the account,
            # not just shared event or contributor-name overlap.
            significant=terms-{'contributed','contributor','identified','children','says','tells','differently','warm','brought'}
            if significant:matched=[s for s in ss if expanded_terms(s)&significant]
            elif 'identified' in qt:matched=[s for s in ss if 'identif' in s.lower()]
            else:matched=ss
        if chronological and matched:matched=ss
        if matched:
            quote=' '.join(dict.fromkeys(matched))
            # A joined excerpt is made only of complete original sentences.
            chosen.append({'source_id':row['id'],'quote':quote,'sentences':list(dict.fromkeys(matched)),
                           'text':narrate(quote,name(row),row['kind']), 'verified':True})
    suffix=''
    if date and len(chosen)>1:
        suffix='These accounts do not establish a single certain date or outing.'
    if compare:
        suffix='These recollections do not establish whether they describe the same outing.' if qt & {'same','separate'} else 'The accounts differ; the notes do not establish which recollection is correct.'
    return chosen,suffix


def focus_plan(question, sources):
    """Bound candidate sentences to a requested topic before semantic selection.

    Referential continuations stay with their antecedent. Exclusions filter
    sentences rather than deleting a mixed-topic original source record.
    """
    spec=analyse(question)
    anchors=stems(set(keywords_for_focus(spec.positive))-HUMOR-GENERIC)
    excluded=stems(set().union(*(expanded_terms(e) for e in spec.excluded)) if spec.excluded else set())-GENERIC
    candidates=[]
    for row in sources:
        ss=sentences(row['content'])
        if not all(safe(s) for s in ss):continue
        hits={i for i,s in enumerate(ss) if stems(tokens(s))&anchors}
        # Titles identify an account whose vocabulary differs from the question.
        if not hits and stems(tokens(row['title']))&anchors:hits=set(range(len(ss)))
        if not anchors:hits=set(range(len(ss)))
        for i in list(hits):
            # An immediate consequence may introduce a named actor rather than
            # a pronoun. Keep that adjacent result available for selection.
            if i+1<len(ss):hits.add(i+1)
            j=i+1
            while j<len(ss) and re.match(r'^(he|she|they|then|afterward|instead|but|so)\b',ss[j],re.I):
                hits.add(j);j+=1
        # For a requested detail, surrounding antecedents can be selected by the
        # model; they remain within the same local topic cluster.
        allowed=[s for i,s in enumerate(ss) if i in hits and not stems(tokens(s))&excluded]
        if allowed:
            candidates.append({'source_id':row['id'],'quote':' '.join(allowed),'sentences':allowed,
                               'text':narrate(' '.join(allowed),name(row),row['kind']),'verified':True})
    return candidates


def keywords_for_focus(question):
    from .retrieval import keywords
    return keywords(question)
