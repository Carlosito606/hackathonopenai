"""R1's retrieval (root memsys.py, unchanged) for a list of questions, cached with text so R3 can build on it
and R1 can be scored as the baseline from the same run.

    python rockets/r3/r1_cands.py ../data/dev rockets/r3/m1_questions.txt cache/r3/r1_cands.jsonl --device cpu
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import memsys  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("split")
    ap.add_argument("ids")
    ap.add_argument("out")
    ap.add_argument("--emb-cache", default="cache/dev.pkl")
    ap.add_argument("--device", default="mps")
    args = ap.parse_args()
    hist, qs, _ = memsys.load_split(args.split)
    ids = set(Path(args.ids).read_text().split())
    qs = [q for q in qs if q["question_id"] in ids]
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    done = {json.loads(line)["question_id"] for line in out.open()} if out.exists() else set()
    from sentence_transformers import CrossEncoder
    memsys._reranker = CrossEncoder(memsys.RERANK_MODEL, device=args.device, max_length=512)
    emb = memsys.Embedder(args.emb_cache, device=args.device)
    with out.open("a", encoding="utf-8") as f:
        for i, q in enumerate(qs, 1):
            if q["question_id"] in done:
                continue
            cands = memsys.retrieve(hist[q["history_id"]], q["question"], emb)
            f.write(json.dumps({"question_id": q["question_id"], "cands": cands}) + "\n")
            f.flush()
            print(f"{i}/{len(qs)}", flush=True)


if __name__ == "__main__":
    main()
