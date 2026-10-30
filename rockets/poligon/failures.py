"""Failure analysis of one run: every question gets one outcome, counted per question type.

    python rockets/poligon/failures.py ../data/dev runs/<rocket>/<run_id> [--details details-judged.jsonl]
    python rockets/poligon/failures.py ../data/dev_hard RUN_DIR --details ...     # manifest.jsonl adds near-misses

Reads RUN_DIR/predictions.jsonl, RUN_DIR/evidence.jsonl (if present) and score.py details (RUN_DIR/details.jsonl
or --details, e.g. judge.py's output). The first matching outcome wins:
  ok                    answer correct (or correct abstention) and evidence F1 == 1 (answerable)
  false_abstention      gold answerable, run abstained
  answered_unanswerable gold abstain, run answered; "+near" when it cited an injected near-miss session (dev-hard)
  retrieval_miss        answer wrong and some gold session never reached the evidence pack ("none" or "partial")
  near_miss_cited       answer wrong, all gold in the pack, but an injected near-miss session was cited
  stale_value           knowledge-update answer wrong with all gold in the pack (old value or misread)
  wrong_date            temporal-reasoning answer wrong with all gold in the pack
  reader_error          other answer wrong with all gold in the pack
  citation_miss         answer correct but evidence F1 < 1 (cited too little or too much)
  unjudged              score.py could not decide and no judge verdict
Without evidence.jsonl, retrieval cannot be told apart from reading: wrong answers become reader_error.
"""
import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

TYPES = ("knowledge-update", "multi-session", "single-session-assistant", "single-session-user",
         "temporal-reasoning")
SHORT = {"knowledge-update": "k-update", "multi-session": "multi", "single-session-assistant": "ss-asst",
         "single-session-user": "ss-user", "temporal-reasoning": "temporal", "all": "all"}
ORDER = ("ok", "false_abstention", "answered_unanswerable", "answered_unanswerable+near", "retrieval_miss:none",
         "retrieval_miss:partial", "near_miss_cited", "stale_value", "wrong_date", "reader_error", "citation_miss",
         "unjudged")


def rj(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def outcome(g, p, d, pack, injected):
    cited = set(p.get("citations", []))
    if g["abstain"]:
        if p["abstain"]:
            return "ok"
        return "answered_unanswerable+near" if cited & injected else "answered_unanswerable"
    if p["abstain"]:
        return "false_abstention"
    if d["answer"] == "unjudged":
        return "unjudged"
    if d["answer"] == "correct":
        return "ok" if (d["evidence_f1"] or 0) >= 0.999 else "citation_miss"
    ev = set(g["evidence"])
    if pack is not None and not ev <= pack:
        return "retrieval_miss:none" if not ev & pack else "retrieval_miss:partial"
    if cited & injected:
        return "near_miss_cited"
    return {"knowledge-update": "stale_value", "temporal-reasoning": "wrong_date"}.get(g["question_type"],
                                                                                      "reader_error")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("split")
    ap.add_argument("run", type=Path)
    ap.add_argument("--details", type=Path)
    ap.add_argument("--out", type=Path, help="per-question outcomes (JSONL)")
    args = ap.parse_args()
    split = Path(args.split)
    gold = {g["question_id"]: g for g in rj(split / "gold.jsonl")}
    preds = {p["question_id"]: p for p in rj(args.run / "predictions.jsonl")}
    details = {d["question_id"]: d for d in rj(args.details or args.run / "details.jsonl")}
    packs = {}
    if (args.run / "evidence.jsonl").exists():
        packs = {e["question_id"]: set(e["sessions"]) for e in rj(args.run / "evidence.jsonl")}
    injected = {}
    if (split / "manifest.jsonl").exists():
        injected = {m["question_id"]: {i["session_id"] for i in m["injected"]} for m in rj(split / "manifest.jsonl")}
    rows, counts = [], defaultdict(Counter)
    for qid, p in preds.items():
        g = gold[qid]
        o = outcome(g, p, details[qid], packs.get(qid) if packs else None, injected.get(qid, set()))
        rows.append({"question_id": qid, "question_type": g["question_type"], "outcome": o})
        counts[g["question_type"]][o] += 1
        counts["all"][o] += 1
    if args.out:
        with open(args.out, "w", encoding="utf-8", newline="\n") as f:
            f.writelines(json.dumps(r) + "\n" for r in rows)
    cols = [o for o in ORDER if counts["all"][o]]
    print(f"{'outcome':27s} " + " ".join(f"{SHORT[t]:>8s}" for t in (*TYPES, "all")))
    for o in cols:
        print(f"{o:27s} " + " ".join(f"{counts[t][o]:8d}" for t in (*TYPES, "all")))
    print(f"{'n':27s} " + " ".join(f"{sum(counts[t].values()):8d}" for t in (*TYPES, "all")))


if __name__ == "__main__":
    main()
