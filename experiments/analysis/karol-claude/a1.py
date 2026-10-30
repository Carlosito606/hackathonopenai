import sys; sys.path.insert(0, sys.argv[2]); sys.argv = sys.argv[:2]
from load import *
import statistics as st
print("questions", len(Q), "histories", len(H))
tc = Counter(G[q["question_id"]]["question_type"] for q in Q)
ab = Counter(G[q["question_id"]]["question_type"] for q in Q if G[q["question_id"]]["abstain"])
for t, c in tc.most_common(): print(f"  {t:28s} {c:4d}  abstain={ab[t]}")
ns = [len(h["sessions"]) for h in H.values()]
print("sessions/history", min(ns), st.mean(ns), max(ns))
lens = [len(stext(s)) for h in H.values() for s in h["sessions"]]
print("session chars median/mean/max", st.median(lens), int(st.mean(lens)), max(lens))
turns = [len(s["turns"]) for h in H.values() for s in h["sessions"]]
print("turns/session median/mean/max", st.median(turns), int(st.mean(turns)), max(turns))
ne = Counter(len(G[q["question_id"]]["evidence"]) for q in Q)
print("evidence count dist", sorted(ne.items()))
for t in tc:
    e = [len(G[q["question_id"]]["evidence"]) for q in Q if G[q["question_id"]]["question_type"]==t and not G[q["question_id"]]["abstain"]]
    print(f"  {t:28s} ev mean {st.mean(e):.2f} max {max(e)}")
# session reuse across histories
occ = defaultdict(set); dates = defaultdict(set)
for h in H.values():
    for s in h["sessions"]:
        occ[s["session_id"]].add(h["history_id"]); dates[s["session_id"]].add(s["date"])
c = Counter(len(v) for v in occ.values())
print("unique sessions", len(occ), "reuse dist (n histories -> n sessions) top", sorted(c.items())[:5], "... max", max(c))
print("sessions with >1 distinct date", sum(len(v)>1 for v in dates.values()))
# evidence sessions of q appearing in OTHER histories (as distractors)
evset = {e for g in G.values() for e in g["evidence"]}
ev_elsewhere = 0; tot=0
for q in Q:
    g = G[q["question_id"]]
    for e in g["evidence"]:
        tot+=1
        if len(occ[e])>1: ev_elsewhere+=1
print("evidence sessions also appearing in other histories:", ev_elsewhere, "/", tot)
# how many sessions per history are someone else's evidence (non-evidence for this q)
oth=[]
for q in Q:
    g=G[q["question_id"]]; h=H[q["history_id"]]
    oth.append(sum(1 for s in h["sessions"] if s["session_id"] in evset and s["session_id"] not in g["evidence"]))
print("per history: sessions that are evidence for OTHER questions (mean/max)", st.mean(oth), max(oth))
# role/empty turns, structure
roles = Counter(t["role"] for h in H.values() for s in h["sessions"] for t in s["turns"])
print("roles", roles)
starts = Counter(s["turns"][0]["role"] for h in H.values() for s in h["sessions"] if s["turns"])
print("first turn role", starts)
empty = sum(1 for h in H.values() for s in h["sessions"] for t in s["turns"] if not t["content"].strip())
print("empty turns", empty)
