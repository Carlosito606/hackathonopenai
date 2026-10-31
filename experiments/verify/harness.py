"""VERIFIER experiment harness: fixed stratified dev sample (no holdout), cached retrieval, plan variants, judge.

    python experiments/verify/harness.py cands ../data/dev ../cache/dev-verify.pkl cands.pkl
    python experiments/verify/harness.py plan ../data/dev cands.pkl plan-V.jsonl --variant V
    python experiments/verify/harness.py judge ../data/dev pred-V.jsonl details-V.jsonl --score ../repo/score.py
"""
import argparse
import json
import pickle
import random
import sys
import urllib.request
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import prepare  # noqa: E402
from memsys import load_split  # noqa: E402

HOLDOUT = Path(__file__).resolve().parents[2] / "splits" / "dev_holdout.txt"


def sample(qs, gold, per_type=15, seed=0):
    """All non-holdout abstention questions + per_type answerable questions of each type."""
    hold = set(HOLDOUT.read_text().split())
    pool = [q for q in qs if q["question_id"] not in hold]
    out = [q for q in pool if gold[q["question_id"]]["abstain"]]
    by_type = defaultdict(list)
    for q in pool:
        if not gold[q["question_id"]]["abstain"]:
            by_type[gold[q["question_id"]]["question_type"]].append(q)
    rng = random.Random(seed)
    for t in sorted(by_type):
        out += rng.sample(by_type[t], min(per_type, len(by_type[t])))
    return out


BUILD = prepare.build_evidence


def budget(n):
    return lambda h, c, **kw: BUILD(h, c, **{**kw, "budget": n})


BASE = """
(How to answer: the evidence is excerpts from my own past chats with you, oldest first, each with its date; "user" is me, "assistant" is you.
- Some excerpts are near misses: other people's things, other pets, a different event, a plan that changed, or a value I corrected later. Use only what matches the question exactly.
- If it changed over time, the most recent conversation wins.
- The final line holds only the short answer (a name, number, date or short phrase) and the labels of the excerpts that state it, e.g. "Sombra [E4]". One answer, no hedging, no alternatives.
- Write INSUFFICIENT_EVIDENCE only if no excerpt states what is asked.{extra})"""
QUOTE = """
(How to answer: the evidence is excerpts from my own past chats with you, each with its date; "user" is me, "assistant" is you.
- First write "Quotes:" and copy, word for word, the sentence(s) from the excerpts that answer the question, each with its label, e.g. [E3] "I just started reading The Nightingale". The answer is often a side remark in a chat about something else, and may use other words than the question.
- If it changed over time, the most recent conversation wins.
- Then the final line holds only the short answer (a name, number, date or short phrase) and the labels of the excerpts you quoted, e.g. "Sombra [E4]". One answer, no hedging, no alternatives.
- Write INSUFFICIENT_EVIDENCE only if you could quote nothing that answers it, or what you quoted is about a different person, thing or event than the question asks about.{extra})"""
QUOTE2 = """
(How to answer: the evidence is excerpts from my own past chats with you, each with its date; "user" is me, "assistant" is you.
- First write "Quotes:" and copy, word for word, the sentence(s) from the excerpts that answer the question, each with its label, e.g. [E3] "I just started reading The Nightingale". The answer is often a side remark in a chat about something else, and may use other words than the question.
- Then write "Check:" and say whether the quotes are about the very thing the question names (the same person, place, item, activity). A similar but different one (guitar for violin, tennis for table tennis, Japan for Korea, a friend for me) does not answer it.
- If it changed over time, the most recent conversation wins.
- The final line holds only the short answer (a name, number, date or short phrase) and the labels of the excerpts you quoted, e.g. "Sombra [E4]". One answer, no hedging, no alternatives.
- Write INSUFFICIENT_EVIDENCE only if you could quote nothing that answers it, or the check failed.{extra})"""
# Runs up to quote8k+v put the "+v" note at the end of the GUIDE; "final" is prepare.py as committed.
VARIANTS = {
    "base": {"GUIDE": BASE, "build_evidence": budget(18000)},
    "base_s": {"GUIDE": BASE, "build_evidence": budget(18000)},  # base again, with the fixed ref seed
    "quote": {"GUIDE": QUOTE, "build_evidence": budget(18000)},
    "quote2": {"GUIDE": QUOTE2, "build_evidence": budget(18000)},
    "quote8k": {"GUIDE": QUOTE, "build_evidence": budget(8000)},
    "final": {},
    "final2": {},  # final after "labels count only on that line" was added to the GUIDE
}


