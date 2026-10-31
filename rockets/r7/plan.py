"""R7 with a reader: plans for ask.py, and R7's abstentions laid over the reader's predictions.

    python rockets/r7/plan.py make ../data/dev plan.jsonl --only splits/reactor_mini.txt --qa
    python ask.py plan.jsonl results.jsonl --local http://127.0.0.1:8899
    python reactor/predictions.py results.jsonl --histories ../data/dev/histories.jsonl --out reader.jsonl \\
        --abstain-on agent,no-answer
    python rockets/r7/plan.py overlay plan.jsonl reader.jsonl predictions.jsonl

The reader gets R1's prompt (prepare.py GUIDE) on R7's evidence pack, so one reader pass gives R1's behaviour
("none") and R7's (the same answers, abstained where R7's gate fires). `make --warn` writes only the questions R7
would warn about, with the warning in the question; `overlay --replace` puts the reader's answers to those in.
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import rocket  # noqa: E402
from memsys import TEMPORAL, day_no, load_split, parse_date  # noqa: E402  (R1, read-only)
from prepare import COUNT, COUNTING, DATES, GUIDE  # noqa: E402  (R1's prompt, read-only)


def guide(q):
    """R1's answering notes for a question (prepare.plan_question)."""
    extra = DATES.format(today=day_no(parse_date(q["question_date"]))) if TEMPORAL.search(q["question"]) else ""
    if COUNTING.search(q["question"]) and not re.search(r"how many (days|weeks|months|years)", q["question"], re.I):
        extra += COUNT
    return GUIDE.format(extra=extra)


def make(args):
    hist, qs, _ = load_split(args.split)
    if args.only:
        keep = set(Path(args.only).read_text().split())
        qs = [q for q in qs if q["question_id"] in keep]
    with open(args.out, "w", encoding="utf-8") as f:
        for i, q in enumerate(qs, 1):
            h = hist[q["history_id"]]
            cands = rocket.retrieve(q, h)
            pack = rocket.assemble(q, h, cands)
            gate = rocket.decide(q, h, cands, pack, policy="pack", use_qa=args.qa)
            warn = rocket.decide(q, h, cands, pack, policy="warn", use_qa=False)
            warned = warn["question"] != q["question"].strip()
            if args.warn and not warned:
                continue
            text = warn["question"] if args.warn else q["question"].strip()
            f.write(json.dumps({"question_id": q["question_id"], "history_id": q["history_id"],
                                "question_date": q["question_date"], "question": text + "\n" + guide(q),
                                "evidence": pack["evidence"],
                                "r7": {"abstain": gate["abstain"], "warned": warned, "qa": gate["qa"]}}) + "\n")
            if i % 10 == 0:
                print(f"{i}/{len(qs)}", flush=True)


def overlay(args):
    plan = [json.loads(line) for line in open(args.plan, encoding="utf-8") if line.strip()]
    reader = {p["question_id"]: p for p in map(json.loads, open(args.reader, encoding="utf-8")) if p}
    if args.replace:
        reader.update({p["question_id"]: p for p in map(json.loads, open(args.replace, encoding="utf-8")) if p})
    empty = {"abstain": False, "answer": "", "citations": []}
    with open(args.out, "w", encoding="utf-8") as f:
        for p in plan:
            pred = {k: reader.get(p["question_id"], empty)[k] for k in ("abstain", "answer", "citations")}
            if p["r7"]["abstain"] and not args.reader_only:
                # Evidence F1 is scored on every answerable question, abstained or not (challenge README), so the
                # reader's citations stay: a false abstention then loses the answer but not the evidence.
                pred = {"abstain": True, "answer": "", "citations": pred["citations"]}
            f.write(json.dumps({"question_id": p["question_id"], **pred}) + "\n")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("make")
    m.add_argument("split")
    m.add_argument("out")
    m.add_argument("--only", help="file of question ids")
    m.add_argument("--qa", action="store_true", help="gate with the SQuAD 2.0 signal too")
    m.add_argument("--warn", action="store_true", help="only questions R7 warns about, warning in the question")
    o = sub.add_parser("overlay")
    o.add_argument("plan")
    o.add_argument("reader", help="predictions.jsonl made from the reader's results")
    o.add_argument("out")
    o.add_argument("--replace", help="predictions that replace the reader's (the --warn pass)")
    o.add_argument("--reader-only", action="store_true", help="ignore R7's gate (R1's behaviour)")
    args = ap.parse_args()
    make(args) if args.cmd == "make" else overlay(args)


if __name__ == "__main__":
    main()
