import json, sys, statistics as st
sys.stdout.reconfigure(encoding="utf-8")
R = json.load(open(sys.argv[1], encoding="utf-8"))
def auc(pos, neg):
    return sum((p > n) + .5 * (p == n) for p in pos for n in neg) / (len(pos) * len(neg))
def z(key):
    v = [r[key] for r in R]; m, s = st.mean(v), st.pstdev(v)
    return {r["qid"]: (r[key] - m) / s for r in R}
zq, zc = z("qa"), z("cov")
for r in R: r["combo"] = zq[r["qid"]] + zc[r["qid"]]
A = [r for r in R if not r["abstain"]]; U = [r for r in R if r["abstain"]]
print(f"answerable={len(A)} unanswerable={len(U)}")
print("method   AUC   | caught abstain @ keep 95% / 90% / 80% of answerable")
for k in ("cov", "qa", "combo"):
    a = sorted(r[k] for r in A)
    out = []
    for keep in (.95, .90, .80):
        thr = a[int(len(a) * (1 - keep))]
        out.append(f"{sum(r[k] < thr for r in U)}/{len(U)}")
    print(f"{k:6s} {auc([r[k] for r in A], [r[k] for r in U]):.3f} | " + " / ".join(out))
print("\nper type AUC (qa / cov / combo):")
for t in sorted({r["type"] for r in U}):
    a = [r for r in A if r["type"] == t]; u = [r for r in U if r["type"] == t]
    print(f"  {t:26s} n_abs={len(u)}  " + "  ".join(f"{auc([r[k] for r in a],[r[k] for r in u]):.2f}" for k in ("qa", "cov", "combo")))
pct = lambda k, v: sum(r[k] < v for r in A) / len(A)
print("\nunanswerable questions, sorted by combo (higher = looks more answerable); pctl = share of answerable scoring lower")
for r in sorted(U, key=lambda r: -r["combo"]):
    print(f"  combo pctl {pct('combo', r['combo']):.2f} | qa {r['qa']:+.1f} cov {r['cov']:.2f} | {r['question'][:70]}  -> span: {r['qa_span'][:50]!r}")
print("\nanswerable with lowest combo (would be false abstentions):")
for r in sorted(A, key=lambda r: r["combo"])[:10]:
    print(f"  qa {r['qa']:+.1f} cov {r['cov']:.2f} hit={r['hit']} [{r['type']}] {r['question'][:80]}")
