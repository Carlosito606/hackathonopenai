import sys, re; sys.path.insert(0, sys.argv[2]); sys.argv = sys.argv[:2]
from load import *
def find(qtext):
    for q in Q:
        if q["question"].startswith(qtext): return q
def show(qtext, kw, width=220):
    q=find(qtext); g=G[q["question_id"]]; h=H[q["history_id"]]
    print(f"\n### Q [{q['question_date']}]: {q['question']}\n    gold: {g['answer']}")
    for s in h["sessions"]:
        tag="EVID" if s["session_id"] in g["evidence"] else "----"
        for t in s["turns"]:
            if t["role"]!="user": continue
            for m in re.finditer(kw, t["content"], re.I):
                a=max(0,m.start()-width//2); print(f"  {tag} {s['date']} ...{t['content'][a:a+width]}...".replace("\n"," "))
                break


show("I received a piece of jewelry last Saturday", r"jewel|necklace|bracelet|ring\b|earring")
show("How many different doctors did I visit", r"\bDr\.|doctor")
evset={e for g in G.values() for e in g["evidence"]}
btw=re.compile(r"\b(by the way|speaking of|actually|oh,? and|on a side note|i forgot to mention)\b",re.I)
corr=re.compile(r"\b(actually,? (i|it|my|we)|not \d+|i meant|correction|i was wrong|i misspoke|to correct)\b",re.I)
for name,cond in (("evidence",lambda s:s["session_id"] in evset),("non-evidence",lambda s:s["session_id"] not in evset)):
    ss=[s for h in H.values() for s in h["sessions"] if cond(s)]
    u=lambda s:" ".join(t["content"] for t in s["turns"] if t["role"]=="user")
    print(f"{name}: aside-markers {sum(bool(btw.search(u(s))) for s in ss)/len(ss):.2f}  self-correction {sum(bool(corr.search(u(s))) for s in ss)/len(ss):.2f}")
