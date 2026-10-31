"""Experiment: a local LLM as a narrow verifier instead of a reader. For each question it sees the top candidate
chunks and answers one word, YES or NO: do the excerpts state the specific thing asked about, about the user?
P(YES) from the token probabilities is the answerability score (AUC and thresholds via measure-like counting).

    python rockets/r7/llm_check.py ../data/dev_hard out.jsonl --local http://127.0.0.1:8899 [--only ids.txt]
"""
import argparse
import json
import math
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rocket  # noqa: E402
from memsys import load_split  # noqa: E402  (R1, read-only)

K, CHUNK = 8, 1200
PROMPT = """Below are excerpts from my past chats with an assistant ("user" is me). Some excerpts may be about other \
people, other pets, other places or other events than the ones in my question.

{excerpts}

My question: {question}

Do the excerpts state the specific thing my question asks about, for me, with the same names, items, places and \
events as in the question (not a similar one)? Answer with one word: YES or NO."""


def excerpts(cands):
    seen, out = set(), []
    for c in cands:
        key = (c["session_id"], c["turn"], c["text"][:50])
        if key in seen:
            continue
        seen.add(key)
        out.append(f"[{len(out) + 1}] {c['role']}: {c['text'][:CHUNK]}")
        if len(out) == K:
            break
    return "\n\n".join(out)


def p_yes(url, prompt):
    body = json.dumps({"messages": [{"role": "user", "content": prompt}], "max_tokens": 1, "temperature": 0,
                       "logprobs": True, "top_logprobs": 10}).encode()
    req = urllib.request.Request(url + "/v1/chat/completions", body, {"Content-Type": "application/json"})
    r = json.loads(urllib.request.urlopen(req, timeout=600).read())["choices"][0]
    top = r["logprobs"]["content"][0]["top_logprobs"]
    yes = sum(math.exp(t["logprob"]) for t in top if t["token"].strip().upper().startswith("YES"))
    no = sum(math.exp(t["logprob"]) for t in top if t["token"].strip().upper().startswith("NO"))
    return yes / (yes + no) if yes + no else 0.5, r["message"]["content"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("split")
    ap.add_argument("out")
    ap.add_argument("--local", required=True)
    ap.add_argument("--only")
    args = ap.parse_args()
    hist, qs, _ = load_split(args.split)
    if args.only:
        keep = set(Path(args.only).read_text().split())
        qs = [q for q in qs if q["question_id"] in keep]
    done = set()
    if Path(args.out).exists():
        done = {json.loads(line)["question_id"] for line in open(args.out, encoding="utf-8") if line.strip()}
    with open(args.out, "a", encoding="utf-8") as f:
        for i, q in enumerate(qs, 1):
            if q["question_id"] in done:
                continue
            t = time.time()
            cands = rocket.retrieve(q, hist[q["history_id"]])
            p, raw = p_yes(args.local, PROMPT.format(excerpts=excerpts(cands), question=q["question"].strip()))
            f.write(json.dumps({"question_id": q["question_id"], "p_yes": round(p, 4), "raw": raw,
                                "latency_s": round(time.time() - t, 1)}) + "\n")
            f.flush()
            if i % 20 == 0:
                print(f"{i}/{len(qs)}", flush=True)


if __name__ == "__main__":
    main()
