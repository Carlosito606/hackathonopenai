"""Smoke-test artifacts for permlab: 3 BM25 variants (all turns / user only / assistant only) on dev."""
import sys, re, math, json, os; sys.path.insert(0, sys.argv[2]); out = sys.argv[3]; sys.argv = sys.argv[:2]
from load import *
tok = lambda s: re.findall(r"[a-z0-9']+", s.lower())
STOP = set("the a an of to and in on for is it i my me you your was what how many did do does with at that this from by be are have has as or which when who where".split())
def rank(q, h, roles):
    rows = [(s["session_id"], i, t["content"]) for s in h["sessions"] for i, t in enumerate(s["turns"]) if t["role"] in roles]
    docs = [tok(r[2]) for r in rows]; N = len(docs); avg = sum(map(len, docs)) / N
    df = Counter(w for d in docs for w in set(d)); qt = [w for w in tok(q) if w not in STOP]
    sc = []
    for r, d in zip(rows, docs):
        tf = Counter(d)
        v = sum(math.log(1 + (N - df[w] + .5) / (df[w] + .5)) * tf[w] * 2.2 / (tf[w] + 1.2 * (.25 + .75 * len(d) / avg)) for w in qt if w in tf)
        sc.append([r[0], r[1], round(v, 3)])
    sc.sort(key=lambda x: -x[2]); return sc[:100]
for name, roles in (("all", {"user", "assistant"}), ("user", {"user"}), ("asst", {"assistant"})):
    os.makedirs(f"{out}/{name}", exist_ok=True)
    with open(f"{out}/{name}/candidates.jsonl", "w", encoding="utf-8") as f, open(f"{out}/{name}/predictions.jsonl", "w", encoding="utf-8") as p:
        for q in Q:
            r = rank(q["question"], H[q["history_id"]], roles)
            f.write(json.dumps({"question_id": q["question_id"], "ranked": r}) + "\n")
            m = {s["session_id"]: s for s in H[q["history_id"]]["sessions"]}
            txt = m[r[0][0]]["turns"][r[0][1]]["content"] if r else ""
            p.write(json.dumps({"question_id": q["question_id"], "abstain": False, "answer": txt[:2000], "citations": [r[0][0]] if r else []}) + "\n")
print("ok")
