"""Evidence budget for counting questions: gold sessions in the pack at two budgets, per question type.

    python experiments/r1/compare_budget.py ../data/dev_hard ../cache/dev-poligon.pkl --budgets 18000 24000

Answerable questions without the dev holdout whose text matches prepare.COUNTING (durations excluded), same
retrieval for both budgets.
"""
import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from dates import TEMPORAL  # noqa: E402
from evidence import build_evidence  # noqa: E402
from prepare import COUNTING  # noqa: E402
from retrieval import Embedder, load_split, retrieve  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("split")
ap.add_argument("cache")
ap.add_argument("--budgets", type=int, nargs="+", default=[18000, 24000])
args = ap.parse_args()
hist, qs, gold = load_split(args.split)
hold = set((ROOT / "splits" / "dev_holdout.txt").read_text().split())
qs = [q for q in qs if q["question_id"] not in hold and not gold[q["question_id"]]["abstain"]
      and COUNTING.search(q["question"]) and not re.search(r"how many (days|weeks|months|years)", q["question"], re.I)]
emb = Embedder(args.cache)
res = defaultdict(lambda: defaultdict(list))
for q in qs:
    h, g = hist[q["history_id"]], gold[q["question_id"]]
    cands = retrieve(h, q["question"], emb)
    for b in args.budgets:
        ev = build_evidence(h, cands, budget=b, dates=bool(TEMPORAL.search(q["question"])))
        for t in (g["question_type"], "all"):
            res[t, b]["all_gold"].append(set(g["evidence"]) <= {e["id"] for e in ev})
            res[t, b]["sessions"].append(len(ev))
for (t, b), r in sorted(res.items()):
    n = len(r["all_gold"])
    print(f"{t:26s} budget={b:5d} n={n:3d} all_gold={sum(r['all_gold']) / n:.3f} sessions={sum(r['sessions']) / n:.1f}")
