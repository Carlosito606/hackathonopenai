"""Two plans of the same dev questions: which evidence packs changed, per type, and whether the gold sessions stay.

    python experiments/r1/diff_plans.py ../data/dev/gold.jsonl OLD_PLAN.jsonl NEW_PLAN.jsonl
"""
import json
import sys
from collections import Counter

gold = {g["question_id"]: g for g in map(json.loads, open(sys.argv[1], encoding="utf-8"))}
old, new = ({p["question_id"]: p for p in map(json.loads, open(f, encoding="utf-8"))} for f in sys.argv[2:4])
changed, rows = Counter(), []
for q, p in new.items():
    g, o = gold[q], old[q]
    so, sn = [e["id"] for e in o["evidence"]], [e["id"] for e in p["evidence"]]
    ev = set(g["evidence"])
    kind = "abstain" if g["abstain"] else g["question_type"]
    same = so == sn and [e["text"] for e in o["evidence"]] == [e["text"] for e in p["evidence"]]
    changed[kind, "same" if same else "changed"] += 1
    if not same:
        rows.append(f"{kind:26s} sessions {len(so):2d} -> {len(sn):2d}  gold in pack {len(ev & set(so))}/{len(ev)} -> "
                    f"{len(ev & set(sn))}/{len(ev)}  chars {sum(len(e['text']) for e in o['evidence'])} -> "
                    f"{sum(len(e['text']) for e in p['evidence'])}")
for (kind, s), n in sorted(changed.items()):
    print(f"{kind:26s} {s:8s} {n}")
print("\n".join(sorted(rows)))
