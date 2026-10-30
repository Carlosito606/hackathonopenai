"""Same retrieval, two evidence builders: gold sessions in the pack and pack size, per question type.

    python experiments/r1/compare_evidence.py ../data/dev ../cache/dev.pkl OLD_EVIDENCE.py [--n 150]

Dev questions without the holdout, answerable only, stratified sample (seed 0). OLD_EVIDENCE.py is an earlier
evidence.py (e.g. from git show <sha>:evidence.py); the current one is imported from the repo root.
"""
import argparse
import importlib.util
import random
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from dates import TEMPORAL  # noqa: E402
from evidence import build_evidence  # noqa: E402
from retrieval import Embedder, load_split, retrieve  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("split")
ap.add_argument("cache")
ap.add_argument("old")
ap.add_argument("--n", type=int, default=150)
args = ap.parse_args()
spec = importlib.util.spec_from_file_location("evidence_old", args.old)
old = importlib.util.module_from_spec(spec)
spec.loader.exec_module(old)

hist, qs, gold = load_split(args.split)
hold = set((ROOT / "splits" / "dev_holdout.txt").read_text().split())
by_type = defaultdict(list)
for q in qs:
    g = gold[q["question_id"]]
    if q["question_id"] not in hold and not g["abstain"]:
        by_type[g["question_type"]].append(q)
random.seed(0)
per = args.n // len(by_type)
sample = [q for t in sorted(by_type) for q in random.sample(by_type[t], min(per, len(by_type[t])))]
emb = Embedder(args.cache)
res = defaultdict(lambda: defaultdict(list))
for q in sample:
    h, g = hist[q["history_id"]], gold[q["question_id"]]
    cands = retrieve(h, q["question"], emb)
    dates = bool(TEMPORAL.search(q["question"]))
    for name, fn in (("old", old.build_evidence), ("new", build_evidence)):
        ev = fn(h, cands, dates=dates)
        for t in (g["question_type"], "all"):
            r = res[name, t]
            r["all_gold"].append(set(g["evidence"]) <= {e["id"] for e in ev})
            r["sessions"].append(len(ev))
            r["chars"].append(sum(len(e["text"]) for e in ev))
for (name, t), r in sorted(res.items(), key=lambda x: (x[0][1], x[0][0])):
    print(f"{t:26s} {name}  n={len(r['all_gold']):3d}  all_gold={sum(r['all_gold']) / len(r['all_gold']):.3f}  "
          f"sessions={sum(r['sessions']) / len(r['sessions']):.1f}  chars={sum(r['chars']) / len(r['chars']):.0f}")
