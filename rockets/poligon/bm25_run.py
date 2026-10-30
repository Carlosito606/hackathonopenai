"""Plain BM25 over all turns of a split -> candidates.jsonl (core/CONTRACT.md format), a no-dependency baseline.

    python rockets/poligon/bm25_run.py ../data/dev runs/poligon/bm25-dev/candidates.jsonl
    python rockets/poligon/bm25_run.py ../data/dev_hard runs/poligon/bm25-dev_hard/candidates.jsonl

Forked from experiments/analysis/karol-claude/mkruns.py (variant "all"): same tokenizer, stop words and BM25.
"""
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

STOP = set("the a an of to and in on for is it i my me you your was what how many did do does with at that this "
           "from by be are have has as or which when who where".split())


def tok(s):
    return re.findall(r"[a-z0-9']+", s.lower())


def rank(q, h, k=100):
    rows = [(s["session_id"], i, t["content"]) for s in h["sessions"] for i, t in enumerate(s["turns"])]
    docs = [tok(r[2]) for r in rows]
    n, avg = len(docs), sum(map(len, docs)) / len(docs)
    df = Counter(w for d in docs for w in set(d))
    qt = [w for w in tok(q) if w not in STOP]
    sc = []
    for r, d in zip(rows, docs):
        tf = Counter(d)
        v = sum(math.log(1 + (n - df[w] + .5) / (df[w] + .5)) * tf[w] * 2.2 / (tf[w] + 1.2 * (.25 + .75 * len(d) / avg))
                for w in qt if w in tf)
        sc.append([r[0], r[1], round(v, 3)])
    sc.sort(key=lambda x: -x[2])
    return sc[:k]


def main():
    split, out = Path(sys.argv[1]), Path(sys.argv[2])
    rj = lambda p: [json.loads(line) for line in open(p, encoding="utf-8") if line.strip()]
    hist = {h["history_id"]: h for h in rj(split / "histories.jsonl")}
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        for q in rj(split / "questions.jsonl"):
            f.write(json.dumps({"question_id": q["question_id"], "ranked": rank(q["question"], hist[q["history_id"]])})
                    + "\n")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
