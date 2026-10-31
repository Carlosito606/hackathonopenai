"""One POLIGON report for any rocket: dev vs dev-hard v2 vs dev-hard-long, from its run artifacts only.

    python rockets/poligon/report.py ../data RUN_DEV RUN_HARD [RUN_LONG]

Each RUN_* is a core/CONTRACT.md run folder with candidates.jsonl and evidence.jsonl on that split (dev minus
holdout, ../data/dev_hard, ../data/dev_hard_long). Prints, per question type, paired by source question:
  1. all gold sessions in the evidence pack, and in the top 5 sessions of the candidates;
  2. for every answerable question that misses a gold session in its pack: was a gold session outside the
     candidates (retrieval) or among them but not packed (budget / pack order);
  3. near-miss intrusion: injected sessions per pack.
No models, no histories loaded (only questions, gold, manifests), so it runs anywhere in seconds. For why packs
lose gold (crowding vs ranking) run crowding.py; for pack orders, pack_policies.py.
"""
import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

TYPES = ("knowledge-update", "multi-session", "single-session-assistant", "single-session-user",
         "temporal-reasoning", "all")
SHORT = {"knowledge-update": "k-update", "multi-session": "multi", "single-session-assistant": "ss-asst",
         "single-session-user": "ss-user", "temporal-reasoning": "temporal", "all": "all"}


def rj(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def top_sessions(ranked, k):
    out = []
    for sid, *_ in ranked:
        if sid not in out:
            out.append(sid)
            if len(out) == k:
                break
    return out


def load(split, run):
    gold = {g["question_id"]: g for g in rj(split / "gold.jsonl")}
    man = {m["question_id"]: m for m in rj(split / "manifest.jsonl")} if (split / "manifest.jsonl").exists() else {}
    cands = {r["question_id"]: r["ranked"] for r in rj(run / "candidates.jsonl")}
    packs = {r["question_id"]: r["sessions"] for r in rj(run / "evidence.jsonl")}
    rows = {}
    for qid, pack in packs.items():
        g = gold[qid]
        m = man.get(qid, {"source_qid": qid, "variant": "inject", "injected": []})
        if g["abstain"] or m["variant"] != "inject" or qid not in cands:
            continue
        gs = set(g["evidence"])
        incand = {r[0] for r in cands[qid]}
        rows[m["source_qid"]] = {"type": g["question_type"], "pack": gs <= set(pack),
                                 "top5": gs <= set(top_sessions(cands[qid], 5)),
                                 "miss": None if gs <= set(pack) else ("retrieval" if not gs <= incand else "budget"),
                                 "injected": len(set(pack) & {i["session_id"] for i in m["injected"]})}
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("data", type=Path, help="folder with dev/, dev_hard/, dev_hard_long/")
    ap.add_argument("runs", type=Path, nargs="+", help="run folders on dev, dev_hard[, dev_hard_long]")
    ap.add_argument("--splits", nargs="+", default=["dev", "dev_hard", "dev_hard_long"],
                    help="split folder names under data, in the order of the runs (e.g. dev dev_hard_v1)")
    args = ap.parse_args()
    names = tuple(args.splits[:len(args.runs)])
    res = {n: load(args.data / n, r) for n, r in zip(names, args.runs)}
    common = set.intersection(*(set(r) for r in res.values()))
    print(f"{len(common)} answerable questions present in every run (paired by source question)\n")
    for metric, label in (("pack", "all gold sessions in the evidence pack"), ("top5", "all gold in the top 5 sessions")):
        print(label)
        print(f"  {'type':9s} " + " ".join(f"{n:>14s}" for n in names))
        for t in TYPES:
            qs = [q for q in common if t == "all" or res[names[0]][q]["type"] == t]
            if qs:
                print(f"  {SHORT[t]:9s} " + " ".join(f"{sum(res[n][q][metric] for q in qs) / len(qs):14.3f}"
                                                   for n in names))
        print()
    print("questions missing a gold session in the pack: gold outside the candidates / among them but not packed")
    for n in names:
        c = Counter(res[n][q]["miss"] for q in common if res[n][q]["miss"])
        by = defaultdict(Counter)
        for q in common:
            if res[n][q]["miss"]:
                by[SHORT[res[n][q]["type"]]][res[n][q]["miss"]] += 1
        detail = ", ".join(f"{t} {v['retrieval']}/{v['budget']}" for t, v in sorted(by.items()))
        print(f"  {n:14s} {c['retrieval']:3d} / {c['budget']:3d}   ({detail})")
    for n in names[1:]:
        inj = [res[n][q]["injected"] for q in common]
        print(f"\nnear-miss sessions per pack on {n}: {sum(inj) / len(inj):.2f} "
              f"(packs with at least one: {sum(x > 0 for x in inj) / len(inj):.0%})")


if __name__ == "__main__":
    main()
