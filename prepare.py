"""Retrieval for every question of a split -> plan.jsonl (question with answering notes, date, evidence).

    python prepare.py ../data/test plan-test.jsonl --cache ../cache/test.pkl
    python prepare.py ../data/dev plan-dev.jsonl --cache ../cache/dev.pkl --sample 150
"""
import argparse
import json
import random
import re

from memsys import TEMPORAL, Embedder, build_evidence, day_no, load_split, parse_date, retrieve

GUIDE = """
(How to answer: the evidence is excerpts from my own past chats with you, oldest first, each with its date; "user" is me, "assistant" is you.
- Some excerpts are near misses: other people's things, other pets, a different event, a plan that changed, or a value I corrected later. Use only what matches the question exactly.
- If it changed over time, the most recent conversation wins.
- The final line holds only the short answer (a name, number, date or short phrase) and the labels of the excerpts that state it, e.g. "Sombra [E4]". One answer, no hedging, no alternatives. It is the last line of your reply: nothing after it.
- Write INSUFFICIENT_EVIDENCE only if no excerpt states what is asked.{extra})"""
DATES = """
- Dates are tagged [YYYY-MM-DD, day N]: days between two dates = the difference of their day numbers (weeks = days / 7). The question date is day {today}. Use the date the event happened as stated, else the date of the conversation that reports it."""
COUNT = """
- Before the final line, list each distinct item with its label, without counting one item twice, then give the total."""
COUNTING = re.compile(r"\bhow (many|much)\b|\btotal\b|\bcombined\b|\bin all\b|\baltogether\b", re.I)


def plan_question(q, history, emb):
    temporal = bool(TEMPORAL.search(q["question"]))
    cands = retrieve(history, q["question"], emb)
    evidence = build_evidence(history, cands, dates=temporal)
    extra = DATES.format(today=day_no(parse_date(q["question_date"]))) if temporal else ""
    if COUNTING.search(q["question"]) and not re.search(r"how many (days|weeks|months|years)", q["question"], re.I):
        extra += COUNT
    return {"question_id": q["question_id"], "history_id": q["history_id"], "question_date": q["question_date"],
            "question": q["question"].strip() + "\n" + GUIDE.format(extra=extra), "evidence": evidence,
            "top_score": cands[0]["score"] if cands else None}


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
