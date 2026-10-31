"""Re-tag the dates of an existing plan with the current dates.py, without running retrieval again (the evidence
chunks do not depend on dates.py). Gives the plan prepare.py would write with the same retrieval.

    python experiments/temporal/reannotate.py plan-before.jsonl plan-after.jsonl
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from dates import TEMPORAL, _mark, annotate_dates, day_no, parse_date  # noqa: E402
from prepare import COUNT, COUNTING, DATES, GUIDE  # noqa: E402

OLD_TAG = re.compile(r" \[(?:about )?\d{4}-\d\d-\d\d, day -?\d+(?: to \d{4}-\d\d-\d\d, day -?\d+)?\]")


def reannotate(p):
    question = p["question"].split("\n(How to answer:")[0].rstrip()
    temporal = bool(TEMPORAL.search(question))
    for e in p["evidence"]:
        lines = [OLD_TAG.sub("", line) for line in e["text"].split("\n") if not line.startswith("(this conversation:")]
        if temporal:
            sd = parse_date(e["date"])
            lines = [f"(this conversation: {_mark(sd)})"] + [annotate_dates(line, sd) for line in lines]
        e["text"] = "\n".join(lines)
    extra = DATES.format(today=day_no(parse_date(p["question_date"]))) if temporal else ""
    if COUNTING.search(question) and not re.search(r"how many (days|weeks|months|years)", question, re.I):
        extra += COUNT
    p["question"] = question + "\n" + GUIDE.format(extra=extra)
    return p


if __name__ == "__main__":
    with open(sys.argv[1], encoding="utf-8") as f, open(sys.argv[2], "w", encoding="utf-8") as out:
        for line in f:
            if line.strip():
                out.write(json.dumps(reannotate(json.loads(line))) + "\n")
