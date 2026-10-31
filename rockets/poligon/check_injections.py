"""LLM audit of dev-hard's injected sessions: can the question be answered from one? -> suspect list.

    python rockets/poligon/check_injections.py ../data/dev_hard --local http://127.0.0.1:8897 --calibrate 150
    python rockets/poligon/check_injections.py ../data/dev_hard --local http://127.0.0.1:8897 \\
        --exclude rockets/poligon/exclude.jsonl
    python rockets/poligon/make_dev_hard.py ../data/dev ../data/dev_hard --exclude rockets/poligon/exclude.jsonl \\
        --ids splits/dev_hard_ids.txt                                   # then audit again until nothing is added

An injected session should NOT answer its question. The model reads a short excerpt (the sentences sharing most
words with the question, plus their neighbours: a 7B model on CPU needs short prompts) and answers the question
from it, or says NONE. Any other reply marks the pair as suspect: the session states the answer or a conflicting
fact about the user. Suspects are appended to --exclude as {"source_qid", "source_session", "why", "reply"};
make_dev_hard.py never injects them again. Replies are cached in --cache, so a second round only asks about the
replacement sessions.

--calibrate N measures the method first, on N single-session questions whose answer is written in an evidence
session: excerpt coverage (answer in the excerpt), model recall on the gold session (reply not NONE, and reply
matching gold), and NONE on a random session of another history.
"""
import argparse
import json
import random
import re
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from judge import Judge, rj  # noqa: E402
from make_dev_hard import AnswerMatcher, stext, words  # noqa: E402

PROMPT = """Below is an excerpt from a chat between a user and an AI assistant. Answer the question using ONLY this excerpt. Questions are asked by the same user, so "I" and "my" mean the user. If the excerpt does not state the answer to this exact question, reply NONE.

Excerpt:
{excerpt}

Question: {question}

Reply with the short answer only, or NONE."""


def excerpt(question, session, n=4, limit=1500):
    """The n sentences sharing most words with the question, each with its neighbours, in session order."""
    qw = set(words(question))
    sents = []
    for t in session["turns"]:
        for s in re.split(r"(?<=[.!?\n])\s+", t["content"]):
            s = s.strip()
            if len(s) > 15:
                sents.append((t["role"], s))
    best = sorted(range(len(sents)), key=lambda i: (-len(qw & set(words(sents[i][1]))), i))[:n]
    keep = sorted({j for i in best for j in (i - 1, i, i + 1) if 0 <= j < len(sents)})
    text = "\n".join(f"{sents[i][0]}: {sents[i][1][:300]}" for i in keep)
    return text[:limit]


def is_none(reply):
    return reply is None or not reply.strip() or bool(re.match(r"\W*none\b", reply.strip(), re.I))


