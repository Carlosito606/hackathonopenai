"""Retrieval: chunk sessions into turn-level pieces, score them with BM25 + dense embeddings, rerank with a
cross-encoder."""
import json
import math
import pickle
import re
from pathlib import Path

import numpy as np
from rank_bm25 import BM25Okapi

EMB_MODEL = "BAAI/bge-base-en-v1.5"
RERANK_MODEL = "BAAI/bge-reranker-v2-m3"
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "
CHUNK, OVERLAP = 900, 200

STOP = set("""a an the and or but if of to in on at for with from by about as is are was were be been being am do does did
have has had i me my mine we our you your yours he she it its they them their this that these those what which who whom
whose when where why how there here than then so too very can could would should will shall may might must not no
just also any some all each other into over after before up down out off again once ever now any much many more most
tell told remember recall name named called""".split())


def read_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def load_split(d):
    d = Path(d)
    hist = {h["history_id"]: h for h in read_jsonl(d / "histories.jsonl")}
    qs = read_jsonl(d / "questions.jsonl")
    gold = {g["question_id"]: g for g in read_jsonl(d / "gold.jsonl")} if (d / "gold.jsonl").exists() else {}
    return hist, qs, gold


def split_text(text):
    """Windows of about CHUNK chars with OVERLAP, cut at whitespace."""
    if len(text) <= CHUNK + OVERLAP:
        return [text]
    out, start = [], 0
    while start < len(text):
        end = min(len(text), start + CHUNK)
        if end < len(text):
            sp = text.rfind(" ", start + CHUNK // 2, end)
            end = sp if sp > 0 else end
        out.append(text[start:end])
        if end >= len(text):
            break
        start = max(end - OVERLAP, start + 1)
    return out


def session_chunks(session):
    """(turn_index, role, text) pieces of a session."""
    return [(i, t["role"], piece) for i, t in enumerate(session["turns"]) for piece in split_text(t["content"])]


def tokens(text):
    out = []
    for w in re.findall(r"[a-z0-9]+(?:'[a-z]+)?", text.lower()):
        w = w.split("'")[0]
        if w in STOP or len(w) < 2:
            continue
        for suf in ("ing", "ed", "es", "s"):
            if len(w) > len(suf) + 3 and w.endswith(suf):
                w = w[: -len(suf)]
                break
        out.append(w)
    return out


class Embedder:
    """Session-id keyed cache of chunk embeddings (a session id always names the same content)."""

    def __init__(self, cache_path, device="mps"):
        self.path = Path(cache_path)
        self.cache = pickle.loads(self.path.read_bytes()) if self.path.exists() else {}
        self.device = device
        self._model = None

    @property
    def model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(EMB_MODEL, device=self.device)
        return self._model

    def ensure(self, sessions):
        todo = [s for s in sessions if s["session_id"] not in self.cache]
        if not todo:
            return
        texts, owners = [], []
        for s in todo:
            for _, _, text in session_chunks(s):
                texts.append(text)
                owners.append(s["session_id"])
        order = sorted(range(len(texts)), key=lambda i: len(texts[i]))  # length-sorted batches run faster
        embs = np.zeros((len(texts), 768), dtype=np.float16)
        vecs = self.model.encode([texts[i] for i in order], batch_size=64, normalize_embeddings=True)
        embs[order] = vecs.astype(np.float16)
        pos = 0
        for s in todo:
            n = len(session_chunks(s))
            self.cache[s["session_id"]] = embs[pos:pos + n]
            pos += n
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_bytes(pickle.dumps(self.cache))

    def query(self, texts):
        return self.model.encode([QUERY_PREFIX + t for t in texts], normalize_embeddings=True)


_reranker = None


def reranker(device="mps"):
    global _reranker
    if _reranker is None:
        from sentence_transformers import CrossEncoder
        _reranker = CrossEncoder(RERANK_MODEL, device=device, max_length=512)
    return _reranker


def sub_queries(question):
    """The whole question plus each side of a two-event question, so both events get retrieved."""
    q = question.strip()
    m = re.search(r"(?:between|apart were|after|before) (.+?) (?:and|did|was|were|is) (.+?)[?.]", q, re.I)
    parts = [q]
    if m and re.search(r"how (many|long)|which .* first|order", q, re.I):
        parts += [m.group(1), m.group(2)]
    return parts


def retrieve(history, question, emb, n_fuse=80, rerank=True):
    """Chunks of a history ranked for a question: list of dicts with session, turn, role, text, score."""
    sessions = history["sessions"]
    emb.ensure(sessions)
    rows, vecs = [], []
    for si, s in enumerate(sessions):
        for (ti, role, text), v in zip(session_chunks(s), emb.cache[s["session_id"]]):
            rows.append({"si": si, "session_id": s["session_id"], "date": s["date"], "turn": ti, "role": role,
                         "text": text})
            vecs.append(v)
    vecs = np.asarray(vecs, dtype=np.float32)
    queries = sub_queries(question)
    bm25 = BM25Okapi([tokens(r["text"]) or ["_"] for r in rows])
    qv = emb.query(queries)
    fused = np.zeros(len(rows))
    for q, v in zip(queries, qv):
        w = 1.0 if q is queries[0] else 0.5
        for scores in (bm25.get_scores(tokens(q)), vecs @ v):
            ranks = np.empty(len(rows))
            ranks[np.argsort(-scores)] = np.arange(len(rows))
            fused += w / (60 + ranks)
    top = np.argsort(-fused)[:n_fuse]
    cands = [dict(rows[i], fused=float(fused[i])) for i in top]
    if rerank:
        pairs = [(q, f"[{c['role']}] {c['text']}") for c in cands for q in queries]
        raw = reranker().predict(pairs, batch_size=32).reshape(len(cands), len(queries))
        for c, r in zip(cands, raw):
            c["score"] = float(max(r[0], r[1:].max() - 0.5) if len(queries) > 1 else r[0])
    else:
        for c in cands:
            c["score"] = c["fused"]
    cands.sort(key=lambda c: -c["score"])
    return cands


def session_ranking(cands):
    best = {}
    for c in cands:
        best.setdefault(c["session_id"], c["score"])
    return sorted(best, key=lambda s: -best[s])


def recall_at(ranking, evidence, k):
    if not evidence:
        return None
    return len(set(ranking[:k]) & set(evidence)) / len(evidence)


def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else math.nan
