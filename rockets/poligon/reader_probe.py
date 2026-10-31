"""Does a reader take test-like traps? R1's prompt on small R1-style packs, two dev-hard builds compared.

    python rockets/poligon/reader_probe.py ../data/dev_hard ../data/dev_hard_trap --local http://127.0.0.1:8897 \\
        --out ../data/poligon_runs/reader-probe.jsonl

For every question of the trap build whose manifest marks a trap (and its twin in the plain build, matched by
source question and variant): BM25 over all turns (bm25_run.py), R1's build_evidence at --budget chars (small
enough for a 4k-token stand-in), R1's GUIDE (prepare.py) and the kit's build_message, then the reader's final
answer line as the kit parses it. Reports per variant (inject: answerable, gold unchanged; remove: gold abstain):
the reader abstains, answers with gold, or answers with a phrase taken from the trap sentence ("trap taken").
The stand-in is a weak reader; compare plain vs trap, never read it as Reactor's score.
"""
import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "reactor"))
import client as kit  # noqa: E402
from bm25_run import rank  # noqa: E402
from judge import Judge, rj  # noqa: E402
from make_dev_hard import AnswerMatcher, words  # noqa: E402
from memsys import TEMPORAL, build_evidence, day_no, load_split, parse_date, session_chunks  # noqa: E402
from prepare import COUNT, COUNTING, DATES, GUIDE  # noqa: E402


def pack(q, h, budget):
    """R1-style evidence from BM25-ranked turns (first chunk of each ranked turn)."""
    si = {s["session_id"]: i for i, s in enumerate(h["sessions"])}
    cands = []
    for sid, turn, score in rank(q["question"], h, 60):
        s = h["sessions"][si[sid]]
        piece = next(p for t, _, p in session_chunks(s) if t == turn)
        cands.append({"si": si[sid], "session_id": sid, "turn": turn, "role": s["turns"][turn]["role"],
                      "text": piece, "score": score})
    temporal = bool(TEMPORAL.search(q["question"]))
    return build_evidence(h, cands, budget=budget, dates=temporal), temporal


def message(q, evidence, temporal):
    extra = DATES.format(today=day_no(parse_date(q["question_date"]))) if temporal else ""
    if COUNTING.search(q["question"]):
        extra += COUNT
    question = q["question"].strip() + "\n" + GUIDE.format(extra=extra)
    passages = kit.load_evidence(json.dumps(evidence))
    return kit.build_message(question, passages, "0000beef", kit.parse_question_date(q["question_date"]))


def final_answer(reply):
    finals = kit.final_answers(reply or "")
    return finals.get("0000beef")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plain", help="dev-hard build without traps (e.g. ../data/dev_hard)")
    ap.add_argument("trap", help="the same build with --traps")
    ap.add_argument("--local", required=True)
    ap.add_argument("--model", default="")
    ap.add_argument("--budget", type=int, default=9000)
    ap.add_argument("--max-tokens", type=int, default=400)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--cache", default=str(Path.home() / ".cache" / "poligon-reader.jsonl"))
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    splits = {}
    for name in ("plain", "trap"):
        hist, qs, gold = load_split(getattr(args, name))
        man = {m["question_id"]: m for m in rj(Path(getattr(args, name)) / "manifest.jsonl")}
        splits[name] = (hist, {q["question_id"]: q for q in qs}, gold, man)
    _, tqs, tgold, tman = splits["trap"]
    trap_text = {}
    for m in tman.values():
        h = splits["trap"][0][tqs[m["question_id"]]["history_id"]]
        for i in m["injected"]:
            if "trap" in i:
                s = next(s for s in h["sessions"] if s["session_id"] == i["session_id"])
                trap_text[m["source_qid"], m["variant"]] = (i["trap"], s)
    pkey = {(m["source_qid"], m["variant"]): qid for qid, m in splits["plain"][3].items()}
    jobs = []
    for qid, m in sorted(tman.items()):
        key = (m["source_qid"], m["variant"])
        if key not in trap_text or key not in pkey:
            continue
        for name, sqid in (("plain", pkey[key]), ("trap", qid)):
            hist, qs, gold, _ = splits[name]
            q = qs[sqid]
            ev, temporal = pack(q, hist[q["history_id"]], args.budget)
            jobs.append((name, key, sqid, gold[sqid], ev, message(q, ev, temporal)))
    print(f"{len(jobs)} reader calls ({len(jobs) // 2} trapped questions x plain/trap)", flush=True)
    judge = Judge(args.local, args.model, args.cache)
    replies = judge.many([j[5] for j in jobs], args.workers, max_tokens=args.max_tokens)
    res, rows = defaultdict(Counter), []
    for (name, key, sqid, g, ev, _), reply in zip(jobs, replies):
        kind, trap_session = trap_text[key]
        ans = final_answer(reply)
        trap_sent = trap_session["turns"]
        in_pack = trap_session["session_id"] in {e["id"] for e in ev}
        if ans is None:
            out = "no final line"
        elif kit._INSUFFICIENT.match(ans):
            out = "abstained"
        elif not g["abstain"] and AnswerMatcher(g)(ans):
            out = "gold"
        else:
            trap_words = set(words(" ".join(t["content"] for t in trap_sent if t["role"] == "user")[-400:]))
            aw = set(words(ans)) - set(words(g["answer"] if not g["abstain"] else ""))
            out = "trap taken" if aw and aw <= trap_words and name == "trap" else "other answer"
        res[name, key[1]][out] += 1
        res[name, key[1]]["trap in pack"] += in_pack and name == "trap"
        rows.append({"question_id": sqid, "split": name, "variant": key[1], "kind": kind, "answer": ans,
                     "outcome": out, "trap_in_pack": in_pack})
    with open(args.out, "w", encoding="utf-8", newline="\n") as f:
        f.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)
    for (name, variant), c in sorted(res.items()):
        n = sum(v for k, v in c.items() if k != "trap in pack")
        print(f"{name:5s} {variant:6s} n={n:3d} " + "  ".join(f"{k}={c[k]}" for k in
              ("gold", "abstained", "trap taken", "other answer", "no final line", "trap in pack")))


if __name__ == "__main__":
    main()