def calibrate(args, judge, qs, gold, hist, man):
    rng = random.Random(0)
    cases = []
    for m in sorted(man, key=lambda m: m["question_id"]):
        g = gold[m["question_id"]]
        if g["abstain"] or g["question_type"] not in ("single-session-user", "single-session-assistant"):
            continue
        match = AnswerMatcher(g)
        sessions = {s["session_id"]: s for s in hist[qs[m["question_id"]]["history_id"]]["sessions"]}
        ev = [sessions[s] for s in g["evidence"] if match(stext(sessions[s]))]
        if ev:
            cases.append((m, g, match, ev[0]))
    cases = rng.sample(cases, min(args.calibrate, len(cases)))
    others = [s for h in sorted(hist) for s in hist[h]["sessions"]]
    prompts, rows = [], []
    for m, g, match, ev in cases:
        q = qs[m["question_id"]]["question"]
        own = {s["session_id"] for s in hist[qs[m["question_id"]]["history_id"]]["sessions"]}
        other = rng.choice([s for s in rng.sample(others, 20) if s["session_id"] not in own])
        ex_ev, ex_other = excerpt(q, ev), excerpt(q, other)
        rows.append((match, match(ex_ev)))
        prompts += [PROMPT.format(excerpt=ex_ev, question=q), PROMPT.format(excerpt=ex_other, question=q)]
    replies = judge.many(prompts, args.workers, max_tokens=args.max_tokens)
    n = len(rows)
    cover = sum(c for _, c in rows)
    said = sum(not is_none(replies[2 * i]) for i in range(n))
    right = sum(match(replies[2 * i] or "") for i, (match, _) in enumerate(rows))
    said_cov = sum(not is_none(replies[2 * i]) for i, (_, c) in enumerate(rows) if c)
    none_other = sum(is_none(replies[2 * i + 1]) for i in range(n))
    print(f"{n} single-session questions with the answer written in an evidence session")
    print(f"  excerpt contains the answer          {cover:4d}/{n}  {cover / n:.3f}")
    print(f"  gold session: reply not NONE         {said:4d}/{n}  {said / n:.3f}  (when excerpt covers: "
          f"{said_cov}/{cover})")
    print(f"  gold session: reply matches gold     {right:4d}/{n}  {right / n:.3f}")
    print(f"  random other session: NONE           {none_other:4d}/{n}  {none_other / n:.3f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("hard", help="dev_hard folder (questions, histories, gold, manifest)")
    ap.add_argument("--local", required=True)
    ap.add_argument("--model", default="")
    ap.add_argument("--cache", default=str(Path.home() / ".cache" / "poligon-inject-check.jsonl"))
    ap.add_argument("--exclude", help="JSONL to append suspect {source_qid, source_session} pairs to")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--max-tokens", type=int, default=24)
    ap.add_argument("--calibrate", type=int, default=0, help="instead of auditing: N questions with known answers")
    args = ap.parse_args()
    hard = Path(args.hard)
    qs = {q["question_id"]: q for q in rj(hard / "questions.jsonl")}
    gold = {g["question_id"]: g for g in rj(hard / "gold.jsonl")}
    hist = {h["history_id"]: h for h in rj(hard / "histories.jsonl")}
    man = [m for m in rj(hard / "manifest.jsonl") if m["variant"] == "inject"]  # remove variants share injections
    judge = Judge(args.local, args.model, args.cache)
    if args.calibrate:
        return calibrate(args, judge, qs, gold, hist, man)
    if not args.exclude:
        ap.error("--exclude is required unless --calibrate")
    have = {(r["source_qid"], r["source_session"]) for r in rj(args.exclude)} if Path(args.exclude).exists() else set()
    items = []
    for m in man:
        q = qs[m["question_id"]]
        sessions = {s["session_id"]: s for s in hist[q["history_id"]]["sessions"]}
        for inj in m["injected"]:
            ex = excerpt(q["question"], sessions[inj["session_id"]])
            items.append((m["source_qid"], inj["source_session"], ex, PROMPT.format(excerpt=ex, question=q["question"])))
    flagged, seen, t = [], Counter(), time.time()
    for i in range(0, len(items), 100):  # in blocks, so progress shows and a crash keeps the cached replies
        block = items[i:i + 100]
        for (sq, ss, ex, _), reply in zip(block, judge.many([it[3] for it in block], args.workers, args.max_tokens)):
            none = is_none(reply)
            seen["none" if none else "answer"] += 1
            if not none and (sq, ss) not in have:
                flagged.append({"source_qid": sq, "source_session": ss, "why": "llm answers from it",
                                "reply": reply.strip()[:100], "excerpt": ex[:400]})
                have.add((sq, ss))
        print(f"{min(i + 100, len(items))}/{len(items)} {time.time() - t:.0f}s {dict(seen)}", flush=True)
    with open(args.exclude, "a", encoding="utf-8", newline="\n") as f:
        for r in flagged:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"audited {len(items)} injected sessions ({judge.calls} model calls), replies {dict(seen)}, "
          f"{len(flagged)} new suspect pairs appended to {args.exclude}")


if __name__ == "__main__":
    main()
