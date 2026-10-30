"""LLM check of dev-hard's injected sessions: does one answer the question or contradict its gold? -> exclude list.

    python rockets/poligon/check_injections.py ../data/dev_hard --local http://127.0.0.1:8899 \\
        --exclude rockets/poligon/exclude.jsonl
    python rockets/poligon/make_dev_hard.py ../data/dev ../data/dev_hard --exclude rockets/poligon/exclude.jsonl \\
        --ids splits/dev_hard_ids.txt                                   # then check again until nothing is added

Each injected session is cut to the few sentences that share most words with the question (the model never sees
the whole session: a 7B judge on CPU needs short prompts). Flagged pairs are appended to --exclude as
{"source_qid", "source_session", "why"}; make_dev_hard.py never injects them again. Verdicts are cached in --cache,
so a second round only asks about the replacement sessions.
"""
import argparse
import json
import re
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from judge import Judge, rj  # noqa: E402
from make_dev_hard import words  # noqa: E402

PROMPT = """Below is an excerpt from a chat between a user and an AI assistant, and a question the same user asks later about their own life or about what the assistant said.

Question: {question}
Correct answer: {answer}

Excerpt:
{excerpt}

Does the excerpt state the answer to the question, or state a fact about the user (or about what the assistant said) that would make a different answer to this exact question correct? Things about other people, other items, other events, or general advice do not count. Answer yes or no only."""

PROMPT_ABSTAIN = """Below is an excerpt from a chat between a user and an AI assistant, and a question the same user asks later about their own life. The question cannot be answered from the user's history: {answer}

Question: {question}

Excerpt:
{excerpt}

Does the excerpt state the answer to this exact question (the same entity, not a similar one)? Answer yes or no only."""


def excerpt(question, session, n=4, limit=900):
    qw = set(words(question))
    sents = []
    for t in session["turns"]:
        for s in re.split(r"(?<=[.!?\n])\s+", t["content"]):
            s = s.strip()
            if len(s) > 15:
                sents.append((len(sents), t["role"], s))
    best = sorted(sents, key=lambda x: (-len(qw & set(words(x[2]))), x[0]))[:n]
    text = "\n".join(f"{role}: {s[:300]}" for _, role, s in sorted(best))
    return text[:limit]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("hard", help="dev_hard folder (questions, histories, gold, manifest)")
    ap.add_argument("--local", required=True)
    ap.add_argument("--model", default="")
    ap.add_argument("--cache", default=str(Path.home() / ".cache" / "poligon-inject-check.jsonl"))
    ap.add_argument("--exclude", required=True, help="JSONL to append flagged {source_qid, source_session} to")
    args = ap.parse_args()
    hard = Path(args.hard)
    qs = {q["question_id"]: q for q in rj(hard / "questions.jsonl")}
    gold = {g["question_id"]: g for g in rj(hard / "gold.jsonl")}
    hist = {h["history_id"]: h for h in rj(hard / "histories.jsonl")}
    man = [m for m in rj(hard / "manifest.jsonl") if m["variant"] == "inject"]  # remove variants share injections
    have = set()
    if Path(args.exclude).exists():
        have = {(r["source_qid"], r["source_session"]) for r in rj(args.exclude)}
    judge = Judge(args.local, args.model, args.cache)
    flagged, seen, t = [], Counter(), time.time()
    total = sum(len(m["injected"]) for m in man)
    for m in man:
        q, g = qs[m["question_id"]], gold[m["question_id"]]
        sessions = {s["session_id"]: s for s in hist[q["history_id"]]["sessions"]}
        for inj in m["injected"]:
            ex = excerpt(q["question"], sessions[inj["session_id"]])
            p = (PROMPT_ABSTAIN if g["abstain"] else PROMPT).format(question=q["question"], answer=g["answer"],
                                                                   excerpt=ex)
            v = judge(p)
            seen[v] += 1
            if v == "yes" and (m["source_qid"], inj["source_session"]) not in have:
                flagged.append({"source_qid": m["source_qid"], "source_session": inj["source_session"],
                                "why": "llm: answers or contradicts", "excerpt": ex[:400]})
                have.add((m["source_qid"], inj["source_session"]))
            if sum(seen.values()) % 100 == 0:
                print(f"{sum(seen.values())}/{total} {time.time() - t:.0f}s {dict(seen)}", flush=True)
    with open(args.exclude, "a", encoding="utf-8", newline="\n") as f:
        for r in flagged:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"checked {total} injected sessions ({judge.calls} model calls), verdicts {dict(seen)}, "
          f"{len(flagged)} new pairs appended to {args.exclude}")


if __name__ == "__main__":
    main()
