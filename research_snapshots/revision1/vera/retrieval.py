"""Bounded lexical retrieval with event/person scope and explicit query expansion."""
from __future__ import annotations
import json
import re
import sqlite3
from .db import get_memories
from .query import analyse, stems, HUMOR, GENERIC

STOP = {'not','only','just','whole','entire','anything','something','focus','exclusively'} | set('the a an and or but we what where when why how are was were is it i my our us you me tell about know did do does some that this there for from with at on in of to please can could would who which family story stories remember remembers memories memory again more happened after next have same trip definitely year actually mentioned recorded type longer version'.split())
# Vocabulary expansion describes concepts, never adds family facts to an answer.
CONCEPTS = (
    {'accommodation','lodging','stay','stayed','rented','rental','cottage','tent','hotel','cabin'},
    {'photo','photograph','picture','image'},
    {'audio','recording','transcript'},
    {'place','places','location','locations'},
    {'related','relationship','relationships','cousin','sibling','brother','sister','parent'},
    {'sand','sandcastle','sandcastles'},
    {'garden','gardener','gardening','planted','sunflowers'},
    HUMOR,
    {'play','played','playing','games','sand','sandcastle','sandcastles'},
)


def tokens(text):
    return set(re.findall(r'[a-z0-9]+', text.lower()))


def keywords(question: str) -> list[str]:
    return list(dict.fromkeys(t for t in re.findall(r'[a-z0-9]+', question.lower()) if len(t)>=3 and t not in STOP))[:16]


def expanded_terms(question):
    terms=set(keywords(question))
    for group in CONCEPTS:
        if terms & group:terms |= group
    return terms


