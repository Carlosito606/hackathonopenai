"""prepare.py's plan for a fixed list of question ids (run from the code dir whose retrieval you want to test):

    python ../w-retrieval/experiments/retrieval/plan_ids.py ../data/dev ids.txt plan.jsonl --cache ../cache/dev-x.pkl
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, ".")
from prepare import plan_question  # noqa: E402
from retrieval import Embedder, read_jsonl  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("split")
ap.add_argument("ids")
ap.add_argument("out")
ap.add_argument("--cache", required=True)
args = ap.parse_args()
ids = Path(args.ids).read_text().split()
qs = {q["question_id"]: q for q in read_jsonl(Path(args.split) / "questions.jsonl")}
need = {qs[i]["history_id"] for i in ids}
hist = {}
with open(Path(args.split) / "histories.jsonl", encoding="utf-8") as f:
    for line in f:
        if line[:80].split('"history_id": "', 1)[-1][:14] in need:
            h = json.loads(line)
            hist[h["history_id"]] = h
emb = Embedder(args.cache)
with open(args.out, "w", encoding="utf-8") as f:
    for i in ids:
        f.write(json.dumps(plan_question(qs[i], hist[qs[i]["history_id"]], emb)) + "\n")
