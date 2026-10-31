"""Pack-building policies against near-miss crowding, tested on a run's candidates.jsonl (no models needed).

    python rockets/poligon/pack_policies.py ../data/dev RUN_DEV ../data/dev_hard RUN_HARD --budgets 18000 26000

Same rebuild of R1's ranked chunks as pack_budget.py, then build_evidence (root memsys.py) on:
  r1       the ranked chunks as they are (R1)
  sessdiv  the best chunk of every session first (session order = best chunk), then the rest: more distinct
           sessions before any session gets a second chunk (gbrain's "sessdiv", LongMemEval-S)
  prune    each chunk cut to its sentences sharing a content word with the question, plus one neighbour on each
           side (a rule-based take on Nano-Memory's query-driven pruning, arXiv 2604.11628): less filler per
           chunk, so more sessions fit the same budget
  both     sessdiv + prune
Per type: all gold sessions in the pack, and (where the gold answer is checkable as a phrase, as score.py
matches it) the gold answer still written in the pack text, so pruning that drops the answer sentence shows up.
"""
import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from make_dev_hard import AnswerMatcher, words  # noqa: E402
from pack_budget import SHORT, rebuild, rj  # noqa: E402  (also puts the repo root on sys.path)
from memsys import build_evidence, load_split  # noqa: E402

SENT = re.compile(r"(?<=[.!?\n])\s+")


def sessdiv(cands):
    first, rest, seen = [], [], set()
    for c in cands:
        (rest if c["session_id"] in seen else first).append(c)
        seen.add(c["session_id"])
    return first + rest


def prune(cands, question):
    qw = set(words(question))
    out = []
    for c in cands:
        sents = [s for s in SENT.split(c["text"]) if s.strip()]
        hit = [i for i, s in enumerate(sents) if qw & set(words(s))]
        keep = sorted({j for i in hit for j in (i - 1, i, i + 1) if 0 <= j < len(sents)})
        text = " ".join(sents[i] for i in keep) if keep else c["text"][:200]
        out.append(dict(c, text=text))
    return out


POLICIES = {"r1": lambda cs, q: cs, "sessdiv": lambda cs, q: sessdiv(cs), "prune": lambda cs, q: prune(cs, q),
            "both": lambda cs, q: prune(sessdiv(cs), q)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pairs", nargs="+", help="split_dir run_dir [split_dir run_dir ...]")
    ap.add_argument("--budgets", type=int, nargs="+", default=[18000, 26000])
    args = ap.parse_args()
    for split, run in zip(args.pairs[::2], args.pairs[1::2]):
        hist, qs, gold = load_split(split)
        qs = {q["question_id"]: q for q in qs}
        cands = {r["question_id"]: r["ranked"] for r in rj(Path(run) / "candidates.jsonl")}
        res = defaultdict(list)
        for qid, ranked in cands.items():
            q, g = qs[qid], gold[qid]
            if g["abstain"]:
                continue
            h = hist[q["history_id"]]
            base = rebuild(h, ranked)
            match = AnswerMatcher(g)
            checkable = bool(match.phrases)
            for name, fn in POLICIES.items():
                cs = fn(base, q["question"])
                for b in args.budgets:
                    ev = build_evidence(h, cs, budget=b)
                    ids = {e["id"] for e in ev}
                    for t in (g["question_type"], "all"):
                        res[name, b, t, "gold"].append(set(g["evidence"]) <= ids)
                        if checkable:
                            res[name, b, t, "answer"].append(match("\n".join(e["text"] for e in ev)))
                        res[name, b, t, "sessions"].append(len(ev))
        types = ["knowledge-update", "multi-session", "single-session-assistant", "single-session-user",
                 "temporal-reasoning", "all"]
        mean = lambda xs: sum(xs) / len(xs) if xs else float("nan")
        print(f"\n== {split}: all gold sessions in pack | gold answer phrase in pack (checkable only) | sessions")
        print(f"{'policy':8s} {'budget':>6s} " + " ".join(f"{SHORT[t]:>9s}" for t in types) + "  answer(all)  sess")
        for name in POLICIES:
            for b in args.budgets:
                print(f"{name:8s} {b:6d} " + " ".join(f"{mean(res[name, b, t, 'gold']):9.3f}" for t in types) +
                      f"  {mean(res[name, b, 'all', 'answer']):11.3f}  {mean(res[name, b, 'all', 'sessions']):4.1f}")


if __name__ == "__main__":
    main()
