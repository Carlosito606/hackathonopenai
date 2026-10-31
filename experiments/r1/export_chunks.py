"""R1 candidates with the chunk index of each turn (no text), for rockets that rebuild R1's packs exactly.

    python experiments/r1/export_chunks.py ../data/dev OUT_DIR --cache ../cache/dev.pkl --type temporal-reasoning

Writes OUT_DIR/candidates.jsonl: {"question_id", "ranked": [[session_id, turn, chunk_idx, score], ...]} (top 100),
where chunk_idx indexes retrieval.split_text(turn content); and OUT_DIR/evidence.jsonl as rockets/poligon/r1_run.py.
Dev questions without the holdout, answerable or not, of the given type.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from dates import TEMPORAL  # noqa: E402
from evidence import build_evidence  # noqa: E402
from retrieval import Embedder, load_split, retrieve, split_text  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("split")
ap.add_argument("out", type=Path)
ap.add_argument("--cache", required=True)
ap.add_argument("--type", default="temporal-reasoning")
args = ap.parse_args()
hist, qs, gold = load_split(args.split)
hold = set((ROOT / "splits" / "dev_holdout.txt").read_text().split())
qs = [q for q in qs if q["question_id"] not in hold and gold[q["question_id"]]["question_type"] == args.type]
emb = Embedder(args.cache)
args.out.mkdir(parents=True, exist_ok=True)
with open(args.out / "candidates.jsonl", "w", encoding="utf-8") as fc, \
        open(args.out / "evidence.jsonl", "w", encoding="utf-8") as fe:
    for q in qs:
        h = hist[q["history_id"]]
        cands = retrieve(h, q["question"], emb, question_date=q["question_date"])
        ranked = []
        for c in cands[:100]:
            pieces = split_text(h["sessions"][c["si"]]["turns"][c["turn"]]["content"])
            assert c["text"] in pieces, (q["question_id"], c["session_id"], c["turn"])
            ranked.append([c["session_id"], c["turn"], pieces.index(c["text"]), round(c["score"], 4)])
        fc.write(json.dumps({"question_id": q["question_id"], "ranked": ranked}) + "\n")
        ev = build_evidence(h, cands, dates=bool(TEMPORAL.search(q["question"])))
        fe.write(json.dumps({"question_id": q["question_id"], "sessions": [e["id"] for e in ev],
                             "chars": sum(len(e["text"]) for e in ev)}) + "\n")
print(f"wrote {len(qs)} questions to {args.out}")
