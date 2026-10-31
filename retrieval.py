"""Retrieval: chunk sessions into turn-level pieces, score them with BM25 + dense embeddings, rerank with a
cross-encoder."""
import json
import math
import os
import pickle
import re
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
from rank_bm25 import BM25Okapi

EMB_MODEL = "BAAI/bge-base-en-v1.5"
RERANK_MODEL = "BAAI/bge-reranker-v2-m3"
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "
CHUNK, OVERLAP = 900, 200
DEVICE = os.environ.get("MEMSYS_DEVICE", "mps")  # cpu / cuda elsewhere

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

    def __init__(self, cache_path, device=DEVICE):
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

    def ensure(self, sessions, block=1500):
        """Embeds missing sessions in blocks and saves the cache after each, so a killed run keeps its progress."""
        todo = list({s["session_id"]: s for s in sessions if s["session_id"] not in self.cache}.values())
        for b in range(0, len(todo), block):
            part = todo[b:b + block]
            texts = [text for s in part for _, _, text in session_chunks(s)]
            order = sorted(range(len(texts)), key=lambda i: len(texts[i]))  # length-sorted batches run faster
            embs = np.zeros((len(texts), 768), dtype=np.float16)
            vecs = self.model.encode([texts[i] for i in order], batch_size=64, normalize_embeddings=True)
            embs[order] = vecs.astype(np.float16)
            pos = 0
            for s in part:
                n = len(session_chunks(s))
                self.cache[s["session_id"]] = embs[pos:pos + n]
                pos += n
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".tmp")
            tmp.write_bytes(pickle.dumps(self.cache))
            tmp.replace(self.path)
            print(f"embedded {min(b + block, len(todo))}/{len(todo)} sessions", flush=True)

    def query(self, texts):
        return self.model.encode([QUERY_PREFIX + t for t in texts], normalize_embeddings=True)


_reranker = None


def reranker(device=DEVICE):
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


_NUMW = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
         "nine": 9, "ten": 10, "few": 3, "couple of": 2}
_UNIT = {"day": 1, "week": 7, "month": 30}
_MONTHS = "january february march april may june july august september october november december".split()
_AGO = re.compile(r"\b(\d+|an?|one|two|three|four|five|six|seven|eight|nine|ten) (day|week|month)s? ago\b", re.I)
_PAST = re.compile(r"\b(?:past|last) (?:(\d+|two|three|four|five|six|few|couple of) )?(day|week|month)s?\b", re.I)
_IN_MONTH = re.compile(r"\b(in|since|during|from) (?:the month of )?(" + "|".join(_MONTHS) + r")\b", re.I)


def time_window(question, today):
    """(first, last) day the question is about, from "two weeks ago", "in the past month", "in March", "since April";
    None if it names no period. Months without a year are the latest such month up to ``today``."""
    m = _AGO.search(question)
    if m:
        n = int(m.group(1)) if m.group(1).isdigit() else _NUMW[m.group(1).lower()]
        days = n * _UNIT[m.group(2).lower()]
        slack = max(3, days // 4)
        return today - timedelta(days=days + slack), today - timedelta(days=days - slack)
    m = _PAST.search(question)
    if m:
        n = 1 if not m.group(1) else int(m.group(1)) if m.group(1).isdigit() else _NUMW[m.group(1).lower()]
        return today - timedelta(days=(n + (not m.group(1))) * _UNIT[m.group(2).lower()]), today
    m = _IN_MONTH.search(question)
    if m:
        mo = _MONTHS.index(m.group(2).lower()) + 1
        first = datetime(today.year - (mo > today.month), mo, 1)
        if m.group(1).lower() in ("since", "from"):
            return first, today
        return first, datetime(first.year + (mo == 12), mo % 12 + 1, 1) - timedelta(days=1)
    return None


def _logit(p):
    p = min(max(p, 1e-7), 1 - 1e-7)
    return math.log(p / (1 - p))


MULTI = re.compile(r"\bhow (many|much)\b|\btotal\b|\bcombined\b|\bin all\b|\baltogether\b|\baverage\b|\bapart\b"
                   r"|\bbetween\b|\bfirst\b|\bmost\b|\bbefore\b|\bafter\b|\bsince\b|\border\b", re.I)


def diversify(cands, penalty=2.0, boost=(), bonus=3.0):
    """Score-sorted reranked chunks reordered by logit(score) minus `penalty` per better chunk of the same session,
    plus `bonus` for sessions in `boost`, so the evidence budget reaches more sessions (counting and two-event
    questions need several). The best chunk stays first and scores stay unchanged (sigmoid probabilities)."""
    seen, keyed = {}, []
    for c in cands:
        k = seen[c["session_id"]] = seen.get(c["session_id"], -1) + 1
        keyed.append((_logit(c["score"]) - penalty * k + bonus * (c["session_id"] in boost), c))
    return cands[:1] + [c for _, c in sorted(keyed[1:], key=lambda x: -x[0])]


def retrieve(history, question, emb, n_fuse=80, rerank=True, question_date=None, n_window=30):
    """Chunks of a history ranked for a question: list of dicts with session, turn, role, text, score.
    If the question names a period ("two weeks ago", "in March"), the best `n_window` chunks of sessions dated in it
    are reranked too; ``question_date`` defaults to the last session date."""
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
    today = datetime.strptime((question_date or max(s["date"] for s in sessions))[:10], "%Y/%m/%d")
    win = time_window(question, today)
    inwin = np.array([win[0] <= datetime.strptime(r["date"][:10], "%Y/%m/%d") <= win[1] for r in rows]) \
        if win else np.zeros(len(rows), bool)
    bm25 = BM25Okapi([tokens(r["text"]) or ["_"] for r in rows])
    qv = emb.query(queries)
    fused = np.zeros(len(rows))
    for q, v in zip(queries, qv):
        w = 1.0 if q is queries[0] else 0.5
        for scores in (bm25.get_scores(tokens(q)), vecs @ v):
            ranks = np.empty(len(rows))
            ranks[np.argsort(-scores)] = np.arange(len(rows))
            fused += w / (60 + ranks)
    top = list(np.argsort(-fused)[:n_fuse])
    seen = set(top)
    top += [i for i in np.argsort(-np.where(inwin, fused, -1))[:n_window] if inwin[i] and i not in seen]
    cands = [dict(rows[i], fused=float(fused[i])) for i in top]
    if rerank:
        pairs = [(q, f"[{c['role']}] {c['text']}") for c in cands for q in queries]
        raw = reranker().predict(pairs, batch_size=32).reshape(len(cands), len(queries))
        for c, r in zip(cands, raw):
            # the reranker returns probabilities: a sub-query match counts 0.5 logit less than a whole-question one
            best = r[0] if len(queries) == 1 else 1 / (1 + math.exp(-max(_logit(r[0]), _logit(r[1:].max()) - 0.5)))
            c["score"] = float(best)
    else:
        for c in cands:
            c["score"] = c["fused"]
    cands.sort(key=lambda c: -c["score"])
    if rerank and (win or MULTI.search(question)):
        cands = diversify(cands, 1.0, {rows[i]["session_id"] for i in top if inwin[i]}, 4.0)
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
