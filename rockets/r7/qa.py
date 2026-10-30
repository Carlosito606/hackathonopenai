"""SQuAD 2.0 no-answer signal: best span score minus the no-answer score over the top candidate chunks.
Forked from experiments/analysis/karol-claude/verify.py (qa_scores). Needs torch and transformers
(rockets/r7/requirements.txt; on Windows with an old VC++ runtime torch==2.6.0 loads where newer ones fail)."""
import re

MODEL = "deepset/roberta-base-squad2"
K, CHUNK = 8, 1200
_tk = _model = None

# Question shapes the QA signal is used for. Test has no type labels, so the type is guessed from the question:
# the signal separates answerable questions well for single-fact lookups (AUC 0.95-0.99 on single-session-user and
# knowledge-update) and badly for computed answers: dates, counts, sums, orderings, comparisons (0.65 temporal).
# "How long" and "how much" stay in: their answers are usually stated ("How long was I in Korea for?").
COMPUTED = re.compile(r"how many (days|weeks|months|years)|when did|what date|\b(who|which|what)\b.*\b(first|earlier|"
                      r"later)\b|\bago\b|\border\b|before or after|\bhow many\b|\btotal\b|\bcombined\b|\bin all\b|"
                      r"\baltogether\b|\bdifference\b|\bpercentage\b|\baverage\b|\bbetween\b|\bthan\b", re.I)


def load(device="cpu"):
    global _tk, _model
    if _model is None:
        import torch
        from transformers import AutoModelForQuestionAnswering, AutoTokenizer
        torch.set_num_threads(8)
        _tk = AutoTokenizer.from_pretrained(MODEL)
        _model = AutoModelForQuestionAnswering.from_pretrained(MODEL).to(device).eval()
    return _tk, _model


def scores(question, texts):
    """[(best span minus no-answer, span text)] per text."""
    import torch
    tk, model = load()
    with torch.no_grad():
        enc = tk([question] * len(texts), texts, truncation="only_second", max_length=384, padding=True,
                 return_tensors="pt")
        out = model(**enc)
    res = []
    for b in range(len(texts)):
        st, en = out.start_logits[b], out.end_logits[b]
        ctx = [i for i, s in enumerate(enc.sequence_ids(b)) if s == 1]
        null = (st[0] + en[0]).item()
        s_c, e_c = st[ctx], en[ctx]
        n = len(ctx)
        best, span = -1e9, (0, 0)
        top_s = torch.topk(s_c, min(20, n)).indices.tolist()
        top_e = torch.topk(e_c, min(20, n)).indices.tolist()
        for i in top_s:
            for j in top_e:
                if i <= j < i + 30 and s_c[i] + e_c[j] > best:
                    best, span = (s_c[i] + e_c[j]).item(), (ctx[i], ctx[j])
        res.append((best - null, tk.decode(enc["input_ids"][b][span[0]:span[1] + 1]).strip()))
    return res


def signal(q, h, cands):
    """{"qa", "qa_span", "qa_session"} from the first K distinct chunks of the candidates, each prefixed with its
    session date and role as in verify.py."""
    dates = {s["session_id"]: s["date"] for s in h["sessions"]}
    seen, texts, sids = set(), [], []
    for c in cands:
        key = (c["session_id"], c["turn"], c["text"][:50])
        if key in seen:
            continue
        seen.add(key)
        texts.append(f"[{dates[c['session_id']]}] {c['role']}: {c['text'][:CHUNK + 200]}")
        sids.append(c["session_id"])
        if len(texts) == K:
            break
    if not texts:
        return {"qa": None, "qa_span": "", "qa_session": None}
    sc = scores(q["question"], texts)
    i = max(range(len(sc)), key=lambda k: sc[k][0])
    return {"qa": round(sc[i][0], 4), "qa_span": sc[i][1], "qa_session": sids[i]}
