"""Why a rocket loses gold on dev-hard: near-miss crowding vs retrieval, from its dev and dev-hard candidates.

    python rockets/poligon/crowding.py ../data/dev DEV_RUN ../data/dev_hard HARD_RUN [--budget 18000]

For every answerable inject question whose gold is complete in the dev pack, rebuilds both packs from the runs'
candidates.jsonl (pack_budget.rebuild: exact with chunk-indexed rows) and classifies a dev-hard loss as
  crowded     the gold returns when the injected (and padded) sessions are dropped from the same ranking
  retrieval   a gold session is not among the dev-hard candidates at all
  other       neither (the ranking itself changed around the gold)
Also prints how many injected / padded sessions the dev-hard packs hold.
"""
import argparse
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pack_budget import SHORT, rebuild, rj  # noqa: E402  (also puts the repo root on sys.path)
from memsys import TEMPORAL, build_evidence, load_split  # noqa: E402


def pack_ids(h, cands, budget, question):
    return {e["id"] for e in build_evidence(h, cands, budget=budget, dates=bool(TEMPORAL.search(question)))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dev")
    ap.add_argument("dev_run", type=Path)
    ap.add_argument("hard")
    ap.add_argument("hard_run", type=Path)
    ap.add_argument("--budget", type=int, default=18000)
    args = ap.parse_args()
    dhist, dqs, dgold = load_split(args.dev)
    dqs = {q["question_id"]: q for q in dqs}
    hhist, hqs, hgold = load_split(args.hard)
    hqs = {q["question_id"]: q for q in hqs}
    man = {m["question_id"]: m for m in rj(Path(args.hard) / "manifest.jsonl")}
    dc = {r["question_id"]: r["ranked"] for r in rj(args.dev_run / "candidates.jsonl")}
    hc = {r["question_id"]: r["ranked"] for r in rj(args.hard_run / "candidates.jsonl")}
    out, noise = defaultdict(Counter), Counter()
    for qid, m in sorted(man.items()):
        g = hgold[qid]
        if m["variant"] != "inject" or g["abstain"] or qid not in hc or m["source_qid"] not in dc:
            continue
        t, gs = g["question_type"], set(g["evidence"])
        dq, hq = dqs[m["source_qid"]], hqs[qid]
        dh, hh = dhist[dq["history_id"]], hhist[hq["history_id"]]
        noisy = {i["session_id"] for i in m["injected"]} | set(m.get("padded", []))
        cs = rebuild(hh, hc[qid])
        hard_pack = pack_ids(hh, cs, args.budget, hq["question"])
        noise["injected in pack"] += len(hard_pack & {i["session_id"] for i in m["injected"]})
        noise["padded in pack"] += len(hard_pack & set(m.get("padded", [])))
        noise["packs"] += 1
        if not gs <= pack_ids(dh, rebuild(dh, dc[m["source_qid"]]), args.budget, dq["question"]):
            k = "missed on dev too"
        elif gs <= hard_pack:
            k = "ok"
        elif not gs <= {c["session_id"] for c in cs}:
            k = "retrieval"
        elif gs <= pack_ids(hh, [c for c in cs if c["session_id"] not in noisy], args.budget, hq["question"]):
            k = "crowded"
        else:
            k = "other"
        for key in (t, "all"):
            out[key][k] += 1
    kinds = ("ok", "crowded", "retrieval", "other", "missed on dev too")
    print(f"{'type':9s} " + " ".join(f"{k:>17s}" for k in kinds))
    for t in sorted(out, key=lambda t: (t == "all", t)):
        print(f"{SHORT.get(t, t):9s} " + " ".join(f"{out[t][k]:17d}" for k in kinds))
    n = max(1, noise["packs"])
    print(f"per pack: {noise['injected in pack'] / n:.2f} injected, {noise['padded in pack'] / n:.2f} padded sessions")


if __name__ == "__main__":
    main()