def judge_prompt(question, gold, answer):
    return (f"Question: {question}\nCorrect answer: {gold}\nModel answer: {answer}\n\n"
            "Does the model answer contain the correct answer or an equivalent of it (same meaning; for numbers, the "
            "same value; partial lists or a different value count as wrong)? Reply with yes or no only.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["cands", "plan", "judge"])
    ap.add_argument("split")
    ap.add_argument("a")
    ap.add_argument("b")
    ap.add_argument("--variant", default="base")
    ap.add_argument("--local", default="http://127.0.0.1:8899")
    ap.add_argument("--score", default="../repo/score.py", help="the challenge's score.py")
    args = ap.parse_args()
    hist, qs, gold = load_split(args.split)
    qs = sample(qs, gold)
    if args.cmd == "cands":
        emb = prepare.Embedder(args.a)
        out = pickle.loads(Path(args.b).read_bytes()) if Path(args.b).exists() else {}  # resumable
        for i, q in enumerate(qs, 1):
            if q["question_id"] not in out:
                out[q["question_id"]] = prepare.retrieve(hist[q["history_id"]], q["question"], emb)
            if i % 10 == 0:
                Path(args.b).write_bytes(pickle.dumps(out))
                print(i, flush=True)
        Path(args.b).write_bytes(pickle.dumps(out))
    elif args.cmd == "plan":
        cands = pickle.loads(Path(args.a).read_bytes())
        prepare.retrieve = lambda history, question, emb: cands[current["qid"]]
        current = {}
        variant = args.variant.removesuffix("+v")  # "+v": with verify.py's note on missing names
        if variant == args.variant:
            prepare.missing_names = lambda question, history: []
        for name, value in VARIANTS[variant].items():
            setattr(prepare, name, value)
        with open(args.b, "w", encoding="utf-8") as f:
            for q in qs:
                current["qid"] = q["question_id"]
                p = prepare.plan_question(q, hist[q["history_id"]], None)
                f.write(json.dumps(p) + "\n")
    else:
        import importlib.util
        spec = importlib.util.spec_from_file_location("score", args.score)
        score = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(score)
        preds = {p["question_id"]: p for p in map(json.loads, open(args.a))}
        rows = []
        for q in qs:
            g, p = gold[q["question_id"]], preds.get(q["question_id"])
            r = score.score_question(p, g)
            r["pred_abstain"] = bool(p and p["abstain"])
            if r["answer"] == "unjudged":
                body = json.dumps({"messages": [{"role": "user", "content": judge_prompt(
                    q["question"], g["answer"], p["answer"])}], "max_tokens": 3, "temperature": 0}).encode()
                req = urllib.request.Request(args.local + "/v1/chat/completions", body,
                                             {"Content-Type": "application/json"})
                reply = json.loads(urllib.request.urlopen(req, timeout=300).read())["choices"][0]["message"]["content"]
                r["judged"] = "correct" if reply.strip().lower().startswith("yes") else "wrong"
            rows.append(r)
        with open(args.b, "w") as f:
            for r in rows:
                f.write(json.dumps(r) + "\n")
        report(rows)


def report(rows):
    types = sorted({r["question_type"] for r in rows}) + ["ALL"]
    print(f"{'type':26} {'n':>3} {'acc':>5} {'match':>5} {'judg':>5} {'fabst':>5} {'abs_n':>5} {'abs_rec':>7} {'evF1':>5}")
    for t in types:
        rs = [r for r in rows if t == "ALL" or r["question_type"] == t]
        ans = [r for r in rs if not r["gold_abstain"]]
        ab = [r for r in rs if r["gold_abstain"]]
        ok = [r for r in ans if r["answer"] == "correct" or r.get("judged") == "correct"]
        f1 = [r["evidence_f1"] for r in ans if r.get("evidence_f1") is not None]
        n = max(len(ans), 1)
        print(f"{t:26} {len(rs):3} {len(ok)/n:5.3f} {sum(r['answer'] == 'correct' for r in ans)/n:5.3f} "
              f"{sum(r.get('judged') == 'correct' for r in ans)/n:5.3f} "
              f"{sum(r['pred_abstain'] for r in ans)/n:5.3f} {len(ab):5} "
              f"{(sum(r['pred_abstain'] for r in ab)/len(ab)) if ab else float('nan'):7.3f} "
              f"{(sum(f1)/len(f1)) if f1 else float('nan'):5.3f}")


if __name__ == "__main__":
    main()
