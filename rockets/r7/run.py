"""Run R7 on a split -> runs/r7/<run_id>/ (core/CONTRACT.md section 2) plus decisions.jsonl (entity checks).

    python rockets/r7/run.py ../data/dev --exclude splits/dev_holdout.txt
    python rockets/r7/run.py ../data/dev --exclude splits/dev_holdout.txt --cands runs/r1/<run_id>/candidates.jsonl

No reader is called: predictions carry R7's abstentions and an empty answer otherwise, so answer accuracy is not
measured here; measure.py reports abstention recall and false abstention per type for every policy.
"""
import argparse
import gzip
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import rocket  # noqa: E402
from memsys import load_split, session_chunks  # noqa: E402


def cands_from_file(path, hist):
    """R1-style candidates rebuilt from a candidates.jsonl ([session_id, turn, score] rows, no text)."""
    opener = gzip.open if str(path).endswith(".gz") else open
    with opener(path, "rt", encoding="utf-8") as f:
        ranked = {r["question_id"]: r["ranked"] for r in map(json.loads, f)}

    def get(q):
        h = hist[q["history_id"]]
        where = {s["session_id"]: si for si, s in enumerate(h["sessions"])}
        out = []
        for sid, turn, score in ranked[q["question_id"]]:
            si = where[sid]
            for ti, role, text in session_chunks(h["sessions"][si]):
                if turn is None or ti == turn:
                    out.append({"si": si, "session_id": sid, "turn": ti, "role": role, "text": text, "kind": "turn",
                                "score": score, "notes": {}})
        return out
    return get


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("split")
    ap.add_argument("--exclude", help="file of question ids to skip (the holdout)")
    ap.add_argument("--only", help="file of question ids to run")
    ap.add_argument("--policy", default=rocket.POLICY, choices=rocket.POLICIES)
    ap.add_argument("--cands", help="candidates.jsonl of another run (e.g. R1) instead of R7's BM25 retrieve")
    ap.add_argument("--out", default=str(ROOT / "runs" / "r7"))
    args = ap.parse_args()

    hist, qs, _ = load_split(args.split)
    if args.exclude:
        skip = set(Path(args.exclude).read_text().split())
        qs = [q for q in qs if q["question_id"] not in skip]
    if args.only:
        keep = set(Path(args.only).read_text().split())
        qs = [q for q in qs if q["question_id"] in keep]
    retrieve = cands_from_file(args.cands, hist) if args.cands else (lambda q: rocket.retrieve(q, hist[q["history_id"]]))

    sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=ROOT).stdout.strip()
    run_id = f"{datetime.now():%Y%m%d-%H%M}-{sha}"
    out = Path(args.out) / run_id
    out.mkdir(parents=True, exist_ok=True)
    meta = {"rocket": "r7", "run_id": run_id, "git_sha": sha,
            "stages": {"retrieve": "r1" if args.cands else "r7-bm25", "enrich": None, "assemble": "r1",
                       "decide": f"r7-{args.policy}"},
            "split": Path(args.split).name + (" minus " + Path(args.exclude).name if args.exclude else ""),
            "reader": None, "flags": {"policy": args.policy, "cands": args.cands}}
    (out / "meta.json").write_text(json.dumps(meta, indent=1) + "\n", encoding="utf-8")

    files = {n: open(out / f"{n}.jsonl", "w", encoding="utf-8")
             for n in ("candidates", "evidence", "predictions", "decisions")}
    for i, q in enumerate(qs, 1):
        h = hist[q["history_id"]]
        cands = retrieve(q)
        pack = rocket.assemble(q, h, cands)
        ask = rocket.decide(q, h, cands, pack, policy=args.policy)
        sessions = [e["id"] for e in pack["evidence"]]
        files["candidates"].write(json.dumps({"question_id": q["question_id"], "ranked": [
            [c["session_id"], c["turn"], round(c["score"], 6)] for c in cands[:100]]}) + "\n")
        files["evidence"].write(json.dumps({"question_id": q["question_id"], "sessions": sessions,
                                            "chars": sum(len(e["text"]) for e in pack["evidence"])}) + "\n")
        files["predictions"].write(json.dumps({"question_id": q["question_id"], "abstain": ask["abstain"],
                                               "answer": "", "citations": []}) + "\n")
        files["decisions"].write(json.dumps({"question_id": q["question_id"], "question": q["question"],
                                             "abstain": ask["abstain"], "sessions": sessions,
                                             "checked": [{k: e[k] for k in ("text", "kind", "words", "found", "head_found",
                                                                          "in")}
                                                         for e in ask["checked"]]}) + "\n")
        if i % 50 == 0:
            print(f"{i}/{len(qs)}", flush=True)
    for f in files.values():
        f.close()
    print(out)


if __name__ == "__main__":
    main()
