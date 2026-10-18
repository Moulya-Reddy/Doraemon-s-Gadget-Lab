"""
rag.py  -  the "pocket library" (Retrieval-Augmented Generation)

Pipeline:   documents -> chunks -> embeddings -> (question) -> top-k similar chunks

Everything here is free and runs on a Mac CPU:
  * Embedder uses sentence-transformers (all-MiniLM-L6-v2, ~90 MB, downloaded once)
  * If that is not installed it silently falls back to TF-IDF (scikit-learn)
"""
import glob
import os
import re
from dataclasses import dataclass

import numpy as np


# Words that carry no topic ("explain", "works", "make"...). Removing them stops TF-IDF
# from matching on question-phrasing instead of the real subject.
_FILLER = set("""explain tell give show summarize summary describe difference between compare vs versus
how what why when where who which does do did is are was were can could should would work works working
make made making use used using like please me my about one two many much""".split())


def _analyzer(text):
    from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS
    out = []
    for w in re.findall(r"[a-z0-9]+", text.lower()):
        if w in ENGLISH_STOP_WORDS or w in _FILLER:
            continue
        for suf in ("ing", "es", "s"):          # crude stemmer: planets -> planet
            if w.endswith(suf) and len(w) - len(suf) >= 4:
                w = w[: -len(suf)]
                break
        out.append(w)
    return out


# --------------------------------------------------------------------------- #
# 1. Embedder: text  ->  vector of numbers (so we can measure "similar meaning")
# --------------------------------------------------------------------------- #
class Embedder:
    def __init__(self):
        self.kind = "tfidf"
        self._model = None
        self._tfidf = None

        # Keep small/free hosting instances within their memory limits. The
        # neural embedder is opt-in; set EMBEDDER_BACKEND=sentence-transformers
        # and install requirements-ml.txt to enable it on a machine with enough RAM.
        backend = os.getenv("EMBEDDER_BACKEND", "tfidf").strip().lower()
        if backend not in ("sentence-transformers", "transformer", "neural"):
            print("[rag] using lightweight TF-IDF embedder")
            return

        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
            self.kind = "sentence-transformers"
        except Exception as e:  # missing dependency / network unavailable
            print(f"[rag] sentence-transformers unavailable ({type(e).__name__}); using TF-IDF fallback")

    # TF-IDF needs to see the text once to learn its vocabulary. Neural embedders don't.
    def fit(self, texts):
        if self.kind == "tfidf":
            from sklearn.feature_extraction.text import TfidfVectorizer
            self._tfidf = TfidfVectorizer(analyzer=_analyzer, sublinear_tf=True)
            self._tfidf.fit(texts)

    def encode(self, texts):
        if self.kind == "sentence-transformers":
            vecs = self._model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
            return np.asarray(vecs, dtype=np.float32)
        vecs = self._tfidf.transform(texts).toarray().astype(np.float32)
        norms = np.linalg.norm(vecs, axis=1, keepdims=True)
        return vecs / np.maximum(norms, 1e-9)  # unit length -> dot product == cosine similarity

    @property
    def min_score(self):
        """Below this top score we tell the user the pocket probably doesn't know."""
        return 0.40 if self.kind == "sentence-transformers" else 0.15


# --------------------------------------------------------------------------- #
# 2. Knowledge base: load files, chunk, index, search
# --------------------------------------------------------------------------- #
@dataclass
class Chunk:
    topic: str   # file name without .txt, e.g. "space"
    text: str
    url: str = ""


class KnowledgeBase:
    def __init__(self, folder, embedder):
        self.embedder = embedder
        self.chunks = []
        for path in sorted(glob.glob(os.path.join(folder, "*.txt"))):
            topic = os.path.splitext(os.path.basename(path))[0]
            with open(path, encoding="utf-8") as f:
                # one paragraph (blank-line separated) == one chunk.
                # Each paragraph in our files is a self-contained fact card.
                for para in re.split(r"\n\s*\n", f.read()):
                    para = para.strip()
                    if para:
                        self.chunks.append(Chunk(topic, para))
        texts = [c.text for c in self.chunks]
        embedder.fit(texts)
        self.matrix = embedder.encode(texts)   # shape: (num_chunks, dim)
        print(f"[rag] indexed {len(self.chunks)} chunks with {embedder.kind}")

    def search(self, query, k=3):
        q = self.embedder.encode([query])[0]
        scores = self.matrix @ q               # cosine similarity with every chunk
        top = np.argsort(-scores)[:k]
        return [(float(scores[i]), self.chunks[i]) for i in top]


# --------------------------------------------------------------------------- #
# 3. Wikipedia fallback (free, no key): used when the local library has no good match
# --------------------------------------------------------------------------- #
_wiki_cache = {}
_LEAD = re.compile(r"^(please\s+)?(tell me about|who (is|was|were)|what (is|are|was|were)|explain|describe|"
                   r"define|about)\s+(a |an |the )?", re.I)


def wikipedia_lookup(question):
    """Returns a Chunk with the article summary, or None. Needs internet."""
    import requests
    q = _LEAD.sub("", question.strip().rstrip("?!. "))
    if q in _wiki_cache:
        return _wiki_cache[q]
    headers = {"User-Agent": "PipsPocket/1.0 (learning project)"}
    chunk = None
    try:
        r = requests.get("https://en.wikipedia.org/w/api.php", headers=headers, timeout=8, params={
            "action": "query", "list": "search", "srsearch": q, "srlimit": 1, "format": "json"}).json()
        hits = r["query"]["search"]
        if hits:
            title = hits[0]["title"]
            s = requests.get("https://en.wikipedia.org/api/rest_v1/page/summary/" +
                             requests.utils.quote(title.replace(" ", "_"), safe=""),
                             headers=headers, timeout=8).json()
            if s.get("type") == "standard" and s.get("extract"):
                chunk = Chunk(f"Wikipedia: {s['title']}", s["extract"],
                              s.get("content_urls", {}).get("desktop", {}).get("page", ""))
    except Exception as e:
        print("[rag] wikipedia lookup failed:", type(e).__name__)
    _wiki_cache[q] = chunk
    return chunk
