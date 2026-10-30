import json, sys
from collections import Counter, defaultdict
from datetime import datetime
D = sys.argv[1] if len(sys.argv) > 1 else "dev"
def rj(p): return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]
H = {h["history_id"]: h for h in rj(f"{D}/histories.jsonl")}
Q = rj(f"{D}/questions.jsonl")
G = {g["question_id"]: g for g in rj(f"{D}/gold.jsonl")}
FMT = "%Y/%m/%d (%a) %H:%M"
def dt(s): return datetime.strptime(s, FMT)
def stext(s): return "\n".join(t["content"] for t in s["turns"])
