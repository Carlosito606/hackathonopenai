"""How R1's evidence budget trades recall for message size, from a run's candidates.jsonl (no models needed).

    python rockets/poligon/pack_budget.py ../data/dev RUN_DEV ../data/dev_hard RUN_HARD --budgets 18000 22000 26000

Rebuilds R1's pack with build_evidence (root memsys.py, same code as evidence.py at 926005e) from the ranked chunks
in candidates.jsonl: exact when rows carry the chunk index ([session_id, turn, chunk_idx, score], R1's export
since fee061f), otherwise the k-th piece of its turn for the k-th time that turn appears. At the run's own budget (18000) the rebuilt session list is compared with the run's evidence.jsonl, so
the rebuild can be trusted. For each budget it prints, per type: all gold sessions in the pack, the share of
gold sessions that never reached the candidates (no budget can recover them), and the longest whole message
(the kit's build_message with prepare.py's question and guide), which ask.py refuses above 30000 characters.
"""
import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "reactor"))
import client as kit  # noqa: E402
from memsys import build_evidence, load_split, session_chunks  # noqa: E402
from prepare import GUIDE  # noqa: E402

SHORT = {"knowledge-update": "k-update", "multi-session": "multi", "single-session-assistant": "ss-asst",
         "single-session-user": "ss-user", "temporal-reasoning": "temporal", "all": "all"}


def rj(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def rebuild(h, ranked):
    """Candidate dicts in build_evidence's format from [session_id, turn, score] rows."""
    si = {s["session_id"]: i for i, s in enumerate(h["sessions"])}
    seen, cands = defaultdict(int), []
    for row in ranked:  # [session_id, turn, score], or [session_id, turn, chunk_idx, score] (exact)
        sid, turn, score = row[0], row[1], row[-1]
        s = h["sessions"][si[sid]]
        pieces = [p for t, _, p in session_chunks(s) if t == turn]
        k = row[2] if len(row) == 4 else seen[sid, turn]
        seen[sid, turn] += 1
        cands.append({"si": si[sid], "session_id": sid, "turn": turn, "role": s["turns"][turn]["role"],
                      "text": pieces[min(k, len(pieces) - 1)], "score": score})
    return cands


def message_len(q, evidence):
    passages = kit.load_evidence(json.dumps(evidence))
    return len(kit.build_message(q["question"].strip() + "\n" + GUIDE.format(extra=""), passages, "00000000",
                                 kit.parse_question_date(q["question_date"])))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pairs", nargs="+", help="split_dir run_dir [split_dir run_dir ...]")
    ap.add_argument("--budgets", type=int, nargs="+", default=[18000, 22000, 26000, 30000])
    args = ap.parse_args()
    for split, run in zip(args.pairs[::2], args.pairs[1::2]):
        hist, qs, gold = load_split(split)
        qs = {q["question_id"]: q for q in qs}
        cands = {r["question_id"]: r["ranked"] for r in rj(Path(run) / "candidates.jsonl")}
        packs = {r["question_id"]: r["sessions"] for r in rj(Path(run) / "evidence.jsonl")}
        print(f"\n== {split} ({len(cands)} questions)")
        same = 0
        rows = defaultdict(lambda: defaultdict(list))
        for qid, ranked in cands.items():
            q, g = qs[qid], gold[qid]
            h = hist[q["history_id"]]
            cs = rebuild(h, ranked)
            in_cands = {c["session_id"] for c in cs}
            for b in args.budgets:
                ev = build_evidence(h, cs, budget=b)
                ids = {e["id"] for e in ev}
                if b == 18000:
                    same += ids == set(packs[qid])
                if g["abstain"]:
                    continue
                gs = set(g["evidence"])
                for t in (g["question_type"], "all"):
                    rows[b, t]["all_in"].append(gs <= ids)
                    rows[b, t]["never"].append(len(gs - in_cands) / len(gs))
                    rows[b, t]["msg"].append(message_len(q, ev))
        print(f"rebuilt pack == run's evidence.jsonl at budget 18000: {same}/{len(cands)}")
        types = [t for t in SHORT if any((args.budgets[0], t) == k for k in rows)]
        print(f"{'budget':>7s} " + " ".join(f"{SHORT[t]:>9s}" for t in types) + "   never-in-cands(all)  max msg  mean msg")
        for b in args.budgets:
            cells = [sum(rows[b, t]["all_in"]) / len(rows[b, t]["all_in"]) for t in types]
            msg = rows[b, "all"]["msg"]
            print(f"{b:7d} " + " ".join(f"{c:9.3f}" for c in cells) +
                  f"   {sum(rows[b, 'all']['never']) / len(rows[b, 'all']['never']):19.3f}  {max(msg):7d}  "
                  f"{sum(msg) / len(msg):8.0f}")


if __name__ == "__main__":
    main()
