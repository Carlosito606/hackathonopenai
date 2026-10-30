"""Session recall of retrieval on a dev split: python eval_retrieval.py data/dev cache/dev.pkl [n_questions]"""
import random
import sys
import time
from collections import defaultdict

from memsys import Embedder, build_evidence, load_split, mean, recall_at, retrieve, session_ranking

split, cache = sys.argv[1], sys.argv[2]
n = int(sys.argv[3]) if len(sys.argv) > 3 else 150
hist, qs, gold = load_split(split)
random.seed(0)
qs = [q for q in qs if not gold[q["question_id"]]["abstain"]]
qs = random.sample(qs, min(n, len(qs)))
emb = Embedder(cache)
t = time.time()
emb.ensure([s for q in qs for s in hist[q["history_id"]]["sessions"]])
print(f"embedded in {time.time() - t:.0f}s", flush=True)
res = defaultdict(lambda: defaultdict(list))
for q in qs:
    g = gold[q["question_id"]]
    h = hist[q["history_id"]]
    for mode in ("fused", "rerank"):
        cands = retrieve(h, q["question"], emb, rerank=mode == "rerank")
        rank = session_ranking(cands)
        passages, _ = build_evidence(h, cands, q["question_date"])
        sent = {sid for sid, _ in passages}
        for typ in (g["question_type"], "all"):
            r = res[mode, typ]
            for k in (1, 3, 5, 10):
                r[f"R@{k}"].append(recall_at(rank, g["evidence"], k))
            r["sent_recall"].append(len(sent & set(g["evidence"])) / len(g["evidence"]))
            r["sent_all"].append(float(set(g["evidence"]) <= sent))
            r["n_sent"].append(len(sent))
for (mode, typ), r in sorted(res.items()):
    print(f"{mode:7s} {typ:26s} n={len(r['R@1']):3d} " + " ".join(f"{k}={mean(v):.3f}" for k, v in r.items()))
