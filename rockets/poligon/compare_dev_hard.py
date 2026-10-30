"""Retrieval on dev vs dev-hard, paired by source question, per type.

    python rockets/poligon/compare_dev_hard.py ../data/dev ../data/dev_hard DEV/candidates.jsonl HARD/candidates.jsonl
    python rockets/poligon/compare_dev_hard.py ../data/dev ../data/dev_hard DEV/evidence.jsonl HARD/evidence.jsonl

Columns, top-k sessions of each candidates.jsonl (session order = first appearance in the ranking), or every
session of the pack when given evidence.jsonl files (k is then ignored):
  dev / hard   share of answerable questions with ALL gold sessions in the top k (same questions on both splits)
  drop         dev minus hard, in points (one point is about one question per type)
  intrude      share of hard questions with at least one injected near-miss session in the top k
  inj@k        mean number of injected sessions in the top k
Unanswerable questions ("remove" variants and dev's own) only enter the intrude columns.
"""
import argparse
import json
from collections import defaultdict
from pathlib import Path

TYPES = ("knowledge-update", "multi-session", "single-session-assistant", "single-session-user",
         "temporal-reasoning")
SHORT = {"knowledge-update": "k-update", "multi-session": "multi", "single-session-assistant": "ss-asst",
         "single-session-user": "ss-user", "temporal-reasoning": "temporal", "all": "all"}


def rj(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def sessions(row, k):
    if "sessions" in row:  # evidence.jsonl: the whole pack
        return row["sessions"]
    out = []
    for sid, *_ in row["ranked"]:
        if sid not in out:
            out.append(sid)
            if len(out) == k:
                break
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dev")
    ap.add_argument("hard")
    ap.add_argument("dev_cands")
    ap.add_argument("hard_cands")
    ap.add_argument("--k", type=int, default=5)
    args = ap.parse_args()
    dgold = {g["question_id"]: g for g in rj(Path(args.dev) / "gold.jsonl")}
    man = rj(Path(args.hard) / "manifest.jsonl")
    dc = {r["question_id"]: r for r in rj(args.dev_cands)}
    hc = {r["question_id"]: r for r in rj(args.hard_cands)}
    acc = defaultdict(lambda: defaultdict(list))
    for m in man:
        if m["question_id"] not in hc:
            continue
        t = m["question_type"]
        top = sessions(hc[m["question_id"]], args.k)
        inj = {i["session_id"] for i in m["injected"]}
        n_inj = sum(s in inj for s in top)
        for key in (t, "all"):
            acc[key]["intrude"].append(n_inj > 0)
            acc[key]["inj"].append(n_inj)
        g = dgold[m["source_qid"]]
        if m["variant"] == "inject" and not g["abstain"] and m["source_qid"] in dc:
            ev = set(g["evidence"])
            for key in (t, "all"):
                acc[key]["dev"].append(ev <= set(sessions(dc[m["source_qid"]], args.k)))
                acc[key]["hard"].append(ev <= set(top))
    mean = lambda xs: sum(xs) / len(xs) if xs else float("nan")
    where = "the evidence pack" if "sessions" in next(iter(hc.values())) else f"top {args.k} sessions"
    print(f"all gold sessions in {where}, paired answerable questions; near-miss intrusion on dev-hard")
    print(f"{'type':9s} {'n':>4s} {'dev':>6s} {'hard':>6s} {'drop':>6s} {'intrude':>8s} {'inj@k':>6s}")
    for key in (*TYPES, "all"):
        a = acc[key]
        d, h = mean(a["dev"]), mean(a["hard"])
        print(f"{SHORT[key]:9s} {len(a['dev']):4d} {d:6.3f} {h:6.3f} {100 * (d - h):6.1f} {mean(a['intrude']):8.3f} "
              f"{mean(a['inj']):6.2f}")


if __name__ == "__main__":
    main()
