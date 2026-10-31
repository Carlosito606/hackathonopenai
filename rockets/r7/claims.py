"""Experiment, step 1 of the NLI gate: a local LLM turns each question into the first-person claims it takes for
granted ("What is the name of my hamster?" -> "I have a hamster."). Step 2 (nli.py) checks each claim against the
user's own sentences in the retrieved chunks.

    python rockets/r7/claims.py ../data/dev_hard claims.jsonl --local http://127.0.0.1:8899 [--only ids.txt]

Resumable: questions already in the output file are skipped.
"""
import argparse
import json
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from memsys import load_split  # noqa: E402  (R1, read-only)

PROMPT = """I am asking a question about my own past. List the facts about me that the question takes for granted, \
as short first-person statements, one per line, at most 3. Keep the exact names, items, places, people and events \
from the question; do not generalise them and do not add anything. A question about two things gets one statement \
for each. A question about what the assistant said gets a statement like "You told me about ...".

Example question: How many days did I spend traveling in Lisbon and in Oslo?
I traveled in Lisbon.
I traveled in Oslo.

Example question: What is the name of my parrot?
I have a parrot.

Question: {question}"""


def ask(url, prompt):
    body = json.dumps({"messages": [{"role": "user", "content": prompt}], "max_tokens": 80,
                       "temperature": 0}).encode()
    req = urllib.request.Request(url + "/v1/chat/completions", body, {"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=300).read())["choices"][0]["message"]["content"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("split")
    ap.add_argument("out")
    ap.add_argument("--local", required=True)
    ap.add_argument("--only")
    ap.add_argument("--exclude")
    args = ap.parse_args()
    _, qs, _ = load_split(args.split)
    if args.only:
        keep = set(Path(args.only).read_text().split())
        qs = [q for q in qs if q["question_id"] in keep]
    if args.exclude:
        skip = set(Path(args.exclude).read_text().split())
        qs = [q for q in qs if q["question_id"] not in skip]
    done = set()
    if Path(args.out).exists():
        done = {json.loads(line)["question_id"] for line in open(args.out, encoding="utf-8") if line.strip()}
    with open(args.out, "a", encoding="utf-8") as f:
        for i, q in enumerate(qs, 1):
            if q["question_id"] in done:
                continue
            t = time.time()
            raw = ask(args.local, PROMPT.format(question=q["question"].strip()))
            claims = [c.strip(" -*\t") for c in raw.splitlines() if c.strip(" -*\t")][:3]
            f.write(json.dumps({"question_id": q["question_id"], "question": q["question"], "claims": claims,
                                "latency_s": round(time.time() - t, 1)}) + "\n")
            f.flush()
            if i % 50 == 0:
                print(f"{i}/{len(qs)}", flush=True)


if __name__ == "__main__":
    main()
