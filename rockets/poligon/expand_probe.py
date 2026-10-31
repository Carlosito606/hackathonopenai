"""Does an LLM category expansion of the question recover paraphrased gold sessions? BM25 only, streamed.

    python rockets/poligon/expand_probe.py ../data/dev_hard_long --local http://127.0.0.1:8897 --workers 2

Motivation: on test-length histories most gold sessions R1 misses share at most one word with the question
(coord/findings/20261031-0335-*). For every answerable inject question the stand-in lists words a person might
have used when talking about what the question asks (it is told not to answer). Rankings compared per type, all
gold sessions in the top k sessions: plain BM25 (bm25_run.py), BM25 on question + expansion, and RRF of the two
(c=60). gbrain's LongMemEval-S report found LLM query expansion harmful (93% -> 55%), hence the fused variant.
"""
import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from bm25_run import rank  # noqa: E402
from judge import Judge, rj  # noqa: E402

PROMPT = """A user asks an AI assistant about their own past chats:
"{question}"

List up to 10 specific words or short phrases the user might have used in those past chats when talking about the things this question is about (kinds of things, places, activities, objects, people). Do not answer the question. Reply with a comma-separated list only."""
TYPES = ("knowledge-update", "multi-session", "single-session-assistant", "single-session-user",
         "temporal-reasoning", "all")
HID = re.compile(r'"history_id":\s*"([^"]+)"')


def sessions(ranked, k):
    out = []
    for sid, *_ in ranked:
        if sid not in out:
            out.append(sid)
    return out[:k]


def rrf(*rankings, c=60):
    score = defaultdict(float)
    for r in rankings:
        for i, sid in enumerate(sessions(r, 10 ** 6)):
            score[sid] += 1 / (c + i)
    return [[s, None, v] for s, v in sorted(score.items(), key=lambda x: -x[1])]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("split")
    ap.add_argument("--local", required=True)
    ap.add_argument("--model", default="")
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--cache", default=str(Path.home() / ".cache" / "poligon-expand.jsonl"))
    ap.add_argument("--k", type=int, nargs="+", default=[5, 10])
    args = ap.parse_args()
    split = Path(args.split)
    man = {m["question_id"]: m for m in rj(split / "manifest.jsonl")} if (split / "manifest.jsonl").exists() else {}
    gold = {g["question_id"]: g for g in rj(split / "gold.jsonl")}
    hold = set((HERE.parents[1] / "splits" / "dev_holdout.txt").read_text().split())
    qs = {q["question_id"]: q for q in rj(split / "questions.jsonl")
          if not gold[q["question_id"]]["abstain"] and q["question_id"] not in hold
          and man.get(q["question_id"], {"variant": "inject"})["variant"] == "inject"}
    order = sorted(qs)
    judge = Judge(args.local, args.model, args.cache)
    replies = judge.many([PROMPT.format(question=qs[q]["question"]) for q in order], args.workers, max_tokens=60)
    exp = {q: re.sub(r"\s+", " ", (r or "").replace(",", " ")).strip() for q, r in zip(order, replies)}
    byh = defaultdict(list)
    for q in order:
        byh[qs[q]["history_id"]].append(q)
    res = defaultdict(list)
    with open(split / "histories.jsonl", encoding="utf-8") as f:
        for line in f:
            m = HID.search(line[:80])
            if not m or m.group(1) not in byh:
                continue
            h = json.loads(line)
            for qid in byh[m.group(1)]:
                q, g = qs[qid], gold[qid]
                plain = rank(q["question"], h, 400)
                expanded = rank(q["question"] + " " + exp[qid], h, 400)
                for name, r in (("plain", plain), ("expanded", expanded), ("rrf", rrf(plain, expanded))):
                    for k in args.k:
                        ok = set(g["evidence"]) <= set(sessions(r, k))
                        for t in (g["question_type"], "all"):
                            res[name, k, t].append(ok)
    for k in args.k:
        print(f"all gold sessions in the top {k} sessions ({split.name}, answerable inject questions)")
        for name in ("plain", "expanded", "rrf"):
            print(f"  {name:9s} " + " ".join(f"{t[:8]}={sum(res[name, k, t]) / len(res[name, k, t]):.3f}"
                                             for t in TYPES if res[name, k, t]))
    ex = [(qs[q]["question"][:60], exp[q][:90]) for q in order[:3]]
    for e in ex:
        print("  e.g.", e[0], "->", e[1])


if __name__ == "__main__":
    main()
