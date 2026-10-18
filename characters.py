"""
characters.py  -  who they are and how they talk

Each character has a personality ("persona", used as a tone hint for the LLM) and canned lines the page shows
around the answer: greet / thinking / intro (before the answer) / outro (after) / notfound.
The FACTS never change with the voice: the answer card always shows the same text.
Names go through names.N(), so renaming in static/cast.json applies here too.
"""
import random

from names import N

CHARACTERS = {
    "pip": dict(
        name="Pip", trait="kind",
        persona="kind, responsible and sensible; a little anxious when unsure",
        greet="Hi, I'm Pip! What do you want to know?",
        thinking="Hmm… let me look in my pouch!",
        intro=["Here you go!", "Found just the right gadget!", "Got it!"],
        outro=["I hope that helps! Ask me anything else.", "Let me know if you need anything more."],
        notfound="Oh no, oh no! It's not in my pocket! I'm so sorry!"),
}


def get(cid):
    return CHARACTERS.get(cid) or CHARACTERS["pip"]


def public():
    return [dict(id=k, name=N(c["name"]), trait=c["trait"], greet=N(c["greet"]), thinking=N(c["thinking"]))
            for k, c in CHARACTERS.items()]


def voice(cid, grounded=True):
    """Lines the page shows around the answer."""
    c = get(cid)
    return dict(intro=N(random.choice(c["intro"])),
                outro=N(random.choice(c["outro"])) if grounded else N(c["notfound"]))


def persona(cid):
    c = get(cid)
    return dict(name=N(c["name"]), persona=c["persona"])
