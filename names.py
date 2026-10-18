"""
names.py  -  optional renaming. Edit static/cast.json ("names") to rename Pip and the friends everywhere
(UI text, dialogue, server messages, the LLM's persona). Defaults are the built-in original names.
"""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT = {"Pip": "Pip", "Kiko": "Kiko", "Mira": "Mira", "Bruno": "Bruno", "Rico": "Rico"}
try:
    with open(os.path.join(HERE, "static", "cast.json"), encoding="utf-8") as f:
        NAMES = {**DEFAULT, **json.load(f).get("names", {})}
except Exception:
    NAMES = dict(DEFAULT)
_pat = re.compile(r"\b(" + "|".join(DEFAULT) + r")\b")


def N(text, host=None):
    """Apply custom names. host: character id whose name should replace 'Pip' (the one running the gadgets)."""
    hostname = NAMES.get((host or "pip").capitalize())
    return _pat.sub(lambda m: hostname if (m.group(1) == "Pip" and host and host != "pip" and hostname)
                    else NAMES[m.group(1)], text)
