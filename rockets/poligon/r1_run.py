"""R1 HYBRID retrieval (root memsys.py, unchanged) on every question of a split -> candidates.jsonl, evidence.jsonl.

    python rockets/poligon/r1_run.py ../data/dev OUT --cache ../cache/r1.pkl --device cpu --skip-holdout
    python rockets/poligon/r1_run.py ../data/dev_hard OUT --cache ../cache/r1.pkl --device cpu [--rerank]

Same calls as prepare.plan_question (retrieve, then build_evidence with dates for temporal questions), so the pack
is what R1 would send. Device is a flag because memsys defaults to mps. One embedding cache serves dev and
dev-hard: the cache is keyed by session id, and dev-hard keeps original ids and gives injected sessions new ones.
Resumable: questions already in OUT/candidates.jsonl are skipped.
"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import memsys  # noqa: E402
from memsys import TEMPORAL, Embedder, build_evidence, load_split, retrieve  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("split")
    ap.add_argument("out", type=Path)
    ap.add_argument("--cache", required=True)
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--rerank", action="store_true", help="R1's cross-encoder rerank (slow on CPU)")
    ap.add_argument("--skip-holdout", action="store_true")
    ap.add_argument("--batch", type=int, default=25, help="histories embedded between cache saves")
    args = ap.parse_args()
    hist, qs, _ = load_split(args.split)
    if args.skip_holdout:
        hold = set((Path(__file__).resolve().parents[2] / "splits" / "dev_holdout.txt").read_text().split())
        qs = [q for q in qs if q["question_id"] not in hold]
    args.out.mkdir(parents=True, exist_ok=True)
    cpath, epath = args.out / "candidates.jsonl", args.out / "evidence.jsonl"
    done = {json.loads(line)["question_id"] for line in open(cpath, encoding="utf-8")} if cpath.exists() else set()
    if not done:  # a fresh run: drop a partial evidence file from an interrupted one
        epath.unlink(missing_ok=True)
    qs = [q for q in qs if q["question_id"] not in done]
    if args.rerank:
        memsys.reranker(args.device)  # initialise the global cross-encoder on our device, not mps
    emb = Embedder(args.cache, device=args.device)
    t = time.time()
    hids = list(dict.fromkeys(q["history_id"] for q in qs))
    for i in range(0, len(hids), args.batch):  # Embedder.ensure saves the cache, so a long CPU run can resume
        emb.ensure([s for h in hids[i:i + args.batch] for s in hist[h]["sessions"]])
        print(f"embedded histories {min(i + args.batch, len(hids))}/{len(hids)} {time.time() - t:.0f}s", flush=True)
    with open(cpath, "a", encoding="utf-8", newline="\n") as fc, open(epath, "a", encoding="utf-8", newline="\n") as fe:
        for i, q in enumerate(qs, 1):
            h = hist[q["history_id"]]
            cands = retrieve(h, q["question"], emb, rerank=args.rerank)
            ev = build_evidence(h, cands, dates=bool(TEMPORAL.search(q["question"])))
            fc.write(json.dumps({"question_id": q["question_id"], "ranked": [
                [c["session_id"], c["turn"], round(c["score"], 4)] for c in cands[:100]]}) + "\n")
            fe.write(json.dumps({"question_id": q["question_id"], "sessions": [e["id"] for e in ev],
                                 "chars": sum(len(e["text"]) for e in ev)}) + "\n")
            if i % 50 == 0:
                fc.flush()
                fe.flush()
                print(f"{i}/{len(qs)} {time.time() - t:.0f}s", flush=True)
    print(f"wrote {cpath} and {epath}")


if __name__ == "__main__":
    main()
