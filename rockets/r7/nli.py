"""Experiment, step 2 of the NLI gate: is each claim (claims.py) entailed by some sentence window of the retrieved
chunks? Claims about me are checked against my own turns, claims about what the assistant said ("You told me ...")
against the assistant's. support = the weakest claim's best entailment probability; low support suggests abstaining.

    python rockets/r7/nli.py ../data/dev_hard claims.jsonl out.jsonl
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rocket  # noqa: E402
from memsys import load_split  # noqa: E402  (R1, read-only)

MODEL = "MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli"
N_CHUNKS, WINDOW, MAX_CHARS = 12, 2, 400
_tk = _model = None


def load():
    global _tk, _model
    if _model is None:
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
        torch.set_num_threads(8)
        _tk = AutoTokenizer.from_pretrained(MODEL)
        _model = AutoModelForSequenceClassification.from_pretrained(MODEL).eval()
    return _tk, _model


def windows(text):
    """Windows of WINDOW consecutive sentences, at most MAX_CHARS each."""
    sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", text) if len(s.strip()) > 3]
    return [" ".join(sents[i:i + WINDOW])[:MAX_CHARS] for i in range(max(1, len(sents) - WINDOW + 1))] if sents else []


def invented(claim, question):
    """The LLM wrote a name the question does not have ("I met Sophia in Paris." for "Where did I meet Sophia?"):
    it filled in an answer, and no excerpt can entail a made-up one, so the claim is not checked."""
    qw = set(re.findall(r"[a-z]+", question.lower()))
    return any(t[0].isupper() and t.lower() not in qw and t not in ("I", "You")
               for t in re.findall(r"[A-Za-z]+", claim)[1:])


def entail(pairs):
    import torch
    tk, model = load()
    ent = [i for i, lab in model.config.id2label.items() if lab.lower().startswith("entail")][0]
    out = []
    with torch.no_grad():
        for b in range(0, len(pairs), 32):
            enc = tk([p for p, _ in pairs[b:b + 32]], [h for _, h in pairs[b:b + 32]], truncation="only_first",
                     max_length=256, padding=True, return_tensors="pt")
            out.extend(torch.softmax(model(**enc).logits, -1)[:, ent].tolist())
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("split")
    ap.add_argument("claims")
    ap.add_argument("out")
    args = ap.parse_args()
    hist, qs, _ = load_split(args.split)
    qmap = {q["question_id"]: q for q in qs}
    rows = [json.loads(line) for line in open(args.claims, encoding="utf-8") if line.strip()]
    with open(args.out, "w", encoding="utf-8") as f:
        for i, r in enumerate(rows, 1):
            q = qmap[r["question_id"]]
            cands = rocket.retrieve(q, hist[q["history_id"]])
            seen, chunks = set(), []
            for c in cands:
                key = (c["session_id"], c["turn"], c["text"][:50])
                if key not in seen:
                    seen.add(key)
                    chunks.append(c)
                if len(chunks) == N_CHUNKS:
                    break
            per_claim = []
            for claim in [c for c in r["claims"] if not invented(c, q["question"])]:
                role = "assistant" if re.match(r"(you|the assistant)\b", claim, re.I) else "user"
                prem = [(w, c["session_id"]) for c in chunks if c["role"] == role for w in windows(c["text"])]
                if not prem:
                    per_claim.append({"claim": claim, "best": 0.0, "window": "", "session": None})
                    continue
                ps = entail([(w, claim) for w, _ in prem])
                k = max(range(len(ps)), key=ps.__getitem__)
                per_claim.append({"claim": claim, "best": round(ps[k], 4), "window": prem[k][0][:200],
                                  "session": prem[k][1]})
            # no claim left to check: no NLI decision (support 1.0)
            f.write(json.dumps({"question_id": r["question_id"], "support": min((c["best"] for c in per_claim),
                                                                                default=1.0),
                                "claims": per_claim}) + "\n")
            f.flush()
            if i % 25 == 0:
                print(f"{i}/{len(rows)}", flush=True)


if __name__ == "__main__":
    main()
