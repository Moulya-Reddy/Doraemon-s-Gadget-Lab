"""
gadgets.py  -  Pip's gadget drawer

Each gadget has:
  purpose   what it is for (embedded, used for semantic routing)
  reason    short phrase shown to the user: "Pip chose X because your question <reason>"
  patterns  regexes that nudge the router toward this gadget
  hard      regexes that FORCE this gadget (used by the live-tool gadgets)
  tool      None for library gadgets, or "time" / "weather" / "calc" for live gadgets (see tools.py)
  style     answer layout, prompt = formatting instruction for the LLM
"""
import re
from dataclasses import dataclass, field

import numpy as np

from names import N


@dataclass
class Gadget:
    id: str
    name: str
    tagline: str
    purpose: str
    reason: str
    style: str
    prompt: str
    patterns: list = field(default_factory=list)
    hard: list = field(default_factory=list)
    tool: str = None
    vec: np.ndarray = None


GADGETS = [
    # ------------------------------------------------------------ live tools
    Gadget(
        id="pocket_watch", name="Pocket Watch", tagline="Tick tock, checking the clock!",
        purpose="Asks for the current time or today's date, in a city or country.",
        reason="asks for the current time or date", style="paragraph", prompt="", tool="time",
        hard=[r"\bwhat('?s| is) the (current )?(time|date)\b", r"\btime (is it|now)\b", r"\bcurrent (time|date)\b",
              r"\btime in\b", r"\bwhat (day|date) is (it|today)\b", r"\btoday'?s date\b", r"\bwhat time\b"],
    ),
    Gadget(
        id="weather_vane", name="Weather Vane", tagline="Spin, spin... the sky says:",
        purpose="Asks about the weather, temperature or forecast of a place right now.",
        reason="asks about the weather", style="bullets", prompt="", tool="weather",
        hard=[r"\bweather\b", r"\bforecast\b", r"\b(temperature|raining|rain) (in|at|now|today)\b",
              r"\bhow (hot|cold) is it\b"],
    ),
    Gadget(
        id="calc_cube", name="Calc Cube", tagline="Crunch, crunch... done!",
        purpose="Asks to calculate a sum, percentage or arithmetic expression.",
        reason="needs a calculation", style="paragraph", prompt="", tool="calc",
        hard=[r"\d\s*[\+\-\*/x×÷^]\s*\d", r"\d\s*%\s*of\s*\d", r"\b(calculate|compute|square root of|sqrt)\b"],
    ),
    # ------------------------------------------------------- library gadgets
    Gadget(
        id="portal_door", name="Portal Door", tagline="One step through and we're there!",
        purpose="Questions about places, locations, geography, countries, cities, mountains, rivers, "
                "travel and where something is.",
        reason="is about a place or where something is", style="paragraph",
        prompt="Answer like a quick virtual trip: say where it is first, then 2-3 vivid facts about the place.",
        patterns=[r"\bwhere\b", r"\blocat(ed|ion)\b", r"\bcapital\b",
                  r"\b(country|city|mountain|river|desert|ocean|continent)\b", r"\bvisit|travel\b"],
    ),
    Gadget(
        id="rewind_cloth", name="Rewind Cloth", tagline="Let's rewind time and see what happened!",
        purpose="Questions about history, the past, origins, when something happened, who invented or "
                "founded something, and timelines of events.",
        reason="is about the past or when something happened", style="timeline",
        prompt="Answer as a short timeline in chronological order. Start each bullet with the year or period.",
        patterns=[r"\bhistory\b", r"\bwhen (did|was|were)\b", r"\bwho (invented|discovered|built|founded|started)\b",
                  r"\b(ago|origin|timeline|ancient|century|war|independence|empire)\b", r"\bbegan|started\b"],
    ),
    Gadget(
        id="recall_toast", name="Recall Toast", tagline="Press it on the page and you'll never forget it!",
        purpose="Requests to summarize, memorize, revise, study, list key points or give a definition.",
        reason="asks for a summary, key points or a definition", style="bullets",
        prompt="Give 3-5 short key points someone could memorize, then one line starting with 'Remember:'.",
        patterns=[r"\bsummar", r"\bkey points?\b", r"\bremember|memori[sz]e|revise|revision|study|notes\b",
                  r"\bdefin(e|ition)\b|\bmeaning of\b"],
    ),
    Gadget(
        id="shrink_light", name="Shrink Light", tagline="Zap! Big idea, tiny size.",
        purpose="Explain a complicated idea in a simple way, like for a child; how or why something works, "
                "science concepts, ELI5.",
        reason="asks how or why something works", style="simple",
        prompt="Explain it very simply in 3-4 short sentences, using one everyday comparison. No jargon.",
        patterns=[r"\bexplain\b", r"\bsimpl(e|y)|eli5|easy|kid|child|beginner\b",
                  r"\bhow (does|do|is|are) .* (work|made|form)", r"\bwhy\b"],
    ),
    Gadget(
        id="propeller_cap", name="Sky Propeller", tagline="Hop on, here's the way up!",
        purpose="How-to questions: step by step instructions, recipes, cooking, building, installing, "
                "setting up or fixing something.",
        reason="asks how to do something step by step", style="steps",
        prompt="Give clear numbered steps (max 7). One action per step. Mention any quantities from the context.",
        patterns=[r"\bhow (to|do i|can i|do you|should i)\b", r"\bsteps?\b", r"\brecipe\b",
                  r"\b(make|cook|bake|build|install|create|set ?up|fix|brew)\b"],
    ),
    Gadget(
        id="fact_scanner", name="Fact Scanner", tagline="Scanning... got the facts!",
        purpose="Quick factual lookups, numbers, comparisons, differences between things, who or what or how "
                "many, and general questions.",
        reason="needs quick facts or a comparison", style="compare",
        prompt="Answer directly in the first sentence, then give 2-4 bullet facts. If two things are compared, "
               "give one bullet per difference.",
        patterns=[r"\bcompar|differen(ce|t)|versus|\bvs\b", r"\bhow (many|much|tall|big|far|long|old|high|deep)\b",
                  r"\blist\b", r"\bwho\b", r"\bfacts?\b"],
    ),
]
DEFAULT_GADGET = "fact_scanner"
BY_ID = {g.id: g for g in GADGETS}


def prepare(embedder):
    """Embed each gadget's purpose once, at server start-up."""
    for g, v in zip(GADGETS, embedder.encode([g.purpose for g in GADGETS])):
        g.vec = v


def _why(g):
    return f"Pip chose the {g.name} because your question {g.reason}."


def pick_gadget(question, embedder):
    # 1. live-tool gadgets win outright when their patterns match
    for g in GADGETS:
        if g.hard and any(re.search(p, question, re.I) for p in g.hard):
            return g, _why(g)
    # 2. otherwise: semantic similarity + keyword bonus
    q = embedder.encode([question])[0]
    best, best_score = BY_ID[DEFAULT_GADGET], -1.0
    for g in GADGETS:
        if g.tool:
            continue
        hits = sum(1 for p in g.patterns if re.search(p, question, re.I))
        score = float(q @ g.vec) + 0.35 * min(hits, 2)
        if score > best_score:
            best, best_score = g, score
    if best_score < 0.12:
        best = BY_ID[DEFAULT_GADGET]
    return best, _why(best)
