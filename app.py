"""
app.py  -  the web server. Run:  python app.py   then open http://localhost:8000
"""
import os

from flask import Flask, jsonify, request, send_from_directory

import gadgets
import llm
import tools
import cast
import characters
from names import N
from rag import Embedder, KnowledgeBase, wikipedia_lookup

HERE = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, static_folder=os.path.join(HERE, "static"))

# ---- start-up: build the library and the gadget index once ----------------
embedder = Embedder()
kb = KnowledgeBase(os.path.join(HERE, "data", "knowledge"), embedder)
gadgets.prepare(embedder)


@app.get("/")
def home():
    return send_from_directory(app.static_folder, "index.html")


@app.get("/api/art")
def art():
    """Lists custom artwork you dropped into static/characters and static/gadgets (see README)."""
    out = {}
    for kind in ("characters", "gadgets"):
        d = os.path.join(app.static_folder, kind)
        out[kind] = ({os.path.splitext(f)[0]: f for f in os.listdir(d)
                      if f.lower().endswith((".png", ".webp", ".svg", ".gif", ".jpg", ".html"))} if os.path.isdir(d) else {})
    return jsonify(out)


@app.get("/api/sounds")
def sounds():
    """Optional real recordings in static/sounds/ (rustle, pull, gadget, bell, pop, blip, correct, wrong)."""
    d = os.path.join(app.static_folder, "sounds")
    return jsonify([f for f in sorted(os.listdir(d)) if f.lower().endswith((".mp3", ".wav", ".ogg"))] if os.path.isdir(d) else [])


@app.get("/api/quiz")
def quiz():
    q = cast.make_quiz(kb.chunks, request.args.get("topic") or None) or cast.make_quiz(kb.chunks)
    return jsonify(q or {"error": "No quiz available."})


@app.get("/api/fact")
def fact():
    return jsonify(cast.make_fact(kb.chunks, request.args.get("topic") or None))


@app.get("/api/characters")
def list_characters():
    return jsonify(characters.public())


@app.get("/api/health")
def health():
    return jsonify(embedder=embedder.kind, chunks=len(kb.chunks), ollama=llm.ollama_alive())


@app.post("/api/ask")
def ask():
    body = request.get_json(silent=True) or {}
    question = body.get("question", "").strip()
    force = body.get("force")
    cid = body.get("character") if body.get("character") in characters.CHARACTERS else "pip"
    if not question:
        return jsonify(error="Type a question first."), 400
    question = question[:400]

    gadget, why = gadgets.pick_gadget(question, embedder)            # 1. choose the gadget
    if force in gadgets.BY_ID and not gadgets.BY_ID[force].tool:      #    (a friend can ask for a specific one)
        gadget, why = gadgets.BY_ID[force], f"You asked for the {gadgets.BY_ID[force].name}, so Pip pulled it out."
    meta = {"id": gadget.id, "name": gadget.name, "tagline": gadget.tagline, "style": gadget.style}

    if gadget.tool:                                                   # 2a. live gadget: compute the answer
        text, via = tools.run(gadget.tool, question)
        return jsonify(gadget=meta, why=N(why, cid), answer=text, grounded=True, backend="live tool", via=via, sources=[],
                       followups=cast.followups(question, tool=True), character=cid, **characters.voice(cid, True))

    hits = kb.search(question, k=3)                                   # 2b. library gadget: retrieve context
    grounded = hits[0][0] >= embedder.min_score
    via = "pocket library"
    if not grounded and os.getenv("WEB_FALLBACK", "on") != "off":     # nothing close? ask Wikipedia
        wc = wikipedia_lookup(question)
        if wc:
            hits, grounded, via = [(1.0, wc)], True, "Wikipedia"
    text, backend = llm.answer(question, hits, gadget, grounded, characters.persona(cid))      # 3. write the answer
    topic = hits[0][1].topic if via == "pocket library" else None
    return jsonify(
        gadget=meta, why=N(why, cid), answer=text, grounded=grounded, backend=backend, via=via, topic=topic,
        followups=cast.followups(question, topic), character=cid, **characters.voice(cid, grounded),
        sources=[{"topic": c.topic, "score": round(s, 2), "text": c.text, "url": c.url} for s, c in hits] if grounded else [],
    )


# ---- Google Search Console Verification Route ----
@app.route('/google07aef1322a4299b9.html')
def google_verify():
    return "google-site-verification: google07aef1322a4299b9.html"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8000)), debug=False)
