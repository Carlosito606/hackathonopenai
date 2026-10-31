"""Retrieval for every question of a split -> plan.jsonl (question with answering notes, date, evidence).

    python prepare.py ../data/test plan-test.jsonl --cache ../cache/test.pkl
    python prepare.py ../data/dev plan-dev.jsonl --cache ../cache/dev.pkl --sample 150
"""
import argparse
import json
import random
import re

from memsys import TEMPORAL, Embedder, build_evidence, day_no, load_split, parse_date, retrieve
from verify import missing_names

GUIDE = """
(How to answer: the evidence is excerpts from my own past chats with you, oldest first, each with its date; "user" is me, "assistant" is you.
- First write "Quotes:" and copy, word for word, the sentence(s) from the excerpts that answer the question, each with its label, e.g. [E3] "I just started reading The Nightingale". The answer is often a side remark in a chat about something else, and may use other words than the question.
- If it changed over time, the most recent conversation wins.
- Then the final line holds only the short answer (a name, number, date or short phrase) followed by the labels of the excerpts you quoted, e.g. "Sombra [E4]". Labels count only on that line, so always repeat them there. One answer, no hedging, no alternatives.
- Write INSUFFICIENT_EVIDENCE only if you could quote nothing that answers it, or what you quoted is about a different person, thing or event than the question asks about.{extra})"""
DATES = """
- Dates are tagged [YYYY-MM-DD, day N]: days between two dates = the difference of their day numbers (weeks = days / 7). The question date is day {today}. Use the date the event happened as stated, else the date of the conversation that reports it."""
COUNT = """
- Before the final line, list each distinct item with its label, without counting one item twice, then give the total."""
MISSING = """
(Note: {names} never came up in our chats. Unless an excerpt names {them}, the answer is INSUFFICIENT_EVIDENCE.)"""
COUNTING = re.compile(r"\bhow (many|much)\b|\btotal\b|\bcombined\b|\bin all\b|\baltogether\b", re.I)


def plan_question(q, history, emb):
    temporal = bool(TEMPORAL.search(q["question"]))
    cands = retrieve(history, q["question"], emb)
    evidence = build_evidence(history, cands, budget=8000, dates=temporal)
    extra = DATES.format(today=day_no(parse_date(q["question_date"]))) if temporal else ""
    if COUNTING.search(q["question"]) and not re.search(r"how many (days|weeks|months|years)", q["question"], re.I):
        extra += COUNT
    missing = missing_names(q["question"], history)
    note = MISSING.format(names=" and ".join(f'"{n}"' for n in missing), them="them" if len(missing) > 1 else "it")
    return {"question_id": q["question_id"], "history_id": q["history_id"], "question_date": q["question_date"],
            "question": q["question"].strip() + (note if missing else "") + "\n" + GUIDE.format(extra=extra),
            "evidence": evidence,
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
