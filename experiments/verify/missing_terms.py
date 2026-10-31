"""Offline: how often verify.missing_names flags answerable vs abstention questions (dev without holdout).

    python experiments/verify/missing_terms.py ../data/dev
"""
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from retrieval import load_split  # noqa: E402
from verify import missing_names  # noqa: E402

hist, qs, gold = load_split(sys.argv[1])
hold = set((Path(__file__).resolve().parents[2] / "splits" / "dev_holdout.txt").read_text().split())
stats = Counter()
for q in qs:
    if q["question_id"] in hold:
        continue
    g = gold[q["question_id"]]
    m = missing_names(q["question"], hist[q["history_id"]])
    key = ("ABSTAIN " if g["abstain"] else "") + g["question_type"]
    stats[key, "n"] += 1
    stats[key, "flag"] += bool(m)
    if m:
        print(key[:20], "|", q["question"][:90], "|", m)
for key in sorted({k for k, _ in stats}):
    print(f"{key:35} n={stats[key, 'n']:3} flagged={stats[key, 'flag']}")
