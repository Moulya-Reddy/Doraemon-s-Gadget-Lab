"""
llm.py  -  turns (question + retrieved context + gadget style) into an answer

Backends (all free):
  ollama      local model on your Mac, no key, no internet needed after download
  gemini      Google AI Studio free tier (needs a free key in GEMINI_API_KEY)
  extractive  no model at all - picks the best sentences from the retrieved text
  tinygpt     the small GPT you trained yourself (fun, but only babbles)

LLM_BACKEND=auto (default) tries ollama -> gemini -> extractive.
"""
import os
import re

import requests

from names import N

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:1b")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-latest")

SYSTEM = N(
    "You are Pip, a kind, responsible pocket robot who answers questions. "
    "Use ONLY the facts in the CONTEXT below. If the context does not contain the answer, say "
    "'That is not in my pocket library yet' and give at most one short best-effort sentence. "
    "Never invent numbers or dates. Keep it under 120 words."
)


def build_prompt(question, chunks, gadget):
    ctx = "\n".join(f"[{i + 1}] {c.text}" for i, (_, c) in enumerate(chunks))
    return (f"CONTEXT:\n{ctx}\n\nFORMAT: {gadget.prompt}\n\nQUESTION: {question}\n\nANSWER:")


# ---------------------------------------------------------------- ollama ---
def ollama_alive():
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=0.6)
        return r.ok
    except requests.RequestException:
        return False


_RULES = ("Use ONLY the facts in the CONTEXT below. If the context does not contain the answer, say "
          "'That is not in my pocket library yet' and give at most one short best-effort sentence. "
          "Never invent numbers or dates. Keep it under 120 words.")


def system_for(character):
    if not character:
        return SYSTEM
    return (f"You are {character['name']}, a cartoon character who answers questions. "
            f"Tone: {character['persona']}. Keep every fact, number and date exactly as in the context. " + _RULES)


def ask_ollama(prompt, system=SYSTEM):
    r = requests.post(f"{OLLAMA_URL}/api/chat", timeout=180, json={
        "model": OLLAMA_MODEL, "stream": False,
        "options": {"temperature": 0.3, "num_predict": 300},
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
    })
    r.raise_for_status()
    return r.json()["message"]["content"].strip()


# ---------------------------------------------------------------- gemini ---
def ask_gemini(prompt, system=SYSTEM):
    key = os.environ["GEMINI_API_KEY"]
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
    r = requests.post(url, timeout=60, headers={"x-goog-api-key": key}, json={
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.3, "maxOutputTokens": 400},
    })
    r.raise_for_status()
    return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()


# ------------------------------------------------------------ extractive ---
_STOP = set("a an the is are was were of to in on and or for with what how why when where who does do did "
            "it its this that be by as at from can i you me my about tell give".split())


def _words(s):
    return {w for w in re.findall(r"[a-z0-9]+", s.lower()) if w not in _STOP}


def ask_extractive(question, chunks, gadget):
    """No-LLM fallback. Uses ONLY the best chunk (mixing chunks produced off-topic answers)
    and lays its sentences out in the gadget's style."""
    text = chunks[0][1].text
    sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
    qw = _words(question)
    ranked = sorted(range(len(sents)), key=lambda i: (-len(qw & _words(sents[i])), i))
    keep = sorted(ranked[:4])                     # most relevant sentences, back in original order
    picked = [sents[i] for i in keep] or sents[:3]
    st = gadget.style
    if st == "steps":
        return "\n".join(f"{i + 1}. {s}" for i, s in enumerate(picked))
    if st == "timeline":
        return "\n".join(f"- {s}" for s in picked)
    if st == "bullets":
        short = min(picked, key=len)
        return "\n".join(f"- {s}" for s in picked) + f"\n\n**Remember:** {short}"
    if st == "compare":
        rest = "\n".join(f"- {s}" for s in picked[1:])
        return f"**{picked[0]}**" + (f"\n\n{rest}" if rest else "")
    return " ".join(picked[:3])


# ------------------------------------------------------------- dispatcher ---
def answer(question, chunks, gadget, grounded=True, character=None):
    """Returns (text, backend_name)."""
    mode = os.getenv("LLM_BACKEND", "auto")
    prompt = build_prompt(question, chunks, gadget)

    if mode in ("auto", "ollama") and ollama_alive():
        try:
            return ask_ollama(prompt, system_for(character)), f"ollama:{OLLAMA_MODEL}"
        except Exception as e:
            print("[llm] ollama failed:", e)
    if mode in ("auto", "gemini") and os.getenv("GEMINI_API_KEY"):
        try:
            return ask_gemini(prompt, system_for(character)), f"gemini:{GEMINI_MODEL}"
        except Exception as e:
            print("[llm] gemini failed:", e)
    if mode == "tinygpt":
        try:
            from tinygpt.tiny_gpt import generate_text
            return generate_text(question, max_new_tokens=60), "tinygpt"
        except Exception as e:
            print("[llm] tinygpt failed:", e)
    if not grounded:
        return "That is not in my pocket library yet. Add a text file about it to data/knowledge/ and restart me!", "extractive"
    return ask_extractive(question, chunks, gadget), "extractive"
