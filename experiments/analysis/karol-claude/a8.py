import sys, re; sys.path.insert(0, sys.argv[2]); sys.argv = sys.argv[:2]
sys.stdout.reconfigure(encoding="utf-8")
from load import *
for pref,kw in (("I received a piece of jewelry",r"aunt"),("How many years older am I",r"graduat|\b\d\d\b years|I'm \d\d|turned \d\d|age")):
    q=next(q for q in Q if q["question"].startswith(pref)); g=G[q["question_id"]]
    m={s["session_id"]:s for s in H[q["history_id"]]["sessions"]}
    for e in g["evidence"]:
        for t in m[e]["turns"]:
            if t["role"]=="user":
                x=re.search(kw,t["content"],re.I)
                if x: a=max(0,x.start()-150); print(m[e]["date"], "...", t["content"][a:a+300].replace("\n"," ")); break
    print()
