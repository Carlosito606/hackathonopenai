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
from rocket import missing, qa_abstains, qa_applies  # noqa: E402


def read_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def auc(pos, neg):
    """P(answerable score > unanswerable score), ties count half."""
    if not pos or not neg:
        return None
    return sum((p > n) + 0.5 * (p == n) for p in pos for n in neg) / (len(pos) * len(neg))


def qa_table(rows, gold, types):
    """SQuAD 2.0 signal (run.py --qa): AUC per type, share of questions it applies to, and pack + QA abstention
    for a sweep of thresholds."""
    print(f"{'qa signal':26} {'n':>4} {'applies':>7} {'auc_all':>7} {'auc_applies':>11}")
    for t in types + ["all"]:
        rs = [r for r in rows if r.get("qa") and r["qa"]["qa"] is not None
              and (t == "all" or gold[r["question_id"]]["question_type"] == t)]
        ap_ = [r for r in rs if qa_applies(r["question"])]
        a = [auc([r["qa"]["qa"] for r in s if not gold[r["question_id"]]["abstain"]],
                 [r["qa"]["qa"] for r in s if gold[r["question_id"]]["abstain"]]) for s in (rs, ap_)]
        cells = ["-" if v is None else f"{v:.3f}" for v in a]
        print(f"{t:26} {len(rs):4} {len(ap_):7} {cells[0]:>7} {cells[1]:>11}")
    print()
    print("pack + qa below threshold (single-fact questions only): abstention recall / false abstention")
    print(f"{'threshold':>9}  " + "  ".join(f"{t[:14]:>14}" for t in types + ["all"]))
    for th in (-8, -6, -5, -4, -3, -2, -1, 0, 1, 2):
        cells = []
        for t in types + ["all"]:
            rs = [r for r in rows if t == "all" or gold[r["question_id"]]["question_type"] == t]
            dec = {r["question_id"]: bool(missing(r["checked"], "pack", r["question"]))
                   or qa_abstains(r["question"], r.get("qa"), th) for r in rs}
            ab = [r for r in rs if gold[r["question_id"]]["abstain"]]
            an = [r for r in rs if not gold[r["question_id"]]["abstain"]]
            rec = f"{sum(dec[r['question_id']] for r in ab)}/{len(ab)}" if ab else "-"
            cells.append(f"{rec:>5} {sum(dec[r['question_id']] for r in an):>3}/{len(an):<3}")
        print(f"{th:>9}  " + "  ".join(f"{c:>14}" for c in cells))
    print()


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
    if any(r.get("qa") for r in rows):
        qa_table(rows, gold, types)
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
