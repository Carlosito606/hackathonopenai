"""Experiment: entity sensitivity of the SQuAD 2.0 signal. Replace the question's most specific entity with a made-up
word and score both questions on the same chunks. Evidence that is really about the entity should lose confidence
("How long was I in Zorbland for?"); a near-miss session answers both alike, so a small drop hints at a swap.

    python rockets/r7/swap.py ../data/dev out.jsonl --exclude splits/dev_holdout.txt
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import entities  # noqa: E402
import qa  # noqa: E402
import rocket  # noqa: E402
from memsys import load_split  # noqa: E402  (R1, read-only)

def session_df(h):
    """In how many sessions of the history each stemmed word occurs."""
    df = {}
    for s in h["sessions"]:
        for w in set(entities.words(" ".join(t["content"] for t in s["turns"]))):
            df[w] = df.get(w, 0) + 1
    return df


def target(question, df):
    """(surface text to replace, made-up word): the longest name or quoted title; else the question's content word
    that is rarest in this history (the most specific thing asked about)."""
    es = entities.extract(question)
    names = [e for e in es if e["kind"] in ("proper", "quoted")]
    if names:
        return max(names, key=lambda e: len(e["text"]))["text"], "Zorbland"
    words = {w for e in es for w in e["words"]}
    best = None
    for m in entities.WORD.finditer(question):
        w = entities.stem(m.group(0))
        if w in words and (best is None or df.get(w, 0) < best[0]):
            best = (df.get(w, 0), m.group(0))
    return (best[1], "zorble") if best else None


def swapped(question, tgt):
    text, nonce = tgt
    new, n = re.subn(r"(?<!\w)" + re.escape(text) + r"(?!\w)", nonce, question, count=1)
    return new if n else None


def chunks(q, h, cands):
    seen, texts = set(), []
    for c in cands:
        key = (c["session_id"], c["turn"], c["text"][:50])
        if key in seen:
            continue
        seen.add(key)
        texts.append(f"{c['role']}: {c['text'][:qa.CHUNK + 200]}")
        if len(texts) == qa.K:
            break
    return texts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("split")
    ap.add_argument("out")
    ap.add_argument("--exclude")
    args = ap.parse_args()
    hist, qs, _ = load_split(args.split)
    if args.exclude:
        skip = set(Path(args.exclude).read_text().split())
        qs = [q for q in qs if q["question_id"] not in skip]
    with open(args.out, "w", encoding="utf-8") as f:
        dfs = {}
        for i, q in enumerate(qs, 1):
            h = hist[q["history_id"]]
            if q["history_id"] not in dfs:
                dfs[q["history_id"]] = session_df(h)
            tgt = target(q["question"], dfs[q["history_id"]])
            row = {"question_id": q["question_id"], "question": q["question"], "entity": tgt and tgt[0],
                   "swapped": None, "qa": None, "qa_swapped": None}
            new = swapped(q["question"], tgt) if tgt else None
            if new:
                texts = chunks(q, h, rocket.retrieve(q, h))
                if texts:
                    a = max(s for s, _ in qa.scores(q["question"], texts))
                    b = max(s for s, _ in qa.scores(new, texts))
                    row.update(swapped=new, qa=round(a, 4), qa_swapped=round(b, 4))
            f.write(json.dumps(row) + "\n")
            if i % 50 == 0:
                print(f"{i}/{len(qs)}", flush=True)


if __name__ == "__main__":
    main()
