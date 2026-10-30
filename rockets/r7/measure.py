"""Abstention recall and false abstention per question type for every R7 policy, from one run's decisions.jsonl.

    python rockets/r7/measure.py runs/r7/<run_id> ../data/dev/gold.jsonl [--show]

Same definitions as score.py (abstention_recall over gold-abstain questions, false_abstention over answerable
ones). For "warn" the columns count questions whose reader gets a warning, not abstentions.
"pack_all_gold" is the share of answerable questions whose pack holds every gold session.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rocket import missing  # noqa: E402


def read_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run")
    ap.add_argument("gold")
    ap.add_argument("--show", action="store_true", help="list wrong decisions of the pack policy")
    args = ap.parse_args()
    gold = {g["question_id"]: g for g in read_jsonl(args.gold)}
    rows = read_jsonl(Path(args.run) / "decisions.jsonl")
    types = sorted({gold[r["question_id"]]["question_type"] for r in rows})
    print(f"{'policy':12} {'type':26} {'n':>4} {'abst_n':>6} {'abst_rec':>8} {'false_abst':>10} {'pack_all_gold':>13}")
    for policy in ("none", "pack", "pack-strict", "warn"):
        for t in types + ["all"]:
            rs = [r for r in rows if t == "all" or gold[r["question_id"]]["question_type"] == t]
            ab = [r for r in rs if gold[r["question_id"]]["abstain"]]
            an = [r for r in rs if not gold[r["question_id"]]["abstain"]]
            dec = {r["question_id"]: policy != "none" and bool(missing(r["checked"], policy, r["question"]))
                   for r in rs}
            rec = sum(dec[r["question_id"]] for r in ab) / len(ab) if ab else None
            fa = sum(dec[r["question_id"]] for r in an) / len(an) if an else None
            full = sum(set(gold[r["question_id"]]["evidence"]) <= set(r["sessions"]) for r in an) / len(an)
            cell = lambda v: "-" if v is None else f"{v:.3f}"  # noqa: E731
            print(f"{policy:12} {t:26} {len(rs):4} {len(ab):6} {cell(rec):>8} {cell(fa):>10} {full:13.3f}")
        print()
    if args.show:
        for r in rows:
            g = gold[r["question_id"]]
            miss = [e["text"] for e in missing(r["checked"], "pack", r["question"])]
            if bool(miss) != g["abstain"]:
                kind = "MISSED-ABSTAIN" if g["abstain"] else "FALSE-ABSTAIN"
                inpack = set(g["evidence"]) <= set(r["sessions"])
                print(f"{kind:14} {g['question_type'][:14]:14} gold_in_pack={inpack!s:5} {r['question'][:80]!r} "
                      f"missing={miss} all={[(e['text'], e['found']) for e in r['checked']]}")


if __name__ == "__main__":
    main()
