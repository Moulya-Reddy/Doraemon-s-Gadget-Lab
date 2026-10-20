
"""
app.py - the web server.
Run: python app.py
Then open http://localhost:8000
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

app = Flask(
    __name__,
    static_folder=os.path.join(HERE, "static")
)

# ---- Start-up: build the library and gadget index once ----------------
embedder = Embedder()
kb = KnowledgeBase(
    os.path.join(HERE, "data", "knowledge"),
    embedder
)
gadgets.prepare(embedder)


# ---- Homepage ---------------------------------------------------------
@app.get("/")
def home():
    return send_from_directory(app.static_folder, "index.html")


# ---- Google Search Console Verification ------------------------------
# IMPORTANT:
# Place Google's original verification HTML file in the same directory
# as this app.py file. Do not modify the downloaded file's contents.
#
# Expected file:
# google07aef1322a4299b9.html

@app.get("/google07aef1322a4299b9.html")
# ---- XML Sitemap for Google Search -------------------------------
@app.get("/sitemap.xml")
def sitemap():
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url>
        <loc>https://doraemons-gadget-lab.onrender.com/</loc>
    </url>
</urlset>
"""
    return app.response_class(
        response=xml,
        status=200,
        mimetype="application/xml"
    )
    
def google_verify():
    verification_file = "google07aef1322a4299b9.html"

    return send_from_directory(
        HERE,
        verification_file
    )


# ---- Artwork ----------------------------------------------------------
@app.get("/api/art")
def art():
    """Lists custom artwork in static/characters and static/gadgets."""
    out = {}

    for kind in ("characters", "gadgets"):
        directory = os.path.join(app.static_folder, kind)

        if os.path.isdir(directory):
            out[kind] = {
                os.path.splitext(filename)[0]: filename
                for filename in os.listdir(directory)
                if filename.lower().endswith(
                    (".png", ".webp", ".svg", ".gif", ".jpg", ".html")
                )
            }
        else:
            out[kind] = {}

    return jsonify(out)


# ---- Sounds -----------------------------------------------------------
@app.get("/api/sounds")
def sounds():
    """Lists optional audio recordings in static/sounds."""
    directory = os.path.join(app.static_folder, "sounds")

    if os.path.isdir(directory):
        files = [
            filename
            for filename in sorted(os.listdir(directory))
            if filename.lower().endswith((".mp3", ".wav", ".ogg"))
        ]
    else:
        files = []

    return jsonify(files)


# ---- Quiz -------------------------------------------------------------
@app.get("/api/quiz")
def quiz():
    question = request.args.get("topic") or None

    result = (
        cast.make_quiz(kb.chunks, question)
        or cast.make_quiz(kb.chunks)
    )

    return jsonify(result or {"error": "No quiz available."})


# ---- Fact -------------------------------------------------------------
@app.get("/api/fact")
def fact():
    return jsonify(
        cast.make_fact(
            kb.chunks,
            request.args.get("topic") or None
        )
    )


# ---- Characters -------------------------------------------------------
@app.get("/api/characters")
def list_characters():
    return jsonify(characters.public())


# ---- Health -----------------------------------------------------------
@app.get("/api/health")
def health():
    return jsonify(
        embedder=embedder.kind,
        chunks=len(kb.chunks),
        ollama=llm.ollama_alive()
    )


# ---- Ask Pip ----------------------------------------------------------
@app.post("/api/ask")
def ask():
    body = request.get_json(silent=True) or {}

    question = body.get("question", "").strip()
    force = body.get("force")

    cid = (
        body.get("character")
        if body.get("character") in characters.CHARACTERS
        else "pip"
    )

    if not question:
        return jsonify(error="Type a question first."), 400

    question = question[:400]

    # 1. Choose a gadget
    gadget, why = gadgets.pick_gadget(question, embedder)

    if force in gadgets.BY_ID and not gadgets.BY_ID[force].tool:
        gadget = gadgets.BY_ID[force]
        why = (
            f"You asked for the {gadgets.BY_ID[force].name}, "
            "so Pip pulled it out."
        )

    meta = {
        "id": gadget.id,
        "name": gadget.name,
        "tagline": gadget.tagline,
        "style": gadget.style
    }

    # 2a. Live gadget: compute the answer
    if gadget.tool:
        text, via = tools.run(gadget.tool, question)

        return jsonify(
            gadget=meta,
            why=N(why, cid),
            answer=text,
            grounded=True,
            backend="live tool",
            via=via,
            sources=[],
            followups=cast.followups(question, tool=True),
            character=cid,
            **characters.voice(cid, True)
        )

    # 2b. Library gadget: retrieve context
    hits = kb.search(question, k=3)
    grounded = hits[0][0] >= embedder.min_score
    via = "pocket library"

    # Use Wikipedia if no relevant library result is found
    if not grounded and os.getenv("WEB_FALLBACK", "on") != "off":
        wikipedia_context = wikipedia_lookup(question)

        if wikipedia_context:
            hits = [(1.0, wikipedia_context)]
            grounded = True
            via = "Wikipedia"

    # 3. Generate the answer
    answer_text, backend = llm.answer(
        question,
        hits,
        gadget,
        grounded,
        characters.persona(cid)
    )

    topic = (
        hits[0][1].topic
        if via == "pocket library"
        else None
    )

    return jsonify(
        gadget=meta,
        why=N(why, cid),
        answer=answer_text,
        grounded=grounded,
        backend=backend,
        via=via,
        topic=topic,
        followups=cast.followups(question, topic),
        character=cid,
        **characters.voice(cid, grounded),
        sources=[
            {
                "topic": chunk.topic,
                "score": round(score, 2),
                "text": chunk.text,
                "url": chunk.url
            }
            for score, chunk in hits
        ] if grounded else []
    )


# ---- Run the application ---------------------------------------------
if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        debug=False
    )
