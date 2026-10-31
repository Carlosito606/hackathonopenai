"""Date expressions that annotate_dates leaves untagged, on user turns.

    python experiments/temporal/coverage.py ../data/dev ../data/test [--show 40]

dev: user turns of the gold sessions of non-holdout temporal-reasoning questions; test: user turns of all
histories. Prints, per split, how many broad date-like phrases get a tag and the most common untagged ones.
"""
import argparse
import collections
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from dates import annotate_dates, parse_date  # noqa: E402

WD = r"(?:mon|tues|wednes|thurs|fri|satur|sun)day"
MON = (r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|sept?(?:ember)?|"
       r"oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)")
NUMW = r"(?:\d+|a|an|one|two|three|four|five|six|seven|eight|nine|ten|a couple of|a few|several)"
BROAD = re.compile("|".join([
    rf"\b(?:last|this past|past|this|next|on|previous|coming)? ?{WD}s?\b(?: (?:morning|afternoon|evening|night))?",
    r"\b(?:last|this past|past|previous|next|this|coming) (?:weekend|week|month|year|night|summer|spring|winter|fall|autumn)\b",
    rf"\b{NUMW} (?:days?|weeks?|weekends?|months?|years?) ago\b",
    r"\b(?:earlier|later) this (?:week|month|year)\b",
    r"\b(?:over|on) the weekend\b|\bthe other day\b|\bday before yesterday\b|\b(?:last|yesterday) (?:night|evening|morning)\b",
    r"\b(?:yesterday|today|tonight|tomorrow)\b",
    rf"\bthe \d{{1,2}}(?:st|nd|rd|th)\b",
    rf"\b{MON}\.? \d{{1,2}}(?:st|nd|rd|th)?(?: ?(?:-|–|to|and|through) ?\d{{1,2}}(?:st|nd|rd|th)?)?(?:,? 20\d\d)?\b",
    rf"\b\d{{1,2}}(?:st|nd|rd|th)? (?:of )?{MON}\b(?:,? 20\d\d)?",
    r"\b\d{1,2}/\d{1,2}(?:/\d{2,4})?\b",
    r"\b20\d\d-\d\d-\d\d\b",
]), re.I)
TAG_AFTER = re.compile(r"[^\[\n.]{0,25}\[(?:about )?\d{4}-\d\d-\d\d, day -?\d+")


def read_jsonl(p):
    with open(p, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def user_turns(split, sessions_filter=None):
    with open(os.path.join(split, "histories.jsonl"), encoding="utf-8") as f:
        for line in f:
            h = json.loads(line)
            for s in h["sessions"]:
                if sessions_filter is not None and s["session_id"] not in sessions_filter:
                    continue
                for t in s["turns"]:
                    if t["role"] == "user":
                        yield t["content"], parse_date(s["date"])


def coverage(turns):
    """Untagged / tagged broad matches. A broad match counts as tagged when a tag follows it closely in the
    annotated text (the annotation keeps the original text, so each match is located again there)."""
    hit, miss = collections.Counter(), collections.Counter()
    examples = {}
    for text, sd in turns:
        ann = annotate_dates(text, sd)
        pos = 0
        for m in BROAD.finditer(text):
            i = ann.find(m.group(0), pos)
            if i < 0:
                continue
            pos = i + len(m.group(0))
            key = re.sub(r"\d+", "N", m.group(0).lower())
            if TAG_AFTER.match(ann, pos):
                hit[key] += 1
            else:
                miss[key] += 1
                examples.setdefault(key, text[max(0, m.start() - 60):m.end() + 40].replace("\n", " "))
    return hit, miss, examples


def report(name, turns, show):
    hit, miss, ex = coverage(turns)
    h, m = sum(hit.values()), sum(miss.values())
    print(f"== {name}: tagged {h}, untagged {m} ({h / max(1, h + m):.1%} tagged)")
    for k, n in miss.most_common(show):
        print(f"  {n:5d}  {k!r:35}  …{ex[k]}…")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dev")
    ap.add_argument("test", nargs="?")
    ap.add_argument("--holdout", default=os.path.join(os.path.dirname(__file__), "..", "..", "splits", "dev_holdout.txt"))
    ap.add_argument("--show", type=int, default=40)
    args = ap.parse_args()
    holdout = set(open(args.holdout).read().split())
    gold = [g for g in read_jsonl(os.path.join(args.dev, "gold.jsonl"))
            if g["question_type"] == "temporal-reasoning" and g["question_id"] not in holdout]
    report(f"dev temporal gold sessions ({len(gold)} questions)",
           list(user_turns(args.dev, {s for g in gold for s in g["evidence"]})), args.show)
    if args.test:
        report("test all user turns", list(user_turns(args.test)), args.show)


if __name__ == "__main__":
    main()
