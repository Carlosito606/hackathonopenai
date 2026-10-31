"""Test-like trap sentences for dev-hard: the gold fact told about someone else, or as a mere plan, with another value.

    python rockets/poligon/make_traps.py ../data/dev ../data/poligon_runs/traps.jsonl --local http://127.0.0.1:8897
    python rockets/poligon/make_dev_hard.py ../data/dev ../data/dev_hard_trap --exclude rockets/poligon/exclude_v2.jsonl \\
        --traps ../data/poligon_runs/traps.jsonl --ids splits/dev_hard_trap_ids.txt

Why: R1's audit of the test evidence (experiments/r1/20261030-2300-gpt-audit-test-evidence.md) found a misleading
near-miss in 109 of 146 test packs, mostly a fact about another person (family, friend, neighbour, colleague) or a
plan / attempt / undone change taken as the current state. dev-hard's injected sessions come from other users and
cannot be that. Here, for every non-holdout answerable question whose gold answer is a checkable phrase, the
stand-in model rewrites the evidence sentence that states the answer into an aside ("By the way, ...") about
another person or about a plan, with a different value of the same kind. make_dev_hard.py --traps appends it to a
user turn of one injected session. The sentences are derived from dev text: keep the output local, never commit it.

Checks on every rewrite: no gold answer (as score.py matches it), the person or plan word present, one sentence of
at most 300 characters; rejected rewrites are skipped (counted). Deterministic at temperature 0 on one server.
"""
import argparse
import json
import random
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from judge import Judge, rj  # noqa: E402
from make_dev_hard import AnswerMatcher, rng_for  # noqa: E402

PEOPLE = ["my sister", "my brother", "my coworker", "my neighbor", "my best friend", "my cousin", "my roommate"]
PROMPT_PERSON = """A user said this in a chat with an AI assistant:
"{sentence}"
The key fact in it is: {answer}

Write ONE new sentence the same user could say later in a different chat, starting with "By the way," in which the same kind of fact is about {person} instead of the user, and the value is different from "{answer}" (a plausible alternative of the same kind). Do not mention "{answer}". Reply with the sentence only."""
PROMPT_PLAN = """A user said this in a chat with an AI assistant:
"{sentence}"
The key fact in it is: {answer}

Write ONE new sentence the same user could say earlier in a different chat, starting with "By the way," in which the user is only considering or planning something of the same kind (it has not happened), with a value different from "{answer}" (a plausible alternative of the same kind). Do not mention "{answer}". Reply with the sentence only."""
PLAN_WORDS = re.compile(r"\b(thinking|considering|plan|planning|might|maybe|wondering|hoping|want to|would like)\b",
                        re.I)
SENT = re.compile(r"(?<=[.!?\n])\s+")


def answer_sentence(g, sessions, match):
    """The last user (or, for single-session-assistant, assistant) sentence in the evidence that states the answer."""
    role = "assistant" if g["question_type"] == "single-session-assistant" else "user"
    found = None
    for s in sorted((s for s in sessions if s["session_id"] in set(g["evidence"])), key=lambda s: s["date"]):
        for t in s["turns"]:
            if t["role"] != role:
                continue
            for sent in SENT.split(t["content"]):
                if match(sent) and len(sent) < 400:
                    found = sent.strip()
    return found


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src", help="dev split folder")
    ap.add_argument("out", help="traps JSONL (local, never committed)")
    ap.add_argument("--local", required=True)
    ap.add_argument("--model", default="")
    ap.add_argument("--holdout", default=str(HERE.parents[1] / "splits" / "dev_holdout.txt"))
    ap.add_argument("--cache", default=str(Path.home() / ".cache" / "poligon-traps.jsonl"))
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    src = Path(args.src)
    hist = {h["history_id"]: h for h in rj(src / "histories.jsonl")}
    gold = {g["question_id"]: g for g in rj(src / "gold.jsonl")}
    holdout = set(Path(args.holdout).read_text(encoding="utf-8").split())
    jobs, skipped = [], Counter()
    for q in sorted(rj(src / "questions.jsonl"), key=lambda q: q["question_id"]):
        g = gold[q["question_id"]]
        if q["question_id"] in holdout or g["abstain"] or g["question_type"] == "single-session-assistant":
            continue
        match = AnswerMatcher(g)
        if not match.phrases:
            skipped["answer_not_checkable"] += 1
            continue
        sent = answer_sentence(g, hist[q["history_id"]]["sessions"], match)
        if not sent:
            skipped["no_answer_sentence"] += 1
            continue
        rng = rng_for(args.seed, q["question_id"], "trap")
        kind = rng.choice(["person", "plan"])
        person = rng.choice(PEOPLE)
        tmpl = PROMPT_PERSON if kind == "person" else PROMPT_PLAN
        jobs.append((q, g, kind, person, match, tmpl.format(sentence=sent, answer=g["answer"], person=person)))
    judge = Judge(args.local, args.model, args.cache)
    replies = judge.many([j[5] for j in jobs], args.workers, max_tokens=80)
    rows = []
    for (q, g, kind, person, match, _), reply in zip(jobs, replies):
        s = (reply or "").strip().strip('"').split("\n")[0].strip()
        if not s.lower().startswith("by the way") or len(s) > 300 or len(s) < 25:
            skipped["bad_shape"] += 1
            continue
        if match(s):
            skipped["contains_gold"] += 1
            continue
        if kind == "person" and person.split()[-1] not in s.lower():
            skipped["person_missing"] += 1
            continue
        if kind == "plan" and not PLAN_WORDS.search(s):
            skipped["plan_word_missing"] += 1
            continue
        rows.append({"source_qid": q["question_id"], "kind": kind, "sentence": s})
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8", newline="\n") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"{len(rows)} traps from {len(jobs)} rewrites ({judge.calls} model calls); kinds "
          f"{dict(Counter(r['kind'] for r in rows))}; skipped {dict(skipped)}")


if __name__ == "__main__":
    main()
