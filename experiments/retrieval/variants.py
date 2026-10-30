"""Offline candidate-order variants on dumped reranked candidates (eval_retrieval.py --dump), no GPU needed:
how many gold sessions end up in build_evidence's pack, per question type.

    python experiments/retrieval/variants.py ../data/dev out/cands-dev.pkl
"""
import json
import pickle
from datetime import datetime
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from memsys import build_evidence, mean, read_jsonl  # noqa: E402
from retrieval import MULTI, diversify, time_window  # noqa: E402

split, dump = Path(sys.argv[1]), pickle.loads(Path(sys.argv[2]).read_bytes())
gold = {g["question_id"]: g for g in read_jsonl(split / "gold.jsonl")}
need = {q["history_id"] for q in read_jsonl(split / "questions.jsonl") if q["question_id"] in dump}
qh = {q["question_id"]: q["history_id"] for q in read_jsonl(split / "questions.jsonl")}
qrow = {q["question_id"]: q for q in read_jsonl(split / "questions.jsonl")}


def window_sessions(cands, q):
    """Session ids of candidates dated inside the period the question names (empty if none)."""
    win = time_window(q["question"], datetime.strptime(q["question_date"][:10], "%Y/%m/%d"))
    return {c["session_id"] for c in cands if win and win[0] <= datetime.strptime(c["date"][:10], "%Y/%m/%d") <= win[1]}


hist = {}
with open(split / "histories.jsonl", encoding="utf-8") as f:
    for line in f:
        if line[:80].split('"history_id": "', 1)[-1][:14] in need:
            h = json.loads(line)
            hist[h["history_id"]] = h

variants = {"base": lambda c, q: c}
for pen in (0.5, 1.0, 2.0):
    variants[f"div{pen:g}"] = lambda c, q, pen=pen: diversify(c, pen)
    variants[f"multi-div{pen:g}"] = lambda c, q, pen=pen: diversify(c, pen) if MULTI.search(q["question"]) else c
for bonus in (2.0, 4.0, 8.0):
    variants[f"win{bonus:g}"] = lambda c, q, bonus=bonus: diversify(c, 0.0, window_sessions(c, q), bonus)
    variants[f"win{bonus:g}-div1"] = lambda c, q, bonus=bonus: diversify(c, 1.0, window_sessions(c, q), bonus)
variants["final"] = lambda c, q: (diversify(c, 1.0, window_sessions(c, q), 4.0) if window_sessions(c, q)
                                  or MULTI.search(q["question"]) else c)
if len(sys.argv) > 3:
    variants = {k: variants[k] for k in sys.argv[3].split(",")}
for name, f in variants.items():
    res = defaultdict(lambda: defaultdict(list))
    for qid, cands in dump.items():
        g = gold[qid]
        ev = build_evidence(hist[qh[qid]], f(sorted([dict(c) for c in cands], key=lambda c: -c["score"]), qrow[qid]))
        sent = {e["id"] for e in ev}
        for typ in (g["question_type"], "all"):
            r = res[typ]
            r["sent_recall"].append(len(sent & set(g["evidence"])) / len(g["evidence"]))
            r["multi"].append(float(bool(MULTI.search(qrow[qid]["question"]))))
            r["window"].append(float(bool(time_window(qrow[qid]["question"], datetime(2030, 1, 1)))))
            r["sent_all"].append(float(set(g["evidence"]) <= sent))
            r["n_sent"].append(len(sent))
            r["chars"].append(sum(len(e["text"]) for e in ev))
            r["gold_chars"].append(sum(len(e["text"]) for e in ev if e["id"] in g["evidence"]))
    for typ, r in sorted(res.items()):
        print(f"{name:13s} {typ:26s} n={len(r['sent_all']):3d} " + " ".join(f"{k}={mean(v):.3f}" for k, v in r.items()))
