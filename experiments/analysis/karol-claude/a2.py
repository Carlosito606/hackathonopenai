import sys; sys.path.insert(0, sys.argv[2]); sys.argv = sys.argv[:2]
from load import *
import re, math, statistics as st
tok = lambda s: re.findall(r"[a-z0-9']+", s.lower())
STOP=set("the a an of to and in on for is it i my me you your was what how many did do with at that this from by be are have has as or which when who where".split())
def bm25_rank(q, h, field="all"):
    docs=[]
    for s in h["sessions"]:
        if field=="user": txt="\n".join(t["content"] for t in s["turns"] if t["role"]=="user")
        else: txt=stext(s)
        docs.append(tok(txt))
    N=len(docs); avg=sum(map(len,docs))/N
    df=Counter(w for d in docs for w in set(d))
    qt=[w for w in tok(q) if w not in STOP]
    sc=[]
    for d,s in zip(docs,h["sessions"]):
        tf=Counter(d); v=0
        for w in qt:
            if w in tf:
                idf=math.log(1+(N-df[w]+.5)/(df[w]+.5)); f=tf[w]
                v+=idf*f*2.2/(f+1.2*(.25+.75*len(d)/avg))
        sc.append((v,s["session_id"]))
    sc.sort(reverse=True); return sc
res=defaultdict(list); examples=[]
for q in Q:
    g=G[q["question_id"]]
    if g["abstain"]: continue
    h=H[q["history_id"]]
    for field in ("all","user"):
        r=[sid for _,sid in bm25_rank(q["question"],h,field)]
        ranks=[r.index(e)+1 for e in g["evidence"]]
        res[(g["question_type"],field)].append((min(ranks),max(ranks)))
        if field=="user" and min(ranks)>5 and len(examples)<8: examples.append((g["question_type"],q["question"],min(ranks)))
for (t,f),v in sorted(res.items()):
    best=[a for a,b in v]; worst=[b for a,b in v]
    print(f"{t:26s} {f:4s} best@1={sum(x==1 for x in best)/len(v):.2f} best@5={sum(x<=5 for x in best)/len(v):.2f} all@10={sum(x<=10 for x in worst)/len(v):.2f} median_worst={st.median(worst)}")
print("\nhard for BM25 (user field):")
for e in examples: print(" ",e)
