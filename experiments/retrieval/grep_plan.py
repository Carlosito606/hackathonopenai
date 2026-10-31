"""Manual audit helper: user turns of one question's history matching a regex, and whether each turn's session is in
the plan's evidence (IN/OUT) and whether that exact turn text is in it (+turn).

    python experiments/retrieval/grep_plan.py ../data/test plan-test.jsonl "How many orchids" "orchid"
"""
import json
import re
import sys
from pathlib import Path

split, plan, qpat, pat = Path(sys.argv[1]), sys.argv[2], sys.argv[3], re.compile(sys.argv[4], re.I)
p = next(json.loads(x) for x in open(plan) if qpat.lower() in json.loads(x)["question"].lower())
h = next(json.loads(x) for x in open(split / "histories.jsonl") if p["history_id"] in x[:80])
ev = {e["id"]: e["text"] for e in p["evidence"]}
print(p["question"].split("\n")[0], f"| {len(ev)} sessions in evidence")
for s in h["sessions"]:
    for t in s["turns"]:
        m = pat.search(t["content"])
        if t["role"] == "user" and m:
            i = max(0, m.start() - 150)
            snip = t["content"][i:m.end() + 150].replace("\n", " ")
            inside = s["session_id"] in ev and t["content"][m.start():m.end() + 40] in ev[s["session_id"]]
            print(f"  {'IN ' if s['session_id'] in ev else 'OUT'}{'+turn' if inside else '     '} {s['date'][:10]} …{snip}")
