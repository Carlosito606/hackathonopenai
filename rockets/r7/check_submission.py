"""Sanity checks on a predictions.jsonl before it is submitted (no gold needed).

    python rockets/r7/check_submission.py ship/predictions.jsonl ../data/test

Checks: one line per question of the split and no other ids, no duplicates, the field types of the evaluator's
format, citations that are session ids of the question's own history, no empty answer without an abstention, no
leftover INSUFFICIENT_EVIDENCE or [E#] labels in an answer, no hedged answers ("or" between alternatives is only
flagged, not an error). Prints counts and every problem; exit 1 on errors, 0 otherwise.
"""
import argparse
import json
import re
import sys
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("predictions")
    ap.add_argument("split", help="folder with questions.jsonl and histories.jsonl")
    args = ap.parse_args()
    split = Path(args.split)
    questions = {}
    with open(split / "questions.jsonl", encoding="utf-8") as f:
        for q in map(json.loads, filter(str.strip, f)):
            questions[q["question_id"]] = q["history_id"]
    sessions = {}
    with open(split / "histories.jsonl", encoding="utf-8") as f:
        for line in f.read().split("\n"):  # not splitlines(): chats contain U+2028
            if line.strip():
                h = json.loads(line)
                sessions[h["history_id"]] = {s["session_id"] for s in h["sessions"]}
    errors, notes, seen = [], [], set()
    abstained = cited = 0
    with open(args.predictions, encoding="utf-8") as f:
        for n, line in enumerate(f.read().split("\n"), 1):
            if not line.strip():
                continue
            try:
                p = json.loads(line)
            except ValueError as e:
                errors.append(f"line {n}: not JSON ({e})")
                continue
            qid = p.get("question_id")
            if qid not in questions:
                errors.append(f"line {n}: unknown question_id {qid!r}")
                continue
            if qid in seen:
                errors.append(f"line {n}: duplicate {qid}")
            seen.add(qid)
            if not isinstance(p.get("abstain"), bool) or not isinstance(p.get("answer"), str) or \
                    not isinstance(p.get("citations"), list):
                errors.append(f"line {n}: {qid}: abstain must be bool, answer str, citations list")
                continue
            abstained += p["abstain"]
            cited += bool(p["citations"])
            bad = [c for c in p["citations"] if c not in sessions[questions[qid]]]
            if bad:
                errors.append(f"line {n}: {qid}: citations not in its history: {bad}")
            if not p["abstain"] and not p["answer"].strip():
                errors.append(f"line {n}: {qid}: empty answer without abstaining")
            if "INSUFFICIENT_EVIDENCE" in p["answer"] and not p["abstain"]:
                errors.append(f"line {n}: {qid}: INSUFFICIENT_EVIDENCE in an answer that does not abstain")
            if re.search(r"\[\s*E\d+", p["answer"]):
                notes.append(f"line {n}: {qid}: [E#] label left in the answer")
            if re.search(r"\b(either|or maybe|possibly|might be)\b", p["answer"], re.I):
                notes.append(f"line {n}: {qid}: answer may hedge: {p['answer'][:80]!r}")
    missing = sorted(set(questions) - seen)
    if missing:
        errors.append(f"{len(missing)} questions without a prediction, e.g. {missing[:3]}")
    print(f"{len(seen)}/{len(questions)} questions, {abstained} abstained, {cited} with citations")
    for e in errors:
        print("ERROR", e)
    for m in notes:
        print("note ", m)
    print("OK" if not errors else f"{len(errors)} errors")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
