# Run from ~/vibathon/mc on the Mac (needs the Reactor calibration results and plans)
"""Evidence F1 on the Reactor calibration (new prompt): final-line citations, + reply fallback, + cite_expand."""
import json
import subprocess
import sys

sys.path.insert(0, "reactor")
import client as kit  # noqa: E402

gold = {g["question_id"]: g for g in map(json.loads, open("../data/dev/gold.jsonl"))}
plan = {p["question_id"]: p for p in map(json.loads, open("../rakieta-dev/plan-cal40-new.jsonl"))}
res = [json.loads(l) for l in open("../rakieta-dev/results-cal40-new.jsonl")]


def f1(c, e):
    c, e = set(c), set(e)
    h = len(c & e)
    return 0 if not h else 2 * h / (len(c) + len(e))


subprocess.run([sys.executable, "reactor/predictions.py", "../rakieta-dev/results-cal40-new.jsonl", "--out",
                "/tmp/pred-new.jsonl", "--abstain-on", "agent,no-answer"], check=True, capture_output=True)
fb = []
for r in res:
    p = plan[r["question_id"]]
    cit = [c["id"] for c in r.get("citations", [])]
    if not r.get("abstained") and not cit:
        cited, _ = kit.citations(r.get("reply", ""), kit.load_evidence(json.dumps(p["evidence"])))
        cit = list(dict.fromkeys(c["id"] for c in cited))
    fb.append({"question_id": r["question_id"], "abstain": bool(r.get("abstained")), "answer": r.get("answer", ""),
               "citations": cit})
open("/tmp/pred-fb.jsonl", "w").writelines(json.dumps(x) + "\n" for x in fb)
subprocess.run([sys.executable, "../poligon2/rockets/poligon/cite_expand.py", "/tmp/pred-fb.jsonl",
                "../rakieta-dev/plan-cal40-new.jsonl", "../data/dev/histories.jsonl", "--out", "/tmp/pred-fbx.jsonl"],
               check=True, capture_output=True)
base = {p["question_id"]: p for p in map(json.loads, open("/tmp/pred-new.jsonl"))}
fbx = {p["question_id"]: p for p in map(json.loads, open("/tmp/pred-fbx.jsonl"))}
fbd = {p["question_id"]: p for p in fb}
rows = {"final line": base, "+ reply fallback": fbd, "+ fallback + cite_expand": fbx}
by_type = {}
for name, P in rows.items():
    for q, g in gold.items():
        if q not in P or g["abstain"]:
            continue
        by_type.setdefault((name, g["question_type"]), []).append(f1(P[q]["citations"], g["evidence"]))
        by_type.setdefault((name, "all"), []).append(f1(P[q]["citations"], g["evidence"]))
for (name, t), v in sorted(by_type.items(), key=lambda x: (x[0][1], list(rows).index(x[0][0]))):
    print(f"{t:26s} {name:26s} n={len(v):2d} F1={sum(v) / len(v):.3f}")
changed = sum(fbd[q]["answer"] != fbx[q]["answer"] or fbd[q]["abstain"] != fbx[q]["abstain"] for q in fbd)
print("answers/abstentions changed by cite_expand:", changed)
