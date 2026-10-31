"""Offline: share of gold sessions inside the evidence per budget / cutoff, on the harness sample (no LLM).

    python experiments/verify/coverage.py ../data/dev cands.pkl
"""
import pickle
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from harness import sample  # noqa: E402
from memsys import build_evidence, load_split  # noqa: E402

hist, qs, gold = load_split(sys.argv[1])
cands = pickle.loads(Path(sys.argv[2]).read_bytes())
settings = {f"{b // 1000}k": dict(budget=b) for b in (4000, 8000, 12000, 18000)}
settings.update({f"18k rel-{d}": dict(rel=d) for d in (3, 5, 8)})
rows = defaultdict(lambda: defaultdict(list))
for q in sample(qs, gold):
    g = gold[q["question_id"]]
    if g["abstain"]:
        continue
    c = cands[q["question_id"]]
    for name, kw in settings.items():
        cc = [x for x in c if x["score"] >= c[0]["score"] - kw["rel"]] if "rel" in kw else c
        ev = build_evidence(hist[q["history_id"]], cc, budget=kw.get("budget", 18000))
        ids = {e["id"] for e in ev}
        for t in (g["question_type"], "ALL"):
            rows[t][name].append((len(ids & set(g["evidence"])) / len(g["evidence"]), len(ev),
                                  sum(len(e["text"]) for e in ev)))
print(f"{'type':26} " + " ".join(f"{n:>16}" for n in settings))
for t in sorted(rows):
    cells = []
    for n in settings:
        v = rows[t][n]
        cells.append(f"{sum(x[0] for x in v) / len(v):.2f}/{sum(x[1] for x in v) / len(v):4.1f}s/{sum(x[2] for x in v) / len(v) / 1000:4.1f}k")
    print(f"{t:26} " + " ".join(f"{c:>16}" for c in cells))
print("cell = gold-session recall / sessions sent / chars sent")
