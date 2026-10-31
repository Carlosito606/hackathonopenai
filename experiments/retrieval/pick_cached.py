"""Pick eval questions that need the fewest new embeddings (the shared GPU is slow): greedy by uncached sessions.

    python experiments/retrieval/pick_cached.py ../data/dev-large ../cache/devlarge-retrieval.pkl 40 ids.txt \
        [--types multi-session,temporal-reasoning] [--holdout-questions ../data/dev/questions.jsonl]
"""
import argparse
import json
import pickle
import re
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("split")
ap.add_argument("cache")
ap.add_argument("n", type=int)
ap.add_argument("out")
ap.add_argument("--types")
ap.add_argument("--holdout", default=Path(__file__).resolve().parents[2] / "splits/dev_holdout.txt")
ap.add_argument("--holdout-questions", default="../data/dev/questions.jsonl")
args = ap.parse_args()
split = Path(args.split)
cached = set(pickle.loads(Path(args.cache).read_bytes()))
held = set(Path(args.holdout).read_text().split())
held_text = {json.loads(x)["question"] for x in open(args.holdout_questions) if json.loads(x)["question_id"] in held}
gold = {g["question_id"]: g for g in map(json.loads, open(split / "gold.jsonl"))}
qs = [q for q in map(json.loads, open(split / "questions.jsonl"))
      if q["question_id"] not in held and q["question"] not in held_text and not gold[q["question_id"]]["abstain"]
      and (not args.types or gold[q["question_id"]]["question_type"] in args.types.split(","))]
by_hist = {}
for q in qs:
    by_hist.setdefault(q["history_id"], []).append(q)
missing = {}
with open(split / "histories.jsonl", encoding="utf-8") as f:
    for line in f:
        hid = re.search(r'"history_id": "(h_[0-9a-f]+)"', line[:80]).group(1)
        if hid in by_hist:
            missing[hid] = set(re.findall(r'"session_id": "(s_[0-9a-f]+)"', line)) - cached
picked, todo = [], set()
while len(picked) < args.n and missing:
    hid = min(missing, key=lambda h: (len(missing[h] - todo), h))
    todo |= missing.pop(hid)
    picked += [q["question_id"] for q in by_hist[hid]]
Path(args.out).write_text("\n".join(picked[:args.n]) + "\n")
print(f"{len(picked[:args.n])} questions, {len(todo)} sessions to embed")
