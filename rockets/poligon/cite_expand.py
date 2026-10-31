"""Add one evidence citation the reader left out, by code, after the run (answers untouched).

WARNING: the expansion helps on dev but costs ~7 points of evidence F1 on dev-hard (near-miss sessions share the
most question words, so it cites traps): coord/findings/20261031-0300-*, CORRECTION. Only --abstentions-only
(cite the best pack session when we abstain, where the score is 0 anyway) is safe on test-like data.

    python rockets/poligon/cite_expand.py predictions.jsonl plan.jsonl ../data/test/histories.jsonl \\
        --out predictions-cited.jsonl [--ratio 0.8]

Reactor under-cites: on R1's 39 Reactor calibration answers (dev) every citation miss with a correct answer was a
gold session left out, never an extra one (knowledge-update: the old-value session; temporal: the other event).
For each answered question this adds the pack session (plan.jsonl evidence ids) that shares the most question
words with the question (user turns of the session), when it shares at least --ratio times as many as the best
session already cited. When the reader cited nothing, the best pack session is cited. Abstentions keep their
empty citations unless --cite-abstentions (evidence F1 also counts answerable questions we abstained on).
The answer, the abstention and Reactor's own citations are never changed or removed. Standard library only.
"""
import argparse
import json
import re

STOP = set("""the a an of to and in on for is it i my me you your was what how many did do does with at that this
from by be are have has as or which when who where were can could would should will just about some any all also so
if but not no than then there their they them we our""".split())


def words(text):
    return {w for w in re.findall(r"[a-z0-9']+", text.lower()) if w not in STOP and len(w) > 2}


def rj(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def expand(cited, pack, qw, text, ratio):
    """cited + at most one pack session; text(sid) -> its words."""
    others = sorted((s for s in pack if s not in cited), key=lambda s: (-len(qw & text(s)), pack.index(s)))
    if not others:
        return cited
    if not cited:
        return [others[0]]
    best = max(len(qw & text(s)) for s in cited)
    if best and len(qw & text(others[0])) >= ratio * best:
        return cited + [others[0]]
    return cited


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("predictions")
    ap.add_argument("plan", help="prepare.py's plan.jsonl (question, history_id, evidence ids)")
    ap.add_argument("histories")
    ap.add_argument("--out", required=True)
    ap.add_argument("--ratio", type=float, default=0.8)
    ap.add_argument("--cite-abstentions", action="store_true")
    ap.add_argument("--abstentions-only", action="store_true",
                    help="leave answered questions alone; only cite the best pack session on abstentions")
    args = ap.parse_args()
    plan = {p["question_id"]: p for p in rj(args.plan)}
    need = {p["history_id"] for p in plan.values()}
    text = {}
    with open(args.histories, encoding="utf-8") as f:
        for line in f:
            h = json.loads(line)
            if h["history_id"] in need:
                for s in h["sessions"]:
                    text[h["history_id"], s["session_id"]] = words(
                        " ".join(t["content"] for t in s["turns"] if t["role"] == "user"))
    out, added = [], 0
    for p in rj(args.predictions):
        q = plan.get(p["question_id"])
        if q and args.abstentions_only and not p["abstain"]:
            q = None
        if q and (not p["abstain"] or args.cite_abstentions or args.abstentions_only):
            question = q["question"].split("\n(How to answer")[0]
            pack = [e["id"] for e in q["evidence"]]
            new = expand(list(p["citations"]), pack, words(question),
                         lambda s: text.get((q["history_id"], s), set()), args.ratio)
            added += len(new) - len(p["citations"])
            p = dict(p, citations=new)
        out.append(p)
    with open(args.out, "w", encoding="utf-8", newline="\n") as f:
        f.writelines(json.dumps(p, ensure_ascii=False) + "\n" for p in out)
    print(f"{len(out)} predictions, {added} citations added -> {args.out}")


if __name__ == "__main__":
    main()
