"""Session recall of retrieval on a dev split, per question type, holdout excluded:

    python eval_retrieval.py ../data/dev ../cache/dev.pkl [n_questions] [--details out.jsonl]

dev-large shares dev's questions under other ids, so holdout questions are matched by id or by question text
(texts from --holdout-questions, default ../data/dev/questions.jsonl). Only the needed histories are loaded.
"""
import argparse
import inspect
import json
import pickle
import random
import time
from collections import defaultdict
from pathlib import Path

from memsys import Embedder, build_evidence, mean, read_jsonl, recall_at, retrieve, session_ranking

ap = argparse.ArgumentParser()
ap.add_argument("split")
ap.add_argument("cache")
ap.add_argument("n", nargs="?", type=int, default=150)
ap.add_argument("--holdout", default=Path(__file__).parent / "splits/dev_holdout.txt")
ap.add_argument("--holdout-questions", default="../data/dev/questions.jsonl")
ap.add_argument("--types", help="comma-separated question types to keep")
ap.add_argument("--ids", help="file with the question ids to evaluate (e.g. from experiments/retrieval/pick_cached.py)")
ap.add_argument("--fused", action="store_true", help="also report BM25 + dense without the reranker")
ap.add_argument("--details", help="per-question jsonl: gold sessions, their rank, sent or not, best score")
ap.add_argument("--dump", help="pickle of the reranked candidates per question id, for offline packing experiments")
args = ap.parse_args()

split = Path(args.split)
qs = read_jsonl(split / "questions.jsonl")
gold = {g["question_id"]: g for g in read_jsonl(split / "gold.jsonl")}
held = set(Path(args.holdout).read_text().split())
held_text = {q["question"] for q in read_jsonl(args.holdout_questions) if q["question_id"] in held}
qs = [q for q in qs if q["question_id"] not in held and q["question"] not in held_text
      and not gold[q["question_id"]]["abstain"]
      and (not args.types or gold[q["question_id"]]["question_type"] in args.types.split(","))
      and (not args.ids or q["question_id"] in set(Path(args.ids).read_text().split()))]
random.seed(0)
qs = random.sample(qs, min(args.n, len(qs)))
need = {q["history_id"] for q in qs}
hist = {}
with open(split / "histories.jsonl", encoding="utf-8") as f:
    for line in f:
        if line[:80].split('"history_id": "', 1)[-1][:14] in need:
            h = json.loads(line)
            hist[h["history_id"]] = h
print(f"{len(qs)} questions, {len(hist)} histories", flush=True)
emb = Embedder(args.cache)
t = time.time()
emb.ensure([s for q in qs for s in hist[q["history_id"]]["sessions"]])
print(f"embedded in {time.time() - t:.0f}s", flush=True)
res = defaultdict(lambda: defaultdict(list))
kw = {}
details = open(args.details, "w") if args.details else None
dump = {}
for q in qs:
    if "question_date" in inspect.signature(retrieve).parameters:
        kw = {"question_date": q["question_date"]}
    g = gold[q["question_id"]]
    h = hist[q["history_id"]]
    for mode in ("fused", "rerank") if args.fused else ("rerank",):
        cands = retrieve(h, q["question"], emb, rerank=mode == "rerank", **kw)
        rank = session_ranking(cands)
        sent = {e["id"] for e in build_evidence(h, cands)}
        for typ in (g["question_type"], "all"):
            r = res[mode, typ]
            for k in (1, 3, 5, 10):
                r[f"R@{k}"].append(recall_at(rank, g["evidence"], k))
            r["sent_recall"].append(len(sent & set(g["evidence"])) / len(g["evidence"]))
            r["sent_all"].append(float(set(g["evidence"]) <= sent))
            r["n_sent"].append(len(sent))
        if mode == "rerank":
            dump[q["question_id"]] = cands
        if details and mode == "rerank":
            details.write(json.dumps({"question_id": q["question_id"], "type": g["question_type"],
                                      "question": q["question"], "n_sessions": len(h["sessions"]),
                                      "n_sent": len(sent),
                                      "gold": {s: [rank.index(s) if s in rank else None, s in sent,
                                                   next((round(c["score"], 2) for c in cands
                                                         if c["session_id"] == s), None)]
                                               for s in g["evidence"]}}) + "\n")
if args.dump:
    Path(args.dump).write_bytes(pickle.dumps(dump))
for (mode, typ), r in sorted(res.items()):
    print(f"{mode:7s} {typ:26s} n={len(r['R@1']):3d} " + " ".join(f"{k}={mean(v):.3f}" for k, v in r.items()))
