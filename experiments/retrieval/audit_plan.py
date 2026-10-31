"""Recall audit of a plan without gold: for each question, the user turns that mention its rarest content words,
and whether their sessions made it into the plan's evidence.

    python experiments/retrieval/audit_plan.py ../data/test ../mc/plan-test.jsonl [n] > audit.txt
"""
import json
import random
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from retrieval import read_jsonl, tokens  # noqa: E402

split, plan = Path(sys.argv[1]), read_jsonl(sys.argv[2])
n = int(sys.argv[3]) if len(sys.argv) > 3 else 30
need = {p["history_id"] for p in plan}
hist = {}
with open(split / "histories.jsonl", encoding="utf-8") as f:
    for line in f:
        h = json.loads(line)
        if h["history_id"] in need:
            hist[h["history_id"]] = h
random.seed(0)
plan = random.sample(plan, min(n, len(plan)))
missed_total = hit_total = 0
for p in plan:
    h = hist[p["history_id"]]
    q = p["question"].split("\n")[0]
    sess_toks = [set(tokens(" ".join(t["content"] for t in s["turns"] if t["role"] == "user"))) for s in h["sessions"]]
    df = Counter(w for st in sess_toks for w in st)
    keys = sorted({w for w in tokens(q) if 0 < df[w] <= len(h["sessions"]) // 4}, key=lambda w: df[w])[:3]
    sent = {e["id"] for e in p["evidence"]}
    print(f"\n## {q}\nkeys={keys} df={[df[w] for w in keys]} sent={len(sent)}")
    for s in h["sessions"]:
        for t in s["turns"]:
            if t["role"] != "user":
                continue
            tt = set(tokens(t["content"]))
            if keys and keys[0] in tt and sum(w in tt for w in keys) >= min(2, len(keys)):
                ok = s["session_id"] in sent
                hit_total += ok
                missed_total += not ok
                low = t["content"].lower()
                i = max(0, min(low.find(k) for k in keys if k in low) - 120)
                print(f"  {'IN ' if ok else 'OUT'} {s['session_id']} {s['date'][:10]} …{t['content'][i:i + 260]!r}")
print(f"\nkey-word user turns in evidence: {hit_total}, missing: {missed_total}")
