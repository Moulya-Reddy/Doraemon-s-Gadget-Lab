"""
cast.py  -  the supporting characters' brains

  followups()   Mira's "ask next" suggestions (picked from data/questions.json)
  make_quiz()   Bruno's quiz: a fill-in-the-blank built from the library itself
"""
import json
import os
import random
import re

HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(HERE, "data", "questions.json"), encoding="utf-8") as f:
    QUESTIONS = json.load(f)

TOOL_DEMOS = ["What time is it in Tokyo?", "Weather in Hyderabad", "What is 15% of 240?",
              "What time is it in London?", "Weather in Delhi", "Calculate 12 * (3 + 4)"]


def followups(asked, topic=None, tool=False, n=3):
    asked_l = asked.lower().strip(" ?!.")
    pool = []
    if tool:
        pool = TOOL_DEMOS[:]
    else:
        same = [q for q in QUESTIONS.get(topic, [])]
        random.shuffle(same)
        others = [q for t, qs in QUESTIONS.items() if t != topic for q in qs]
        random.shuffle(others)
        pool = same[:2] + others
    out = []
    for q in pool:
        if q.lower().strip(" ?!.") != asked_l and q not in out:
            out.append(q)
        if len(out) == n:
            break
    return out


_NUM = re.compile(r"\b\d[\d,]*(?:\.\d+)?\b")
_WORD = re.compile(r"\b[A-Z][a-z]{3,}\b")


def _tokens(sentence):
    """(kind, token) candidates that can be blanked out. Capitalised words at the start are skipped."""
    out = [("num", m.group()) for m in _NUM.finditer(sentence)]
    out += [("word", m.group()) for m in _WORD.finditer(sentence) if m.start() > 0]
    return out


def make_quiz(chunks, topic=None):
    """chunks: list of Chunk. Returns dict(question, options, answer, fact) or None."""
    pool = [c for c in chunks if topic is None or c.topic == topic] or chunks
    random.shuffle(pool)
    for chunk in pool:
        sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", chunk.text) if len(s.strip()) > 40]
        random.shuffle(sents)
        for s in sents:
            cands = _tokens(s)
            random.shuffle(cands)
            for kind, tok in cands:
                # distractors: same kind of token, taken from OTHER paragraphs
                others = {t for c in chunks if c is not chunk for k, t in _tokens(c.text) if k == kind and t != tok}
                if len(others) < 3:
                    continue
                options = random.sample(sorted(others), 3) + [tok]
                random.shuffle(options)
                return {"question": re.sub(r"\b" + re.escape(tok) + r"\b", "_____", s, count=1), "options": options,
                        "answer": options.index(tok), "fact": s, "topic": chunk.topic}
    return None


def make_fact(chunks, topic=None):
    """Rico's 'did you know': the opening sentence(s) of a random library paragraph."""
    pool = [c for c in chunks if topic is None or c.topic == topic] or chunks
    c = random.choice(pool)
    sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", c.text) if s.strip()]
    fact, i = "", 0
    while i < len(sents) and len(fact) < 140:
        fact = (fact + " " + sents[i]).strip()
        i += 1
    return {"topic": c.topic, "fact": fact}
