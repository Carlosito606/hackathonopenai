"""What R7's gate changes for a reader: on the questions the gate abstains on, ask the reader anyway and count
what the abstention wins or loses.

    python rockets/r7/gate_value.py reader_predictions.jsonl ../data/dev/gold.jsonl ../data/dev_hard/gold.jsonl

gain:   unanswerable, the reader answered (R7's abstention turns a wrong answer into a right one)
same:   unanswerable and the reader abstained too, or answerable and the reader was wrong or abstained
loss:   answerable and the reader's answer matches the gold (R7's abstention throws a right answer away)
unsure: answerable, the reader's answer is not a gold match ("unjudged": needs a judge or a human)
"""
import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path


def read_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("predictions")
    ap.add_argument("gold", nargs="+")
    ap.add_argument("--score", required=True, help="the challenge's score.py (for its answer matching)")
    ap.add_argument("--show", action="store_true")
    args = ap.parse_args()
    sys.path.insert(0, str(Path(args.score).resolve().parent))
    from score import answer_matched  # noqa: E402  (organisers' matching, read-only)
    gold = {g["question_id"]: g for p in args.gold for g in read_jsonl(p)}
    by = defaultdict(Counter)
    for p in read_jsonl(args.predictions):
        g = gold[p["question_id"]]
        if g["abstain"]:
            kind = "same" if p["abstain"] else "gain"
        elif p["abstain"] or not p["answer"].strip():
            kind = "same"
        else:
            kind = "loss" if answer_matched(p["answer"], g) else "unsure"
        for t in (g["question_type"], "all"):
            by[t][kind] += 1
        if args.show:
            print(f"{kind:6} {g['question_type'][:12]:12} answer={p['answer'][:50]!r} gold={g['answer'][:50]!r}")
    print(f"{'type':26} {'n':>3} {'gain':>5} {'same':>5} {'loss':>5} {'unsure':>6}")
    for t, c in sorted(by.items(), key=lambda kv: kv[0] == "all"):
        print(f"{t:26} {sum(c.values()):3} {c['gain']:5} {c['same']:5} {c['loss']:5} {c['unsure']:6}")


if __name__ == "__main__":
    main()
