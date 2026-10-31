"""Check a predictions.jsonl against a split before submitting; exit 1 on any problem.

    python experiments/r1/check_predictions.py ../data/test predictions.jsonl [--results results-test.jsonl]

Problems: wrong number of lines, unknown / missing / repeated question ids, wrong field types, an empty answer that
is not an abstention, a citation that is not a session of the question's own history. With --results, also prints
how the answers came about (abstentions, citations taken from the reply, latency).
"""
import argparse
import json
import statistics
import sys
from collections import Counter
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("split", type=Path)
ap.add_argument("predictions", type=Path)
ap.add_argument("--results", type=Path)
args = ap.parse_args()

questions = {q["question_id"]: q for q in map(json.loads, open(args.split / "questions.jsonl", encoding="utf-8"))}
sessions = {}
for line in open(args.split / "histories.jsonl", encoding="utf-8"):
    h = json.loads(line)
    sessions[h["history_id"]] = {s["session_id"] for s in h["sessions"]}
preds = [json.loads(line) for line in open(args.predictions, encoding="utf-8") if line.strip()]

problems = []
ids = Counter(p.get("question_id") for p in preds)
problems += [f"repeated {q}" for q, n in ids.items() if n > 1]
problems += [f"unknown {q}" for q in ids if q not in questions]
problems += [f"missing {q}" for q in questions if q not in ids]
for p in preds:
    q = p.get("question_id")
    if not (isinstance(p.get("abstain"), bool) and isinstance(p.get("answer"), str)
            and isinstance(p.get("citations"), list)):
        problems.append(f"{q}: field types")
        continue
    if not p["abstain"] and not p["answer"].strip():
        problems.append(f"{q}: empty answer without abstain")
    if q in questions:
        foreign = [c for c in p["citations"] if c not in sessions[questions[q]["history_id"]]]
        if foreign:
            problems.append(f"{q}: citations outside its history {foreign}")

answered = [p for p in preds if not p["abstain"]]
print(f"{len(preds)} predictions for {len(questions)} questions; abstain {len(preds) - len(answered)}; "
      f"answered without citations {sum(not p['citations'] for p in answered)}; "
      f"citations per answer {statistics.mean(len(p['citations']) for p in answered) if answered else 0:.2f}")
if args.results:
    rs = [json.loads(line) for line in open(args.results, encoding="utf-8") if line.strip()]
    st = Counter(r.get("status") for r in rs)
    lat = [r["latency_s"] for r in rs if r.get("latency_s")]
    print(f"results: {dict(st)}; citations from reply {sum(r.get('citations_from') == 'reply' for r in rs)}; "
          f"latency median {statistics.median(lat) if lat else 0:.0f}s max {max(lat) if lat else 0:.0f}s")
for p in problems:
    print("PROBLEM", p)
sys.exit(1 if problems else 0)