def retrieve(con: sqlite3.Connection, question: str, limit: int = 8,
             previous_ids: list[int] | None = None) -> list[sqlite3.Row]:
    """Rank candidates, scope follow-ups, then expand the selected event dossier.

    Metadata is scanned locally (no schema migration); source text is fetched
    only for candidates. No archive-wide text is put into model context.
    """
    spec=analyse(question)
    question=spec.positive
    qt=tokens(question);terms=expanded_terms(question)
    records={r['memory_id']:json.loads(r['metadata']) for r in con.execute('SELECT memory_id,metadata FROM memory_details WHERE retired=0')}
    previous=get_memories(con,previous_ids or [])
    previous_people={p for r in previous for p in json.loads(r['metadata']).get('people',[])}
    previous_events={e for r in previous for e in json.loads(r['metadata']).get('events',[])}
    event_ids={e for m in records.values() for e in m.get('events',[])}
    # Shared event words (coast) cannot disambiguate similar outings.
    counts={t:sum(t in tokens(e) for e in event_ids) for e in event_ids for t in tokens(e)}
    explicit_events={e for e in event_ids if any(t in qt and counts[t]==1 for t in tokens(e))}
    comparison=bool(qt & {'same','compare','both','different','separate'})
    explicit_people={p for m in records.values() for p in m.get('people',[]) if tokens(p) <= qt}
    person_query=bool(re.search(r'(tell me|know|stories|memories).*\babout\b',question.lower())) and bool(explicit_people)
    # A complete named event takes priority over incidental shared words.
    matched={i for i,m in records.items() if explicit_events.intersection(m.get('events',[]))}
    ids=[]
    if terms:
        fts=' OR '.join('"'+t+'"' for t in sorted(terms))
        rows=con.execute('SELECT rowid FROM memories_fts WHERE memories_fts MATCH ? AND rowid NOT IN (SELECT memory_id FROM memory_details WHERE retired=1) ORDER BY bm25(memories_fts) LIMIT 64',(fts,)).fetchall()
        ids=[r['rowid'] for r in rows]
    if person_query:
        ids=list(dict.fromkeys([i for i,m in records.items() if explicit_people.intersection(m.get('people',[]))]+ids))
        # A person dossier includes linked events; unrelated lexical hits do not.
        lexical=get_memories(con,ids)
        ids=[r['id'] for r in lexical if explicit_people.intersection(records.get(r['id'],{}).get('people',[])) or any(tokens(p)<=tokens(r['content']) for p in explicit_people)]
    elif matched:
        ids=sorted(matched)
        if comparison:ids=list(dict.fromkeys(ids+[r['id'] for r in previous]))
    else:
        followup=bool(previous) and (bool(qt & {'that','they','them','it','there','his','her','those','after','next','same','year','date','accommodation','places','related','recorded','mentioned','longer','recollections'}) or question.lower().startswith(('who ', 'could ', 'what type', 'does ', 'do we ', 'was ', 'did ', 'were ', 'is ')))
        # Topic changes introduced with 'tell me about' run a fresh retrieval.
        if re.search(r'\b(tell me|know).*\babout\b',question.lower()):followup=False
        if spec.detail and previous and not stems(set(keywords(question))-GENERIC-HUMOR):
            followup=True
        person_words=set().union(*(tokens(p) for p in explicit_people)) if explicit_people else set()
        role_terms=expanded_terms(question)-person_words-GENERIC-HUMOR
        same_subject=any(role_terms & expanded_terms(r['title']+' '+r['content']) for r in previous)
        if explicit_people and not explicit_people.intersection(previous_people) and not same_subject:
            followup=False
        if followup:
            if ids or not terms or qt & {'year','date','dates','who'} or terms & {'year','date','accommodation','places','related','longer','recollections','certain','remembered','children','identified','photo','audio'}:
                ids=[r['id'] for r in previous]
    selected=get_memories(con,ids)
    if explicit_people and not matched:
        named=[r for r in selected if explicit_people.intersection(records.get(r['id'],{}).get('people',[])) or any(tokens(p)<=tokens(r['content']) for p in explicit_people)]
        if named:selected=named
    # Rank original term coverage before expansion so distractors do not crowd
    # out the query's actual subject. Stable IDs break ties reproducibly.
    base=set(keywords(question))
    selected.sort(key=lambda r:(-len(tokens(r['title']+' '+r['content']+' '+r['contributor']) & base),r['id']))
    direct=[r for r in selected if tokens(r['title']+' '+r['content']+' '+r['contributor']) & base]
    if direct and not matched and not person_query and not previous:
        selected=direct
    # Distinguish an actual activity from a source only denying it. This
    # affects fresh activity searches, not questions about a known prior event.
    anchors=stems(set(keywords(question))-GENERIC-HUMOR)
    if selected and (spec.narrow or spec.detail):
        topical=[r for r in selected if stems(tokens(r['title']+' '+r['content'])) & anchors]
        if topical:selected=topical
    if selected and (spec.narrow or spec.detail or not previous):
        affirmative=[]
        for row in selected:
            ss=re.split(r'(?<=[.!?])\s+',row['content'])
            hits=[s for s in ss if stems(tokens(s)) & anchors]
            denied=hits and all(re.search(r"\b(no one|never|did not|didn't|not)\b",s,re.I) for s in hits)
            if not denied:affirmative.append(row)
        if affirmative:selected=affirmative
    if tokens(question)&HUMOR:
        humorous=[r for r in selected if tokens(r['content'])&HUMOR]
        if humorous:selected=humorous
    seeds=[r['id'] for r in selected]
    events={e for r in selected for e in json.loads(r['metadata']).get('events',[])}
    expanded=[i for i,m in records.items() if events.intersection(m.get('events',[]))]
    # Explicit person queries must not expand into every unrelated family story.
    if person_query:expanded=[i for i in expanded if explicit_people.intersection(records[i].get('people',[]))]
    return get_memories(con,list(dict.fromkeys(seeds+expanded))[:limit])


def format_context(memories: list[sqlite3.Row]) -> str:
    return '\n\n'.join(f"SOURCE ID {m['id']}\nTitle: {m['title']}\nContributor: {m['contributor']}\nType: {m['kind']}\nOriginal media: {m['media_path'] or 'none linked'}\nMetadata: {m['metadata']}\nRecorded account: {m['content']}" for m in memories)
