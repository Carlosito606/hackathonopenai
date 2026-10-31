"""Fuse expanded BM25 (expand_probe.py) with R1 final session rankings (RRF) and count all gold in the top k.

    python rockets/poligon/fuse_probe.py   # run from the repo root; reads ../data and runs/r1 exports under ../data/poligon_runs/r1f
"""
import json, re, sys
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, "rockets/poligon")
from bm25_run import rank
from judge import Judge, rj
from expand_probe import PROMPT, sessions, rrf
D = "../../../data"
judge = Judge("http://127.0.0.1:8897", "", str(Path.home() / ".cache" / "poligon-expand.jsonl"))
hold = set(open("splits/dev_holdout.txt").read().split())
for split, run in (("dev", "dev"), ("dev_hard", "dev-hard-v2"), ("dev_hard_long", "dev-hard-long")):
    gold = {g["question_id"]: g for g in rj(f"{D}/{split}/gold.jsonl")}
    r1 = {r["question_id"]: r["ranked"] for r in rj(f"{D}/poligon_runs/r1f/{run}/candidates.jsonl")}
    qs = {q["question_id"]: q for q in rj(f"{D}/{split}/questions.jsonl") if q["question_id"] in r1
          and not gold[q["question_id"]]["abstain"] and q["question_id"] not in hold}
    exp = {qid: re.sub(r"\s+", " ", (judge.ask(PROMPT.format(question=q["question"]), 60)["raw"] or "").replace(",", " "))
           for qid, q in qs.items()}
    byh = defaultdict(list)
    for qid, q in qs.items(): byh[q["history_id"]].append(qid)
    res = defaultdict(list)
    for line in open(f"{D}/{split}/histories.jsonl", encoding="utf-8"):
        m = re.search(r'"history_id":\s*"([^"]+)"', line[:80])
        if not m or m.group(1) not in byh: continue
        h = json.loads(line)
        for qid in byh[m.group(1)]:
            g = gold[qid]; gs = set(g["evidence"])
            base = r1[qid]; ex = rank(qs[qid]["question"] + " " + exp[qid], h, 400)
            fused = rrf(base, ex)
            for k in (8, 12):
                for name, r in (("r1", base), ("r1+exp", fused)):
                    for t in (g["question_type"], "all"): res[name, k, t].append(gs <= set(sessions(r, k)))
    for k in (8, 12):
        for name in ("r1", "r1+exp"):
            print(f"{split:14s} top{k:2d} {name:7s} " + " ".join(f"{t[:8]}={sum(res[name,k,t])/len(res[name,k,t]):.3f}" for t in ("knowledge-update","multi-session","temporal-reasoning","single-session-user","single-session-assistant","all")))
