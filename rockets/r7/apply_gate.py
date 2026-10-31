"""Lay R7's abstentions over any rocket's predictions.jsonl (e.g. the ship's), without calling Reactor again.

    python rockets/r7/run.py ../data/test --qa --out ../r7-test             # R7's gate on the split, no reader
    python rockets/r7/apply_gate.py ../r7-test/<run_id> ship_predictions.jsonl predictions_r7.jsonl

A question R7 abstains on becomes {"abstain": true, "answer": ""} and keeps the ship's citations: evidence F1 is
scored on every answerable question, abstained or not, so a false abstention loses the answer but not the evidence.
Every other line is copied unchanged. Prints how many answers were turned into abstentions.
"""
import argparse
import json
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("r7_run", help="an R7 run folder (its predictions.jsonl holds R7's abstentions)")
    ap.add_argument("predictions")
    ap.add_argument("out")
    args = ap.parse_args()
    with open(Path(args.r7_run) / "predictions.jsonl", encoding="utf-8") as f:
        gate = {p["question_id"] for p in map(json.loads, f) if p["abstain"]}
    changed = kept = 0
    with open(args.predictions, encoding="utf-8") as f, open(args.out, "w", encoding="utf-8") as out:
        for line in f:
            if not line.strip():
                continue
            p = json.loads(line)
            if p["question_id"] in gate and not p["abstain"]:
                p = {**p, "abstain": True, "answer": ""}
                changed += 1
            else:
                kept += 1
            out.write(json.dumps(p) + "\n")
    print(f"{changed} answers turned into abstentions, {kept} lines unchanged; R7 abstains on {len(gate)} questions")


if __name__ == "__main__":
    main()
