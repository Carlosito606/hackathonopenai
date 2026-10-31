"""Retrieval for every question of a split -> plan.jsonl (question with answering notes, date, evidence).

    python prepare.py ../data/test plan-test.jsonl --cache ../cache/test.pkl
    python prepare.py ../data/dev plan-dev.jsonl --cache ../cache/dev.pkl --sample 150
"""
import argparse
import json
import random
import re

import sys
from pathlib import Path

from memsys import TEMPORAL, Embedder, build_evidence, day_no, load_split, parse_date, retrieve

sys.path.insert(0, str(Path(__file__).resolve().parent / "reactor"))
import client as kit  # noqa: E402

BUDGET = 18000  # evidence chars; 24000 for counting questions was within noise on dev-hard (experiments/r1)
MAX_MESSAGE = 29000  # ask.py sends with --max-chars 30000

GUIDE = """
(How to answer: the evidence is excerpts from my own past chats with you, oldest first, each with its date; "user" is me, "assistant" is you.
- Some excerpts are near misses: other people's things, other pets, a different event, a plan that changed, or a value I corrected later. Use only what matches the question exactly.
- If it changed over time, the most recent conversation wins. A plan, a recommendation, an attempt, or a change I later undid ("removed it", "didn't keep it", "used to") is not my current state.
- Things said about other people (family, friends, neighbors, colleagues) or their pets do not answer a question about me or mine.
- The final line holds only the short answer (a name, number, date or short phrase) and the labels of the excerpts that state it, e.g. "<answer> [E4]". One answer, no hedging, no alternatives. It is the last line of your reply: nothing after it.
- Write INSUFFICIENT_EVIDENCE only if no excerpt states what is asked about me (it is never said, or said only about someone else).{extra})"""
DATES = """
- Dates are tagged [YYYY-MM-DD, day N]: days between two dates = the difference of their day numbers (weeks = days / 7). The question date is day {today}. Use the date the event happened as stated, else the date of the conversation that reports it. Tags with "about" are approximate: prefer an exact date for the same event if one is given."""
COUNT = """
- Before the final line, list each distinct item with its label, without counting one item twice, then give the total."""
COUNTING = re.compile(r"\bhow (many|much)\b|\btotal\b|\bcombined\b|\bin all\b|\baltogether\b", re.I)


def message_chars(question, evidence, question_date):
    """Length of the one message the kit's client sends for this question."""
    passages = kit.load_evidence(json.dumps(evidence)) if evidence else []
    return len(kit.build_message(question, passages, "0" * 8, kit.parse_question_date(question_date)))


def plan_question(q, history, emb):
    temporal = bool(TEMPORAL.search(q["question"]))
    counting = bool(COUNTING.search(q["question"])) and not re.search(r"how many (days|weeks|months|years)",
                                                                    q["question"], re.I)
    cands = retrieve(history, q["question"], emb, question_date=q["question_date"])
    extra = DATES.format(today=day_no(parse_date(q["question_date"]))) if temporal else ""
    if counting:
        extra += COUNT
    question = q["question"].strip() + "\n" + GUIDE.format(extra=extra)
    budget = BUDGET
    evidence = build_evidence(history, cands, budget=budget, dates=temporal)
    while message_chars(question, evidence, q["question_date"]) > MAX_MESSAGE and budget > 4000:
        budget -= 2000
        evidence = build_evidence(history, cands, budget=budget, dates=temporal)
    return {"question_id": q["question_id"], "history_id": q["history_id"], "question_date": q["question_date"],
            "question": question, "evidence": evidence, "top_score": cands[0]["score"] if cands else None}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("split")
    ap.add_argument("out")
    ap.add_argument("--cache", required=True)
    ap.add_argument("--sample", type=int)
    args = ap.parse_args()
    hist, qs, _ = load_split(args.split)
    if args.sample:
        random.seed(0)
        qs = random.sample(qs, args.sample)
    emb = Embedder(args.cache)
    emb.ensure([s for q in qs for s in hist[q["history_id"]]["sessions"]])
    with open(args.out, "w", encoding="utf-8") as f:
        for i, q in enumerate(qs, 1):
            f.write(json.dumps(plan_question(q, hist[q["history_id"]], emb)) + "\n")
            f.flush()
            if i % 20 == 0:
                print(f"{i}/{len(qs)}", flush=True)


if __name__ == "__main__":
    main()
