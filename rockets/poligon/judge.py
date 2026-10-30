"""Local LLM judge for score.py's "unjudged" answers, LongMemEval-style prompts, any OpenAI-compatible server.

    python score.py ../data/dev/gold.jsonl preds.jsonl --details details.jsonl
    python rockets/poligon/judge.py ../data/dev/gold.jsonl preds.jsonl details.jsonl --local http://127.0.0.1:8899 \\
        --out details-judged.jsonl
    python rockets/poligon/judge.py ../data/dev/gold.jsonl --selftest --local http://127.0.0.1:8899

Only rows score.py left "unjudged" (gold answerable, prediction not abstaining, no string match) go to the model;
its yes/no turns them into "correct" or "wrong". The rest is copied, so the printed table has score.py's columns
with "unjudged" near zero. Verdicts are cached in --cache by prompt hash, so reruns are free. The prompts follow
LongMemEval's evaluate_qa.py (default, temporal off-by-one, knowledge-update "updated answer wins") plus the
challenge's rule that several candidate answers, hedging or negation count as wrong.

--selftest needs no predictions: from dev gold it builds responses with a known verdict (the gold answer in a
sentence, another question's answer, hedged and negated gold, temporal off-by-one, knowledge-update with the old
value first) and prints the judge's agreement per kind. A stand-in model is a weak judge; check this first.
"""
import argparse
import hashlib
import json
import random
import re
import time
import urllib.request
from collections import defaultdict
from pathlib import Path

RULES = ("If the response is equivalent to the correct answer or contains all the intermediate steps to get the "
         "correct answer, you should also answer yes. If the response only contains a subset of the information "
         "required by the answer, answer no. If the response gives several different candidate answers, hedges "
         "between options, or says the correct answer is not the case, answer no.")
EXTRA = {
    "temporal-reasoning": " In addition, do not penalize off-by-one errors for the number of days. If the question "
                          "asks for the number of days/weeks/months, etc., and the model makes off-by-one errors "
                          "(e.g., predicting 19 days when the answer is 18), the model's response is still correct.",
    "knowledge-update": " If the response contains some previous information along with an updated answer, the "
                        "response should be considered as correct as long as the updated answer is the required "
                        "answer.",
}
PROMPT = ("I will give you a question, a correct answer, and a response from a model. Please answer yes if the "
          "response contains the correct answer. Otherwise, answer no. {rules}{extra}\n\nQuestion: {question}\n\n"
          "Correct Answer: {answer}\n\nModel Response: {response}\n\nIs the model response correct? "
          "Answer yes or no only.")


def rj(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def wj(path, rows):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def prompt_for(qtype, question, answer, response):
    return PROMPT.format(rules=RULES, extra=EXTRA.get(qtype, ""), question=question, answer=answer,
                         response=response)


class Judge:
    def __init__(self, url, model, cache):
        self.url, self.model, self.cache_path = url.rstrip("/"), model, Path(cache)
        self.cache = {}
        if self.cache_path.exists():
            self.cache = {r["key"]: r for r in rj(self.cache_path)}
        self.calls = 0

    def __call__(self, prompt):
        key = hashlib.sha1(f"{self.model}|{prompt}".encode()).hexdigest()
        if key not in self.cache:
            body = {"messages": [{"role": "user", "content": prompt}], "max_tokens": 8, "temperature": 0}
            if self.model:
                body["model"] = self.model
            req = urllib.request.Request(self.url + "/v1/chat/completions", json.dumps(body).encode(),
                                         {"Content-Type": "application/json"})
            raw = json.loads(urllib.request.urlopen(req, timeout=600).read())["choices"][0]["message"]["content"]
            m = re.search(r"\b(yes|no)\b", raw.lower())
            row = {"key": key, "verdict": m.group(1) if m else None, "raw": raw[:200]}
            self.cache[key] = row
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_path, "a", encoding="utf-8", newline="\n") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
            self.calls += 1
        return self.cache[key]["verdict"]


# summarize() follows the challenge's score.py, so the table means what score.py's table means.
COLUMNS = ("n", "correct", "unjudged", "abstention_n", "abstention_recall", "false_abstention", "evidence_f1")


def summarize(results):
    groups = defaultdict(list)
    for r in results:
        groups[r["question_type"]].append(r)
    groups = dict(sorted(groups.items()))
    groups["all"] = list(results)
    rows = {}
    for name, rs in groups.items():
        f1s = [r["evidence_f1"] for r in rs if r["evidence_f1"] is not None]
        abst = [r for r in rs if r["gold_abstain"]]
        answerable = [r for r in rs if not r["gold_abstain"]]
        rows[name] = {
            "n": len(rs),
            "correct": sum(r["answer"] == "correct" for r in rs) / len(rs),
            "unjudged": sum(r["answer"] == "unjudged" for r in rs) / len(rs),
            "abstention_n": len(abst),
            "abstention_recall": sum(r["abstain_ok"] for r in abst) / len(abst) if abst else None,
            "false_abstention": sum(not r["abstain_ok"] for r in answerable) / len(answerable) if answerable else None,
            "evidence_f1": sum(f1s) / len(f1s) if f1s else None,
        }
    return rows


