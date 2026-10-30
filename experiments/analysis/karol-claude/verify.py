"""Answerability test: BM25 top-K chunks per question (no gold used), then lexical coverage vs SQuAD2 QA no-answer score."""
import sys, re, math, json, time; sys.path.insert(0, sys.argv[2]); D = sys.argv[1]; sys.argv = sys.argv[:2]
sys.stdout.reconfigure(encoding="utf-8")
from load import *
K = 8; CH = 1200
tok = lambda s: re.findall(r"[a-z0-9']+", s.lower())
STOP = set("the a an of to and in on for is it i my me you your was what how many did do does with at that this from by be are have has as or which when who where can could remind us we our time long much ago last first one did i'm i've".split())

def chunks(h):
    out = []
    for s in h["sessions"]:
        for t in s["turns"]:
            c = t["content"]
            for i in range(0, max(len(c), 1), CH):
                out.append((s["session_id"], s["date"], t["role"], c[i:i + CH + 200]))
    return out

def bm25_top(q, cs):
    docs = [tok(c[3]) for c in cs]; N = len(docs); avg = sum(map(len, docs)) / N
    df = Counter(w for d in docs for w in set(d))
    qt = [w for w in tok(q) if w not in STOP]
    idf = {w: math.log(1 + (N - df[w] + .5) / (df[w] + .5)) for w in qt}
    sc = []
    for i, d in enumerate(docs):
        tf = Counter(d); v = sum(idf[w] * tf[w] * 2.2 / (tf[w] + 1.2 * (.25 + .75 * len(d) / avg)) for w in qt if w in tf)
        sc.append((v, i))
    sc.sort(reverse=True)
    return [cs[i] for _, i in sc[:K]], idf

def coverage(idf, text):
    """idf-weighted share of question content words present in the chunk (crude prefix match for inflections)."""
    words = set(tok(text)); tot = sum(idf.values()) or 1
    return sum(v for w, v in idf.items() if any(x.startswith(w[:5]) for x in words)) / tot

rows = []
for q in Q:
    g = G[q["question_id"]]; cs = chunks(H[q["history_id"]])
    top, idf = bm25_top(q["question"], cs)
    rows.append({"qid": q["question_id"], "type": g["question_type"], "abstain": g["abstain"], "question": q["question"],
                 "top": top, "cov": max(coverage(idf, c[3]) for c in top),
                 "hit": any(c[0] in g["evidence"] for c in top)})
ans = [r for r in rows if not r["abstain"]]
print(f"recall: top-{K} chunks contain a gold session for {sum(r['hit'] for r in ans)}/{len(ans)} answerable")

import torch
from transformers import AutoTokenizer, AutoModelForQuestionAnswering
torch.set_num_threads(8)
M = "deepset/roberta-base-squad2"
tk = AutoTokenizer.from_pretrained(M); model = AutoModelForQuestionAnswering.from_pretrained(M).eval()

@torch.no_grad()
def qa_scores(question, texts):
    enc = tk([question] * len(texts), texts, truncation="only_second", max_length=384, padding=True, return_tensors="pt")
    out = model(**enc); res = []
    for b in range(len(texts)):
        st_, en = out.start_logits[b], out.end_logits[b]
        ctx = [i for i, s in enumerate(enc.sequence_ids(b)) if s == 1]
        null = (st_[0] + en[0]).item()
        s_c, e_c = st_[ctx], en[ctx]
        L = len(ctx); best, span = -1e9, (0, 0)
        top_s = torch.topk(s_c, min(20, L)).indices.tolist(); top_e = torch.topk(e_c, min(20, L)).indices.tolist()
        for i in top_s:
            for j in top_e:
                if i <= j < i + 30 and s_c[i] + e_c[j] > best: best, span = (s_c[i] + e_c[j]).item(), (ctx[i], ctx[j])
        ans_txt = tk.decode(enc["input_ids"][b][span[0]:span[1] + 1]).strip()
        res.append((best - null, ans_txt))
    return res

t0 = time.time()
for n, r in enumerate(rows):
    sc = qa_scores(r["question"], [f"[{c[1]}] {c[2]}: {c[3]}" for c in r["top"]])
    i = max(range(len(sc)), key=lambda k: sc[k][0])
    r["qa"], r["qa_span"], r["qa_sid"] = sc[i][0], sc[i][1], r["top"][i][0]
    if n % 100 == 0: print(n, f"{time.time() - t0:.0f}s", flush=True)
for r in rows: del r["top"]
json.dump(rows, open("verify_rows.json", "w", encoding="utf-8"), ensure_ascii=False)
print("done", f"{time.time() - t0:.0f}s")
