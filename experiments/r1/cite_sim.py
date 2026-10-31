# Run from ~/vibathon/rakieta-dev (needs out/final-<split>/evidence.jsonl and ../poligon2/rockets/poligon/cite_expand.py)
"""Simulated reader cites the gold session in the pack with the most question words; then cite_expand's rule.
Evidence F1 before/after per type on dev, dev-hard v2 and dev-hard-long (final R1 packs)."""
import json
import sys
from collections import defaultdict

sys.path.insert(0, "../poligon2/rockets/poligon")
from cite_expand import expand, words  # noqa: E402


def rj(p):
    return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]


def f1(c, e):
    c, e = set(c), set(e)
    h = len(c & e)
    return 0 if not h else 2 * h / (len(c) + len(e))


for split in ("dev", "dev_hard_v2", "dev_hard_long"):
    gold = {g["question_id"]: g for g in rj(f"../data/{split}/gold.jsonl")}
    qs = {q["question_id"]: q for q in rj(f"../data/{split}/questions.jsonl")}
    hist = {}
    for line in open(f"../data/{split}/histories.jsonl", encoding="utf-8"):
        h = json.loads(line)
        hist[h["history_id"]] = {s["session_id"]: words(" ".join(t["content"] for t in s["turns"] if t["role"] == "user"))
                                 for s in h["sessions"]}
    acc = defaultdict(lambda: [[], []])
    for e in rj(f"out/final-{split}/evidence.jsonl"):
        g = gold[e["question_id"]]
        if g["abstain"]:
            continue
        q = qs[e["question_id"]]
        text = hist[q["history_id"]].get
        qw = words(q["question"])
        gold_in = [s for s in e["sessions"] if s in g["evidence"]]
        cited = sorted(gold_in, key=lambda s: -len(qw & text(s)))[:1]
        new = expand(cited, e["sessions"], qw, lambda s: text(s) or set(), 0.8)
        for t in (g["question_type"], "all"):
            acc[t][0].append(f1(cited, g["evidence"]))
            acc[t][1].append(f1(new, g["evidence"]))
    print("==", split)
    for t, (a, b) in sorted(acc.items()):
        print(f"  {t:26s} n={len(a):3d}  {sum(a) / len(a):.3f} -> {sum(b) / len(b):.3f}")