def print_table(results):
    fmt = lambda v: "-" if v is None else f"{v:.3f}" if isinstance(v, float) else str(v)
    rows = summarize(results)
    width = max(map(len, ["type", *rows]))
    print(f"{'type':{width}s}  " + "  ".join(f"{c:>{max(len(c), 5)}s}" for c in COLUMNS))
    for name, row in rows.items():
        print(f"{name:{width}s}  " + "  ".join(f"{fmt(row[c]):>{max(len(c), 5)}s}" for c in COLUMNS))


def judge_run(args, judge):
    gold = {g["question_id"]: g for g in rj(args.gold)}
    preds = {p["question_id"]: p for p in rj(args.predictions)}
    qs = {}
    if args.questions:
        qs = {q["question_id"]: q["question"] for q in rj(args.questions)}
    else:
        qpath = Path(args.gold).with_name("questions.jsonl")
        qs = {q["question_id"]: q["question"] for q in rj(qpath)}
    out, t = [], time.time()
    todo = [r for r in rj(args.details) if r["answer"] == "unjudged"]
    print(f"{len(todo)} unjudged answers to judge", flush=True)
    for r in rj(args.details):
        r = dict(r)
        if r["answer"] == "unjudged":
            g, p = gold[r["question_id"]], preds[r["question_id"]]
            v = judge(prompt_for(g["question_type"], qs[r["question_id"]], g["answer"], p["answer"]))
            r["judge"] = v
            r["answer"] = {"yes": "correct", "no": "wrong"}.get(v, "unjudged")
        out.append(r)
    print(f"judged in {time.time() - t:.0f}s, {judge.calls} model calls (rest cached)")
    if args.out:
        wj(args.out, out)
    print_table(out)


def selftest(args, judge):
    """Responses with a known verdict, built from gold; agreement of the judge per kind."""
    gold = [g for g in rj(args.gold) if not g["abstain"]]
    qs = {q["question_id"]: q["question"] for q in rj(Path(args.gold).with_name("questions.jsonl"))}
    rng = random.Random(0)
    rng.shuffle(gold)
    by_type = defaultdict(list)
    for g in gold:
        by_type[g["question_type"]].append(g)
    cases = []
    for t, gs in sorted(by_type.items()):
        for i, g in enumerate(gs[:args.per_type]):
            other = gs[(i + 1) % len(gs)]["answer"]
            a = g["answer"]
            cases.append(("gold in a sentence", True, g, f"Based on our earlier conversations, the answer is {a}."))
            cases.append(("another question's answer", False, g, f"Based on our earlier conversations, {other}."))
            cases.append(("hedged between two", False, g, f"It is either {a} or {other}, I am not sure which."))
            cases.append(("negated gold", False, g, f"It was not {a}."))
            if t == "knowledge-update":
                cases.append(("old value, then updated", True, g,
                              f"You first mentioned {other}, but later you updated it: {a}."))
    for g in by_type["temporal-reasoning"]:  # every day count, not only the first per_type: they are few
        n = re.match(r"(\d+)\s+days?\b", g["answer"].strip(), re.I)  # "7 days. 8 days (including ...) is also ok"
        if n:
            cases.append(("temporal off by one", True, g, f"{int(n.group(1)) + 1} days"))
            cases.append(("temporal off by five", False, g, f"{int(n.group(1)) + 5} days"))
    t0, agree = time.time(), defaultdict(list)
    for kind, want, g, resp in cases:
        v = judge(prompt_for(g["question_type"], qs[g["question_id"]], g["answer"], resp))
        agree[kind].append(v == ("yes" if want else "no"))
        agree["all"].append(v == ("yes" if want else "no"))
    print(f"{len(cases)} cases in {time.time() - t0:.0f}s ({judge.calls} model calls)")
    for kind, xs in agree.items():
        print(f"  {kind:28s} {sum(xs):4d}/{len(xs):<4d} {sum(xs) / len(xs):.3f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("gold")
    ap.add_argument("predictions", nargs="?")
    ap.add_argument("details", nargs="?", help="score.py --details output for these predictions")
    ap.add_argument("--questions", help="questions.jsonl (default: next to gold)")
    ap.add_argument("--local", required=True, help="OpenAI-compatible server, e.g. http://127.0.0.1:8899")
    ap.add_argument("--model", default="", help="model name, if the server needs one")
    ap.add_argument("--cache", default=str(Path.home() / ".cache" / "poligon-judge.jsonl"))
    ap.add_argument("--out", help="write judged details here")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--per-type", type=int, default=20, help="selftest: gold questions per type")
    args = ap.parse_args()
    judge = Judge(args.local, args.model, args.cache)
    if args.selftest:
        selftest(args, judge)
    else:
        if not (args.predictions and args.details):
            ap.error("predictions and details are required unless --selftest")
        judge_run(args, judge)


if __name__ == "__main__":
    main()
