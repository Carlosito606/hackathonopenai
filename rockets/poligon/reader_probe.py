"""Does a reader take test-like traps? R1's prompt on small R1-style packs, with and without the trap aside.

    python rockets/poligon/reader_probe.py ../data/dev_hard ../data/poligon_runs/traps.jsonl \\
        --local http://127.0.0.1:8897 --out ../data/poligon_runs/reader-probe.jsonl

For every dev-hard question (inject and remove variants) whose source question has a trap (make_traps.py), the
history is read twice: as built, and with the trap aside appended to the same injected session and user turn that
make_dev_hard.py --traps picks (same seeded choice), so no trap build is needed and only the needed histories
are loaded (low memory). Each history: BM25 over all turns (bm25_run.py), R1's build_evidence at --budget chars
(small enough for a 4k-token stand-in), R1's GUIDE (prepare.py) and the kit's build_message; the reader's final
answer line as the kit parses it. Reports per variant (inject: answerable, gold unchanged; remove: gold abstain):
gold, abstained, "trap taken" (the answer's words all come from the trap sentence), other answer.
The stand-in is a weak reader; compare plain vs trap, never read it as Reactor's score.
"""
import argparse
import json
import re
import sys
import urllib.request
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
from make_dev_hard import AnswerMatcher, rng_for, words  # noqa: E402
from memsys import TEMPORAL, build_evidence, day_no, parse_date, session_chunks  # noqa: E402
from prepare import COUNT, COUNTING, DATES, GUIDE  # noqa: E402

REF = "0000beef"
HID = re.compile(r'"history_id":\s*"([^"]+)"')


def with_trap(h, m, sentence, seed):
    """The history with the trap appended where make_dev_hard.py --traps puts it; returns (history, session id)."""
    trng = rng_for(seed, m["source_qid"], "trapsite")
    site_id = trng.choice(m["injected"])["session_id"]
    sessions = []
    for s in h["sessions"]:
        if s["session_id"] == site_id:
            users = [j for j, t in enumerate(s["turns"]) if t["role"] == "user"]
            j = trng.choice(users)
            s = dict(s, turns=[dict(t, content=t["content"].rstrip() + " " + sentence) if k == j else t
                               for k, t in enumerate(s["turns"])])
        sessions.append(s)
    return dict(h, sessions=sessions), site_id


def n_tokens(url, text):
    req = urllib.request.Request(url + "/tokenize", json.dumps({"content": text}).encode(),
                                 {"Content-Type": "application/json"})
    return len(json.loads(urllib.request.urlopen(req, timeout=120).read())["tokens"])


def fitted_message(q, h, budget, url, limit):
    """ask_message, shrinking the evidence budget (as prepare.py does for chars) until it fits the context."""
    while True:
        msg, ids = ask_message(q, h, budget)
        if budget <= 2000 or n_tokens(url, msg) <= limit:
            return msg, ids
        budget -= 1000


def ask_message(q, h, budget):
    si = {s["session_id"]: i for i, s in enumerate(h["sessions"])}
    cands = []
    for sid, turn, score in rank(q["question"], h, 60):
        s = h["sessions"][si[sid]]
        piece = next(p for t, _, p in session_chunks(s) if t == turn)
        cands.append({"si": si[sid], "session_id": sid, "turn": turn, "role": s["turns"][turn]["role"],
                      "text": piece, "score": score})
    temporal = bool(TEMPORAL.search(q["question"]))
    ev = build_evidence(h, cands, budget=budget, dates=temporal)
    extra = DATES.format(today=day_no(parse_date(q["question_date"]))) if temporal else ""
    if COUNTING.search(q["question"]):
        extra += COUNT
    question = q["question"].strip() + "\n" + GUIDE.format(extra=extra)
    msg = kit.build_message(question, kit.load_evidence(json.dumps(ev)), REF,
                            kit.parse_question_date(q["question_date"]))
    return msg, {e["id"] for e in ev}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("hard", help="dev-hard build without traps (e.g. ../data/dev_hard)")
    ap.add_argument("traps", help="make_traps.py output")
    ap.add_argument("--local", required=True)
    ap.add_argument("--model", default="")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--budget", type=int, default=7000)
    ap.add_argument("--max-tokens", type=int, default=300)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--ctx", type=int, default=4096, help="the server's context per slot (tokens)")
    ap.add_argument("--cache", default=str(Path.home() / ".cache" / "poligon-reader.jsonl"))
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    hard = Path(args.hard)
    traps = {r["source_qid"]: r for r in rj(args.traps)}
    man = {m["question_id"]: m for m in rj(hard / "manifest.jsonl") if m["source_qid"] in traps}
    qs = {q["question_id"]: q for q in rj(hard / "questions.jsonl") if q["question_id"] in man}
    gold = {g["question_id"]: g for g in rj(hard / "gold.jsonl") if g["question_id"] in man}
    need = {q["history_id"] for q in qs.values()}
    hist = {}
    with open(hard / "histories.jsonl", encoding="utf-8") as f:  # stream: keep only the needed histories
        for line in f:
            m = HID.search(line[:80])
            if m and m.group(1) in need:
                hist[m.group(1)] = json.loads(line)
    jobs = []
    for qid in sorted(man):
        m, q, g = man[qid], qs[qid], gold[qid]
        h = hist[q["history_id"]]
        trapped, site = with_trap(h, m, traps[m["source_qid"]]["sentence"], args.seed)
        for name, hh in (("plain", h), ("trap", trapped)):
            msg, ids = fitted_message(q, hh, args.budget, args.local.rstrip("/"), args.ctx - args.max_tokens - 64)
            jobs.append((name, m, g, site, site in ids, msg))
    print(f"{len(jobs)} reader calls ({len(jobs) // 2} questions x plain/trap)", flush=True)
    judge = Judge(args.local, args.model, args.cache)
    replies = judge.many([j[5] for j in jobs], args.workers, max_tokens=args.max_tokens)
    res, rows = defaultdict(Counter), []
    for (name, m, g, site, in_pack, _), reply in zip(jobs, replies):
        trap = traps[m["source_qid"]]
        ans = kit.final_answers(reply or "").get(REF)
        if (reply or "").startswith("ERROR"):
            out = "server error"
        elif ans is None:
            out = "no final line"
        elif kit._INSUFFICIENT.match(ans):
            out = "abstained"
        elif not g["abstain"] and AnswerMatcher(g)(ans):
            out = "gold"
        else:
            aw = set(words(ans)) - set(words(g["answer"] if not g["abstain"] else ""))
            out = "trap taken" if aw and aw <= set(words(trap["sentence"])) else "other answer"
        key = (name, m["variant"])
        res[key][out] += 1
        res[key]["n"] += 1
        res[key]["trap session in pack"] += in_pack
        rows.append({"question_id": m["question_id"], "split": name, "variant": m["variant"], "kind": trap["kind"],
                     "answer": ans, "outcome": out, "trap_session_in_pack": in_pack})
    with open(args.out, "w", encoding="utf-8", newline="\n") as f:
        f.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)
    for (name, variant), c in sorted(res.items()):
        print(f"{name:5s} {variant:6s} " + "  ".join(f"{k}={c[k]}" for k in
              ("n", "gold", "abstained", "trap taken", "other answer", "no final line", "server error",
               "trap session in pack")))


if __name__ == "__main__":
    main()
