import sys, re, random; sys.path.insert(0, sys.argv[2]); sys.argv = sys.argv[:2]
from load import *
random.seed(3)
# uncued pairs: same history & gold answer
byh=defaultdict(list)
for q in Q: byh[q["history_id"]].append(q)
print("=== UNCUED rephrasings (original -> uncued)")
k=0
for hid,qs in byh.items():
    if len(qs)==2 and k<8:
        print(f"- {qs[0]['question']}\n  -> {qs[1]['question']}"); k+=1
print("\n=== sessions whose first turn is assistant: samples")
fs=[s for h in H.values() for s in h["sessions"] if s["turns"] and s["turns"][0]["role"]=="assistant"]
for s in random.sample(fs,3): print("-", s["turns"][0]["content"][:200].replace("\n"," "))
print("\n=== filler style: fraction of sessions whose user turns contain first-person life facts")
evset={e for g in G.values() for e in g["evidence"]}
pers=re.compile(r"\b(my (wife|husband|sister|brother|mom|dad|friend|kid|son|daughter|boss|cat|dog)|I (just|recently) (bought|got|started|moved|finished|visited))\b",re.I)
for name,cond in (("evidence",lambda s:s["session_id"] in evset),("non-evidence",lambda s:s["session_id"] not in evset)):
    ss=[s for h in H.values() for s in h["sessions"] if cond(s)]
    hit=sum(1 for s in ss if pers.search(" ".join(t["content"] for t in s["turns"] if t["role"]=="user")))
    print(f"  {name}: {hit}/{len(ss)} = {hit/len(ss):.2f}")
print("\n=== relative time words inside evidence USER turns")
rel=re.compile(r"\b(yesterday|today|last (week|month|weekend|year|monday|tuesday|wednesday|thursday|friday|saturday|sunday)|(\w+) (days|weeks|months) ago|this (morning|week|weekend)|next (week|month))\b",re.I)
c=Counter(); tot=0
for q in Q:
    g=G[q["question_id"]]; m={s["session_id"]:s for s in H[q["history_id"]]["sessions"]}
    for e in g["evidence"]:
        tot+=1
        txt=" ".join(t["content"] for t in m[e]["turns"] if t["role"]=="user")
        f=[x.group(0).lower() for x in rel.finditer(txt)]
        if f: c["has_rel"]+=1
        for x in f: c[x]+=1
print(" evidence sessions with relative-time expressions:", c["has_rel"], "/", tot); del c["has_rel"]; print(" ", c.most_common(12))
