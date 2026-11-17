"""Small request parser: grammatical action requests and positive/negative scope.

No family names, source IDs, places, or answers belong in this module.
"""
from dataclasses import dataclass
import re

HUMOR = {'funny','humor','humour','humorous','amusing','amused','joke','joked','jokes','laugh','laughed','laughter','teased','teasing','comic','comical','comedy','hilarious','lighthearted','punchline'}
GENERIC = set('only just exclusively focus concentrate please anything something funny whole entire rest vacation outing account part detail details moment humorous amusing everything catching made make expedition recorded incident episode mishap adventure event'.split())


def stems(words):
    result=set()
    for word in words:
        result.add(word)
        if word.endswith('ing') and len(word)>5:
            root=word[:-3]
            if len(root)>2 and root[-1]==root[-2]:root=root[:-1]
            result.add(root)
        if word.endswith('ed') and len(word)>5:
            root=word[:-2]
            if len(root)>2 and root[-1]==root[-2]:root=root[:-1]
            result.add(root)
        if word.endswith('s') and len(word)>4:result.add(word[:-1])
    return result


@dataclass(frozen=True)
class Query:
    positive: str
    excluded: tuple[str,...]
    narrow: bool
    detail: bool
    media_action: bool


def question_text(text):
    """A preamble may mention dates/actions without asking about them."""
    clauses=re.split(r'[.!]\s+',text.strip())
    return clauses[-1] if len(clauses)>1 and clauses[-1].endswith('?') else text


def analyse(question):
    question=question_text(question)
    q=question.lower().strip()
    # Historical subjects ('Did Dad play ...?') and conversational requests
    # ('share a memory') do not request an external action from Vera.
    request=re.match(r'^(?:please\s+)?(?:(?:can|could|would|will)\s+you\s+(?:please\s+)?)?(play(?:\s+back)?|send|email|share)\b\s*(.*)',q)
    media=False
    if request:
        verb,obj=request.groups()
        media=bool(re.search(r'\b(photo|photograph|picture|image|recording|audio|cassette|video|clip|file|it|that)\b',obj))
        if verb=='email':media=True
    negative=r'(?:,\s*not\s+|\bbut\s+not\s+|\bwithout\s+|\bleave\s+out\s+|\bskip\s+|\b(?:exclude|omit)\s+|\bexcept\s+(?:for\s+)?|\b(?:do\s+not|don\x27t)\s+(?:include|mention)\s+|\brather\s+than\s+)'
    pieces=re.split(negative,question,flags=re.I)
    positive=pieces[0].strip(' ,;')
    excluded=tuple(s.strip(' ,;.?!') for s in pieces[1:] if s.strip(' ,;.?!'))
    narrow=bool(excluded or re.search(r'\b(only|just|exclusively|focus|concentrate)\b',q))
    words=set(re.findall(r'[a-z0-9]+',positive.lower()))
    detail=bool(words&HUMOR or words&{'anything','something','part','detail','moment'} or re.match(r'^what\b',positive.lower()))
    return Query(positive,excluded,narrow,detail,media)
