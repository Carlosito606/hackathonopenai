"""Plan again, with the current code, the questions of an earlier plan (same ids, same split).

    python experiments/r1/replan.py ../data/dev OLD_PLAN.jsonl NEW_PLAN.jsonl --cache ../cache/dev.pkl
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from prepare import plan_question  # noqa: E402
from retrieval import Embedder, load_split  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("split")
ap.add_argument("old")
ap.add_argument("out")
ap.add_argument("--cache", required=True)
args = ap.parse_args()
hist, qs, _ = load_split(args.split)
ids = [json.loads(line)["question_id"] for line in open(args.old, encoding="utf-8") if line.strip()]
by_id = {q["question_id"]: q for q in qs}
emb = Embedder(args.cache)
with open(args.out, "w", encoding="utf-8") as f:
    for qid in ids:
        q = by_id[qid]
        f.write(json.dumps(plan_question(q, hist[q["history_id"]], emb)) + "\n")
print(f"wrote {len(ids)} questions to {args.out}")
