import sys, re, random; sys.path.insert(0, sys.argv[2]); sys.argv = sys.argv[:2]
from load import *
import statistics as st
random.seed(1)
sid2 = lambda h: {s["session_id"]: s for s in h["sessions"]}
print("=== KNOWLEDGE-UPDATE: evidence dates & gap")
gaps=[]; same_day=0; n=0
ku=[q for q in Q if G[q["question_id"]]["question_type"]=="knowledge-update" and not G[q["question_id"]]["abstain"]]
for q in ku:
    g=G[q["question_id"]]; m=sid2(H[q["history_id"]])
    ds=sorted(dt(m[e]["date"]) for e in g["evidence"])
    gaps.append((ds[-1]-ds[0]).days); same_day+= (ds[-1]-ds[0]).days==0; n+=1
print(f"n={n} gap days median={st.median(gaps)} min={min(gaps)} max={max(gaps)} same-day={same_day}")
for q in random.sample(ku,4):
    g=G[q["question_id"]]; print(f"- Q: {q['question']}  A: {g['answer']}")
print("\n=== TEMPORAL: relative-time phrasing in questions")
tr=[q for q in Q if G[q["question_id"]]["question_type"]=="temporal-reasoning"]
pat=re.compile(r"\b(ago|last (week|month|saturday|sunday|monday|tuesday|wednesday|thursday|friday|year)|past (week|month|two weeks|few)|first|earliest|latest|order|how many (days|weeks|months)|before|after|when)\b",re.I)
c=Counter()
for q in tr:
    for m_ in pat.finditer(q["question"]): c[m_.group(0).lower()]+=1
print(c.most_common(20))
for q in random.sample(tr,6):
    g=G[q["question_id"]]; print(f"- [{q['question_date']}] {q['question']}  A: {g['answer'][:100]}")
print("\n=== question date vs last session / evidence")
d_last=[]; d_ev=[]
for q in Q:
    g=G[q["question_id"]]; h=H[q["history_id"]]; m=sid2(h)
    qd=dt(q["question_date"]); d_last.append((qd-dt(h["sessions"][-1]["date"])).total_seconds()/86400)
    if g["evidence"]: d_ev.append((qd-max(dt(m[e]["date"]) for e in g["evidence"])).days)
print("days q - last session: median", st.median(d_last), "min", min(d_last))
print("days q - latest evidence: median", st.median(d_ev), "max", max(d_ev), "zero", sum(x==0 for x in d_ev))
print("\n=== Date clustering: sessions sharing identical timestamp within history")
dup=0
for h in H.values():
    c2=Counter(s["date"] for s in h["sessions"]); dup+=sum(v-1 for v in c2.values() if v>1)
print("sessions sharing timestamp with another:", dup)
spans=[(dt(h["sessions"][-1]["date"])-dt(h["sessions"][0]["date"])).days for h in H.values()]
print("history span days median/max", st.median(spans), max(spans))
